"""Sharder stage: TOKENIZED -> SHARDED. One batch == one Parquet shard.

shard_index continues from existing shards (deterministic ordering), each
shard records a sha256 checksum + row/token counts for reproducibility.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.config import settings
from arc.core.hashing import content_hash
from arc.core.metrics import DOCS_PROCESSED
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.models import Shard
from arc.db.repositories import DocumentRepository, ShardRepository
from arc.services.base import PipelineStage, register
from arc.services.sharder import domain


class SharderService(PipelineStage):
    stage = Stage.SHARD

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        repo = DocumentRepository(session)
        shards = ShardRepository(session)
        batch = await repo.iter_by_status(
            inp.dataset_id, DocStatus.TOKENIZED, after_id=None, limit=inp.batch_size
        )
        if not batch:
            return StageResult(stage=Stage.SHARD, done=True)

        rows: list[dict] = []
        for doc in batch:
            tokens_uri = doc.doc_metadata.get("tokens_uri")
            ids = json.loads(await store.get_bytes(ObjectRef.from_uri(tokens_uri)))
            rows.append(
                {
                    "doc_id": str(doc.id),
                    "label": doc.label.value if doc.label else None,
                    "language": doc.language,
                    "quality": doc.quality,
                    "token_count": doc.token_count or 0,
                    "tokens": ids,
                }
            )

        parquet = domain.build_parquet(rows, compression="zstd")
        existing = await shards.list(inp.dataset_id)
        shard_index = len(existing)
        ref = ObjectRef(
            bucket=settings.s3_bucket_datasets,
            key=f"shards/{inp.dataset_id}/shard-{shard_index:06d}.parquet",
        )
        await store.put_bytes(ref, parquet, "application/vnd.apache.parquet")

        await shards.add(
            Shard(
                dataset_id=inp.dataset_id,
                shard_index=shard_index,
                path=ref.uri,
                size_bytes=len(parquet),
                row_count=len(rows),
                token_count=sum(r["token_count"] for r in rows),
                checksum=content_hash(parquet),
                compression="zstd",
                schema_version=domain.SCHEMA_VERSION,
            )
        )

        for doc in batch:
            doc.status = DocStatus.SHARDED
            DOCS_PROCESSED.labels(stage="shard", result="ok").inc()

        done = len(batch) < inp.batch_size
        return StageResult(
            stage=Stage.SHARD,
            processed=len(batch),
            advanced=len(batch),
            cursor={},  # status-drain; processed docs leave the TOKENIZED set
            done=done,
            metrics={"shard_index": shard_index, "rows": len(rows)},
        )


register(SharderService())
