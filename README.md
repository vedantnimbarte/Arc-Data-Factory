# ARC Data Factory

Production-grade platform for collecting, cleaning, deduplicating, classifying,
scoring, tokenizing, and sharding AI training datasets for ARC models
(300M → 1B → 10B+ roadmap).

- **Backend:** Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · Celery · Ray · PostgreSQL · Redis · MinIO (S3)
- **Frontend:** Next.js 15 · TypeScript · Tailwind · TanStack Query · Recharts
- **Dataset format:** Parquet · **Observability:** Prometheus + Grafana

---

## Table of contents

1. [Architecture at a glance](#architecture-at-a-glance)
2. [Repository layout](#repository-layout)
3. [Prerequisites](#prerequisites)
4. [Quick start (Docker Compose)](#quick-start-docker-compose)
5. [Configuration reference](#configuration-reference)
6. [Service endpoints & ports](#service-endpoints--ports)
7. [Detailed setup A — Docker Compose](#detailed-setup-a--docker-compose)
8. [Detailed setup B — local, without Docker](#detailed-setup-b--local-without-docker)
9. [Frontend dashboard](#frontend-dashboard)
10. [End-to-end walkthrough](#end-to-end-walkthrough-build-a-dataset)
11. [API reference](#api-reference)
12. [Running tests](#running-tests)
13. [Observability](#observability)
14. [Troubleshooting](#troubleshooting)
15. [Production notes](#production-notes)

---

## Architecture at a glance

The **API gateway** (control plane) only enqueues work and serves reads. An
**orchestrator** drives each `PipelineRun` stage-by-stage, one batch per Celery
task; a batch re-enqueues itself until the stage is drained, then advances to
the next stage. Heavy compute (dedup, tokenize) runs on **Ray** inside those
tasks. Document **payloads** live in S3-compatible object storage; PostgreSQL
holds only **metadata + lineage**.

```
sources → collect → clean → dedupe → compliance → classify
        → score → tokenize → shard → register → READY dataset (+ manifest)
```

Each stage is **resumable** (checkpoints persist a cursor), each dataset is
**versioned** (lineage parent + manifest), and every service **emits metrics**.

---

## Repository layout

```
arc-data-factory/
├─ backend/
│  ├─ arc/
│  │  ├─ core/         settings, async DB, S3 store, logging, metrics, hashing, Ray
│  │  ├─ security/     API-key auth, SSRF guard
│  │  ├─ db/           ORM models, enums, repositories, alembic/
│  │  ├─ contracts/    StageInput / StageResult (cross-service hand-off)
│  │  ├─ orchestrator/ DAG driver + Celery self-chaining task
│  │  ├─ services/     collector, cleaner, deduper, compliance, classifier,
│  │  │               scorer, tokenizer, sharder, registry
│  │  ├─ workers/      Celery app + per-stage queues
│  │  └─ api/          FastAPI app, routers, schemas, /metrics
│  ├─ tests/           unit/ + integration/
│  ├─ alembic.ini  ·  pyproject.toml  ·  Dockerfile  ·  .env.example
├─ frontend/           Next.js 15 dashboard (7 pages)
├─ infra/              docker-compose.yml, prometheus/
├─ docs/               product/spec docs (01–12)
└─ Makefile  ·  README.md
```

---

## Prerequisites

**Recommended path — Docker (everything containerized):**

| Tool | Version | Notes |
|------|---------|-------|
| Docker Engine | 24+ | Docker Desktop on Windows/macOS |
| Docker Compose | v2 | bundled with Docker Desktop |
| GNU Make | optional | convenience targets; otherwise run `docker compose` directly |

**Local path (no Docker) additionally needs:**

| Tool | Version |
|------|---------|
| Python | 3.12 |
| Node.js | 20+ (for the dashboard) |
| PostgreSQL | 16 |
| Redis | 7 |
| MinIO | latest (or any S3-compatible store) |

> Windows note: the Docker path is strongly recommended. Some backend deps
> (`asyncpg`, `ray`) are smoother on Linux containers than native Windows.

---

## Quick start (Docker Compose)

```bash
# 1. configure env
cp backend/.env.example backend/.env

# 2. build & start the whole stack (db, 2x redis, minio, prometheus, grafana, api, workers)
make up                      # == docker compose -f infra/docker-compose.yml up --build -d

# 3. migrations run automatically (the `migrate` service); wait ~20s then:
open http://localhost:8000/docs     # interactive API (Swagger UI)
```

Tear down with `make down`. Follow logs with `make logs`.

---

## Configuration reference

All settings are environment variables prefixed `ARC_` (parsed by
`backend/arc/core/config.py`). Copy `backend/.env.example` → `backend/.env`.

| Variable | Default (compose) | Purpose |
|----------|-------------------|---------|
| `ARC_ENVIRONMENT` | `dev` | `dev` \| `staging` \| `prod` |
| `ARC_LOG_JSON` | `true` | JSON logs (set `false` for pretty console) |
| `ARC_POSTGRES_HOST` | `postgres` | DB host |
| `ARC_POSTGRES_USER` / `_PASSWORD` / `_DB` | `arc` / `arc` / `arc` | DB creds |
| `ARC_REDIS_CACHE_URL` | `redis://redis-cache:6379/0` | cache (separate from broker) |
| `ARC_CELERY_BROKER_URL` | `redis://redis-broker:6379/0` | Celery broker |
| `ARC_CELERY_RESULT_BACKEND` | `redis://redis-broker:6379/1` | Celery results |
| `ARC_S3_ENDPOINT_URL` | `http://minio:9000` | S3 endpoint (set empty for real AWS) |
| `ARC_S3_ACCESS_KEY` / `_SECRET_KEY` | `minioadmin` / `minioadmin` | S3 creds |
| `ARC_S3_BUCKET_RAW` / `_DATASETS` | `arc-raw` / `arc-datasets` | buckets (auto-created) |
| `ARC_RAY_ADDRESS` | _(empty)_ | empty = local Ray; `ray://host:10001` for a cluster |
| `ARC_API_KEYS` | `["dev-key-change-me"]` | JSON list of accepted API keys |
| `ARC_ALLOW_COLLECTOR_PRIVATE_RANGES` | `false` | SSRF guard; keep `false` |
| `ARC_CREDENTIALS` | `{}` | JSON map of source credentials, looked up by a source's `credential_ref` (e.g. `{"github-main": "ghp_..."}`) |

**Authentication:** when `ARC_API_KEYS` is set, every `/api/*` call must send
`X-API-Key: <key>`. In `dev` **with no keys configured**, the API is open
(convenient for local exploration). `.env.example` ships a key, so the
examples below include the header.

---

## Service endpoints & ports

| Service | URL | Credentials |
|---------|-----|-------------|
| API (Swagger) | http://localhost:8000/docs | `X-API-Key: dev-key-change-me` |
| API metrics | http://localhost:8000/metrics | — |
| Dashboard | http://localhost:3000 | — |
| MinIO console | http://localhost:9001 | `minioadmin` / `minioadmin` |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | `admin` / `admin` |
| PostgreSQL | `localhost:5432` | `arc` / `arc` |
| Redis (broker) | `localhost:6380` | — |
| Redis (cache) | `localhost:6381` | — |

---

## Detailed setup A — Docker Compose

1. **Env file**

   ```bash
   cp backend/.env.example backend/.env
   # edit ARC_API_KEYS to your own secret before exposing anything
   ```

2. **Build & start**

   ```bash
   docker compose -f infra/docker-compose.yml up --build -d
   ```

   This launches: `postgres`, `redis-broker`, `redis-cache`, `minio`, a
   one-shot `migrate` job (`alembic upgrade head`), `api`, and **2 worker
   replicas** consuming every stage queue, plus `prometheus` and `grafana`.

3. **Verify health**

   ```bash
   curl http://localhost:8000/health/ready          # {"status":"ready"}
   docker compose -f infra/docker-compose.yml ps     # all services Up/healthy
   ```

4. **Re-run migrations manually** (e.g. after a model change)

   ```bash
   docker compose -f infra/docker-compose.yml run --rm migrate
   ```

5. **Scale workers**

   ```bash
   docker compose -f infra/docker-compose.yml up -d --scale worker=4
   ```

---

## Detailed setup B — local, without Docker

Use this when you want to run/debug the API or workers directly.

1. **Start the stateful services** (any way you like). Quickest is to run only
   those from compose and run Python on the host:

   ```bash
   docker compose -f infra/docker-compose.yml up -d postgres redis-broker redis-cache minio
   ```

   If you installed them natively instead, point the env vars at
   `localhost` and the host ports above.

2. **Create a virtualenv & install the backend (editable, with dev extras)**

   ```bash
   cd backend
   python3.12 -m venv .venv
   source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **Point env at localhost** — create `backend/.env`:

   ```ini
   ARC_ENVIRONMENT=dev
   ARC_POSTGRES_HOST=localhost
   ARC_REDIS_CACHE_URL=redis://localhost:6381/0
   ARC_CELERY_BROKER_URL=redis://localhost:6380/0
   ARC_CELERY_RESULT_BACKEND=redis://localhost:6380/1
   ARC_S3_ENDPOINT_URL=http://localhost:9000
   ARC_API_KEYS=["dev-key-change-me"]
   ```

4. **Run migrations**

   ```bash
   alembic upgrade head
   ```

5. **Run the API**

   ```bash
   uvicorn arc.api.main:app --reload --port 8000
   ```

6. **Run a Celery worker** (separate terminal, same venv + env)

   ```bash
   celery -A arc.workers.celery_app worker \
     -Q collect,clean,dedupe,compliance,classify,score,tokenize,shard,register,orchestrate \
     --concurrency 4 -l INFO
   ```

   Ray initializes **locally and automatically** the first time a dedup/tokenize
   task runs (because `ARC_RAY_ADDRESS` is empty). No separate Ray process is
   needed for single-node dev.

---

## Frontend dashboard

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

- The dev server proxies `/api/*` to the backend (default
  `http://localhost:8000`; override with `ARC_API_URL`).
- If the API requires a key, expose it to the browser client via
  `NEXT_PUBLIC_ARC_API_KEY=dev-key-change-me` (e.g. in `frontend/.env.local`).
- Pages: **Overview, Datasets, Sources, Jobs, Languages, Quality, Shards**.

Production build: `npm run build && npm run start`.

---

## End-to-end walkthrough: build a dataset

This ingests a few inline documents and runs the **entire** pipeline. The
easiest UI is **http://localhost:8000/docs**; the equivalent `curl` calls
(bash) are below. On Windows PowerShell, prefer the Swagger UI or use
`curl.exe`.

```bash
KEY="dev-key-change-me"
H=(-H "Content-Type: application/json" -H "X-API-Key: $KEY")

# 1) Create a versioned dataset -> capture its id
curl -s "${H[@]}" -X POST http://localhost:8000/api/datasets \
  -d '{"name":"demo","version":"v1"}'
# => {"id":"<DATASET_ID>", ...}

# 2) Register an inline source (no network needed) -> capture its id
curl -s "${H[@]}" -X POST http://localhost:8000/api/sources \
  -d '{
        "name":"demo-inline",
        "type":"web_dataset",
        "url":"http://inline.local",
        "config":{"documents":[
          {"id":"d1","text":"def add(a, b):\n    return a + b\n"},
          {"id":"d2","text":"The quick brown fox jumps over the lazy dog. "},
          {"id":"d3","text":"def add(a, b):\n    return a + b\n"}
        ]}
      }'
# => {"id":"<SOURCE_ID>", ...}   (d3 is a near-dup of d1 to exercise the deduper)

# 3) Start the FULL pipeline run (collect requires source_id)
curl -s "${H[@]}" -X POST http://localhost:8000/api/runs \
  -d '{"dataset_id":"<DATASET_ID>","source_id":"<SOURCE_ID>"}'
# => {"id":"<RUN_ID>","status":"pending", ...}

# 4) Watch progress
curl -s "${H[@]}" http://localhost:8000/api/runs/<RUN_ID>     # status: running -> succeeded
curl -s "${H[@]}" http://localhost:8000/api/jobs              # per-stage jobs
curl -s "${H[@]}" http://localhost:8000/api/stats/<DATASET_ID>
# => {"status_counts":{"sharded":2,...},"token_count":N,"document_count":M}

# 5) Inspect outputs
curl -s "${H[@]}" http://localhost:8000/api/datasets/<DATASET_ID>/shards
curl -s "${H[@]}" http://localhost:8000/api/datasets        # status becomes "ready", manifest_uri set
```

The Parquet shards and `manifest.json` are written to the `arc-datasets`
bucket — browse them in the MinIO console (http://localhost:9001).

**Run individual stages** instead of a full run (the pipeline is resumable, so
you can stop and continue):

```bash
curl "${H[@]}" -X POST http://localhost:8000/api/collect \
  -d '{"dataset_id":"<DATASET_ID>","source_id":"<SOURCE_ID>"}'
curl "${H[@]}" -X POST http://localhost:8000/api/clean    -d '{"dataset_id":"<DATASET_ID>"}'
curl "${H[@]}" -X POST http://localhost:8000/api/dedupe   -d '{"dataset_id":"<DATASET_ID>"}'
# ... classify / score / tokenize / shard the same way
```

---

## API reference

Full interactive docs at `/docs` (OpenAPI). Summary:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/sources` | register a source |
| GET | `/api/sources` | list sources |
| POST | `/api/datasets` | create a versioned dataset |
| GET | `/api/datasets` | list datasets |
| GET | `/api/datasets/{id}/shards` | list a dataset's Parquet shards |
| POST | `/api/collect` | enqueue collection (`dataset_id` + `source_id`) |
| POST | `/api/clean` · `/dedupe` · `/classify` · `/score` · `/tokenize` · `/shard` | enqueue one stage |
| POST | `/api/runs` | start a full/partial run (`source_id` required if it includes collect) |
| GET | `/api/runs/{id}` | run status |
| GET | `/api/jobs` · `/api/jobs/{id}` | job status |
| GET | `/api/stats/{dataset_id}` | document/status/token counts |
| GET | `/api/quality/{dataset_id}` | quality + language breakdown |
| GET | `/api/languages` | supported languages |
| GET | `/metrics` | Prometheus metrics |
| GET | `/health/live` · `/health/ready` | probes |

Source `type` values: `github`, `gitlab`, `sourcehut`, `web_docs`, `rfc`,
`wikipedia`, `web_dataset`. (`gitlab` has no connector yet; collecting from it fails.)

Pass `"params": {"tokenizer": "<huggingface-name>"}` on runs that tokenize. Without it the
stage uses a placeholder hashing tokenizer that is only meant for tests and dry runs.

---

## Running tests

```bash
cd backend
pip install -e ".[dev]"

pytest                          # full suite (unit + integration markers)
pytest tests/unit -q            # fast, pure-domain logic only

# integration test drives every stage against the live stack:
docker compose -f infra/docker-compose.yml up -d postgres redis-broker redis-cache minio
ARC_RUN_INTEGRATION=1 pytest tests/integration -q
```

Lint / format / types: `make lint` · `make fmt` · `make typecheck`.
Coverage gate is 80% (`--cov-fail-under=80` in `pyproject.toml`).

---

## Observability

- **Metrics:** every service emits Prometheus metrics (documents processed,
  stage duration, queue depth, bytes stored). Scraped from the API's
  `/metrics`; config in `infra/prometheus/prometheus.yml`.
- **Prometheus:** http://localhost:9090 — query e.g.
  `arc_documents_processed_total`.
- **Grafana:** http://localhost:3001 (`admin`/`admin`) — add Prometheus
  (`http://prometheus:9090`) as a data source and build dashboards from the
  `arc_*` metrics.
- **Logs:** structured (JSON in prod) via structlog — ready for Loki/ELK.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 Unauthorized` on `/api/*` | send `X-API-Key`; or unset `ARC_API_KEYS` in dev |
| API can't reach DB on start | ensure `migrate` ran; `docker compose ... run --rm migrate` |
| Jobs stay `queued` | a worker isn't running / not consuming that queue; check `make logs` |
| `bucket does not exist` | the API auto-creates buckets on startup; ensure MinIO is healthy |
| Dedup/tokenize errors about Ray | first call inits Ray locally; ensure enough CPU/RAM, or set `ARC_RAY_NUM_CPUS` |
| Port already in use | edit the host ports in `infra/docker-compose.yml` |
| Frontend 404s on `/api` | set `ARC_API_URL` (rewrite target) and restart `npm run dev` |

---

## Production notes

- **Kubernetes + KubeRay** for the Ray cluster (set `ARC_RAY_ADDRESS`), HPA on
  Celery queue depth (`arc_queue_depth`), managed PostgreSQL/Redis/object
  storage, and a secrets manager for source credentials (`credential_ref`).
- Put `/metrics`, Grafana, Prometheus, and the MinIO console behind auth/ingress
  — never expose them publicly.
- Replace the dev API keys with real OIDC/RBAC before any external exposure.
- `infra/k8s` (Helm/KubeRay manifests) is the next infra deliverable.
