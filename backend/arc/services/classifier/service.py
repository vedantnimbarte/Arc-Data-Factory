"""Classifier stage: COMPLIANT -> CLASSIFIED (sets label)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.models import Document
from arc.services.base import PipelineStage, register
from arc.services.batch import DocOutcome, run_doc_batch
from arc.services.classifier import domain


class ClassifierService(PipelineStage):
    stage = Stage.CLASSIFY

    async def _process(self, doc: Document, store: ObjectStore) -> DocOutcome:
        text = (await store.get_bytes(ObjectRef.from_uri(doc.storage_uri))).decode(
            "utf-8", errors="replace"
        )
        doc.label = domain.classify(text, doc.doc_metadata)
        return DocOutcome(new_status=DocStatus.CLASSIFIED)

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        return await run_doc_batch(
            session, store, inp,
            stage=Stage.CLASSIFY, input_status=DocStatus.COMPLIANT, processor=self._process,
        )


register(ClassifierService())
