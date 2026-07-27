"""Tests for the tailor pipeline: submit, poll, download, worker execution."""

from __future__ import annotations

from httpx import AsyncClient

JD_TEXT = """AI Engineer — TestCorp

Responsibilities:
- Building LLM-powered agents and multi-agent orchestration systems.
- Improving retrieval, document processing, and context management.
- Designing backend systems, APIs, and services.

Qualifications:
- Strong engineering fundamentals in Python.
- Experience building with LLMs, agents, retrieval systems.
- Comfortable with Postgres, Redis, Docker, cloud services.
"""


async def _create_complete_user(client: AsyncClient) -> None:
    """Create a user, fill profile, mark onboarding complete, and verify email."""
    # Sign up
    await client.post(
        "/api/v1/auth/signup",
        json={"email": "tailor@test.com", "password": "strongPass123!", "name": "Tailor User"},
    )
    # Fill basics
    await client.patch(
        "/api/v1/profile/basics",
        json={"full_name": "Tailor User", "phone": "1234567890", "email": "tailor@test.com"},
    )
    # Add education
    await client.put(
        "/api/v1/profile/educations",
        json=[{"degree": "BS CS", "institution": "Test U", "dates": "2020-2024"}],
    )
    # Add experience
    await client.put(
        "/api/v1/profile/experiences",
        json=[
            {
                "title": "SWE",
                "company": "BigCo",
                "dates": "2024-Present",
                "bullets": ["Built stuff."],
            }
        ],
    )
    # Add skills
    await client.put(
        "/api/v1/profile/skills",
        json=[{"category": "Languages", "items": ["Python", "TypeScript"]}],
    )
    # Complete onboarding
    await client.post("/api/v1/profile/step", json={"step": 8})

    # Verify email (directly via DB since we can't click the email link in tests)
    from sqlalchemy import select

    from app.db.base import utcnow
    from app.db.models.user import User
    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as db:
        result = await db.execute(select(User).where(User.email == "tailor@test.com"))
        user = result.scalar_one()
        user.email_verified_at = utcnow()
        await db.commit()


class TestSubmitTailor:
    async def test_submit_returns_202_with_run_id(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT, "company": "TestCorp", "role": "AI Engineer"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 202
        body = r.json()
        assert "run_id" in body
        assert body["status"] == "queued"

    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT},
            headers={"X-CSRF-Token": "fake"},
        )
        assert r.status_code in (401, 403)

    async def test_requires_completed_onboarding(self, client: AsyncClient) -> None:
        # Sign up but don't complete profile
        await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "incomplete@test.com",
                "password": "strongPass123!",
                "name": "Incomplete",
            },
        )
        # Verify email
        from sqlalchemy import select

        from app.db.base import utcnow
        from app.db.models.user import User
        from app.db.session import get_sessionmaker

        async with get_sessionmaker()() as db:
            result = await db.execute(select(User).where(User.email == "incomplete@test.com"))
            user = result.scalar_one()
            user.email_verified_at = utcnow()
            await db.commit()

        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "onboarding_incomplete"

    async def test_validates_short_jd(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": "Too short."},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 422


class TestListRuns:
    async def test_lists_user_runs(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        # Submit a job
        await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT, "company": "TestCorp"},
            headers={"X-CSRF-Token": csrf},
        )
        r = await client.get("/api/v1/runs")
        assert r.status_code == 200
        runs = r.json()
        assert len(runs) >= 1
        assert runs[0]["company"] == "TestCorp"
        assert runs[0]["status"] == "queued"

    async def test_empty_when_no_runs(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": "noruns@test.com", "password": "strongPass123!", "name": "No Runs"},
        )
        r = await client.get("/api/v1/runs")
        assert r.status_code == 200
        assert r.json() == []


