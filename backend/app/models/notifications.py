import uuid
from datetime import datetime

from sqlalchemy import DateTime, Foreignkey, INdex, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modeld.enums import NotificationChannel, NotifictionStatus
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column

class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, base):
    __tablename__ = "notifications"
    __table_args__ = (index("ix_notificatons_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True), ForeignKey("users.id", onddelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
            enum_column(NotificationChannel, "notification_channel"), nullable=False
    )
    status: mapped[NotificationStatus] = mapped_column(
            enum_column(NotificationStatus, "notification_status"),
            nullable=False,
            default=NotificationStatus.PENDING,
            server_default=NotificationStatus.PENDING.value,
    )
    related_reporter_id: Mapped[uuid.UUID | None] = mapped_column(
            UUID(as_uuid=True), ForeignKey("pollution_reports.id", ondelete="SET NULL")
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

