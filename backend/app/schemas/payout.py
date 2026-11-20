"""Shapes for payout monitoring (administrators)."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PayoutProvider, PayoutStatus, PollutionCategory


def mask_phone(phone: str) -> str:
    """+254712345678 -> +2547****678: enough to recognise, not to misuse."""
    return phone[:5] + "*" * max(len(phone) - 8, 0) + phone[-3:] if len(phone) > 8 else "****"


class PayoutOut(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    report_category: PollutionCategory
    reporter_name: str
    phone_masked: str
    amount: Decimal
    currency: str
    provider: PayoutProvider
    is_test_payment: bool = Field(description="MOCK provider: no real money moved")
    status: PayoutStatus
    transaction_ref: str | None
    provider_request_id: str | None
    failure_reason: str | None
    attempts: int
    created_at: datetime
    last_attempt_at: datetime | None
    paid_at: datetime | None


class PayoutPage(BaseModel):
    items: list[PayoutOut]
    total: int
    limit: int
    offset: int


class TriggerRequest(BaseModel):
    report_id: uuid.UUID | None = Field(
        None,
        description="Request (if missing) and send the payout for this verified report. "
        "Omit to send every PENDING payout that is due.",
    )


class ProcessResult(BaseModel):
    processed: int
    completed: int
    accepted: int
    failed: int
    retry_later: int
    not_configured: int
