"""Baseline schema — all tables, enums, indexes, constraints.

Creates the full redesigned schema from arc.db.models. The documents table
is the partition target at scale; the prod migration that follows converts
it to RANGE/LIST partitioning by dataset_id (declared separately so dev
stays simple).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-02
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from arc.core.db import Base
from arc.db import models  # noqa: F401  registers tables on Base.metadata

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
