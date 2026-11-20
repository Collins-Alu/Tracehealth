# TraceHealth

Community pollution reporting linked to aggregated clinic data, so health and
environmental agencies can prioritise cleanup and advisories by health impact.

Built from the *TraceHealth Proposal and SRS* (Collins Gathungu, ALU).

> **Status: all five sprints complete (0–4).** Mobile reporting with offline
> sync, verification, clinic data import, health linkage, the web dashboard,
> incentive payouts (mock by default, M-Pesa Daraja sandbox-ready), tests at
> every level and deployment files. See `docs/changelog.md` for what each
> sprint added.

## Try it online (no installation)

| What | Link |
|---|---|
| Web dashboard | https://tracehealth-bpqa.netlify.app |
| API and interactive docs | https://tracehealth-api-4msu.onrender.com/docs |
| Android app (APK) | https://github.com/Collins-Alu/tracehealth/releases/download/v1.0.0/TraceHealth-1.0.0.apk (GitHub Releases) |
| SRS document |  |

> The demo uses **synthetic data only** and payouts are **test payments**
> (no real money). The API runs on a free plan that sleeps when idle: the first
> request after a quiet spell can take **up to a minute**. If the dashboard or
> app seems stuck, open https://tracehealth-api-4msu.onrender.com/health once, wait for `"status": "ok"`,
> then try again.

Demo logins (password for all: `ChangeMe123!`):

| Login | Role | Use it in |
|---|---|---|
| `admin@example.org` | Administrator | dashboard |
| `agency@example.org` | Agency staff | dashboard |
| `verifier1@example.org` | Verifier (Dandora zone) | Android app |
| `0700000005` | Reporter | Android app |

You can also register a new reporter account in the app.

### Install the Android app

1. On an Android phone (Android 8 or newer), open https://github.com/Collins-Alu/tracehealth/releases/download/v1.0.0/TraceHealth-1.0.0.apk and download
   `TraceHealth-1.0.0.apk`.
2. Open the downloaded file. If Android asks, allow your browser to
   **install unknown apps** (Settings → Apps → your browser → Install unknown apps).
3. Tap **Install**, then **Open**.
4. Choose English or Kiswahili, then log in with a demo account above or
   register as a reporter.
5. Allow camera and location when you submit your first report.

The demo app uses in-app notifications (the **Inbox** tab); phone push
alerts are switched off on the free demo.

## Repository layout

```
tracehealth/
├── backend/                 FastAPI API, models, Alembic migrations, tests, Dockerfile
├── dashboard/               React + TypeScript web dashboard, Vitest and Playwright tests
├── mobile/                  React Native / Expo app (Expo SDK 58)
├── docs/                    Architecture, method, API, data protection, deployment,
│                            testing, user guide, UML, decisions, traceability, changelog
├── infra/                   PostgreSQL init script, Caddy (HTTPS + dashboard)
├── docker-compose.yml       Local PostgreSQL + PostGIS
├── docker-compose.prod.yml  Production stack (see docs/deployment.md)
├── .env.example             Template for your local .env (never commit .env)
└── .env.production.example  Template for the server
```

## Prerequisites

You only need these to run TraceHealth on your own computer.

| Tool | Version | Check with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | 3.12 or 3.13 | `python --version` (Windows) / `python3 --version` |
| Docker (with Compose) | any recent | `docker --version` and `docker compose version` |
| Node.js | 22 LTS | `node --version` (mobile app and dashboard) |
| VS Code | any recent | recommended extensions are suggested on first open |
| Expo Go app | SDK 58 | Play Store, on your Android phone (or use the APK above) |

Installing them:

```bash
# Manjaro / Arch
sudo pacman -S --needed git python nodejs-lts-jod npm docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER          # then log out and back in

# Ubuntu / Debian
sudo apt install git python3 python3-venv
# Node.js 22: https://nodejs.org/en/download  Docker: https://docs.docker.com/engine/install/ubuntu/

# Windows / macOS
# Install Git, Python 3.12, Node.js 22 LTS and Docker Desktop from their websites.
```

