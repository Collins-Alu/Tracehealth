"""
DevicePushToken: where to send push notifications for a user (Sprint 2).

The mobile app registers its Expo push token after login and removes it on
logout. One user can have several devices. A token that Expo reports as no
longer registered (app uninstalled) is deleted automatically.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class DevicePushToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "device_push_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Unique: if another account logs in on the same phone, the token moves to them
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # android | ios
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
