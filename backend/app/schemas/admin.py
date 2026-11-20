"""Shapes for administration: users, audit log, settings, zones."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.deps import Role
from app.core.phone import InvalidPhoneNumber, normalize_phone
from app.models.enums import Language
from app.schemas.auth import PASSWORD_RULE, _check_password


class AdminUserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    phone_number: str
    email: str | None
    preferred_language: Language
    is_active: bool
    roles: list[str]
    assigned_zone: str | None = None
    agency_name: str | None = None
    department: str | None = None
    admin_level: int | None = None
    created_at: datetime


class AdminUserPage(BaseModel):
    items: list[AdminUserOut]
    total: int
    limit: int
    offset: int


class _RoleFields(BaseModel):
    assigned_zone: str | None = Field(None, description="Verifier zone code (null = all zones)")
    agency_name: str | None = Field(None, max_length=150)
    department: str | None = Field(None, max_length=150)
    admin_level: int | None = Field(None, ge=1, le=3)


def _phone(v: str) -> str:
    try:
        return normalize_phone(v)
    except InvalidPhoneNumber as exc:
        raise ValueError(str(exc)) from None


class AdminUserCreate(_RoleFields):
    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str = Field(max_length=25)
    email: EmailStr | None = None
    password: str = Field(max_length=128, description=f"Temporary password. {PASSWORD_RULE}")
    roles: list[Role] = Field(min_length=1)
    preferred_language: Language = Language.EN

    @field_validator("phone_number")
    @classmethod
    def _phone_ok(cls, v: str) -> str:
        return _phone(v)

    @field_validator("password")
    @classmethod
    def _password_ok(cls, v: str) -> str:
        return _check_password(v)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str | None) -> str | None:
        return v.lower() if v else None


class AdminUserUpdate(_RoleFields):
    full_name: str | None = Field(None, min_length=2, max_length=120)
    email: EmailStr | None = None
    is_active: bool | None = None
    roles: list[Role] | None = Field(None, min_length=1)
    preferred_language: Language | None = None
    password: str | None = Field(None, max_length=128, description="Set a new temporary password")

    @field_validator("password")
    @classmethod
    def _password_ok(cls, v: str | None) -> str | None:
        return _check_password(v) if v is not None else None

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str | None) -> str | None:
        return v.lower() if v else None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    actor_id: uuid.UUID | None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    details: dict | None


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    description: str | None
    updated_at: datetime


class SettingUpdate(BaseModel):
    value: Any


class ZoneIn(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,39}$")
    name: str = Field(min_length=2, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=50)


class ZoneUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    radius_km: float | None = Field(None, gt=0, le=50)
    is_active: bool | None = None


class ZoneAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    latitude: float
    longitude: float
    radius_km: float
    is_active: bool
    reports: int = 0
    verifiers: int = 0
