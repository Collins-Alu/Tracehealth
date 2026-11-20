"""Photos stored in PostgreSQL (STORAGE_BACKEND=database, free cloud hosting)."""

from contextlib import contextmanager

from app.core.config import Settings
from app.storage.database import DatabasePhotoStorage


def test_database_storage_round_trip_and_overwrite(db):
    @contextmanager
    def same_session():
        yield db  # the test's rolled-back session

    storage = DatabasePhotoStorage(same_session)
    storage.save("reports/2026/11/a.jpg", b"first")
    storage.save("reports/2026/11/a.jpg", b"second")  # same key: replaced, not duplicated
    assert storage.read("reports/2026/11/a.jpg") == b"second"
    assert storage.read("reports/missing.jpg") is None
    storage.delete("reports/2026/11/a.jpg")
    assert storage.read("reports/2026/11/a.jpg") is None


def test_hosting_provider_database_urls_get_the_psycopg_driver():
    def url(raw: str) -> str:
        return Settings(DATABASE_URL=raw, JWT_SECRET_KEY="x" * 40).DATABASE_URL

    neon = "postgresql://user:pw@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert (
        url(neon)
        == "postgresql+psycopg://user:pw@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    )
    assert url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
