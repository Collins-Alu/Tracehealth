"""The interface every mobile-money adapter implements (FR 5.1)."""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True)
class PaymentRequest:
    payout_id: uuid.UUID
    attempt: int
    phone_number: str  # E.164, e.g. +254712345678
    amount: Decimal
    currency: str
    remarks: str


class Outcome(StrEnum):
    COMPLETED = "COMPLETED"  # money moved; transaction_ref is the receipt
    ACCEPTED = "ACCEPTED"  # provider accepted the request; result arrives by callback
    FAILED = "FAILED"  # provider refused; safe to retry after fixing the cause
    RETRY = "RETRY"  # request never reached the provider (e.g. connection refused)
    UNKNOWN = "UNKNOWN"  # sent, but no clear answer: must NOT be retried automatically


@dataclass
class PaymentResult:
    outcome: Outcome
    transaction_ref: str | None = None
    provider_request_id: str | None = None
    message: str | None = None


class PaymentAdapter(Protocol):
    name: str

    def send(self, request: PaymentRequest) -> PaymentResult: ...
