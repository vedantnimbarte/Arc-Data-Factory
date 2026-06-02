"""Run async coroutines from synchronous Celery tasks.

Services are async (async DB/S3). Celery tasks are sync. This bridge runs a
coroutine on a fresh event loop per call — correct and simple for the
worker's one-task-at-a-time model (prefetch_multiplier=1).
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)
