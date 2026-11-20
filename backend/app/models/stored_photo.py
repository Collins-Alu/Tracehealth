"""
StoredPhoto: report photos kept inside PostgreSQL (STORAGE_BACKEND=database).

Used on free cloud hosting (e.g. Render) where the server's disk is wiped on
every restart and no object storage is set up. Photos are already shrunk to at
most 1600 px JPEG on upload (typically 100-300 KB), so a pilot's photos fit
comfortably. For larger deployments use local disk on a server or S3 (D6).
"""

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StoredPhoto(Base):
    __tablename__ = "stored_photos"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
