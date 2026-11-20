"""
Notifications (SRS 3.4; UML B.3 step 6 and B.4 steps 9 and 12).

Every event creates:
  * one IN_APP notification per recipient: the inbox inside the app, always
    available, also with no push token and in Expo Go; and
  * one delivery notification per recipient on PUSH (if they have a device
    registered) or SMS, created PENDING.

The delivery rows are sent after the request finishes by
NotificationDispatcher (notification_dispatch.py), so a slow provider never
delays the person who triggered the event. If push fails for a reporter, the
dispatcher falls back to SMS.

Who is told what:
  * new report      -> verifiers for that zone (in-app + push; no SMS)
  * verified        -> the reporter (in-app + push, SMS fallback)
  * rejected        -> the reporter, with the reason (same channels)
  * flagged         -> the reporter, with the reason (same channels)
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.models import DevicePushToken, Notification, Payout, PollutionReport, User, Verifier
from app.models.enums import Language, NotificationChannel, NotificationStatus

# Event types the dispatcher may fall back to SMS for (reporter-facing only)
SMS_FALLBACK_TYPES = {
    "report.verified",
    "report.rejected",
    "report.flagged",
    "payout.sent",
    "payout.failed",
}

CATEGORY_NAMES = {
    Language.EN: {
        "OPEN_BURNING": "open burning",
        "ILLEGAL_DUMPING": "illegal dumping",
        "BLOCKED_DRAINAGE": "blocked drainage",
        "MEDICAL_WASTE": "medical waste",
        "OTHER": "other pollution",
    },
    Language.SW: {
        "OPEN_BURNING": "uchomaji wa taka",
        "ILLEGAL_DUMPING": "utupaji haramu wa taka",
        "BLOCKED_DRAINAGE": "mfereji ulioziba",
        "MEDICAL_WASTE": "taka za hospitali",
        "OTHER": "uchafuzi mwingine",
    },
}

TEMPLATES = {
    "report.submitted": {
        Language.EN: ("New report to review", "A new {category} report is waiting for review."),
        Language.SW: ("Ripoti mpya ya kukagua", "Ripoti mpya ya {category} inasubiri kukaguliwa."),
    },
    "report.verified": {
        Language.EN: (
            "Report verified",
            "Thank you! Your {category} report was confirmed.{reward}",
        ),
        Language.SW: (
            "Ripoti imethibitishwa",
            "Asante! Ripoti yako ya {category} imethibitishwa.{reward}",
        ),
    },
    "report.rejected": {
        Language.EN: (
            "Report not accepted",
            "Your {category} report was not accepted. Reason: {reason}",
        ),
        Language.SW: (
            "Ripoti haikukubaliwa",
            "Ripoti yako ya {category} haikukubaliwa. Sababu: {reason}",
        ),
    },
    "report.flagged": {
        Language.EN: (
            "Report under review",
            "Your {category} report is being checked again. Reason: {reason}. "
            "We will tell you the result.",
        ),
        Language.SW: (
            "Ripoti inakaguliwa",
            "Ripoti yako ya {category} inakaguliwa tena. Sababu: {reason}. "
            "Tutakujulisha matokeo.",
        ),
    },
}

TEMPLATES["payout.sent"] = {
    Language.EN: (
        "Reward sent",
        "Your reward of {currency} {amount} for your {category} report has been sent. "
        "Reference: {ref}.{test}",
    ),
    Language.SW: (
        "Zawadi imetumwa",
        "Zawadi yako ya {currency} {amount} kwa ripoti yako ya {category} imetumwa. "
        "Kumbukumbu: {ref}.{test}",
    ),
}
TEMPLATES["payout.failed"] = {
    Language.EN: (
        "Reward not sent yet",
        "We could not send your reward of {currency} {amount} for your {category} report. "
        "Our team will check and try again.",
    ),
    Language.SW: (
        "Zawadi bado haijatumwa",
        "Hatukuweza kutuma zawadi yako ya {currency} {amount} kwa ripoti yako ya {category}. "
        "Timu yetu itaangalia na kujaribu tena.",
    ),
}
TEST_PAYMENT_TEXT = {
    Language.EN: " (TEST payment: no real money was sent.)",
    Language.SW: " (Malipo ya MAJARIBIO: hakuna pesa halisi zilizotumwa.)",
}

REWARD_TEXT = {
    Language.EN: " Your reward of {currency} {amount} is being processed.",
    Language.SW: " Zawadi yako ya {currency} {amount} inashughulikiwa.",
}


@dataclass
class NotifyResult:
    recipients: int = 0
    delivery_ids: list[uuid.UUID] = field(default_factory=list)


def _render(event: str, language: Language, report: PollutionReport, **extra) -> tuple[str, str]:
    title, body = TEMPLATES[event][language]
    return title, body.format(category=CATEGORY_NAMES[language][report.category.value], **extra)


def _has_push_token(db: Session, user_id: uuid.UUID) -> bool:
    return bool(db.scalar(select(exists().where(DevicePushToken.user_id == user_id))))


def _create(
    db: Session,
    *,
    user: tuple[uuid.UUID, Language],
    event: str,
    report: PollutionReport,
    allow_sms: bool,
    result: NotifyResult,
    **extra,
) -> None:
    user_id, language = user
    title, body = _render(event, language, report, **extra)
    now = datetime.now(UTC)
    db.add(
        Notification(
            user_id=user_id,
            type=event,
            title=title,
            body=body,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,  # stored = available in the inbox
            related_report_id=report.id,
            sent_at=now,
            # Real clock time, so the inbox order is right even for several
            # notifications created in one transaction (now() would tie)
            created_at=now,
        )
    )
    channel = (
        NotificationChannel.PUSH
        if _has_push_token(db, user_id)
        else (NotificationChannel.SMS if allow_sms else None)
    )
    if channel is not None:
        delivery = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type=event,
            title=title,
            body=body,
            channel=channel,
            status=NotificationStatus.PENDING,
            related_report_id=report.id,
            created_at=now,
        )
        db.add(delivery)
        result.delivery_ids.append(delivery.id)
    result.recipients += 1


def notify_verifiers_of_new_report(db: Session, report: PollutionReport) -> NotifyResult:
    """Tell the verifiers responsible for the report's zone.

    A verifier is responsible if assigned to that zone or to no zone. Reports
    outside every zone go to all verifiers. The reporter is never told about
    their own report, even if they are also a verifier.
    """
    query = (
        select(User.id, User.preferred_language)
        .join(Verifier, Verifier.user_id == User.id)
        .where(User.is_active.is_(True), User.id != report.reporter_id)
    )
    if report.zone_code is not None:
        query = query.where(
            or_(Verifier.assigned_zone == report.zone_code, Verifier.assigned_zone.is_(None))
        )
    result = NotifyResult()
    for row in db.execute(query).all():
        _create(
            db,
            user=(row.id, row.preferred_language),
            event="report.submitted",
            report=report,
            allow_sms=False,
            result=result,
        )
    return result


def notify_reporter_of_decision(
    db: Session,
    report: PollutionReport,
    event: str,
    reason: str | None = None,
    payout: Payout | None = None,
) -> NotifyResult:
    reporter = db.execute(
        select(User.id, User.preferred_language).where(User.id == report.reporter_id)
    ).one()
    language = reporter.preferred_language
    reward = (
        REWARD_TEXT[language].format(currency=payout.currency, amount=f"{payout.amount:.0f}")
        if payout is not None
        else ""
    )
    result = NotifyResult()
    _create(
        db,
        user=(reporter.id, language),
        event=event,
        report=report,
        allow_sms=True,
        result=result,
        reason=reason or "",
        reward=reward,
    )
    return result


def notify_reporter_of_payout(db: Session, payout: Payout, event: str) -> NotifyResult:
    report = db.get(PollutionReport, payout.report_id)
    language = db.scalar(select(User.preferred_language).where(User.id == payout.reporter_id))
    is_test = payout.provider.value == "MOCK"
    result = NotifyResult()
    _create(
        db,
        user=(payout.reporter_id, language),
        event=event,
        report=report,
        allow_sms=True,
        result=result,
        currency=payout.currency,
        amount=f"{payout.amount:.0f}",
        ref=payout.transaction_ref or "",
        test=TEST_PAYMENT_TEXT[language] if is_test else "",
    )
    return result


def pending_delivery_ids(db: Session, older_than_minutes: int = 2) -> list[uuid.UUID]:
    """Push/SMS deliveries still PENDING (e.g. the server stopped before sending)."""
    cutoff = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
    return list(
        db.scalars(
            select(Notification.id)
            .where(
                Notification.status == NotificationStatus.PENDING,
                Notification.channel != NotificationChannel.IN_APP,
                Notification.created_at < cutoff,
            )
            .limit(200)
        )
    )


# --------------------------------------------------------------------------
# Inbox
# --------------------------------------------------------------------------
def inbox_query(user_id: uuid.UUID):
    return select(Notification).where(
        Notification.user_id == user_id, Notification.channel == NotificationChannel.IN_APP
    )
