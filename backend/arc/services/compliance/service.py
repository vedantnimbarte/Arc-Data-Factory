"""Compliance stage: UNIQUE -> COMPLIANT | REJECTED."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.models import Document
from arc.services.base import PipelineStage, register
from arc.services.batch import DocOutcome, run_doc_batch
from arc.services.compliance import domain


class ComplianceService(PipelineStage):
    stage = Stage.COMPLIANCE

    async def _process(self, doc: Document, store: ObjectStore) -> DocOutcome:
        text = (await store.get_bytes(ObjectRef.from_uri(doc.storage_uri))).decode(
            "utf-8", errors="replace"
        )
        verdict = domain.evaluate(text, doc.doc_metadata)
        doc.compliance = verdict.as_dict()
        if not verdict.compliant:
            return DocOutcome(new_status=DocStatus.REJECTED, dropped=True)
        return DocOutcome(new_status=DocStatus.COMPLIANT)

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        return await run_doc_batch(
            session, store, inp,
            stage=Stage.COMPLIANCE, input_status=DocStatus.UNIQUE, processor=self._process,
        )


register(ComplianceService())
