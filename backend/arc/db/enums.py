"""Enumerations shared across the schema and the pipeline.

Stage order here is canonical and drives the orchestrator DAG.
"""

from __future__ import annotations

import enum


class Stage(str, enum.Enum):
    """Pipeline stages in canonical execution order."""

    COLLECT = "collect"
    CLEAN = "clean"
    DEDUPE = "dedupe"
    COMPLIANCE = "compliance"
    CLASSIFY = "classify"
    SCORE = "score"
    TOKENIZE = "tokenize"
    SHARD = "shard"
    REGISTER = "register"

    @classmethod
    def order(cls) -> list["Stage"]:
        return [
            cls.COLLECT, cls.CLEAN, cls.DEDUPE, cls.COMPLIANCE, cls.CLASSIFY,
            cls.SCORE, cls.TOKENIZE, cls.SHARD, cls.REGISTER,
        ]


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"  # exhausted retries -> dead-letter


class DatasetStatus(str, enum.Enum):
    DRAFT = "draft"
    BUILDING = "building"
    READY = "ready"
    ARCHIVED = "archived"
    FAILED = "failed"


class DocStatus(str, enum.Enum):
    """Per-document position in the pipeline (enables resumability)."""

    RAW = "raw"
    CLEANED = "cleaned"
    UNIQUE = "unique"
    DUPLICATE = "duplicate"
    COMPLIANT = "compliant"
    REJECTED = "rejected"  # failed compliance/quality gate
    CLASSIFIED = "classified"
    SCORED = "scored"
    TOKENIZED = "tokenized"
    SHARDED = "sharded"


class SourceType(str, enum.Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    SOURCEHUT = "sourcehut"  # included per PRD (07-spec omitted it)
    WEB_DOCS = "web_docs"
    RFC = "rfc"              # included per PRD
    WIKIPEDIA = "wikipedia"
    WEB_DATASET = "web_dataset"


class DocLabel(str, enum.Enum):
    CODE = "code"
    DOCUMENTATION = "documentation"
    ENGINEERING = "engineering"
    REASONING = "reasoning"
    AGENT = "agent"
    MEMORY = "memory"
    GENERAL = "general"
