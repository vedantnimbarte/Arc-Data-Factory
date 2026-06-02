"""PipelineStage protocol + registry.

The orchestrator does not import concrete services; it looks them up by Stage
in the registry. This keeps the orchestrator decoupled from every service
(open/closed: add a stage by registering it, no orchestrator edits).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.storage import ObjectStore
from arc.db.enums import Stage


@runtime_checkable
class PipelineStage(Protocol):
    """Every stage service implements this. A batch-at-a-time, resumable unit."""

    stage: Stage

    async def run(
        self, session: AsyncSession, store: ObjectStore, inp: StageInput
    ) -> StageResult: ...


_REGISTRY: dict[Stage, PipelineStage] = {}


def register(service: PipelineStage) -> PipelineStage:
    """Register a stage implementation. Idempotent per stage."""
    _REGISTRY[service.stage] = service
    return service


def get_stage(stage: Stage) -> PipelineStage:
    try:
        return _REGISTRY[stage]
    except KeyError as exc:
        raise LookupError(f"No service registered for stage {stage.value!r}") from exc


def registered_stages() -> set[Stage]:
    return set(_REGISTRY)
