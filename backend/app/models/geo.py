from geoalchemy2 import Geography 
from sqlalchemy import Computed

LOCATION_EXPRESSION = "(st_setsrid(st_makepoint(longitude, latitude), 4326))::geography"

def Location_column_type() -> Geography:
    return Geography(geometry_type="POINT", srid=4326, spatial_index=False)

def location_computed() -> Computed:
    return Computed(LOCATION_EXPRESSION, persisted=True)
