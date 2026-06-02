"""Pipeline control: per-stage POSTs and a full-run POST.

These endpoints ONLY enqueue work (control plane). They create an idempotent
Job, create/seed a PipelineRun, and hand off to the orchestrator via Celery.
No heavy compute happens in-process.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from arc.api.deps import PrincipalDep, SessionDep
from arc.api.schemas import CollectRequest, EnqueuedOut, RunOut, RunRequest, StageRequest
from arc.core.hashing import idempotency_key
from arc.core.storage import object_store
from arc.db.enums import JobStatus, Stage
from arc.db.models import Job
from arc.db.repositories import DatasetRepository, JobRepository
from arc.orchestrator.service import OrchestratorService
from arc.orchestrator.tasks import run_stage_batch

router = APIRouter(prefix="/api", tags=["pipeline"])


async def _enqueue_stage(
    session: SessionDep, dataset_id: uuid.UUID, stage: Stage, params: dict
) -> Job:
    if await DatasetRepository(session).get(dataset_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    orch = OrchestratorService(session, object_store())
    run = await orch.create_run(dataset_id, [stage], params=params)
    job = await JobRepository(session).create_idempotent(
        Job(
            run_id=run.id,
            stage=stage,
            status=JobStatus.QUEUED,
            idempotency_key=idempotency_key(str(run.id), stage.value),
            params=params,
        )
    )
    await session.commit()
    run_stage_batch.delay(str(run.id), stage.value, {})
    return job


def _stage_endpoint(stage: Stage):
    async def endpoint(body: StageRequest, session: SessionDep, _: PrincipalDep) -> EnqueuedOut:
        job = await _enqueue_stage(session, body.dataset_id, stage, body.params)
        return EnqueuedOut(job_id=job.id, run_id=job.run_id, stage=stage, status=job.status)

    endpoint.__name__ = f"enqueue_{stage.value}"
    return endpoint


# POST /api/clean, /api/dedupe, /api/classify, /api/score, /api/tokenize, /api/shard
for _stage in (Stage.CLEAN, Stage.DEDUPE, Stage.CLASSIFY, Stage.SCORE, Stage.TOKENIZE, Stage.SHARD):
    router.add_api_route(
        f"/{_stage.value}",
        _stage_endpoint(_stage),
        methods=["POST"],
        response_model=EnqueuedOut,
        summary=f"Enqueue the {_stage.value} stage for a dataset",
    )


@router.post("/collect", response_model=EnqueuedOut, summary="Enqueue collection from a source")
async def collect(body: CollectRequest, session: SessionDep, _: PrincipalDep) -> EnqueuedOut:
    params = {**body.params, "source_id": str(body.source_id)}
    job = await _enqueue_stage(session, body.dataset_id, Stage.COLLECT, params)
    return EnqueuedOut(job_id=job.id, run_id=job.run_id, stage=Stage.COLLECT, status=job.status)


@router.post("/runs", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED,
             summary="Start a full (or partial) pipeline run")
async def start_run(body: RunRequest, session: SessionDep, _: PrincipalDep):
    if await DatasetRepository(session).get(body.dataset_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dataset not found")
    run_params = dict(body.params)
    if body.source_id is not None:
        run_params["source_id"] = str(body.source_id)
    orch = OrchestratorService(session, object_store())
    run = await orch.create_run(body.dataset_id, body.stages, params=run_params)
    first = Stage(run.requested_stages[0])
    if first is Stage.COLLECT and "source_id" not in run_params:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "source_id is required when the run includes the collect stage",
        )
    await JobRepository(session).create_idempotent(
        Job(
            run_id=run.id,
            stage=first,
            status=JobStatus.QUEUED,
            idempotency_key=idempotency_key(str(run.id), first.value),
        )
    )
    await session.commit()
    run_stage_batch.delay(str(run.id), first.value, {})
    return run
