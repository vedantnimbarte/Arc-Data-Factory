"""Unit tests for heuristic quality scoring."""

from __future__ import annotations

from arc.services.scorer import domain


def test_empty_text_scores_zero():
    assert domain.quality_score("") == 0.0
    assert domain.quality_score("   ") == 0.0


def test_score_in_unit_range():
    score = domain.quality_score("def add(a, b):\n    return a + b\n" * 20)
    assert 0.0 <= score <= 1.0


def test_repetitive_text_scores_lower_than_varied():
    repetitive = domain.quality_score("same line\n" * 100)
    varied = domain.quality_score("\n".join(f"unique line number {i}" for i in range(100)))
    assert varied > repetitive
