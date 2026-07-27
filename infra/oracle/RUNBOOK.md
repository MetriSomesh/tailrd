# Deploying Tailrd on Oracle Cloud "Always Free"

A $0/month, always-on deployment: Oracle Arm A1 VM (API + worker + Redis + optional
headless-browser scrape) → Neon (Postgres) → Cloudflare R2 (files) → OpenCode Zen
(free LLM). Frontend stays on Vercel.

## 0. Free services to create first
- **Oracle Cloud** account (credit card required for signup; Always Free is never charged).
- **Neon** — a Postgres project → copy the `psycopg` connection string.
- **Cloudflare R2** — a bucket + an S3 API token (Access Key ID / Secret) + your account's R2 endpoint.
- **OpenCode Zen** key — https://opencode.ai/auth (free models cost $0).
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

## 6. Migrate the database (Postgres/Neon uses Alembic)
```bash
cd /opt/tailrd/apps/api && sudo -u tailrd $VENV/bin/alembic upgrade head
```

## 7. TLS + start
```bash
sudo nano /etc/caddy/Caddyfile     # replace YOUR_DOMAIN with api.yourdomain.com (copy infra/Caddyfile)
sudo cp /opt/tailrd/infra/Caddyfile /etc/caddy/Caddyfile   # then edit the domain
sudo systemctl enable --now tailrd-api caddy
curl -s http://127.0.0.1:8000/ready    # expect {"status":"ready",...}
```
Point your DNS `A` record for `api.yourdomain.com` at the VM's public IP; Caddy auto-issues TLS.

## 8. Redeploys
```bash
cd /opt/tailrd && sudo -u tailrd git pull --ff-only
sudo -u tailrd $VENV/bin/pip install -r apps/api/requirements.txt
cd apps/api && sudo -u tailrd $VENV/bin/alembic upgrade head
sudo systemctl restart tailrd-api && curl -s http://127.0.0.1:8000/ready
```

## Notes
- **Cost:** VM is Always Free; Neon/R2/Zen free tiers cover low volume. Watch Neon compute-hours
  and R2 storage if usage grows.
- **Scrape fallback:** with `JD_SCRAPE_BROWSER_FALLBACK=true`, JS-only SPA postings render via
  Chromium (one at a time — worker concurrency is 1). HTTP-first keeps most scrapes browser-free.
- **Frontend:** set the Vercel project's API base to `https://api.yourdomain.com` and keep the
  same-origin `/api/backend` rewrite pointing there.
