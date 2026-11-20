# TraceHealth

Community pollution reporting linked to aggregated clinic data, so health and
environmental agencies can prioritise cleanup and advisories by health impact.

Built from the *TraceHealth Proposal and SRS* (Collins Gathungu, ALU).

> **Status: Sprint 0 complete.** Database schema, migrations, database-enforced
> business rules, seed data, API skeleton and CI. Authentication and reporting
> arrive in Sprints 1–2.

## Repository layout

```
tracehealth/
├── backend/            FastAPI API, SQLAlchemy models, Alembic migrations, tests
├── dashboard/          React web dashboard            (created in Sprint 4)
├── mobile/             React Native / Expo app        (created in Sprint 1)
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

## First-time setup

All commands are run in the VS Code terminal (**Terminal → New Terminal**).

```bash
# 1. Create your private environment file
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
#    then open .env and change POSTGRES_PASSWORD in all three places it appears

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
uvicorn app.main:app --reload             # API on http://localhost:8000
```

- Health check: http://localhost:8000/health
- Interactive API docs (Swagger): http://localhost:8000/docs

## Tests

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

## Data and safety principles

- Clinic data is aggregated and anonymised only; the schema has no place for individual patients.
- All seed data is synthetic. Mock payouts are labelled `MOCK` and are never real payments.
- Health linkages are statistical associations, not proof that pollution caused illness.
- Secrets live only in `.env` / environment variables.

See `docs/decisions.md` for the approved design decisions and
`docs/traceability-matrix.md` for SRS requirement coverage.
