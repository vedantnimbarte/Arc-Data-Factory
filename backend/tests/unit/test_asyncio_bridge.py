"""run_sync must reuse one loop: pooled DB connections are bound to it."""

from __future__ import annotations

import asyncio

from arc.core.asyncio_bridge import run_sync


async def _current_loop() -> asyncio.AbstractEventLoop:
    return asyncio.get_running_loop()


def test_run_sync_reuses_one_event_loop():
    assert run_sync(_current_loop()) is run_sync(_current_loop())
