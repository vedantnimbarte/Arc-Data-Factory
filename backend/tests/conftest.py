"""Shared test fixtures and markers."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: requires the live dev stack (Postgres/Redis/MinIO)"
    )
