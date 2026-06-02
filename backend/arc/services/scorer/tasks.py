"""Registers the scorer stage on worker import (orchestrator runs it generically)."""

from arc.services.scorer import service as _service  # noqa: F401
