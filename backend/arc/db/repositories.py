"""Repository layer — the sole owner of database queries.

Services receive an AsyncSession and instantiate repositories; they never
write SQL inline. This isolates persistence (testable, swappable) from
business logic, per CLAUDE.md's service-boundary rule.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from arc.db.enums import DocStatus, JobStatus, Stage
from arc.db.models import (
    Dataset,
    Document,
    Job,
    Language,
    PipelineRun,
    Shard,
    Source,
    StageCheckpoint,
    TokenStat,
)


def _given(**values: object) -> dict:
    """Drop None values: on Core inserts an explicit None overrides the column
    default (e.g. id, max_attempts), unlike the ORM which applies it."""
    return {k: v for k, v in values.items() if v is not None}


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def add(self, source: Source) -> Source:
        self.s.add(source)
        await self.s.flush()
        return source

    async def get(self, source_id: uuid.UUID) -> Source | None:
        return await self.s.get(Source, source_id)

    async def list(self, *, enabled_only: bool = False) -> Sequence[Source]:
        stmt = select(Source).order_by(Source.created_at.desc())
        if enabled_only:
            stmt = stmt.where(Source.enabled.is_(True))
        return (await self.s.scalars(stmt)).all()


class DatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def add(self, dataset: Dataset) -> Dataset:
        self.s.add(dataset)
        await self.s.flush()
        return dataset

    async def get(self, dataset_id: uuid.UUID) -> Dataset | None:
        return await self.s.get(Dataset, dataset_id)

    async def list(self) -> Sequence[Dataset]:
        return (await self.s.scalars(select(Dataset).order_by(Dataset.created_at.desc()))).all()


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def upsert_raw(self, doc: Document) -> Document:
        """Insert, ignoring exact duplicates within the dataset (idempotent collect)."""
        doc.id = doc.id or uuid.uuid4()  # callers get the id back
        stmt = (
            pg_insert(Document)
            .values(**_given(
                id=doc.id,
                source_id=doc.source_id,
                dataset_id=doc.dataset_id,
                content_hash=doc.content_hash,
                storage_uri=doc.storage_uri,
                size_bytes=doc.size_bytes,
                mime_type=doc.mime_type,
                status=doc.status,
                doc_metadata=doc.doc_metadata,
            ))
            .on_conflict_do_nothing(index_elements=["dataset_id", "content_hash"])
            .returning(Document.id)
        )
        await self.s.execute(stmt)
        return doc

    async def get(self, doc_id: uuid.UUID) -> Document | None:
        return await self.s.get(Document, doc_id)

    async def iter_by_status(
        self, dataset_id: uuid.UUID, status: DocStatus, *, after_id: uuid.UUID | None, limit: int
    ) -> Sequence[Document]:
        """Cursor-paginated fetch for resumable stage processing (keyset on id)."""
        stmt = (
            select(Document)
            .where(Document.dataset_id == dataset_id, Document.status == status)
            .order_by(Document.id)
            .limit(limit)
        )
        if after_id is not None:
            stmt = stmt.where(Document.id > after_id)
        return (await self.s.scalars(stmt)).all()

    async def count_by_status(self, dataset_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Document.status, func.count())
            .where(Document.dataset_id == dataset_id)
            .group_by(Document.status)
        )
        return {row[0].value: row[1] for row in (await self.s.execute(stmt)).all()}

    async def language_breakdown(self, dataset_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Document.language, func.count())
            .where(Document.dataset_id == dataset_id, Document.language.is_not(None))
            .group_by(Document.language)
        )
        return {row[0]: row[1] for row in (await self.s.execute(stmt)).all()}


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def create_idempotent(self, job: Job) -> Job:
        """Create a job unless one with (stage, idempotency_key) already exists."""
        job.id = job.id or uuid.uuid4()  # callers get the id back
        stmt = (
            pg_insert(Job)
            .values(**_given(
                id=job.id,
                run_id=job.run_id,
                stage=job.stage,
                status=job.status,
                idempotency_key=job.idempotency_key,
                params=job.params,
                max_attempts=job.max_attempts,
            ))
            .on_conflict_do_nothing(index_elements=["stage", "idempotency_key"])
            .returning(Job.id)
        )
        result = (await self.s.execute(stmt)).scalar_one_or_none()
        if result is None:  # already existed -> fetch it
            existing = await self.s.scalar(
                select(Job).where(
                    Job.stage == job.stage, Job.idempotency_key == job.idempotency_key
                )
            )
            assert existing is not None
            return existing
        return job

    async def get(self, job_id: uuid.UUID) -> Job | None:
        return await self.s.get(Job, job_id)

    async def list(self, *, status: JobStatus | None = None, limit: int = 100) -> Sequence[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(Job.status == status)
        return (await self.s.scalars(stmt)).all()


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def add(self, run: PipelineRun) -> PipelineRun:
        self.s.add(run)
        await self.s.flush()
        return run

    async def get(self, run_id: uuid.UUID) -> PipelineRun | None:
        return await self.s.get(PipelineRun, run_id)

    async def checkpoint(self, run_id: uuid.UUID, stage: Stage) -> StageCheckpoint | None:
        return await self.s.scalar(
            select(StageCheckpoint).where(
                StageCheckpoint.run_id == run_id, StageCheckpoint.stage == stage
            )
        )

    async def upsert_checkpoint(self, cp: StageCheckpoint) -> StageCheckpoint:
        existing = await self.checkpoint(cp.run_id, cp.stage)
        if existing is None:
            self.s.add(cp)
            await self.s.flush()
            return cp
        existing.status = cp.status
        existing.cursor = cp.cursor
        existing.processed_count = cp.processed_count
        existing.metrics = cp.metrics
        await self.s.flush()
        return existing


class ShardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def add(self, shard: Shard) -> Shard:
        self.s.add(shard)
        await self.s.flush()
        return shard

    async def list(self, dataset_id: uuid.UUID) -> Sequence[Shard]:
        stmt = (
            select(Shard)
            .where(Shard.dataset_id == dataset_id)
            .order_by(Shard.shard_index)
        )
        return (await self.s.scalars(stmt)).all()


class TokenStatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def increment(
        self,
        dataset_id: uuid.UUID,
        *,
        tokenizer_name: str,
        tokenizer_version: str,
        vocab_size: int,
        token_count: int,
        document_count: int,
    ) -> None:
        """Atomically add to the dataset's token rollup (idempotent per call set)."""
        stmt = (
            pg_insert(TokenStat)
            .values(
                dataset_id=dataset_id,
                tokenizer_name=tokenizer_name,
                tokenizer_version=tokenizer_version,
                vocab_size=vocab_size,
                token_count=token_count,
                document_count=document_count,
            )
            .on_conflict_do_update(
                index_elements=["dataset_id", "tokenizer_name", "tokenizer_version"],
                set_={
                    "token_count": TokenStat.token_count + token_count,
                    "document_count": TokenStat.document_count + document_count,
                },
            )
        )
        await self.s.execute(stmt)

    async def for_dataset(self, dataset_id: uuid.UUID) -> Sequence[TokenStat]:
        return (
            await self.s.scalars(select(TokenStat).where(TokenStat.dataset_id == dataset_id))
        ).all()


class LanguageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def list(self) -> Sequence[Language]:
        return (await self.s.scalars(select(Language).order_by(Language.code))).all()
