"""Registers the tokenizer stage on worker import (orchestrator runs it generically)."""

from arc.services.tokenizer import service as _service  # noqa: F401
