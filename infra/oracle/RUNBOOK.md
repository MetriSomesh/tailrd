# Deploying Tailrd on Oracle Cloud "Always Free"

A $0/month, always-on deployment: Oracle Arm A1 VM (API + worker + Redis +
zen_proxy + `opencode serve` + optional headless-browser scrape) → Neon
(Postgres) → Cloudflare R2 (files) → OpenCode (free LLM, local proxy).
Frontend stays on Vercel.

The LLM path is entirely local and free: the API (`AGENT_BACKEND=openai`) calls
`zen_proxy` on `127.0.0.1:9876`, which bridges to `opencode serve` on `:9875`,
which uses OpenCode's built-in `deepseek-v4-flash-free` via stored credentials —
no external API key.

## 0. Free services to create first
- **Oracle Cloud** account (credit card required for signup; Always Free is never charged).
- **Neon** — a Postgres project → copy the `psycopg` connection string.
- **Cloudflare R2** — a bucket + an S3 API token (Access Key ID / Secret) + your account's R2 endpoint.
- **OpenCode CLI** — installed on the VM and logged in once (`opencode auth login`, pick the
  free Zen provider). No API key needs to live in `.env`.
- (Optional) **Resend** (email) and **Razorpay** (payments) for full production.

## 1. Launch the VM
- Compute → Create Instance.
- Shape: **Ampere (Arm) — VM.Standard.A1.Flex**, 2 OCPU / 12 GB (Always Free eligible).
  - If A1 capacity is unavailable in your home region, try another availability domain,
    retry later, or fall back to the AMD `VM.Standard.E2.1.Micro` (1 GB — API works, but
    keep `JD_SCRAPE_BROWSER_FALLBACK=false` there).
- Image: **Ubuntu 22.04/24.04**.
- Add your SSH public key. Assign a public IP.

## 2. Open the network (two layers!)
Oracle blocks inbound by default at BOTH the cloud and OS level.
1. **VCN Security List / NSG** (cloud): add Ingress rules for TCP **80** and **443** from `0.0.0.0/0`.
2. **OS iptables**: handled by `provision-oracle.sh` (step 3), but verify with `sudo iptables -L INPUT`.

## 3. Provision
```bash
ssh ubuntu@YOUR_PUBLIC_IP
sudo mkdir -p /opt/tailrd && sudo chown $USER /opt/tailrd
git clone <your-repo-url> /opt/tailrd
sudo bash /opt/tailrd/infra/oracle/provision-oracle.sh
sudo chown -R tailrd:tailrd /opt/tailrd
```

## 4. Configure env
```bash
sudo cp /opt/tailrd/infra/oracle/.env.production.example /opt/tailrd/.env
sudo nano /opt/tailrd/.env      # fill in Neon / R2 / Zen (+ Resend/Razorpay for full prod)
sudo chown tailrd:tailrd /opt/tailrd/.env && sudo chmod 600 /opt/tailrd/.env
```

## 5. Install Python deps (+ browser fallback)
```bash
VENV=/opt/tailrd/api/.venv
sudo -u tailrd $VENV/bin/pip install --upgrade pip
sudo -u tailrd $VENV/bin/pip install -r /opt/tailrd/apps/api/requirements.txt

# Browser fallback (only if JD_SCRAPE_BROWSER_FALLBACK=true):
sudo -u tailrd $VENV/bin/pip install -r /opt/tailrd/apps/api/requirements-scraper.txt
sudo $VENV/bin/playwright install-deps chromium
sudo -u tailrd PLAYWRIGHT_BROWSERS_PATH=/opt/tailrd/ms-playwright $VENV/bin/playwright install chromium
```
Note: the systemd unit runs uvicorn from `WorkingDirectory=/opt/tailrd/api`. Ensure the
API code is reachable there (e.g. symlink `sudo -u tailrd ln -s /opt/tailrd/apps/api /opt/tailrd/api`
if you cloned the monorepo), or adjust the unit's paths to `/opt/tailrd/apps/api`.

## 5b. LLM stack: OpenCode CLI + zen_proxy (local, free, no API key)
```bash
# Install the OpenCode CLI for the tailrd user (npm global into ~/.npm-global).
sudo -u tailrd -i bash -c '
  npm config set prefix /opt/tailrd/.npm-global
  npm install -g opencode-ai
  /opt/tailrd/.npm-global/bin/opencode auth login    # pick the free Zen provider
'

# Install + start the two LLM units (opencode serve, then the OpenAI bridge).
sudo cp /opt/tailrd/infra/oracle/tailrd-opencode.service /etc/systemd/system/
sudo cp /opt/tailrd/infra/oracle/tailrd-zenproxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tailrd-opencode tailrd-zenproxy

# Verify the bridge answers (loopback only):
curl -s http://127.0.0.1:9876/v1/models        # expect the model list
```
Both ports (9875, 9876) bind to `127.0.0.1` only and are never exposed by Caddy.
`opencode serve` runs without auth because it's loopback-only; set
`OPENCODE_SERVER_PASSWORD` on both units to force Basic auth if you want defence in depth.

