"""Modules 2 and 3: report submission, photos, idempotent sync, visibility."""

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.models import AuditLog, Notification, PollutionReport
from app.models.enums import VerificationDecision
from tests.conftest import auth_headers
from tests.factories import decide, make_payout, make_user
from tests.photos import jpeg_bytes, png_bytes


def fields(**overrides):
    data = {
        "client_report_id": str(uuid.uuid4()),
        "category": "OPEN_BURNING",
        "latitude": "-1.2921",
        "longitude": "36.8219",
        "captured_at": datetime.now(UTC).isoformat(),
        "description": "  Smoke from a burning heap  ",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def submit(client, user, photo=None, path="/reports", **overrides):
    return client.post(
        path,
        data=fields(**overrides),
        files={"photo": ("photo.jpg", photo if photo is not None else jpeg_bytes(), "image/jpeg")},
        headers=auth_headers(user),
    )


@pytest.fixture
def reporter(db):
    return make_user(db, "REPORTER")


# ---------- Submitting -----------------------------------------------------


def test_submit_report_is_stored_as_pending(client, db, reporter):
    r = submit(client, reporter)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["already_received"] is False
    report = body["report"]
    assert report["status"] == "PENDING"
    assert report["sync_status"] == "SUBMITTED_ONLINE"
    assert report["latitude"] == pytest.approx(-1.2921)
    assert report["description"] == "Smoke from a burning heap"  # trimmed
    assert report["photo_url"] == f"/reports/{report['id']}/photo"
    assert "reporter_id" not in report  # identity is not exposed


def test_resending_the_same_report_never_duplicates(client, db, reporter):
    client_id = str(uuid.uuid4())
    first = submit(client, reporter, client_report_id=client_id)
    second = submit(client, reporter, client_report_id=client_id)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["already_received"] is True
    assert second.json()["report"]["id"] == first.json()["report"]["id"]
    count = db.scalar(
        select(func.count())
        .select_from(PollutionReport)
        .where(PollutionReport.client_report_id == uuid.UUID(client_id))
    )
    assert count == 1


def test_offline_sync_endpoint_marks_report_as_synced_from_offline(client, reporter):
    client_id = str(uuid.uuid4())
    r = submit(
        client,
        reporter,
        path=f"/reports/{client_id}/sync",
        client_report_id=None,
        created_offline="true",
    )
    assert r.status_code == 201, r.text
    assert r.json()["report"]["client_report_id"] == client_id
    assert r.json()["report"]["sync_status"] == "SYNCED_FROM_OFFLINE"
    # The queue retrying after a dropped connection gets the same report back
    again = submit(
        client,
        reporter,
        path=f"/reports/{client_id}/sync",
        client_report_id=None,
        created_offline="true",
    )
    assert again.status_code == 200
    assert again.json()["report"]["id"] == r.json()["report"]["id"]


def test_report_id_used_by_another_reporter_is_refused(client, db, reporter):
    client_id = str(uuid.uuid4())
    submit(client, reporter, client_report_id=client_id)
    r = submit(client, make_user(db, "REPORTER"), client_report_id=client_id)
    assert r.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "VOLCANO"},
        {"latitude": "95"},
        {"longitude": "-200"},
        {"latitude": None},
        {"captured_at": "2026-11-08T09:30:00"},  # no timezone
        {"captured_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat()},
        {"captured_at": (datetime.now(UTC) - timedelta(days=45)).isoformat()},
        {"description": "x" * 1001},
        {"client_report_id": "not-a-uuid"},
    ],
)
def test_invalid_reports_are_refused(client, reporter, overrides):
    assert submit(client, reporter, **overrides).status_code == 422


def test_photo_is_required(client, reporter):
    r = client.post("/reports", data=fields(), headers=auth_headers(reporter))
    assert r.status_code == 422


@pytest.mark.parametrize("bad", [b"", b"this is not an image", jpeg_bytes()[:200]])
def test_unreadable_photos_are_refused(client, reporter, bad):
    r = submit(client, reporter, photo=bad)
    assert r.status_code == 422
    assert "photo" in r.json()["detail"].lower()


def test_oversized_photo_is_refused(client, reporter, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "MAX_PHOTO_MB", 0)
    assert submit(client, reporter).status_code == 413


def test_no_file_is_kept_when_a_report_is_refused(client, reporter, isolated_uploads):
    submit(client, reporter, captured_at="2026-11-08T09:30:00")
    assert not isolated_uploads.exists() or not any(isolated_uploads.rglob("*.jpg"))


# ---------- Photo privacy (D12) --------------------------------------------


def test_photo_metadata_is_stripped_and_image_resized(client, reporter):
    original = jpeg_bytes(size=(4000, 3000), with_gps_exif=True)
    assert Image.open(io.BytesIO(original)).getexif().get_ifd(0x8825)  # GPS present
    report = submit(client, reporter, photo=original).json()["report"]
    r = client.get(report["photo_url"], headers=auth_headers(reporter))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    stored = Image.open(io.BytesIO(r.content))
    assert len(stored.getexif()) == 0  # no GPS, camera model or timestamps
    assert max(stored.size) == 1600


def test_photo_orientation_is_applied_before_stripping(client, reporter):
    # EXIF orientation 6 = "rotate 90° clockwise to display"
    photo = jpeg_bytes(size=(400, 200), orientation=6)
    report = submit(client, reporter, photo=photo).json()["report"]
    stored = Image.open(
        io.BytesIO(client.get(report["photo_url"], headers=auth_headers(reporter)).content)
    )
    assert stored.size == (200, 400)


