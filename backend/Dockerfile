# TraceHealth API image (production). Build from the repository root:
#   docker compose -f docker-compose.prod.yml build
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Only runtime dependencies: the test and lint tools are left out of the image
COPY requirements.txt .
RUN grep -vE '^(pytest|ruff)==' requirements.txt > requirements.runtime.txt \
 && pip install -r requirements.runtime.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

# Run as an unprivileged user; photos are written to the mounted volume
RUN useradd --create-home --uid 10001 tracehealth \
 && mkdir -p /data/uploads && chown -R tracehealth /data
USER tracehealth

ENV UPLOAD_DIR=/data/uploads
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/health', timeout=4).status == 200 else 1)"

# Migrations, optional demo data, then the API (see scripts/start.sh)
CMD ["sh", "scripts/start.sh"]
