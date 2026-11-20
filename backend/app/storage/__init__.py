"""Choose photo storage with STORAGE_BACKEND (local | s3 | database). See .env.example."""

from app.core.config import get_settings
from app.storage.base import PhotoStorage
from app.storage.database import DatabasePhotoStorage
from app.storage.local import LocalPhotoStorage
from app.storage.s3_compatible import S3PhotoStorage

_s3: S3PhotoStorage | None = None


def get_storage() -> PhotoStorage:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "s3":
        global _s3
        if _s3 is None:
            if not settings.S3_BUCKET:
                raise RuntimeError("STORAGE_BACKEND=s3 needs S3_BUCKET (see .env.example).")
            _s3 = S3PhotoStorage(
                settings.S3_BUCKET,
                endpoint_url=settings.S3_ENDPOINT_URL,
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            )
        return _s3
    if settings.STORAGE_BACKEND == "database":
        from app.db.session import SessionLocal

        return DatabasePhotoStorage(SessionLocal)
    # Read UPLOAD_DIR each time so tests can point it at a temporary folder
    return LocalPhotoStorage(settings.UPLOAD_DIR)


__all__ = ["PhotoStorage", "get_storage"]
