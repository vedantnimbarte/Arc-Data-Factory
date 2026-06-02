"""The stage contract: what every pipeline service receives and returns.

A stage is a pure function over (dataset, cursor) → (advanced cursor, counts).
It reads documents in a status, processes a batch, advances the cursor, and
reports counts. The orchestrator persists the cursor as a checkpoint, which
is what makes every stage resumable.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from arc.db.enums import Stage


class StageInput(BaseModel):
    """Immutable input handed to a stage's `run` method."""

    model_config = ConfigDict(frozen=True)

    run_id: uuid.UUID
    dataset_id: uuid.UUID
    stage: Stage
    # Opaque resume token from the prior checkpoint (e.g. {"after_id": "..."}).
    cursor: dict = Field(default_factory=dict)
    batch_size: int = 1000
    params: dict = Field(default_factory=dict)


class StageResult(BaseModel):
    """What a stage returns after processing one batch."""

    stage: Stage
    processed: int = 0
    advanced: int = 0          # docs moved to the next status
    dropped: int = 0           # docs rejected at this stage (dup/non-compliant/low quality)
    errors: int = 0
    # New cursor; `done=True` means no more work for this stage in this run.
    cursor: dict = Field(default_factory=dict)
    done: bool = False
    metrics: dict = Field(default_factory=dict)
