"""Read administrator-editable settings from the system_settings table.

Migration 0001 inserts the approved defaults. DEFAULTS repeats them here so a
database that lost rows (e.g. a manual clean-up) heals itself: ensure_defaults()
puts back any missing key without touching values an administrator changed.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import SystemSetting

DEFAULTS: dict[str, tuple[Any, str]] = {
    "linkage.radius_km": (3, "Search radius around a verified report for nearby facilities (km)."),
    "linkage.baseline_weeks": (8, "Weeks before the report used as the baseline visit rate."),
    "linkage.followup_weeks": (4, "Weeks after the report checked for a rise in visits."),
    "linkage.min_baseline_visits": (
        10,
        "Fewer baseline visits than this gives INSUFFICIENT_DATA.",
    ),
    "linkage.p_value_threshold": (0.05, "Significance level for flagging a SIGNAL."),
    "linkage.category_mapping": (
        {
            "OPEN_BURNING": ["RESPIRATORY"],
            "ILLEGAL_DUMPING": ["SKIN", "DIARRHOEAL"],
            "BLOCKED_DRAINAGE": ["DIARRHOEAL", "MALARIA"],
            "MEDICAL_WASTE": ["INJURY", "INFECTION"],
            "OTHER": [],
        },
        "Which health conditions are checked for each pollution category. "
        "To be confirmed with the partner clinic.",
    ),
    "payout.amount": (50, "Incentive paid per verified report."),
    "payout.currency": ("KES", "ISO currency code for incentive payouts."),
    "dashboard.small_count_threshold": (
        5,
        "Visit counts below this are shown as '<N' to protect privacy.",
    ),
}


def get(db: Session, key: str, default: Any = None) -> Any:
    value = db.scalar(select(SystemSetting.value).where(SystemSetting.key == key))
    if value is not None:
        return value
    if default is None and key in DEFAULTS:
        return DEFAULTS[key][0]
    return default


def ensure_defaults(db: Session) -> None:
    """Insert any missing setting with its default. Existing values are kept."""
    rows = [{"key": k, "value": v, "description": d} for k, (v, d) in DEFAULTS.items()]
    db.execute(insert(SystemSetting).values(rows).on_conflict_do_nothing(index_elements=["key"]))
    db.flush()
