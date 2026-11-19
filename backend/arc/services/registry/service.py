"""Registry stage: write the dataset manifest and mark it READY.

Terminal stage — runs once per run. The manifest is the reproducibility
contract: it pins shards (with checksums), tokenizer identity, token totals,
lineage parent, and the canonical shard ordering.
"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.config import settings
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DatasetStatus, Stage
from arc.db.repositories import (
    DatasetRepository,
    ShardRepository,
    TokenStatRepository,
)
from arc.services.base import PipelineStage, register


class RegistryService(PipelineStage):
    stage = Stage.REGISTER

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        datasets = DatasetRepository(session)
        dataset = await datasets.get(inp.dataset_id)
        if dataset is None:
            raise LookupError(f"dataset {inp.dataset_id} not found")

        shards = await ShardRepository(session).list(inp.dataset_id)
        token_stats = await TokenStatRepository(session).for_dataset(inp.dataset_id)

        manifest = {
            "dataset": {
                "id": str(dataset.id),
                "name": dataset.name,
                "version": dataset.version,
                "parent_id": str(dataset.parent_id) if dataset.parent_id else None,
            },
            "tokenizers": [
                {
                    "name": t.tokenizer_name,
                    "version": t.tokenizer_version,
                    "vocab_size": t.vocab_size,
                    "token_count": t.token_count,
                    "document_count": t.document_count,
                }
                for t in token_stats
            ],
            "totals": {
                "shards": len(shards),
                "rows": sum(s.row_count for s in shards),
                "tokens": sum(s.token_count for s in shards),
                "bytes": sum(s.size_bytes for s in shards),
            },
            "shards": [
                {
                    "index": s.shard_index,
                    "path": s.path,
                    "rows": s.row_count,
                    "tokens": s.token_count,
                    "checksum": s.checksum,
                    "schema_version": s.schema_version,
                }
                for s in shards
            ],
            "format": "parquet",
            "schema_version": max((s.schema_version for s in shards), default=1),
        }

        ref = ObjectRef(
            bucket=settings.s3_bucket_datasets,
            key=f"manifests/{dataset.id}/manifest.json",
        )
        await store.put_bytes(
            ref, json.dumps(manifest, indent=2, sort_keys=True).encode(), "application/json"
        )
        dataset.manifest_uri = ref.uri
        dataset.status = DatasetStatus.READY

        return StageResult(
            stage=Stage.REGISTER,
            processed=len(shards),
            done=True,
            metrics=manifest["totals"],
        )


register(RegistryService())
