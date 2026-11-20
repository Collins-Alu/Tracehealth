"""Module 1: registration, login, tokens, logout (NFR 1)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import AuditLog, RefreshToken, User
from tests.conftest import auth_headers
from tests.factories import make_user, make_zone

GOOD = {
    "full_name": "Wanjiru Test",
    "phone_number": "0712 345 678",
    "password": "Clean-air-2026",
    "accept_privacy_notice": True,
}


def register(client, **overrides):
    return client.post("/auth/register", json={**GOOD, **overrides})


def test_register_creates_reporter_and_returns_tokens(client, db):
    r = register(client, payout_consent=True, email="Wanjiru@Example.COM")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["roles"] == ["REPORTER"]
    assert body["user"]["phone_number"] == "+254712345678"  # normalised
    assert body["user"]["email"] == "wanjiru@example.com"
    assert body["user"]["payout_phone"] == "+254712345678"
    user = db.scalar(select(User).where(User.phone_number == "+254712345678"))
    assert user.password_hash.startswith("$argon2id$")
    assert user.reporter_profile.payout_consent_at is not None


def test_payout_phone_not_stored_without_consent(client):
    assert register(client).json()["user"]["payout_phone"] is None


def test_registration_cannot_grant_extra_roles(client):
    r = register(client, roles=["ADMINISTRATOR"], is_admin=True)
    assert r.status_code == 201
    assert r.json()["user"]["roles"] == ["REPORTER"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"accept_privacy_notice": False},
        {"password": "short1"},
        {"password": "nodigitshere"},
        {"phone_number": "12"},
        {"full_name": " "},
        {"email": "not-an-email"},
    ],
)
def test_invalid_registration_is_rejected(client, overrides):
    assert register(client, **overrides).status_code == 422


def test_duplicate_phone_is_rejected_in_any_format(client):
    assert register(client).status_code == 201
    r = register(client, phone_number="+254-712-345678")
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_login_with_phone_or_email(client):
    register(client, email="wanjiru@example.com")
    for identifier in ["0712345678", "+254712345678", "WANJIRU@example.com"]:
        r = client.post(
            "/auth/login", json={"identifier": identifier, "password": GOOD["password"]}
        )
        assert r.status_code == 200, identifier
        assert r.json()["user"]["full_name"] == "Wanjiru Test"


def test_wrong_password_and_unknown_user_get_same_message(client, db):
    register(client)
    wrong = client.post("/auth/login", json={"identifier": "0712345678", "password": "Nope12345"})
    unknown = client.post("/auth/login", json={"identifier": "0799999999", "password": "Nope12345"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.login_failed")) is not None


def test_deactivated_user_cannot_log_in(client, db):
    user = make_user(db, "REPORTER", password_hash=hash_password("Clean-air-2026"))
    user.is_active = False
    db.flush()
    r = client.post(
        "/auth/login", json={"identifier": user.phone_number, "password": "Clean-air-2026"}
    )
    assert r.status_code == 403


def test_me_requires_a_valid_token(client, db):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    make_zone(db, "ZONE-A")
    user = make_user(db, "VERIFIER", zone="ZONE-A")
    r = client.get("/auth/me", headers=auth_headers(user))
    assert r.status_code == 200
    assert r.json()["roles"] == ["VERIFIER"]
    assert r.json()["assigned_zone"] == "ZONE-A"


def test_expired_or_forged_tokens_are_rejected(client, db):
    user = make_user(db, "REPORTER")
    settings = get_settings()
    past = datetime.now(UTC) - timedelta(hours=1)
    expired = jwt.encode(
        {"sub": str(user.id), "type": "access", "iat": past, "exp": past + timedelta(minutes=1)},
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )
    forged = jwt.encode(
        {
            "sub": str(user.id),
            "type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "a-different-secret-key-that-is-long-enough",
        algorithm="HS256",
    )
    unsigned = jwt.encode({"sub": str(user.id), "type": "access"}, None, algorithm="none")
    for token in [expired, forged, unsigned]:
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


def test_deactivation_takes_effect_immediately(client, db):
    user = make_user(db, "REPORTER")
    headers = auth_headers(user)
    user.is_active = False
    db.flush()
    assert client.get("/auth/me", headers=headers).status_code == 403


def test_refresh_rotates_tokens(client):
    first = register(client).json()
    r = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200
    second = r.json()
    assert second["refresh_token"] != first["refresh_token"]
    # The old refresh token no longer works
    again = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert again.status_code == 401


def test_reusing_an_old_refresh_token_ends_all_sessions(client, db):
    first = register(client).json()
    second = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).json()
    client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})  # theft signal
    r = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert r.status_code == 401
    active = db.scalars(select(RefreshToken).where(RefreshToken.revoked_at.is_(None))).all()
    assert active == []
    assert db.scalar(select(AuditLog).where(AuditLog.action == "auth.refresh_token_reused"))


def test_logout_revokes_refresh_token(client):
    tokens = register(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
    )
    assert r.status_code == 204
    assert (
        client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )
    # Logging out twice is harmless
    again = client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
    )
    assert again.status_code == 204


def test_registration_is_audited(client, db):
    user_id = register(client).json()["user"]["id"]
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "auth.registered"))
    assert str(entry.entity_id) == user_id
    assert "privacy_notice_accepted_at" in entry.details
