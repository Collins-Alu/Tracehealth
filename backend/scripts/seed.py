"""
Development seed data for TraceHealth.

Everything created here is SYNTHETIC: invented people, invented facilities
(names end in "(SYNTHETIC)") and invented clinic counts. It exists only so
you can click through the apps and see realistic-looking screens. It must
never be loaded into a production database, and the script refuses to run
when ENVIRONMENT=production.

Usage (from the backend/ folder, with the virtual environment active):
    python -m scripts.seed            # seed an empty database
    python -m scripts.seed --reset    # wipe app data first, then seed

Health linkages are NOT seeded: the linkage engine computes them from the
reports and clinic counts below, exactly as it does for real data.
"""

import argparse
import io
import random
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from PIL import Image, ImageDraw
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Administrator,
    AgencyStaff,
    AuditLog,
    ClinicImportBatch,
    ClinicVisitSummary,
    Facility,
    Notification,
    Payout,
    PollutionReport,
    Reporter,
    User,
    Verification,
    Verifier,
    Zone,
)
from app.models.enums import (
    ConditionCategory,
    ImportBatchStatus,
    NotificationChannel,
    NotificationStatus,
    PayoutProvider,
    PayoutStatus,
    PollutionCategory,
    SyncStatus,
    VerificationDecision,
)
from app.services import linkage_engine, photo_storage, setting_service

# Tables wiped by --reset (settings are restored to defaults afterwards)
APP_TABLES = [
    "health_linkage_evidence",
    "health_linkages",
    "payouts",
    "notifications",
    "verifications",
    "pollution_reports",
    "clinic_visit_summaries",
    "clinic_import_batches",
    "facilities",
    "audit_logs",
    "refresh_tokens",
    "reporters",
    "device_push_tokens",
    "verifiers",
    "zones",
    "agency_staff",
    "administrators",
    "users",
]

FACILITIES = [
    # external_code, name, lat, lng, area_code
    ("SYN-001", "Dandora Community Clinic (SYNTHETIC)", -1.2550, 36.8980, "NBI-DANDORA"),
    ("SYN-002", "Mukuru Health Post (SYNTHETIC)", -1.3120, 36.8750, "NBI-MUKURU"),
    ("SYN-003", "Kibera Health Point (SYNTHETIC)", -1.3130, 36.7880, "NBI-KIBERA"),
]


# Verifier zones: a 3 km circle around each synthetic facility
ZONES = [
    ("NBI-DANDORA", "Dandora", -1.2550, 36.8980),
    ("NBI-MUKURU", "Mukuru", -1.3120, 36.8750),
    ("NBI-KIBERA", "Kibera", -1.3130, 36.7880),
]

CATEGORY_COLOURS = {
    PollutionCategory.OPEN_BURNING: (176, 72, 40),
    PollutionCategory.ILLEGAL_DUMPING: (110, 92, 60),
    PollutionCategory.BLOCKED_DRAINAGE: (52, 96, 120),
    PollutionCategory.MEDICAL_WASTE: (150, 60, 110),
    PollutionCategory.OTHER: (90, 100, 95),
}


def placeholder_photo(category: PollutionCategory, number: int) -> str:
    """Store a clearly labelled synthetic image so photo screens have something to show."""
    img = Image.new("RGB", (800, 600), CATEGORY_COLOURS[category])
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 220, 760, 380), fill=(255, 255, 255))
    draw.text((70, 245), "SYNTHETIC SEED PHOTO", fill=(0, 0, 0), font_size=44)
    draw.text((70, 310), f"{category.value}  #{number:02d}", fill=(60, 60, 60), font_size=34)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=80)
    return photo_storage.save_photo(out.getvalue())


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def create_user(db: Session, full_name: str, phone: str, email: str | None, password_hash: str):
    user = User(full_name=full_name, phone_number=phone, email=email, password_hash=password_hash)
    db.add(user)
    return user


