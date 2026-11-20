"""
Administration endpoints (administrators only).

Users       GET /admin/users, POST /admin/users, PATCH /admin/users/{id}
Audit log   GET /admin/audit-logs
Settings    GET /admin/settings, PATCH /admin/settings/{key}
Zones       GET /admin/zones, POST /admin/zones, PATCH /admin/zones/{code}

Safety rules:
  * administrators cannot deactivate themselves or remove their own
    Administrator role (so the system can't be locked out by mistake);
  * a role can't be removed while records depend on it (e.g. a reporter's
    reports); deactivate the account instead;
  * deactivating an account ends all its sessions at once;
  * every change is written to the audit log (never passwords).
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, or_, select, text, update
from sqlalchemy.orm import Session, selectinload

from app.core.deps import Role, load_user_with_roles, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models import (
    Administrator,
    AgencyStaff,
    AuditLog,
    ClinicImportBatch,
    PollutionReport,
    RefreshToken,
    Reporter,
    SystemSetting,
    User,
    Verification,
    Verifier,
    Zone,
)
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserPage,
    AdminUserUpdate,
    AuditLogOut,
    AuditLogPage,
    SettingOut,
    SettingUpdate,
    ZoneAdminOut,
    ZoneIn,
    ZoneUpdate,
)
from app.services import audit_service, linkage_engine, setting_service, settings_rules

router = APIRouter(prefix="/admin", tags=["Administration"])
admin_only = require_roles(Role.ADMINISTRATOR)


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
def _user_out(u: User) -> AdminUserOut:
    return AdminUserOut(
        id=u.id,
        full_name=u.full_name,
        phone_number=u.phone_number,
        email=u.email,
        preferred_language=u.preferred_language,
        is_active=u.is_active,
        roles=u.roles,
        assigned_zone=u.verifier_profile.assigned_zone if u.verifier_profile else None,
        agency_name=u.agency_staff_profile.agency_name if u.agency_staff_profile else None,
        department=u.agency_staff_profile.department if u.agency_staff_profile else None,
        admin_level=u.administrator_profile.admin_level if u.administrator_profile else None,
        created_at=u.created_at,
    )


_PROFILES = {
    Role.REPORTER: (Reporter, "reporter_profile"),
    Role.VERIFIER: (Verifier, "verifier_profile"),
    Role.AGENCY_STAFF: (AgencyStaff, "agency_staff_profile"),
    Role.ADMINISTRATOR: (Administrator, "administrator_profile"),
}

_ROLE_IN_USE = {
    Role.REPORTER: (
        PollutionReport.reporter_id,
        "This person has submitted reports, so the Reporter role can't be removed. "
        "Deactivate the account instead.",
    ),
    Role.VERIFIER: (
        Verification.verifier_id,
        "This person has made verification decisions, so the Verifier role can't be "
        "removed. Deactivate the account instead.",
    ),
    Role.ADMINISTRATOR: (
        ClinicImportBatch.imported_by,
        "This person has imported clinic data, so the Administrator role can't be "
        "removed. Deactivate the account instead.",
    ),
}


def _check_zone(db: Session, code: str | None):
    if code is not None and db.get(Zone, code) is None:
        raise HTTPException(422, f'Zone "{code}" does not exist.')


def _apply_roles(db: Session, user: User, roles: set[Role], data) -> list[str]:
    """Add/remove role profiles and update role fields. Returns a list of changes."""
    changes = []
    for role, (_model, attr) in _PROFILES.items():
        has = getattr(user, attr) is not None
        if role in roles and not has:
            if role == Role.AGENCY_STAFF and not data.agency_name:
                raise HTTPException(422, "Agency staff need an agency name.")
            profile = {
                Role.REPORTER: lambda: Reporter(),
                Role.VERIFIER: lambda: Verifier(assigned_zone=data.assigned_zone),
                Role.AGENCY_STAFF: lambda: AgencyStaff(
                    agency_name=data.agency_name, department=data.department
                ),
                Role.ADMINISTRATOR: lambda: Administrator(admin_level=data.admin_level or 1),
            }[role]()
            setattr(user, attr, profile)
            changes.append(f"+{role.value}")
        elif role not in roles and has:
            in_use = _ROLE_IN_USE.get(role)
            if in_use and db.scalar(select(exists().where(in_use[0] == user.id))):
                raise HTTPException(409, in_use[1])
            setattr(user, attr, None)
            changes.append(f"-{role.value}")
    return changes


def _apply_role_fields(user: User, data, fields_set: set[str]) -> list[str]:
    changes = []
    if user.verifier_profile and "assigned_zone" in fields_set:
        user.verifier_profile.assigned_zone = data.assigned_zone
        changes.append("assigned_zone")
    if user.agency_staff_profile:
        for name in ("agency_name", "department"):
            if name in fields_set and getattr(data, name) is not None:
                setattr(user.agency_staff_profile, name, getattr(data, name))
                changes.append(name)
    if user.administrator_profile and data.admin_level is not None:
        user.administrator_profile.admin_level = data.admin_level
        changes.append("admin_level")
    return changes


@router.get("/users", response_model=AdminUserPage, summary="List users")
def list_users(
    q: str | None = Query(None, description="name, phone or email contains"),
    role: Role | None = None,
    active: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> AdminUserPage:
    conditions = []
    if q:
        like = f"%{q.strip()}%"
        conditions.append(
            or_(User.full_name.ilike(like), User.phone_number.ilike(like), User.email.ilike(like))
        )
    if active is not None:
        conditions.append(User.is_active.is_(active))
    if role:
        model, _attr = _PROFILES[role]
        conditions.append(exists().where(model.user_id == User.id))
    total = db.scalar(select(func.count()).select_from(User).where(*conditions))
    users = db.scalars(
        select(User)
        .where(*conditions)
        .options(
            selectinload(User.reporter_profile),
            selectinload(User.verifier_profile),
            selectinload(User.agency_staff_profile),
            selectinload(User.administrator_profile),
        )
        .order_by(User.full_name)
        .limit(limit)
        .offset(offset)
    ).all()
    return AdminUserPage(
        items=[_user_out(u) for u in users], total=total, limit=limit, offset=offset
    )


@router.post("/users", response_model=AdminUserOut, status_code=201, summary="Create a user")
def create_user(
    data: AdminUserCreate, admin: User = Depends(admin_only), db: Session = Depends(get_db)
) -> AdminUserOut:
    taken = db.scalar(
        select(User.id).where(
            or_(User.phone_number == data.phone_number, User.email == data.email)
            if data.email
            else User.phone_number == data.phone_number
        )
    )
    if taken:
        raise HTTPException(409, "An account with this phone number or email already exists.")
    _check_zone(db, data.assigned_zone)
    if Role.AGENCY_STAFF in data.roles and not data.agency_name:
        raise HTTPException(422, "Agency staff need an agency name.")
    user = User(
        id=uuid.uuid4(),
        full_name=" ".join(data.full_name.split()),
        phone_number=data.phone_number,
        email=data.email,
        password_hash=hash_password(data.password),
        preferred_language=data.preferred_language,
    )
    db.add(user)
    _apply_roles(db, user, set(data.roles), data)
    db.flush()
    audit_service.record(
        db,
        actor_id=admin.id,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        details={"roles": user.roles},
    )
    db.commit()
    return _user_out(load_user_with_roles(db, user.id))


@router.patch("/users/{user_id}", response_model=AdminUserOut, summary="Update a user")
def update_user(
    user_id: uuid.UUID,
    data: AdminUserUpdate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    user = load_user_with_roles(db, user_id)
    if user is None:
        raise HTTPException(404, "User not found.")
    fields = data.model_fields_set
    is_self = user.id == admin.id
    if is_self and data.is_active is False:
        raise HTTPException(409, "You can't deactivate your own account.")
    if is_self and data.roles is not None and Role.ADMINISTRATOR not in data.roles:
        raise HTTPException(409, "You can't remove your own Administrator role.")
    if "assigned_zone" in fields:
        _check_zone(db, data.assigned_zone)

    changes: list[str] = []
    if data.full_name and data.full_name != user.full_name:
        user.full_name = " ".join(data.full_name.split())
        changes.append("full_name")
    if "email" in fields and data.email != user.email:
        if data.email and db.scalar(
            select(User.id).where(User.email == data.email, User.id != user.id)
        ):
            raise HTTPException(409, "Another account already uses this email.")
        user.email = data.email
        changes.append("email")
    if data.preferred_language and data.preferred_language != user.preferred_language:
        user.preferred_language = data.preferred_language
        changes.append("preferred_language")
    if data.roles is not None:
        changes += _apply_roles(db, user, set(data.roles), data)
        db.flush()
    changes += _apply_role_fields(user, data, fields)
    if data.password:
        user.password_hash = hash_password(data.password)
        changes.append("password_reset")
    if data.is_active is not None and data.is_active != user.is_active:
        user.is_active = data.is_active
        changes.append("activated" if data.is_active else "deactivated")
    if data.password or data.is_active is False:
        # End every session: the person must log in again (or can't, if deactivated)
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
    if changes:
        audit_service.record(
            db,
            actor_id=admin.id,
            action="user.updated",
            entity_type="user",
            entity_id=user.id,
            details={"changes": changes},
        )
    db.commit()
    return _user_out(load_user_with_roles(db, user.id))


# --------------------------------------------------------------------------
# Audit log
# --------------------------------------------------------------------------
@router.get("/audit-logs", response_model=AuditLogPage, summary="Audit log (newest first)")
def audit_logs(
    action: str | None = Query(None, description="exact action, or a prefix ending in '.'"),
    actor_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    conditions = []
    if action:
        conditions.append(
            AuditLog.action.startswith(action)
            if action.endswith(".")
            else AuditLog.action == action
        )
    if actor_id:
        conditions.append(AuditLog.actor_id == actor_id)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)
    if date_from:
        conditions.append(AuditLog.created_at >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to:
        conditions.append(
            AuditLog.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        )
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id)
        .limit(limit)
        .offset(offset)
    ).all()
    items = []
    for entry, name in rows:
        out = AuditLogOut.model_validate(entry)
        out.actor_name = name if entry.actor_id else "System"
        items.append(out)
    return AuditLogPage(items=items, total=total, limit=limit, offset=offset)


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
@router.get("/settings", response_model=list[SettingOut], summary="System settings")
def list_settings(_: User = Depends(admin_only), db: Session = Depends(get_db)) -> list[SettingOut]:
    setting_service.ensure_defaults(db)
    db.commit()
    return [
        SettingOut.model_validate(s)
        for s in db.scalars(select(SystemSetting).order_by(SystemSetting.key))
    ]


@router.patch(
    "/settings/{key}",
    response_model=SettingOut,
    summary="Change a setting (linkage settings trigger a recompute)",
)
def update_setting(
    key: str,
    body: SettingUpdate,
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> SettingOut:
    setting_service.ensure_defaults(db)
    setting = db.get(SystemSetting, key)
    if setting is None:
        raise HTTPException(404, "Unknown setting.")
    try:
        value = settings_rules.validate(key, body.value)
    except settings_rules.SettingError as exc:
        raise HTTPException(422, str(exc)) from None
    old = setting.value
    setting.value = value
    setting.updated_by = admin.id
    setting.updated_at = datetime.now(UTC)
    audit_service.record(
        db,
        actor_id=admin.id,
        action="setting.updated",
        entity_type="system_setting",
        details={"key": key, "old": old, "new": value},
    )
    db.commit()
    if key.startswith("linkage."):
        linkage_engine.compute_safely(db)  # results always reflect current settings
    db.refresh(setting)
    return SettingOut.model_validate(setting)


# --------------------------------------------------------------------------
# Zones
# --------------------------------------------------------------------------
_REASSIGN_ZONES = text(
    """
    UPDATE pollution_reports r
       SET zone_code = (
             SELECT z.code FROM zones z
              WHERE z.is_active AND ST_DWithin(z.location, r.location, z.radius_km * 1000)
              ORDER BY ST_Distance(z.location, r.location)
              LIMIT 1)
    """
)


def _zone_out(db: Session, zone: Zone) -> ZoneAdminOut:
    out = ZoneAdminOut.model_validate(zone)
    out.reports = db.scalar(
        select(func.count())
        .select_from(PollutionReport)
        .where(PollutionReport.zone_code == zone.code)
    )
    out.verifiers = db.scalar(
        select(func.count()).select_from(Verifier).where(Verifier.assigned_zone == zone.code)
    )
    return out


@router.get("/zones", response_model=list[ZoneAdminOut], summary="All zones, including inactive")
def list_zones(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [_zone_out(db, z) for z in db.scalars(select(Zone).order_by(Zone.name))]


@router.post("/zones", response_model=ZoneAdminOut, status_code=201, summary="Create a zone")
def create_zone(data: ZoneIn, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    if db.get(Zone, data.code):
        raise HTTPException(409, "A zone with this code already exists.")
    zone = Zone(**data.model_dump())
    db.add(zone)
    db.flush()
    db.execute(_REASSIGN_ZONES)  # existing reports inside the circle join the zone
    audit_service.record(
        db, actor_id=admin.id, action="zone.created", entity_type="zone", details=data.model_dump()
    )
    db.commit()
    return _zone_out(db, zone)


@router.patch("/zones/{code}", response_model=ZoneAdminOut, summary="Update a zone")
def update_zone(
    code: str, data: ZoneUpdate, admin: User = Depends(admin_only), db: Session = Depends(get_db)
):
    zone = db.get(Zone, code)
    if zone is None:
        raise HTTPException(404, "Zone not found.")
    changes = data.model_dump(exclude_unset=True)
    for name, value in changes.items():
        setattr(zone, name, value)
    db.flush()
    db.execute(_REASSIGN_ZONES)
    audit_service.record(
        db,
        actor_id=admin.id,
        action="zone.updated",
        entity_type="zone",
        details={"code": code, **changes},
    )
    db.commit()
    db.refresh(zone)
    return _zone_out(db, zone)
