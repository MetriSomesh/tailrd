#!/bin/bash
# First-time provisioning for Tailrd on an Oracle Cloud "Always Free" VM.
#
# Target: Ubuntu 22.04/24.04 on an Ampere A1 (Arm64) Always Free instance
#         (2 OCPU / 12 GB after Jun 2026 — plenty for the API, worker, Redis,
#          and an occasional headless-browser scrape).
#
# Run as root on a fresh instance:  sudo bash provision-oracle.sh
#
# It installs system packages (Python, Redis, Caddy, Git + Chromium OS libs),
# creates the service user, venv, swap, firewall rules, and systemd units.
# It does NOT clone the repo or install Python deps — see RUNBOOK.md for those.

set -euo pipefail
echo "=== Tailrd Oracle provisioning (Ubuntu/Arm) ==="

export DEBIAN_FRONTEND=noninteractive

# 1. System packages
echo "Installing system packages..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip redis-server git curl ca-certificates debian-keyring debian-archive-keyring apt-transport-https

# Caddy (official apt repo)
if ! command -v caddy &>/dev/null; then
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    apt-get update -y
    apt-get install -y caddy
fi

# 2. Service user
if ! id tailrd &>/dev/null; then
    useradd --system --create-home --home-dir /opt/tailrd --shell /usr/sbin/nologin tailrd
    echo "Created user: tailrd"
fi

# 3. Directory layout
# The repo is cloned at $APP_DIR (see RUNBOOK step 3), so the API lives at
# $APP_DIR/apps/api. venv + writable dirs live there; no symlink needed.
APP_DIR="/opt/tailrd"
API_DIR="$APP_DIR/apps/api"
mkdir -p "$API_DIR"/{_storage,_agent_workspaces,.cache} "$APP_DIR/ms-playwright"
chown -R tailrd:tailrd "$APP_DIR"

# 4. Python venv
echo "Creating venv..."
sudo -u tailrd python3 -m venv "$API_DIR/.venv"

# 5. Swap (optional on 12 GB, kept small as insurance)
if [ ! -f /swapfile ]; then
    echo "Creating 2G swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    echo "vm.swappiness=10" >> /etc/sysctl.conf
    sysctl -q vm.swappiness=10
fi

# 6. Firewall — Oracle images ship restrictive iptables. Open HTTP/HTTPS.
# (You must ALSO open 80/443 ingress in the VCN Security List — see RUNBOOK.)
echo "Opening ports 80/443 in iptables..."
iptables -I INPUT 5 -p tcp --dport 80 -j ACCEPT || true
iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT || true
if command -v netfilter-persistent &>/dev/null; then
    netfilter-persistent save || true
else
    apt-get install -y iptables-persistent || true
    netfilter-persistent save || true
fi

# 7. systemd units (API + the LLM stack: opencode serve + zen_proxy)
echo "Installing systemd units..."
cp "$APP_DIR/infra/oracle/tailrd-api.service" /etc/systemd/system/tailrd-api.service
cp "$APP_DIR/infra/oracle/tailrd-opencode.service" /etc/systemd/system/tailrd-opencode.service
cp "$APP_DIR/infra/oracle/tailrd-zenproxy.service" /etc/systemd/system/tailrd-zenproxy.service
systemctl daemon-reload
systemctl enable redis-server caddy
systemctl start redis-server

echo ""
echo "=== System provisioning complete ==="
echo "Next (see infra/oracle/RUNBOOK.md):"
echo "  1. Repo already cloned at $APP_DIR (code at $API_DIR)."
echo "  2. cp infra/oracle/.env.production.example /opt/tailrd/.env  &&  edit it"
echo "  3. $API_DIR/.venv/bin/pip install -r $API_DIR/requirements.txt"
echo "  4. (browser fallback) pip install -r requirements-scraper.txt"
echo "     sudo $API_DIR/.venv/bin/playwright install-deps chromium"
echo "     sudo -u tailrd PLAYWRIGHT_BROWSERS_PATH=$APP_DIR/ms-playwright $API_DIR/.venv/bin/playwright install chromium"
echo "  5. Install the OpenCode CLI + 'opencode auth login' (RUNBOOK 5b)"
echo "  6. Edit /etc/caddy/Caddyfile (your domain) ; systemctl enable --now tailrd-opencode tailrd-zenproxy tailrd-api caddy"
echo "  7. curl http://127.0.0.1:8000/ready"
