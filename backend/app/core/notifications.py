"""FastAPI dependency that provides the notification dispatcher."""

from functools import lru_cache

from app.db.session import SessionLocal
from app.integrations.push import build_push_sender
from app.integrations.sms import build_sms_sender
from app.services.notification_dispatch import NotificationDispatcher


@lru_cache
def _dispatcher() -> NotificationDispatcher:
    return NotificationDispatcher(SessionLocal, build_push_sender(), build_sms_sender())


def get_notification_dispatcher() -> NotificationDispatcher:
    return _dispatcher()
