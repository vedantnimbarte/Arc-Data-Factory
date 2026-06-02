"""Registers the classifier stage on worker import (orchestrator runs it generically)."""

from arc.services.classifier import service as _service  # noqa: F401
