# TraceHealth API

The API is a FastAPI application. Its **live, always-current reference** is the
interactive Swagger page at `http://localhost:8000/docs` (and ReDoc at
`/redoc`) while the backend is running. This page is the overview: who may call
what, how to authenticate, and the conventions every endpoint follows.

## Authentication

1. `POST /auth/login` with `{"identifier": "<phone or email>", "password": "..."}`.
   The answer contains an `access_token` (valid 15 minutes), a `refresh_token`
   (30 days) and the user with their roles.
2. Send `Authorization: Bearer <access_token>` on every other request.
3. When a request answers **401**, call `POST /auth/refresh` with the refresh
   token. You get a new pair; the old refresh token stops working (rotation).
   Presenting an old refresh token again logs that user out everywhere (D21).
4. `POST /auth/logout` revokes the refresh token for this device.

In Swagger, click **Authorize** and paste an access token.

## Roles

| Role | Typical user | Main endpoints |
|---|---|---|
| `REPORTER` | community member (mobile app) | `POST /reports`, `/reports/{id}/sync`, `/reports/my-reports`, `/notifications`, `PATCH /auth/me` (payout consent) |
| `VERIFIER` | trained community verifier (mobile app) | `/reports/pending`, `/reports/flagged`, `/reports/{id}/verify`, `/reject`, `/flag`, `/nearby` |
| `AGENCY_STAFF` | county health / environment officer (dashboard) | `/dashboard/*`, `/health-linkage`, `/health-linkage/trends`, `/clinic-data`, `/facilities`, `GET /reports` (**VERIFIED only**) |
| `ADMINISTRATOR` | project administrator (dashboard) | everything agency staff can do, plus `/admin/*`, `/clinic-data/import`, `/health-linkage/compute`, `/payouts/*` |

Roles are checked against the database on every request (D22), so removing a
role or deactivating an account takes effect immediately.

## Conventions

- **JSON** everywhere except photo upload (`multipart/form-data`), the clinic
  CSV upload, the photo download (`image/jpeg`) and the CSV template.
- **Errors** use FastAPI's shape: `{"detail": "plain-language message"}`, or for
  validation errors (422) `{"detail": [{"loc": [...], "msg": "..."}]}`.
  Messages are written to be shown to people as they are.
- **Status codes**: 201 created, 200 already received (idempotent sync),
  401 not logged in / token expired, 403 role not allowed, 404 not found or not
  visible to you, 409 conflict (e.g. already decided, role still in use),
  413 photo too large, 422 invalid input, 503 service busy (retry after the
  `Retry-After` seconds).
- **Paging**: list endpoints take `limit` and `offset` and answer
  `{"items": [...], "total": n, "limit": l, "offset": o}`.
- **Dates**: ISO 8601. Timestamps carry a time zone; clinic periods are dates.
- **Health-linkage responses** always carry a `notice` saying results are
  statistical associations, not proof of causation.
- **Small counts**: clinic visit counts under the `dashboard.small_count_threshold`
  setting (default 5) are returned as `null` with `suppressed: true` (D11).

## Endpoints

### System

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Service and database health check |

### Authentication

| Method | Path | What it does |
|---|---|---|
| POST | `/auth/register` | Create a Community Reporter account |
| POST | `/auth/login` | Log in with phone/email and password |
| POST | `/auth/refresh` | Exchange a refresh token |
| POST | `/auth/logout` | Revoke this device's session |
| GET | `/auth/me` | The logged-in user and their roles |
| PATCH | `/auth/me` | Update my language, name or payout details |

### Verification

| Method | Path | What it does |
|---|---|---|
| GET | `/zones` | Active verifier zones |
| GET | `/reports` | Search reports |
| GET | `/reports/pending` | Reports waiting for review |
| GET | `/reports/flagged` | Flagged reports awaiting a final decision |
| GET | `/reports/{report_id}/nearby` | Reports close in place and time (possible duplicates) |
| POST | `/reports/{report_id}/verify` | Confirm a report |
| POST | `/reports/{report_id}/reject` | Reject a report |
| POST | `/reports/{report_id}/flag` | Flag a report (e.g. possible duplicate) for a second review |

