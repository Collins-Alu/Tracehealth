"""FR 3.1 / NFR 6: clinic data import accepts only anonymised, aggregated counts."""

from sqlalchemy import func, select

from app.models import AuditLog, ClinicImportBatch, ClinicVisitSummary, Facility
from app.services.clinic_import_service import ALLOWED_COLUMNS
from tests.conftest import auth_headers
from tests.factories import make_user

HEADER = ",".join(ALLOWED_COLUMNS)
GOOD = (
    HEADER
    + """
KE-001,Test Clinic,AREA-1,-1.2550,36.8980,RESPIRATORY,2026-09-07,2026-09-13,18
KE-001,,,,,SKIN,2026-09-07,2026-09-13,3
KE-001,,,,,respiratory,2026-09-14,2026-09-20,21
"""
)


def upload(client, user, text: str, name="counts.csv"):
    return client.post(
        "/clinic-data/import",
        files={"file": (name, text.encode("utf-8"), "text/csv")},
        headers=auth_headers(user),
    )


def test_valid_file_is_stored_with_a_summary_and_audited(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    r = upload(client, admin, GOOD)
    assert r.status_code == 201, r.text
    batch = r.json()["batch"]
    assert batch["status"] == "ACCEPTED"
    assert batch["summary"]["rows_inserted"] == 3
    assert batch["summary"]["facilities_created"] == 1
    assert batch["summary"]["small_counts"] == 1
    assert r.json()["linkage"] is not None  # B.5: linkage recomputed after import
    assert db.scalar(select(func.count()).select_from(ClinicVisitSummary)) == 3
    assert db.scalar(select(Facility.name)) == "Test Clinic"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "clinic_data.imported"))


def test_patient_columns_reject_the_whole_file(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    bad = GOOD.replace("visit_count", "visit_count,patient_name").replace(",18\n", ",18,Jane Doe\n")
    r = upload(client, admin, bad)
    assert r.status_code == 422
    body = r.json()
    assert body["batch"]["status"] == "REJECTED"
    assert "individual patient information" in body["batch"]["errors"][0]["message"]
    assert db.scalar(select(func.count()).select_from(ClinicVisitSummary)) == 0
    # The rejected attempt is still recorded
    assert db.scalar(select(ClinicImportBatch.status)) == "REJECTED"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "clinic_data.rejected"))


def test_identifier_hints_and_unknown_columns_are_explained(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    for column, expected in [
        ("date_of_birth", "individual patient information"),
        ("national_id", "individual patient information"),
        ("phone", "individual patient information"),
        ("ward", "is not allowed"),
    ]:
        text = (
            HEADER + f",{column}\nKE-001,Clinic,A,-1.2,36.8,RESPIRATORY,2026-09-07,2026-09-13,5,x\n"
        )
        r = upload(client, admin, text)
        assert r.status_code == 422, column
        assert expected in r.json()["batch"]["errors"][0]["message"], column


def test_personal_data_hidden_in_allowed_columns_is_caught(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    text = HEADER + "\nKE-001,Call 0712 345 678,A,-1.2,36.8,RESPIRATORY,2026-09-07,2026-09-13,5\n"
    r = upload(client, admin, text)
    assert r.status_code == 422
    assert "personal data" in r.json()["batch"]["errors"][0]["message"]


def test_row_errors_are_all_listed_and_nothing_is_stored(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    text = (
        HEADER
        + """
KE-001,Clinic,A,-1.2,36.8,FEVER,2026-09-07,2026-09-13,5
KE-001,Clinic,A,-1.2,36.8,RESPIRATORY,2026-09-13,2026-09-07,5
KE-001,Clinic,A,-1.2,36.8,RESPIRATORY,2026-09-01,2026-10-30,5
KE-001,Clinic,A,-1.2,36.8,SKIN,2026-09-07,2026-09-13,-4
KE-001,Clinic,A,-1.2,36.8,SKIN,2026-09-07,2026-09-13,2.5
KE-002,,,,,SKIN,2026-09-07,2026-09-13,4
KE-001,Clinic,A,-1.2,36.8,MALARIA,2099-01-01,2099-01-07,4
"""
    )
    r = upload(client, admin, text)
    assert r.status_code == 422
    problems = {(e["row"], e["field"]) for e in r.json()["batch"]["errors"]}
    assert (2, "condition_category") in problems
    assert (3, "period_end") in problems  # end before start
    assert (4, "period_end") in problems  # longer than a month
    assert (5, "visit_count") in problems
    assert (6, "visit_count") in problems
    assert (7, "facility_name") in problems  # new facility without details
    assert (8, "period_end") in problems  # future period
    assert db.scalar(select(func.count()).select_from(ClinicVisitSummary)) == 0


def test_duplicate_rows_in_one_file_are_rejected(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    line = "KE-001,Clinic,A,-1.2,36.8,SKIN,2026-09-07,2026-09-13,5\n"
    r = upload(client, admin, HEADER + "\n" + line + line)
    assert r.status_code == 422
    assert "Duplicate row" in r.json()["batch"]["errors"][0]["message"]


def test_reimport_updates_counts_instead_of_duplicating(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    upload(client, admin, GOOD)
    corrected = GOOD.replace(",18\n", ",20\n")
    r = upload(client, admin, corrected)
    assert r.status_code == 201
    assert r.json()["batch"]["summary"]["rows_updated"] == 3
    assert r.json()["batch"]["summary"]["rows_inserted"] == 0
    assert db.scalar(select(func.count()).select_from(ClinicVisitSummary)) == 3
    assert db.scalar(select(func.max(ClinicVisitSummary.visit_count))) == 21


def test_unreadable_files_get_a_plain_message(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    assert "empty" in upload(client, admin, "").json()["detail"]
    r = client.post(
        "/clinic-data/import",
        files={"file": ("x.csv", "é".encode("latin-1"), "text/csv")},
        headers=auth_headers(admin),
    )
    assert "UTF-8" in r.json()["detail"]


def test_excel_bom_and_uppercase_headers_are_accepted(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    text = "﻿" + GOOD.replace("facility_code", "FACILITY_CODE")
    assert upload(client, admin, text).status_code == 201


def test_only_administrators_can_import(client, db):
    for role in ["AGENCY_STAFF", "VERIFIER", "REPORTER"]:
        assert upload(client, make_user(db, role), GOOD).status_code == 403


def test_small_counts_are_suppressed_when_listed(client, db):
    upload(client, make_user(db, "ADMINISTRATOR"), GOOD)
    staff = make_user(db, "AGENCY_STAFF")
    page = client.get("/clinic-data?condition=SKIN", headers=auth_headers(staff)).json()
    assert page["items"][0]["visit_count"] is None
    assert page["items"][0]["suppressed"] is True
    assert page["small_count_threshold"] == 5


def test_template_and_facilities_and_import_history(client, db):
    admin = make_user(db, "ADMINISTRATOR")
    template = client.get("/clinic-data/template.csv", headers=auth_headers(admin))
    assert template.text.startswith(HEADER)
    assert upload(client, admin, template.text.replace("2026-09-", "2026-08-")).status_code == 201
    facilities = client.get("/facilities", headers=auth_headers(admin)).json()
    assert facilities[0]["summaries"] == 2
    history = client.get("/clinic-data/imports", headers=auth_headers(admin)).json()
    assert history[0]["imported_by_name"] == admin.full_name
