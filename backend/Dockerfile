# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prom

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY . .

# Run as an unprivileged user. Code stays root-owned (read-only to the app);
# the user only needs its home (HF tokenizer cache) and the metrics dir.
RUN useradd --create-home --uid 10001 arc \
    && mkdir -p /tmp/prom && chown arc:arc /tmp/prom
USER arc

# API image default; workers override the command in compose/k8s.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ready || exit 1

CMD ["uvicorn", "arc.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
