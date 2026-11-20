# TraceHealth

Community pollution reporting linked to aggregated clinic data, so health and
environmental agencies can prioritise cleanup and advisories by health impact.

Built from the *TraceHealth Proposal and SRS* (Collins Gathungu, ALU).

> **Status: Sprint 1 complete.** Login and registration, role-based access,
> report submission with photo and GPS, offline queue with automatic sync,
> and the reporter mobile app (English and Swahili). Verification arrives in
> Sprint 3.

## Repository layout

```
tracehealth/
├── backend/            FastAPI API, SQLAlchemy models, Alembic migrations, tests
├── dashboard/          React web dashboard            (created in Sprint 4)
├── mobile/             React Native / Expo app (Expo SDK 58)
├── docs/               Decisions, methods, traceability matrix
├── infra/              Docker support files
├── docker-compose.yml  Local PostgreSQL + PostGIS
└── .env.example        Template for your local .env (never commit .env)
```

## Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Git | any recent | `git --version` |
| Python | 3.12 | `python --version` (Windows) / `python3 --version` |
| Docker Desktop | any recent | `docker --version` and `docker compose version` |
| VS Code | any recent | recommended extensions are suggested on first open |
| Node.js | 22 LTS | `node --version` (for the mobile app) |
| Expo Go app | SDK 58 | install from the Play Store on your Android phone |

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
| `verifier2@example.org` | Verifier and reporter |
| `verifier1@example.org` | Verifier |
| `agency@example.org` | Agency staff |
| `admin@example.org` | Administrator |

## Mobile app

```bash
cd mobile
npm install
cp .env.example .env            # Windows: Copy-Item .env.example .env
#    set EXPO_PUBLIC_API_URL to http://<your computer's Wi-Fi IP>:8000
npx expo start                  # scan the QR code with Expo Go
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

- Health check: http://localhost:8000/health
- Interactive API docs (Swagger): http://localhost:8000/docs

## Backend tests

```bash
cd backend
pytest                  # all tests (uses the separate tracehealth_test database)
ruff check . && ruff format --check .     # code style
```

The tests rebuild `tracehealth_test` from the migrations on every run, so they
always check the real schema. Your development database is never touched.

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
| Phone app says "No connection" | Check `EXPO_PUBLIC_API_URL`, start uvicorn with `--host 0.0.0.0`, then restart `npx expo start` (env values are read at start) |
| `npx expo install` fails behind a proxy | Use `npm install <pkg>@<version>` with the version from `node_modules/expo/bundledNativeModules.json` |

## Data and safety principles

- Clinic data is aggregated and anonymised only; the schema has no place for individual patients.
- All seed data is synthetic. Mock payouts are labelled `MOCK` and are never real payments.
- Health linkages are statistical associations, not proof that pollution caused illness.
- Secrets live only in `.env` / environment variables.

See `docs/decisions.md` for the approved design decisions and
`docs/traceability-matrix.md` for SRS requirement coverage.
