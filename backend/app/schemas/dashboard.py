"""Shapes for the agency dashboard (FR 4.1, FR 4.2, Module 7)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PollutionCategory


class ZoneCount(BaseModel):
    zone_code: str | None
    zone_name: str
    verified: int


class PayoutTotals(BaseModel):
    by_status: dict[str, int]
    paid_total: Decimal
    currency: str
    test_payments: int


class Overview(BaseModel):
    total: int
    by_status: dict[str, int]
    verified_by_category: dict[str, int]
    verified_last_7_days: int
    top_zones: list[ZoneCount]
    linkages_by_status: dict[str, int]
    payouts: PayoutTotals | None = None  # administrators only


class MapPoint(BaseModel):
    id: uuid.UUID
    latitude: float
    longitude: float
    category: PollutionCategory
    captured_at: datetime
    zone_code: str | None


class HeatPoint(BaseModel):
    latitude: float
    longitude: float
    weight: int


class Trends(BaseModel):
    weeks: list[date]
    reports: dict[str, list[int]]
    visits: dict[str, list[float | None]]
    suppressed: dict[str, list[bool]]
    small_count_threshold: int
    notice: str
