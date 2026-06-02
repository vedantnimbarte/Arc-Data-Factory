"""Tokenizer stage: SCORED -> TOKENIZED.

Encodes in parallel with Ray, stores token ids in object storage (the
Sharder reads them), records per-doc token_count, and upserts the dataset's
TokenStat with the pinned tokenizer identity.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.compute import ensure_ray
from arc.core.config import settings
from arc.core.metrics import DOCS_PROCESSED
from arc.core.storage import ObjectRef, ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.repositories import DocumentRepository, TokenStatRepository
from arc.services.base import PipelineStage, register
from arc.services.tokenizer import domain


class TokenizerService(PipelineStage):
    stage = Stage.TOKENIZE

    async def run(self, session: AsyncSession, store: ObjectStore, inp: StageInput) -> StageResult:
        ensure_ray()
        tokenizer = domain.get_tokenizer(inp.params.get("tokenizer"))
        tinfo = domain.info(tokenizer)

        repo = DocumentRepository(session)
        after_id = uuid.UUID(inp.cursor["after_id"]) if inp.cursor.get("after_id") else None
        batch = await repo.iter_by_status(
            inp.dataset_id, DocStatus.SCORED, after_id=after_id, limit=inp.batch_size
        )
        if not batch:
            return StageResult(stage=Stage.TOKENIZE, done=True)

        texts = [
            (await store.get_bytes(ObjectRef.from_uri(d.storage_uri))).decode(
                "utf-8", errors="replace"
            )
            for d in batch
        ]
        token_lists = _parallel_encode(texts, inp.params.get("tokenizer"))

        total_tokens = 0
        last_id = None
        for doc, ids in zip(batch, token_lists, strict=True):
            last_id = doc.id
            ref = ObjectRef(
                bucket=settings.s3_bucket_datasets, key=f"tokens/{inp.dataset_id}/{doc.id}"
            )
            await store.put_bytes(ref, json.dumps(ids).encode(), "application/json")
            doc.token_count = len(ids)
            doc.doc_metadata = {**doc.doc_metadata, "tokens_uri": ref.uri}
            doc.status = DocStatus.TOKENIZED
            total_tokens += len(ids)
            DOCS_PROCESSED.labels(stage="tokenize", result="ok").inc()

        await TokenStatRepository(session).increment(
            inp.dataset_id,
            tokenizer_name=tinfo.name,
            tokenizer_version=tinfo.version,
            vocab_size=tinfo.vocab_size,
            token_count=total_tokens,
            document_count=len(batch),
        )

        done = len(batch) < inp.batch_size
        return StageResult(
            stage=Stage.TOKENIZE,
            processed=len(batch),
            advanced=len(batch),
            cursor={} if done else {"after_id": str(last_id)},
            done=done,
            metrics={"tokens": total_tokens, "tokenizer": tinfo.name},
        )


def _parallel_encode(texts: list[str], name: str | None) -> list[list[int]]:
    import ray

    @ray.remote
    def _enc(chunk: list[str], n: str | None) -> list[list[int]]:
        tok = domain.get_tokenizer(n)
        return [tok.encode_ids(t) for t in chunk]

    # Chunk to amortize task overhead.
    size = max(1, len(texts) // 8)
    chunks = [texts[i : i + size] for i in range(0, len(texts), size)]
    results = ray.get([_enc.remote(c, name) for c in chunks])
    return [ids for group in results for ids in group]


register(TokenizerService())
