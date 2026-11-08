"""
Application configuration.

All settings are read from environment variables (or a .env file) so that no
secret ever lives in source code. pydantic-settings validates the values at
startup: if a required variable is missing, the app refuses to start with a
clear error instead of failing later in a confusing way.
"""

from functools import lru_cache
from pathlib import Path

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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

