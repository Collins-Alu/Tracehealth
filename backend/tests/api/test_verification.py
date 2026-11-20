"""Module 4 / FR 2.1, FR 2.2 / UML B.4: verification decisions and review queues."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import AuditLog, Notification, Payout, PollutionReport, Verification
from app.models.enums import (
    NotificationChannel,
    PayoutProvider,
    PayoutStatus,
    ReportStatus,
    VerificationDecision,
)
from tests.conftest import auth_headers
from tests.factories import decide, make_report, make_user, make_zone

DANDORA = (-1.2550, 36.8980)
MUKURU = (-1.3120, 36.8750)
FAR_AWAY = (-0.0917, 34.7680)  # Kisumu, outside every test zone


@pytest.fixture
def zones(db):
    make_zone(db, "DANDORA", latitude=DANDORA[0], longitude=DANDORA[1], radius_km=3)
    make_zone(db, "MUKURU", latitude=MUKURU[0], longitude=MUKURU[1], radius_km=3)


@pytest.fixture
def reporter(db):
    from datetime import UTC, datetime

    user = make_user(db, "REPORTER")
    user.reporter_profile.payout_phone = user.phone_number
    user.reporter_profile.payout_consent_at = datetime.now(UTC)
    db.flush()
    return user


@pytest.fixture
def verifier(db, zones):
    return make_user(db, "VERIFIER", zone="DANDORA")


def report_in(db, reporter, where, zone=None, **kw):
    return make_report(db, reporter, latitude=where[0], longitude=where[1], zone_code=zone, **kw)


def post(client, user, report, action, **body):
    return client.post(
        f"/reports/{report.id}/{action}", json=body or None, headers=auth_headers(user)
    )


# ---------- Confirm (B.4 steps 4-9) ------------------------------------------


def test_confirm_marks_verified_requests_payout_audits_and_notifies(
    client, db, reporter, verifier, outbox
):
    report = report_in(db, reporter, DANDORA, "DANDORA")
    r = post(client, verifier, report, "verify")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["report"]["status"] == "VERIFIED"
    assert body["verification"]["decision"] == "VERIFIED"
    assert body["verification"]["is_final"] is True
    assert body["payout_requested"] is True

    payout = db.scalar(select(Payout).where(Payout.report_id == report.id))
    assert payout.status == PayoutStatus.PENDING  # sent by the Sprint 4 adapter
    assert payout.provider == PayoutProvider.MOCK
    assert payout.reporter_id == reporter.id
    assert str(payout.amount) == "50.00"

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "report.verified"))
    assert audit.actor_id == verifier.id
    assert audit.details["previous_status"] == "PENDING"
    assert audit.details["payout_id"] == str(payout.id)

    inbox = db.scalar(
        select(Notification).where(
            Notification.user_id == reporter.id,
            Notification.channel == NotificationChannel.IN_APP,
        )
    )
    assert inbox.title == "Report verified"
    assert "KES 50" in inbox.body
    # No phone registered for push, so the reporter is told by SMS (SRS 3.4)
    assert [phone for phone, _ in outbox.sms.sent] == [reporter.phone_number]


def test_no_payout_without_consent_but_report_still_verified(client, db, verifier):
    no_consent = make_user(db, "REPORTER")
    report = report_in(db, no_consent, DANDORA)
    r = post(client, verifier, report, "verify")
    assert r.json()["report"]["status"] == "VERIFIED"
    assert r.json()["payout_requested"] is False
    assert r.json()["payout_skipped_reason"] == "no_payout_consent"
    assert db.scalar(select(func.count()).select_from(Payout)) == 0


# ---------- Reject and flag (B.4 steps 10-12) --------------------------------


def test_reject_requires_a_reason_and_never_pays(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA)
    assert post(client, verifier, report, "reject").status_code == 422
    assert post(client, verifier, report, "reject", reason="  ").status_code == 422
    r = post(client, verifier, report, "reject", reason="Photo shows a household bin")
    assert r.status_code == 200
    assert r.json()["report"]["status"] == "REJECTED"
    assert r.json()["report"]["decision_reason"] == "Photo shows a household bin"
    assert r.json()["payout_requested"] is False
    assert db.scalar(select(func.count()).select_from(Payout)) == 0
    inbox = db.scalar(
        select(Notification.body).where(
            Notification.user_id == reporter.id, Notification.channel == "IN_APP"
        )
    )
    assert "Photo shows a household bin" in inbox


def test_flag_requires_reason_and_keeps_report_off_the_verified_list(
    client, db, reporter, verifier
):
    report = report_in(db, reporter, DANDORA)
    assert post(client, verifier, report, "flag").status_code == 422
    r = post(client, verifier, report, "flag", reason="Same fire as an earlier report")
    assert r.json()["report"]["status"] == "FLAGGED"
    assert r.json()["verification"]["is_final"] is False
    staff = make_user(db, "AGENCY_STAFF")
    listed = client.get("/reports", headers=auth_headers(staff)).json()
    assert listed["total"] == 0  # SRS 5.5: only verified reports are shown


def test_flagged_report_needs_a_second_verifier(client, db, reporter, verifier, zones):
    report = report_in(db, reporter, DANDORA, "DANDORA")
    post(client, verifier, report, "flag", reason="Possible duplicate")
    r = post(client, verifier, report, "verify")
    assert r.status_code == 403
    assert "different verifier" in r.json()["detail"]

    second = make_user(db, "VERIFIER", zone="DANDORA")
    r = post(client, second, report, "reject", reason="Confirmed duplicate of an earlier report")
    assert r.status_code == 200
    assert r.json()["report"]["status"] == "REJECTED"


def test_second_verifier_can_confirm_a_flagged_report_with_a_note(
    client, db, reporter, verifier, zones
):
    report = report_in(db, reporter, DANDORA)
    post(client, verifier, report, "flag", reason="Possible duplicate")
    second = make_user(db, "VERIFIER")
    r = post(client, second, report, "verify", note="Different site, 400 m away")
    assert r.json()["report"]["status"] == "VERIFIED"
    assert r.json()["verification"]["reason"] == "Different site, 400 m away"


# ---------- Business rules ----------------------------------------------------


def test_reporter_cannot_verify_own_report(client, db, zones):
    both = make_user(db, "REPORTER", "VERIFIER")
    report = report_in(db, both, DANDORA)
    for action, body in [
        ("verify", {}),
        ("reject", {"reason": "x" * 5}),
        ("flag", {"reason": "dup"}),
    ]:
        r = post(client, both, report, action, **body)
        assert r.status_code == 403, action
        assert "you submitted" in r.json()["detail"]
    db.refresh(report)
    assert report.status == ReportStatus.PENDING


def test_final_decisions_cannot_be_changed(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA)
    post(client, verifier, report, "verify")
    other = make_user(db, "VERIFIER")
    for action, body in [
        ("verify", {}),
        ("reject", {"reason": "changed mind"}),
        ("flag", {"reason": "dup"}),
    ]:
        r = post(client, other, report, action, **body)
        assert r.status_code == 409, action
    assert db.scalar(select(func.count()).select_from(Payout)) == 1


def test_confirming_twice_creates_one_payout(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA)
    assert post(client, verifier, report, "verify").status_code == 200
    assert post(client, verifier, report, "verify").status_code == 409
    assert db.scalar(select(func.count()).select_from(Payout)) == 1
    assert db.scalar(select(func.count()).select_from(Verification)) == 1


def test_cannot_flag_twice(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA)
    post(client, verifier, report, "flag", reason="Possible duplicate")
    r = post(client, make_user(db, "VERIFIER"), report, "flag", reason="Also a duplicate")
    assert r.status_code == 409


@pytest.mark.parametrize("role", ["REPORTER", "AGENCY_STAFF", "ADMINISTRATOR"])
def test_only_verifiers_can_decide(client, db, reporter, role):
    report = report_in(db, reporter, DANDORA)
    r = post(client, make_user(db, role), report, "verify")
    assert r.status_code == 403
    assert client.post(f"/reports/{report.id}/verify").status_code == 401


def test_unknown_report_is_404(client, db, verifier):
    r = client.post(f"/reports/{uuid.uuid4()}/verify", headers=auth_headers(verifier))
    assert r.status_code == 404


def test_every_decision_is_audited(client, db, reporter, verifier):
    a, b, c = (report_in(db, reporter, DANDORA) for _ in range(3))
    post(client, verifier, a, "verify")
    post(client, verifier, b, "reject", reason="Not pollution")
    post(client, verifier, c, "flag", reason="Possible duplicate")
    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.actor_id == verifier.id)))
    assert {"report.verified", "report.rejected", "report.flagged"} <= actions


# ---------- Queues and zone filter -------------------------------------------


def test_pending_queue_defaults_to_my_zone_plus_unassigned(client, db, reporter, verifier):
    mine = report_in(db, reporter, DANDORA, "DANDORA")
    other_zone = report_in(db, reporter, MUKURU, "MUKURU")
    unassigned = report_in(db, reporter, FAR_AWAY, None)
    decided = report_in(db, reporter, DANDORA, "DANDORA")
    decide(db, decided, make_user(db, "VERIFIER"), VerificationDecision.VERIFIED)

    def ids(query=""):
        r = client.get(f"/reports/pending{query}", headers=auth_headers(verifier))
        assert r.status_code == 200, r.text
        return {i["id"] for i in r.json()["items"]}

    assert ids() == {str(mine.id), str(unassigned.id)}
    assert ids("?zone=MUKURU") == {str(other_zone.id)}
    assert ids("?zone=UNASSIGNED") == {str(unassigned.id)}
    assert ids("?zone=ALL") == {str(mine.id), str(other_zone.id), str(unassigned.id)}


def test_pending_queue_is_oldest_first_and_hides_my_own_reports(client, db, reporter, zones):
    both = make_user(db, "REPORTER", "VERIFIER")
    now = datetime.now(UTC)
    newer = report_in(db, reporter, DANDORA, captured_at=now - timedelta(hours=1))
    older = report_in(db, reporter, DANDORA, captured_at=now - timedelta(hours=5))
    report_in(db, both, DANDORA)  # their own: not shown
    items = client.get("/reports/pending", headers=auth_headers(both)).json()["items"]
    assert [i["id"] for i in items] == [str(older.id), str(newer.id)]
    assert all(i["can_decide"] for i in items)


def test_flagged_queue_shows_who_may_decide(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA, "DANDORA")
    post(client, verifier, report, "flag", reason="Possible duplicate")

    mine = client.get("/reports/flagged", headers=auth_headers(verifier)).json()["items"]
    assert mine[0]["can_decide"] is False
    assert mine[0]["cannot_decide_reason"] == "FLAGGED_BY_YOU"
    assert mine[0]["decision_reason"] == "Possible duplicate"

    second = make_user(db, "VERIFIER")
    theirs = client.get("/reports/flagged", headers=auth_headers(second)).json()["items"]
    assert theirs[0]["can_decide"] is True

    admin = make_user(db, "ADMINISTRATOR")
    r = client.get("/reports/flagged", headers=auth_headers(admin))
    assert r.status_code == 200 and r.json()["total"] == 1
    assert r.json()["items"][0]["can_decide"] is False  # admins view; verifiers decide


def test_report_detail_tells_a_verifier_why_they_cannot_decide(client, db, zones):
    both = make_user(db, "REPORTER", "VERIFIER")
    report = report_in(db, both, DANDORA)
    body = client.get(f"/reports/{report.id}", headers=auth_headers(both)).json()
    assert body["can_decide"] is False
    assert body["cannot_decide_reason"] == "OWN_REPORT"


def test_search_filters_and_agency_staff_restriction(client, db, reporter, verifier):
    a = report_in(db, reporter, DANDORA, "DANDORA", category="OPEN_BURNING")
    report_in(db, reporter, MUKURU, "MUKURU", category="ILLEGAL_DUMPING")
    decide(db, a, verifier, VerificationDecision.VERIFIED)

    admin = auth_headers(make_user(db, "ADMINISTRATOR"))
    assert client.get("/reports", headers=admin).json()["total"] == 2
    assert client.get("/reports?status=PENDING", headers=admin).json()["total"] == 1
    assert client.get("/reports?zone=MUKURU", headers=admin).json()["total"] == 1
    assert client.get("/reports?category=OPEN_BURNING", headers=admin).json()["total"] == 1

    staff = auth_headers(make_user(db, "AGENCY_STAFF"))
    # Even asking for PENDING returns verified reports only
    r = client.get("/reports?status=PENDING", headers=staff).json()
    assert [i["id"] for i in r["items"]] == [str(a.id)]
    assert client.get("/reports", headers=auth_headers(reporter)).status_code == 403


def test_nearby_reports_help_spot_duplicates(client, db, reporter, verifier):
    now = datetime.now(UTC)
    target = report_in(db, reporter, DANDORA, captured_at=now)
    close = report_in(db, reporter, (DANDORA[0] + 0.0009, DANDORA[1]), captured_at=now)  # ~100 m
    report_in(db, reporter, (DANDORA[0] + 0.01, DANDORA[1]), captured_at=now)  # ~1.1 km
    report_in(db, reporter, DANDORA, captured_at=now - timedelta(days=20))  # too old
    r = client.get(f"/reports/{target.id}/nearby", headers=auth_headers(verifier))
    assert r.status_code == 200
    found = r.json()
    assert [n["report"]["id"] for n in found] == [str(close.id)]
    assert 80 < found[0]["distance_m"] < 120


def test_zones_endpoint(client, db, verifier):
    r = client.get("/zones", headers=auth_headers(verifier))
    assert [z["code"] for z in r.json()] == ["DANDORA", "MUKURU"]


def test_new_reports_are_assigned_to_a_zone(db, zones):
    from app.services.zone_service import zone_for_point

    assert zone_for_point(db, *DANDORA) == "DANDORA"
    assert zone_for_point(db, MUKURU[0] + 0.01, MUKURU[1]) == "MUKURU"  # ~1.1 km away
    assert zone_for_point(db, *FAR_AWAY) is None


def test_decision_report_status_matches_database(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA)
    post(client, verifier, report, "verify")
    assert db.get(PollutionReport, report.id).status == ReportStatus.VERIFIED


def test_blank_verify_note_is_stored_as_no_note(client, db, reporter, verifier):
    report = report_in(db, reporter, DANDORA)
    r = post(client, verifier, report, "verify", note="   ")
    assert r.json()["verification"]["reason"] is None
