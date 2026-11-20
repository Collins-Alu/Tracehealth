"""Shapes for the in-app inbox and push token registration."""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EXPO_TOKEN = re.compile(r"^Expo(nent)?PushToken\[[A-Za-z0-9_\-]{10,200}\]$")


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str
    related_report_id: uuid.UUID | None
    created_at: datetime
    read_at: datetime | None


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread: int
    limit: int
    offset: int


class PushTokenIn(BaseModel):
    token: str = Field(max_length=255, description="Expo push token from the mobile app")
    platform: Literal["android", "ios"]

    @field_validator("token")
    @classmethod
    def _expo_format(cls, v: str) -> str:
        if not _EXPO_TOKEN.match(v.strip()):
            raise ValueError("Not an Expo push token (expected ExponentPushToken[...]).")
        return v.strip()


class PushTokenDelete(BaseModel):
    token: str = Field(max_length=255)
