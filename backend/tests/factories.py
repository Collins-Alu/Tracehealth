"""
Small helpers that create valid test records with sensible defaults.
Every value is synthetic; there is no real personal or patient data here.
"""

import itertools
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    Administrator,
    AgencyStaff,
    ClinicImportBatch,
    ClinicVisitSummary,
    Facility,
    Payout,
    PollutionReport,
    Reporter,
    User,
    Verification,
    Verifier,
)
from app.models.enums import (
    ConditionCategory,
    ImportBatchStatus,
    PayoutProvider,
    PollutionCategory,
    SyncStatus,
    VerificationDecision,
)

_counter = itertools.count(1)

# A pre-computed Argon2 hash keeps the tests fast (hashing is deliberately slow)
TEST_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$dGVzdHNhbHR0ZXN0$test-hash-not-real"


def make_user(db: Session, *roles: str, **overrides) -> User:
    n = next(_counter)
    user = User(
        full_name=overrides.pop("full_name", f"Test User {n}"),
        phone_number=overrides.pop("phone_number", f"+2547000{n:05d}"),
        email=overrides.pop("email", f"user{n}@example.test"),
        password_hash=TEST_PASSWORD_HASH,
        **overrides,
    )
    if "REPORTER" in roles:
        user.reporter_profile = Reporter()
    if "VERIFIER" in roles:
        user.verifier_profile = Verifier(assigned_zone="Zone A")
    if "AGENCY_STAFF" in roles:
        user.agency_staff_profile = AgencyStaff(agency_name="County Environment Office")
    if "ADMINISTRATOR" in roles:
        user.administrator_profile = Administrator(admin_level=1)
    db.add(user)
    db.flush()
    return user


def make_report(db: Session, reporter: User, **overrides) -> PollutionReport:
    report = PollutionReport(
        client_report_id=overrides.pop("client_report_id", uuid.uuid4()),
        reporter_id=reporter.id,
        photo_url=overrides.pop("photo_url", "uploads/test/photo.jpg"),
        latitude=overrides.pop("latitude", -1.2921),
        longitude=overrides.pop("longitude", 36.8219),
        category=overrides.pop("category", PollutionCategory.OPEN_BURNING),
        captured_at=overrides.pop("captured_at", datetime.now(UTC)),
        sync_status=overrides.pop("sync_status", SyncStatus.SUBMITTED_ONLINE),
        **overrides,
    )
    db.add(report)
    db.flush()
    return report


def decide(
    db: Session,
    report: PollutionReport,
    verifier: User,
    decision: VerificationDecision,
    reason: str | None = None,
) -> Verification:
    verification = Verification(
        report_id=report.id,
        verifier_id=verifier.id,
        decision=decision,
        reason=reason,
        is_final=decision != VerificationDecision.FLAGGED,
    )
    db.add(verification)
    db.flush()
    db.refresh(report)  # the trigger changed the report's status
    return verification


def make_payout(db: Session, report: PollutionReport, verification: Verification) -> Payout:
    payout = Payout(
        report_id=report.id,
        verification_id=verification.id,
        reporter_id=report.reporter_id,
        amount=Decimal("50.00"),
        phone_number="+254700000001",
        provider=PayoutProvider.MOCK,
    )
    db.add(payout)
    db.flush()
    return payout


def make_facility(db: Session, **overrides) -> Facility:
    n = next(_counter)
    facility = Facility(
        external_code=overrides.pop("external_code", f"TEST-FAC-{n}"),
        name=overrides.pop("name", f"Test Health Centre {n}"),
        latitude=overrides.pop("latitude", -1.2950),
        longitude=overrides.pop("longitude", 36.8250),
        area_code=overrides.pop("area_code", "AREA-1"),
        **overrides,
    )
    db.add(facility)
    db.flush()
    return facility


def make_import_batch(db: Session, admin: User) -> ClinicImportBatch:
    batch = ClinicImportBatch(
        filename="test.csv",
        imported_by=admin.id,
        status=ImportBatchStatus.ACCEPTED,
        row_count=1,
    )
    db.add(batch)
    db.flush()
    return batch


def make_summary(
    db: Session, facility: Facility, batch: ClinicImportBatch, **overrides
) -> ClinicVisitSummary:
    summary = ClinicVisitSummary(
        facility_id=facility.id,
        import_batch_id=batch.id,
        condition_category=overrides.pop("condition_category", ConditionCategory.RESPIRATORY),
        period_start=overrides.pop("period_start", date(2026, 9, 7)),
        period_end=overrides.pop("period_end", date(2026, 9, 13)),
        visit_count=overrides.pop("visit_count", 12),
        **overrides,
    )
    db.add(summary)
    db.flush()
    return summary

