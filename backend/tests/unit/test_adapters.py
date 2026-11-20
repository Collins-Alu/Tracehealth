"""The real Expo push and Africa's Talking SMS adapters, against fake HTTP servers."""

import json

import httpx
import pytest

from app.integrations.push.base import PushMessage
from app.integrations.push.expo import EXPO_PUSH_URL, ExpoPushSender
from app.integrations.sms.africastalking import AfricasTalkingSmsSender
from app.services.notification_dispatch import sms_text

GOOD = "ExponentPushToken[good-token-000000]"
DEAD = "ExponentPushToken[dead-token-000000]"


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_expo_sends_one_message_per_token_and_reports_dead_tokens():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"status": "ok", "id": "receipt-1"},
                    {
                        "status": "error",
                        "message": "not registered",
                        "details": {"error": "DeviceNotRegistered"},
                    },
                ]
            },
        )

    sender = ExpoPushSender(access_token="secret", client=client_for(handler))
    result = sender.send([GOOD, DEAD], PushMessage("Title", "Body", {"report_id": "r1"}))
    assert seen["url"] == EXPO_PUSH_URL
    assert seen["auth"] == "Bearer secret"
    assert [m["to"] for m in seen["body"]] == [GOOD, DEAD]
    assert seen["body"][0]["channelId"] == "report-updates"
    assert seen["body"][0]["data"] == {"report_id": "r1"}
    assert result.ok and result.delivered_refs == ["receipt-1"]
    assert result.invalid_tokens == [DEAD]


def test_expo_request_errors_are_reported_not_raised():
    def handler(request):
        return httpx.Response(429, json={"errors": [{"code": "TOO_MANY_REQUESTS"}]})

    result = ExpoPushSender(client=client_for(handler)).send([GOOD], PushMessage("t", "b"))
    assert not result.ok
    assert "TOO_MANY_REQUESTS" in result.error


def test_expo_network_failure_is_reported_not_raised():
    def handler(request):
        raise httpx.ConnectError("offline")

    result = ExpoPushSender(client=client_for(handler)).send([GOOD], PushMessage("t", "b"))
    assert not result.ok and result.error.startswith("network")


def test_expo_batches_at_100():
    calls = []

    def handler(request):
        batch = json.loads(request.content)
        calls.append(len(batch))
        return httpx.Response(200, json={"data": [{"status": "ok", "id": "x"}] * len(batch)})

    tokens = [f"ExponentPushToken[t{i:015d}]" for i in range(150)]
    ExpoPushSender(client=client_for(handler)).send(tokens, PushMessage("t", "b"))
    assert calls == [100, 50]


def at_sender(handler, sender_id=None):
    return AfricasTalkingSmsSender(
        username="sandbox",
        api_key="at-key",
        url="https://api.sandbox.africastalking.com/version1/messaging",
        sender_id=sender_id,
        client=client_for(handler),
    )


def test_africastalking_success():
    seen = {}

    def handler(request: httpx.Request):
        seen["headers"] = request.headers
        seen["form"] = dict(httpx.QueryParams(request.content.decode()))
        return httpx.Response(
            201,
            json={
                "SMSMessageData": {
                    "Message": "Sent to 1/1",
                    "Recipients": [
                        {
                            "statusCode": 101,
                            "status": "Success",
                            "messageId": "ATXid_1",
                            "number": "+254700000001",
                            "cost": "KES 0.8000",
                        }
                    ],
                }
            },
        )

    result = at_sender(handler, sender_id="TRACEHLTH").send("+254700000001", "hello")
    assert result.ok and result.ref == "ATXid_1"
    assert seen["headers"]["apiKey"] == "at-key"
    assert seen["form"] == {
        "username": "sandbox",
        "to": "+254700000001",
        "message": "hello",
        "from": "TRACEHLTH",
    }


@pytest.mark.parametrize(
    "response, expected_error",
    [
        (
            httpx.Response(
                201,
                json={
                    "SMSMessageData": {
                        "Recipients": [{"statusCode": 403, "status": "InvalidPhoneNumber"}]
                    }
                },
            ),
            "InvalidPhoneNumber",
        ),
        (httpx.Response(401, text="The supplied authentication is invalid"), "HTTP 401"),
        (httpx.Response(201, json={"unexpected": True}), "unexpected response"),
        (httpx.Response(201, json={"SMSMessageData": {"Recipients": []}}), "no recipients"),
    ],
)
def test_africastalking_failures(response, expected_error):
    result = at_sender(lambda request: response).send("+254700000001", "hello")
    assert not result.ok
    assert expected_error in result.error


def test_sms_text_is_prefixed_and_capped():
    text = sms_text("Report verified", "x" * 500)
    assert text.startswith("TraceHealth: Report verified.")
    assert len(text) == 300
