"""Push notification adapters. Choose one with PUSH_PROVIDER (mock | expo | disabled)."""

from app.core.config import get_settings
from app.integrations.push.base import PushMessage, PushResult, PushSender
from app.integrations.push.expo import ExpoPushSender
from app.integrations.push.mock import MockPushSender


def build_push_sender() -> PushSender | None:
    settings = get_settings()
    if settings.PUSH_PROVIDER == "expo":
        return ExpoPushSender(access_token=settings.EXPO_ACCESS_TOKEN)
    if settings.PUSH_PROVIDER == "mock":
        return MockPushSender()
    return None


__all__ = ["PushMessage", "PushResult", "PushSender", "build_push_sender"]
