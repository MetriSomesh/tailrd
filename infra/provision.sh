#!/bin/bash
# First-time EC2 provisioning script.
# Run as root on a fresh Amazon Linux 2023 instance.
#
# Usage: sudo bash provision.sh
#
# This script:
# 1. Installs system packages (Python 3.11, Redis, Caddy, Git)
# 2. Creates the tailrd user
# 3. Sets up the project directory structure
# 4. Creates the Python venv
# 5. Sets up swap
# 6. Installs systemd units
# 7. Prints next steps

set -euo pipefail

echo "=== Tailrd EC2 Provisioning ==="

# 1. System packages
echo "Installing system packages..."
dnf install -y python3.11 python3.11-pip redis6 git

# Install Caddy
dnf install -y 'dnf-command(copr)'
dnf copr enable -y @caddy/caddy epel-9-$(uname -m)
dnf install -y caddy

# 2. Create service user
if ! id tailrd &>/dev/null; then
    useradd --system --shell /sbin/nologin --home /opt/tailrd tailrd
    echo "Created user: tailrd"
fi

# 3. Project directory
APP_DIR="/opt/tailrd"
mkdir -p "$APP_DIR"/{api/_storage,api/_agent_workspaces,infra}
chown -R tailrd:tailrd "$APP_DIR"

# 4. Python venv
echo "Creating Python venv..."
sudo -u tailrd python3.11 -m venv "$APP_DIR/api/.venv"

# 5. Swap
echo "Setting up swap..."
bash "$(dirname "$0")/setup-swap.sh"

# 6. Install systemd units
echo "Installing systemd units..."
cp "$APP_DIR/infra/tailrd-api.service" /etc/systemd/system/
cp "$APP_DIR/infra/redis.service" /etc/systemd/system/tailrd-redis.service
systemctl daemon-reload
systemctl enable tailrd-redis tailrd-api caddy

# 7. Redis config
systemctl start tailrd-redis

# 8. Caddy
echo "Caddy installed. Edit /etc/caddy/Caddyfile with your domain, then:"
echo "  sudo systemctl start caddy"

echo ""
echo "=== Provisioning complete ==="
echo ""
echo "Next steps:"
echo "  1. Clone your repo:   sudo -u tailrd git clone <url> /opt/tailrd"
echo "  2. Create .env:       sudo cp /opt/tailrd/apps/api/.env.example /opt/tailrd/.env"
echo "     Edit .env with production values (ENVIRONMENT=production, DATABASE_URL, etc.)"
echo "  3. Install deps:      /opt/tailrd/api/.venv/bin/pip install -r /opt/tailrd/api/requirements.txt"
echo "  4. Set Caddy domain:  Edit /etc/caddy/Caddyfile, replace YOUR_DOMAIN"
echo "  5. Start services:    sudo systemctl start caddy tailrd-api"
echo "  6. Verify:            curl http://localhost:8000/health"
echo ""
echo "Memory budget:"
echo "  OS + kernel:   ~150 MB"
echo "  Caddy:         ~25 MB"
echo "  Redis (64MB):  ~80 MB"
echo "  API + worker:  ~180 MB"
echo "  Agent (peak):  ~400 MB transient"
echo "  Swap:          2 GB (swappiness=10)"
