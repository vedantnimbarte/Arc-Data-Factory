"""Unit tests for stage ordering and registry wiring (no DB)."""

from __future__ import annotations

from arc.db.enums import Stage
from arc.services import bootstrap  # noqa: F401  registers all stages
from arc.services.base import get_stage, registered_stages


def test_canonical_stage_order():
    order = [s.value for s in Stage.order()]
    assert order == [
        "collect", "clean", "dedupe", "compliance", "classify",
        "score", "tokenize", "shard", "register",
    ]


def test_all_stages_have_a_registered_service():
    assert registered_stages() == set(Stage.order())


def test_each_service_reports_its_stage():
    for stage in Stage.order():
        assert get_stage(stage).stage is stage
