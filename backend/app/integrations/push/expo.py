"""
Expo push adapter.

POST https://exp.host/--/api/v2/push/send with up to 100 messages. Expo
answers with one "ticket" per message, in the same order:
  {"status": "ok", "id": "<receipt id>"}
  {"status": "error", "message": "...", "details": {"error": "DeviceNotRegistered"}}
"ok" means Expo accepted the message, not that the phone displayed it.
DeviceNotRegistered means the app was uninstalled, so that token is dropped.

No account key is needed unless "enhanced push security" is enabled for the
Expo project, in which case set EXPO_ACCESS_TOKEN.
"""

import httpx

from app.integrations.push.base import PushMessage, PushResult

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
MAX_PER_REQUEST = 100
ANDROID_CHANNEL_ID = "report-updates"  # created by the mobile app


class ExpoPushSender:
    name = "expo"

    def __init__(self, access_token: str | None = None, client: httpx.Client | None = None):
        self._access_token = access_token
        self._client = client or httpx.Client(timeout=10)

    def send(self, tokens: list[str], message: PushMessage) -> PushResult:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        result = PushResult()
        errors: list[str] = []
        for start in range(0, len(tokens), MAX_PER_REQUEST):
            batch = tokens[start : start + MAX_PER_REQUEST]
            payload = [
                {
                    "to": token,
                    "title": message.title,
                    "body": message.body,
                    "data": message.data,
                    "sound": "default",
                    "channelId": ANDROID_CHANNEL_ID,
                    "priority": "high",
                }
                for token in batch
            ]
            try:
                response = self._client.post(EXPO_PUSH_URL, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                errors.append(f"network: {exc.__class__.__name__}")
                continue
            if response.status_code >= 400:
                errors.append(_request_error(response))
                continue
            tickets = response.json().get("data", [])
            for token, ticket in zip(batch, tickets, strict=False):
                if ticket.get("status") == "ok":
                    result.delivered_refs.append(str(ticket.get("id", "")))
                else:
                    detail = (ticket.get("details") or {}).get("error")
                    if detail == "DeviceNotRegistered":
                        result.invalid_tokens.append(token)
                    errors.append(detail or ticket.get("message", "error"))
        if not result.ok:
            result.error = "; ".join(errors) or "no devices accepted the message"
        return result


def _request_error(response: httpx.Response) -> str:
    try:
        errs = response.json().get("errors") or []
        if errs:
            return f"HTTP {response.status_code} {errs[0].get('code', '')}".strip()
    except ValueError:
        pass
    return f"HTTP {response.status_code}"
