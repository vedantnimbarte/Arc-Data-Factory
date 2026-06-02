"""Collector stage: fetch a page from the source, store payloads, index docs.

Resumable via the connector cursor (carried in the stage cursor). Idempotent
via content-hash upsert (re-collecting the same blob is a no-op). Payloads go
to object storage; only metadata + the storage URI land in Postgres.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.hashing import content_hash
from arc.core.logging import get_logger
from arc.core.metrics import DOCS_PROCESSED
from arc.core.storage import ObjectRef, ObjectStore
from arc.core.config import settings
from arc.db.enums import DocStatus, Stage
from arc.db.models import Document, Source
from arc.db.repositories import DocumentRepository
from arc.services.base import PipelineStage, register
from arc.services.collector.connectors import get_connector

log = get_logger("service.collector")


class CollectorService(PipelineStage):
    stage = Stage.COLLECT

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        source_id = uuid.UUID(inp.params["source_id"])
        source = await session.get(Source, source_id)
        if source is None:
            raise LookupError(f"source {source_id} not found")

        connector = get_connector(source.type)
        page = await connector.fetch(source, inp.cursor, inp.batch_size)

        docs = DocumentRepository(session)
        stored = 0
        for raw in page.documents:
            digest = content_hash(raw.content)
            ref = ObjectRef(
                bucket=settings.s3_bucket_raw,
                key=f"{inp.dataset_id}/{source_id}/{digest}",
            )
            await store.put_bytes(ref, raw.content, raw.mime_type)
            await docs.upsert_raw(
                Document(
                    source_id=source_id,
                    dataset_id=inp.dataset_id,
                    content_hash=digest,
                    storage_uri=ref.uri,
                    size_bytes=len(raw.content),
                    mime_type=raw.mime_type,
                    status=DocStatus.RAW,
                    doc_metadata={"external_id": raw.external_id, **raw.metadata},
                )
            )
            stored += 1
            DOCS_PROCESSED.labels(stage="collect", result="ok").inc()

        # Persist incremental sync cursor on the source.
        if page.next_cursor is not None:
            source.sync_cursor = str(page.next_cursor)

        done = page.next_cursor is None
        return StageResult(
            stage=Stage.COLLECT,
            processed=stored,
            advanced=stored,
            cursor=page.next_cursor or {},
            done=done,
            metrics={"fetched": stored},
        )


register(CollectorService())
