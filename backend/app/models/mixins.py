import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

def enum_column(enum_cls:type[StrEnum], name: str) -> Enum:
    return Enum(
            enum_cls,
            name=name,
            native_enum=False,
            create_constraint=True,
            length=max(len(m.value) for m in enum_cls),
            values_collable=lambda e: [m.value for m in e],
            validate_strings=True,
            )

class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
            UUID(as_uuid=True)
            primary_key=True,
            default=uuid.uuid4,
            server_default=text("gen_random_uuid()"),
            )

class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            nullable=False
            server_default=func.now(),
            onupdate=func.now(),
            )

