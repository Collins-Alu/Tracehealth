"""
Africa's Talking SMS adapter (SRS 3.4: SMS fallback).

POST {url} with form fields username, to, message and optionally from.
  Sandbox: https://api.sandbox.africastalking.com/version1/messaging
           (username "sandbox"; messages appear in the sandbox simulator,
           not on real phones)
  Live:    https://api.africastalking.com/version1/messaging
Header "apiKey" carries the key. The reply lists one entry per recipient in
SMSMessageData.Recipients; statusCode 100 (Processed), 101 (Sent) and
102 (Queued) mean accepted. Anything else is a failure with a reason.
"""

import httpx

from app.integrations.sms.base import SmsResult

SUCCESS_CODES = {100, 101, 102}


class AfricasTalkingSmsSender:
    name = "africastalking"

    def __init__(
        self,
        username: str,
        api_key: str,
        url: str,
        sender_id: str | None = None,
        client: httpx.Client | None = None,
    ):
        self._username = username
        self._api_key = api_key
        self._url = url
        self._sender_id = sender_id
        self._client = client or httpx.Client(timeout=15)

    def send(self, phone_number: str, text: str) -> SmsResult:
        form = {"username": self._username, "to": phone_number, "message": text}
        if self._sender_id:
            form["from"] = self._sender_id
        headers = {"apiKey": self._api_key, "Accept": "application/json"}
        try:
            response = self._client.post(self._url, data=form, headers=headers)
        except httpx.HTTPError as exc:
            return SmsResult(ok=False, error=f"network: {exc.__class__.__name__}")
        if response.status_code >= 400:
            # Never echo the response body: it can contain account details
            return SmsResult(ok=False, error=f"HTTP {response.status_code}")
        try:
            recipients = response.json()["SMSMessageData"]["Recipients"]
        except (ValueError, KeyError, TypeError):
            return SmsResult(ok=False, error="unexpected response from Africa's Talking")
        if not recipients:
            return SmsResult(ok=False, error="no recipients accepted")
        first = recipients[0]
        if int(first.get("statusCode", 0)) in SUCCESS_CODES:
            return SmsResult(ok=True, ref=first.get("messageId"))
        return SmsResult(ok=False, error=str(first.get("status", "failed")))
