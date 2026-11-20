"""
Clinic data endpoints (Module 5; UML B.5 steps 1-6).

POST /clinic-data/import        upload a CSV (administrators)
GET  /clinic-data/imports       past imports, accepted and rejected
GET  /clinic-data/template.csv  an example file with the allowed columns
GET  /clinic-data               imported visit counts (small counts suppressed)
GET  /facilities                facilities that supply clinic data
"""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Role, require_roles
from app.db.session import get_db
from app.models import ClinicImportBatch, ClinicVisitSummary, Facility, User
from app.models.enums import ConditionCategory
from app.schemas.clinic import (
    FacilityOut,
    ImportBatchOut,
    ImportResult,
    LinkageRunOut,
    VisitSummaryOut,
    VisitSummaryPage,
)
from app.services import clinic_import_service, linkage_engine, setting_service
from app.services.clinic_import_service import ImportFileError

router = APIRouter(tags=["Clinic data"])

admin_only = require_roles(Role.ADMINISTRATOR)
analysts = require_roles(Role.ADMINISTRATOR, Role.AGENCY_STAFF)


def _batch_out(batch: ClinicImportBatch, name: str | None = None) -> ImportBatchOut:
    out = ImportBatchOut.model_validate(batch)
    out.imported_by_name = name
    return out


@router.post(
    "/clinic-data/import",
    response_model=ImportResult,
    status_code=201,
    summary="Import anonymised, aggregated clinic visit counts (CSV)",
    responses={422: {"description": "File rejected; nothing stored. Problems are listed."}},
)
async def import_clinic_data(
    file: UploadFile = File(description="CSV, UTF-8, max 5 MB"),
    admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    raw = await file.read(clinic_import_service.MAX_FILE_BYTES + 1)
    try:
        outcome = clinic_import_service.import_csv(
            db, admin, file.filename or "upload.csv", raw, today=datetime.now(UTC).date()
        )
    except ImportFileError as exc:
        raise HTTPException(422, str(exc)) from None
    if not outcome.accepted:
        body = ImportResult(batch=_batch_out(outcome.batch, admin.full_name))
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))
    # UML B.5 steps 4-6: link the new clinic data to verified reports
    run = linkage_engine.compute_safely(db)
    return ImportResult(
        batch=_batch_out(outcome.batch, admin.full_name),
        linkage=LinkageRunOut(**run.__dict__) if run else None,
    )


@router.get("/clinic-data/imports", response_model=list[ImportBatchOut], summary="Past imports")
def list_imports(
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(admin_only),
    db: Session = Depends(get_db),
) -> list[ImportBatchOut]:
    rows = db.execute(
        select(ClinicImportBatch, User.full_name)
        .join(User, User.id == ClinicImportBatch.imported_by)
        .order_by(ClinicImportBatch.created_at.desc())
        .limit(limit)
    ).all()
    return [_batch_out(b, name) for b, name in rows]


@router.get(
    "/clinic-data/template.csv",
    response_class=PlainTextResponse,
    summary="Example CSV with the allowed columns",
)
def template(_: User = Depends(admin_only)) -> PlainTextResponse:
    return PlainTextResponse(
        clinic_import_service.TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tracehealth-clinic-template.csv"'},
    )


@router.get("/clinic-data", response_model=VisitSummaryPage, summary="Imported visit counts")
def list_summaries(
    facility_code: str | None = None,
    area_code: str | None = None,
    condition: ConditionCategory | None = None,
    date_from: date | None = Query(None, description="periods ending on or after"),
    date_to: date | None = Query(None, description="periods starting on or before"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(analysts),
    db: Session = Depends(get_db),
) -> VisitSummaryPage:
    threshold = int(setting_service.get(db, "dashboard.small_count_threshold", 5))
    conditions = []
    if facility_code:
        conditions.append(Facility.external_code == facility_code)
    if area_code:
        conditions.append(Facility.area_code == area_code)
    if condition:
        conditions.append(ClinicVisitSummary.condition_category == condition)
    if date_from:
        conditions.append(ClinicVisitSummary.period_end >= date_from)
    if date_to:
        conditions.append(ClinicVisitSummary.period_start <= date_to)
    base = select(ClinicVisitSummary, Facility).join(
        Facility, Facility.id == ClinicVisitSummary.facility_id
    )
    total = db.scalar(select(func.count()).select_from(base.where(*conditions).subquery()))
    rows = db.execute(
        base.where(*conditions)
        .order_by(
            ClinicVisitSummary.period_start.desc(),
            Facility.external_code,
            ClinicVisitSummary.condition_category,
        )
        .limit(limit)
        .offset(offset)
    ).all()
    items = []
    for s, f in rows:
        small = 0 < s.visit_count < threshold  # D11: protect small groups
        items.append(
            VisitSummaryOut(
                id=s.id,
                facility_code=f.external_code,
                facility_name=f.name,
                area_code=f.area_code,
                condition_category=s.condition_category,
                period_start=s.period_start,
                period_end=s.period_end,
                visit_count=None if small else s.visit_count,
                suppressed=small,
            )
        )
    return VisitSummaryPage(
        items=items, total=total, limit=limit, offset=offset, small_count_threshold=threshold
    )


@router.get("/facilities", response_model=list[FacilityOut], summary="Facilities")
def list_facilities(
    _: User = Depends(analysts), db: Session = Depends(get_db)
) -> list[FacilityOut]:
    rows = db.execute(
        select(
            Facility,
            func.count(ClinicVisitSummary.id),
            func.max(ClinicVisitSummary.period_end),
        )
        .outerjoin(ClinicVisitSummary, ClinicVisitSummary.facility_id == Facility.id)
        .group_by(Facility.id)
        .order_by(Facility.name)
    ).all()
    out = []
    for f, count, latest in rows:
        item = FacilityOut.model_validate(f)
        item.summaries = count
        item.latest_period_end = latest
        out.append(item)
    return out
