#!/bin/bash
# Deploy script for Tailrd API on EC2.
# Pulls latest code, installs deps, runs migrations, restarts service.
#
# Usage: ssh ec2-user@your-host "bash /opt/tailrd/infra/deploy.sh"
# Or:    ./deploy.sh (if run from the server)
#
# Prerequisites:
#   - Git repo cloned to /opt/tailrd
#   - Python venv at /opt/tailrd/api/.venv
#   - .env at /opt/tailrd/.env
#   - systemd units installed
#   - Caddy installed and configured

set -euo pipefail

APP_DIR="/opt/tailrd"
API_DIR="$APP_DIR/api"
VENV="$API_DIR/.venv"
SERVICE="tailrd-api"

echo "=== Tailrd Deploy $(date -Iseconds) ==="

# 1. Pull latest code
cd "$APP_DIR"
echo "Pulling latest..."
git pull --ff-only origin main

# 2. Install/update Python dependencies
echo "Installing Python deps..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$API_DIR/requirements.txt"

# 3. Run database migrations (when using PostgreSQL + Alembic)
# echo "Running migrations..."
# cd "$API_DIR"
# "$VENV/bin/alembic" upgrade head

# 4. Validate config (fail fast if .env is misconfigured for production)
echo "Validating config..."
"$VENV/bin/python" -c "
from app.core.config import Settings
s = Settings()
problems = s.validate_for_runtime()
if problems:
    for p in problems:
        print(f'  ERROR: {p}')
    exit(1)
print('  Config OK')
" || { echo "Config validation FAILED. Aborting deploy."; exit 1; }

# 5. Restart the API service (graceful: SIGTERM → drain → new process)
echo "Restarting $SERVICE..."
sudo systemctl restart "$SERVICE"

# 6. Wait for health check
echo "Waiting for health..."
for i in {1..15}; do
    if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "  Healthy after ${i}s"
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "  FAILED: API did not become healthy in 15s"
        sudo journalctl -u "$SERVICE" --no-pager -n 30
        exit 1
    fi
    sleep 1
done

# 7. Verify readiness (includes DB + Redis checks)
READY=$(curl -sf http://127.0.0.1:8000/ready | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
if [ "$READY" != "ready" ]; then
    echo "  WARNING: Readiness check returned '$READY' (degraded mode possible)"
fi

echo "=== Deploy complete ==="
echo "  Service: $(sudo systemctl is-active $SERVICE)"
echo "  Health:  $(curl -sf http://127.0.0.1:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"status\"]} uptime={d[\"uptime_seconds\"]}s')")"
