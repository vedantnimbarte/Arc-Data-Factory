"""Registers the deduper stage on worker import (orchestrator runs it generically)."""

from arc.services.deduper import service as _service  # noqa: F401
