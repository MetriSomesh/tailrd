"""Tests for profile and onboarding endpoints."""

from __future__ import annotations

from httpx import AsyncClient


async def _signup_and_get_client(
    client: AsyncClient, email: str = "profile@test.com"
) -> AsyncClient:
    """Helper: sign up a user so the client has auth cookies."""
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "testPass123!", "name": "Profile User"},
    )
    return client


class TestGetProfile:
    async def test_returns_empty_profile_on_first_access(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.get("/api/v1/profile")
        assert r.status_code == 200
        body = r.json()
        assert body["onboarding_step"] == 0
        assert body["is_complete"] is False
        assert body["educations"] == []
        assert body["experiences"] == []

    async def test_requires_auth(self, client: AsyncClient) -> None:
        r = await client.get("/api/v1/profile")
        assert r.status_code == 401


class TestUpdateBasics:
    async def test_saves_contact_info(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.patch(
            "/api/v1/profile/basics",
            json={
                "full_name": "Somesh Metri",
                "phone": "9359611792",
                "email": "somesh@test.com",
                "location": "India",
                "linkedin_url": "https://linkedin.com/in/somesh",
                "github_url": "https://github.com/somesh",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["full_name"] == "Somesh Metri"
        assert body["phone"] == "9359611792"
        assert body["github_url"] == "https://github.com/somesh"


class TestEducations:
    async def test_set_educations(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.put(
            "/api/v1/profile/educations",
            json=[
                {
                    "degree": "B.S. Computer Science",
                    "institution": "DY Patil",
                    "dates": "2022-2025",
                },
                {"degree": "High School", "institution": "Some School", "dates": "2020-2022"},
            ],
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["educations"]) == 2
        assert body["educations"][0]["degree"] == "B.S. Computer Science"
        assert body["educations"][1]["sort_order"] == 1

    async def test_replace_educations(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        await client.put(
            "/api/v1/profile/educations",
            json=[{"degree": "Old", "institution": "Old U"}],
        )
        r = await client.put(
            "/api/v1/profile/educations",
            json=[{"degree": "New", "institution": "New U"}],
        )
        assert r.status_code == 200
        assert len(r.json()["educations"]) == 1
        assert r.json()["educations"][0]["degree"] == "New"


class TestExperiences:
    async def test_set_experiences_with_bullets(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.put(
            "/api/v1/profile/experiences",
            json=[
                {
                    "title": "AI Engineer",
                    "company": "Hitachi",
                    "location": "Remote",
                    "dates": "Dec 2025 - Present",
                    "bullets": [
                        "Built document processing pipelines handling 10k pages/week.",
                        "Deployed REST APIs on AWS with p95 latency under 800ms.",
                    ],
                }
            ],
        )
        assert r.status_code == 200
        exp = r.json()["experiences"][0]
        assert exp["title"] == "AI Engineer"
        assert len(exp["bullets"]) == 2
        assert "10k pages" in exp["bullets"][0]


class TestProjects:
    async def test_set_projects(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.put(
            "/api/v1/profile/projects",
            json=[
                {
                    "title": "AI Chat Assistant",
                    "description": "Built a chatbot with React and FastAPI.",
                    "technologies": ["React", "FastAPI", "Python"],
                    "url": "https://github.com/user/chatbot",
                }
            ],
        )
        assert r.status_code == 200
        proj = r.json()["projects"][0]
        assert proj["title"] == "AI Chat Assistant"
        assert "React" in proj["technologies"]


class TestSkills:
    async def test_set_categorized_skills(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.put(
            "/api/v1/profile/skills",
            json=[
                {"category": "Languages", "items": ["Python", "TypeScript", "JavaScript"]},
                {"category": "Frameworks", "items": ["React", "FastAPI", "Next.js"]},
                {"category": "Databases", "items": ["PostgreSQL", "Redis", "MongoDB"]},
            ],
        )
        assert r.status_code == 200
        skills = r.json()["skills"]
        assert len(skills) == 3
        assert skills[0]["category"] == "Languages"
        assert "Python" in skills[0]["items"]


class TestVoice:
    async def test_set_hook_line_and_ai_toggle(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.patch(
            "/api/v1/profile/voice",
            json={
                "hook_line": "Skilled at tackling ambiguous problem spaces.",
                "allow_ai_projects": True,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "ambiguous" in body["hook_line"]
        assert body["allow_ai_projects"] is True


class TestOnboardingStep:
    async def test_advance_step(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.post("/api/v1/profile/step", json={"step": 3})
        assert r.status_code == 200
        assert r.json()["onboarding_step"] == 3

    async def test_step_8_marks_complete(self, client: AsyncClient) -> None:
        await _signup_and_get_client(client)
        r = await client.post("/api/v1/profile/step", json={"step": 8})
        assert r.status_code == 200
        assert r.json()["is_complete"] is True


class TestBuildBaseResume:
    async def test_produces_correct_format(self, client: AsyncClient) -> None:
        """Verify the internal build_base_resume_json function via the profile service."""
        await _signup_and_get_client(client)
        # Set up a complete profile
        await client.patch(
            "/api/v1/profile/basics",
            json={"full_name": "Test Person", "phone": "1234567890", "email": "t@t.com"},
        )
        await client.put(
            "/api/v1/profile/educations",
            json=[{"degree": "BS CS", "institution": "MIT", "dates": "2020-2024"}],
        )
        await client.put(
            "/api/v1/profile/experiences",
            json=[
                {
                    "title": "SWE",
                    "company": "Google",
                    "dates": "2024-Present",
                    "bullets": ["Did stuff."],
                }
            ],
        )
        await client.put(
            "/api/v1/profile/skills",
            json=[{"category": "Languages", "items": ["Python"]}],
        )

        # Access via internal service (not an API endpoint — it's used by the tailoring pipeline)
        from app.db.session import get_sessionmaker
        from app.services.profile import build_base_resume_json

        async with get_sessionmaker()() as db:
            # Get user ID from /me
            me_r = await client.get("/api/v1/auth/me")
            user_id = me_r.json()["id"]

            resume = await build_base_resume_json(db, user_id)

        assert resume["immutable"]["name"] == "Test Person"
        assert resume["immutable"]["contact"]["phone"] == "1234567890"
        assert len(resume["immutable"]["education"]) == 1
        assert resume["editable"]["experience"][0]["title"] == "SWE"
        assert "Python" in resume["editable"]["skills"]["Languages"]
