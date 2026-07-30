"""Tests for crash-recovery + data-retention maintenance."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.db.base import new_uuid, utcnow
from app.db.models.run import TailorRun
from app.db.models.user import User
from app.db.session import get_sessionmaker
from app.services import maintenance


async def _mk_user(db, **kw) -> User:
    u = User(id=new_uuid(), email=f"{new_uuid()[:10]}@ex.com", name="T", **kw)
    db.add(u)
    await db.flush()
    return u


class TestRecoverOrphanedJobs:
    async def test_running_job_failed_and_refunded(self, app) -> None:
        sm = get_sessionmaker()
        async with sm() as db:
            u = await _mk_user(db)
            run = TailorRun(
                id=new_uuid(),
                user_id=u.id,
                status="running",
                jd_text="x",
                entitlement_consumed=True,
                entitlement_refunded=False,
                entitlement_source="free",
            )
            db.add(run)
            await db.commit()
            rid = run.id

        async with sm() as db:
            assert await maintenance.recover_orphaned_jobs(db) == 1

        async with sm() as db:
            r = (await db.execute(select(TailorRun).where(TailorRun.id == rid))).scalar_one()
            assert r.status == "failed"
            assert r.error_code == "interrupted"
            assert r.entitlement_refunded is True

    async def test_leaves_non_running_untouched(self, app) -> None:
        sm = get_sessionmaker()
        async with sm() as db:
            u = await _mk_user(db)
            for st in ("queued", "succeeded", "failed"):
                db.add(TailorRun(id=new_uuid(), user_id=u.id, status=st, jd_text="x"))
            await db.commit()

        async with sm() as db:
            assert await maintenance.recover_orphaned_jobs(db) == 0


class TestRetention:
    async def test_purge_expired_docx_keeps_row(self, app) -> None:
        sm = get_sessionmaker()
        old = utcnow() - timedelta(days=settings.RETAIN_DOCX_DAYS + 1)
        async with sm() as db:
            u = await _mk_user(db)
            run = TailorRun(
                id=new_uuid(),
                user_id=u.id,
                status="succeeded",
                jd_text="x",
                docx_storage_key="resumes/x/y/z.docx",
                created_at=old,
            )
            db.add(run)
            await db.commit()
            rid = run.id

        async with sm() as db:
            assert await maintenance.purge_expired_docx(db) == 1

        async with sm() as db:
            r = (await db.execute(select(TailorRun).where(TailorRun.id == rid))).scalar_one()
            assert r.docx_storage_key is None  # file dereferenced
            assert r.status == "succeeded"  # row kept for history/score

    async def test_recent_docx_untouched(self, app) -> None:
        sm = get_sessionmaker()
        async with sm() as db:
            u = await _mk_user(db)
            run = TailorRun(
                id=new_uuid(),
                user_id=u.id,
                status="succeeded",
                jd_text="x",
                docx_storage_key="resumes/a/b/c.docx",
            )
            db.add(run)
            await db.commit()
            rid = run.id

        async with sm() as db:
            assert await maintenance.purge_expired_docx(db) == 0

        async with sm() as db:
            r = (await db.execute(select(TailorRun).where(TailorRun.id == rid))).scalar_one()
            assert r.docx_storage_key == "resumes/a/b/c.docx"

    async def test_purge_old_runs_deletes_row(self, app) -> None:
        sm = get_sessionmaker()
        old = utcnow() - timedelta(days=settings.RETAIN_RUNS_DAYS + 1)
        async with sm() as db:
            u = await _mk_user(db)
            db.add(
                TailorRun(
                    id=new_uuid(), user_id=u.id, status="succeeded", jd_text="x", created_at=old
                )
            )
            await db.commit()

        async with sm() as db:
            assert await maintenance.purge_old_runs(db) == 1

        async with sm() as db:
            remaining = (await db.execute(select(TailorRun))).scalars().all()
            assert remaining == []

    async def test_finalize_account_past_grace(self, app) -> None:
        sm = get_sessionmaker()
        old = utcnow() - timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS + 1)
        async with sm() as db:
            gone = await _mk_user(db, deleted_at=old)
            db.add(TailorRun(id=new_uuid(), user_id=gone.id, status="succeeded", jd_text="x"))
            # A user still within grace must survive.
            await _mk_user(db, deleted_at=utcnow())
            # An active user must survive.
            await _mk_user(db)
            await db.commit()
            gone_id = gone.id

        async with sm() as db:
            assert await maintenance.finalize_account_deletions(db) == 1

        async with sm() as db:
            assert (
                await db.execute(select(User).where(User.id == gone_id))
            ).scalar_one_or_none() is None
            assert (await db.execute(select(User))).scalars().all().__len__() == 2
            # The deleted user's runs are gone too.
            assert (
                await db.execute(select(TailorRun).where(TailorRun.user_id == gone_id))
            ).scalars().all() == []
