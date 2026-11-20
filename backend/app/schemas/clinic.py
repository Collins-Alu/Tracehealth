"""Shapes for clinic data, facilities and health linkages."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConditionCategory, ImportBatchStatus, LinkageStatus, PollutionCategory


class ImportProblem(BaseModel):
    row: int | None
    field: str | None
    message: str


class ImportBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: ImportBatchStatus
    row_count: int
    summary: dict | None
    errors: list[ImportProblem] | None
    created_at: datetime
    imported_by_name: str | None = None


class LinkageRunOut(BaseModel):
    reports_considered: int
    linkages: int
    by_status: dict[str, int]
    params: dict


class ImportResult(BaseModel):
    batch: ImportBatchOut
    linkage: LinkageRunOut | None = Field(
        None, description="Health linkages recomputed after an accepted import"
    )


class FacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_code: str
    name: str
    area_code: str
    latitude: float
    longitude: float
    summaries: int = 0
    latest_period_end: date | None = None


class VisitSummaryOut(BaseModel):
    id: uuid.UUID
    facility_code: str
    facility_name: str
    area_code: str
    condition_category: ConditionCategory
    period_start: date
    period_end: date
    visit_count: int | None = Field(description="null when suppressed (small count)")
    suppressed: bool = False


class VisitSummaryPage(BaseModel):
    items: list[VisitSummaryOut]
    total: int
    limit: int
    offset: int
    small_count_threshold: int


class LinkageOut(BaseModel):
    id: uuid.UUID
    status: LinkageStatus
    insufficient_reason: str | None
    condition_category: ConditionCategory
    report_id: uuid.UUID
    report_category: PollutionCategory
    report_captured_at: datetime
    report_latitude: float
    report_longitude: float
    report_zone_code: str | None
    facility_id: uuid.UUID
    facility_code: str
    facility_name: str
    facility_area_code: str
    distance_km: float
    radius_km: float
    baseline_visits: int | None
    followup_visits: int | None
    baseline_days: int | None
    followup_days: int | None
    rate_ratio: float | None
    p_value: float | None
    correlation_score: float | None
    detected_at: datetime
    params_snapshot: dict


class LinkagePage(BaseModel):
    items: list[LinkageOut]
    total: int
    limit: int
    offset: int
    notice: str


class ClusterOut(BaseModel):
    """A facility where at least one verified report was followed by a rise
    in visits for a linked condition (a POTENTIAL illness cluster)."""

    facility_id: uuid.UUID
    facility_code: str
    facility_name: str
    area_code: str
    latitude: float
    longitude: float
    condition_category: ConditionCategory
    signal_reports: int
    pollution_categories: list[PollutionCategory]
    max_rate_ratio: float
    min_p_value: float
    latest_report_at: datetime


class LinkageTrendsOut(BaseModel):
    by_status: dict[str, int]
    by_condition: dict[str, dict[str, int]]
    clusters: list[ClusterOut]
    notice: str
