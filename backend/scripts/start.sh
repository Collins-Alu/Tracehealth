#!/bin/sh
# Container start-up: apply migrations, optionally load the demo data, start the API.
#
#   PORT              port to listen on (Render sets it; default 8000)
#   WEB_CONCURRENCY   API worker processes (default 4; use 1 on 512 MB free plans)
#   SEED_DEMO_DATA    "true" = load the SYNTHETIC demo data once, if the database
#                     is empty (public demo only; never with real users)
set -e

alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python -m scripts.seed --if-empty
fi

# --proxy-headers: trust X-Forwarded-* from the proxy in front (HTTPS ends there)
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-4}" \
  --proxy-headers --forwarded-allow-ips "*"
