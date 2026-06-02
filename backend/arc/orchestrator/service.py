"""Orchestration logic: run lifecycle + stage advancement (no Celery here).

Pure-ish coordinator: given a session + store, it can create a run, execute
one batch of a stage, persist the checkpoint, and decide what comes next.
The Celery layer (tasks.py) only schedules calls into this.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.logging import get_logger
from arc.core.storage import ObjectStore
from arc.db.enums import RunStatus, Stage
from arc.db.models import PipelineRun, StageCheckpoint
from arc.db.repositories import RunRepository
from arc.services.base import get_stage

log = get_logger("orchestrator")


@dataclass(frozen=True, slots=True)
class BatchOutcome:
    result: StageResult
    next_stage: Stage | None
    run_done: bool


class OrchestratorService:
    """Coordinates a PipelineRun across stages, batch by batch."""

    def __init__(self, session: AsyncSession, store: ObjectStore) -> None:
        self.s = session
        self.store = store
        self.runs = RunRepository(session)

    async def create_run(
        self,
        dataset_id: uuid.UUID,
        stages: list[Stage] | None,
        params: dict | None = None,
    ) -> PipelineRun:
        ordered = stages or Stage.order()
        # Always execute in canonical order regardless of request order.
        ordered = [s for s in Stage.order() if s in set(ordered)]
        run = PipelineRun(
            dataset_id=dataset_id,
            status=RunStatus.PENDING,
            requested_stages=[s.value for s in ordered],
            params=params or {},
        )
        return await self.runs.add(run)

    def _requested(self, run: PipelineRun) -> list[Stage]:
        return [Stage(v) for v in run.requested_stages]

    def _next_stage(self, run: PipelineRun, completed: Stage) -> Stage | None:
        seq = self._requested(run)
        idx = seq.index(completed)
        return seq[idx + 1] if idx + 1 < len(seq) else None

    async def execute_batch(self, run_id: uuid.UUID, stage: Stage, cursor: dict) -> BatchOutcome:
        """Run ONE batch of `stage`, persist the checkpoint, decide next step."""
        run = await self.runs.get(run_id)
        if run is None:
            raise LookupError(f"run {run_id} not found")

        if run.status in (RunStatus.PENDING,):
            run.status = RunStatus.RUNNING
        run.current_stage = stage

        service = get_stage(stage)
        inp = StageInput(
            run_id=run_id,
            dataset_id=run.dataset_id,
            stage=stage,
            cursor=cursor,
            params=run.params or {},
        )
        result = await service.run(self.s, self.store, inp)

        # Persist checkpoint (resumability): merge processed counts.
        existing = await self.runs.checkpoint(run_id, stage)
        processed_total = (existing.processed_count if existing else 0) + result.processed
        await self.runs.upsert_checkpoint(
            StageCheckpoint(
                run_id=run_id,
                stage=stage,
                status=RunStatus.SUCCEEDED if result.done else RunStatus.RUNNING,
                cursor=result.cursor,
                processed_count=processed_total,
                metrics=result.metrics,
            )
        )

        if not result.done:
            return BatchOutcome(result=result, next_stage=stage, run_done=False)

        nxt = self._next_stage(run, stage)
        if nxt is None:
            run.status = RunStatus.SUCCEEDED
            run.current_stage = None
            return BatchOutcome(result=result, next_stage=None, run_done=True)
        return BatchOutcome(result=result, next_stage=nxt, run_done=False)

    async def mark_failed(self, run_id: uuid.UUID, error: str) -> None:
        run = await self.runs.get(run_id)
        if run is not None:
            run.status = RunStatus.FAILED
            run.error = error[:4000]