class TestGetRun:
    async def test_get_run_detail(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        submit_r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT, "role": "AI Eng"},
            headers={"X-CSRF-Token": csrf},
        )
        run_id = submit_r.json()["run_id"]
        r = await client.get(f"/api/v1/runs/{run_id}")
        assert r.status_code == 200
        detail = r.json()
        assert detail["id"] == run_id
        assert detail["jd_text"] == JD_TEXT
        assert detail["role"] == "AI Eng"

    async def test_404_for_other_users_run(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/runs/nonexistent_id_12345678")
        # Will be 401 (no auth) or 404
        assert r.status_code in (401, 404)


class TestQuotaEnforcement:
    async def test_free_tier_exhaustion_returns_402(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        # Three free resumes are allowed.
        for _ in range(3):
            r = await client.post(
                "/api/v1/tailor",
                json={"jd_text": JD_TEXT},
                headers={"X-CSRF-Token": csrf},
            )
            assert r.status_code == 202
        # The fourth is blocked with 402.
        r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 402
        assert r.json()["code"] == "quota_exceeded"

    async def test_submit_decrements_free_usage(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT},
            headers={"X-CSRF-Token": csrf},
        )
        r = await client.get("/api/v1/billing/usage")
        body = r.json()
        assert body["free_used"] == 1
        assert body["free_remaining"] == 2

    async def test_credit_consumed_when_no_free_left(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        # Exhaust free tier.
        for _ in range(3):
            await client.post(
                "/api/v1/tailor", json={"jd_text": JD_TEXT}, headers={"X-CSRF-Token": csrf}
            )
        # Grant a credit directly, then the next submit should consume it.
        from sqlalchemy import select

        from app.db.models.user import User
        from app.db.session import get_sessionmaker
        from app.services.quota import add_credits

        async with get_sessionmaker()() as db:
            uid = (
                await db.execute(select(User).where(User.email == "tailor@test.com"))
            ).scalar_one().id
            await add_credits(db, uid, 1)
            await db.commit()

        r = await client.post(
            "/api/v1/tailor", json={"jd_text": JD_TEXT}, headers={"X-CSRF-Token": csrf}
        )
        assert r.status_code == 202
        usage = (await client.get("/api/v1/billing/usage")).json()
        assert usage["credit_balance"] == 0

    async def test_entitlement_refunded_on_system_failure(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")

        # Force the agent to fail with a refundable (system) error.
        from app.core.errors import AgentUnavailableError
        from app.services import tailor as tailor_service

        async def _boom(*_a, **_k):
            raise AgentUnavailableError("engine down")

        monkeypatch.setattr(tailor_service, "run_agent", _boom)

        submit = await client.post(
            "/api/v1/tailor", json={"jd_text": JD_TEXT}, headers={"X-CSRF-Token": csrf}
        )
        run_id = submit.json()["run_id"]
        # Free usage was consumed on submit.
        assert (await client.get("/api/v1/billing/usage")).json()["free_used"] == 1

        from app.workers.runner import _tick

        await _tick()

        detail = (await client.get(f"/api/v1/runs/{run_id}")).json()
        assert detail["status"] == "failed"
        # The consumed free resume must be refunded.
        assert (await client.get("/api/v1/billing/usage")).json()["free_used"] == 0


class TestWorkerExecution:
    async def test_worker_processes_queued_job(self, client: AsyncClient) -> None:
        """Submit a job, manually tick the worker, verify it completes."""
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        submit_r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT, "company": "WorkerTest"},
            headers={"X-CSRF-Token": csrf},
        )
        run_id = submit_r.json()["run_id"]

        # Manually process the job (simulates what the worker loop does)
        from app.workers.runner import _tick

        processed = await _tick()
        assert processed is True

        # Check the run is now succeeded
        r = await client.get(f"/api/v1/runs/{run_id}")
        detail = r.json()
        assert detail["status"] == "succeeded"
        assert detail["overall_score"] is not None
        assert detail["overall_score"] > 0
        assert detail["tailored_json"] is not None
        assert detail["score_json"] is not None
        assert detail["docx_storage_key"] is not None
        assert detail["iterations"] >= 1

    async def test_worker_produces_downloadable_docx(self, client: AsyncClient) -> None:
        """Full pipeline: submit → process → download."""
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        submit_r = await client.post(
            "/api/v1/tailor",
            json={"jd_text": JD_TEXT},
            headers={"X-CSRF-Token": csrf},
        )
        run_id = submit_r.json()["run_id"]

        from app.workers.runner import _tick

        await _tick()

        # Download
        r = await client.get(f"/api/v1/runs/{run_id}/download")
        assert r.status_code == 200
        assert "application/vnd.openxmlformats" in r.headers["content-type"]
        assert len(r.content) > 1000  # A real DOCX is at least a few KB

    async def test_url_only_submit_scrapes_then_tailors(
        self, client: AsyncClient, monkeypatch
    ) -> None:
        """Primary flow: submit a posting URL (no text); the worker scrapes it,
        fills jd_text, and tailors against that."""
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")

        scraped = (
            "AI Engineer — TestCorp\n\nBuild LLM agents, retrieval pipelines and "
            "backend APIs. Python, FastAPI, evaluation and observability required."
        )

        from app.services import jd_scraper

        async def _fake_scrape(url: str) -> str:
            assert url == "https://jobs.testcorp.com/ai-engineer"
            return scraped

        monkeypatch.setattr(jd_scraper, "scrape_jd", _fake_scrape)

        submit_r = await client.post(
            "/api/v1/tailor",
            json={"jd_url": "https://jobs.testcorp.com/ai-engineer"},
            headers={"X-CSRF-Token": csrf},
        )
        assert submit_r.status_code == 202
        run_id = submit_r.json()["run_id"]

        from app.workers.runner import _tick

        await _tick()

        detail = (await client.get(f"/api/v1/runs/{run_id}")).json()
        assert detail["status"] == "succeeded"
        assert detail["jd_text"] == scraped  # scraped text was persisted
        assert detail["overall_score"] is not None

    async def test_submit_without_url_or_text_is_rejected(self, client: AsyncClient) -> None:
        await _create_complete_user(client)
        csrf = client.cookies.get("tailrd_csrf")
        r = await client.post(
            "/api/v1/tailor",
            json={"company": "NoSource"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 422
