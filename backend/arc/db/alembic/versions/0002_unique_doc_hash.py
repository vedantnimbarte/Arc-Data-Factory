"""Make (dataset_id, content_hash) unique on documents.

The collector inserts with ON CONFLICT (dataset_id, content_hash) DO NOTHING,
which Postgres rejects unless a matching unique index exists. The baseline
created a plain index, so every collect failed.

Revision ID: 0002_unique_doc_hash
Revises: 0001_baseline
Create Date: 2026-11-19
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_unique_doc_hash"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLS = ["dataset_id", "content_hash"]


def upgrade() -> None:
    op.drop_index("ix_doc_dataset_hash", table_name="documents")
    op.create_index("ix_doc_dataset_hash", "documents", _COLS, unique=True)


def downgrade() -> None:
    op.drop_index("ix_doc_dataset_hash", table_name="documents")
    op.create_index("ix_doc_dataset_hash", "documents", _COLS)
