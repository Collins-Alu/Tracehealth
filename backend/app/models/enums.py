"""
Fixed value sets used across the data model.

They are stored as VARCHAR columns guarded by CHECK constraints rather than
native PostgreSQL ENUM types, because native enums are awkward to change in
later migrations. The names match the UML class diagram (Appendix B.2a).
"""

from enum import StrEnum


class Language(StrEnum):
    EN = "EN"
    SW = "SW"


class PollutionCategory(StrEnum):
    OPEN_BURNING = "OPEN_BURNING"
    ILLEGAL_DUMPING = "ILLEGAL_DUMPING"
    BLOCKED_DRAINAGE = "BLOCKED_DRAINAGE"
    MEDICAL_WASTE = "MEDICAL_WASTE"
    OTHER = "OTHER"


class ReportStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"


class SyncStatus(StrEnum):
    """How a report reached the server (the device tracks QUEUED/SYNCING locally)."""

    SUBMITTED_ONLINE = "SUBMITTED_ONLINE"
    SYNCED_FROM_OFFLINE = "SYNCED_FROM_OFFLINE"


class VerificationDecision(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"


class PayoutStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PayoutProvider(StrEnum):
    MPESA_DARAJA = "MPESA_DARAJA"
    MOCK = "MOCK"  # test-only adapter; never a real payment


class ConditionCategory(StrEnum):
    RESPIRATORY = "RESPIRATORY"
    SKIN = "SKIN"
    DIARRHOEAL = "DIARRHOEAL"
    MALARIA = "MALARIA"
    INJURY = "INJURY"
    INFECTION = "INFECTION"
    OTHER = "OTHER"


class ImportBatchStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class LinkageStatus(StrEnum):
    SIGNAL = "SIGNAL"
    NO_SIGNAL = "NO_SIGNAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EvidenceWindow(StrEnum):
    BASELINE = "BASELINE"
    FOLLOWUP = "FOLLOWUP"


class NotificationChannel(StrEnum):
    PUSH = "PUSH"
    SMS = "SMS"
    IN_APP = "IN_APP"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
