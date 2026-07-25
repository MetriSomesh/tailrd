"""In-process job worker.

Runs as an asyncio task inside the API process. This is a deliberate memory
optimisation for the 1 GB target host: a separate worker process would cost
~120 MB of duplicated interpreter and imports.

Because agent concurrency is 1 anyway (serialised by a Redis lock), sharing the
event loop costs no throughput.

Fully implemented in Phase 5; this scaffold proves the lifecycle and shutdown
semantics work.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


async def worker_loop() -> None:
    """Poll the job queue until cancelled.

    Every iteration is individually guarded: a failure processing one job must
    never kill the loop, or the whole queue stalls silently.
    """
    log.info("worker_loop_entered", queue=settings.JOB_QUEUE_KEY)
    consecutive_errors = 0

    try:
        while True:
            try:
                processed = await _tick()
                consecutive_errors = 0
                # Only sleep when idle, so a busy queue drains promptly.
                if not processed:
                    await asyncio.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - loop must survive anything
                consecutive_errors += 1
                # Exponential backoff, capped, so a persistent fault (e.g. Redis
                # down) does not spin the CPU on a 1 vCPU host.
                backoff = min(2**consecutive_errors, 60)
                log.exception(
                    "worker_tick_failed",
                    consecutive_errors=consecutive_errors,
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)
    except asyncio.CancelledError:
        log.info("worker_loop_cancelled")
        raise


async def _tick() -> bool:
    """Process at most one job. Returns True if work was done.

    Phase 5 replaces this body with real dequeue + pipeline execution.
    """
    return False
