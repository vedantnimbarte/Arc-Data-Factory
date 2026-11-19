"""Unit tests for MinHash near-duplicate signatures."""

from __future__ import annotations

import pytest

pytest.importorskip("datasketch")

from datasketch import MinHashLSH  # noqa: E402

from arc.services.deduper import domain  # noqa: E402

_BASE = " ".join(f"word{i}" for i in range(60))


def test_shingles_basic():
    sh = domain.shingles("the quick brown fox jumps", k=2)
    assert "the quick" in sh and "brown fox" in sh


def test_near_duplicates_have_high_similarity():
    a = domain.minhash(_BASE)
    b = domain.minhash(_BASE.replace("word30", "changed"))  # one-word edit
    assert a.jaccard(b) > 0.7


def test_distinct_texts_have_low_similarity():
    a = domain.minhash("completely unrelated content about gardening and flowers")
    b = domain.minhash("quantum chromodynamics and particle physics lectures")
    assert a.jaccard(b) < 0.3


def test_find_canonical_ignores_self_match():
    # A retried batch re-queries docs it already indexed; they must not dedupe against themselves.
    lsh = MinHashLSH(threshold=0.8, num_perm=128)
    sig = domain.minhash(_BASE)
    lsh.insert("a", sig)
    assert domain.find_canonical(lsh, "a", sig) is None
    assert domain.find_canonical(lsh, "b", sig) == "a"
