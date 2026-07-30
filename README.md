# Tailrd

**Paste a job posting URL. Get your resume rewritten for that exact role, scored against real ATS criteria, with every unmet requirement named.**

Tailrd is a full-stack, production-grade SaaS that tailors a candidate's master resume to a specific job description using an LLM, then measures the result against the same signals an Applicant Tracking System (ATS) uses to rank applicants — all on a $0/month free-tier stack.

---

## The problem

Most qualified candidates get filtered out before a human ever reads their resume, and the reasons are almost entirely mechanical:

1. **ATS keyword filtering.** Companies use Applicant Tracking Systems (Workday, Greenhouse, Lever, iCIMS, Ashby…) that rank or filter resumes by how well they match the job description's keywords, skills, and responsibilities. A strong candidate with a generic resume routinely loses to a weaker one whose resume simply used the words the recruiter searched for.

2. **Tailoring is tedious and people don't do it.** The correct advice — "tailor your resume to every job" — is real but almost nobody follows it, because rewriting a resume for each of 30+ applications is exhausting and error-prone. So people send the same generic resume everywhere and quietly get rejected.

3. **You get no feedback.** When an ATS filters you out, you receive silence. You never learn *which* requirements your resume failed to address, so you can't improve. The loop is invisible.

4. **Generic AI rewrites are obvious and risky.** Pasting "rewrite my resume for this job" into a chatbot produces text littered with em-dashes and buzzwords that a recruiter's eye (and increasingly, AI-detectors) flags instantly — and it gives you no objective measure of whether the result actually matches the role.

## What Tailrd does

Tailrd closes that loop end to end:

- **You paste a job posting URL.** Tailrd scrapes the posting itself — no copy-pasting the description.
- **It rewrites your resume for that role.** An LLM reworks your summary, skills, experience bullets, and projects to foreground what the job asks for, while keeping your name, contact, education, and real employers factual.
- **It scores the result against ATS criteria** — keyword match, skills coverage, multi-word technical-term overlap, and how well your experience addresses the posting's actual responsibilities.
- **It iterates.** If the score is below target, Tailrd feeds the specific gaps (missing skills, uncovered responsibilities) back to the model and tries again, keeping the best-scoring draft.
- **It tells you what's still missing.** The gap report names the exact requirements your resume doesn't yet cover — the feedback an ATS never gives you.
- **It writes clean, human-sounding output.** A deterministic post-pass strips em-dashes, smart quotes, and AI-tell punctuation so the resume reads like a person wrote it.
- **You download a formatted, ATS-parseable DOCX.**

The user watches all of this happen on a live progress screen (scraping → tailoring → generating → scoring) rather than waiting on a blank page.

## How the tailoring pipeline works

```
Job URL ─▶ Scrape JD ─▶ Build base resume ─▶ ┌─ LLM rewrite ─▶ Score vs ATS ─┐
           (httpx +      (from the user's     │                               │
            JSON-LD,      structured profile)  └──── below target? feed gaps ──┘
            Playwright                                back and retry (max N)
            fallback)                                       │
                                                            ▼
                                    Humanize (strip AI tells) ─▶ Generate DOCX ─▶ Score report + download
```

- **JD scraping is tiered and safe.** A lightweight HTTP fetch + schema.org `JobPosting` JSON-LD parse handles most ATS/job boards with no browser. A Playwright headless-browser fallback (optional) reads JavaScript-only single-page career sites. Every URL is **SSRF-guarded** — the target host is resolved and any private/loopback/link-local/cloud-metadata address is refused, and each redirect hop is re-checked.
- **Scoring is dynamic**, extracted from the JD itself (not a hardcoded keyword list), and cleaned so company-marketing sections don't dilute the match. Weighted: keyword match 35%, skills match 25%, experience relevance 30%, multi-word term overlap 10%.
- **The loop is honest.** It aims for a target score but never fabricates employers or degrees; it keeps the best of N attempts and reports the real gaps.

## Architecture

```
┌────────────────────────┐        ┌──────────────────────────────────────────────┐
│  Vercel (Next.js 15)   │        │  Oracle Cloud "Always Free" Arm VM (Ubuntu)    │
│  App Router, RSC, Tail-  │        │  ┌──────────────────────────────────────────┐ │
│  wind. Same-origin proxy │─HTTPS─▶│  │ Caddy            auto-TLS, security hdrs  │ │
│  to the API keeps auth   │        │  │ tailrd-api       FastAPI + in-proc worker │ │
│  cookies first-party.    │        │  │ zen_proxy :9876  OpenAI-compat bridge     │ │
└────────────────────────┘        │  │ opencode serve   OpenCode LLM (:9875)     │ │
                                    │  │ Redis            queue, locks, rate limits│ │
                                    │  └──────────────────────────────────────────┘ │
                                    └───────────┬───────────────┬───────────────────┘
                                                ▼               ▼
                                        Neon Postgres     Cloudflare R2
                                        (serverless DB)   (S3-compatible files)
```

