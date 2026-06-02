"""Registers the cleaner stage on worker import (orchestrator runs it generically)."""

from arc.services.cleaner import service as _service  # noqa: F401
