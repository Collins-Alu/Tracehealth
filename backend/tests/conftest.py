"""
Shared test fixtures.

Tests run against a SEPARATE database (TEST_DATABASE_URL) that is wiped and
rebuilt from the Alembic migrations at the start of every test session, so the
tests always check the real schema, triggers included.

Each test runs inside a transaction that is rolled back afterwards, so tests
never see each other's data and the database stays clean.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.core.config import BACKEND_DIR, get_settings


def _test_database_url() -> str:
    settings = get_settings()
    url = settings.TEST_DATABASE_URL
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set. Add it to your .env file.", returncode=1)
    if url == settings.DATABASE_URL:
        pytest.exit(
            "TEST_DATABASE_URL must differ from DATABASE_URL: the tests wipe their database.",
            returncode=1,
        )
    return url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _test_database_url()


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = test_database_url
    return config


@pytest.fixture(scope="session")
def engine(test_database_url: str, alembic_config: Config):
    engine = create_engine(test_database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()

