"""The development seed must satisfy every database rule (it runs in a rolled-back transaction)."""

from sqlalchemy import func, select

from app.models import ClinicVisitSummary, Payout, PollutionReport
from app.models.enums import PayoutProvider, ReportStatus
from scripts.seed import seed


def test_seed_loads_consistent_synthetic_data(db):
    counts = seed(db)
    assert counts["reports"] == 12
    assert counts["clinic_rows"] == db.scalar(select(func.count()).select_from(ClinicVisitSummary))

    verified = db.scalar(
        select(func.count())
        .select_from(PollutionReport)
        .where(PollutionReport.status == ReportStatus.VERIFIED)
    )
    payouts = db.scalars(select(Payout)).all()
    assert len(payouts) == verified  # exactly one payout per verified report
    assert all(p.provider == PayoutProvider.MOCK for p in payouts)
    assert all(p.transaction_ref.startswith("MOCK-") for p in payouts)

