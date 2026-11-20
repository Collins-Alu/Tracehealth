"""
Importing every model here registers it on Base.metadata, which Alembic uses
to compare the models with the database.
"""

from app.models.audit import AuditLog
from app.models.auth_token import RefreshToken
from app.models.clinic import ClinicImportBatch, ClinicVisitSummary, Facility
from app.models.health_linkage import HealthLinkage, HealthLinkageEvidence
from app.models.notification import Notification
from app.models.payout import Payout
from app.models.report import PollutionReport
from app.models.setting import SystemSetting
from app.models.user import Administrator, AgencyStaff, Reporter, User, Verifier
from app.models.verification import Verification

__all__ = [
    "Administrator",
    "AgencyStaff",
    "AuditLog",
    "ClinicImportBatch",
    "ClinicVisitSummary",
    "Facility",
    "HealthLinkage",
    "HealthLinkageEvidence",
    "Notification",
    "Payout",
    "PollutionReport",
    "RefreshToken",
    "Reporter",
    "SystemSetting",
    "User",
    "Verification",
    "Verifier",
]