## Get the code

```bash
git clone https://github.com/Collins-Alu/tracehealth.git
cd tracehealth
code .                                 # open in VS Code
```

## First-time setup

All commands are run in the VS Code terminal (**Terminal → New Terminal**).

```bash
# 1. Create your private environment file
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
#    then open .env and:
#    - change POSTGRES_PASSWORD in all three places it appears
#    - set JWT_SECRET_KEY to the output of:
#        python -c "import secrets; print(secrets.token_urlsafe(48))"

# 2. Start PostgreSQL + PostGIS
docker compose up -d
docker compose ps               # wait until the db service shows "healthy"

# 3. Create the Python virtual environment and install dependencies
cd backend
python -m venv .venv            # macOS/Linux: python3 -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# 4. Build the database schema
alembic upgrade head

# 5. (Optional) Load synthetic development data
python -m scripts.seed
```

## Daily development

```bash
docker compose up -d                      # from the repo root
cd backend && <activate the venv>
alembic upgrade head                      # after pulling new migrations
uvicorn app.main:app --reload --host 0.0.0.0   # API on port 8000
```

`--host 0.0.0.0` lets your phone reach the API over Wi-Fi. Without it the API
only answers on `localhost`.

Development logins after `python -m scripts.seed` (password `ChangeMe123!`):

| Login | Role |
|---|---|
| `0700000005`, `0700000006`, `0700000007` | Reporter |
| `verifier2@example.org` | Verifier (Mukuru zone) and reporter |
| `verifier1@example.org` | Verifier (Dandora zone) |
| `agency@example.org` | Agency staff |
| `admin@example.org` | Administrator |

## Web dashboard

```bash
cd dashboard
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000 (the default)
npm run dev                     # http://localhost:5173
```

Sign in as `admin@example.org` or `agency@example.org` (password `ChangeMe123!`
after seeding). Reporter and verifier accounts use the mobile app instead.

Dashboard checks:

```bash
npx tsc -b           # typecheck
npx vitest run       # component tests
npm run build        # production build into dist/
npm run e2e          # end-to-end in Google Chrome (API must be running with seed data)
```

## Mobile app

```bash
cd mobile
npm install
cp .env.example .env            # Windows: Copy-Item .env.example .env
#    set EXPO_PUBLIC_API_URL to http://<your computer's Wi-Fi IP>:8000
npx expo start --go             # scan the QR code with Expo Go
```

The phone and computer must be on the same Wi-Fi. If the app can't reach the
API, open `http://<your IP>:8000/health` in the phone's browser first. If that
fails, allow port 8000 through your computer's firewall (Windows asks the first
time uvicorn runs; choose "Private networks").

Mobile checks:

```bash
npx tsc --noEmit     # typecheck
npx jest             # unit and component tests
```

