"""
Report verification (FR 2.1, FR 2.2; UML B.4; SRS 5.5).

Decisions
  VERIFY  PENDING or FLAGGED -> VERIFIED  (final; incentive payout requested)
  REJECT  PENDING or FLAGGED -> REJECTED  (final; reason required; no payout)
  FLAG    PENDING            -> FLAGGED   (not final; reason required; hidden from
                                           the dashboard until a second verifier decides)

Rules, checked here AND enforced again by the database (migration 0001):
  * a reporter can never decide on their own report             -> 403
  * VERIFIED / REJECTED are final; one final decision per report -> 409
  * the verifier who flagged a report cannot make its final
    decision; a different verifier must (decision D7)           -> 403

Two verifiers acting on the same report at the same moment: the report row is
locked (SELECT ... FOR UPDATE), so the second one waits, then sees the first
decision and gets a clear 409 instead of a database error.

Everything for one decision (verification row, status change, payout request,
audit entry, notifications) is committed in ONE transaction.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Role
from app.models import Payout, PollutionReport, User, Verification
from app.models.enums import (
    PollutionCategory,
    ReportStatus,
    VerificationDecision,
)
from app.schemas.report import NearbyReport, ReportPage
from app.services import audit_service, notification_service, payout_service, report_service


class VerificationError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


OWN_REPORT = "You cannot review a report that you submitted."
FLAGGED_BY_YOU = "You flagged this report, so a different verifier must make the final decision."
ALREADY_FINAL = "This report already has a final decision ({status})."
ALREADY_FLAGGED = "This report is already under review."

EVENTS = {
    VerificationDecision.VERIFIED: "report.verified",
    VerificationDecision.REJECTED: "report.rejected",
    VerificationDecision.FLAGGED: "report.flagged",
}


@dataclass
class DecisionOutcome:
    report: PollutionReport
    verification: Verification
    payout: Payout | None
    payout_skipped_reason: str | None
    delivery_ids: list[uuid.UUID] = field(default_factory=list)


def _latest_flagger(db: Session, report_id: uuid.UUID) -> uuid.UUID | None:
    return db.scalar(
        select(Verification.verifier_id)
        .where(
            Verification.report_id == report_id,
            Verification.decision == VerificationDecision.FLAGGED,
        )
        .order_by(Verification.verified_at.desc())
        .limit(1)
    )


def _check(db: Session, verifier: User, report: PollutionReport, decision: VerificationDecision):
    if report.reporter_id == verifier.id:
        raise VerificationError(OWN_REPORT, 403)
    if report.status in (ReportStatus.VERIFIED, ReportStatus.REJECTED):
        raise VerificationError(ALREADY_FINAL.format(status=report.status.value), 409)
    if decision == VerificationDecision.FLAGGED:
        if report.status == ReportStatus.FLAGGED:
            raise VerificationError(ALREADY_FLAGGED, 409)
        return
    if report.status == ReportStatus.FLAGGED and _latest_flagger(db, report.id) == verifier.id:
        raise VerificationError(FLAGGED_BY_YOU, 403)


def decide(
    db: Session,
    verifier: User,
    report_id: uuid.UUID,
    decision: VerificationDecision,
    reason: str | None,
) -> DecisionOutcome:
    # Lock the report so concurrent decisions are handled one after another
    report = db.scalar(
        select(PollutionReport).where(PollutionReport.id == report_id).with_for_update()
    )
    if report is None:
        raise VerificationError("Report not found.", 404)
    previous_status = report.status
    _check(db, verifier, report, decision)

    verification = Verification(
        id=uuid.uuid4(),
        report_id=report.id,
        verifier_id=verifier.id,
        decision=decision,
        reason=reason,
        is_final=decision != VerificationDecision.FLAGGED,
    )
    try:
        with db.begin_nested():
            db.add(verification)
            db.flush()  # the database trigger sets the report status here
    except IntegrityError as exc:
        db.rollback()
        # Only reachable if a rule above was bypassed; the database caught it
        if "own report" in str(exc.orig) or "cannot verify their own" in str(exc.orig):
            raise VerificationError(OWN_REPORT, 403) from None
        raise VerificationError("This report was just decided by someone else.", 409) from None
    db.refresh(report)

    payout_request = payout_service.PayoutRequest(None, None)
    if decision == VerificationDecision.VERIFIED:
        payout_request = payout_service.request_incentive(db, report, verification)

    audit_service.record(
        db,
        actor_id=verifier.id,
        action=EVENTS[decision],
        entity_type="pollution_report",
        entity_id=report.id,
        details={
            "verification_id": str(verification.id),
            "decision": decision.value,
            "reason": reason,
            "previous_status": previous_status.value,
            "new_status": report.status.value,
            "payout_id": str(payout_request.payout.id) if payout_request.payout else None,
            "payout_skipped_reason": payout_request.skipped_reason,
        },
    )
    notified = notification_service.notify_reporter_of_decision(
        db, report, EVENTS[decision], reason=reason, payout=payout_request.payout
    )
    db.commit()
    db.refresh(report)
    return DecisionOutcome(
        report=report,
        verification=verification,
        payout=payout_request.payout,
        payout_skipped_reason=payout_request.skipped_reason,
        delivery_ids=notified.delivery_ids,
    )


# --------------------------------------------------------------------------
# Review queues and report lists
# --------------------------------------------------------------------------
ZONE_ALL = "ALL"
ZONE_UNASSIGNED = "UNASSIGNED"


def _zone_condition(viewer: User, zone: str | None):
    """
    zone omitted   -> the verifier's own zone plus unassigned reports
                      (everything if they have no zone)
    zone=ALL       -> every zone
    zone=UNASSIGNED-> reports outside every zone
    zone=<code>    -> that zone only
    """
    if zone is None:
        own = viewer.verifier_profile.assigned_zone if viewer.verifier_profile else None
        if own is None:
            return None
        return or_(PollutionReport.zone_code == own, PollutionReport.zone_code.is_(None))
    if zone.upper() == ZONE_ALL:
        return None
    if zone.upper() == ZONE_UNASSIGNED:
        return PollutionReport.zone_code.is_(None)
    return PollutionReport.zone_code == zone


def _page(db: Session, viewer: User, conditions: list, order, limit: int, offset: int):
    total = db.scalar(select(func.count()).select_from(PollutionReport).where(*conditions))
    reports = db.scalars(
        select(PollutionReport).where(*conditions).order_by(*order).limit(limit).offset(offset)
    ).all()
    return ReportPage(
        items=report_service.build_outs(db, viewer, list(reports)),
        total=total,
        limit=limit,
        offset=offset,
    )


def pending_queue(
    db: Session,
    viewer: User,
    zone: str | None,
    category: PollutionCategory | None,
    limit: int,
    offset: int,
) -> ReportPage:
    """PENDING reports for review, oldest first. The viewer's own reports are left
    out because they could not decide on them anyway."""
    conditions = [
        PollutionReport.status == ReportStatus.PENDING,
        PollutionReport.reporter_id != viewer.id,
    ]
    zone_cond = _zone_condition(viewer, zone)
    if zone_cond is not None:
        conditions.append(zone_cond)
    if category is not None:
        conditions.append(PollutionReport.category == category)
    order = (PollutionReport.captured_at.asc(), PollutionReport.id)
    return _page(db, viewer, conditions, order, limit, offset)


def flagged_queue(
    db: Session, viewer: User, zone: str | None, limit: int, offset: int
) -> ReportPage:
    """FLAGGED reports awaiting a final decision by a second verifier (D7).
    Administrators see every zone."""
    conditions = [PollutionReport.status == ReportStatus.FLAGGED]
    if Role.VERIFIER.value in viewer.roles:
        conditions.append(PollutionReport.reporter_id != viewer.id)
        zone_cond = _zone_condition(viewer, zone)
        if zone_cond is not None:
            conditions.append(zone_cond)
    elif zone is not None and zone.upper() != ZONE_ALL:
        conditions.append(_zone_condition(viewer, zone))
    order = (PollutionReport.updated_at.asc(), PollutionReport.id)
    return _page(db, viewer, conditions, order, limit, offset)


def list_reports(
    db: Session,
    viewer: User,
    *,
    status: ReportStatus | None,
    zone: str | None,
    category: PollutionCategory | None,
    date_from,
    date_to,
    limit: int,
    offset: int,
) -> ReportPage:
    """General report search for verifiers, administrators and agency staff.
    Agency staff only ever see VERIFIED reports (SRS 5.5)."""
    roles = set(viewer.roles)
    conditions = []
    if not roles & {Role.VERIFIER.value, Role.ADMINISTRATOR.value}:
        conditions.append(PollutionReport.status == ReportStatus.VERIFIED)
    elif status is not None:
        conditions.append(PollutionReport.status == status)
    if zone is not None:
        zone_cond = _zone_condition(viewer, zone)
        if zone_cond is not None:
            conditions.append(zone_cond)
    if category is not None:
        conditions.append(PollutionReport.category == category)
    if date_from is not None:
        conditions.append(PollutionReport.captured_at >= date_from)
    if date_to is not None:
        conditions.append(PollutionReport.captured_at <= date_to)
    order = (PollutionReport.captured_at.desc(), PollutionReport.id)
    return _page(db, viewer, conditions, order, limit, offset)


_NEARBY = text(
    """
    SELECT other.id, ST_Distance(other.location, this.location) AS distance_m
      FROM pollution_reports this
      JOIN pollution_reports other
        ON other.id <> this.id
       AND ST_DWithin(other.location, this.location, :radius_m)
       AND other.captured_at BETWEEN this.captured_at - make_interval(days => :days)
                                 AND this.captured_at + make_interval(days => :days)
     WHERE this.id = :report_id
     ORDER BY distance_m, other.captured_at
     LIMIT :limit
    """
)


def nearby_reports(
    db: Session, viewer: User, report_id: uuid.UUID, radius_m: int, days: int, limit: int = 10
) -> list[NearbyReport]:
    """Other reports close in place and time: helps verifiers spot duplicates."""
    if db.get(PollutionReport, report_id) is None:
        raise VerificationError("Report not found.", 404)
    rows = db.execute(
        _NEARBY, {"report_id": report_id, "radius_m": radius_m, "days": days, "limit": limit}
    ).all()
    if not rows:
        return []
    by_id = {
        r.id: r
        for r in db.scalars(
            select(PollutionReport).where(PollutionReport.id.in_([row.id for row in rows]))
        )
    }
    outs = {o.id: o for o in report_service.build_outs(db, viewer, list(by_id.values()))}
    return [NearbyReport(report=outs[row.id], distance_m=round(row.distance_m, 1)) for row in rows]
