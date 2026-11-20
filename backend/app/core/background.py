"""
Work that happens outside the request (Sprint 4).

PayoutProcessor  sends payouts and then delivers the resulting notifications.
                 Used right after a report is verified (so the reporter is paid
                 within seconds) and by the periodic job.

run_periodic_jobs  every JOBS_INTERVAL_SECONDS while the API runs:
                   1. send PENDING payouts whose retry time has come
                   2. mark M-Pesa requests with no result for too long FAILED
                   3. resend push/SMS notifications stuck in PENDING
                 Safe with several API workers: rows are locked with
                 SKIP LOCKED, so each item is handled by one worker only.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.notifications import get_notification_dispatcher
from app.db.session import SessionLocal
from app.integrations.payments import PaymentAdapter, build_payment_adapters
from app.models.enums import PayoutProvider
from app.services import notification_service, payout_service
from app.services.notification_dispatch import NotificationDispatcher
from app.services.payout_service import ProcessSummary

log = logging.getLogger("tracehealth.jobs")


class PayoutProcessor:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]],
        adapters: dict[PayoutProvider, PaymentAdapter],
        dispatcher: NotificationDispatcher,
    ):
        self.session_factory = session_factory
        self.adapters = adapters
        self.dispatcher = dispatcher

    def process(self, payout_ids: list[uuid.UUID] | None = None) -> ProcessSummary:
        with self.session_factory() as db:
            summary = payout_service.process_payouts(db, self.adapters, payout_ids)
        self.dispatcher.dispatch(summary.delivery_ids)
        return summary

    def run_periodic_jobs(self) -> None:
        self.process()
        with self.session_factory() as db:
            expired = payout_service.expire_stale(db)
            stuck = notification_service.pending_delivery_ids(db)
        self.dispatcher.dispatch(expired.delivery_ids + stuck)


@lru_cache
def _processor() -> PayoutProcessor:
    return PayoutProcessor(SessionLocal, build_payment_adapters(), get_notification_dispatcher())


def get_payout_processor() -> PayoutProcessor:
    return _processor()


async def periodic_jobs_loop() -> None:
    interval = get_settings().JOBS_INTERVAL_SECONDS
    while True:
        try:
            await asyncio.to_thread(get_payout_processor().run_periodic_jobs)
        except Exception:
            log.exception("Periodic jobs failed; will try again")
        await asyncio.sleep(interval)