## 6. Migrate the database (Postgres/Neon uses Alembic)
```bash
cd /opt/tailrd/apps/api && sudo -u tailrd $VENV/bin/alembic upgrade head
```

## 7. TLS + start
```bash
sudo nano /etc/caddy/Caddyfile     # replace YOUR_DOMAIN with api.yourdomain.com (copy infra/Caddyfile)
sudo cp /opt/tailrd/infra/Caddyfile /etc/caddy/Caddyfile   # then edit the domain
sudo systemctl enable --now tailrd-api caddy
# /ready should show agent: "openai endpoint up (http://127.0.0.1:9876/v1, ...)"
curl -s http://127.0.0.1:8000/ready    # expect {"status":"ready",...}
```
Point your DNS `A` record for `api.yourdomain.com` at the VM's public IP; Caddy auto-issues TLS.

## 8. Redeploys
```bash
cd /opt/tailrd && sudo -u tailrd git pull --ff-only
sudo -u tailrd $VENV/bin/pip install -r apps/api/requirements.txt
cd apps/api && sudo -u tailrd $VENV/bin/alembic upgrade head
sudo systemctl restart tailrd-api && curl -s http://127.0.0.1:8000/ready
# If zen_proxy.py changed: sudo systemctl restart tailrd-zenproxy
# If the LLM is unreachable: sudo systemctl status tailrd-opencode tailrd-zenproxy
```

## Notes
- **Cost:** VM is Always Free; Neon/R2/Zen free tiers cover low volume. Watch Neon compute-hours
  and R2 storage if usage grows.
- **Scrape fallback:** with `JD_SCRAPE_BROWSER_FALLBACK=true`, JS-only SPA postings render via
  Chromium (one at a time — worker concurrency is 1). HTTP-first keeps most scrapes browser-free.
- **Frontend:** set the Vercel project's API base to `https://api.yourdomain.com` and keep the
  same-origin `/api/backend` rewrite pointing there.

## Monitoring & health

Two probes (no auth, cheap):
- `GET /health` — liveness only, never touches dependencies. Point an external
  uptime monitor (e.g. UptimeRobot's free tier, Better Uptime) at
  `https://api.yourdomain.com/health` on a 1–5 min interval.
- `GET /ready` — readiness: checks Postgres (required → 503 if down), Redis and
  the LLM endpoint (informational, surfaced via `"degraded": true`). Useful for a
  deeper check or a status page.

Error tracking (optional but recommended): set `SENTRY_DSN` in `/opt/tailrd/.env`
(free Sentry tier). It's initialised at startup with `send_default_pii=false` and
a 10% trace sample; leave it unset to disable.

Process health: systemd restarts each unit on failure (`Restart=on-failure`/
`always`). Inspect logs with:
```bash
journalctl -u tailrd-api -u tailrd-zenproxy -u tailrd-opencode -f
```
The API also logs structured JSON per request (skipping `/health`,`/ready`) with a
request id you can grep for when a user reports an error.

## Capacity & backups

Throughput: the API runs a single in-process worker (`WORKER_CONCURRENCY=1`), so
exactly one tailor job runs at a time. A job is typically 2 LLM calls and lands
around 1–3 minutes, i.e. very roughly 20–40 resumes/hour. Jobs queue in Redis and
run FIFO; users watch live progress while they wait. This is comfortable for the
free tier. Scale by moving the worker to its own process/box (set
`WORKER_ENABLED=false` on the API and run a dedicated worker) before raising
concurrency — two simultaneous agents roughly double memory.

Footprint on the 12 GB A1: API+worker, `opencode serve`, `zen_proxy`, Redis, and
(optionally) one headless Chromium peak a few hundred MB transiently — far under
the box. `MemoryMax` on each unit is a guard, not a target.

Maintenance: the API runs an in-process sweep every `MAINTENANCE_INTERVAL_SECONDS`
(6h) that recovers crash-interrupted runs at startup and enforces retention
(`RETAIN_DOCX_DAYS`, `RETAIN_RUNS_DAYS`, `ACCOUNT_DELETION_GRACE_DAYS`).

Backups:
- Postgres (Neon): use Neon's point-in-time restore / branching. Verify the free
  tier's retention window meets your needs; take a periodic `pg_dump` if you want
  an off-Neon copy.
- Files (R2): object storage is durable; DOCX are regenerable from run JSON, so
  they're not critical to back up.
- Config: keep `/opt/tailrd/.env` backed up securely (it holds secrets); it is the
  only non-reproducible state on the VM.

Dependency audit (2026-07): `pip-audit` (API) and `npm audit` (web) both report
zero known vulnerabilities. Re-run before each release:
`pip-audit -r apps/api/requirements.txt` and `npm audit` in `apps/web`.
