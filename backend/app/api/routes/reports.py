"""
/reports endpoints (Modules 2 and 3).

POST /reports                      submit a report (photo + form fields)
POST /reports/{client_id}/sync     the same, keyed by the phone's report id;
                                   used by the offline queue
GET  /reports/my-reports           the logged-in reporter's reports + payout state
GET  /reports/{id}                 one report (permission-checked)
GET  /reports/{id}/photo           the report photo (permission-checked)

The verifier list endpoints (GET /reports, GET /reports/pending) and the
verify/reject/flag decisions are added in Sprint 3.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import Role, get_current_user, require_roles
from app.db.session import get_db
from app.models import User
from app.models.enums import PollutionCategory, ReportStatus
from app.schemas.report import NewReportFields, ReportFields, ReportOut, ReportPage, SubmitResult
from app.services import photo_storage, report_service
from app.services.report_service import ReportError

router = APIRouter(prefix="/reports", tags=["Pollution reports"])

reporter_only = require_roles(Role.REPORTER)


def _validated(model, **values):
    """Build the Pydantic model so its rules apply; errors become normal 422s."""
    try:
        return model(**values)
    except ValidationError as exc:
        raise RequestValidationError(
            [{**e, "loc": ("body", *e["loc"])} for e in exc.errors(include_url=False)]
        ) from None


# Multipart form fields are declared one by one (FastAPI cannot yet combine a
# form *model* with a file upload); they are then validated by ReportFields.
def report_form(
    category: Annotated[PollutionCategory, Form()],
    latitude: Annotated[float, Form()],
    longitude: Annotated[float, Form()],
    captured_at: Annotated[datetime, Form(description="ISO 8601 with timezone")],
    description: Annotated[str | None, Form(max_length=1000)] = None,
    created_offline: Annotated[bool, Form()] = False,
) -> ReportFields:
    return _validated(
        ReportFields,
        category=category,
        latitude=latitude,
        longitude=longitude,
        captured_at=captured_at,
        description=description,
        created_offline=created_offline,
    )


def new_report_form(
    client_report_id: Annotated[uuid.UUID, Form(description="UUID generated on the phone")],
    fields: Annotated[ReportFields, Depends(report_form)],
) -> NewReportFields:
    return NewReportFields(client_report_id=client_report_id, **fields.model_dump())


async def _read_photo(photo: UploadFile) -> bytes:
    limit = get_settings().MAX_PHOTO_MB * 1024 * 1024
    data = await photo.read(limit + 1)  # never read more than the limit into memory
    if len(data) > limit:
        raise HTTPException(
            413, f"The photo is too large. The limit is {get_settings().MAX_PHOTO_MB} MB."
        )
    return data


def _submit(
    db: Session,
    user: User,
    client_report_id: uuid.UUID,
    fields: ReportFields,
    photo_bytes: bytes,
    response: Response,
    via_sync: bool,
) -> SubmitResult:
    try:
        outcome = report_service.submit_report(
            db, user, client_report_id, fields, photo_bytes, via_sync=via_sync
        )
    except ReportError as exc:
        raise HTTPException(exc.status_code, exc.message) from None
    response.status_code = 201 if outcome.created else 200
    return SubmitResult(
        report=report_service.report_out(db, user, outcome.report),
        already_received=not outcome.created,
    )


@router.post(
    "",
    response_model=SubmitResult,
    status_code=201,
    summary="Submit a pollution report",
    responses={200: {"description": "This report was already received; nothing new stored"}},
)
async def submit_report(
    response: Response,
    fields: Annotated[NewReportFields, Depends(new_report_form)],
    photo: Annotated[UploadFile, File(description="JPEG, PNG or WebP photo")],
    user: User = Depends(reporter_only),
    db: Session = Depends(get_db),
) -> SubmitResult:
    photo_bytes = await _read_photo(photo)
    return _submit(db, user, fields.client_report_id, fields, photo_bytes, response, via_sync=False)


@router.post(
    "/{client_report_id}/sync",
    response_model=SubmitResult,
    status_code=201,
    summary="Sync a report from the phone's offline queue",
    responses={200: {"description": "Already synced earlier; nothing new stored"}},
)
async def sync_report(
    client_report_id: uuid.UUID,
    response: Response,
    fields: Annotated[ReportFields, Depends(report_form)],
    photo: Annotated[UploadFile, File(description="JPEG, PNG or WebP photo")],
    user: User = Depends(reporter_only),
    db: Session = Depends(get_db),
) -> SubmitResult:
    photo_bytes = await _read_photo(photo)
    return _submit(db, user, client_report_id, fields, photo_bytes, response, via_sync=True)


@router.get("/my-reports", response_model=ReportPage, summary="My submitted reports")
def my_reports(
    status: ReportStatus | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(reporter_only),
    db: Session = Depends(get_db),
) -> ReportPage:
    return report_service.list_my_reports(db, user, status, limit, offset)


@router.get("/{report_id}", response_model=ReportOut, summary="One report")
def get_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    try:
        report = report_service.get_visible_report(db, user, report_id)
    except ReportError as exc:
        raise HTTPException(exc.status_code, exc.message) from None
    return report_service.report_out(db, user, report)


@router.get(
    "/{report_id}/photo",
    response_class=FileResponse,
    summary="Report photo (JPEG)",
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_report_photo(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    try:
        report = report_service.get_visible_report(db, user, report_id)
    except ReportError as exc:
        raise HTTPException(exc.status_code, exc.message) from None
    path = photo_storage.open_photo_path(report.photo_url)
    if path is None:
        raise HTTPException(404, "The photo for this report is not available.")
    # private: browsers may cache it, shared proxies may not
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"}
    )
