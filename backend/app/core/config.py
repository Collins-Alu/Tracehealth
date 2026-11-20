"""
Application configuration.

All settings are read from environment variables (or a .env file) so that no
secret ever lives in source code. pydantic-settings validates the values at
startup: if a required variable is missing, the app refuses to start with a
clear error instead of failing later in a confusing way.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the repository root
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # The root .env is shared with docker-compose; backend/.env (optional)
        # can override it for backend-only experiments.
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "TraceHealth API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | test | demo | production

    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL")
    @classmethod
    def _use_psycopg_driver(cls, v: str | None) -> str | None:
        # Hosting providers (Neon, Render, Heroku-style) give "postgres://" or
        # "postgresql://" URLs; SQLAlchemy needs the psycopg 3 driver named.
        if v and v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v and v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://") :]
        return v

    # Per API worker process. Keep workers x (pool + overflow) below the
    # database's max_connections (PostgreSQL default 100), leaving room for
    # migrations and admin tools: 4 workers x 15 = 60.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: int = 10

    # Comma-separated list of browser origins allowed to call the API
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173"

    # Only used by scripts/seed.py in development
    SEED_DEFAULT_PASSWORD: str = "ChangeMe123!"

    # --- Authentication (Sprint 1) ---------------------------------------
    # Signs every access token. Must be long and random; see .env.example.
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    # Short-lived: a stolen access token is only useful for a few minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # Long-lived but revocable (stored hashed in refresh_tokens)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    # Phone numbers typed as 07XXXXXXXX are stored as +2547XXXXXXXX
    DEFAULT_COUNTRY_CODE: str = "254"

    # --- Report photos (Sprint 1) ----------------------------------------
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    MAX_PHOTO_MB: int = 8
    # Photos are shrunk so their longest side is at most this many pixels
    PHOTO_MAX_DIMENSION: int = 1600
    # Offline reports may be synced late, but not absurdly late
    REPORT_MAX_AGE_DAYS: int = 30

    # --- Notifications (Sprint 2) ----------------------------------------
    # mock     = log only, nothing leaves the server (default; clearly marked MOCK-)
    # expo     = Expo push service
    # disabled = in-app inbox only
    PUSH_PROVIDER: Literal["mock", "expo", "disabled"] = "mock"
    # Only needed if "enhanced push security" is switched on in your Expo project
    EXPO_ACCESS_TOKEN: str | None = None

    # mock | africastalking | disabled
    SMS_PROVIDER: Literal["mock", "africastalking", "disabled"] = "mock"
    AT_USERNAME: str = "sandbox"  # "sandbox" for the Africa's Talking sandbox
    AT_API_KEY: str | None = None
    AT_SENDER_ID: str | None = None  # optional; not needed in the sandbox
    # Leave unset to choose the sandbox or live URL from AT_USERNAME
    AT_API_URL: str | None = None

    # --- Incentive payouts -----------------------------------------------
    # Sprint 2 records a PENDING payout when a report is verified; Sprint 4
    # adds the adapter that actually sends it. MOCK = no real money.
    PAYOUT_PROVIDER: Literal["MOCK", "MPESA_DARAJA"] = "MOCK"
    # Give up on automatic retries after this many attempts
    PAYOUT_MAX_ATTEMPTS: int = 5
    # An accepted M-Pesa request with no result after this long is marked FAILED
    PAYOUT_RESULT_TIMEOUT_HOURS: int = 24

    # --- M-Pesa Daraja B2C (Sprint 4; see .env.example) -----------------
    MPESA_ENVIRONMENT: Literal["sandbox", "production"] = "sandbox"
    MPESA_CONSUMER_KEY: str | None = None
    MPESA_CONSUMER_SECRET: str | None = None
    MPESA_SHORTCODE: str | None = None
    MPESA_INITIATOR_NAME: str | None = None
    MPESA_SECURITY_CREDENTIAL: str | None = None
    # Public HTTPS address of this API, used for M-Pesa result callbacks
    MPESA_CALLBACK_BASE_URL: str | None = None
    # Long random secret included in the callback path, so only M-Pesa
    # (who was given the URL) can post results
    MPESA_CALLBACK_TOKEN: str | None = None
    MPESA_B2C_PATH: str = "/mpesa/b2c/v1/paymentrequest"

    # --- Background jobs (Sprint 4) ---------------------------------------
    # Every JOBS_INTERVAL_SECONDS: send pending payouts, expire stale M-Pesa
    # requests, retry undelivered notifications. Off in tests.
    BACKGROUND_JOBS_ENABLED: bool = True
    JOBS_INTERVAL_SECONDS: int = 60

    # --- Photo storage (D6) ---------------------------------------------
    STORAGE_BACKEND: Literal["local", "s3", "database"] = "local"
    S3_BUCKET: str | None = None
    S3_ENDPOINT_URL: str | None = None  # e.g. Cloudflare R2 or MinIO; empty for AWS
    S3_REGION: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def at_messaging_url(self) -> str:
        if self.AT_API_URL:
            return self.AT_API_URL
        if self.AT_USERNAME == "sandbox":
            return "https://api.sandbox.africastalking.com/version1/messaging"
        return "https://api.africastalking.com/version1/messaging"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
