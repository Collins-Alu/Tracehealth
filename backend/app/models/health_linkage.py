"""
HealthLinkage (UML B.2b): a statistical association between one verified
report and visit counts for one condition at one nearby facility.

The method  compares visit rates in a follow-up window after the report with a
baseline window before it. Results are associations, never proof of
causation. When there is not enough data, status is INSUFFICIENT_DATA and the
statistical fields stay empty rather than being invented.

HealthLinkageEvidence records exactly which clinic summaries were used, so
every result can be traced and reproduced.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ConditionCategory, EvidenceWindow, LinkageStatus
from app.models.mixins import UUIDPrimaryKeyMixin, enum_column


class HealthLinkage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "health_linkages"
    __table_args__ = (
        CheckConstraint("radius_km > 0", name="radius_positive"),
        CheckConstraint("distance_km >= 0", name="distance_non_negative"),
        CheckConstraint("p_value IS NULL OR p_value BETWEEN 0 AND 1", name="p_value_range"),
        CheckConstraint(
            "correlation_score IS NULL OR correlation_score BETWEEN -1 AND 1",
            name="correlation_range",
        ),
        CheckConstraint("rate_ratio IS NULL OR rate_ratio >= 0", name="rate_ratio_non_negative"),
        CheckConstraint(
            "status = 'INSUFFICIENT_DATA' OR (rate_ratio IS NOT NULL AND p_value IS NOT NULL)",
            name="statistics_required_for_result",
        ),
        UniqueConstraint(
            "report_id",
            "facility_id",
            "condition_category",
            name="uq_health_linkages_report_facility_condition",
        ),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pollution_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    condition_category: Mapped[ConditionCategory] = mapped_column(
        enum_column(ConditionCategory, "condition_category"), nullable=False
    )
    radius_km: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    distance_km: Mapped[float] = mapped_column(Double, nullable=False)
    baseline_visits: Mapped[int | None] = mapped_column(Integer)
    followup_visits: Mapped[int | None] = mapped_column(Integer)
    rate_ratio: Mapped[float | None] = mapped_column(Double)
    p_value: Mapped[float | None] = mapped_column(Double)
    # Spearman rank correlation of weekly report counts vs weekly visit counts
    correlation_score: Mapped[float | None] = mapped_column(Double)
    status: Mapped[LinkageStatus] = mapped_column(
        enum_column(LinkageStatus, "linkage_status"), nullable=False, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # The exact parameters (radius, windows, thresholds) used to compute this row
    params_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    evidence: Mapped[list["HealthLinkageEvidence"]] = relationship(
        back_populates="linkage", cascade="all, delete-orphan", passive_deletes=True
    )


class HealthLinkageEvidence(Base):
    __tablename__ = "health_linkage_evidence"

    linkage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("health_linkages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinic_visit_summaries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_window: Mapped[EvidenceWindow] = mapped_column(
        enum_column(EvidenceWindow, "evidence_window"), nullable=False
    )

    linkage: Mapped[HealthLinkage] = relationship(back_populates="evidence")

