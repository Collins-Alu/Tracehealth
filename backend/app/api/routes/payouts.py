"""
Payout endpoints (Module 8; FR 5.1).

GET  /payouts                   payout monitoring (administrators)
GET  /payouts/{id}              one payout (administrators, or the reporter it pays)
POST /payouts/trigger           send due payouts, or the payout for one report
POST /payouts/{id}/retry        send a FAILED payout again
POST /payouts/callbacks/mpesa/result/{token}    M-Pesa result (no login; secret path)
POST /payouts/callbacks/mpesa/timeout/{token}   M-Pesa queue timeout
"""

import hmac
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.background import PayoutProcessor, get_payout_processor
from app.core.config import get_settings
from app.core.deps import Role, get_current_user, require_roles
from app.core.notifications import get_notification_dispatcher
from app.db.session import get_db
from app.models import Payout, PollutionReport, User, Verification
from app.models.enums import PayoutProvider, PayoutStatus, VerificationDecision
from app.schemas.payout import (
    PayoutOut,
    PayoutPage,
    ProcessResult,
    TriggerRequest,
    mask_phone,
)
from app.services import payout_service
from app.services.notification_dispatch import NotificationDispatcher

router = APIRouter(prefix="/payouts", tags=["Payouts"])
admin_only = require_roles(Role.ADMINISTRATOR)


def _out(p: Payout, report: PollutionReport, name: str) -> PayoutOut:
    return PayoutOut(
        id=p.id,
        report_id=p.report_id,
        report_category=report.category,
        reporter_name=name,
        phone_masked=mask_phone(p.phone_number),
        amount=p.amount,
        currency=p.currency,
        provider=p.provider,
        is_test_payment=p.provider == PayoutProvider.MOCK,
        status=p.status,
        transaction_ref=p.transaction_ref,
        provider_request_id=p.provider_request_id,
        failure_reason=p.failure_reason,
        attempts=p.attempts,
        created_at=p.created_at,
        last_attempt_at=p.last_attempt_at,
        paid_at=p.paid_at,
    )


def _base():
    return (
        select(Payout, PollutionReport, User.full_name)
        .join(PollutionReport, PollutionReport.id == Payout.report_id)
        .join(User, User.id == Payout.reporter_id)
    )


@router.get("", response_model=PayoutPage, summary="Payout monitoring")
def list_payouts(
    status: PayoutStatus | None = None,
    provider: PayoutProvider | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> PayoutPage:
    conditions = []
    if status:
        conditions.append(Payout.status == status)
    if provider:
        conditions.append(Payout.provider == provider)
    total = db.scalar(select(func.count()).select_from(Payout).where(*conditions))
    rows = db.execute(
        _base().where(*conditions).order_by(Payout.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return PayoutPage(items=[_out(*r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/{payout_id}", response_model=PayoutOut, summary="One payout")
def get_payout(
    payout_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PayoutOut:
    row = db.execute(_base().where(Payout.id == payout_id)).first()
    if row is None or (
        Role.ADMINISTRATOR.value not in user.roles and row[0].reporter_id != user.id
    ):
        raise HTTPException(404, "Payout not found.")
    return _out(*row)


@router.post("/trigger", response_model=ProcessResult, summary="Send payouts now")
def trigger(
    body: TriggerRequest,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
    processor: PayoutProcessor = Depends(get_payout_processor),
) -> ProcessResult:
    ids = None
    if body.report_id:
        report = db.get(PollutionReport, body.report_id)
        verification = db.scalar(
            select(Verification).where(
                Verification.report_id == body.report_id,
                Verification.decision == VerificationDecision.VERIFIED,
                Verification.is_final.is_(True),
            )
        )
        if report is None or verification is None:
            raise HTTPException(409, "Only verified reports can be paid.")
        request = payout_service.request_incentive(db, report, verification)
        if request.payout is None:
            raise HTTPException(409, "The reporter has not agreed to mobile money payouts.")
        db.commit()
        ids = [request.payout.id]
    summary = processor.process(ids)
    return ProcessResult(**{k: getattr(summary, k) for k in ProcessResult.model_fields})


@router.post("/{payout_id}/retry", response_model=ProcessResult, summary="Retry a failed payout")
def retry_payout(
    payout_id: uuid.UUID,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
    processor: PayoutProcessor = Depends(get_payout_processor),
) -> ProcessResult:
    payout = db.get(Payout, payout_id, with_for_update=True)
    if payout is None:
        raise HTTPException(404, "Payout not found.")
    if payout.status != PayoutStatus.FAILED:
        raise HTTPException(
            409, f"Only FAILED payouts can be retried (this one is {payout.status.value})."
        )
    payout_service.retry(db, payout, admin.id)
    summary = processor.process([payout.id])
    return ProcessResult(**{k: getattr(summary, k) for k in ProcessResult.model_fields})


def _check_token(token: str) -> None:
    expected = get_settings().MPESA_CALLBACK_TOKEN
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(404, "Not found.")


async def _callback(
    request: Request,
    token: str,
    timed_out: bool,
    db: Session,
    background: BackgroundTasks,
    dispatcher: NotificationDispatcher,
) -> dict:
    _check_token(token)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    summary = payout_service.apply_mpesa_result(
        db, body if isinstance(body, dict) else {}, timed_out=timed_out
    )
    background.add_task(dispatcher.dispatch, summary.delivery_ids)
    # M-Pesa only needs to know we received it
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/callbacks/mpesa/result/{token}", include_in_schema=False)
async def mpesa_result(
    token: str,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
):
    return await _callback(request, token, False, db, background, dispatcher)


@router.post("/callbacks/mpesa/timeout/{token}", include_in_schema=False)
async def mpesa_timeout(
    token: str,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
):
    return await _callback(request, token, True, db, background, dispatcher)
