"""
/auth endpoints (Module 1).

Flow for a client app:
  1. POST /auth/register or /auth/login  -> access_token + refresh_token
  2. Send "Authorization: Bearer <access_token>" with every request
  3. When a request returns 401, call POST /auth/refresh once and retry
  4. POST /auth/logout revokes the refresh token on this device
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _raise(exc: AuthError):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    raise HTTPException(status_code=exc.status_code, detail=exc.message, headers=headers)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Community Reporter account",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return auth_service.register_reporter(db, data)
    except AuthError as exc:
        _raise(exc)


@router.post("/login", response_model=TokenResponse, summary="Log in with phone/email and password")
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return auth_service.login(db, data.identifier, data.password)
    except AuthError as exc:
        _raise(exc)


@router.post("/refresh", response_model=TokenResponse, summary="Exchange a refresh token")
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return auth_service.refresh(db, data.refresh_token)
    except AuthError as exc:
        _raise(exc)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke this device's session"
)
def logout(
    data: LogoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    auth_service.logout(db, user, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="The logged-in user and their roles")
def me(user: User = Depends(get_current_user)) -> UserOut:
    return auth_service.user_to_out(user)
