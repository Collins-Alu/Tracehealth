"""
Database-level business rules from the SRS.

Each test proves the database itself refuses invalid data, so these rules
hold even if a future API bug tries to bypass them.
"""

import uuid
from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import AuditLog, HealthLinkage, SystemSetting
from app.models.enums import (
    ConditionCategory,
    LinkageStatus,
    ReportStatus,
    VerificationDecision,
)
from tests.factories import (
    decide,
    make_facility,
    make_import_batch,
    make_payout,
    make_report,
    make_summary,
    make_user,
)


@contextmanager
def rejected_by_database(db):
    """Assert the block raises IntegrityError, rolling back only that block."""
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            yield


@pytest.fixture
def people(db):
    return {
        "reporter": make_user(db, "REPORTER"),
        "verifier": make_user(db, "VERIFIER"),
        "admin": make_user(db, "ADMINISTRATOR"),
    }


# ---------- Users ----------------------------------------------------------


def test_user_can_hold_reporter_and_verifier_roles(db):
    user = make_user(db, "REPORTER", "VERIFIER")
    assert user.roles == ["REPORTER", "VERIFIER"]


def test_email_must_be_stored_lowercase(db):
    with rejected_by_database(db):
        make_user(db, email="Mixed@Example.test")


def test_payout_phone_requires_consent(db):
    user = make_user(db, "REPORTER")
    with rejected_by_database(db):
        user.reporter_profile.payout_phone = "+254700000099"
        db.flush()


# ---------- Reports & offline sync -----------------------------------------


def test_new_report_is_pending(db, people):
    report = make_report(db, people["reporter"])
    db.refresh(report)
    assert report.status == ReportStatus.PENDING


def test_same_client_report_id_cannot_be_stored_twice(db, people):
    """This is what makes offline re-sync safe from duplicates."""
    client_id = uuid.uuid4()
    make_report(db, people["reporter"], client_report_id=client_id)
    with rejected_by_database(db):
        make_report(db, people["reporter"], client_report_id=client_id)


def test_coordinates_must_be_valid(db, people):
    with rejected_by_database(db):
        make_report(db, people["reporter"], latitude=95.0)


def test_location_point_is_derived_from_coordinates(db, people):
    report = make_report(db, people["reporter"], latitude=-1.30, longitude=36.80)
    lat, lng = db.execute(
        text(
            "SELECT ST_Y(location::geometry), ST_X(location::geometry) "
            "FROM pollution_reports WHERE id = :id"
        ),
        {"id": report.id},
    ).one()
    assert (round(lat, 6), round(lng, 6)) == (-1.30, 36.80)


def test_distance_between_report_and_facility_in_km(db, people):
    report = make_report(db, people["reporter"], latitude=-1.2921, longitude=36.8219)
    facility = make_facility(db, latitude=-1.2921, longitude=36.8419)  # ~2.2 km east
    km = db.execute(
        text(
            "SELECT ST_Distance(r.location, f.location) / 1000 "
            "FROM pollution_reports r, facilities f WHERE r.id = :r AND f.id = :f"
        ),
        {"r": report.id, "f": facility.id},
    ).scalar_one()
    assert 2.0 < km < 2.4


# ---------- Verification ---------------------------------------------------


def test_reporter_cannot_verify_own_report(db):
    person = make_user(db, "REPORTER", "VERIFIER")
    report = make_report(db, person)
    with rejected_by_database(db):
        decide(db, report, person, VerificationDecision.VERIFIED)


def test_verification_updates_report_status(db, people):
    report = make_report(db, people["reporter"])
    decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    assert report.status == ReportStatus.VERIFIED


def test_only_one_final_decision_per_report(db, people):
    report = make_report(db, people["reporter"])
    decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    other = make_user(db, "VERIFIER")
    with rejected_by_database(db):
        decide(db, report, other, VerificationDecision.REJECTED, reason="Not pollution")


def test_flagged_report_can_later_receive_final_decision(db, people):
    report = make_report(db, people["reporter"])
    decide(
        db, report, people["verifier"], VerificationDecision.FLAGGED, reason="Possible duplicate"
    )
    assert report.status == ReportStatus.FLAGGED
    admin_verifier = make_user(db, "VERIFIER")
    decide(db, report, admin_verifier, VerificationDecision.REJECTED, reason="Confirmed duplicate")
    assert report.status == ReportStatus.REJECTED


def test_rejection_requires_reason(db, people):
    report = make_report(db, people["reporter"])
    with rejected_by_database(db):
        decide(db, report, people["verifier"], VerificationDecision.REJECTED, reason="   ")


