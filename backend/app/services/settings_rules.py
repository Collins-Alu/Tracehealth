"""
Validation for administrator-editable settings. Each key has a rule; a value
that breaks it is refused with a plain explanation. Unknown keys can't be set.
"""

import re
from typing import Any

from app.models.enums import ConditionCategory, PollutionCategory


class SettingError(ValueError):
    pass


def _number(lo: float, hi: float, integer: bool = False):
    def check(v: Any):
        if isinstance(v, bool) or not isinstance(v, int | float):
            raise SettingError("Must be a number.")
        if integer and int(v) != v:
            raise SettingError("Must be a whole number.")
        if not lo <= v <= hi:
            raise SettingError(f"Must be between {lo:g} and {hi:g}.")
        return int(v) if integer else float(v)

    return check


def _currency(v: Any):
    if not isinstance(v, str) or not re.fullmatch(r"[A-Z]{3}", v):
        raise SettingError("Use a 3-letter currency code, e.g. KES.")
    return v


def _mapping(v: Any):
    if not isinstance(v, dict):
        raise SettingError("Must map each pollution category to a list of conditions.")
    allowed = {c.value for c in ConditionCategory}
    out = {}
    for category in PollutionCategory:
        conditions = v.get(category.value, [])
        if not isinstance(conditions, list) or any(c not in allowed for c in conditions):
            raise SettingError(f"{category.value}: use conditions from {sorted(allowed)}.")
        out[category.value] = sorted(set(conditions))
    extra = set(v) - {c.value for c in PollutionCategory}
    if extra:
        raise SettingError(f"Unknown pollution categories: {sorted(extra)}.")
    return out


RULES = {
    "linkage.radius_km": _number(0.1, 20),
    "linkage.baseline_weeks": _number(2, 26, integer=True),
    "linkage.followup_weeks": _number(1, 12, integer=True),
    "linkage.min_baseline_visits": _number(1, 1000, integer=True),
    "linkage.p_value_threshold": _number(0.001, 0.2),
    "linkage.category_mapping": _mapping,
    "payout.amount": _number(1, 1000),
    "payout.currency": _currency,
    "dashboard.small_count_threshold": _number(1, 20, integer=True),
}


def validate(key: str, value: Any) -> Any:
    rule = RULES.get(key)
    if rule is None:
        raise SettingError("This setting can't be changed.")
    return rule(value)
