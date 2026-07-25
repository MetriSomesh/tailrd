"""In-process job worker.

Runs as an asyncio task inside the API process. Polls Redis for job IDs,
then executes the tailoring pipeline for each one.

Memory optimization: shares the process with the API (saves ~120 MB vs a
separate worker process on the 1 GB target host). Since agent concurrency is 1
(enforced by Redis lock), this costs no throughput.
"""

from __future__ import annotations

import asyncio
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.cache import get_redis

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
                if processed:
                    consecutive_errors = 0
                else:
                    await asyncio.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - loop must survive anything
                consecutive_errors += 1
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
    """Process at most one job. Returns True if work was done."""
    try:
        redis = get_redis()
        # LPOP: FIFO order. Non-blocking.
        raw = await redis.lpop(settings.JOB_QUEUE_KEY)
    except Exception as exc:  # noqa: BLE001
        log.warning("worker_redis_pop_failed", error=type(exc).__name__)
        return False

    if not raw:
        return False

    # Parse the job payload
    try:
        job = json.loads(raw)
        run_id = job["run_id"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        log.error("worker_invalid_job_payload", raw=str(raw)[:200], error=str(exc))
        return True  # consumed the bad message, don't retry it

    log.info("worker_job_start", run_id=run_id)

    # Execute the pipeline
    from app.db.session import get_sessionmaker
    from app.services.tailor import execute_tailor_job

    async with get_sessionmaker()() as db:
        await execute_tailor_job(db, run_id)

    log.info("worker_job_done", run_id=run_id)
    return True


async def enqueue_job(run_id: str) -> bool:
    """Push a job onto the Redis queue. Returns True on success."""
    try:
        redis = get_redis()
        payload = json.dumps({"run_id": run_id})
        await redis.rpush(settings.JOB_QUEUE_KEY, payload)
        log.info("job_enqueued", run_id=run_id)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("job_enqueue_failed", run_id=run_id, error=type(exc).__name__)
        return False
