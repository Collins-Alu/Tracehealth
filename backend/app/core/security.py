"""
Passwords and tokens.

Passwords: Argon2id, the current OWASP-recommended algorithm. It is
deliberately slow and memory-hard, which makes brute-forcing leaked hashes
expensive. Plain-text passwords are never stored or logged.

Tokens: after login the client holds two tokens.
  * Access token  - a signed JWT, valid for ACCESS_TOKEN_EXPIRE_MINUTES. Sent
    with every request ("Authorization: Bearer ..."). Not stored on the server.
  * Refresh token - a long random string, valid for REFRESH_TOKEN_EXPIRE_DAYS.
    Used only to get a new access token. The server stores its SHA-256 hash,
    so it can be revoked (logout) and a database leak exposes nothing usable.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()  # library defaults follow the OWASP-recommended profile

# A real hash of a random password. Used to spend the same time verifying a
# password when the account does not exist, so response times do not reveal
# which phone numbers/emails are registered.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerificationError, InvalidHashError):
        return False


def burn_password_check(plain_password: str) -> None:
    """Spend the time of a real check when there is no account to check against."""
    verify_password(plain_password, _DUMMY_HASH)


def password_needs_rehash(password_hash: str) -> bool:
    """True when the stored hash used weaker parameters than today's defaults."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return False


# --------------------------------------------------------------------------
# Access tokens (JWT)
# --------------------------------------------------------------------------
class InvalidTokenError(Exception):
    """The token is missing, malformed, expired or signed with the wrong key."""


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    roles: list[str]


def create_access_token(user_id: uuid.UUID, roles: list[str]) -> tuple[str, int]:
    """Return (token, lifetime_in_seconds)."""
    settings = get_settings()
    lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "roles": roles,  # informational for clients; the API re-reads roles from the DB
        "type": "access",
        "iat": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],  # never trust the token's own "alg"
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("not an access token")
        return AccessTokenClaims(user_id=uuid.UUID(payload["sub"]), roles=payload.get("roles", []))
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenError(str(exc)) from exc


# --------------------------------------------------------------------------
# Refresh tokens (opaque random strings, stored hashed)
# --------------------------------------------------------------------------
def new_refresh_token() -> tuple[str, str, datetime]:
    """Return (token_for_client, sha256_hash_for_db, expires_at)."""
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return token, hash_refresh_token(token), expires_at


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
