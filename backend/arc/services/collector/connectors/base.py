"""Connector protocol + the RawDocument value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from arc.db.models import Source


@dataclass(frozen=True, slots=True)
class RawDocument:
    external_id: str          # stable id at the source (used for incremental sync)
    content: bytes
    mime_type: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FetchPage:
    documents: list[RawDocument]
    next_cursor: dict | None  # None => source exhausted for this run


@runtime_checkable
class Connector(Protocol):
    async def fetch(self, source: Source, cursor: dict, limit: int) -> FetchPage:
        """Return one page of raw documents and the cursor for the next page."""
        ...
