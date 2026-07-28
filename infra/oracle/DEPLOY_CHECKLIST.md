# Tailrd — Oracle deploy checklist

A condensed, ordered pre-flight. Full detail is in `RUNBOOK.md`. Canonical
artifacts are under `infra/oracle/` (the top-level `infra/` set is the legacy
EC2 deploy — ignore it for Oracle).

Dry-run status (validated locally, 2026-07): Alembic emits valid Postgres DDL
(17 tables), a fully-configured prod boots clean (`validate_for_runtime() == []`),
`pip check`/`pip-audit`/`npm audit` clean, shell scripts are LF. See "Known
blocker" before starting.

## ⚠ Known blocker: payments in production

`validate_for_runtime()` refuses to boot with `PAYMENT_PROVIDER=mock` in
production. So today prod requires Razorpay configured. If launching free-only
(payments deferred), you must first either wire Razorpay OR add a
payments-disabled mode (see the team; not yet implemented). Everything else below
is ready.

## 0. Accounts + secrets to have on hand
- [ ] Oracle Cloud account + an Ampere A1 (Arm) Always Free VM, Ubuntu 22.04/24.04
- [ ] Neon Postgres connection string (`postgresql+psycopg://...`)
- [ ] Cloudflare R2 bucket + S3 API key/secret + account endpoint
- [ ] A domain for the API (e.g. `api.yourdomain.com`) with DNS access
- [ ] Resend API key + a verified sender domain
- [ ] (optional) Sentry DSN
- [ ] (required for prod today) Razorpay key id/secret + webhook secret

## 1. Network (two layers)
- [ ] VCN Security List: ingress TCP 80 + 443 from 0.0.0.0/0
- [ ] OS iptables 80/443 (handled by provision script; verify `sudo iptables -L INPUT`)

## 2. Provision
- [ ] `sudo mkdir -p /opt/tailrd && sudo chown $USER /opt/tailrd`
- [ ] `git clone <repo> /opt/tailrd`  (code lands at `/opt/tailrd/apps/api`)
- [ ] `sudo bash /opt/tailrd/infra/oracle/provision-oracle.sh`
- [ ] `sudo chown -R tailrd:tailrd /opt/tailrd`

## 3. Configure env
- [ ] `sudo cp /opt/tailrd/infra/oracle/.env.production.example /opt/tailrd/.env`
- [ ] Fill Neon / R2 / Resend / Razorpay / (Sentry); set `FRONTEND_URL` https,
      `CORS_ORIGINS` to the site, `ALLOWED_HOSTS=api.yourdomain.com,127.0.0.1,localhost`,
      `TRUST_PROXY_HEADERS=true`
- [ ] `sudo chown tailrd:tailrd /opt/tailrd/.env && sudo chmod 600 /opt/tailrd/.env`

## 4. Python deps
- [ ] `VENV=/opt/tailrd/apps/api/.venv`
- [ ] `sudo -u tailrd $VENV/bin/pip install -r /opt/tailrd/apps/api/requirements.txt`
- [ ] (SPA scraping) install `requirements-scraper.txt` + `playwright install chromium`

## 5. LLM stack (free, local)
- [ ] Install OpenCode CLI for the tailrd user; `opencode auth login` (free Zen)
- [ ] `sudo systemctl enable --now tailrd-opencode tailrd-zenproxy`
- [ ] `curl -s http://127.0.0.1:9876/v1/models` → model list

## 6. Database
- [ ] `cd /opt/tailrd/apps/api && sudo -u tailrd $VENV/bin/alembic upgrade head`

## 7. TLS + start
- [ ] `sudo cp /opt/tailrd/infra/Caddyfile /etc/caddy/Caddyfile` then set your domain
- [ ] DNS `A` record for the API host → VM public IP
- [ ] `sudo systemctl enable --now tailrd-api caddy`
- [ ] `curl -s http://127.0.0.1:8000/ready` → `{"status":"ready", ... agent: openai endpoint up}`

## 8. Smoke test (prod)
- [ ] Sign up → receive verification email (Resend) → verify via `/verify`
- [ ] Complete onboarding (resume upload parse works)
- [ ] Tailor a real posting URL → progress → succeeded → download DOCX
- [ ] Forgot-password → reset via `/reset-password` → login with new password
- [ ] Hammer login 6× → 6th returns 429 (rate limiting live)

## 9. Ops
- [ ] Point an uptime monitor at `https://api.yourdomain.com/health`
- [ ] `journalctl -u tailrd-api -u tailrd-zenproxy -u tailrd-opencode -f` looks clean

## Rollback
- [ ] `cd /opt/tailrd && sudo -u tailrd git checkout <previous-tag>`
- [ ] `sudo -u tailrd $VENV/bin/pip install -r apps/api/requirements.txt`
- [ ] `cd apps/api && sudo -u tailrd $VENV/bin/alembic downgrade -1` (only if a migration shipped)
- [ ] `sudo systemctl restart tailrd-api tailrd-zenproxy`
