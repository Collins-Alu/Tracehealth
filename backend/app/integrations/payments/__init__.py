"""
Mobile-money adapters, one per PayoutProvider.

Each payout is processed by the adapter matching ITS provider, so a MOCK
payout is never sent to M-Pesa and an M-Pesa payout is never "paid" by the
mock, whatever PAYOUT_PROVIDER says today.
"""

from app.core.config import get_settings
from app.integrations.payments.base import Outcome, PaymentAdapter, PaymentRequest, PaymentResult
from app.integrations.payments.mock import MockPaymentAdapter
from app.integrations.payments.mpesa_daraja import LIVE_URL, SANDBOX_URL, MpesaDarajaAdapter
from app.models.enums import PayoutProvider


def mpesa_configured() -> bool:
    s = get_settings()
    return all(
        [
            s.MPESA_CONSUMER_KEY,
            s.MPESA_CONSUMER_SECRET,
            s.MPESA_SHORTCODE,
            s.MPESA_INITIATOR_NAME,
            s.MPESA_SECURITY_CREDENTIAL,
            s.MPESA_CALLBACK_BASE_URL,
            s.MPESA_CALLBACK_TOKEN,
        ]
    )


def build_payment_adapters() -> dict[PayoutProvider, PaymentAdapter]:
    s = get_settings()
    adapters: dict[PayoutProvider, PaymentAdapter] = {PayoutProvider.MOCK: MockPaymentAdapter()}
    if mpesa_configured():
        callback = f"{s.MPESA_CALLBACK_BASE_URL.rstrip('/')}/payouts/callbacks/mpesa"
        adapters[PayoutProvider.MPESA_DARAJA] = MpesaDarajaAdapter(
            base_url=LIVE_URL if s.MPESA_ENVIRONMENT == "production" else SANDBOX_URL,
            consumer_key=s.MPESA_CONSUMER_KEY,
            consumer_secret=s.MPESA_CONSUMER_SECRET,
            shortcode=s.MPESA_SHORTCODE,
            initiator_name=s.MPESA_INITIATOR_NAME,
            security_credential=s.MPESA_SECURITY_CREDENTIAL,
            result_url=f"{callback}/result/{s.MPESA_CALLBACK_TOKEN}",
            timeout_url=f"{callback}/timeout/{s.MPESA_CALLBACK_TOKEN}",
            b2c_path=s.MPESA_B2C_PATH,
        )
    return adapters


__all__ = [
    "Outcome",
    "PaymentAdapter",
    "PaymentRequest",
    "PaymentResult",
    "build_payment_adapters",
    "mpesa_configured",
]
