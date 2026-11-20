"""
Sends PENDING push and SMS notifications (runs after the response is sent).

For each delivery notification:
  PUSH -> send to all of the user's registered devices.
          Accepted by at least one device  -> SENT (provider_ref stored)
          Otherwise                        -> FAILED, and for reporter-facing
                                              events a new SMS is created and sent
          Tokens Expo says are dead are deleted.
  SMS  -> send to the user's phone number    -> SENT or FAILED

A failure never raises: the reason is stored on the notification so an
administrator can see what happened.
"""

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.integrations.push import PushMessage, PushSender
from app.integrations.sms import SmsSender
from app.models import DevicePushToken, Notification, User
from app.models.enums import NotificationChannel, NotificationStatus
from app.services.notification_service import SMS_FALLBACK_TYPES

log = logging.getLogger("tracehealth.notifications")

SMS_MAX_CHARS = 300


def sms_text(title: str, body: str) -> str:
    text = f"TraceHealth: {title}. {body}"
    return text if len(text) <= SMS_MAX_CHARS else text[: SMS_MAX_CHARS - 1] + "…"


class NotificationDispatcher:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        push: PushSender | None,
        sms: SmsSender | None,
    ):
        self._session_factory = session_factory
        self._push = push
        self._sms = sms

    def dispatch(self, notification_ids: list[uuid.UUID]) -> None:
        if not notification_ids:
            return
        with self._session_factory() as db:
            for notification_id in notification_ids:
                try:
                    self._deliver(db, notification_id)
                    db.commit()
                except Exception:  # one bad message must not stop the others
                    db.rollback()
                    log.exception("Notification %s could not be delivered", notification_id)

    def _deliver(self, db: Session, notification_id: uuid.UUID) -> None:
        n = db.get(Notification, notification_id, with_for_update=True)
        if n is None or n.status != NotificationStatus.PENDING:
            return  # already handled (e.g. dispatched twice)
        if n.channel == NotificationChannel.PUSH:
            self._deliver_push(db, n)
        elif n.channel == NotificationChannel.SMS:
            self._deliver_sms(db, n)

    def _deliver_push(self, db: Session, n: Notification) -> None:
        tokens = list(
            db.scalars(select(DevicePushToken.token).where(DevicePushToken.user_id == n.user_id))
        )
        if self._push is None or not tokens:
            self._fail(n, "push disabled" if self._push is None else "no registered device")
        else:
            data = {"type": n.type, "report_id": str(n.related_report_id or "")}
            result = self._push.send(tokens, PushMessage(title=n.title, body=n.body, data=data))
            if result.invalid_tokens:
                db.execute(
                    delete(DevicePushToken).where(DevicePushToken.token.in_(result.invalid_tokens))
                )
            if result.ok:
                self._succeed(n, ",".join(result.delivered_refs)[:120])
                return
            self._fail(n, result.error or "push failed")

        if n.type in SMS_FALLBACK_TYPES and self._sms is not None:
            fallback = Notification(
                id=uuid.uuid4(),
                user_id=n.user_id,
                type=n.type,
                title=n.title,
                body=n.body,
                channel=NotificationChannel.SMS,
                status=NotificationStatus.PENDING,
                related_report_id=n.related_report_id,
            )
            db.add(fallback)
            db.flush()
            self._deliver_sms(db, fallback)

    def _deliver_sms(self, db: Session, n: Notification) -> None:
        if self._sms is None:
            self._fail(n, "sms disabled")
            return
        phone = db.scalar(select(User.phone_number).where(User.id == n.user_id))
        result = self._sms.send(phone, sms_text(n.title, n.body))
        if result.ok:
            self._succeed(n, (result.ref or "")[:120])
        else:
            self._fail(n, result.error or "sms failed")

    @staticmethod
    def _succeed(n: Notification, ref: str) -> None:
        n.status = NotificationStatus.SENT
        n.provider_ref = ref or None
        n.sent_at = datetime.now(UTC)
        n.failure_reason = None

    @staticmethod
    def _fail(n: Notification, reason: str) -> None:
        n.status = NotificationStatus.FAILED
        n.failure_reason = reason[:500]
