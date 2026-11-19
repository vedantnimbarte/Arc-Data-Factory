"""Deduper stage: CLEANED -> UNIQUE | DUPLICATE.

Signatures for the batch are computed in parallel with Ray; the LSH index is
Redis-backed so it persists across the orchestrator's self-chained batches
and across workers (single in-memory index would not survive at scale).

The "keep highest quality source / drop forks & mirrors" rule (08-spec) is
realized by keeping the first-seen canonical and pointing duplicates at it.
"""

from __future__ import annotations

from urllib.parse import urlparse

from datasketch import MinHashLSH
from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.compute import ensure_ray
from arc.core.config import settings
from arc.core.logging import get_logger
from arc.core.metrics import DOCS_PROCESSED
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.repositories import DocumentRepository
from arc.services.base import PipelineStage, register
from arc.services.deduper import domain

log = get_logger("service.deduper")


def _lsh(dataset_id: str) -> MinHashLSH:
    redis = urlparse(str(settings.redis_cache_url))
    return MinHashLSH(
        threshold=settings.lsh_threshold,
        num_perm=settings.minhash_num_perm,
        storage_config={
            "type": "redis",
            "basename": f"arc-lsh-{dataset_id}".encode(),
            "redis": {
                "host": redis.hostname or "localhost",
                "port": redis.port or 6379,
                "db": int(redis.path.lstrip("/") or 0),
                "password": redis.password,
            },
        },
    )


class DeduperService(PipelineStage):
    stage = Stage.DEDUPE

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        import uuid

        ensure_ray()
        repo = DocumentRepository(session)
        after_id = uuid.UUID(inp.cursor["after_id"]) if inp.cursor.get("after_id") else None
        batch = await repo.iter_by_status(
            inp.dataset_id, DocStatus.CLEANED, after_id=after_id, limit=inp.batch_size
        )
        if not batch:
            return StageResult(stage=Stage.DEDUPE, done=True)

        # Fetch texts, then compute MinHash signatures in parallel (Ray).
        texts: list[str] = []
        for doc in batch:
            raw = await store.get_bytes(ObjectRef.from_uri(doc.storage_uri))
            texts.append(raw.decode("utf-8", errors="replace"))
        signatures = _parallel_minhash(texts)

        lsh = _lsh(str(inp.dataset_id))
        unique = duplicate = 0
        last_id = None
        for doc, sig in zip(batch, signatures, strict=True):
            last_id = doc.id
            key = str(doc.id)
            canonical = domain.find_canonical(lsh, key, sig)
            if canonical:
                doc.status = DocStatus.DUPLICATE
                doc.duplicate_of = uuid.UUID(canonical)
                duplicate += 1
                DOCS_PROCESSED.labels(stage="dedupe", result="dropped").inc()
            else:
                if key not in lsh:
                    lsh.insert(key, sig)
                doc.status = DocStatus.UNIQUE
                unique += 1
                DOCS_PROCESSED.labels(stage="dedupe", result="ok").inc()

        done = len(batch) < inp.batch_size
        return StageResult(
            stage=Stage.DEDUPE,
            processed=len(batch),
            advanced=unique,
            dropped=duplicate,
            cursor={} if done else {"after_id": str(last_id)},
            done=done,
            metrics={"unique": unique, "duplicate": duplicate},
        )


def _parallel_minhash(texts: list[str]) -> list:
    """Compute MinHash signatures across the batch using Ray workers."""
    import ray

    @ray.remote
    def _sig(text: str):
        return domain.minhash(text)

    return ray.get([_sig.remote(t) for t in texts])


register(DeduperService())
