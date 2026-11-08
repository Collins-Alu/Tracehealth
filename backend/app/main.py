"""
TraceHealth API entry point.

Run locally with:  uvicorn app.main:app --reload
Interactive API documentation (Swagger UI) is served at /docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
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

app.include_router(health_router)

