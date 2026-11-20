"""
Agency dashboard endpoints (Module 7; FR 4.1, FR 4.2; SRS 5.5).

GET /dashboard/overview   headline numbers
GET /dashboard/reports    VERIFIED reports as map points
GET /dashboard/heatmap    VERIFIED reports counted on a ~110 m grid
GET /dashboard/trends     weekly verified reports and clinic visits

Only VERIFIED reports appear on the map, heatmap and trends. Overview counts
of other statuses are totals only. Clinic visit totals below the small-count
threshold are hidden (D11). Reporter identity never appears.
"""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.deps import Role, require_roles
from app.db.session import get_db
from app.models import (
    ClinicVisitSummary,
    Facility,
    HealthLinkage,
    Payout,
    PollutionReport,
    User,
    Zone,
)
from app.models.enums import (
    ConditionCategory,
    LinkageStatus,
    PayoutProvider,
    PayoutStatus,
    PollutionCategory,
    ReportStatus,
)
from app.schemas.dashboard import HeatPoint, MapPoint, Overview, PayoutTotals, Trends, ZoneCount
from app.services import linkage_engine, setting_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
analysts = require_roles(Role.AGENCY_STAFF, Role.ADMINISTRATOR)

MAX_POINTS = 5000


def _start(d: date | None):
    return datetime.combine(d, time.min, tzinfo=UTC) if d else None


def _end(d: date | None):
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=UTC) if d else None


def _report_filters(date_from, date_to, zone, category) -> list:
    conditions = []
    if date_from:
        conditions.append(PollutionReport.captured_at >= _start(date_from))
    if date_to:
        conditions.append(PollutionReport.captured_at < _end(date_to))
    if zone:
        conditions.append(
            PollutionReport.zone_code.is_(None)
            if zone == "UNASSIGNED"
            else PollutionReport.zone_code == zone
        )
    if category:
        conditions.append(PollutionReport.category == category)
    return conditions


@router.get("/overview", response_model=Overview, summary="Headline statistics")
def overview(
    date_from: date | None = None,
    date_to: date | None = None,
    zone: str | None = None,
    user: User = Depends(analysts),
    db: Session = Depends(get_db),
) -> Overview:
    filters = _report_filters(date_from, date_to, zone, None)
    by_status = {s.value: 0 for s in ReportStatus}
    for status, n in db.execute(
        select(PollutionReport.status, func.count())
        .where(*filters)
        .group_by(PollutionReport.status)
    ):
        by_status[status.value] = n

    verified = [*filters, PollutionReport.status == ReportStatus.VERIFIED]
    by_category = {c.value: 0 for c in PollutionCategory}
    for category, n in db.execute(
        select(PollutionReport.category, func.count())
        .where(*verified)
        .group_by(PollutionReport.category)
    ):
        by_category[category.value] = n

    week_ago = datetime.now(UTC) - timedelta(days=7)
    recent = db.scalar(
        select(func.count()).where(*verified, PollutionReport.captured_at >= week_ago)
    )

    names = dict(db.execute(select(Zone.code, Zone.name)).all())
    top = [
        ZoneCount(
            zone_code=code, zone_name=names.get(code, code) if code else "Unassigned", verified=n
        )
        for code, n in db.execute(
            select(PollutionReport.zone_code, func.count())
            .where(*verified)
            .group_by(PollutionReport.zone_code)
            .order_by(func.count().desc())
            .limit(5)
        )
    ]

    linkages = {s.value: 0 for s in LinkageStatus}
    for status, n in db.execute(
        select(HealthLinkage.status, func.count())
        .join(PollutionReport, PollutionReport.id == HealthLinkage.report_id)
        .where(*filters)
        .group_by(HealthLinkage.status)
    ):
        linkages[status.value] = n

    payouts = None
    if Role.ADMINISTRATOR.value in user.roles:
        counts = {s.value: 0 for s in PayoutStatus}
        for status, n in db.execute(select(Payout.status, func.count()).group_by(Payout.status)):
            counts[status.value] = n
        paid = db.scalar(
            select(func.coalesce(func.sum(Payout.amount), 0)).where(
                Payout.status == PayoutStatus.SUCCESS, Payout.provider != PayoutProvider.MOCK
            )
        )
        tests = db.scalar(select(func.count()).where(Payout.provider == PayoutProvider.MOCK))
        payouts = PayoutTotals(
            by_status=counts,
            paid_total=Decimal(paid),
            currency=str(setting_service.get(db, "payout.currency", "KES")),
            test_payments=tests,
        )

    return Overview(
        total=sum(by_status.values()),
        by_status=by_status,
        verified_by_category=by_category,
        verified_last_7_days=recent,
        top_zones=top,
        linkages_by_status=linkages,
        payouts=payouts,
    )


