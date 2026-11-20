"""Request and response shapes for /auth endpoints."""

import re
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.phone import InvalidPhoneNumber, normalize_phone
from app.models.enums import Language

PASSWORD_RULE = "Use at least 8 characters, including at least one letter and one number."


def _check_password(value: str) -> str:
    if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError(PASSWORD_RULE)
    return value


class RegisterRequest(BaseModel):
    """Public self-registration always creates a Community Reporter account.

    Verifier, agency-staff and administrator accounts are created by an
    administrator, so nobody can give themselves extra permissions.
    """

    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(max_length=25)
    password: str = Field(max_length=128)
    email: EmailStr | None = None
    preferred_language: Language = Language.EN
    # D12: the reporter must accept the privacy notice to create an account
    accept_privacy_notice: bool
    # D4: payouts go to the registration phone only if the reporter agrees
    payout_consent: bool = False

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Please enter your name.")
        return v

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except InvalidPhoneNumber as exc:
            raise ValueError(str(exc)) from None

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str | None) -> str | None:
        return v.lower() if v else None

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _check_password(v)

    @field_validator("accept_privacy_notice")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You need to accept the privacy notice to create an account.")
        return v


class LoginRequest(BaseModel):
    identifier: str = Field(
        min_length=3, max_length=254, description="Phone number or email address"
    )
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone_number: str
    email: str | None
    preferred_language: Language
    roles: list[str]
    assigned_zone: str | None = None
    payout_phone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")
    user: UserOut


class MeUpdate(BaseModel):
    """What people can change about their own account from the app."""

    full_name: str | None = Field(None, min_length=2, max_length=120)
    preferred_language: Language | None = None
    # Reporters only (D4): agree to receive rewards by mobile money, and where
    payout_consent: bool | None = None
    payout_phone: str | None = Field(None, max_length=25)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        return " ".join(v.split()) if v else None

    @field_validator("payout_phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            return normalize_phone(v)
        except InvalidPhoneNumber as exc:
            raise ValueError(str(exc)) from None
