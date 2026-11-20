"""
Pollution report business logic (FR 1.1, FR 1.2; UML B.3).

Submitting is IDEMPOTENT. The phone generates `client_report_id` when the
report is created, before it ever goes online. If the same report arrives
twice (a retry after a dropped connection, or the offline queue re-sending),
the first copy is returned and nothing new is stored. The UNIQUE constraint on
client_report_id guarantees this even when two copies arrive at the same time.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import Role
from app.models import Payout, PollutionReport, User, Verification
from app.models.enums import PayoutProvider, ReportStatus, SyncStatus, VerificationDecision
from app.schemas.report import PayoutSummary, ReportFields, ReportOut, ReportPage
from app.services import audit_service, notification_service, photo_storage, zone_service

# Phones' clocks drift; allow a little "future" before calling it an error
CLOCK_SKEW = timedelta(minutes=10)


class ReportError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class SubmitOutcome:
    report: PollutionReport
    created: bool
    # Push notifications to send after the response (see notification_dispatch)
    delivery_ids: list[uuid.UUID] = field(default_factory=list)


def _check_timestamp(captured_at: datetime) -> None:
    now = datetime.now(UTC)
    if captured_at > now + CLOCK_SKEW:
        raise ReportError(
            "The report time is in the future. Please check the date and time on your phone."
        )
    max_age = get_settings().REPORT_MAX_AGE_DAYS
    if captured_at < now - timedelta(days=max_age):
        raise ReportError(f"This report is older than {max_age} days and can no longer be sent.")


def _existing(db: Session, client_report_id: uuid.UUID) -> PollutionReport | None:
    return db.scalar(
        select(PollutionReport).where(PollutionReport.client_report_id == client_report_id)
    )


def _same_owner_or_conflict(existing: PollutionReport, reporter: User) -> SubmitOutcome:
    if existing.reporter_id != reporter.id:
        # Practically impossible with random UUIDs; refuse rather than leak data
        raise ReportError("This report id is already in use. Please create the report again.", 409)
    return SubmitOutcome(report=existing, created=False)


def submit_report(
    db: Session,
    reporter: User,
    client_report_id: uuid.UUID,
    fields: ReportFields,
    photo_bytes: bytes,
    *,
    via_sync: bool,
) -> SubmitOutcome:
    # 1. Already received? Answer immediately without re-processing the photo.
    existing = _existing(db, client_report_id)
    if existing is not None:
        return _same_owner_or_conflict(existing, reporter)

    # 2. Validate (B.3 step 4: required fields, coordinates, timestamps, role)
    _check_timestamp(fields.captured_at)
    try:
        jpeg = photo_storage.process_photo(photo_bytes)
    except photo_storage.PhotoError as exc:
        raise ReportError(str(exc)) from None

    sync_status = (
        SyncStatus.SYNCED_FROM_OFFLINE
        if via_sync and fields.created_offline
        else SyncStatus.SUBMITTED_ONLINE
    )

    # 3. Store photo, then the report row (B.3 step 5: INSERT ... PENDING)
    key = photo_storage.save_photo(jpeg)
    report = PollutionReport(
        client_report_id=client_report_id,
        reporter_id=reporter.id,
        photo_url=key,
        latitude=fields.latitude,
        longitude=fields.longitude,
        category=fields.category,
        description=fields.description,
        zone_code=zone_service.zone_for_point(db, fields.latitude, fields.longitude),
        captured_at=fields.captured_at,
        sync_status=sync_status,
    )
    try:
        with db.begin_nested():
            db.add(report)
            db.flush()
    except IntegrityError:
        # The same report arrived twice at the same moment; keep the first copy
        photo_storage.delete_photo(key)
        existing = _existing(db, client_report_id)
        if existing is None:
            raise
        return _same_owner_or_conflict(existing, reporter)

    # 4. Notify verifiers (B.3 step 6) and audit, in the same transaction
    notified = notification_service.notify_verifiers_of_new_report(db, report)
    audit_service.record(
        db,
        actor_id=reporter.id,
        action="report.submitted",
        entity_type="pollution_report",
        entity_id=report.id,
        details={
            "sync_status": sync_status.value,
            "zone_code": report.zone_code,
            "verifiers_notified": notified.recipients,
        },
    )
    try:
        db.commit()
    except Exception:
        photo_storage.delete_photo(key)
        raise
    db.refresh(report)
    return SubmitOutcome(report=report, created=True, delivery_ids=notified.delivery_ids)


# --------------------------------------------------------------------------
# Reading reports
# --------------------------------------------------------------------------
def can_view(user: User, report: PollutionReport) -> bool:
    roles = set(user.roles)
    if report.reporter_id == user.id:
        return True
    if roles & {Role.VERIFIER.value, Role.ADMINISTRATOR.value}:
        return True
    if Role.AGENCY_STAFF.value in roles:
        return report.status == ReportStatus.VERIFIED  # SRS 5.5: verified only
    return False


def get_visible_report(db: Session, user: User, report_id: uuid.UUID) -> PollutionReport:
    report = db.get(PollutionReport, report_id)
    # Same answer for "doesn't exist" and "not yours", so ids can't be probed
    if report is None or not can_view(user, report):
        raise ReportError("Report not found.", 404)
    return report


def _payouts_for(db: Session, report_ids: list[uuid.UUID]) -> dict[uuid.UUID, Payout]:
    if not report_ids:
        return {}
    rows = db.scalars(select(Payout).where(Payout.report_id.in_(report_ids)))
    return {p.report_id: p for p in rows}


def _decision_reasons(db: Session, report_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not report_ids:
        return {}
    rows = db.execute(
        select(Verification.report_id, Verification.reason, Verification.verified_at)
        .where(Verification.report_id.in_(report_ids), Verification.reason.is_not(None))
        .order_by(Verification.verified_at)
    ).all()
    return {report_id: reason for report_id, reason, _ in rows}  # latest wins


def _flaggers(db: Session, report_ids: list[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
    """Who flagged each report (the latest flag)."""
    if not report_ids:
        return {}
    rows = db.execute(
        select(Verification.report_id, Verification.verifier_id)
        .where(
            Verification.report_id.in_(report_ids),
            Verification.decision == VerificationDecision.FLAGGED,
        )
        .order_by(Verification.verified_at)
    ).all()
    return {report_id: verifier_id for report_id, verifier_id in rows}


def review_status(
    viewer: User, report: PollutionReport, flagged_by: uuid.UUID | None
) -> tuple[bool, str | None]:
    """(can_decide, reason_if_not) for this viewer. Mirrors verification_service rules."""
    if Role.VERIFIER.value not in viewer.roles:
        return False, None
    if report.reporter_id == viewer.id:
        return False, "OWN_REPORT"
    if report.status in (ReportStatus.VERIFIED, ReportStatus.REJECTED):
        return False, "ALREADY_DECIDED"
    if report.status == ReportStatus.FLAGGED and flagged_by == viewer.id:
        return False, "FLAGGED_BY_YOU"
    return True, None


def to_out(
    report: PollutionReport,
    viewer: User,
    payout: Payout | None = None,
    reason: str | None = None,
    flagged_by: uuid.UUID | None = None,
) -> ReportOut:
    is_owner = report.reporter_id == viewer.id
    privileged = bool({Role.VERIFIER.value, Role.ADMINISTRATOR.value} & set(viewer.roles))
    show_payout = payout is not None and (is_owner or Role.ADMINISTRATOR.value in viewer.roles)
    out = ReportOut.model_validate(report)
    out.photo_url = f"/reports/{report.id}/photo"
    out.decision_reason = (
        reason
        if (is_owner or privileged)
        and report.status in (ReportStatus.REJECTED, ReportStatus.FLAGGED)
        else None
    )
    out.payout = (
        PayoutSummary(
            status=payout.status,
            amount=payout.amount,
            currency=payout.currency,
            provider=payout.provider,
            is_test_payment=payout.provider == PayoutProvider.MOCK,
            paid_at=payout.paid_at,
        )
        if show_payout
        else None
    )
    out.can_decide, out.cannot_decide_reason = review_status(viewer, report, flagged_by)
    return out


def build_outs(db: Session, viewer: User, reports: list[PollutionReport]) -> list[ReportOut]:
    """Convert many reports with three batched lookups instead of three per report."""
    ids = [r.id for r in reports]
    payouts = _payouts_for(db, ids)
    reasons = _decision_reasons(db, ids)
    flaggers = _flaggers(db, ids)
    return [
        to_out(r, viewer, payouts.get(r.id), reasons.get(r.id), flaggers.get(r.id)) for r in reports
    ]


def report_out(db: Session, viewer: User, report: PollutionReport) -> ReportOut:
    return build_outs(db, viewer, [report])[0]


def list_my_reports(
    db: Session, reporter: User, status: ReportStatus | None, limit: int, offset: int
) -> ReportPage:
    condition = PollutionReport.reporter_id == reporter.id
    if status is not None:
        condition = condition & (PollutionReport.status == status)
    total = db.scalar(select(func.count()).select_from(PollutionReport).where(condition))
    reports = db.scalars(
        select(PollutionReport)
        .where(condition)
        .order_by(PollutionReport.captured_at.desc(), PollutionReport.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return ReportPage(
        items=build_outs(db, reporter, list(reports)),
        total=total,
        limit=limit,
        offset=offset,
    )
