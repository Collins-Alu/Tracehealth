"""
User and role profiles (UML B.2a: User, Reporter, Verifier, AgencyStaff,
Administrator).

Design decision (approved): every person has one row in `users` holding the
common identity and login data. Each role is a separate profile table keyed by
the same user id (a 1-to-0..1 relationship). This keeps the UML
generalization (each role "is a" User) while letting one person hold more than
one role, e.g. a community verifier who also submits reports. That is exactly
the situation the "a reporter may not verify their own report" rule guards.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Language
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, enum_column

if TYPE_CHECKING:
    from app.models.report import PollutionReport


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Emails are stored lower-case so "A@x.com" and "a@x.com" can't both register
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_lowercase"),
        CheckConstraint("char_length(trim(full_name)) > 0", name="full_name_not_blank"),
    )

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    # Optional: many reporters have no email address (data minimisation)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[Language] = mapped_column(
        enum_column(Language, "language"),
        nullable=False,
        default=Language.EN,
        server_default=Language.EN.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    reporter_profile: Mapped["Reporter | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    verifier_profile: Mapped["Verifier | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    agency_staff_profile: Mapped["AgencyStaff | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    administrator_profile: Mapped["Administrator | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def roles(self) -> list[str]:
        """Role names held by this user, used for role-based access control."""
        roles = []
        if self.reporter_profile is not None:
            roles.append("REPORTER")
        if self.verifier_profile is not None:
            roles.append("VERIFIER")
        if self.agency_staff_profile is not None:
            roles.append("AGENCY_STAFF")
        if self.administrator_profile is not None:
            roles.append("ADMINISTRATOR")
        return roles


class Reporter(Base):
    __tablename__ = "reporters"
    __table_args__ = (
        # A payout number may only be stored once the reporter has consented
        CheckConstraint(
            "payout_phone IS NULL OR payout_consent_at IS NOT NULL",
            name="payout_phone_requires_consent",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    reputation_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    payout_phone: Mapped[str | None] = mapped_column(String(20))
    payout_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="reporter_profile")
    reports: Mapped[list["PollutionReport"]] = relationship(back_populates="reporter")


class Verifier(Base):
    __tablename__ = "verifiers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # NULL means the verifier is not restricted to a single zone
    assigned_zone: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship(back_populates="verifier_profile")


class AgencyStaff(Base):
    __tablename__ = "agency_staff"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    agency_name: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str | None] = mapped_column(String(150))

    user: Mapped[User] = relationship(back_populates="agency_staff_profile")


class Administrator(Base):
    __tablename__ = "administrators"
    __table_args__ = (CheckConstraint("admin_level BETWEEN 1 AND 3", name="admin_level_range"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    admin_level: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )

    user: Mapped[User] = relationship(back_populates="administrator_profile")

