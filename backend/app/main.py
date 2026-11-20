"""
TraceHealth API entry point.

Run locally with:  uvicorn app.main:app --reload
Interactive API documentation (Swagger UI) is served at /docs.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.api.health import router as health_router
from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.clinic_data import router as clinic_data_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health_linkage import router as health_linkage_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.payouts import router as payouts_router
from app.api.routes.reports import router as reports_router
from app.api.routes.verification import router as verification_router
from app.core.background import periodic_jobs_loop
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(periodic_jobs_loop()) if settings.BACKGROUND_JOBS_ENABLED else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend for TraceHealth: community pollution reporting, verification, "
        "clinic-data health linkage and incentive payouts."
    ),
    # Hide the interactive docs in production; they stay available in development
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PoolTimeoutError)
@app.exception_handler(OperationalError)
async def database_busy(_: Request, exc: Exception) -> JSONResponse:
    # The database is overloaded or unreachable: say so with 503 + Retry-After
    # (the phone's offline queue retries automatically) instead of a bare 500
    logging.getLogger("tracehealth").warning("Database unavailable: %s", exc)
    return JSONResponse(
        {"detail": "The service is busy. Please try again in a moment."},
        status_code=503,
        headers={"Retry-After": "5"},
    )


app.include_router(health_router)
app.include_router(auth_router)
# Must come before reports_router: /reports/pending vs /reports/{id}
app.include_router(verification_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(clinic_data_router)
app.include_router(health_linkage_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(payouts_router)
