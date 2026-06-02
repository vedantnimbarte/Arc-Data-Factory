"""Unit tests for MinHash near-duplicate signatures."""

from __future__ import annotations

import pytest

pytest.importorskip("datasketch")

from arc.services.deduper import domain  # noqa: E402


def test_shingles_basic():
    sh = domain.shingles("the quick brown fox jumps", k=2)
    assert "the quick" in sh and "brown fox" in sh


def test_near_duplicates_have_high_similarity():
    a = domain.minhash("the quick brown fox jumps over the lazy dog " * 5)
    b = domain.minhash("the quick brown fox jumps over the lazy dog today " * 5)
    assert a.jaccard(b) > 0.7


def test_distinct_texts_have_low_similarity():
    a = domain.minhash("completely unrelated content about gardening and flowers")
    b = domain.minhash("quantum chromodynamics and particle physics lectures")
    assert a.jaccard(b) < 0.3
