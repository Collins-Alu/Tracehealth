"""Notifications: in-app inbox, push registration, zone targeting, push-then-SMS fallback."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.integrations.push.base import PushResult
from app.models import DevicePushToken, Notification
from app.models.enums import NotificationChannel, NotificationStatus
from tests.conftest import auth_headers
from tests.factories import make_report, make_user, make_zone
from tests.photos import jpeg_bytes

TOKEN = "ExponentPushToken[abcdefghijklmnop1234]"


def register_token(client, user, token=TOKEN):
    return client.post(
        "/devices/push-token",
        json={"token": token, "platform": "android"},
        headers=auth_headers(user),
    )


def submit(client, user, lat=-1.2550, lng=36.8980):
    return client.post(
        "/reports",
        data={
            "client_report_id": str(uuid.uuid4()),
            "category": "OPEN_BURNING",
            "latitude": str(lat),
            "longitude": str(lng),
            "captured_at": datetime.now(UTC).isoformat(),
        },
        files={"photo": ("p.jpg", jpeg_bytes(), "image/jpeg")},
        headers=auth_headers(user),
    )


def test_push_token_registration_validates_and_moves_between_accounts(client, db):
    a, b = make_user(db, "REPORTER"), make_user(db, "REPORTER")
    bad = client.post(
        "/devices/push-token",
        json={"token": "not-a-token", "platform": "android"},
        headers=auth_headers(a),
    )
    assert bad.status_code == 422
    assert register_token(client, a).status_code == 204
    assert register_token(client, a).status_code == 204  # idempotent
    assert register_token(client, b).status_code == 204  # same phone, new account
    owners = list(db.scalars(select(DevicePushToken.user_id)))
    assert owners == [b.id]
    r = client.request(
        "DELETE", "/devices/push-token", json={"token": TOKEN}, headers=auth_headers(b)
    )
    assert r.status_code == 204
    assert db.scalar(select(DevicePushToken)) is None


def test_new_report_alerts_only_verifiers_for_that_zone(client, db, outbox):
    make_zone(db, "DANDORA", latitude=-1.2550, longitude=36.8980, radius_km=3)
    make_zone(db, "KIBERA", latitude=-1.3130, longitude=36.7880, radius_km=3)
    in_zone = make_user(db, "VERIFIER", zone="DANDORA")
    other_zone = make_user(db, "VERIFIER", zone="KIBERA")
    roaming = make_user(db, "VERIFIER")  # no zone: sees everything
    register_token(client, in_zone)
    reporter = make_user(db, "REPORTER")

    report_id = submit(client, reporter).json()["report"]["id"]
    recipients = set(
        db.scalars(
            select(Notification.user_id).where(
                Notification.related_report_id == uuid.UUID(report_id),
                Notification.channel == NotificationChannel.IN_APP,
            )
        )
    )
    assert recipients == {in_zone.id, roaming.id}
    assert other_zone.id not in recipients
    # Push went to the one verifier with a registered phone; verifiers never get SMS
    assert [token for token, _ in outbox.push.sent] == [TOKEN]
    assert outbox.sms.sent == []


def test_reporter_with_a_phone_registered_gets_push_not_sms(client, db, outbox):
    reporter = make_user(db, "REPORTER")
    register_token(client, reporter)
    report = make_report(db, reporter)
    r = client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    assert r.status_code == 200
    assert len(outbox.push.sent) == 1
    token, message = outbox.push.sent[0]
    assert message.title == "Report verified"
    assert message.data == {"type": "report.verified", "report_id": str(report.id)}
    assert outbox.sms.sent == []
    delivery = db.scalar(
        select(Notification).where(Notification.channel == NotificationChannel.PUSH)
    )
    assert delivery.status == NotificationStatus.SENT
    assert delivery.provider_ref.startswith("MOCK-PUSH-")  # clearly not a real delivery


def test_failed_push_falls_back_to_sms_and_drops_dead_tokens(client, db, outbox):
    reporter = make_user(db, "REPORTER")
    register_token(client, reporter)

    def broken(tokens, message):
        return PushResult(invalid_tokens=list(tokens), error="DeviceNotRegistered")

    outbox.push.send = broken
    report = make_report(db, reporter)
    client.post(
        f"/reports/{report.id}/reject",
        json={"reason": "Photo too blurry"},
        headers=auth_headers(make_user(db, "VERIFIER")),
    )
    push = db.scalar(select(Notification).where(Notification.channel == NotificationChannel.PUSH))
    assert push.status == NotificationStatus.FAILED
    assert push.failure_reason == "DeviceNotRegistered"
    sms = db.scalar(select(Notification).where(Notification.channel == NotificationChannel.SMS))
    assert sms.status == NotificationStatus.SENT
    assert outbox.sms.sent[0][0] == reporter.phone_number
    assert "Photo too blurry" in outbox.sms.sent[0][1]
    assert db.scalar(select(DevicePushToken)) is None


def test_failed_sms_is_recorded_not_raised(client, db, outbox):
    from app.integrations.sms.base import SmsResult

    outbox.sms.send = lambda phone, text: SmsResult(ok=False, error="InvalidPhoneNumber")
    reporter = make_user(db, "REPORTER")
    report = make_report(db, reporter)
    r = client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    assert r.status_code == 200
    sms = db.scalar(select(Notification).where(Notification.channel == NotificationChannel.SMS))
    assert sms.status == NotificationStatus.FAILED
    assert sms.failure_reason == "InvalidPhoneNumber"


def test_notifications_are_in_the_reporters_language(client, db, outbox):
    reporter = make_user(db, "REPORTER", preferred_language="SW")
    report = make_report(db, reporter)
    client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    inbox = db.scalar(select(Notification).where(Notification.channel == "IN_APP"))
    assert inbox.title == "Ripoti imethibitishwa"
    assert "uchomaji wa taka" in inbox.body


def test_inbox_lists_marks_read_and_counts_unread(client, db, outbox):
    reporter = make_user(db, "REPORTER")
    verifier = make_user(db, "VERIFIER")
    first, second = make_report(db, reporter), make_report(db, reporter)
    client.post(f"/reports/{first.id}/verify", headers=auth_headers(verifier))
    client.post(
        f"/reports/{second.id}/reject",
        json={"reason": "Not pollution"},
        headers=auth_headers(verifier),
    )
    headers = auth_headers(reporter)
    page = client.get("/notifications", headers=headers).json()
    assert page["total"] == 2 and page["unread"] == 2  # SMS delivery rows are not listed
    assert page["items"][0]["title"] == "Report not accepted"  # newest first

    n_id = page["items"][0]["id"]
    assert client.post(f"/notifications/{n_id}/read", headers=headers).status_code == 204
    assert client.get("/notifications", headers=headers).json()["unread"] == 1
    assert client.post("/notifications/read-all", headers=headers).status_code == 204
    assert client.get("/notifications", headers=headers).json()["unread"] == 0

    # Someone else's notification cannot be touched
    stranger = auth_headers(make_user(db, "REPORTER"))
    assert client.post(f"/notifications/{n_id}/read", headers=stranger).status_code == 404


def test_dispatching_the_same_notification_twice_sends_once(db, outbox):
    from app.models.enums import Language
    from app.services.notification_service import notify_reporter_of_decision

    reporter = make_user(db, "REPORTER", preferred_language=Language.EN)
    report = make_report(db, reporter)
    result = notify_reporter_of_decision(db, report, "report.verified")
    db.flush()
    outbox.dispatcher.dispatch(result.delivery_ids)
    outbox.dispatcher.dispatch(result.delivery_ids)
    assert len(outbox.sms.sent) == 1
