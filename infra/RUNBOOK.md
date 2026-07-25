# Tailrd Operations Runbook

## Architecture Summary

```
Vercel (Mumbai bom1) → HTTPS → EC2 t3.micro (1 GB RAM, Amazon Linux 2023)
                                  ├── Caddy (TLS + reverse proxy)
                                  ├── tailrd-api (FastAPI + in-process worker)
                                  ├── Redis (64 MB, job queue + locks)
                                  └── OpenCode (transient subprocess, per job)
                                        │
                         ┌──────────────┼──────────────┐
                         ▼              ▼              ▼
                  Neon Postgres     AWS S3       Razorpay / Resend
```

## Service Commands

```bash
# Status
sudo systemctl status tailrd-api tailrd-redis caddy

# Logs
sudo journalctl -u tailrd-api -f --no-pager
sudo journalctl -u tailrd-api --since "10 min ago"

# Restart (graceful)
sudo systemctl restart tailrd-api

# Stop (emergency)
sudo systemctl stop tailrd-api
```

## Health Checks

```bash
# Liveness (is the process alive?)
curl http://127.0.0.1:8000/health

# Readiness (can it serve traffic?)
curl http://127.0.0.1:8000/ready | python3 -m json.tool
```

## Memory Monitoring

```bash
# Current memory breakdown
ps aux --sort=-%mem | head -10
free -h
swapon --show

# If swapping heavily
journalctl -u tailrd-api | grep -i "memory\|oom\|kill"
```

## Common Issues

### API won't start
```bash
# Check config validation
cd /opt/tailrd/api
.venv/bin/python -c "from app.core.config import Settings; s=Settings(); print(s.validate_for_runtime())"
```

### Agent jobs stuck
```bash
# Check the agent lock in Redis
redis-cli GET tailrd:agent:lock
# Force release (only if the process holding it is dead)
redis-cli DEL tailrd:agent:lock

# Check circuit breaker state
curl http://127.0.0.1:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin))"
```

### Queue backed up
```bash
# Check queue length
redis-cli LLEN tailrd:jobs

# Peek at queued jobs (non-destructive)
redis-cli LRANGE tailrd:jobs 0 5
```

### High memory / OOM
```bash
# The API is capped at 450M via MemoryMax in systemd.
# If agent jobs push total over 1 GB, swap absorbs it.
# If you see frequent OOM kills:
#   Option 1: Increase instance size to t3.small (2 GB)
#   Option 2: Reduce agent timeout (currently 180s)
#   Option 3: Add more swap (currently 2 GB)

# Check OOM events
dmesg | grep -i "out of memory\|oom"
journalctl -k | grep -i oom
```

### Redis down
```bash
sudo systemctl restart tailrd-redis
# The API degrades gracefully: auth and reads work, tailor jobs reject with 503
```

### Caddy TLS renewal fails
```bash
sudo journalctl -u caddy | grep -i "tls\|cert\|renew"
# Usually means port 80/443 is blocked. Check security group.
```

## Deploy Process

```bash
# From your local machine:
ssh ec2-user@YOUR_HOST "bash /opt/tailrd/infra/deploy.sh"

# Or from the server directly:
sudo -u tailrd bash /opt/tailrd/infra/deploy.sh
```

The deploy script:
1. `git pull` (fast-forward only)
2. `pip install -r requirements.txt`
3. Validates config (aborts if invalid)
4. `systemctl restart tailrd-api`
5. Waits for /health to respond
6. Checks /ready

## Scaling Triggers

Move to a bigger instance when:
- p95 queue wait > 5 minutes
- Swap usage consistently > 500 MB
- > 800 resumes/day

Scale-out path (no code changes needed):
1. Separate worker to dedicated t3.small
2. Then: 2-3 workers behind same Redis queue
3. Then: ALB + ASG for the API
4. Neon → RDS with read replica

## Backup / Recovery

- **Database**: Neon provides PITR (point-in-time recovery)
- **S3**: Versioning enabled, lifecycle policy auto-deletes after 90 days
- **Config**: All in git. .env is the only non-versioned artifact.
- **Disaster recovery**: Fresh instance + provision.sh + deploy.sh + .env = running in 15 minutes

## Secrets Checklist (production .env)

```
ENVIRONMENT=production
SECRET_KEY=<64+ random chars>
COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg://...@....neon.tech/...?sslmode=require
REDIS_URL=redis://127.0.0.1:6379/0
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
STORAGE_BACKEND=s3
S3_BUCKET=tailrd-resumes
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
PAYMENT_PROVIDER=razorpay
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
AGENT_BACKEND=opencode
```