@router.get("/reports", response_model=list[MapPoint], summary="Verified reports for the map")
def map_points(
    date_from: date | None = None,
    date_to: date | None = None,
    zone: str | None = None,
    category: PollutionCategory | None = None,
    _: User = Depends(analysts),
    db: Session = Depends(get_db),
) -> list[MapPoint]:
    rows = db.scalars(
        select(PollutionReport)
        .where(
            PollutionReport.status == ReportStatus.VERIFIED,
            *_report_filters(date_from, date_to, zone, category),
        )
        .order_by(PollutionReport.captured_at.desc())
        .limit(MAX_POINTS)
    )
    return [MapPoint.model_validate(r, from_attributes=True) for r in rows]


@router.get("/heatmap", response_model=list[HeatPoint], summary="Verified report density")
def heatmap(
    date_from: date | None = None,
    date_to: date | None = None,
    zone: str | None = None,
    category: PollutionCategory | None = None,
    _: User = Depends(analysts),
    db: Session = Depends(get_db),
) -> list[HeatPoint]:
    lat = func.round(func.cast(PollutionReport.latitude, _numeric()), 3)
    lng = func.round(func.cast(PollutionReport.longitude, _numeric()), 3)
    rows = db.execute(
        select(lat, lng, func.count())
        .where(
            PollutionReport.status == ReportStatus.VERIFIED,
            *_report_filters(date_from, date_to, zone, category),
        )
        .group_by(lat, lng)
    )
    return [HeatPoint(latitude=float(a), longitude=float(b), weight=n) for a, b, n in rows]


def _numeric():
    from sqlalchemy import Numeric

    return Numeric(10, 6)


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


_FACILITIES_IN_ZONE = text(
    """
    SELECT f.id FROM facilities f JOIN zones z ON z.code = :zone
     WHERE ST_DWithin(f.location, z.location, z.radius_km * 1000)
    """
)


@router.get("/trends", response_model=Trends, summary="Weekly reports and clinic visits")
def trends(
    date_from: date | None = Query(None, description="default: 16 weeks ago"),
    date_to: date | None = Query(None, description="default: today"),
    zone: str | None = Query(None, description="reports in this zone; clinics inside its circle"),
    area_code: str | None = Query(None, description="clinics in this facility area"),
    category: PollutionCategory | None = None,
    condition: ConditionCategory | None = None,
    _: User = Depends(analysts),
    db: Session = Depends(get_db),
) -> Trends:
    today = datetime.now(UTC).date()
    end = date_to or today
    start = date_from or (end - timedelta(weeks=15))
    weeks: list[date] = []
    week = _monday(start)
    while week <= end:
        weeks.append(week)
        week += timedelta(weeks=1)
    index = {w: i for i, w in enumerate(weeks)}

    report_series: dict[str, list[int]] = {
        c.value: [0] * len(weeks) for c in PollutionCategory if category in (None, c)
    }
    for captured_at, cat in db.execute(
        select(PollutionReport.captured_at, PollutionReport.category).where(
            PollutionReport.status == ReportStatus.VERIFIED,
            *_report_filters(start, end, zone if zone != "UNASSIGNED" else None, category),
        )
    ):
        i = index.get(_monday(captured_at.date()))
        if i is not None:
            report_series[cat.value][i] += 1

    visit_filters = [
        ClinicVisitSummary.period_end >= weeks[0],
        ClinicVisitSummary.period_start <= end,
    ]
    if condition:
        visit_filters.append(ClinicVisitSummary.condition_category == condition)
    if area_code:
        visit_filters.append(Facility.area_code == area_code)
    if zone and zone not in ("ALL", "UNASSIGNED"):
        ids = [row[0] for row in db.execute(_FACILITIES_IN_ZONE, {"zone": zone})]
        visit_filters.append(Facility.id.in_(ids))

    # Spread each period's visits evenly over its days, then add up by week,
    # so weekly and monthly clinic data can be shown on the same chart
    totals: dict[str, list[float]] = defaultdict(lambda: [0.0] * len(weeks))
    for s in db.scalars(
        select(ClinicVisitSummary)
        .join(Facility, Facility.id == ClinicVisitSummary.facility_id)
        .where(*visit_filters)
    ):
        days = (s.period_end - s.period_start).days + 1
        per_day = s.visit_count / days
        series = totals[s.condition_category.value]
        for offset in range(days):
            i = index.get(_monday(s.period_start + timedelta(days=offset)))
            if i is not None:
                series[i] += per_day

    threshold = int(setting_service.get(db, "dashboard.small_count_threshold", 5))
    visits: dict[str, list[float | None]] = {}
    suppressed: dict[str, list[bool]] = {}
    for cond, values in sorted(totals.items()):
        rounded = [round(v, 1) for v in values]
        hidden = [0 < v < threshold for v in rounded]
        visits[cond] = [None if h else v for v, h in zip(rounded, hidden, strict=True)]
        suppressed[cond] = hidden

    return Trends(
        weeks=weeks,
        reports=report_series,
        visits=visits,
        suppressed=suppressed,
        small_count_threshold=threshold,
        notice=linkage_engine.ASSOCIATION_NOTICE,
    )
