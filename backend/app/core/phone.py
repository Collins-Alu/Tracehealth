"""
Phone number normalisation.

People type numbers in many ways ("0712 345 678", "254712345678",
"+254-712-345678"). Every number is stored in one international format
(E.164, e.g. +254712345678) so the same person cannot register twice and
mobile-money payouts always get a number the provider accepts.
"""

import re

from app.core.config import get_settings

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class InvalidPhoneNumber(ValueError):
    pass


def normalize_phone(raw: str) -> str:
    country = get_settings().DEFAULT_COUNTRY_CODE
    cleaned = re.sub(r"[\s\-().]", "", raw or "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif cleaned.startswith("0"):
        cleaned = f"+{country}{cleaned[1:]}"
    elif not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not _E164.match(cleaned):
        raise InvalidPhoneNumber("Enter a valid phone number, for example 0712 345 678.")
    return cleaned
