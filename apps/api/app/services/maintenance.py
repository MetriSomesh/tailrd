"""Background maintenance: crash recovery + data retention.

Runs in-process (like the job worker) so the single-host free-tier deploy needs
no extra scheduler. Recovery runs once at startup; retention sweeps run on an
interval. Every function is idempotent and safe to run repeatedly.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import utcnow
from app.db.models.run import TailorRun
from app.db.models.user import User
from app.services.quota import refund_entitlement
from app.services.storage import get_storage

log = get_logger(__name__)


async def recover_orphaned_jobs(db: AsyncSession) -> int:
    """Fail runs left 'running' by a crash/restart and refund their entitlement.

    A run is only 'running' while the worker actively holds it; if the process
    died mid-tailor the row would otherwise be stuck forever. Since we can't
    resume, we fail it (our fault → always refund) so the user isn't charged.
    """
    result = await db.execute(select(TailorRun).where(TailorRun.status == "running"))
    runs = result.scalars().all()
    for run in runs:
        run.status = "failed"
        run.error_code = "interrupted"
        run.error_message = "The server restarted while this run was in progress. Please try again."
        run.progress_stage = "failed"
        run.finished_at = utcnow()
        if run.entitlement_consumed and not run.entitlement_refunded:
            await refund_entitlement(db, run.user_id, run.entitlement_source or "free")
            run.entitlement_refunded = True
    await db.commit()
    if runs:
        log.info("orphaned_jobs_recovered", count=len(runs))
    return len(runs)


async def purge_expired_docx(db: AsyncSession) -> int:
    """Delete DOCX artifacts older than RETAIN_DOCX_DAYS (keep the run/score row)."""
    cutoff = utcnow() - timedelta(days=settings.RETAIN_DOCX_DAYS)
    result = await db.execute(
        select(TailorRun).where(
            TailorRun.docx_storage_key.is_not(None),
            TailorRun.created_at < cutoff,
        )
    )
    runs = result.scalars().all()
    storage = get_storage()
    for run in runs:
        try:
            await storage.delete(run.docx_storage_key)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001 - storage delete is best-effort
            log.warning("docx_purge_delete_failed", run_id=run.id, error=type(exc).__name__)
        run.docx_storage_key = None
    await db.commit()
    if runs:
        log.info("expired_docx_purged", count=len(runs))
    return len(runs)


async def purge_old_runs(db: AsyncSession) -> int:
    """Delete run rows (and any lingering DOCX) older than RETAIN_RUNS_DAYS."""
    cutoff = utcnow() - timedelta(days=settings.RETAIN_RUNS_DAYS)
    result = await db.execute(select(TailorRun).where(TailorRun.created_at < cutoff))
    runs = result.scalars().all()
    storage = get_storage()
    for run in runs:
        if run.docx_storage_key:
            try:
                await storage.delete(run.docx_storage_key)
            except Exception as exc:  # noqa: BLE001
                log.warning("old_run_docx_delete_failed", run_id=run.id, error=type(exc).__name__)
        await db.delete(run)
    await db.commit()
    if runs:
        log.info("old_runs_purged", count=len(runs))
    return len(runs)


async def finalize_account_deletions(db: AsyncSession) -> int:
    """Hard-delete users whose deletion grace period has passed.

    Removes their DOCX and run rows first, then the user row (Postgres cascades
    the remaining child tables; sessions/oauth cascade via the ORM relationship).
    """
    cutoff = utcnow() - timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)
    result = await db.execute(
        select(User).where(User.deleted_at.is_not(None), User.deleted_at < cutoff)
    )
    users = result.scalars().all()
    storage = get_storage()
    for user in users:
        runs = (
            (await db.execute(select(TailorRun).where(TailorRun.user_id == user.id)))
            .scalars()
            .all()
        )
        for run in runs:
            if run.docx_storage_key:
                try:
                    await storage.delete(run.docx_storage_key)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "account_docx_delete_failed", run_id=run.id, error=type(exc).__name__
                    )
            await db.delete(run)
        await db.delete(user)
        log.info("account_finalized", user_id=user.id)
    await db.commit()
    return len(users)


async def run_retention_sweep() -> None:
    """One full retention pass, each step in its own session."""
    from app.db.session import get_sessionmaker

    sm = get_sessionmaker()
    async with sm() as db:
        docx = await purge_expired_docx(db)
    async with sm() as db:
        runs = await purge_old_runs(db)
    async with sm() as db:
        accts = await finalize_account_deletions(db)
    log.info("maintenance_cycle", docx_purged=docx, runs_purged=runs, accounts_finalized=accts)


async def maintenance_loop() -> None:
    """Startup crash-recovery, then a retention sweep every interval."""
    from app.db.session import get_sessionmaker

    log.info("maintenance_loop_entered", interval=settings.MAINTENANCE_INTERVAL_SECONDS)
    sm = get_sessionmaker()

    try:
        async with sm() as db:
            await recover_orphaned_jobs(db)
    except Exception:  # noqa: BLE001 - never let startup recovery kill the loop
        log.exception("orphaned_recovery_failed")

    try:
        while True:
            try:
                await run_retention_sweep()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - a bad sweep must not stop future ones
                log.exception("maintenance_cycle_failed")
            await asyncio.sleep(settings.MAINTENANCE_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        log.info("maintenance_loop_cancelled")
        raise
