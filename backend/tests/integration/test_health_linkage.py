"""FR 3.2: the health-linkage engine finds rises in nearby clinic visits after
verified reports, and says INSUFFICIENT_DATA instead of inventing results."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import HealthLinkage, HealthLinkageEvidence
from app.models.enums import (
    ConditionCategory,
    LinkageStatus,
    PollutionCategory,
    VerificationDecision,
)
from app.services import linkage_engine
from tests.conftest import auth_headers
from tests.factories import (
    decide,
    make_facility,
    make_import_batch,
    make_report,
    make_summary,
    make_user,
)

REPORT_DAY = date(2026, 8, 5)  # a Wednesday


def weekly(db, facility, batch, condition, counts_before, counts_after):
    """Weekly counts: len(counts_before) weeks before REPORT_DAY's week, then after."""
    report_monday = REPORT_DAY - timedelta(days=REPORT_DAY.weekday())
    for i, count in enumerate(reversed(counts_before)):
        start = report_monday - timedelta(weeks=i + 1)
        make_summary(
            db,
            facility,
            batch,
            condition_category=condition,
            period_start=start,
            period_end=start + timedelta(days=6),
            visit_count=count,
        )
    for i, count in enumerate(counts_after):
        start = report_monday + timedelta(weeks=i + 1)
        make_summary(
            db,
            facility,
            batch,
            condition_category=condition,
            period_start=start,
            period_end=start + timedelta(days=6),
            visit_count=count,
        )


@pytest.fixture
def setup(db):
    reporter = make_user(db, "REPORTER")
    verifier = make_user(db, "VERIFIER")
    admin = make_user(db, "ADMINISTRATOR")
    facility = make_facility(db, latitude=-1.2550, longitude=36.8980)
    batch = make_import_batch(db, admin)

    def verified_report(category=PollutionCategory.OPEN_BURNING, lat=-1.2600, day=REPORT_DAY):
        report = make_report(
            db,
            reporter,
            latitude=lat,
            longitude=36.8980,
            category=category,
            captured_at=datetime(day.year, day.month, day.day, 10, tzinfo=UTC),
        )
        decide(db, report, verifier, VerificationDecision.VERIFIED)
        return report

    return {"facility": facility, "batch": batch, "report": verified_report, "admin": admin}


def only_linkage(db):
    return db.scalar(select(HealthLinkage))


def test_rise_after_report_is_a_signal(db, setup):
    weekly(
        db,
        setup["facility"],
        setup["batch"],
        ConditionCategory.RESPIRATORY,
        [18, 17, 19, 18, 20, 16, 18, 19],
        [34, 31, 30, 29],
    )
    setup["report"]()
    run = linkage_engine.compute(db)
    assert run.by_status["SIGNAL"] == 1
    link = only_linkage(db)
    assert link.status == LinkageStatus.SIGNAL
    assert link.baseline_visits == 145 and link.followup_visits == 124
    assert link.baseline_days == 56 and link.followup_days == 28
    assert link.rate_ratio == pytest.approx((124 / 28) / (145 / 56), rel=1e-3)
    assert link.p_value < 0.001
    assert 0.5 < link.distance_km < 0.6
    assert link.params_snapshot["radius_km"] == 3
    # Every summary used is recorded as evidence (8 baseline + 4 follow-up)
    assert db.scalar(select(func.count()).select_from(HealthLinkageEvidence)) == 12


def test_no_rise_is_no_signal(db, setup):
    weekly(
        db,
        setup["facility"],
        setup["batch"],
        ConditionCategory.RESPIRATORY,
        [18] * 8,
        [19, 17, 18, 18],
    )
    setup["report"]()
    linkage_engine.compute(db)
    link = only_linkage(db)
    assert link.status == LinkageStatus.NO_SIGNAL
    assert link.p_value > 0.05


def test_missing_clinic_data_gives_insufficient_data_without_statistics(db, setup):
    weekly(
        db, setup["facility"], setup["batch"], ConditionCategory.RESPIRATORY, [18] * 8, [30]
    )  # only 1 of 4 follow-up weeks
    setup["report"]()
    linkage_engine.compute(db)
    link = only_linkage(db)
    assert link.status == LinkageStatus.INSUFFICIENT_DATA
    assert link.insufficient_reason == "followup_coverage"
    assert link.rate_ratio is None and link.p_value is None


