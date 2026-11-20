"""
Health-linkage engine (FR 3.2, UML B.5 steps 4-6).

For every VERIFIED pollution report it asks: in clinics near this report, did
visits for the health conditions linked to this kind of pollution go UP after
the report, compared with the weeks before it?

Method (full explanation in docs/health-linkage-method.md):

  1. Facilities within `radius_km` of the report (PostGIS distance).
  2. Conditions to check come from `category_mapping` (e.g. open burning ->
     respiratory).
  3. Baseline: clinic periods that END in the `baseline_weeks` before the
     report date (and before it). Follow-up: periods that START on or after
     the report date, within `followup_weeks`. Assigning whole periods this
     way means a weekly count is never cut in half by a window edge. The
     period containing the report date mixes "before" and "after" and is
     left out of both.
  4. Rates are visits per day of data, so weekly and monthly counts mix fairly.
     rate_ratio = follow-up rate / baseline rate.
  5. p_value: exact one-sided Poisson rate test (linkage_stats).
  6. Status:
       INSUFFICIENT_DATA  less than half of either window has clinic data, or
                          fewer than `min_baseline_visits` baseline visits.
                          No statistics are produced (none are invented).
       SIGNAL             rate_ratio > 1 and p_value < `p_value_threshold`
       NO_SIGNAL          otherwise
  7. correlation_score (descriptive only, never decides the status):
     Spearman correlation, across all reporting periods in both windows
     (including the one containing the report date), between verified
     reports of that category near the facility and that facility's visits
     per day for the condition.

Results are STATISTICAL ASSOCIATIONS, never proof that pollution caused
illness. Every row stores the parameters used (params_snapshot) and the clinic
summaries it was based on (HealthLinkageEvidence), so it can be reproduced.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models import (
    ClinicVisitSummary,
    HealthLinkage,
    HealthLinkageEvidence,
    PollutionReport,
)
from app.models.enums import ConditionCategory, EvidenceWindow, LinkageStatus, ReportStatus
from app.services import setting_service
from app.services.linkage_stats import poisson_rate_test_greater, spearman

log = logging.getLogger("tracehealth.linkage")

MIN_COVERAGE = 0.5  # at least half of each window must have clinic data

DEFAULT_MAPPING = {
    "OPEN_BURNING": ["RESPIRATORY"],
    "ILLEGAL_DUMPING": ["SKIN", "DIARRHOEAL"],
    "BLOCKED_DRAINAGE": ["DIARRHOEAL", "MALARIA"],
    "MEDICAL_WASTE": ["INJURY", "INFECTION"],
    "OTHER": [],
}

ASSOCIATION_NOTICE = (
    "A statistical association between verified pollution reports and clinic visits. "
    "It is not evidence that the pollution caused the illness."
)


@dataclass(frozen=True)
class LinkageParams:
    radius_km: float
    baseline_weeks: int
    followup_weeks: int
    min_baseline_visits: int
    p_value_threshold: float
    category_mapping: dict[str, list[str]]
    min_coverage: float = MIN_COVERAGE

    @classmethod
    def from_settings(cls, db: Session) -> "LinkageParams":
        get = setting_service.get
        return cls(
            radius_km=float(get(db, "linkage.radius_km", 3)),
            baseline_weeks=int(get(db, "linkage.baseline_weeks", 8)),
            followup_weeks=int(get(db, "linkage.followup_weeks", 4)),
            min_baseline_visits=int(get(db, "linkage.min_baseline_visits", 10)),
            p_value_threshold=float(get(db, "linkage.p_value_threshold", 0.05)),
            category_mapping=get(db, "linkage.category_mapping", DEFAULT_MAPPING),
        )

    def snapshot(self) -> dict:
        return {
            "method": "poisson_rate_ratio_v1",
            "radius_km": self.radius_km,
            "baseline_weeks": self.baseline_weeks,
            "followup_weeks": self.followup_weeks,
            "min_baseline_visits": self.min_baseline_visits,
            "p_value_threshold": self.p_value_threshold,
            "min_coverage": self.min_coverage,
        }


@dataclass
class RunSummary:
    reports_considered: int = 0
    linkages: int = 0
    by_status: dict[str, int] = field(default_factory=lambda: {s.value: 0 for s in LinkageStatus})
    params: dict = field(default_factory=dict)


_FACILITIES_NEAR = text(
    """
    SELECT f.id, ST_Distance(f.location, r.location) / 1000.0 AS distance_km
      FROM facilities f, pollution_reports r
     WHERE r.id = :report_id
       AND ST_DWithin(f.location, r.location, :radius_m)
     ORDER BY distance_km
    """
)

_REPORT_DATES_NEAR_FACILITY = text(
    """
    SELECT r.captured_at
      FROM pollution_reports r, facilities f
     WHERE f.id = :facility_id
       AND r.status = 'VERIFIED'
       AND r.category = :category
       AND ST_DWithin(r.location, f.location, :radius_m)
       AND r.captured_at >= :start AND r.captured_at <= :end
    """
)


def _days(s: ClinicVisitSummary) -> int:
    return (s.period_end - s.period_start).days + 1


def _in_baseline(s: ClinicVisitSummary, baseline_start: date, report_day: date) -> bool:
    return baseline_start <= s.period_end < report_day


def _in_followup(s: ClinicVisitSummary, report_day: date, followup_end: date) -> bool:
    return report_day <= s.period_start < followup_end


def _evaluate(
    db: Session,
    report: PollutionReport,
    facility_id: uuid.UUID,
    distance_km: float,
    condition: ConditionCategory,
    params: LinkageParams,
) -> tuple[HealthLinkage, list[tuple[ClinicVisitSummary, EvidenceWindow]]]:
    report_day = report.captured_at.date()
    baseline_start = report_day - timedelta(weeks=params.baseline_weeks)
    followup_end = report_day + timedelta(weeks=params.followup_weeks)

    summaries = list(
        db.scalars(
            select(ClinicVisitSummary)
            .where(
                ClinicVisitSummary.facility_id == facility_id,
                ClinicVisitSummary.condition_category == condition,
                ClinicVisitSummary.period_end >= baseline_start,
                ClinicVisitSummary.period_start < followup_end,
            )
            .order_by(ClinicVisitSummary.period_start)
        )
    )
    baseline = [s for s in summaries if _in_baseline(s, baseline_start, report_day)]
    followup = [s for s in summaries if _in_followup(s, report_day, followup_end)]
    b_days, f_days = sum(map(_days, baseline)), sum(map(_days, followup))
    b_visits = sum(s.visit_count for s in baseline)
    f_visits = sum(s.visit_count for s in followup)

    linkage = HealthLinkage(
        id=uuid.uuid4(),
        report_id=report.id,
        facility_id=facility_id,
        condition_category=condition,
        radius_km=params.radius_km,
        distance_km=round(distance_km, 3),
        baseline_visits=b_visits,
        followup_visits=f_visits,
        baseline_days=b_days,
        followup_days=f_days,
        params_snapshot=params.snapshot(),
    )
    evidence = [(s, EvidenceWindow.BASELINE) for s in baseline] + [
        (s, EvidenceWindow.FOLLOWUP) for s in followup
    ]

    reason = None
    if b_days < params.min_coverage * params.baseline_weeks * 7:
        reason = "baseline_coverage"
    elif f_days < params.min_coverage * params.followup_weeks * 7:
        reason = "followup_coverage"
    elif b_visits < params.min_baseline_visits:
        reason = "baseline_visits_below_minimum"
    if reason:
        linkage.status = LinkageStatus.INSUFFICIENT_DATA
        linkage.insufficient_reason = reason
        return linkage, evidence

    rate_ratio = (f_visits / f_days) / (b_visits / b_days)
    p_value = poisson_rate_test_greater(f_visits, f_days, b_visits, b_days)
    linkage.rate_ratio = round(rate_ratio, 4)
    linkage.p_value = p_value
    linkage.status = (
        LinkageStatus.SIGNAL
        if rate_ratio > 1 and p_value < params.p_value_threshold
        else LinkageStatus.NO_SIGNAL
    )

    # Correlation across ALL periods in the two windows, including the one
    # containing the report date (left out of the rate test, but it is where
    # the report itself falls): reports nearby vs visits per day
    periods = summaries
    report_times = [
        row.captured_at
        for row in db.execute(
            _REPORT_DATES_NEAR_FACILITY,
            {
                "facility_id": facility_id,
                "category": report.category.value,
                "radius_m": params.radius_km * 1000,
                "start": min(p.period_start for p in summaries),
                "end": max(p.period_end for p in summaries) + timedelta(days=1),
            },
        )
    ]
    reports_per_period = [
        sum(1 for t in report_times if s.period_start <= t.date() <= s.period_end) for s in periods
    ]
    visit_rates = [s.visit_count / _days(s) for s in periods]
    score = spearman([float(c) for c in reports_per_period], visit_rates)
    linkage.correlation_score = round(score, 4) if score is not None else None
    return linkage, evidence


def compute(db: Session, report_ids: list[uuid.UUID] | None = None) -> RunSummary:
    """Recompute linkages for the given reports (all verified reports if None).
    Old results for those reports are replaced. Commits."""
    params = LinkageParams.from_settings(db)
    summary = RunSummary(params=params.snapshot())

    query = select(PollutionReport).where(PollutionReport.status == ReportStatus.VERIFIED)
    if report_ids is not None:
        query = query.where(PollutionReport.id.in_(report_ids))
    reports = list(db.scalars(query))

    stale = delete(HealthLinkage)
    if report_ids is not None:
        stale = stale.where(HealthLinkage.report_id.in_(report_ids))
    db.execute(stale)

    for report in reports:
        conditions = params.category_mapping.get(report.category.value, [])
        if not conditions:
            continue
        summary.reports_considered += 1
        nearby = db.execute(
            _FACILITIES_NEAR, {"report_id": report.id, "radius_m": params.radius_km * 1000}
        ).all()
        for facility_id, distance_km in nearby:
            for condition_name in conditions:
                linkage, evidence = _evaluate(
                    db, report, facility_id, distance_km, ConditionCategory(condition_name), params
                )
                db.add(linkage)
                db.flush()
                db.add_all(
                    HealthLinkageEvidence(
                        linkage_id=linkage.id, summary_id=s.id, evidence_window=window
                    )
                    for s, window in evidence
                )
                summary.linkages += 1
                summary.by_status[linkage.status.value] += 1
    db.commit()
    log.info("Linkage run: %s", summary)
    return summary


def compute_safely(db: Session, report_ids: list[uuid.UUID] | None = None) -> RunSummary | None:
    """Like compute(), but never raises: used right after a verification or
    import, which must not fail because of a linkage problem."""
    try:
        return compute(db, report_ids)
    except Exception:
        db.rollback()
        log.exception("Health-linkage computation failed")
        return None
