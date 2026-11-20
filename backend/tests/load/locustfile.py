"""
Load test for NFR 2: 200 concurrent reporters.

Each simulated reporter logs in once, then behaves like the mobile app:
mostly checking "My reports" and the inbox, sometimes submitting a report
with a photo. Runs against a DEVELOPMENT or STAGING server seeded with
scripts/seed.py; it creates real (synthetic) reports, so never point it at
production. Re-seed afterwards: python -m scripts.seed --reset

    pip install -r requirements-load.txt
    locust -f tests/load/locustfile.py --host http://localhost:8000 \
           --headless -u 200 -r 20 -t 2m --csv load-results

Pass mark used in docs/testing.md: no failed requests and a 95th-percentile
response time under 2 seconds for reads and under 5 seconds for submissions.
"""

import io
import os
import random
import uuid
from datetime import UTC, datetime

from locust import HttpUser, between, task
from PIL import Image

PASSWORD = os.environ.get("SEED_DEFAULT_PASSWORD", "ChangeMe123!")
REPORTERS = ["+254700000005", "+254700000006", "+254700000007"]  # seeded, synthetic
CATEGORIES = ["OPEN_BURNING", "ILLEGAL_DUMPING", "BLOCKED_DRAINAGE", "MEDICAL_WASTE", "OTHER"]
NAIROBI = (-1.2921, 36.8219)


def _photo() -> bytes:
    """A small, valid JPEG (a typical phone photo is resized by the app first)."""
    buffer = io.BytesIO()
    colour = tuple(random.randint(40, 200) for _ in range(3))
    Image.new("RGB", (800, 600), colour).save(buffer, "JPEG", quality=70)
    return buffer.getvalue()


PHOTOS = [_photo() for _ in range(5)]


class Reporter(HttpUser):
    wait_time = between(2, 6)  # people pause between screens

    def on_start(self):
        res = self.client.post(
            "/auth/login",
            json={"identifier": random.choice(REPORTERS), "password": PASSWORD},
            name="/auth/login",
        )
        res.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"

    @task(5)
    def my_reports(self):
        self.client.get("/reports/my-reports?limit=20", name="/reports/my-reports")

    @task(4)
    def inbox(self):
        self.client.get("/notifications?limit=20", name="/notifications")

    @task(2)
    def profile(self):
        self.client.get("/auth/me", name="/auth/me")

    @task(1)
    def submit_report(self):
        lat = NAIROBI[0] + random.uniform(-0.05, 0.05)
        lng = NAIROBI[1] + random.uniform(-0.05, 0.05)
        self.client.post(
            "/reports",
            data={
                "client_report_id": str(uuid.uuid4()),
                "category": random.choice(CATEGORIES),
                "latitude": f"{lat:.6f}",
                "longitude": f"{lng:.6f}",
                "captured_at": datetime.now(UTC).isoformat(),
                "description": "Load test (synthetic)",
            },
            files={"photo": ("photo.jpg", random.choice(PHOTOS), "image/jpeg")},
            name="/reports [submit]",
        )
