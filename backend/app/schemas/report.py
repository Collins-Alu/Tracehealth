"""Request and response shapes for /reports endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    PayoutProvider,
    PayoutStatus,
    PollutionCategory,
    ReportStatus,
    SyncStatus,
)


class ReportFields(BaseModel):
    """The form fields of a report submission (the photo is a separate file part).

    Sent as multipart/form-data because the photo travels in the same request.
    """

    category: PollutionCategory
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    captured_at: datetime = Field(
        description="When the report was made on the phone, ISO 8601 with timezone, "
        "e.g. 2026-11-08T09:30:00Z"
    )
    description: str | None = Field(None, max_length=1000)
    created_offline: bool = Field(
        False, description="True when the phone had no connection when the report was made"
    )

    @field_validator("description")
    @classmethod
    def _clean_description(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None

    @field_validator("captured_at")
    @classmethod
    def _needs_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("captured_at must include a timezone, e.g. 2026-11-08T09:30:00Z")
        return v


class NewReportFields(ReportFields):
    client_report_id: uuid.UUID = Field(
        description="Random UUID generated on the phone when the report is created. "
        "Re-sending the same id never creates a second report."
    )


class PayoutSummary(BaseModel):
    """What a reporter sees about the incentive for one report."""

    model_config = ConfigDict(from_attributes=True)

    status: PayoutStatus
    amount: Decimal
    currency: str
    provider: PayoutProvider
    is_test_payment: bool = Field(description="True for MOCK payouts: no real money moved")
    paid_at: datetime | None


class ReportOut(BaseModel):
    """A report as shown in the apps.

    The reporter's identity is deliberately NOT included (decision D12):
    verifiers and agency staff judge the evidence, not the person.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_report_id: uuid.UUID
    photo_url: str = Field(description="Authenticated download path for the photo")
    latitude: float
    longitude: float
    category: PollutionCategory
    description: str | None
    captured_at: datetime
    received_at: datetime
    status: ReportStatus
    sync_status: SyncStatus
    decision_reason: str | None = Field(
        None, description="Why the report was rejected or flagged, shown to its reporter"
    )
    payout: PayoutSummary | None = None


class ReportPage(BaseModel):
    items: list[ReportOut]
    total: int
    limit: int
    offset: int


class SubmitResult(BaseModel):
    report: ReportOut
    already_received: bool = Field(
        description="True when this exact report (same client_report_id) was received "
        "before; nothing new was stored"
    )
