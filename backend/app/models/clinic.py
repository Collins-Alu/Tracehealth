
import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ConditionCategory, ImportBatchStatus
from app.models.geo import location_column_type, location_computed
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column


class Facility(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "facilities"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        Index("ix_facilities_location", "location", postgresql_using="gist"),
    )

    # The code the clinic or ministry uses for the facility (e.g. a KMHFL code)
    external_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    location = mapped_column(location_column_type(), location_computed(), nullable=False)
    area_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    visit_summaries: Mapped[list["ClinicVisitSummary"]] = relationship(
        back_populates="facility", cascade="all, delete-orphan", passive_deletes=True
    )


class ClinicImportBatch(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "clinic_import_batches"
    __table_args__ = (CheckConstraint("row_count >= 0", name="row_count_non_negative"),)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("administrators.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ImportBatchStatus] = mapped_column(
        enum_column(ImportBatchStatus, "import_batch_status"), nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # Validation errors for rejected files: [{"row": 3, "field": "...", "message": "..."}]
    errors: Mapped[list | None] = mapped_column(JSONB)

    summaries: Mapped[list["ClinicVisitSummary"]] = relationship(back_populates="import_batch")


class ClinicVisitSummary(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "clinic_visit_summaries"
    __table_args__ = (
        CheckConstraint("visit_count >= 0", name="visit_count_non_negative"),
        CheckConstraint("period_end >= period_start", name="period_order"),
        UniqueConstraint(
            "facility_id",
            "condition_category",
            "period_start",
            "period_end",
            name="uq_clinic_visit_summaries_facility_condition_period",
        ),
        Index("ix_clinic_visit_summaries_period", "period_start", "period_end"),
    )

    # Composition (filled diamond in B.2b): a summary cannot outlive its facility
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False
    )
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_import_batches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    condition_category: Mapped[ConditionCategory] = mapped_column(
        enum_column(ConditionCategory, "condition_category"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False)

    facility: Mapped[Facility] = relationship(back_populates="visit_summaries")
    import_batch: Mapped[ClinicImportBatch] = relationship(back_populates="summaries")

