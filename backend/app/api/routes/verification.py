"""
Verification endpoints (Module 4; UML B.4).

GET  /zones                       zones for the filter chips
GET  /reports                     search reports (verifiers, admins; agency staff: VERIFIED only)
GET  /reports/pending             PENDING reports to review, oldest first
GET  /reports/flagged             FLAGGED reports awaiting a second verifier
GET  /reports/{id}/nearby         reports close in place and time (duplicate check)
POST /reports/{id}/verify         confirm
POST /reports/{id}/reject         reject, with a reason
POST /reports/{id}/flag           flag as a possible duplicate, with a reason

This router is registered BEFORE the general /reports router so that
"/reports/pending" is not mistaken for "/reports/{id}".
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import Role, get_current_user, require_roles
from app.core.notifications import get_notification_dispatcher
from app.db.session import get_db
from app.models import User
from app.models.enums import PollutionCategory, ReportStatus, VerificationDecision
from app.schemas.report import (
    DecisionResult,
    NearbyReport,
    ReasonRequest,
    ReportPage,
    VerificationOut,
    VerifyRequest,
    ZoneOut,
)
from app.services import report_service, verification_service, zone_service
from app.services.notification_dispatch import NotificationDispatcher
from app.services.verification_service import VerificationError

router = APIRouter(tags=["Verification"])

verifier_only = require_roles(Role.VERIFIER)
reviewers = require_roles(Role.VERIFIER, Role.ADMINISTRATOR)
report_readers = require_roles(Role.VERIFIER, Role.ADMINISTRATOR, Role.AGENCY_STAFF)

ZONE_HELP = (
    "Omit for your own zone plus unassigned reports; ALL for every zone; "
    "UNASSIGNED for reports outside every zone; or a zone code."
)


def _raise(exc: VerificationError):
    raise HTTPException(exc.status_code, exc.message) from None


@router.get("/zones", response_model=list[ZoneOut], summary="Active verifier zones")
def list_zones(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ZoneOut]:
    return [ZoneOut.model_validate(z) for z in zone_service.list_active_zones(db)]


@router.get("/reports", response_model=ReportPage, summary="Search reports")
def search_reports(
    status: ReportStatus | None = None,
    zone: str | None = Query(None, description=ZONE_HELP),
    category: PollutionCategory | None = None,
    date_from: datetime | None = Query(None, description="captured_at from (ISO 8601)"),
    date_to: datetime | None = Query(None, description="captured_at to (ISO 8601)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(report_readers),
    db: Session = Depends(get_db),
) -> ReportPage:
    return verification_service.list_reports(
        db,
        user,
        status=status,
        zone=zone,
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/reports/pending", response_model=ReportPage, summary="Reports waiting for review")
def pending_reports(
    zone: str | None = Query(None, description=ZONE_HELP),
    category: PollutionCategory | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(verifier_only),
    db: Session = Depends(get_db),
) -> ReportPage:
    return verification_service.pending_queue(db, user, zone, category, limit, offset)


@router.get(
    "/reports/flagged",
    response_model=ReportPage,
    summary="Flagged reports awaiting a final decision",
)
def flagged_reports(
    zone: str | None = Query(None, description=ZONE_HELP),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(reviewers),
    db: Session = Depends(get_db),
) -> ReportPage:
    return verification_service.flagged_queue(db, user, zone, limit, offset)


@router.get(
    "/reports/{report_id}/nearby",
    response_model=list[NearbyReport],
    summary="Reports close in place and time (possible duplicates)",
)
def nearby(
    report_id: uuid.UUID,
    radius_m: int = Query(250, ge=10, le=2000),
    days: int = Query(7, ge=1, le=30),
    user: User = Depends(reviewers),
    db: Session = Depends(get_db),
) -> list[NearbyReport]:
    try:
        return verification_service.nearby_reports(db, user, report_id, radius_m, days)
    except VerificationError as exc:
        _raise(exc)


def _decide(
    db: Session,
    user: User,
    report_id: uuid.UUID,
    decision: VerificationDecision,
    reason: str | None,
    background: BackgroundTasks,
    dispatcher: NotificationDispatcher,
) -> DecisionResult:
    try:
        outcome = verification_service.decide(db, user, report_id, decision, reason)
    except VerificationError as exc:
        _raise(exc)
    background.add_task(dispatcher.dispatch, outcome.delivery_ids)
    return DecisionResult(
        report=report_service.report_out(db, user, outcome.report),
        verification=VerificationOut.model_validate(outcome.verification),
        payout_requested=outcome.payout is not None,
        payout_skipped_reason=outcome.payout_skipped_reason,
    )


@router.post(
    "/reports/{report_id}/verify", response_model=DecisionResult, summary="Confirm a report"
)
def verify_report(
    report_id: uuid.UUID,
    background: BackgroundTasks,
    body: VerifyRequest | None = None,
    user: User = Depends(verifier_only),
    db: Session = Depends(get_db),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> DecisionResult:
    note = body.note if body else None
    return _decide(db, user, report_id, VerificationDecision.VERIFIED, note, background, dispatcher)


@router.post(
    "/reports/{report_id}/reject", response_model=DecisionResult, summary="Reject a report"
)
def reject_report(
    report_id: uuid.UUID,
    body: ReasonRequest,
    background: BackgroundTasks,
    user: User = Depends(verifier_only),
    db: Session = Depends(get_db),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> DecisionResult:
    return _decide(
        db, user, report_id, VerificationDecision.REJECTED, body.reason, background, dispatcher
    )


@router.post(
    "/reports/{report_id}/flag",
    response_model=DecisionResult,
    summary="Flag a report (e.g. possible duplicate) for a second review",
)
def flag_report(
    report_id: uuid.UUID,
    body: ReasonRequest,
    background: BackgroundTasks,
    user: User = Depends(verifier_only),
    db: Session = Depends(get_db),
    dispatcher: NotificationDispatcher = Depends(get_notification_dispatcher),
) -> DecisionResult:
    return _decide(
        db, user, report_id, VerificationDecision.FLAGGED, body.reason, background, dispatcher
    )
