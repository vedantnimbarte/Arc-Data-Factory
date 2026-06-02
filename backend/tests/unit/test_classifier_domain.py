"""Unit tests for rule-based classification."""

from __future__ import annotations

from arc.db.enums import DocLabel
from arc.services.classifier import domain


def test_code_by_extension():
    assert domain.classify("x = 1", {"path": "main.py"}) is DocLabel.CODE


def test_code_by_content_hint():
    assert domain.classify("def f():\n    return 1", {}) is DocLabel.CODE


def test_documentation_by_source_type():
    assert domain.classify("Some article text", {"source_type": "wikipedia"}) is DocLabel.DOCUMENTATION


def test_agent_label():
    assert domain.classify("Thought: I should call a tool\nAction: search", {}) is DocLabel.AGENT


def test_engineering_label():
    assert domain.classify("This RFC describes the architecture", {}) is DocLabel.ENGINEERING


def test_general_fallback():
    assert domain.classify("just some prose without hints", {}) is DocLabel.GENERAL
