"""Import every service module so each registers itself in the stage registry.

The orchestrator imports this once; thereafter `get_stage(...)` resolves any
stage without the orchestrator depending on concrete service classes.
"""

from __future__ import annotations

from arc.services.classifier import service as _classifier  # noqa: F401
from arc.services.cleaner import service as _cleaner  # noqa: F401
from arc.services.collector import service as _collector  # noqa: F401
from arc.services.compliance import service as _compliance  # noqa: F401
from arc.services.deduper import service as _deduper  # noqa: F401
from arc.services.registry import service as _registry  # noqa: F401
from arc.services.scorer import service as _scorer  # noqa: F401
from arc.services.sharder import service as _sharder  # noqa: F401
from arc.services.tokenizer import service as _tokenizer  # noqa: F401
