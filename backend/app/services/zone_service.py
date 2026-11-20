"""Zone lookup (Sprint 2). See app/models/zone.py for what a zone is."""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Zone

# Nearest active zone whose circle contains the point. ST_DWithin on the
# geography type measures in metres along the Earth's surface.
_ZONE_FOR_POINT = text(
    """
    SELECT code
      FROM zones
     WHERE is_active
       AND ST_DWithin(
             location,
             ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
             radius_km * 1000
           )
     ORDER BY ST_Distance(location, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
     LIMIT 1
    """
)


def zone_for_point(db: Session, latitude: float, longitude: float) -> str | None:
    return db.execute(_ZONE_FOR_POINT, {"lat": latitude, "lng": longitude}).scalar()


def list_active_zones(db: Session) -> list[Zone]:
    return list(db.scalars(select(Zone).where(Zone.is_active).order_by(Zone.name)))
