"""Read administrator-editable settings from the system_settings table."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting


def get(db: Session, key: str, default: Any = None) -> Any:
    value = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    return default if value is None else value