def test_status_cannot_be_set_to_verified_without_a_verification(db, people):
    report = make_report(db, people["reporter"])
    with rejected_by_database(db):
        report.status = ReportStatus.VERIFIED
        db.flush()


def test_final_status_cannot_be_changed(db, people):
    report = make_report(db, people["reporter"])
    decide(db, report, people["verifier"], VerificationDecision.REJECTED, reason="Blurry photo")
    with rejected_by_database(db):
        report.status = ReportStatus.PENDING
        db.flush()


# ---------- Payouts --------------------------------------------------------


def test_verified_report_can_be_paid_once(db, people):
    report = make_report(db, people["reporter"])
    verification = decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    make_payout(db, report, verification)
    with rejected_by_database(db):
        make_payout(db, report, verification)


def test_rejected_report_cannot_be_paid(db, people):
    report = make_report(db, people["reporter"])
    verification = decide(
        db, report, people["verifier"], VerificationDecision.REJECTED, reason="Not pollution"
    )
    with rejected_by_database(db):
        make_payout(db, report, verification)


def test_payout_must_go_to_the_reporter(db, people):
    report = make_report(db, people["reporter"])
    verification = decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    someone_else = make_user(db, "REPORTER")
    with rejected_by_database(db):
        payout = make_payout(db, report, verification)
        payout.reporter_id = someone_else.id
        db.flush()


def test_successful_payout_requires_transaction_reference(db, people):
    report = make_report(db, people["reporter"])
    verification = decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    payout = make_payout(db, report, verification)
    with rejected_by_database(db):
        payout.status = "SUCCESS"
        db.flush()


# ---------- Clinic data & health linkage -----------------------------------


def test_visit_counts_cannot_be_negative(db, people):
    batch = make_import_batch(db, people["admin"])
    with rejected_by_database(db):
        make_summary(db, make_facility(db), batch, visit_count=-1)


def test_same_facility_condition_period_cannot_be_imported_twice(db, people):
    batch = make_import_batch(db, people["admin"])
    facility = make_facility(db)
    make_summary(db, facility, batch)
    with rejected_by_database(db):
        make_summary(db, facility, batch)


def test_period_end_cannot_precede_start(db, people):
    batch = make_import_batch(db, people["admin"])
    with rejected_by_database(db):
        make_summary(
            db,
            make_facility(db),
            batch,
            period_start=date(2026, 9, 13),
            period_end=date(2026, 9, 7),
        )


def _linkage(report, facility, status, **stats):
    return HealthLinkage(
        report_id=report.id,
        facility_id=facility.id,
        condition_category=ConditionCategory.RESPIRATORY,
        radius_km=3,
        distance_km=1.2,
        status=status,
        params_snapshot={"radius_km": 3},
        **stats,
    )


def test_linkage_rejected_for_unverified_report(db, people):
    report = make_report(db, people["reporter"])
    facility = make_facility(db)
    with rejected_by_database(db):
        db.add(_linkage(report, facility, LinkageStatus.INSUFFICIENT_DATA))
        db.flush()


def test_insufficient_data_linkage_needs_no_statistics(db, people):
    report = make_report(db, people["reporter"])
    decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    db.add(_linkage(report, make_facility(db), LinkageStatus.INSUFFICIENT_DATA))
    db.flush()


def test_signal_linkage_must_include_statistics(db, people):
    report = make_report(db, people["reporter"])
    decide(db, report, people["verifier"], VerificationDecision.VERIFIED)
    with rejected_by_database(db):
        db.add(_linkage(report, make_facility(db), LinkageStatus.SIGNAL))
        db.flush()


# ---------- Audit log & settings -------------------------------------------


def test_audit_log_is_append_only(db, people):
    entry = AuditLog(
        actor_id=people["verifier"].id, action="report.verified", entity_type="pollution_report"
    )
    db.add(entry)
    db.flush()
    with rejected_by_database(db):
        entry.action = "tampered"
        db.flush()
    with rejected_by_database(db):
        db.delete(entry)
        db.flush()


def test_default_settings_are_installed(db):
    keys = set(db.scalars(select(SystemSetting.key)))
    assert {"linkage.radius_km", "linkage.category_mapping", "payout.amount"} <= keys
    radius = db.scalar(select(SystemSetting.value).where(SystemSetting.key == "linkage.radius_km"))
    assert radius == 3


def test_no_patient_level_table_exists(db):
    """Guards NFR 6: the schema must not grow a table for individual patients."""
    count = db.scalar(
        select(func.count())
        .select_from(text("information_schema.tables"))
        .where(text("table_schema = 'public' AND table_name ILIKE '%patient%'"))
    )
    assert count == 0

