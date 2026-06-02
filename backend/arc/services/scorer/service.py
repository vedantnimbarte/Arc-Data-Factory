"""Scorer stage: CLASSIFIED -> SCORED. Drops docs below the quality floor.

The reject threshold is a stage param (default 0.2), so a run can tune
strictness without code changes.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.models import Document
from arc.services.base import PipelineStage, register
from arc.services.batch import DocOutcome, run_doc_batch
from arc.services.scorer import domain


class ScorerService(PipelineStage):
    stage = Stage.SCORE

    def __init__(self) -> None:
        self._threshold = 0.2

    async def _process(self, doc: Document, store: ObjectStore) -> DocOutcome:
        text = (await store.get_bytes(ObjectRef.from_uri(doc.storage_uri))).decode(
            "utf-8", errors="replace"
        )
        score = domain.quality_score(text)
        doc.quality = score
        if score < self._threshold:
            return DocOutcome(new_status=DocStatus.REJECTED, dropped=True)
        return DocOutcome(new_status=DocStatus.SCORED)

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        self._threshold = float(inp.params.get("quality_threshold", 0.2))
        return await run_doc_batch(
            session, store, inp,
            stage=Stage.SCORE, input_status=DocStatus.CLASSIFIED, processor=self._process,
        )


register(ScorerService())
