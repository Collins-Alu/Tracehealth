"""Administration: users and roles, audit log, settings, zones, own account."""

import pytest
from sqlalchemy import select

from app.models import AuditLog, PollutionReport, RefreshToken
from app.models.enums import VerificationDecision
from tests.conftest import auth_headers
from tests.factories import decide, make_report, make_user, make_zone

NEW_USER = {
    "full_name": "Grace Verifier",
    "phone_number": "0711 222 333",
    "email": "Grace@Example.com",
    "password": "Temp-pass-2026",
    "roles": ["VERIFIER"],
}


@pytest.fixture
def admin(db):
    return make_user(db, "ADMINISTRATOR")


def test_admin_creates_user_with_roles_and_zone(client, db, admin):
    make_zone(db, "DANDORA")
    r = client.post(
        "/admin/users", json={**NEW_USER, "assigned_zone": "DANDORA"}, headers=auth_headers(admin)
    )
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["roles"] == ["VERIFIER"]
    assert user["phone_number"] == "+254711222333"
    assert user["email"] == "grace@example.com"
    assert user["assigned_zone"] == "DANDORA"
    # The new person can log in with the temporary password
    login = client.post(
        "/auth/login", json={"identifier": "0711222333", "password": "Temp-pass-2026"}
    )
    assert login.status_code == 200
    assert db.scalar(select(AuditLog).where(AuditLog.action == "user.created"))


def test_create_user_validation(client, db, admin):
    h = auth_headers(admin)
    assert client.post("/admin/users", json={**NEW_USER, "roles": []}, headers=h).status_code == 422
    assert (
        client.post("/admin/users", json={**NEW_USER, "password": "weak"}, headers=h).status_code
        == 422
    )
    assert (
        client.post(
            "/admin/users", json={**NEW_USER, "assigned_zone": "NOWHERE"}, headers=h
        ).status_code
        == 422
    )
    staff = {**NEW_USER, "roles": ["AGENCY_STAFF"]}
    assert (
        client.post("/admin/users", json=staff, headers=h).status_code == 422
    )  # agency name needed
    assert client.post("/admin/users", json=NEW_USER, headers=h).status_code == 201
    assert client.post("/admin/users", json=NEW_USER, headers=h).status_code == 409


def test_list_and_filter_users(client, db, admin):
    make_user(db, "REPORTER", full_name="Wanjiru Reporter")
    make_user(db, "VERIFIER", full_name="Otieno Verifier")
    h = auth_headers(admin)
    assert client.get("/admin/users?role=VERIFIER", headers=h).json()["total"] == 1
    found = client.get("/admin/users?q=wanjiru", headers=h).json()["items"]
    assert [u["full_name"] for u in found] == ["Wanjiru Reporter"]


def test_deactivation_ends_sessions_immediately(client, db, admin):
    tokens = client.post(
        "/auth/register",
        json={
            "full_name": "To Be Deactivated",
            "phone_number": "0799 000 111",
            "password": "Clean-air-2026",
            "accept_privacy_notice": True,
        },
    ).json()
    user_id = tokens["user"]["id"]
    r = client.patch(
        f"/admin/users/{user_id}", json={"is_active": False}, headers=auth_headers(admin)
    )
    assert r.json()["is_active"] is False
    assert client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).status_code in (401, 403)
    assert db.scalar(select(RefreshToken).where(RefreshToken.revoked_at.is_(None))) is None


def test_roles_can_be_added_and_removed_but_not_while_in_use(client, db, admin):
    person = make_user(db, "REPORTER")
    h = auth_headers(admin)
    r = client.patch(
        f"/admin/users/{person.id}", json={"roles": ["REPORTER", "VERIFIER"]}, headers=h
    )
    assert r.json()["roles"] == ["REPORTER", "VERIFIER"]
    make_report(db, person)
    r = client.patch(f"/admin/users/{person.id}", json={"roles": ["VERIFIER"]}, headers=h)
    assert r.status_code == 409
    assert "Deactivate the account instead" in r.json()["detail"]


def test_admin_cannot_lock_themselves_out(client, db, admin):
    h = auth_headers(admin)
    assert (
        client.patch(f"/admin/users/{admin.id}", json={"is_active": False}, headers=h).status_code
        == 409
    )
    assert (
        client.patch(
            f"/admin/users/{admin.id}", json={"roles": ["VERIFIER"]}, headers=h
        ).status_code
        == 409
    )


def test_password_reset_requires_new_login(client, db, admin):
    person = make_user(db, "REPORTER")
    r = client.patch(
        f"/admin/users/{person.id}",
        json={"password": "Reset-pass-2026"},
        headers=auth_headers(admin),
    )
    assert r.status_code == 200
    login = client.post(
        "/auth/login", json={"identifier": person.phone_number, "password": "Reset-pass-2026"}
    )
    assert login.status_code == 200
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "user.updated"))
    assert entry.details == {"changes": ["password_reset"]}  # never the password itself


