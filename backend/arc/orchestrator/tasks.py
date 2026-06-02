"""Celery tasks that drive the orchestrator. One batch per task.

Self-chaining: a stage batch re-enqueues itself until done, then enqueues
the next stage. acks_late + bounded retries + a dead-letter on exhaustion
give at-least-once execution with idempotent stages = effectively once.
"""

from __future__ import annotations

import uuid

from celery import shared_task

from arc.core.asyncio_bridge import run_sync
from arc.core.db import session_scope
from arc.core.logging import get_logger
from arc.core.storage import object_store
from arc.db.enums import Stage
from arc.orchestrator.service import OrchestratorService
from arc.services import bootstrap  # noqa: F401  registers all stages

log = get_logger("orchestrator.tasks")


@shared_task(
    name="arc.orchestrator.tasks.run_stage_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def run_stage_batch(self, run_id: str, stage: str, cursor: dict | None = None) -> dict:
    """Execute one batch; re-enqueue self or advance to the next stage."""
    rid = uuid.UUID(run_id)
    st = Stage(stage)
    cur = cursor or {}

    async def _go() -> dict:
        async with session_scope() as session:
            orch = OrchestratorService(session, object_store())
            outcome = await orch.execute_batch(rid, st, cur)
            return {
                "processed": outcome.result.processed,
                "advanced": outcome.result.advanced,
                "dropped": outcome.result.dropped,
                "done": outcome.result.done,
                "next_stage": outcome.next_stage.value if outcome.next_stage else None,
                "run_done": outcome.run_done,
                "cursor": outcome.result.cursor,
            }

    try:
        out = run_sync(_go())
    except Exception as exc:  # noqa: BLE001
        log.error("stage_batch_failed", run_id=run_id, stage=stage, error=str(exc))
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            run_sync(_dead_letter(rid, st, str(exc)))
            raise

    log.info("stage_batch_done", run_id=run_id, stage=stage, **{
        k: out[k] for k in ("processed", "advanced", "dropped", "done")
    })

    if out["run_done"]:
        return out
    if out["next_stage"] is None:
        # same stage, more work
        run_stage_batch.delay(run_id, stage, out["cursor"])
    else:
        run_stage_batch.delay(run_id, out["next_stage"], {})
    return out


async def _dead_letter(run_id: uuid.UUID, stage: Stage, error: str) -> None:
    async with session_scope() as session:
        orch = OrchestratorService(session, object_store())
        await orch.mark_failed(run_id, f"[{stage.value}] {error}")
    log.error("run_dead_lettered", run_id=str(run_id), stage=stage.value)


@shared_task(name="arc.orchestrator.tasks.start_run")
def start_run(run_id: str, first_stage: str) -> None:
    """Kick off a run at its first stage."""
    run_stage_batch.delay(run_id, first_stage, {})
