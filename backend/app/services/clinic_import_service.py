"""
Clinic data import (FR 3.1, NFR 6, UML B.5 steps 1-3).

Accepts a CSV of ANONYMISED, AGGREGATED visit counts: one row per facility,
condition category and reporting period. Nothing else is allowed in.

File rules
  * Only the columns in ALLOWED_COLUMNS may appear. Any other column rejects
    the whole file. Columns that look like patient data (name, phone, date of
    birth, ID number, ...) are named as such in the error.
  * Text values are scanned: a phone number or email address in any field
    rejects the file.
  * visit_count is a whole number >= 0; periods are 1-31 days (weekly or
    monthly, D10), not in the future; condition_category is one of the
    ConditionCategory values.
  * A facility code seen for the first time needs facility_name, area_code,
    latitude and longitude (to find nearby reports). For known facilities
    those columns may be blank; when given, they update the facility.

The import is ALL OR NOTHING: if any row has a problem, nothing is stored
and every problem is listed (up to MAX_ERRORS). The attempt itself is always
recorded as a ClinicImportBatch (ACCEPTED or REJECTED) and in the audit log.

Re-importing the same facility + condition + period replaces the old count
(corrections from the clinic), and the summary says how many rows were new
and how many were updated.
"""

import csv
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ClinicImportBatch, ClinicVisitSummary, Facility, User
from app.models.enums import ConditionCategory, ImportBatchStatus
from app.services import audit_service

ALLOWED_COLUMNS = [
    "facility_code",
    "facility_name",
    "area_code",
    "latitude",
    "longitude",
    "condition_category",
    "period_start",
    "period_end",
    "visit_count",
]
REQUIRED_COLUMNS = {
    "facility_code",
    "condition_category",
    "period_start",
    "period_end",
    "visit_count",
}

# Column names that suggest individual-level data (checked as substrings)
PERSONAL_DATA_HINTS = [
    "patient",
    "name",
    "surname",
    "dob",
    "birth",
    "age",
    "sex",
    "gender",
    "phone",
    "mobile",
    "msisdn",
    "email",
    "national",
    "id_no",
    "idno",
    "id_number",
    "passport",
    "nhif",
    "sha_",
    "insurance",
    "address",
    "village",
    "residence",
    "record",
    "mrn",
    "file_no",
    "diagnosis",
    "notes",
    "comment",
    "occupation",
]

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 50_000
MAX_ERRORS = 100
MAX_PERIOD_DAYS = 31

_PHONE = re.compile(r"(?:\+?\d[\s-]?){9,}")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
_CODE = re.compile(r"^[A-Za-z0-9._-]{1,50}$")


class ImportFileError(Exception):
    """The file can't be read at all (too big, not CSV, wrong encoding)."""


@dataclass
class ParsedRow:
    line: int
    facility_code: str
    facility_name: str | None
    area_code: str | None
    latitude: float | None
    longitude: float | None
    condition: ConditionCategory
    period_start: date
    period_end: date
    visit_count: int


@dataclass
class ImportOutcome:
    batch: ClinicImportBatch
    errors: list[dict] = field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.batch.status == ImportBatchStatus.ACCEPTED


class _Errors:
    def __init__(self):
        self.items: list[dict] = []
        self.total = 0

    def add(self, row: int | None, field_name: str | None, message: str):
        self.total += 1
        if len(self.items) < MAX_ERRORS:
            self.items.append({"row": row, "field": field_name, "message": message})

    def as_list(self) -> list[dict]:
        if self.total > len(self.items):
            extra = self.total - len(self.items)
            return self.items + [
                {"row": None, "field": None, "message": f"...and {extra} more problems"}
            ]
        return self.items


def _header_problem(column: str) -> str:
    lowered = column.lower()
    if lowered in ALLOWED_COLUMNS:
        return ""
    if any(hint in lowered for hint in PERSONAL_DATA_HINTS):
        return (
            f'Column "{column}" looks like individual patient information. '
            "Only aggregated counts may be imported; remove this column."
        )
    return f'Column "{column}" is not allowed. Allowed columns: {", ".join(ALLOWED_COLUMNS)}.'


def _decode(raw: bytes) -> str:
    if len(raw) > MAX_FILE_BYTES:
        raise ImportFileError("The file is larger than 5 MB. Split it into smaller files.")
    if not raw.strip():
        raise ImportFileError("The file is empty.")
    try:
        return raw.decode("utf-8-sig")  # tolerates the BOM Excel adds
    except UnicodeDecodeError:
        raise ImportFileError("The file must be saved as CSV UTF-8.") from None


