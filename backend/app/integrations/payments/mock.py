"""
MOCK mobile-money adapter: for development, tests and demonstrations.

NO MONEY MOVES. Payouts processed here are stored with provider MOCK and a
transaction reference starting MOCK-TXN-, and every screen marks them as a
test payment. To demonstrate failure handling, numbers ending in 0000 are
refused with a simulated "invalid account" error.
"""

import logging
import uuid

from app.integrations.payments.base import Outcome, PaymentRequest, PaymentResult

log = logging.getLogger("tracehealth.payments.mock")

FAILING_SUFFIX = "0000"


class MockPaymentAdapter:
    name = "MOCK"

    def __init__(self) -> None:
        self.sent: list[PaymentRequest] = []

    def send(self, request: PaymentRequest) -> PaymentResult:
        self.sent.append(request)
        if request.phone_number.endswith(FAILING_SUFFIX):
            log.info("MOCK payout %s refused (test number)", request.payout_id)
            return PaymentResult(
                Outcome.FAILED, message="MOCK: simulated failure (numbers ending 0000)"
            )
        ref = f"MOCK-TXN-{uuid.uuid4().hex[:10].upper()}"
        log.info(
            "MOCK payout %s: %s %s -> %s", request.payout_id, request.currency, request.amount, ref
        )
        return PaymentResult(Outcome.COMPLETED, transaction_ref=ref, provider_request_id=ref)
