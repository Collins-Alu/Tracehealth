"""
Verification (UML B.2a): a decision a verifier made about one report.

A report may receive a FLAGGED entry (never final) followed later by exactly
one final decision (VERIFIED or REJECTED). The partial unique index
`ux_verifications_one_final_per_report` enforces "at most one final
decision", matching the 1-to-0..1 multiplicity in the class diagram.
A database trigger (see the initial migration) rejects any verification made
by the report's own reporter.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import VerificationDecision
from app.models.mixins import UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.models.report import PollutionReport
    from app.models.user import Verifier


class Verification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "verifications"
    __table_args__ = (
        CheckConstraint(
            "decision = 'VERIFIED' OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)",
            name="reason_required_unless_verified",
        ),
        CheckConstraint("decision <> 'FLAGGED' OR is_final = false", name="flag_never_final"),
        CheckConstraint("decision = 'FLAGGED' OR is_final = true", name="decision_is_final"),
        Index(
            "ux_verifications_one_final_per_report",
            "report_id",
            unique=True,
            postgresql_where=text("is_final"),
        ),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pollution_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verifier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verifiers.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[VerificationDecision] = mapped_column(
        enum_column(VerificationDecision, "verification_decision"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report: Mapped["PollutionReport"] = relationship(back_populates="verifications")
    verifier: Mapped["Verifier"] = relationship()

