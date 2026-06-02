"""Cleaner stage: RAW -> CLEANED. Stores cleaned text, sets language.

Empty-after-clean documents are dropped (status REJECTED).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.hashing import text_hash
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.models import Document
from arc.services.base import PipelineStage, register
from arc.services.batch import DocOutcome, run_doc_batch
from arc.services.cleaner import domain


class CleanerService(PipelineStage):
    stage = Stage.CLEAN

    async def _process(self, doc: Document, store: ObjectStore) -> DocOutcome:
        src = ObjectRef.from_uri(doc.storage_uri)
        raw = await store.get_bytes(src)
        cleaned = domain.clean(raw, doc.mime_type)

        if domain.is_empty_after_clean(cleaned):
            return DocOutcome(new_status=DocStatus.REJECTED, dropped=True)

        cleaned_bytes = cleaned.encode("utf-8")
        dst = ObjectRef(bucket=src.bucket, key=f"cleaned/{doc.dataset_id}/{text_hash(cleaned)}")
        await store.put_bytes(dst, cleaned_bytes, "text/plain")

        doc.storage_uri = dst.uri
        doc.size_bytes = len(cleaned_bytes)
        doc.language = domain.detect_language(cleaned)
        return DocOutcome(new_status=DocStatus.CLEANED)

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        return await run_doc_batch(
            session, store, inp,
            stage=Stage.CLEAN, input_status=DocStatus.RAW, processor=self._process,
        )


register(CleanerService())
