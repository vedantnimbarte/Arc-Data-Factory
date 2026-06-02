"""Importing this module registers the collector stage on the worker.

The generic orchestrator task (`run_stage_batch`) executes every stage via
the registry, so no per-stage Celery task is needed here.
"""

from arc.services.collector import service as _service  # noqa: F401
