"""
FastAPI dependencies for authentication and role-based access control (NFR 1).

Usage in a route:
    def endpoint(user: User = Depends(require_roles(Role.REPORTER))): ...

Roles are always re-read from the database rather than trusted from the token,
so deactivating an account or removing a role takes effect on the very next
request instead of when the token expires.
"""

from collections.abc import Callable
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models import User


class Role(StrEnum):
    REPORTER = "REPORTER"
    VERIFIER = "VERIFIER"
    AGENCY_STAFF = "AGENCY_STAFF"
    ADMINISTRATOR = "ADMINISTRATOR"


# auto_error=False lets us return our own plain-language 401 message
_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/login")

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Please log in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


def load_user_with_roles(db: Session, user_id) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.reporter_profile),
            selectinload(User.verifier_profile),
            selectinload(User.agency_staff_profile),
            selectinload(User.administrator_profile),
        )
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _UNAUTHENTICATED
    try:
        claims = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise _UNAUTHENTICATED from None
    user = load_user_with_roles(db, claims.user_id)
    if user is None:
        raise _UNAUTHENTICATED
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact the administrator.",
        )
    return user


def require_roles(*allowed: Role) -> Callable[..., User]:
    """Allow the request only if the user holds at least one of the given roles."""
    allowed_names = {r.value for r in allowed}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not allowed_names.intersection(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account does not have permission to do this.",
            )
        return user

    return dependency
