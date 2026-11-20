"""
Safaricom M-Pesa Daraja B2C adapter (business pays a customer).

Flow
  1. GET  {base}/oauth/v1/generate?grant_type=client_credentials
          (HTTP Basic auth with consumer key and secret) -> access_token
  2. POST {base}{MPESA_B2C_PATH} with the payment request -> M-Pesa answers
          straight away with ResponseCode "0" and a ConversationID if it
          ACCEPTED the request. That is not a payment yet.
  3. M-Pesa later POSTs the RESULT to our ResultURL (or QueueTimeOutURL).
          ResultCode 0 = paid; TransactionID is the receipt. See
          payout_service.apply_mpesa_result.

Base URLs: sandbox https://sandbox.safaricom.co.ke, live https://api.safaricom.co.ke.

SecurityCredential is the initiator password encrypted with Safaricom's
certificate. The Daraja portal generates it for you (sandbox: "Test
Credentials" page); store the result in MPESA_SECURITY_CREDENTIAL.

Double-payment safety: if the request may have reached M-Pesa but we got no
clear answer (timeout, dropped connection after sending), the result is
UNKNOWN and is never retried automatically. An administrator checks the
M-Pesa portal first. Only "connection refused" style errors, where nothing
was sent, are retried.
"""

import time

import httpx

from app.integrations.payments.base import Outcome, PaymentRequest, PaymentResult

SANDBOX_URL = "https://sandbox.safaricom.co.ke"
LIVE_URL = "https://api.safaricom.co.ke"


class MpesaDarajaAdapter:
    name = "MPESA_DARAJA"

    def __init__(
        self,
        *,
        base_url: str,
        consumer_key: str,
        consumer_secret: str,
        shortcode: str,
        initiator_name: str,
        security_credential: str,
        result_url: str,
        timeout_url: str,
        b2c_path: str = "/mpesa/b2c/v1/paymentrequest",
        command_id: str = "BusinessPayment",
        client: httpx.Client | None = None,
    ):
        self._base = base_url.rstrip("/")
        self._key, self._secret = consumer_key, consumer_secret
        self._shortcode = shortcode
        self._initiator = initiator_name
        self._credential = security_credential
        self._result_url, self._timeout_url = result_url, timeout_url
        self._path = b2c_path
        self._command = command_id
        self._client = client or httpx.Client(timeout=30)
        self._token: str | None = None
        self._token_expires = 0.0

    def _access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires:
            return self._token
        response = self._client.get(
            f"{self._base}/oauth/v1/generate",
            params={"grant_type": "client_credentials"},
            auth=(self._key, self._secret),
        )
        response.raise_for_status()
        body = response.json()
        self._token = body["access_token"]
        # Refresh a minute early
        self._token_expires = time.monotonic() + int(body.get("expires_in", 3599)) - 60
        return self._token

    def send(self, request: PaymentRequest) -> PaymentResult:
        if request.currency != "KES":
            return PaymentResult(Outcome.FAILED, message="M-Pesa pays in KES only.")
        try:
            token = self._access_token()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            # Nothing was sent yet: safe to retry
            return PaymentResult(
                Outcome.RETRY, message=f"M-Pesa login failed: {exc.__class__.__name__}"
            )

        body = {
            # Our own id for this attempt, echoed back in the result callback
            "OriginatorConversationID": f"{request.payout_id}-{request.attempt}",
            "InitiatorName": self._initiator,
            "SecurityCredential": self._credential,
            "CommandID": self._command,
            "Amount": int(request.amount),  # M-Pesa amounts are whole shillings
            "PartyA": self._shortcode,
            "PartyB": request.phone_number.lstrip("+"),  # 2547XXXXXXXX
            "Remarks": request.remarks[:100],
            "QueueTimeOutURL": self._timeout_url,
            "ResultURL": self._result_url,
            "Occasion": "TraceHealth reward",
        }
        try:
            response = self._client.post(
                f"{self._base}{self._path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.ConnectError:
            return PaymentResult(Outcome.RETRY, message="Could not connect to M-Pesa.")
        except httpx.HTTPError as exc:
            return PaymentResult(
                Outcome.UNKNOWN,
                message=f"No clear answer from M-Pesa ({exc.__class__.__name__}). "
                "Check the M-Pesa portal before retrying.",
            )

        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code < 300 and str(data.get("ResponseCode")) == "0":
            return PaymentResult(
                Outcome.ACCEPTED,
                provider_request_id=data.get("ConversationID")
                or data.get("OriginatorConversationID"),
                message=data.get("ResponseDescription"),
            )
        if response.status_code >= 500:
            return PaymentResult(
                Outcome.UNKNOWN,
                message=f"M-Pesa error HTTP {response.status_code}. "
                "Check the portal before retrying.",
            )
        reason = (
            data.get("errorMessage")
            or data.get("ResponseDescription")
            or f"HTTP {response.status_code}"
        )
        return PaymentResult(Outcome.FAILED, message=f"M-Pesa refused the request: {reason}")