- When the API runs on your own computer: health check `http://localhost:8000/health` and Swagger docs `http://localhost:8000/docs` (these only work locally).
- Online demo: [health check](https://tracehealth-api-4msu.onrender.com/health) and [Swagger docs](https://tracehealth-api-4msu.onrender.com/docs).

### Push notifications (optional)

In Expo Go, notifications appear in the app's **Inbox** tab only: Expo Go on
Android cannot receive push notifications. To get phone alerts:

```bash
npm install -g eas-cli
eas login                      # free Expo account
eas init                       # adds your project id to app.json
eas build --profile development --platform android
```

Install the APK it produces, start the backend with `PUSH_PROVIDER=expo` in
`.env`, and run `npx expo start --dev-client`. The Account tab shows
"Phone alerts and inbox" when push is active.

### SMS fallback (optional)

With `SMS_PROVIDER=mock` (default) SMS messages are only logged. To use the
Africa's Talking sandbox, set `SMS_PROVIDER=africastalking`, `AT_USERNAME=sandbox`
and `AT_API_KEY` in `.env` (see `.env.example`). Sandbox messages appear in the
Africa's Talking simulator, not on real phones.

## Backend tests

```bash
cd backend
pytest                  # all tests (uses the separate tracehealth_test database)
ruff check . && ruff format --check .     # code style
```

The tests rebuild `tracehealth_test` from the migrations on every run, so they
always check the real schema. Your development database is never touched.

## End-to-end and load tests

See `docs/testing.md`. In short: start the API with seed data, then
`cd dashboard && npm run e2e` (Chrome) or `npm run e2e:all` (Chrome + Edge).
The load test uses Locust: `pip install -r backend/requirements-load.txt`.

## Payouts

`PAYOUT_PROVIDER=MOCK` (default) pays nobody: payouts get a `MOCK-` reference
and a **Test** badge. Phone numbers ending in `0000` simulate a failed payment.
To try the M-Pesa Daraja sandbox, follow `docs/deployment.md` §8.

## Deployment

- **Public demo on free hosting** (Render + Neon + Netlify + an APK on GitHub
  Releases): `docs/hosting-guide.md`, step by step.
- **Pilot on your own server:** `docs/deployment.md` covers a single-server deployment with Docker Compose,
HTTPS via Caddy, backups, the mobile release build and switching on real
push, SMS and M-Pesa.

## Database migrations

```bash
alembic upgrade head                           # apply all migrations
alembic downgrade -1                           # undo the latest migration
alembic revision --autogenerate -m "message"   # after changing a model
alembic check                                  # confirm models and DB agree
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `port is already allocated` | Change `POSTGRES_PORT` in `.env` (and the port in both URLs) |
| `database "tracehealth_test" does not exist` | The volume predates the init script: `docker compose exec db psql -U tracehealth -c "CREATE DATABASE tracehealth_test;"` |
| `password authentication failed` | The password in `.env` changed after the volume was created: `docker compose down -v` then `docker compose up -d` (deletes local data) |
| PowerShell blocks `Activate.ps1` | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Apple Silicon "no matching manifest" | Uncomment `platform: linux/amd64` in `docker-compose.yml` |
| `JWT_SECRET_KEY ... at least 32 characters` | Set `JWT_SECRET_KEY` in `.env` (see setup step 1) |
| Phone app says "No connection" | Check `EXPO_PUBLIC_API_URL`, start uvicorn with `--host 0.0.0.0`, then restart `npx expo start --go` (env values are read at start) |
| Verifier list is empty | You may be filtered to your zone: tap **All zones**. Your own reports never appear in your review list. |
| Photos don't load in the review screen | Re-run `python -m scripts.seed --reset` (Sprint 2 seed generates placeholder photos) |
| `npx expo install` fails behind a proxy | Use `npm install <pkg>@<version>` with the version from `node_modules/expo/bundledNativeModules.json` |

## Data and safety principles

- Clinic data is aggregated and anonymised only; the schema has no place for individual patients.
- All seed data is synthetic. Mock payouts are labelled `MOCK` and are never real payments.
- Health linkages are statistical associations, not proof that pollution caused illness.
- Secrets live only in `.env` / environment variables.

## Documentation

| Document | What it covers |
|---|---|
| `docs/architecture.md` | Components, layers, main flows |
| `docs/health-linkage-method.md` | The statistical method in plain language, and its limits |
| `docs/api.md` | Authentication, roles, conventions, every endpoint (live: `/docs`) |
| `docs/data-protection.md` | What is collected, who sees what, safeguards, rights |
| `docs/hosting-guide.md` | Free public demo: GitHub, Neon, Render, Netlify, APK |
| `docs/deployment.md` | Server setup, backups, providers, pre-pilot checklist |
| `docs/testing.md` | Test levels, E2E, load-test results |
| `docs/user-guide.md` | Guides for reporters, verifiers, agency staff, administrators |
| `docs/uml/` | As-built class, sequence (B.3–B.6) and state diagrams |
| `docs/decisions.md` | Design decisions D1–D60 and deviations from the planned structure |
| `docs/traceability-matrix.md` | Each SRS requirement → code → tests |
| `docs/changelog.md` | What each sprint delivered, with its files |
