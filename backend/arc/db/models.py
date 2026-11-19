"""SQLAlchemy 2.0 ORM models — the redesigned, production-grade schema.

Fixes every gap from the architecture review:
- timestamps everywhere (audit, incremental sync, reproducibility)
- documents carry content_hash + storage URI + per-stage status (dedup,
  resumability, lineage); payloads live in object storage, not the DB
- jobs/pipeline_runs carry checkpoints, idempotency keys, retries, errors
- datasets have lineage (parent) + (name, version) uniqueness
- shards have checksum, row/token counts, order index, schema version
- token_stats roll up from per-shard counts and pin the tokenizer version
- documents partition-ready by dataset_id for 10B-scale sharding
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from arc.core.db import Base
from arc.db.enums import (
    DatasetStatus,
    DocLabel,
    DocStatus,
    JobStatus,
    RunStatus,
    SourceType,
    Stage,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Credential is a *reference* into secrets management, never the secret itself.
    credential_ref: Mapped[str | None] = mapped_column(String(255), default=None)
    rate_limit_per_min: Mapped[int | None] = mapped_column(Integer, default=None)
    # Incremental sync cursor (commit SHA, ETag, last timestamp, etc.).
    sync_cursor: Mapped[str | None] = mapped_column(Text, default=None)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (UniqueConstraint("type", "name", name="uq_source_type_name"),)


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status"), default=DatasetStatus.DRAFT, nullable=False
    )
    # Lineage: a dataset derived from another (e.g. re-filtered) links to its parent.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), default=None
    )
    description: Mapped[str | None] = mapped_column(Text, default=None)
    manifest_uri: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[str | None] = mapped_column(String(255), default=None)

    parent: Mapped["Dataset | None"] = relationship(remote_side=[id])
    shards: Mapped[list["Shard"]] = relationship(back_populates="dataset")

    __table_args__ = (UniqueConstraint("name", "version", name="uq_dataset_name_version"),)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    # Identity for exact-dedup and idempotent reprocessing.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Payload lives in object storage; DB holds only the pointer + metadata.
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), default=None)

    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus, name="doc_status"), default=DocStatus.RAW, nullable=False
    )
    language: Mapped[str | None] = mapped_column(String(16), default=None)  # ISO 639-1
    label: Mapped[DocLabel | None] = mapped_column(Enum(DocLabel, name="doc_label"), default=None)
    quality: Mapped[float | None] = mapped_column(Float, default=None)  # written ONLY by Scorer
    token_count: Mapped[int | None] = mapped_column(Integer, default=None)

    # Dedup grouping: duplicates point at the surviving canonical document.
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), default=None
    )
    compliance: Mapped[dict] = mapped_column(JSONB, default=dict)  # pii/license/safety verdicts
    doc_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        # Exact-dedup index, scoped per dataset. Unique: the collector's ON CONFLICT needs it.
        Index("ix_doc_dataset_hash", "dataset_id", "content_hash", unique=True),
        Index("ix_doc_dataset_status", "dataset_id", "status"),
        Index("ix_doc_source", "source_id"),
        # documents is partition-ready by dataset_id (declared in migration).
    )


class Shard(TimestampMixin, Base):
    __tablename__ = "shards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    shard_index: Mapped[int] = mapped_column(Integer, nullable=False)  # deterministic ordering
    path: Mapped[str] = mapped_column(Text, nullable=False)  # s3 URI of the Parquet file
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 of the file
    compression: Mapped[str] = mapped_column(String(32), default="zstd")
    schema_version: Mapped[int] = mapped_column(Integer, default=1)

    dataset: Mapped["Dataset"] = relationship(back_populates="shards")

    __table_args__ = (
        UniqueConstraint("dataset_id", "shard_index", name="uq_shard_dataset_index"),
    )


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"), default=None
    )
    stage: Mapped[Stage] = mapped_column(Enum(Stage, name="stage"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.QUEUED, nullable=False
    )
    # Idempotency: a (stage, idempotency_key) is processed at most once.
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), default=None)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    __table_args__ = (
        UniqueConstraint("stage", "idempotency_key", name="uq_job_idempotency"),
        Index("ix_job_status", "status"),
    )


class PipelineRun(TimestampMixin, Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.PENDING, nullable=False
    )
    current_stage: Mapped[Stage | None] = mapped_column(Enum(Stage, name="stage"), default=None)
    requested_stages: Mapped[list] = mapped_column(JSON, default=list)
    # Run-level params (e.g. source_id for collect, quality_threshold) flow to
    # every stage's StageInput, so a full run can drive collection too.
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    checkpoints: Mapped[list["StageCheckpoint"]] = relationship(back_populates="run")


class StageCheckpoint(TimestampMixin, Base):
    """Per-stage resumption state — the heart of "every stage is resumable"."""

    __tablename__ = "stage_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[Stage] = mapped_column(Enum(Stage, name="stage"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.PENDING, nullable=False
    )
    # Cursor: opaque per-stage resume token (last processed doc id, offset, page).
    cursor: Mapped[dict] = mapped_column(JSONB, default=dict)
    processed_count: Mapped[int] = mapped_column(BigInteger, default=0)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)

    run: Mapped["PipelineRun"] = relationship(back_populates="checkpoints")

    __table_args__ = (UniqueConstraint("run_id", "stage", name="uq_checkpoint_run_stage"),)


class TokenStat(TimestampMixin, Base):
    """Per-dataset token rollup, pinned to the tokenizer used (reproducibility)."""

    __tablename__ = "token_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    tokenizer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tokenizer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    vocab_size: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(BigInteger, default=0)
    document_count: Mapped[int] = mapped_column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "tokenizer_name", "tokenizer_version", name="uq_tokenstat"
        ),
    )


class Language(TimestampMixin, Base):
    """Backs the Languages dashboard page (was missing entirely)."""

    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)  # ISO 639-1
    name: Mapped[str] = mapped_column(String(64), nullable=False)
