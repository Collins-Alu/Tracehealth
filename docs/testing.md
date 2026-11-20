# Testing

| Level | Tool | Where | Count (final run) | Command |
|---|---|---|---|---|
| Unit | pytest | `backend/tests/unit/` | part of 230 | `cd backend && pytest tests/unit` |
| Database rules and migrations | pytest | `backend/tests/db/` | part of 230 | `pytest tests/db` |
| API / integration | pytest + FastAPI TestClient | `backend/tests/integration/` | part of 230 | `pytest tests/integration` |
| Mobile unit and component | Jest + React Native Testing Library | `mobile/src/**/__tests__/` | 62 | `cd mobile && npx jest` |
| Dashboard component | Vitest + Testing Library | `dashboard/tests/` | 16 | `cd dashboard && npx vitest run` |
| End to end | Playwright (Chrome, Edge) | `dashboard/e2e/` | 4 per browser | `cd dashboard && npm run e2e` |
| Load | Locust | `backend/tests/load/locustfile.py` | 200 users | see below |

All of these except the load test run in CI on every push
(`.github/workflows/ci.yml`): backend (lint, migrations, tests), mobile
(typecheck, tests), dashboard (typecheck, tests, build) and E2E in Google
Chrome and Microsoft Edge.

## Backend

The tests use a separate database (`TEST_DATABASE_URL`), rebuilt from the
Alembic migrations at the start of each run, so they always test the real
schema, constraints and triggers. Outside providers are replaced by the mock
adapters through FastAPI dependency overrides; nothing leaves the machine.

Notable tests:

- `tests/db/test_business_rules.py`: the database itself refuses
  self-verification, a second final decision, a payout for an unverified
  report or without consent, a linkage for an unverified report, and any edit
  of the audit log.
- `tests/unit/test_linkage_stats.py`: the exact Poisson test and Spearman
  correlation against known values (validated against SciPy during
  development).
- `tests/integration/test_health_linkage.py`: rises give SIGNAL, flat data
  NO_SIGNAL, missing data INSUFFICIENT_DATA **with no statistics**.
- `tests/integration/test_clinic_import.py`: patient columns, phone/email values
  and bad rows reject the whole file; re-imports replace counts.
- `tests/integration/test_payouts.py` and `tests/unit/test_mpesa_adapter.py`:
  mock success and failure, retries with backoff, UNKNOWN never retried,
  M-Pesa callbacks (success, failure, duplicate, wrong token), stale expiry.

## End-to-end (Playwright)

The E2E tests drive the **built** dashboard in a real browser against the real
API and the synthetic seed data.

```bash
# terminal 1: API with seed data
cd backend && python -m scripts.seed --reset && uvicorn app.main:app
# terminal 2
cd dashboard
npm run e2e          # Google Chrome
npm run e2e:all      # Chrome and Microsoft Edge (Edge must be installed)
```

Playwright builds the dashboard and starts `vite preview` on port 4173 itself
(or reuses one already running). First time only:
`npx playwright install chrome` (and `msedge`).

| Spec | Checks |
|---|---|
| `lifecycle.spec.ts` | UML B.6 end to end: reporter submits a report (with photo) → Dandora verifier confirms → mock payout paid → administrator sees it Verified with a **Test** reward and its health linkage → payout list shows the MOCK reference → audit log shows the decision |
| `access.spec.ts` | Agency staff: no administration links, administration URLs redirect, only verified reports, no status filter. Reporter accounts are refused at sign-in. |
| `clinic-import.spec.ts` | A CSV with a `patient_name` column is refused as a whole and the clinic in it is not created |

The lifecycle test adds one report each run; re-seed with
`python -m scripts.seed --reset` whenever you want a clean database.

## Load test (NFR 2: 200 concurrent reporters)

```bash
cd backend
pip install -r requirements-load.txt
python -m scripts.seed --reset
uvicorn app.main:app --workers 4 --port 8000      # BACKGROUND_JOBS_ENABLED=false for a clean measurement
locust -f tests/load/locustfile.py --host http://localhost:8000 \
       --headless -u 200 -r 20 -t 3m --reset-stats --csv load-results
python -m scripts.seed --reset                      # remove the load-test reports
```

Each simulated reporter logs in once and then, with 2–6 s pauses, opens "My
reports" (5×), the inbox (4×), their profile (2×) and submits a report with an
800×600 photo (1×).

### Result (development sandbox, 19 Nov 2026)

Setup: API with 4 workers, PostgreSQL 16 and Locust **all on one 2-vCPU
machine**, so Locust competed with the API for the same CPUs. A real server
would do better; these are cautious numbers.

| Request | Requests | 50 % | 95 % | 99 % |
|---|---|---|---|---|
| `GET /reports/my-reports` | 3 292 | 19 ms | 46 ms | 5.9 s |
| `GET /notifications` | 2 648 | 14 ms | 38 ms | 6.0 s |
| `GET /auth/me` | 1 335 | 11 ms | 34 ms | 5.8 s |
| `POST /reports` (with photo) | 651 | 33 ms | 61 ms | 5.8 s |
| `POST /auth/login` | 143 | 10 s | 12 s | 14 s |

8 of 8 069 requests (0.1 %) were answered 503 "busy, try again"; no request
failed with a server error.

**What this shows**

- With 200 reporters active, 95 % of normal app requests, including photo
  submissions, finish in well under 0.1 s. NFR 2 is met for normal use.
- **Logins are slow when 200 people log in within ten seconds.** Each password
  check uses Argon2id, which is deliberately expensive; 200 at once saturate
  2 CPUs, and that is also what causes the slow 1 % tail for other requests
  during the burst. In real use people log in once and the app then renews
  its session with refresh tokens, so such a burst is unlikely. If it matters
  for the pilot (e.g. a training session where everyone logs in together),
  use a 4-vCPU server or stagger the logins.

**Problem found and fixed by the load test.** The first run gave 0.9 % server
errors: 4 workers × 30 database connections exceeded PostgreSQL's limit of 100.
The pool is now 5 + 10 per worker (60 in total), waits up to 10 s for a free
connection, and answers 503 with `Retry-After` instead of 500 if the database
is overloaded (the phone's offline queue retries automatically).

Re-run the test on the staging server before the pilot and record the result
here.

## Manual checks done in development

- Every dashboard page viewed at 1440 px and 390 px wide, signed in as an
  administrator and as agency staff, against the seed data.
- Map tiles need internet access; in an offline sandbox the map shows the
  markers on a grey background.
