"""
Geographic point column shared by reports and facilities.

Latitude and longitude are stored as plain numbers (easy to read and to send
to the apps). PostgreSQL then derives a PostGIS `geography` point from them
automatically (a STORED generated column), so the two can never disagree.
The geography type measures distances in metres on the Earth's surface, which
is what the health-linkage radius search needs.
"""

from geoalchemy2 import Geography
from sqlalchemy import Computed

LOCATION_EXPRESSION = "(st_setsrid(st_makepoint(longitude, latitude), 4326))::geography"


def location_column_type() -> Geography:
    # spatial_index=False: the GiST index is declared explicitly in each model
    return Geography(geometry_type="POINT", srid=4326, spatial_index=False)


def location_computed() -> Computed:
    return Computed(LOCATION_EXPRESSION, persisted=True)