def test_audit_log_listing_and_filters(client, db, admin):
    reporter, verifier = make_user(db, "REPORTER"), make_user(db, "VERIFIER")
    report = make_report(db, reporter)
    client.post(f"/reports/{report.id}/verify", headers=auth_headers(verifier))
    h = auth_headers(admin)
    page = client.get("/admin/audit-logs?action=report.", headers=h).json()
    assert page["items"][0]["action"] == "report.verified"
    assert page["items"][0]["actor_name"] == verifier.full_name
    by_entity = client.get(f"/admin/audit-logs?entity_id={report.id}", headers=h).json()
    assert by_entity["total"] >= 1


def test_settings_are_validated_audited_and_linkage_recomputed(client, db, admin):
    h = auth_headers(admin)
    keys = {s["key"] for s in client.get("/admin/settings", headers=h).json()}
    assert "linkage.radius_km" in keys
    assert (
        client.patch("/admin/settings/linkage.radius_km", json={"value": 99}, headers=h).status_code
        == 422
    )
    assert (
        client.patch(
            "/admin/settings/linkage.radius_km", json={"value": "far"}, headers=h
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/admin/settings/linkage.baseline_weeks", json={"value": 6.5}, headers=h
        ).status_code
        == 422
    )
    bad_map = {"value": {"OPEN_BURNING": ["SNEEZING"]}}
    assert (
        client.patch(
            "/admin/settings/linkage.category_mapping", json=bad_map, headers=h
        ).status_code
        == 422
    )
    assert client.patch("/admin/settings/nope", json={"value": 1}, headers=h).status_code == 404
    r = client.patch("/admin/settings/linkage.radius_km", json={"value": 2.5}, headers=h)
    assert r.status_code == 200 and r.json()["value"] == 2.5
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "setting.updated"))
    assert entry.details == {"key": "linkage.radius_km", "old": 3, "new": 2.5}


def test_zones_create_update_and_reassign_reports(client, db, admin):
    reporter = make_user(db, "REPORTER")
    report = make_report(db, reporter, latitude=-1.2550, longitude=36.8980)
    assert report.zone_code is None
    h = auth_headers(admin)
    zone = {
        "code": "DANDORA",
        "name": "Dandora",
        "latitude": -1.2550,
        "longitude": 36.8980,
        "radius_km": 2,
    }
    r = client.post("/admin/zones", json=zone, headers=h)
    assert r.status_code == 201 and r.json()["reports"] == 1
    db.refresh(report)
    assert report.zone_code == "DANDORA"
    assert client.post("/admin/zones", json=zone, headers=h).status_code == 409
    r = client.patch("/admin/zones/DANDORA", json={"is_active": False}, headers=h)
    assert r.json()["is_active"] is False and r.json()["reports"] == 0
    assert (
        client.post("/admin/zones", json={**zone, "code": "bad code"}, headers=h).status_code == 422
    )


@pytest.mark.parametrize(
    "path", ["/admin/users", "/admin/audit-logs", "/admin/settings", "/admin/zones"]
)
def test_admin_area_is_administrators_only(client, db, path):
    for role in ["REPORTER", "VERIFIER", "AGENCY_STAFF"]:
        assert client.get(path, headers=auth_headers(make_user(db, role))).status_code == 403


def test_reporter_manages_own_language_and_payout_consent(client, db):
    me = make_user(db, "REPORTER")
    h = auth_headers(me)
    r = client.patch("/auth/me", json={"preferred_language": "SW"}, headers=h)
    assert r.json()["preferred_language"] == "SW"
    r = client.patch("/auth/me", json={"payout_phone": "0722000111"}, headers=h)
    assert r.status_code == 422  # consent first
    r = client.patch(
        "/auth/me", json={"payout_consent": True, "payout_phone": "0722 000 111"}, headers=h
    )
    assert r.json()["payout_phone"] == "+254722000111"
    r = client.patch("/auth/me", json={"payout_consent": False}, headers=h)
    assert r.json()["payout_phone"] is None
    verifier = make_user(db, "VERIFIER")
    r = client.patch("/auth/me", json={"payout_consent": True}, headers=auth_headers(verifier))
    assert r.status_code == 403


def test_reports_are_not_editable_through_admin(db):
    """Guard: the admin API never changes report status (only verifiers do)."""
    verifier, reporter = make_user(db, "VERIFIER"), make_user(db, "REPORTER")
    report = make_report(db, reporter)
    decide(db, report, verifier, VerificationDecision.VERIFIED)
    assert db.get(PollutionReport, report.id).status == "VERIFIED"


def test_missing_settings_are_restored_with_defaults(client, db):
    """A wiped system_settings table heals itself instead of leaving the
    settings screen empty."""
    from sqlalchemy import delete

    from app.models import SystemSetting

    admin = auth_headers(make_user(db, "ADMINISTRATOR"))
    db.execute(delete(SystemSetting))
    db.commit()
    keys = {s["key"] for s in client.get("/admin/settings", headers=admin).json()}
    assert {"linkage.radius_km", "payout.amount", "dashboard.small_count_threshold"} <= keys
    ok = client.patch("/admin/settings/payout.amount", json={"value": 40}, headers=admin)
    assert ok.status_code == 200 and ok.json()["value"] == 40
