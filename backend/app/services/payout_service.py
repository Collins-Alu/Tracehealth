"""
Incentive payouts (FR 5.1), Sprint 2 part.

When a report is VERIFIED, a Payout row is recorded with status PENDING in the
same transaction as the decision. Sprint 4 adds the provider adapters
(M-Pesa Daraja sandbox and the mock) that send PENDING payouts and set
SUCCESS or FAILED. Nothing in Sprint 2 moves money or pretends to.

Safeguards (also enforced by the database):
  * at most one payout per report (UNIQUE report_id)
  * only for a final VERIFIED decision, never for REJECTED or FLAGGED
  * only to the reporter, and only if they consented to payouts (D4)
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Payout, PollutionReport, Reporter, Verification
from app.models.enums import PayoutProvider, PayoutStatus, VerificationDecision
from app.services import setting_service


@dataclass
class PayoutRequest:
    payout: Payout | None
    skipped_reason: str | None = None  # e.g. "no_payout_consent"


def request_incentive(
    db: Session, report: PollutionReport, verification: Verification
) -> PayoutRequest:
    if verification.decision != VerificationDecision.VERIFIED or not verification.is_final:
        return PayoutRequest(None, "not_verified")

    existing = db.scalar(select(Payout).where(Payout.report_id == report.id))
    if existing is not None:
        return PayoutRequest(existing)

    reporter = db.get(Reporter, report.reporter_id)
    if reporter is None or not reporter.payout_phone or reporter.payout_consent_at is None:
        return PayoutRequest(None, "no_payout_consent")

    amount = Decimal(str(setting_service.get(db, "payout.amount", 50)))
    currency = str(setting_service.get(db, "payout.currency", "KES"))
    payout = Payout(
        id=uuid.uuid4(),
        report_id=report.id,
        verification_id=verification.id,
        reporter_id=report.reporter_id,
        amount=amount,
        currency=currency,
        phone_number=reporter.payout_phone,
        provider=PayoutProvider(get_settings().PAYOUT_PROVIDER),
        status=PayoutStatus.PENDING,
    )
    try:
        with db.begin_nested():
            db.add(payout)
            db.flush()
    except IntegrityError:
        # Another request recorded the payout first; keep that one
        return PayoutRequest(db.scalar(select(Payout).where(Payout.report_id == report.id)))
    return PayoutRequest(payout)