def _looks_personal(value: str) -> bool:
    return bool(_PHONE.search(value) or _EMAIL.search(value))


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse(raw: bytes, today: date) -> tuple[list[ParsedRow], _Errors]:
    errors = _Errors()
    reader = csv.DictReader(io.StringIO(_decode(raw)))
    header = [h.strip() for h in (reader.fieldnames or [])]
    if not header:
        raise ImportFileError("The file has no header row.")
    for column in header:
        problem = _header_problem(column)
        if problem:
            errors.add(1, column, problem)
    missing = REQUIRED_COLUMNS - {h.lower() for h in header}
    for column in sorted(missing):
        errors.add(1, column, f'Required column "{column}" is missing.')
    if errors.total:
        return [], errors  # don't read rows of a file with a bad structure
    reader.fieldnames = [h.lower() for h in header]

    rows: list[ParsedRow] = []
    seen: set[tuple] = set()
    for index, record in enumerate(reader):
        line = index + 2  # header is line 1
        if index >= MAX_ROWS:
            errors.add(None, None, f"The file has more than {MAX_ROWS} rows.")
            break
        if None in record:  # more cells than headers
            errors.add(line, None, "This row has more values than there are columns.")
            continue
        values = {k: (v or "").strip() for k, v in record.items()}
        if not any(values.values()):
            continue  # blank line
        for key in ("facility_code", "facility_name", "area_code"):
            if values.get(key) and _looks_personal(values[key]):
                errors.add(line, key, "Looks like a phone number or email address (personal data).")
        row = _parse_row(line, values, today, errors)
        if row is None:
            continue
        key = (row.facility_code, row.condition, row.period_start, row.period_end)
        if key in seen:
            errors.add(
                line, None, "Duplicate row: same facility, condition and period as an earlier row."
            )
            continue
        seen.add(key)
        rows.append(row)
    if not rows and not errors.total:
        errors.add(None, None, "The file has no data rows.")
    return rows, errors


def _parse_row(line: int, v: dict[str, str], today: date, errors: _Errors) -> ParsedRow | None:
    before = errors.total
    code = v.get("facility_code", "")
    if not _CODE.match(code):
        errors.add(line, "facility_code", "Use 1-50 letters, digits, dot, dash or underscore.")

    condition = None
    try:
        condition = ConditionCategory(v.get("condition_category", "").upper())
    except ValueError:
        allowed = ", ".join(c.value for c in ConditionCategory)
        errors.add(line, "condition_category", f"Must be one of: {allowed}.")

    start = _parse_date(v.get("period_start", ""))
    end = _parse_date(v.get("period_end", ""))
    if start is None:
        errors.add(line, "period_start", "Use a date like 2026-09-07.")
    if end is None:
        errors.add(line, "period_end", "Use a date like 2026-09-13.")
    if start and end:
        days = (end - start).days + 1
        if days < 1:
            errors.add(line, "period_end", "period_end is before period_start.")
        elif days > MAX_PERIOD_DAYS:
            errors.add(
                line, "period_end", "A period can be at most 31 days (weekly or monthly counts)."
            )
        if end > today:
            errors.add(line, "period_end", "The period has not finished yet.")

    count = None
    raw_count = v.get("visit_count", "")
    if re.fullmatch(r"\d{1,7}", raw_count):
        count = int(raw_count)
    else:
        errors.add(line, "visit_count", "Must be a whole number of visits (0 or more).")

    lat = lng = None
    for key in ("latitude", "longitude"):
        raw = v.get(key, "")
        if not raw:
            continue
        try:
            number = float(raw)
        except ValueError:
            errors.add(line, key, "Must be a number in decimal degrees, e.g. -1.2921.")
            continue
        limit = 90 if key == "latitude" else 180
        if not -limit <= number <= limit:
            errors.add(line, key, f"Must be between -{limit} and {limit}.")
        elif key == "latitude":
            lat = number
        else:
            lng = number
    if (lat is None) != (lng is None) and errors.total == before:
        errors.add(line, "latitude", "Give both latitude and longitude, or neither.")

    if errors.total > before:
        return None
    return ParsedRow(
        line=line,
        facility_code=code,
        facility_name=v.get("facility_name") or None,
        area_code=(v.get("area_code") or None),
        latitude=lat,
        longitude=lng,
        condition=condition,
        period_start=start,
        period_end=end,
        visit_count=count,
    )


