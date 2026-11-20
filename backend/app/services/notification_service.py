"""
Notifications.

Sprint 1 stores in-app notifications (shown inside the apps). Push and SMS
delivery through adapters (Expo push, Africa's Talking) is added in Sprint 3;
those adapters will send the rows created here.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, PollutionReport, User, Verifier
from app.models.enums import Language, NotificationChannel, NotificationStatus

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

NEW_REPORT_TEXT = {
    Language.EN: ("New report to review", "A new {category} report is waiting for review."),
    Language.SW: ("Ripoti mpya ya kukagua", "Ripoti mpya ya {category} inasubiri kukaguliwa."),
}


def notify_verifiers_of_new_report(db: Session, report: PollutionReport) -> int:
    """Create an in-app notification for every active verifier except the reporter.

    Returns how many verifiers were notified. Zone-based targeting is added in
    Sprint 3 together with the zone filter on the pending-reports list.
    """
    rows = db.execute(
        select(User.id, User.preferred_language)
        .join(Verifier, Verifier.user_id == User.id)
        .where(User.is_active.is_(True), User.id != report.reporter_id)
    ).all()
    now = datetime.now(UTC)
    for user_id, language in rows:
        title, body = NEW_REPORT_TEXT[language]
        db.add(
            Notification(
                user_id=user_id,
                type="report.submitted",
                title=title,
                body=body.format(category=CATEGORY_NAMES[language][report.category.value]),
                channel=NotificationChannel.IN_APP,
                status=NotificationStatus.SENT,  # stored = delivered for in-app messages
                related_report_id=report.id,
                sent_at=now,
            )
        )
    return len(rows)
