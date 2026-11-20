"""
Database engine and session handling.

We use SQLAlchemy's synchronous API with a connection pool. FastAPI runs
synchronous endpoints in a worker thread pool, so requests still run
concurrently; this keeps the code easier to read while comfortably meeting the
pilot's 200-concurrent-reporter target (verified with a load test in Sprint 4).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,  # wait for a free connection, then 503
    pool_pre_ping=True,  # transparently replaces connections the server dropped
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
