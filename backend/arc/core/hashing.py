"""Content hashing helpers — the backbone of dedup, idempotency, and lineage.

A document's content hash is its identity for exact-dedup and for
idempotent re-processing (a stage keyed by (run, content_hash) is safe to
retry). Kept here so every service computes it identically.
"""

from __future__ import annotations

import hashlib


def content_hash(data: bytes) -> str:
    """SHA-256 hex digest. Stable across processes and runs."""
    return hashlib.sha256(data).hexdigest()


def text_hash(text: str) -> str:
    return content_hash(text.encode("utf-8"))


def idempotency_key(*parts: str) -> str:
    """Deterministic key from component strings, e.g. run_id + content_hash."""
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
