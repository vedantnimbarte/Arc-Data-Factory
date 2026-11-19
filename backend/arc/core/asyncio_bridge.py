"""Run async coroutines from synchronous Celery tasks.

Services are async (async DB/S3). Celery tasks are sync. This bridge runs
every coroutine on ONE long-lived event loop per process: the async DB
engine's pooled connections are bound to the loop that opened them, so a
fresh loop per task (asyncio.run) breaks the second task with "Event loop
is closed". One task at a time per process (prefetch_multiplier=1).
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None


def run_sync(coro: Coroutine[object, object, T]) -> T:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)
