from enum import StrEnum

class Language(StrEnum):
    EN = "EN"
    SW = "SW"

class PollutionCategory(StrEnum):
    OPEN_BURNING = "OPEN_BURNING"
    ILLEGAL_DUMPINNG = "ILLEGAL_DUMPING"
    BLOCKED_DRAINAGE = "BLOCKED_DRAINAGE"
    MEDICAL_WASTE = "MEDICAL_WASTE"
    OTHER = "OTHER"

class ReportStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"

class SyncStatus(StrEnum):
    SUBMITTED_ONLINE = "SUBMITTED_ONLINE"
    SYNCED_FROM_OFFLINE = "SYNCED_FROM_OFFLINE"

class PayoutStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED= "FAILED"

class PayoutProvider(StrEnum):
    MPESA_DARAJA = "MPESA_DARAJA"
    MOCK = "MOCK"

class ConditionCategory(StrEnum):
    RESPIRATORY = "RESPIRATORY"
    SKIN = "SKIN"
    DIARRHOEA = "DIARRHOEA"
    MALARIA = "MALARIA"
    INJURY = "INJURY"
    INFECTION = "INFECTION"
    OTHER = "OTHER"

class ImportBatchStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECT = "REJECTED"

class linkageStatus(StrEnum):
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


