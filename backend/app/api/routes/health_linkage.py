"""
Health linkage endpoints (FR 3.2, FR 4.2).

POST /health-linkage/compute   recompute all linkages (administrators)
GET  /health-linkage           linkage results with their statistics
GET  /health-linkage/trends    counts by status/condition and potential clusters

Every response carries the notice that results are associations, not proof
of causation.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Role, require_roles
from app.db.session import get_db
from app.models import Facility, HealthLinkage, PollutionReport, User
from app.models.enums import ConditionCategory, LinkageStatus
from app.schemas.clinic import ClusterOut, LinkageOut, LinkagePage, LinkageRunOut, LinkageTrendsOut
from app.services import audit_service, linkage_engine

router = APIRouter(prefix="/health-linkage", tags=["Health linkage"])

admin_only = require_roles(Role.ADMINISTRATOR)
analysts = require_roles(Role.ADMINISTRATOR, Role.AGENCY_STAFF)


@router.post("/compute", response_model=LinkageRunOut, summary="Recompute all health linkages")
def compute(admin: User = Depends(admin_only), db: Session = Depends(get_db)) -> LinkageRunOut:
    run = linkage_engine.compute(db)
    audit_service.record(
        db,
        actor_id=admin.id,
        action="health_linkage.computed",
        entity_type="health_linkage",
        details={"linkages": run.linkages, "by_status": run.by_status},
    )
    db.commit()
    return LinkageRunOut(**run.__dict__)


@router.get("", response_model=LinkagePage, summary="Health-linkage results")
def list_linkages(
    status: LinkageStatus | None = None,
    condition: ConditionCategory | None = None,
    zone: str | None = Query(None, description="report zone code"),
    area_code: str | None = Query(None, description="facility area code"),
    report_id: uuid.UUID | None = Query(None, description="one report's linkages"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(analysts),
    db: Session = Depends(get_db),
) -> LinkagePage:
    conditions = []
    if status:
        conditions.append(HealthLinkage.status == status)
    if condition:
        conditions.append(HealthLinkage.condition_category == condition)
    if zone:
        conditions.append(PollutionReport.zone_code == zone)
    if area_code:
        conditions.append(Facility.area_code == area_code)
    if report_id:
        conditions.append(HealthLinkage.report_id == report_id)
    base = (
        select(HealthLinkage, PollutionReport, Facility)
        .join(PollutionReport, PollutionReport.id == HealthLinkage.report_id)
        .join(Facility, Facility.id == HealthLinkage.facility_id)
        .where(*conditions)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    # Signals first, strongest evidence first
    order = (
        (HealthLinkage.status != LinkageStatus.SIGNAL),
        HealthLinkage.p_value.asc().nulls_last(),
        PollutionReport.captured_at.desc(),
    )
    rows = db.execute(base.order_by(*order).limit(limit).offset(offset)).all()
    items = [
        LinkageOut(
            id=link.id,
            status=link.status,
            insufficient_reason=link.insufficient_reason,
            condition_category=link.condition_category,
            report_id=r.id,
            report_category=r.category,
            report_captured_at=r.captured_at,
            report_latitude=r.latitude,
            report_longitude=r.longitude,
            report_zone_code=r.zone_code,
            facility_id=f.id,
            facility_code=f.external_code,
            facility_name=f.name,
            facility_area_code=f.area_code,
            distance_km=link.distance_km,
            radius_km=float(link.radius_km),
            baseline_visits=link.baseline_visits,
            followup_visits=link.followup_visits,
            baseline_days=link.baseline_days,
            followup_days=link.followup_days,
            rate_ratio=link.rate_ratio,
            p_value=link.p_value,
            correlation_score=link.correlation_score,
            detected_at=link.detected_at,
            params_snapshot=link.params_snapshot,
        )
        for link, r, f in rows
    ]
    return LinkagePage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        notice=linkage_engine.ASSOCIATION_NOTICE,
    )


@router.get("/trends", response_model=LinkageTrendsOut, summary="Linkage summary and clusters")
def trends(_: User = Depends(analysts), db: Session = Depends(get_db)) -> LinkageTrendsOut:
    by_status = {s.value: 0 for s in LinkageStatus}
    by_condition: dict[str, dict[str, int]] = {}
    for status, condition, count in db.execute(
        select(HealthLinkage.status, HealthLinkage.condition_category, func.count()).group_by(
            HealthLinkage.status, HealthLinkage.condition_category
        )
    ):
        by_status[status.value] += count
        by_condition.setdefault(condition.value, {s.value: 0 for s in LinkageStatus})[
            status.value
        ] = count

    clusters = []
    for row in db.execute(
        select(
            Facility,
            HealthLinkage.condition_category,
            func.count(func.distinct(HealthLinkage.report_id)),
            func.array_agg(func.distinct(PollutionReport.category)),
            func.max(HealthLinkage.rate_ratio),
            func.min(HealthLinkage.p_value),
            func.max(PollutionReport.captured_at),
        )
        .join(Facility, Facility.id == HealthLinkage.facility_id)
        .join(PollutionReport, PollutionReport.id == HealthLinkage.report_id)
        .where(HealthLinkage.status == LinkageStatus.SIGNAL)
        .group_by(Facility.id, HealthLinkage.condition_category)
        .order_by(func.min(HealthLinkage.p_value))
    ):
        f, condition, reports, categories, max_rr, min_p, latest = row
        clusters.append(
            ClusterOut(
                facility_id=f.id,
                facility_code=f.external_code,
                facility_name=f.name,
                area_code=f.area_code,
                latitude=f.latitude,
                longitude=f.longitude,
                condition_category=condition,
                signal_reports=reports,
                pollution_categories=sorted(categories),
                max_rate_ratio=max_rr,
                min_p_value=min_p,
                latest_report_at=latest,
            )
        )
    return LinkageTrendsOut(
        by_status=by_status,
        by_condition=by_condition,
        clusters=clusters,
        notice=linkage_engine.ASSOCIATION_NOTICE,
    )
