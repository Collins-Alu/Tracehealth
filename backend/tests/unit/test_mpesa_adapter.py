"""The M-Pesa Daraja B2C adapter against a fake Safaricom server."""

import json
import uuid
from decimal import Decimal

import httpx
import pytest

from app.integrations.payments.base import Outcome, PaymentRequest
from app.integrations.payments.mpesa_daraja import SANDBOX_URL, MpesaDarajaAdapter
from app.schemas.payout import mask_phone

REQUEST = PaymentRequest(
    payout_id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
    attempt=2,
    phone_number="+254708374149",
    amount=Decimal("50.00"),
    currency="KES",
    remarks="reward",
)


def adapter(handler):
    return MpesaDarajaAdapter(
        base_url=SANDBOX_URL,
        consumer_key="key",
        consumer_secret="secret",
        shortcode="600988",
        initiator_name="testapi",
        security_credential="ENCRYPTED==",
        result_url="https://api.example.org/payouts/callbacks/mpesa/result/t",
        timeout_url="https://api.example.org/payouts/callbacks/mpesa/timeout/t",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def token_then(payment_response):
    seen = {}

    def handler(request: httpx.Request):
        if request.url.path == "/oauth/v1/generate":
            seen["auth"] = request.headers["Authorization"]
            return httpx.Response(200, json={"access_token": "tok", "expires_in": "3599"})
        seen["url"] = str(request.url)
        seen["bearer"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        if isinstance(payment_response, Exception):
            raise payment_response
        return payment_response

    return handler, seen


def test_accepted_request_carries_the_right_fields():
    handler, seen = token_then(
        httpx.Response(
            200,
            json={
                "ConversationID": "AG_20261119_0001",
                "OriginatorConversationID": "x",
                "ResponseCode": "0",
                "ResponseDescription": "Accept the service request successfully.",
            },
        )
    )
    result = adapter(handler).send(REQUEST)
    assert result.outcome == Outcome.ACCEPTED
    assert result.provider_request_id == "AG_20261119_0001"
    assert seen["auth"].startswith("Basic ")
    assert seen["bearer"] == "Bearer tok"
    assert seen["url"] == f"{SANDBOX_URL}/mpesa/b2c/v1/paymentrequest"
    body = seen["body"]
    assert body["PartyB"] == "254708374149"  # no plus sign
    assert body["Amount"] == 50
    assert body["PartyA"] == "600988"
    assert body["CommandID"] == "BusinessPayment"
    assert body["OriginatorConversationID"] == f"{REQUEST.payout_id}-2"
    assert body["ResultURL"].endswith("/result/t")


@pytest.mark.parametrize(
    "response, outcome",
    [
        (
            httpx.Response(
                400,
                json={"errorCode": "400.002.02", "errorMessage": "Bad Request - Invalid PartyB"},
            ),
            Outcome.FAILED,
        ),
        (httpx.Response(500, text="oops"), Outcome.UNKNOWN),
        (httpx.ReadTimeout("slow"), Outcome.UNKNOWN),  # may have been sent: never auto-retry
        (httpx.ConnectError("refused"), Outcome.RETRY),  # never sent: safe to retry
    ],
)
def test_error_outcomes(response, outcome):
    handler, _ = token_then(response)
    assert adapter(handler).send(REQUEST).outcome == outcome


def test_failed_login_is_retryable():
    def handler(request):
        return httpx.Response(401, json={"errorMessage": "Invalid credentials"})

    assert adapter(handler).send(REQUEST).outcome == Outcome.RETRY


def test_token_is_reused():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/oauth/v1/generate":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": "3599"})
        return httpx.Response(200, json={"ConversationID": "AG", "ResponseCode": "0"})

    a = adapter(handler)
    a.send(REQUEST)
    a.send(REQUEST)
    assert calls.count("/oauth/v1/generate") == 1


def test_non_kes_is_refused():
    handler, _ = token_then(httpx.Response(200, json={}))
    usd = PaymentRequest(**{**REQUEST.__dict__, "currency": "USD"})
    assert adapter(handler).send(usd).outcome == Outcome.FAILED


def test_phone_masking():
    assert mask_phone("+254712345678") == "+2547*****678"
    assert mask_phone("123") == "****"