def import_csv(db: Session, admin: User, filename: str, raw: bytes, today: date) -> ImportOutcome:
    """Validate and store the file. Commits. Raises ImportFileError for unreadable files."""
    rows, errors = parse(raw, today)

    facilities: dict[str, Facility] = {}
    if rows:
        codes = {r.facility_code for r in rows}
        facilities = {
            f.external_code: f
            for f in db.scalars(select(Facility).where(Facility.external_code.in_(codes)))
        }
        first_line: dict[str, ParsedRow] = {}
        for r in rows:
            first_line.setdefault(r.facility_code, r)
        for code, r in first_line.items():
            if code in facilities:
                continue
            for key, value in (
                ("facility_name", r.facility_name),
                ("area_code", r.area_code),
                ("latitude", r.latitude),
            ):
                if value is None:
                    errors.add(
                        r.line,
                        key,
                        f'"{code}" is a new facility: facility_name, area_code, latitude and '
                        "longitude are needed the first time it appears.",
                    )
                    break

    batch = ClinicImportBatch(
        id=uuid.uuid4(),
        filename=filename[:255] or "upload.csv",
        imported_by=admin.id,
        status=ImportBatchStatus.REJECTED if errors.total else ImportBatchStatus.ACCEPTED,
        row_count=len(rows) if not errors.total else 0,
        errors=errors.as_list() or None,
    )
    db.add(batch)

    if errors.total:
        audit_service.record(
            db,
            actor_id=admin.id,
            action="clinic_data.rejected",
            entity_type="clinic_import_batch",
            entity_id=batch.id,
            details={"filename": batch.filename, "problems": errors.total},
        )
        db.commit()
        return ImportOutcome(batch=batch, errors=batch.errors or [])

    created_codes: set[str] = set()
    updated_codes: set[str] = set()
    for r in rows:
        f = facilities.get(r.facility_code)
        if f is None:
            f = Facility(
                external_code=r.facility_code,
                name=r.facility_name,
                area_code=r.area_code,
                latitude=r.latitude,
                longitude=r.longitude,
            )
            db.add(f)
            facilities[r.facility_code] = f
            created_codes.add(r.facility_code)
        elif r.facility_code not in created_codes:
            for attr, value in (
                ("name", r.facility_name),
                ("area_code", r.area_code),
                ("latitude", r.latitude),
                ("longitude", r.longitude),
            ):
                if value is not None and getattr(f, attr) != value:
                    setattr(f, attr, value)
                    updated_codes.add(r.facility_code)
    db.flush()

    facility_ids = {f.id for f in facilities.values()}
    existing = {
        (fid, cond, start, end)
        for fid, cond, start, end in db.execute(
            select(
                ClinicVisitSummary.facility_id,
                ClinicVisitSummary.condition_category,
                ClinicVisitSummary.period_start,
                ClinicVisitSummary.period_end,
            ).where(ClinicVisitSummary.facility_id.in_(facility_ids))
        )
    }
    replaced = sum(
        1
        for r in rows
        if (facilities[r.facility_code].id, r.condition, r.period_start, r.period_end) in existing
    )

    stmt = insert(ClinicVisitSummary).values(
        [
            {
                "id": uuid.uuid4(),
                "facility_id": facilities[r.facility_code].id,
                "import_batch_id": batch.id,
                "condition_category": r.condition.value,
                "period_start": r.period_start,
                "period_end": r.period_end,
                "visit_count": r.visit_count,
            }
            for r in rows
        ]
    )
    db.execute(
        stmt.on_conflict_do_update(
            constraint="uq_clinic_visit_summaries_facility_condition_period",
            set_={"visit_count": stmt.excluded.visit_count, "import_batch_id": batch.id},
        )
    )

    batch.summary = {
        "rows": len(rows),
        "rows_inserted": len(rows) - replaced,
        "rows_updated": replaced,
        "facilities_created": len(created_codes),
        "facilities_updated": len(updated_codes),
        "small_counts": sum(1 for r in rows if 0 < r.visit_count < 5),
    }
    audit_service.record(
        db,
        actor_id=admin.id,
        action="clinic_data.imported",
        entity_type="clinic_import_batch",
        entity_id=batch.id,
        details={"filename": batch.filename, **batch.summary},
    )
    db.commit()
    return ImportOutcome(batch=batch)


TEMPLATE_CSV = (
    ",".join(ALLOWED_COLUMNS)
    + "\n"
    + "KE-12345,Example Health Centre,NBI-EXAMPLE,-1.2921,36.8219,"
    + "RESPIRATORY,2026-09-07,2026-09-13,18\n"
    + "KE-12345,,,,,SKIN,2026-09-07,2026-09-13,6\n"
)