**The LLM is free.** Instead of paying per token, Tailrd runs OpenCode's built-in `deepseek-v4-flash-free` model locally: `zen_proxy` exposes an OpenAI-compatible `/v1/chat/completions` endpoint that bridges to a headless `opencode serve` process, which uses OpenCode's own stored credentials — no external API key. The FastAPI backend just points its OpenAI-compatible agent client at the local proxy.

The API runs its job worker **in-process** (an asyncio task, concurrency 1 via a Redis lock) rather than as a separate process, which keeps the memory footprint small enough for a free-tier box.

## Key features

- **Real auth** — email/password (Argon2) + Google OAuth scaffolding, httpOnly session cookies, CSRF double-submit, email verification and password reset (Resend).
- **Onboarding wizard** — multi-step profile builder with resume upload → LLM parse-to-prefill.
- **Quota & entitlements** — free tier (3 resumes/month), credits, and subscriptions, with automatic refunds when a run fails on a system error.
- **Wait-with-progress UX** — the tailor page polls the run and shows a live progress bar + stepper.
- **Security** — SSRF-guarded scraper, Redis-backed rate limiting on auth/tailor endpoints, security headers + CSP, optional trusted-host allow-list, body-size limits, and a production config guard that refuses to boot with any mock/insecure default.
- **Operations** — Alembic migrations, crash-recovery of interrupted jobs on startup, scheduled data-retention cleanup (DOCX / runs / account deletions), structured logging, health/readiness probes, optional Sentry.
- **Free-only launch mode** — `PAYMENT_PROVIDER=disabled` lets the app run in production with just the free tier (billing endpoints return "not available yet") until payments are wired.
- **230+ backend tests**, dependency-audit clean (`pip-audit`, `npm audit`).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router, RSC), TypeScript, Tailwind CSS, deployed on Vercel |
| Backend | FastAPI, Python 3.11, async SQLAlchemy 2, Pydantic v2, uvicorn |
| Database | PostgreSQL (Neon) in prod, SQLite locally; Alembic migrations |
| Cache/queue | Redis (queue, distributed agent lock, rate limits); fakeredis locally |
| LLM | OpenCode `deepseek-v4-flash-free` via a local OpenAI-compatible proxy (`zen_proxy` → `opencode serve`) |
| Storage | Cloudflare R2 (S3-compatible) in prod, filesystem locally |
| Resume engine | `python-docx` generation + custom ATS scorer + JD parser |
| Scraping | httpx + JSON-LD, optional Playwright fallback (SSRF-guarded) |
| Email / Payments | Resend / Razorpay (both behind interfaces with local mocks) |
| Infra | Oracle Cloud Always Free VM, Caddy (TLS), systemd |

## Repository layout

| Path | Contents |
|---|---|
| `apps/web` | Next.js frontend (Vercel) |
| `apps/api` | FastAPI backend + in-process worker |
| `apps/api/app/engine` | Resume DOCX generator, ATS scorer, JD parser |
| `apps/api/app/services` | Agent runner, JD scraper, `zen_proxy`, storage, quota, maintenance |
| `apps/api/migrations` | Alembic migrations |
| `infra/oracle` | Oracle deploy: provision script, systemd units, Caddyfile, RUNBOOK, DEPLOY_CHECKLIST |
| `DESIGN.md` | Design system and constraints |

## Local development

Prerequisites: Node 20+, Python 3.11+. Everything runs offline by default — SQLite, fakeredis, console email, filesystem storage, mock payments — no credentials required.

**Backend**
```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

**Frontend**
```powershell
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

**Real LLM locally (optional).** Set `AGENT_BACKEND=openai` and run the proxy (needs the `opencode` CLI, logged in once via `opencode auth login`):
```powershell
cd apps/api
.\.venv\Scripts\python.exe -m app.services.zen_proxy   # starts opencode serve + the OpenAI bridge
```

## Testing

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

## Deployment

The full $0/month stack — Oracle Always Free VM + Neon + Cloudflare R2 + OpenCode (free model) + Vercel — is documented step by step in **[`infra/oracle/DEPLOY_CHECKLIST.md`](infra/oracle/DEPLOY_CHECKLIST.md)** and **[`infra/oracle/RUNBOOK.md`](infra/oracle/RUNBOOK.md)**.

## Configuration philosophy

Every external dependency sits behind an interface with a no-credential local implementation, so the entire pipeline is testable offline. `Settings.validate_for_runtime()` refuses to start a production deployment that still has a mock or insecure default active (console email, local storage, SQLite, mock/`disabled` payments handled explicitly, etc.).

---

*Built as a study in shipping a complete, secure, production-shaped SaaS on entirely free infrastructure.*