def seed(db: Session) -> dict:
    settings = get_settings()
    rng = random.Random(2026)  # fixed seed: same data every run
    pw = hash_password(settings.SEED_DEFAULT_PASSWORD)
    now = datetime.now(UTC)

    # ---- Zones ----------------------------------------------------------
    for code, name, lat, lng in ZONES:
        db.add(Zone(code=code, name=name, latitude=lat, longitude=lng, radius_km=3))
    db.flush()

    # ---- People ---------------------------------------------------------
    admin = create_user(db, "Asha Admin", "+254700000001", "admin@example.org", pw)
    admin.administrator_profile = Administrator(admin_level=3)

    staff = create_user(db, "Brian Agency", "+254700000002", "agency@example.org", pw)
    staff.agency_staff_profile = AgencyStaff(
        agency_name="Nairobi County Environment (SYNTHETIC)", department="Public Health"
    )

    verifier_a = create_user(db, "Carol Verifier", "+254700000003", "verifier1@example.org", pw)
    verifier_a.verifier_profile = Verifier(assigned_zone="NBI-DANDORA")
    # A community member who both reports and verifies (tests the self-verification rule)
    verifier_b = create_user(db, "Daniel Verifier", "+254700000004", "verifier2@example.org", pw)
    verifier_b.verifier_profile = Verifier(assigned_zone="NBI-MUKURU")
    verifier_b.reporter_profile = Reporter()

    reporters = []
    for i, name in enumerate(["Esther Reporter", "Felix Reporter", "Grace Reporter"], start=5):
        r = create_user(db, name, f"+2547000000{i:02d}", None, pw)
        r.reporter_profile = Reporter(
            payout_phone=f"+2547000000{i:02d}", payout_consent_at=now - timedelta(days=90)
        )
        reporters.append(r)
    db.flush()

    # ---- Facilities -----------------------------------------------------
    facilities = {}
    for code, name, lat, lng, area in FACILITIES:
        f = Facility(external_code=code, name=name, latitude=lat, longitude=lng, area_code=area)
        db.add(f)
        facilities[area] = f
    db.flush()

    # ---- Pollution reports ----------------------------------------------
    # (area, category, days_ago, outcome, description)
    report_plan = [
        ("NBI-DANDORA", PollutionCategory.OPEN_BURNING, 38, "VERIFIED", "Smoke from burning heap"),
        ("NBI-DANDORA", PollutionCategory.OPEN_BURNING, 36, "VERIFIED", "Burning near the road"),
        ("NBI-DANDORA", PollutionCategory.ILLEGAL_DUMPING, 30, "VERIFIED", None),
        ("NBI-DANDORA", PollutionCategory.OPEN_BURNING, 35, "FLAGGED", "Same fire as yesterday?"),
        ("NBI-MUKURU", PollutionCategory.BLOCKED_DRAINAGE, 25, "VERIFIED", "Drain overflowing"),
        ("NBI-MUKURU", PollutionCategory.MEDICAL_WASTE, 20, "VERIFIED", "Syringes near the river"),
        ("NBI-MUKURU", PollutionCategory.ILLEGAL_DUMPING, 18, "REJECTED", None),
        ("NBI-KIBERA", PollutionCategory.ILLEGAL_DUMPING, 12, "VERIFIED", None),
        ("NBI-KIBERA", PollutionCategory.OTHER, 9, "REJECTED", "Unclear photo"),
        ("NBI-KIBERA", PollutionCategory.OPEN_BURNING, 3, "PENDING", "Fire behind the market"),
        ("NBI-MUKURU", PollutionCategory.BLOCKED_DRAINAGE, 1, "PENDING", None),
        ("NBI-DANDORA", PollutionCategory.ILLEGAL_DUMPING, 0, "PENDING", None),
    ]
    reject_reasons = {
        "NBI-MUKURU": "Photo shows a household bin, not illegal dumping.",
        "NBI-KIBERA": "Photo is too blurry to confirm the incident.",
    }
    reports = []
    for idx, (area, category, days_ago, outcome, description) in enumerate(report_plan):
        fac = facilities[area]
        # Daniel (verifier2) also reports: one verified report and one pending one,
        # which he must not be able to verify himself
        reporter = reporters[idx % len(reporters)] if idx not in (4, 10) else verifier_b
        captured = now - timedelta(days=days_ago, hours=rng.randint(1, 10))
        lat = round(fac.latitude + rng.uniform(-0.01, 0.01), 6)
        lng = round(fac.longitude + rng.uniform(-0.01, 0.01), 6)
        if idx == 3:
            # The flagged "same fire" report sits ~60 m from report 2, so the
            # verifier's nearby-reports check shows the likely original
            first_fire = reports[1][0]
            lat, lng = first_fire.latitude + 0.0005, first_fire.longitude + 0.0002
        report = PollutionReport(
            client_report_id=uuid.uuid4(),
            reporter_id=reporter.id,
            photo_url=placeholder_photo(category, idx + 1),
            latitude=lat,
            longitude=lng,
            category=category,
            description=description,
            zone_code=area,
            captured_at=captured,
            sync_status=SyncStatus.SYNCED_FROM_OFFLINE
            if idx % 3 == 0
            else SyncStatus.SUBMITTED_ONLINE,
        )
        db.add(report)
        reports.append((report, reporter, outcome, area, captured))
    db.flush()

    # ---- Verifications, payouts, notifications, audit log ----------------
    payout_amount = Decimal("50.00")
    for report, reporter, outcome, area, captured in reports:
        if outcome == "PENDING":
            continue
        # Pick a verifier who is not the reporter
        verifier = verifier_a if reporter.id != verifier_a.id else verifier_b
        if reporter.id == verifier.id:
            verifier = verifier_a
        decided_at = captured + timedelta(hours=rng.randint(2, 30))
        decision = VerificationDecision(outcome)
        reason = None
        if decision == VerificationDecision.REJECTED:
            reason = reject_reasons[area]
        elif decision == VerificationDecision.FLAGGED:
            reason = "Possible duplicate of an earlier open-burning report nearby."
        verification = Verification(
            report_id=report.id,
            verifier_id=verifier.id,
            decision=decision,
            reason=reason,
            is_final=decision != VerificationDecision.FLAGGED,
            verified_at=decided_at,
        )
        db.add(verification)
        db.flush()
        db.add(
            AuditLog(
                actor_id=verifier.id,
                action=f"report.{decision.value.lower()}",
                entity_type="pollution_report",
                entity_id=report.id,
                details={"verification_id": str(verification.id), "reason": reason},
            )
        )

        title, body = {
            VerificationDecision.VERIFIED: (
                "Report verified",
                "Thank you! Your report was confirmed.",
            ),
            VerificationDecision.REJECTED: ("Report not accepted", f"Reason: {reason}"),
            VerificationDecision.FLAGGED: ("Report under review", "Your report is being reviewed."),
        }[decision]
        db.add(
            Notification(
                user_id=reporter.id,
                type=f"report.{decision.value.lower()}",
                title=title,
                body=body,
                channel=NotificationChannel.IN_APP,
                status=NotificationStatus.SENT,
                related_report_id=report.id,
                sent_at=decided_at,
            )
        )

        if decision == VerificationDecision.VERIFIED:
            phone = reporter.reporter_profile.payout_phone or reporter.phone_number
            db.add(
                Payout(
                    report_id=report.id,
                    verification_id=verification.id,
                    reporter_id=reporter.id,
                    amount=payout_amount,
                    currency="KES",
                    phone_number=phone,
                    provider=PayoutProvider.MOCK,  # TEST ONLY: no real money moved
                    provider_request_id=f"MOCK-REQ-{uuid.uuid4().hex[:10].upper()}",
                    transaction_ref=f"MOCK-TXN-{uuid.uuid4().hex[:10].upper()}",
                    status=PayoutStatus.SUCCESS,
                    paid_at=decided_at + timedelta(minutes=2),
                )
            )
    db.flush()

    # ---- Clinic import (synthetic weekly counts, 16 weeks) --------------
    batch = ClinicImportBatch(
        filename="synthetic_weekly_counts.csv",
        imported_by=admin.id,
        status=ImportBatchStatus.ACCEPTED,
        row_count=0,
    )
    db.add(batch)
    db.flush()

    base_rates = {
        ConditionCategory.RESPIRATORY: 18,
        ConditionCategory.SKIN: 7,
        ConditionCategory.DIARRHOEAL: 9,
        ConditionCategory.MALARIA: 4,
    }
    first_week = monday(now.date()) - timedelta(weeks=15)
    burning_week = monday((now - timedelta(days=38)).date())
    rows = 0
    for area, fac in facilities.items():
        for w in range(16):
            week_start = first_week + timedelta(weeks=w)
            for condition, base in base_rates.items():
                count = max(0, base + rng.randint(-3, 3))
                # Synthetic pattern so the Sprint 3 engine has something to find:
                # respiratory visits near Dandora rise in the weeks after the burning reports.
                if (
                    area == "NBI-DANDORA"
                    and condition == ConditionCategory.RESPIRATORY
                    and burning_week < week_start <= burning_week + timedelta(weeks=4)
                ):
                    count += 14
                db.add(
                    ClinicVisitSummary(
                        facility_id=fac.id,
                        import_batch_id=batch.id,
                        condition_category=condition,
                        period_start=week_start,
                        period_end=week_start + timedelta(days=6),
                        visit_count=count,
                    )
                )
                rows += 1
    batch.row_count = rows
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="clinic_data.imported",
            entity_type="clinic_import_batch",
            entity_id=batch.id,
            details={"rows": rows, "synthetic": True},
        )
    )
    db.flush()

    # Health linkages are computed by the engine from the data above (never seeded)
    run = linkage_engine.compute(db)

    return {
        "linkages": run.by_status,
        "users": db.scalar(select(func.count()).select_from(User)),
        "reports": len(reports),
        "facilities": len(facilities),
        "clinic_rows": rows,
        "payouts": db.scalar(select(func.count()).select_from(Payout)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Load synthetic development data.")
    parser.add_argument("--reset", action="store_true", help="wipe app data before seeding")
    args = parser.parse_args()

    settings = get_settings()
    if settings.is_production:
        print("Refusing to seed: ENVIRONMENT=production.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        if args.reset:
            db.execute(text(f"TRUNCATE {', '.join(APP_TABLES)} RESTART IDENTITY CASCADE"))
            # CASCADE also empties system_settings (it references users via
            # updated_by), so put the approved defaults back
            setting_service.ensure_defaults(db)
        elif db.scalar(select(func.count()).select_from(User)):
            print("Database already has users. Run with --reset to wipe and re-seed.")
            return 1
        counts = seed(db)
        db.commit()

    print("Seed complete (all data is SYNTHETIC):")
    for key, value in counts.items():
        print(f"  {key:12} {value}")
    print(f"\nDev logins (password: {settings.SEED_DEFAULT_PASSWORD}):")
    print("  admin@example.org      Administrator")
    print("  agency@example.org     Agency staff")
    print("  verifier1@example.org  Verifier (Dandora)")
    print("  verifier2@example.org  Verifier + reporter (Mukuru)")
    print("  +254700000005 / 06 / 07     Reporters (phone login)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
