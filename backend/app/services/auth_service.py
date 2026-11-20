"""
Account registration, login, token refresh and logout.

Refresh-token ROTATION: every successful refresh revokes the old refresh
token and issues a new one. If a token that was already used shows up again,
someone has copied it, so every session for that account is revoked and the
real user simply logs in again.
"""

from datetime import UTC, datetime

from sqlalchemy import false, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.deps import load_user_with_roles
from app.core.phone import InvalidPhoneNumber, normalize_phone
from app.models import RefreshToken, Reporter, User
from app.schemas.auth import MeUpdate, RegisterRequest, TokenResponse, UserOut
from app.services import audit_service


class AuthError(Exception):
    """Raised with a plain-language message that is safe to show the user."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


INVALID_LOGIN = "Incorrect phone number/email or password."


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        email=user.email,
        preferred_language=user.preferred_language,
        roles=user.roles,
        assigned_zone=user.verifier_profile.assigned_zone if user.verifier_profile else None,
        payout_phone=user.reporter_profile.payout_phone if user.reporter_profile else None,
    )


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    access, lifetime = security.create_access_token(user.id, user.roles)
    refresh, refresh_hash, expires_at = security.new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=refresh_hash, expires_at=expires_at))
    return TokenResponse(
        access_token=access, refresh_token=refresh, expires_in=lifetime, user=user_to_out(user)
    )


def register_reporter(db: Session, data: RegisterRequest) -> TokenResponse:
    taken = db.scalar(
        select(User.id).where(
            or_(
                User.phone_number == data.phone_number,
                (User.email == data.email) if data.email else false(),
            )
        )
    )
    if taken:
        raise AuthError("An account with this phone number or email already exists.", 409)

    now = datetime.now(UTC)
    user = User(
        full_name=data.full_name,
        phone_number=data.phone_number,
        email=data.email,
        password_hash=security.hash_password(data.password),
        preferred_language=data.preferred_language,
    )
    user.reporter_profile = Reporter(
        payout_phone=data.phone_number if data.payout_consent else None,
        payout_consent_at=now if data.payout_consent else None,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        # Two sign-ups with the same number at the same moment
        db.rollback()
        raise AuthError("An account with this phone number or email already exists.", 409) from None

    audit_service.record(
        db,
        actor_id=user.id,
        action="auth.registered",
        entity_type="user",
        entity_id=user.id,
        details={
            "privacy_notice_accepted_at": now.isoformat(),
            "payout_consent": data.payout_consent,
        },
    )
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


def _find_by_identifier(db: Session, identifier: str) -> User | None:
    identifier = identifier.strip()
    if "@" in identifier:
        condition = User.email == identifier.lower()
    else:
        try:
            condition = User.phone_number == normalize_phone(identifier)
        except InvalidPhoneNumber:
            return None
    user_id = db.scalar(select(User.id).where(condition))
    return load_user_with_roles(db, user_id) if user_id else None


def login(db: Session, identifier: str, password: str) -> TokenResponse:
    user = _find_by_identifier(db, identifier)
    if user is None:
        security.burn_password_check(password)
        raise AuthError(INVALID_LOGIN, 401)
    if not security.verify_password(password, user.password_hash):
        audit_service.record(
            db, actor_id=user.id, action="auth.login_failed", entity_type="user", entity_id=user.id
        )
        db.commit()
        raise AuthError(INVALID_LOGIN, 401)
    if not user.is_active:
        raise AuthError("This account has been deactivated. Please contact the administrator.", 403)
    if security.password_needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)

    audit_service.record(
        db, actor_id=user.id, action="auth.login", entity_type="user", entity_id=user.id
    )
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


def refresh(db: Session, refresh_token: str) -> TokenResponse:
    token_hash = security.hash_refresh_token(refresh_token)
    # FOR UPDATE: two simultaneous refreshes with one token cannot both succeed
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )
    now = datetime.now(UTC)
    if stored is None:
        raise AuthError("Your session has expired. Please log in again.", 401)

    if stored.revoked_at is not None:
        # Reuse of an old token: treat as theft and end every session for this user
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        audit_service.record(
            db,
            actor_id=stored.user_id,
            action="auth.refresh_token_reused",
            entity_type="user",
            entity_id=stored.user_id,
        )
        db.commit()
        raise AuthError("Your session has expired. Please log in again.", 401)

    if stored.expires_at <= now:
        raise AuthError("Your session has expired. Please log in again.", 401)

    user = load_user_with_roles(db, stored.user_id)
    if user is None or not user.is_active:
        raise AuthError("This account has been deactivated. Please contact the administrator.", 403)

    stored.revoked_at = now
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


def logout(db: Session, user: User, refresh_token: str) -> None:
    """Revoke the refresh token. Idempotent: logging out twice is not an error."""
    token_hash = security.hash_refresh_token(refresh_token)
    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.user_id == user.id
        )
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        audit_service.record(
            db, actor_id=user.id, action="auth.logout", entity_type="user", entity_id=user.id
        )
    db.commit()


def update_me(db: Session, user: User, data: MeUpdate) -> UserOut:
    changes: dict = {}
    if data.full_name and data.full_name != user.full_name:
        user.full_name = data.full_name
        changes["full_name"] = True
    if data.preferred_language and data.preferred_language != user.preferred_language:
        user.preferred_language = data.preferred_language
        changes["preferred_language"] = data.preferred_language.value
    if data.payout_consent is not None or data.payout_phone is not None:
        profile = user.reporter_profile
        if profile is None:
            raise AuthError("Only reporters receive rewards.", 403)
        if data.payout_consent is False:
            profile.payout_phone = None
            profile.payout_consent_at = None
            changes["payout_consent"] = False
        else:
            phone = data.payout_phone or profile.payout_phone or user.phone_number
            if data.payout_consent or profile.payout_consent_at is not None:
                profile.payout_phone = phone
                profile.payout_consent_at = profile.payout_consent_at or datetime.now(UTC)
                changes["payout_consent"] = True
                changes["payout_phone_changed"] = data.payout_phone is not None
            else:
                raise AuthError("Agree to mobile money payouts before adding a number.", 422)
    if changes:
        audit_service.record(
            db,
            actor_id=user.id,
            action="user.self_updated",
            entity_type="user",
            entity_id=user.id,
            details=changes,
        )
    db.commit()
    db.refresh(user)
    return user_to_out(user)
