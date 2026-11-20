"""
Zone: a named area that verifiers are responsible for (Sprint 2).

The SRS asks verifiers to "filter reports by geographical zone" but does not
define zones. For the pilot a zone is a circle: a centre point and a radius.
That is simple to set up from a map and easy to explain to verifiers. Each
new report is assigned to the nearest zone whose circle contains it; reports
outside every zone stay unassigned and are shown to all verifiers.
"""

from sqlalchemy import Boolean, CheckConstraint, Double, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.geo import location_column_type, location_computed
from app.models.mixins import CreatedAtMixin


class Zone(CreatedAtMixin, Base):
    __tablename__ = "zones"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint("radius_km > 0 AND radius_km <= 50", name="radius_range"),
        CheckConstraint("code ~ '^[A-Z0-9][A-Z0-9_-]{1,39}$'", name="code_format"),
        Index("ix_zones_location", "location", postgresql_using="gist"),
    )

    # Short stable code such as "NBI-DANDORA"; shown in filters and stored on reports
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    location = mapped_column(location_column_type(), location_computed(), nullable=False)
    radius_km: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
