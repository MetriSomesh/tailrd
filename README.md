# Tailrd

AI resume tailoring as a service. Rewrites a resume against a specific job
description, scores it against ATS criteria, validates that ATS parsers can
actually read the output, and reports which requirements remain uncovered.

## Architecture

```
Vercel (Next.js)  ──HTTPS──▶  EC2 t3.micro, 1 GB, native systemd
                                ├── Caddy            TLS + headers
                                ├── tailrd-api       FastAPI + in-process worker
                                ├── Redis (64 MB)    queue, locks, rate limits
                                └── opencode         spawned per job, transient
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                   Neon Postgres    AWS S3     Razorpay / Resend
```

No Docker: the daemon alone costs ~100 MB and the target host has 1 GB. The
agent is a short-lived subprocess, serialised to concurrency 1 by a Redis lock,
so its ~400 MB peak is transient rather than resident.

## Layout

| Path | Contents |
|---|---|
| `apps/web` | Next.js frontend, deployed to Vercel |
| `apps/api` | FastAPI backend, deployed to EC2 |
| `apps/api/app/engine` | Resume engine ported from the original CLI tool |
| `agent/skills` | `SKILL.md` consumed by Hermes + OpenCode |
| `infra` | systemd units, Caddyfile, deploy scripts |
| `DESIGN.md` | Committed design system and its constraints |

## Local development

Prerequisites: Node 20+, Python 3.11+.

### Backend

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Defaults run fully offline: SQLite, fakeredis, console email, local filesystem
storage, mock payments, mock agent. No credentials required.

### Frontend

```powershell
cd apps/web
npm install
npm run dev
```

## Verification

```powershell
# Backend
cd apps/api
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m ruff format --check app tests
.\.venv\Scripts\python.exe -m pytest tests/ -v

# Frontend
cd apps/web
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
npm run test:e2e          # includes axe-core WCAG checks
```

## Configuration

Every external dependency sits behind an interface with a no-credential local
implementation, so the whole pipeline is testable offline:

| Concern | Local default | Production |
|---|---|---|
| Database | SQLite | PostgreSQL (Neon) |
| Cache/queue | fakeredis | Redis |
| Email | stdout | Resend |
| Storage | filesystem | AWS S3 |
| Payments | deterministic mock | Razorpay |
| Agent | deterministic stub | OpenCode subprocess |

`Settings.validate_for_runtime()` refuses to boot if a production deployment
still has any mock or insecure default active.

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Scaffold, design system, CI, local dev | Done |
| 1 | Auth, legal pages, DPDP endpoints, email | Pending |
| 2 | Profile schema, 8-step onboarding, resume parse | Pending |
| 3 | Engine port + test migration | Pending |
| 4 | Agent runner (subprocess, lock, breaker) | Pending |
| 5 | Async pipeline, storage, run history | Pending |
| 6 | Quota, fair-use caps, Razorpay | Pending |
| 7 | Dashboard UI, E2E, a11y audit | Pending |
| 8 | Marketing site, SEO, analytics | Pending |
| 9 | Deployment artifacts | Pending |
| 10 | Visual regression, design iteration | Pending |

## Credentials still required

These are stubbed with working mocks. Real values are needed before launch:

- Razorpay key id / secret / webhook secret (business KYC gates live mode)
- Resend API key, or AWS SES with production access
- Google OAuth client id / secret
- Neon connection string
- S3 bucket and IAM credentials