def test_too_few_baseline_visits_is_insufficient(db, setup):
    weekly(
        db, setup["facility"], setup["batch"], ConditionCategory.RESPIRATORY, [1] * 8, [5, 5, 5, 5]
    )
    setup["report"]()
    linkage_engine.compute(db)
    assert only_linkage(db).insufficient_reason == "baseline_visits_below_minimum"


def test_only_mapped_conditions_and_nearby_facilities_are_checked(db, setup):
    weekly(db, setup["facility"], setup["batch"], ConditionCategory.SKIN, [18] * 8, [40] * 4)
    setup["report"]()  # open burning -> respiratory only, not skin
    far = make_facility(db, latitude=-0.0917, longitude=34.7680)  # ~300 km away
    weekly(db, far, setup["batch"], ConditionCategory.RESPIRATORY, [18] * 8, [40] * 4)
    linkage_engine.compute(db)
    links = list(db.scalars(select(HealthLinkage)))
    assert len(links) == 1
    assert links[0].facility_id == setup["facility"].id
    assert links[0].status == LinkageStatus.INSUFFICIENT_DATA  # no respiratory data there


def test_unverified_reports_are_never_linked(db, setup):
    reporter = make_user(db, "REPORTER")
    make_report(db, reporter, latitude=-1.26, longitude=36.898)  # PENDING
    weekly(db, setup["facility"], setup["batch"], ConditionCategory.RESPIRATORY, [18] * 8, [40] * 4)
    assert linkage_engine.compute(db).linkages == 0


def test_recompute_replaces_old_results(db, setup):
    weekly(db, setup["facility"], setup["batch"], ConditionCategory.RESPIRATORY, [18] * 8, [40] * 4)
    setup["report"]()
    linkage_engine.compute(db)
    linkage_engine.compute(db)
    assert db.scalar(select(func.count()).select_from(HealthLinkage)) == 1


def test_verifying_a_report_links_it_immediately(client, db, setup):
    weekly(db, setup["facility"], setup["batch"], ConditionCategory.RESPIRATORY, [18] * 8, [40] * 4)
    reporter = make_user(db, "REPORTER")
    report = make_report(
        db,
        reporter,
        latitude=-1.26,
        longitude=36.898,
        captured_at=datetime(2026, 8, 5, 10, tzinfo=UTC),
    )
    r = client.post(f"/reports/{report.id}/verify", headers=auth_headers(make_user(db, "VERIFIER")))
    assert r.status_code == 200
    assert only_linkage(db).status == LinkageStatus.SIGNAL


def test_linkage_endpoints(client, db, setup):
    weekly(db, setup["facility"], setup["batch"], ConditionCategory.RESPIRATORY, [18] * 8, [40] * 4)
    first = setup["report"]()
    setup["report"](lat=-1.2560)  # second report, same facility
    staff = auth_headers(make_user(db, "AGENCY_STAFF"))
    admin = auth_headers(setup["admin"])

    run = client.post("/health-linkage/compute", headers=admin).json()
    assert run["by_status"]["SIGNAL"] == 2
    assert client.post("/health-linkage/compute", headers=staff).status_code == 403

    page = client.get("/health-linkage?status=SIGNAL", headers=staff).json()
    assert page["total"] == 2
    assert "not evidence that the pollution caused" in page["notice"]
    assert page["items"][0]["facility_code"] == setup["facility"].external_code

    one = client.get(f"/health-linkage?report_id={first.id}", headers=staff).json()
    assert one["total"] == 1 and one["items"][0]["report_id"] == str(first.id)

    trends = client.get("/health-linkage/trends", headers=staff).json()
    assert trends["by_status"]["SIGNAL"] == 2
    assert trends["by_condition"]["RESPIRATORY"]["SIGNAL"] == 2
    [cluster] = trends["clusters"]  # two reports, one facility -> one cluster
    assert cluster["signal_reports"] == 2
    assert cluster["pollution_categories"] == ["OPEN_BURNING"]
    assert (
        client.get("/health-linkage", headers=auth_headers(make_user(db, "REPORTER"))).status_code
        == 403
    )
