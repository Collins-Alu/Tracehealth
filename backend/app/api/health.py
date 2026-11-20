"""
GET /health: confirms the API is running and can reach PostgreSQL + PostGIS.

Useful during setup ("is everything connected?") and later for deployment
monitoring. It reveals no sensitive information.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["System"])


@router.get("/health", summary="Service and database health check")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    settings = get_settings()
    body = {"status": "ok", "version": settings.APP_VERSION, "database": "ok", "postgis": None}
    try:
        db.execute(text("SELECT 1"))
        body["postgis"] = db.execute(text("SELECT postgis_lib_version()")).scalar_one()
    except SQLAlchemyError:
        body.update(status="degraded", database="unreachable")
        return JSONResponse(status_code=503, content=body)
    return JSONResponse(status_code=200, content=body)
