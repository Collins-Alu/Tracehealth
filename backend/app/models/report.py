"""PollutionReport (UML B.2a): one observed pollution event."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PollutionCategory, ReportStatus, SyncStatus
from app.models.geo import location_column_type, location_computed
from app.models.mixins import UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.models.user import Reporter
    from app.models.verification import Verification


class PollutionReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pollution_reports"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint(
            "description IS NULL OR char_length(description) <= 1000",
            name="description_length",
        ),
        Index("ix_pollution_reports_location", "location", postgresql_using="gist"),
        Index("ix_pollution_reports_status_captured_at", "status", "captured_at"),
    )

    # Generated on the phone when the report is created (even offline).
    # The UNIQUE constraint makes re-sending the same report harmless.
    client_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reporters.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    photo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    location = mapped_column(location_column_type(), location_computed(), nullable=False)
    category: Mapped[PollutionCategory] = mapped_column(
        enum_column(PollutionCategory, "pollution_category"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    # When the photo was taken on the device (may be hours before upload if offline)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # When the server received it
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[ReportStatus] = mapped_column(
        enum_column(ReportStatus, "report_status"),
        nullable=False,
        default=ReportStatus.PENDING,
        server_default=ReportStatus.PENDING.value,
    )
    sync_status: Mapped[SyncStatus] = mapped_column(
        enum_column(SyncStatus, "sync_status"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    reporter: Mapped["Reporter"] = relationship(back_populates="reports")
    verifications: Mapped[list["Verification"]] = relationship(
        back_populates="report", order_by="Verification.verified_at"
    )