def test_png_photos_are_accepted_and_converted(client, reporter):
    report = submit(client, reporter, photo=png_bytes()).json()["report"]
    r = client.get(report["photo_url"], headers=auth_headers(reporter))
    assert Image.open(io.BytesIO(r.content)).format == "JPEG"


# ---------- Verifier notification and audit (B.3 step 6) -------------------


def test_verifiers_are_notified_but_not_the_reporter(client, db):
    both = make_user(db, "REPORTER", "VERIFIER")
    other_verifier = make_user(db, "VERIFIER")
    inactive_verifier = make_user(db, "VERIFIER")
    inactive_verifier.is_active = False
    db.flush()
    report_id = submit(client, both).json()["report"]["id"]
    recipients = set(
        db.scalars(
            select(Notification.user_id).where(
                Notification.related_report_id == uuid.UUID(report_id)
            )
        )
    )
    assert recipients == {other_verifier.id}


def test_submission_is_audited(client, db, reporter):
    report_id = submit(client, reporter).json()["report"]["id"]
    entry = db.scalar(select(AuditLog).where(AuditLog.entity_id == uuid.UUID(report_id)))
    assert entry.action == "report.submitted"
    assert entry.actor_id == reporter.id


# ---------- Reading reports -----------------------------------------------


def test_my_reports_lists_only_my_reports_newest_first(client, db, reporter):
    now = datetime.now(UTC)
    submit(client, reporter, captured_at=(now - timedelta(days=2)).isoformat(), category="OTHER")
    submit(client, reporter, captured_at=now.isoformat(), category="MEDICAL_WASTE")
    submit(client, make_user(db, "REPORTER"))
    page = client.get("/reports/my-reports", headers=auth_headers(reporter)).json()
    assert page["total"] == 2
    assert [i["category"] for i in page["items"]] == ["MEDICAL_WASTE", "OTHER"]


def test_my_reports_shows_decision_reason_and_test_payout(client, db, reporter):
    verifier = make_user(db, "VERIFIER")
    a = submit(client, reporter).json()["report"]
    b = submit(client, reporter).json()["report"]
    report_a = db.get(PollutionReport, uuid.UUID(a["id"]))
    report_b = db.get(PollutionReport, uuid.UUID(b["id"]))
    make_payout(db, report_a, decide(db, report_a, verifier, VerificationDecision.VERIFIED))
    decide(db, report_b, verifier, VerificationDecision.REJECTED, reason="Photo too blurry")

    items = {
        i["id"]: i
        for i in client.get("/reports/my-reports", headers=auth_headers(reporter)).json()["items"]
    }
    assert items[a["id"]]["status"] == "VERIFIED"
    assert items[a["id"]]["payout"]["is_test_payment"] is True
    assert items[a["id"]]["payout"]["status"] == "PENDING"
    assert items[b["id"]]["status"] == "REJECTED"
    assert items[b["id"]]["decision_reason"] == "Photo too blurry"
    assert items[b["id"]]["payout"] is None

    filtered = client.get(
        "/reports/my-reports?status=REJECTED", headers=auth_headers(reporter)
    ).json()
    assert [i["id"] for i in filtered["items"]] == [b["id"]]


def test_other_reporters_cannot_see_my_report_or_photo(client, db, reporter):
    report = submit(client, reporter).json()["report"]
    stranger = auth_headers(make_user(db, "REPORTER"))
    assert client.get(f"/reports/{report['id']}", headers=stranger).status_code == 404
    assert client.get(report["photo_url"], headers=stranger).status_code == 404
    assert client.get(f"/reports/{uuid.uuid4()}", headers=stranger).status_code == 404


def test_verifier_can_view_pending_report_and_photo(client, db, reporter):
    report = submit(client, reporter).json()["report"]
    verifier = auth_headers(make_user(db, "VERIFIER"))
    assert client.get(f"/reports/{report['id']}", headers=verifier).status_code == 200
    assert client.get(report["photo_url"], headers=verifier).status_code == 200


def test_agency_staff_see_only_verified_reports(client, db, reporter):
    report = submit(client, reporter).json()["report"]
    staff = auth_headers(make_user(db, "AGENCY_STAFF"))
    assert client.get(f"/reports/{report['id']}", headers=staff).status_code == 404
    decide(
        db,
        db.get(PollutionReport, uuid.UUID(report["id"])),
        make_user(db, "VERIFIER"),
        VerificationDecision.VERIFIED,
    )
    r = client.get(f"/reports/{report['id']}", headers=staff)
    assert r.status_code == 200
    assert r.json()["payout"] is None  # payouts are not shown to agency staff


# ---------- Role-based access (NFR 1) --------------------------------------


@pytest.mark.parametrize("role", ["VERIFIER", "AGENCY_STAFF", "ADMINISTRATOR"])
def test_only_reporters_can_submit(client, db, role):
    assert submit(client, make_user(db, role)).status_code == 403
    r = client.get("/reports/my-reports", headers=auth_headers(make_user(db, role)))
    assert r.status_code == 403


def test_anonymous_requests_are_refused(client):
    assert client.post("/reports", data=fields()).status_code == 401
    assert client.get("/reports/my-reports").status_code == 401