### Pollution reports

| Method | Path | What it does |
|---|---|---|
| POST | `/reports` | Submit a pollution report |
| POST | `/reports/{client_report_id}/sync` | Sync a report from the phone's offline queue |
| GET | `/reports/my-reports` | My submitted reports |
| GET | `/reports/{report_id}` | One report |
| GET | `/reports/{report_id}/photo` | Report photo (JPEG) |

### Notifications

| Method | Path | What it does |
|---|---|---|
| GET | `/notifications` | My notifications |
| POST | `/notifications/{notification_id}/read` | Mark a notification read |
| POST | `/notifications/read-all` | Mark all notifications read |
| POST | `/devices/push-token` | Register this phone for push |
| DELETE | `/devices/push-token` | Stop push to this phone |

### Clinic data

| Method | Path | What it does |
|---|---|---|
| POST | `/clinic-data/import` | Import anonymised, aggregated clinic visit counts (CSV) |
| GET | `/clinic-data/imports` | Past imports |
| GET | `/clinic-data/template.csv` | Example CSV with the allowed columns |
| GET | `/clinic-data` | Imported visit counts |
| GET | `/facilities` | Facilities |

### Health linkage

| Method | Path | What it does |
|---|---|---|
| POST | `/health-linkage/compute` | Recompute all health linkages |
| GET | `/health-linkage` | Health-linkage results |
| GET | `/health-linkage/trends` | Linkage summary and clusters |

### Dashboard

| Method | Path | What it does |
|---|---|---|
| GET | `/dashboard/overview` | Headline statistics |
| GET | `/dashboard/reports` | Verified reports for the map |
| GET | `/dashboard/heatmap` | Verified report density |
| GET | `/dashboard/trends` | Weekly reports and clinic visits |

### Administration

| Method | Path | What it does |
|---|---|---|
| GET | `/admin/users` | List users |
| POST | `/admin/users` | Create a user |
| PATCH | `/admin/users/{user_id}` | Update a user |
| GET | `/admin/audit-logs` | Audit log (newest first) |
| GET | `/admin/settings` | System settings |
| PATCH | `/admin/settings/{key}` | Change a setting (linkage settings trigger a recompute) |
| GET | `/admin/zones` | All zones, including inactive |
| POST | `/admin/zones` | Create a zone |
| PATCH | `/admin/zones/{code}` | Update a zone |

### Payouts

| Method | Path | What it does |
|---|---|---|
| GET | `/payouts` | Payout monitoring |
| GET | `/payouts/{payout_id}` | One payout |
| POST | `/payouts/trigger` | Send payouts now |
| POST | `/payouts/{payout_id}/retry` | Retry a failed payout |

### Not in Swagger: M-Pesa callbacks

`POST /payouts/callbacks/mpesa/result/{token}` and
`POST /payouts/callbacks/mpesa/timeout/{token}` receive Safaricom's B2C results.
They are hidden from the public schema, need no login (Safaricom cannot log
in), and are protected by the long random `MPESA_CALLBACK_TOKEN` in the path,
compared in constant time. Duplicate or unknown callbacks are acknowledged and
ignored, so Safaricom's retries can never pay twice.

## Example: submit a report from the command line

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"identifier":"0700000005","password":"ChangeMe123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST localhost:8000/reports -H "Authorization: Bearer $TOKEN" \
  -F client_report_id=$(python -c "import uuid;print(uuid.uuid4())") \
  -F category=OPEN_BURNING -F latitude=-1.2580 -F longitude=36.8960 \
  -F captured_at=$(date -u +%Y-%m-%dT%H:%M:%SZ) -F "description=Burning near the market" \
  -F photo=@photo.jpg
```
