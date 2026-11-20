"""
MOCK push adapter (development and tests).

Nothing is sent to any phone. Each "delivery" is logged and gets a reference
starting with MOCK-, which is stored on the notification so it can never be
mistaken for a real delivery.
"""

import logging
import uuid

from app.integrations.push.base import PushMessage, PushResult

log = logging.getLogger("tracehealth.push.mock")


class MockPushSender:
    name = "mock"

    def __init__(self) -> None:
        self.sent: list[tuple[str, PushMessage]] = []

    def send(self, tokens: list[str], message: PushMessage) -> PushResult:
        refs = []
        for token in tokens:
            self.sent.append((token, message))
            refs.append(f"MOCK-PUSH-{uuid.uuid4().hex[:12]}")
            log.info("MOCK push to %s…: %s", token[:24], message.title)
        return PushResult(delivered_refs=refs)
