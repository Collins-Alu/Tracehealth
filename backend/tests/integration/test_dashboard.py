"""Module 7 / FR 4.1, FR 4.2: dashboard statistics, map, heatmap and trends."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.enums import ConditionCategory, VerificationDecision
from tests.conftest import auth_headers
from tests.factories import (
    decide,
    make_facility,
    make_import_batch,
    make_report,
    make_summary,
    make_user,
    make_zone,
)


@pytest.fixture
def data(db):
    make_zone(db, "DANDORA", latitude=-1.2550, longitude=36.8980, radius_km=3)
    reporter, verifier = make_user(db, "REPORTER"), make_user(db, "VERIFIER")
    now = datetime.now(UTC)
    made = []
    for category, status, zone in [
        ("OPEN_BURNING", VerificationDecision.VERIFIED, "DANDORA"),
        ("OPEN_BURNING", VerificationDecision.VERIFIED, "DANDORA"),
        ("ILLEGAL_DUMPING", VerificationDecision.VERIFIED, None),
        ("ILLEGAL_DUMPING", VerificationDecision.REJECTED, "DANDORA"),
        ("MEDICAL_WASTE", VerificationDecision.FLAGGED, "DANDORA"),
        ("OTHER", None, "DANDORA"),
    ]:
        r = make_report(
            db,
            reporter,
            latitude=-1.2551,
            longitude=36.8981,
            category=category,
            zone_code=zone,
            captured_at=now - timedelta(days=2),
        )
        if status:
            decide(db, r, verifier, status, reason=None if status == "VERIFIED" else "reason")
        made.append(r)
    return made


def test_overview_counts(client, db, data):
    staff = auth_headers(make_user(db, "AGENCY_STAFF"))
    o = client.get("/dashboard/overview", headers=staff).json()
    assert o["total"] == 6
    assert o["by_status"] == {"PENDING": 1, "VERIFIED": 3, "REJECTED": 1, "FLAGGED": 1}
    assert o["verified_by_category"]["OPEN_BURNING"] == 2
    assert o["verified_last_7_days"] == 3
    assert o["top_zones"][0] == {"zone_code": "DANDORA", "zone_name": "Zone DANDORA", "verified": 2}
    assert o["payouts"] is None  # payout figures are for administrators only
    admin = auth_headers(make_user(db, "ADMINISTRATOR"))
    assert client.get("/dashboard/overview", headers=admin).json()["payouts"] is not None
    zone = client.get("/dashboard/overview?zone=DANDORA", headers=staff).json()
    assert zone["total"] == 5


def test_map_and_heatmap_show_verified_reports_only(client, db, data):
    staff = auth_headers(make_user(db, "AGENCY_STAFF"))
    points = client.get("/dashboard/reports", headers=staff).json()
    assert len(points) == 3
    assert "reporter_id" not in points[0]
    burning = client.get("/dashboard/reports?category=OPEN_BURNING", headers=staff).json()
    assert len(burning) == 2
    heat = client.get("/dashboard/heatmap", headers=staff).json()
    assert heat == [{"latitude": -1.255, "longitude": 36.898, "weight": 3}]
    old = (date.today() - timedelta(days=30)).isoformat()
    assert client.get(f"/dashboard/reports?date_to={old}", headers=staff).json() == []


def test_trends_weekly_with_small_counts_hidden(client, db, data):
    admin = make_user(db, "ADMINISTRATOR")
    facility = make_facility(db, latitude=-1.2550, longitude=36.8980)
    batch = make_import_batch(db, admin)
    monday = date.today() - timedelta(days=date.today().weekday())
    for weeks_ago, count in [(1, 30), (2, 3)]:
        start = monday - timedelta(weeks=weeks_ago)
        make_summary(
            db,
            facility,
            batch,
            condition_category=ConditionCategory.RESPIRATORY,
            period_start=start,
            period_end=start + timedelta(days=6),
            visit_count=count,
        )
    t = client.get("/dashboard/trends?zone=DANDORA", headers=auth_headers(admin)).json()
    assert len(t["weeks"]) == 16
    week = {w: i for i, w in enumerate(t["weeks"])}
    one = week[(monday - timedelta(weeks=1)).isoformat()]
    two = week[(monday - timedelta(weeks=2)).isoformat()]
    assert t["visits"]["RESPIRATORY"][one] == 30
    assert t["visits"]["RESPIRATORY"][two] is None  # 3 visits < 5: hidden
    assert t["suppressed"]["RESPIRATORY"][two] is True
    assert sum(t["reports"]["OPEN_BURNING"]) == 2
    assert "not evidence" in t["notice"]


def test_monthly_counts_are_spread_across_weeks(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    facility = make_facility(db)
    batch = make_import_batch(db, admin)
    make_summary(
        db,
        facility,
        batch,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        visit_count=300,
    )
    t = client.get(
        "/dashboard/trends?date_from=2026-05-25&date_to=2026-07-05", headers=auth_headers(admin)
    ).json()
    assert sum(v or 0 for v in t["visits"]["RESPIRATORY"]) == pytest.approx(300, abs=0.5)
    assert max(v or 0 for v in t["visits"]["RESPIRATORY"]) == pytest.approx(70, abs=0.1)


@pytest.mark.parametrize(
    "path", ["/dashboard/overview", "/dashboard/reports", "/dashboard/heatmap", "/dashboard/trends"]
)
def test_dashboard_is_for_agency_staff_and_admins(client, db, path):
    for role in ["REPORTER", "VERIFIER"]:
        assert client.get(path, headers=auth_headers(make_user(db, role))).status_code == 403
    assert client.get(path).status_code == 401
