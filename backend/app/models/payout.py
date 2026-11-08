"""
Payout (UML B.2a): the incentive paid for a verified report.

UNIQUE(report_id) makes a second payout for the same report impossible, even
if two requests race each other. A trigger (initial migration) also checks
that the linked verification is a final VERIFIED decision for the same report,
so a rejected report can never be paid.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PayoutProvider, PayoutStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, enum_column


class Payout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payouts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_code"),
        CheckConstraint(
            "status <> 'SUCCESS' OR (transaction_ref IS NOT NULL AND paid_at IS NOT NULL)",
            name="success_requires_reference",
        ),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pollution_reports.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verifications.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reporters.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="KES", server_default=text("'KES'")
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[PayoutProvider] = mapped_column(
        enum_column(PayoutProvider, "payout_provider"), nullable=False
    )
    # Identifier the provider gives when it accepts the request (e.g. M-Pesa ConversationID)
    provider_request_id: Mapped[str | None] = mapped_column(String(100))
    # Final receipt / transaction reference once the money has moved
    transaction_ref: Mapped[str | None] = mapped_column(String(100), unique=True)
    status: Mapped[PayoutStatus] = mapped_column(
        enum_column(PayoutStatus, "payout_status"),
        nullable=False,
        default=PayoutStatus.PENDING,
        server_default=PayoutStatus.PENDING.value,
        index=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

