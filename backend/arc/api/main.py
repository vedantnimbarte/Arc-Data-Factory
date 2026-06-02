"""FastAPI application factory — the API gateway entrypoint.

Wires routers, Prometheus `/metrics`, health probes, structured logging, and
OpenAPI. Heavy work is never done here; routes enqueue to the orchestrator.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from arc.api.routers import datasets, jobs, pipeline, sources, stats
from arc.core.config import settings
from arc.core.logging import configure_logging, get_logger
from arc.core.storage import object_store

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await object_store().ensure_buckets()
    log.info("api_startup", environment=settings.environment)
    yield
    log.info("api_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ARC Data Factory API",
        version="0.1.0",
        description="Control plane for the ARC training-data pipeline.",
        lifespan=lifespan,
    )

    for module in (sources, datasets, pipeline, jobs, stats):
        app.include_router(module.router)

    @app.get("/health/live", tags=["health"], summary="Liveness probe")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"], summary="Readiness probe")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/metrics", tags=["observability"], summary="Prometheus metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
