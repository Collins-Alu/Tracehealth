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

from pydantic import Field
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
    ENVIRONMENT: str = "development"  # development | test | production

    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Comma-separated list of browser origins allowed to call the API
    CORS_ORIGINS: str = "http://localhost:5173"

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
