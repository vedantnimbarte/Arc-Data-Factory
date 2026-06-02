"""Reusable resumable batch driver for per-document stages.

Stages that transform one document at a time (clean, compliance, classify,
score, tokenize) compose this helper and supply only a `processor`. Cross-
document stages (dedupe, shard, register) implement `run` directly.

Resumability: keyset pagination on document id. The cursor carries the last
processed id; redelivery resumes exactly where it left off.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from arc.contracts import StageInput, StageResult
from arc.core.metrics import DOCS_PROCESSED
from arc.core.storage import ObjectStore
from arc.db.enums import DocStatus, Stage
from arc.db.models import Document
from arc.db.repositories import DocumentRepository


@dataclass(slots=True)
class DocOutcome:
    """What a processor decides for a single document."""

    new_status: DocStatus
    dropped: bool = False  # True => rejected/duplicate, counts as dropped not advanced


Processor = Callable[[Document, ObjectStore], Awaitable[DocOutcome]]


async def run_doc_batch(
    session: AsyncSession,
    store: ObjectStore,
    inp: StageInput,
    *,
    stage: Stage,
    input_status: DocStatus,
    processor: Processor,
) -> StageResult:
    docs_repo = DocumentRepository(session)
    after_id = uuid.UUID(inp.cursor["after_id"]) if inp.cursor.get("after_id") else None
    batch = await docs_repo.iter_by_status(
        inp.dataset_id, input_status, after_id=after_id, limit=inp.batch_size
    )

    if not batch:
        return StageResult(stage=stage, done=True)

    advanced = dropped = errors = 0
    last_id: uuid.UUID | None = None
    for doc in batch:
        last_id = doc.id
        try:
            outcome = await processor(doc, store)
        except Exception:  # noqa: BLE001  one bad doc must not fail the batch
            errors += 1
            DOCS_PROCESSED.labels(stage=stage.value, result="error").inc()
            continue
        doc.status = outcome.new_status
        if outcome.dropped:
            dropped += 1
            DOCS_PROCESSED.labels(stage=stage.value, result="dropped").inc()
        else:
            advanced += 1
            DOCS_PROCESSED.labels(stage=stage.value, result="ok").inc()

    # A short page means the source is drained -> stage done.
    done = len(batch) < inp.batch_size
    return StageResult(
        stage=stage,
        processed=len(batch),
        advanced=advanced,
        dropped=dropped,
        errors=errors,
        cursor={} if done else {"after_id": str(last_id)},
        done=done,
    )
