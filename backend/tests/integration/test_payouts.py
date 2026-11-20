"""Module 8 / FR 5.1: payouts are sent once, tracked, retried safely, and
never passed off as real when they are test payments."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.integrations.payments.base import Outcome, PaymentResult
from app.models import AuditLog, Notification, Payout
from app.models.enums import PayoutProvider, PayoutStatus, VerificationDecision
from app.services import payout_service
from tests.conftest import auth_headers
from tests.factories import decide, make_report, make_user


def consenting_reporter(db, phone=None):
    user = make_user(db, "REPORTER", **({"phone_number": phone} if phone else {}))
    user.reporter_profile.payout_phone = user.phone_number
    user.reporter_profile.payout_consent_at = datetime.now(UTC)
    db.flush()
    return user


def pending_payout(db, reporter, provider=PayoutProvider.MOCK):
    report = make_report(db, reporter)
    verification = decide(db, report, make_user(db, "VERIFIER"), VerificationDecision.VERIFIED)
    payout = Payout(
        report_id=report.id,
        verification_id=verification.id,
        reporter_id=reporter.id,
        amount=50,
        currency="KES",
        phone_number=reporter.phone_number,
        provider=provider,
    )
    db.add(payout)
    db.flush()
    return payout


def test_verifying_pays_once_even_if_triggered_again(client, db, outbox):
    reporter = consenting_reporter(db)
    report = make_report(db, reporter)
    admin = auth_headers(make_user(db, "ADMINISTRATOR"))
    client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    r = client.post("/payouts/trigger", json={"report_id": str(report.id)}, headers=admin)
    assert r.status_code == 200 and r.json()["processed"] == 0  # already paid
    assert len(outbox.payments[PayoutProvider.MOCK].sent) == 1
    assert db.scalar(select(func.count()).select_from(Payout)) == 1


def test_simulated_failure_is_recorded_notified_and_retryable(client, db, outbox):
    reporter = consenting_reporter(db, phone="+254700990000")  # mock refuses ...0000
    report = make_report(db, reporter)
    client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    payout = db.scalar(select(Payout))
    assert payout.status == PayoutStatus.FAILED
    assert "simulated failure" in payout.failure_reason
    assert db.scalar(select(Notification).where(Notification.type == "payout.failed"))
    assert db.scalar(select(AuditLog).where(AuditLog.action == "payout.failed")).actor_id is None

    admin = auth_headers(make_user(db, "ADMINISTRATOR"))
    payout.phone_number = "+254700991111"  # the admin fixed the number
    db.flush()
    r = client.post(f"/payouts/{payout.id}/retry", headers=admin)
    assert r.json()["completed"] == 1
    db.refresh(payout)
    assert payout.status == PayoutStatus.SUCCESS and payout.attempts == 2
    assert client.post(f"/payouts/{payout.id}/retry", headers=admin).status_code == 409


def test_payout_list_masks_phone_numbers_and_flags_test_payments(client, db, outbox):
    reporter = consenting_reporter(db, phone="+254712345678")
    report = make_report(db, reporter)
    client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    page = client.get("/payouts", headers=auth_headers(make_user(db, "ADMINISTRATOR"))).json()
    item = page["items"][0]
    assert item["phone_masked"] == "+2547*****678"
    assert item["is_test_payment"] is True
    assert item["status"] == "SUCCESS"
    assert client.get("/payouts", headers=auth_headers(reporter)).status_code == 403
    # The reporter may see their own payout, nobody else's
    assert client.get(f"/payouts/{item['id']}", headers=auth_headers(reporter)).status_code == 200
    other = auth_headers(make_user(db, "REPORTER"))
    assert client.get(f"/payouts/{item['id']}", headers=other).status_code == 404


def test_trigger_rejects_unverified_or_unconsented_reports(client, db, outbox):
    admin = auth_headers(make_user(db, "ADMINISTRATOR"))
    pending = make_report(db, make_user(db, "REPORTER"))
    assert (
        client.post(
            "/payouts/trigger", json={"report_id": str(pending.id)}, headers=admin
        ).status_code
        == 409
    )
    no_consent = make_report(db, make_user(db, "REPORTER"))
    decide(db, no_consent, make_user(db, "VERIFIER"), VerificationDecision.VERIFIED)
    r = client.post("/payouts/trigger", json={"report_id": str(no_consent.id)}, headers=admin)
    assert r.status_code == 409 and "not agreed" in r.json()["detail"]


class Scripted:
    """A fake provider adapter that returns prepared results."""

    name = "MPESA_DARAJA"

    def __init__(self, *results):
        self.results = list(results)
        self.calls = 0

    def send(self, request):
        self.calls += 1
        return self.results.pop(0)


def test_retry_outcome_waits_and_then_gives_up(db, outbox):
    reporter = consenting_reporter(db)
    payout = pending_payout(db, reporter, PayoutProvider.MPESA_DARAJA)
    adapter = Scripted(*[PaymentResult(Outcome.RETRY, message="Could not connect")] * 10)
    adapters = {PayoutProvider.MPESA_DARAJA: adapter}
    payout_service.process_payouts(db, adapters)
    assert payout.status == PayoutStatus.PENDING and payout.attempts == 1
    payout_service.process_payouts(db, adapters)  # too soon: backoff
    assert adapter.calls == 1
    for _ in range(get_settings().PAYOUT_MAX_ATTEMPTS):
        payout.last_attempt_at = datetime.now(UTC) - timedelta(days=1)
        db.flush()
        payout_service.process_payouts(db, adapters, [payout.id])
    assert payout.status == PayoutStatus.FAILED


def test_unknown_outcome_is_never_retried_automatically(db, outbox):
    payout = pending_payout(db, consenting_reporter(db), PayoutProvider.MPESA_DARAJA)
    adapter = Scripted(PaymentResult(Outcome.UNKNOWN, message="No clear answer. Check the portal."))
    payout_service.process_payouts(db, {PayoutProvider.MPESA_DARAJA: adapter})
    assert payout.status == PayoutStatus.FAILED
    assert "Check the portal" in payout.failure_reason


def test_unconfigured_provider_leaves_payout_pending(db, outbox):
    payout = pending_payout(db, consenting_reporter(db), PayoutProvider.MPESA_DARAJA)
    summary = payout_service.process_payouts(db, {PayoutProvider.MOCK: object()})
    assert summary.not_configured == 1
    assert payout.status == PayoutStatus.PENDING and payout.attempts == 0
    assert "not configured" in payout.failure_reason


@pytest.fixture
def mpesa_pending(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "MPESA_CALLBACK_TOKEN", "callback-secret-123")
    payout = pending_payout(db, consenting_reporter(db), PayoutProvider.MPESA_DARAJA)
    adapter = Scripted(PaymentResult(Outcome.ACCEPTED, provider_request_id="AG_2026_0001"))
    payout_service.process_payouts(db, {PayoutProvider.MPESA_DARAJA: adapter})
    assert payout.status == PayoutStatus.PENDING and payout.provider_request_id == "AG_2026_0001"
    return payout


def mpesa_result(code=0, conversation="AG_2026_0001", receipt="TA57ZBCAM3"):
    return {
        "Result": {
            "ResultType": 0,
            "ResultCode": code,
            "ResultDesc": "The service request is processed successfully."
            if code == 0
            else "Insufficient funds",
            "OriginatorConversationID": "x-1",
            "ConversationID": conversation,
            "TransactionID": receipt,
            "ResultParameters": {
                "ResultParameter": [{"Key": "TransactionReceipt", "Value": receipt}]
            },
        }
    }


def test_mpesa_success_callback_marks_paid_once(client, db, mpesa_pending):
    url = "/payouts/callbacks/mpesa/result/callback-secret-123"
    r = client.post(url, json=mpesa_result())
    assert r.json() == {"ResultCode": 0, "ResultDesc": "Accepted"}
    db.refresh(mpesa_pending)
    assert mpesa_pending.status == PayoutStatus.SUCCESS
    assert mpesa_pending.transaction_ref == "TA57ZBCAM3"
    # A repeated callback changes nothing
    client.post(url, json=mpesa_result(code=1))
    db.refresh(mpesa_pending)
    assert mpesa_pending.status == PayoutStatus.SUCCESS
    sent = db.scalar(
        select(Notification).where(
            Notification.type == "payout.sent", Notification.channel == "IN_APP"
        )
    )
    assert "TA57ZBCAM3" in sent.body and "TEST" not in sent.body


def test_mpesa_failure_and_timeout_callbacks(client, db, mpesa_pending):
    client.post("/payouts/callbacks/mpesa/result/callback-secret-123", json=mpesa_result(code=2001))
    db.refresh(mpesa_pending)
    assert mpesa_pending.status == PayoutStatus.FAILED
    assert "Insufficient funds" in mpesa_pending.failure_reason


def test_mpesa_queue_timeout_callback(client, db, mpesa_pending):
    client.post("/payouts/callbacks/mpesa/timeout/callback-secret-123", json=mpesa_result())
    db.refresh(mpesa_pending)
    assert mpesa_pending.status == PayoutStatus.FAILED
    assert "timed out" in mpesa_pending.failure_reason


def test_callbacks_with_a_wrong_token_or_unknown_payout_are_ignored(client, db, mpesa_pending):
    assert (
        client.post("/payouts/callbacks/mpesa/result/guess", json=mpesa_result()).status_code == 404
    )
    client.post(
        "/payouts/callbacks/mpesa/result/callback-secret-123",
        json=mpesa_result(conversation="AG_OTHER"),
    )
    client.post("/payouts/callbacks/mpesa/result/callback-secret-123", content=b"not json")
    db.refresh(mpesa_pending)
    assert mpesa_pending.status == PayoutStatus.PENDING


def test_accepted_requests_with_no_result_expire(db, mpesa_pending):
    mpesa_pending.last_attempt_at = datetime.now(UTC) - timedelta(hours=25)
    db.flush()
    payout_service.expire_stale(db)
    assert mpesa_pending.status == PayoutStatus.FAILED
    assert "before retrying" in mpesa_pending.failure_reason


def test_periodic_jobs_send_due_payouts_and_stuck_notifications(db, outbox):
    payout = pending_payout(db, consenting_reporter(db))
    stuck = Notification(
        id=uuid.uuid4(),
        user_id=payout.reporter_id,
        type="report.verified",
        title="t",
        body="b",
        channel="SMS",
        status="PENDING",
        created_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    db.add(stuck)
    db.flush()
    outbox.processor.run_periodic_jobs()
    assert payout.status == PayoutStatus.SUCCESS
    db.refresh(stuck)
    assert stuck.status == "SENT"
