"""SMS adapters. Choose one with SMS_PROVIDER (mock | africastalking | disabled)."""

from app.core.config import get_settings
from app.integrations.sms.africastalking import AfricasTalkingSmsSender
from app.integrations.sms.base import SmsResult, SmsSender
from app.integrations.sms.mock import MockSmsSender


class SmsConfigurationError(RuntimeError):
    pass


def build_sms_sender() -> SmsSender | None:
    settings = get_settings()
    if settings.SMS_PROVIDER == "africastalking":
        if not settings.AT_API_KEY:
            raise SmsConfigurationError(
                "SMS_PROVIDER=africastalking needs AT_API_KEY (and AT_USERNAME). See .env.example."
            )
        return AfricasTalkingSmsSender(
            username=settings.AT_USERNAME,
            api_key=settings.AT_API_KEY,
            sender_id=settings.AT_SENDER_ID,
            url=settings.at_messaging_url,
        )
    if settings.SMS_PROVIDER == "mock":
        return MockSmsSender()
    return None


__all__ = ["SmsResult", "SmsSender", "build_sms_sender", "SmsConfigurationError"]
