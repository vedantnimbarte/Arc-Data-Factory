"""Pydantic request/response models for the API. Typed in, typed out."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from arc.db.enums import (
    DatasetStatus,
    DocLabel,
    JobStatus,
    RunStatus,
    SourceType,
    Stage,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Sources ---
class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: SourceType
    url: HttpUrl
    credential_ref: str | None = None
    rate_limit_per_min: int | None = Field(default=None, ge=1)
    config: dict = Field(default_factory=dict)


class SourceOut(ORMModel):
    id: uuid.UUID
    name: str
    type: SourceType
    url: str
    enabled: bool
    last_synced_at: datetime | None
    created_at: datetime


# --- Datasets ---
class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    parent_id: uuid.UUID | None = None
    description: str | None = None


class DatasetOut(ORMModel):
    id: uuid.UUID
    name: str
    version: str
    status: DatasetStatus
    parent_id: uuid.UUID | None
    manifest_uri: str | None
    created_at: datetime


# --- Pipeline / stages ---
class StageRequest(BaseModel):
    """Body for POST /api/{stage} — enqueue a stage (or full run) for a dataset."""

    dataset_id: uuid.UUID
    batch_size: int = Field(default=1000, ge=1, le=100_000)
    params: dict = Field(default_factory=dict)


class CollectRequest(StageRequest):
    source_id: uuid.UUID


class RunRequest(BaseModel):
    dataset_id: uuid.UUID
    stages: list[Stage] | None = None  # default: full pipeline
    # Required when the run includes the collect stage; ignored otherwise.
    source_id: uuid.UUID | None = None
    params: dict = Field(default_factory=dict)


class RunOut(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: RunStatus
    current_stage: Stage | None
    created_at: datetime


class JobOut(ORMModel):
    id: uuid.UUID
    run_id: uuid.UUID | None
    stage: Stage
    status: JobStatus
    attempts: int
    error: str | None
    created_at: datetime


# --- Stats / quality / languages / shards ---
class DatasetStats(BaseModel):
    dataset_id: uuid.UUID
    status_counts: dict[str, int]
    token_count: int
    document_count: int


class QualityBucket(BaseModel):
    label: DocLabel | None
    avg_quality: float
    count: int


class LanguageOut(ORMModel):
    code: str
    name: str


class ShardOut(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    shard_index: int
    path: str
    size_bytes: int
    row_count: int
    token_count: int
    checksum: str


class EnqueuedOut(BaseModel):
    job_id: uuid.UUID
    run_id: uuid.UUID | None = None
    stage: Stage
    status: JobStatus
