"""
Incentive payouts (FR 5.1; UML B.4 steps 7-9).

1. When a report is VERIFIED, request_incentive() records a PENDING payout in
   the same transaction as the decision.
2. process_payouts() sends it with the adapter for its provider:
     MOCK          -> SUCCESS at once with a MOCK-TXN reference (no real money)
     MPESA_DARAJA  -> M-Pesa accepts the request; the payout stays PENDING
                      until apply_mpesa_result() records the callback.
3. The reporter is notified when the payout succeeds or fails.
4. Background jobs retry requests that never reached the provider, and mark
   accepted requests with no result after PAYOUT_RESULT_TIMEOUT_HOURS as FAILED.
   An administrator can retry a FAILED payout after checking the cause.

Safeguards (also enforced by the database):
  * at most one payout per report (UNIQUE report_id)
  * only for a final VERIFIED decision, never for REJECTED or FLAGGED
  * only to the reporter, and only if they consented to payouts (D4)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.payments import Outcome, PaymentAdapter, PaymentRequest
from app.models import Payout, PollutionReport, Reporter, Verification
from app.models.enums import PayoutProvider, PayoutStatus, VerificationDecision
from app.services import audit_service, notification_service, setting_service

log = logging.getLogger("tracehealth.payouts")


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


# --------------------------------------------------------------------------
# Sending payouts (Sprint 4)
# --------------------------------------------------------------------------
# Wait before automatic retry number n (after a RETRY outcome)
RETRY_BACKOFF = [
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
]


@dataclass
class ProcessSummary:
    processed: int = 0
    completed: int = 0
    accepted: int = 0
    failed: int = 0
    retry_later: int = 0
    not_configured: int = 0
    delivery_ids: list[uuid.UUID] = field(default_factory=list)


def _backoff(attempts: int) -> timedelta:
    return RETRY_BACKOFF[min(max(attempts, 1), len(RETRY_BACKOFF)) - 1]


def _eligible(db: Session, now: datetime, payout_ids: list[uuid.UUID] | None, limit: int):
    query = select(Payout).where(
        Payout.status == PayoutStatus.PENDING, Payout.provider_request_id.is_(None)
    )
    if payout_ids is not None:
        query = query.where(Payout.id.in_(payout_ids))  # explicit request: no backoff/limit
    else:
        query = query.where(Payout.attempts < get_settings().PAYOUT_MAX_ATTEMPTS)
    # SKIP LOCKED: two workers never send the same payout at the same time
    rows = db.scalars(
        query.order_by(Payout.created_at).limit(limit).with_for_update(skip_locked=True)
    ).all()
    if payout_ids is not None:
        return rows
    return [
        p
        for p in rows
        if p.last_attempt_at is None or p.last_attempt_at + _backoff(p.attempts) <= now
    ]


def _finish(
    db: Session,
    payout: Payout,
    *,
    status: PayoutStatus,
    ref: str | None,
    reason: str | None,
    summary: ProcessSummary,
) -> None:
    now = datetime.now(UTC)
    payout.status = status
    if status == PayoutStatus.SUCCESS:
        payout.transaction_ref = ref
        payout.paid_at = now
        payout.failure_reason = None
        event, action = "payout.sent", "payout.paid"
    else:
        payout.failure_reason = (reason or "failed")[:500]
        event, action = "payout.failed", "payout.failed"
    db.flush()
    audit_service.record(
        db,
        actor_id=None,  # the system
        action=action,
        entity_type="payout",
        entity_id=payout.id,
        details={
            "provider": payout.provider.value,
            "transaction_ref": ref,
            "reason": reason,
            "attempts": payout.attempts,
        },
    )
    notified = notification_service.notify_reporter_of_payout(db, payout, event)
    summary.delivery_ids += notified.delivery_ids


def process_payouts(
    db: Session,
    adapters: dict[PayoutProvider, PaymentAdapter],
    payout_ids: list[uuid.UUID] | None = None,
    limit: int = 20,
) -> ProcessSummary:
    """Send PENDING payouts to their provider. Commits after each payout."""
    summary = ProcessSummary()
    now = datetime.now(UTC)
    for payout in _eligible(db, now, payout_ids, limit):
        adapter = adapters.get(payout.provider)
        if adapter is None:
            payout.failure_reason = f"{payout.provider.value} is not configured on this server."
            summary.not_configured += 1
            db.commit()
            continue
        summary.processed += 1
        payout.attempts += 1
        payout.last_attempt_at = now
        result = adapter.send(
            PaymentRequest(
                payout_id=payout.id,
                attempt=payout.attempts,
                phone_number=payout.phone_number,
                amount=payout.amount,
                currency=payout.currency,
                remarks="TraceHealth reward for a verified pollution report",
            )
        )
        if result.provider_request_id:
            payout.provider_request_id = result.provider_request_id[:100]
        if result.outcome == Outcome.COMPLETED:
            _finish(
                db,
                payout,
                status=PayoutStatus.SUCCESS,
                ref=result.transaction_ref,
                reason=None,
                summary=summary,
            )
            summary.completed += 1
        elif result.outcome == Outcome.ACCEPTED:
            payout.failure_reason = None
            audit_service.record(
                db,
                actor_id=None,
                action="payout.requested",
                entity_type="payout",
                entity_id=payout.id,
                details={
                    "provider_request_id": payout.provider_request_id,
                    "attempts": payout.attempts,
                },
            )
            summary.accepted += 1
        elif (
            result.outcome == Outcome.RETRY and payout.attempts < get_settings().PAYOUT_MAX_ATTEMPTS
        ):
            payout.failure_reason = result.message
            summary.retry_later += 1
        else:  # FAILED, UNKNOWN, or RETRY with no attempts left
            _finish(
                db,
                payout,
                status=PayoutStatus.FAILED,
                ref=None,
                reason=result.message,
                summary=summary,
            )
            summary.failed += 1
        db.commit()
    return summary


def retry(db: Session, payout: Payout, admin_id: uuid.UUID) -> None:
    """An administrator sends a FAILED payout again (after checking the cause)."""
    payout.status = PayoutStatus.PENDING
    payout.provider_request_id = None
    payout.failure_reason = None
    audit_service.record(
        db,
        actor_id=admin_id,
        action="payout.retry_requested",
        entity_type="payout",
        entity_id=payout.id,
        details={"attempts_so_far": payout.attempts},
    )
    db.commit()


def expire_stale(db: Session) -> ProcessSummary:
    """Accepted M-Pesa requests that never got a result are marked FAILED."""
    summary = ProcessSummary()
    hours = get_settings().PAYOUT_RESULT_TIMEOUT_HOURS
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    stale = db.scalars(
        select(Payout)
        .where(
            Payout.status == PayoutStatus.PENDING,
            Payout.provider_request_id.is_not(None),
            Payout.last_attempt_at < cutoff,
        )
        .with_for_update(skip_locked=True)
    ).all()
    for payout in stale:
        _finish(
            db,
            payout,
            status=PayoutStatus.FAILED,
            ref=None,
            reason=f"No result from M-Pesa after {hours} hours. Check the M-Pesa portal "
            "before retrying, so the reporter is not paid twice.",
            summary=summary,
        )
        summary.failed += 1
    db.commit()
    return summary


def _result_parameter(result: dict, key: str):
    params = (result.get("ResultParameters") or {}).get("ResultParameter") or []
    if isinstance(params, dict):
        params = [params]
    for item in params:
        if item.get("Key") == key:
            return item.get("Value")
    return None


def apply_mpesa_result(db: Session, body: dict, *, timed_out: bool) -> ProcessSummary:
    """Record the result M-Pesa posts to our ResultURL / QueueTimeOutURL.
    Duplicate or unknown callbacks are ignored safely."""
    summary = ProcessSummary()
    result = body.get("Result") or {}
    conversation_id = result.get("ConversationID")
    payout = None
    if conversation_id:
        payout = db.scalar(
            select(Payout).where(Payout.provider_request_id == conversation_id).with_for_update()
        )
    if payout is None and result.get("OriginatorConversationID"):
        prefix = str(result["OriginatorConversationID"]).rsplit("-", 1)[0]
        try:
            payout = db.get(Payout, uuid.UUID(prefix), with_for_update=True)
        except ValueError:
            payout = None
    if payout is None or payout.provider != PayoutProvider.MPESA_DARAJA:
        log.warning("M-Pesa callback for an unknown payout: %s", conversation_id)
        return summary
    if payout.status != PayoutStatus.PENDING:
        return summary  # already handled: M-Pesa may repeat callbacks

    code = result.get("ResultCode")
    if not timed_out and str(code) == "0":
        ref = result.get("TransactionID") or _result_parameter(result, "TransactionReceipt")
        _finish(db, payout, status=PayoutStatus.SUCCESS, ref=str(ref), reason=None, summary=summary)
        summary.completed += 1
    else:
        reason = (
            "M-Pesa timed out the request in its queue."
            if timed_out
            else f"M-Pesa: {result.get('ResultDesc') or 'payment failed'} (code {code})"
        )
        _finish(db, payout, status=PayoutStatus.FAILED, ref=None, reason=reason, summary=summary)
        summary.failed += 1
    db.commit()
    return summary
