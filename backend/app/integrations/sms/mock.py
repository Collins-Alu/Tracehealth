"""
MOCK SMS adapter (development and tests). Nothing is sent; messages are logged
and given a MOCK- reference so they can't be mistaken for real deliveries.
"""

import logging
import uuid

from app.integrations.sms.base import SmsResult

log = logging.getLogger("tracehealth.sms.mock")


class MockSmsSender:
    name = "mock"

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, phone_number: str, text: str) -> SmsResult:
        self.sent.append((phone_number, text))
        log.info("MOCK SMS to %s…: %s", phone_number[:7], text[:60])
        return SmsResult(ok=True, ref=f"MOCK-SMS-{uuid.uuid4().hex[:12]}")
