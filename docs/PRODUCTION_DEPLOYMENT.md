# Production Deployment Guide

**Last Updated**: 2025-12-12

This guide provides a comprehensive production deployment procedure for Board of One, covering pre-deployment verification, deployment execution, post-deployment validation, and rollback procedures.

## Quick Reference

| Step | Action | Time |
|------|--------|------|
| 1 | Pre-deployment checklist | 5 min |
| 2 | Trigger deployment | 1 min |
| 3 | Build & push images | 2-3 min |
| 4 | Blue-green deployment | 5-8 min |
| 5 | Post-deployment validation | 2 min |
| **Total** | | **~15 min** |

## Related Documentation

- [PRODUCTION_DEPLOYMENT_QUICKSTART.md](./PRODUCTION_DEPLOYMENT_QUICKSTART.md) - First-time server setup
- [BLUE_GREEN_DEPLOYMENT.md](./BLUE_GREEN_DEPLOYMENT.md) - Blue-green deployment details
- [SYSTEM_SHUTDOWN.md](./SYSTEM_SHUTDOWN.md) - Graceful shutdown procedures
- [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) - Backup and recovery procedures
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) - Incident handling playbook
- [slo.md](./slo.md) - SLI/SLO definitions

---

## Prerequisites

### Infrastructure Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Server | Ubuntu 22.04 LTS | 4GB RAM minimum |
| Docker | 24.0+ | With Compose V2 |
| PostgreSQL | 16 (pgvector) | Via docker-compose.infrastructure.yml |
| Redis | 7.4+ (Stack) | AOF + RDB persistence |
| Nginx | Host-level | For blue-green traffic switching |

### Required Environment Variables

Production `.env` must contain:

```bash
# Core
ENV=production
SITE_URL=https://boardof.one
CORS_ORIGINS=https://boardof.one

# Security (MANDATORY)
COOKIE_SECURE=true                    # Enforced at startup
COOKIE_DOMAIN=.boardof.one
SUPERTOKENS_API_KEY=<32+_char_key>

# Database
POSTGRES_PASSWORD=<strong_password>
DATABASE_URL=postgresql://bo1:<password>@postgres:5432/boardofone

# Redis
REDIS_PASSWORD=<strong_password>

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
ADMIN_API_KEY=<strong_key>

# Optional: Encryption for backups
BACKUP_AGE_RECIPIENT=age1...         # Public key for backup encryption
```

### GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `PRODUCTION_HOST` | Yes | Server IP or hostname |
| `PRODUCTION_USER` | Yes | SSH user (typically `deploy`) |
| `PRODUCTION_SSH_KEY` | Yes | Private SSH key (entire file) |
| `PRODUCTION_SSH_PORT` | No | Default: 22 |
| `COOKIE_SECURE` | Yes | Must be `true` |
| `NTFY_TOPIC` | No | For deployment notifications |

---

## Pre-Deployment Checklist

Run these checks before every production deployment:

### 1. Code Quality

```bash
# Run locally before pushing
make pre-commit            # Lint, format, type check
make test                  # Run test suite
```

### 2. Security Audits

```bash
# Dependency vulnerabilities
make audit-deps            # pip-audit + npm audit
make osv-scan              # OSV vulnerability scanner

# Check for no HIGH/CRITICAL vulnerabilities
```

### 3. Migration Safety

```bash
# Verify migrations are backward-compatible
uv run alembic history --verbose | head -20

# Test migration on staging first
# Migrations must NOT drop columns (breaks blue during green deploy)
```

### 4. Feature Flags

For breaking changes:
- Enable feature flag in `backend/services/feature_flags.py`
- Verify flag is OFF by default
- Plan rollout after deployment succeeds

### 5. Environment Verification

```bash
# Verify production .env (SSH to server)
ssh deploy@boardof.one
grep -E "^(ENV|COOKIE_SECURE|COOKIE_DOMAIN)=" /opt/boardofone/.env

# Expected:
# ENV=production
# COOKIE_SECURE=true
# COOKIE_DOMAIN=.boardof.one
```

### 6. Backup Verification

```bash
# Verify recent backup exists
make verify-backup BACKUP_FILE=./backups/postgres/latest.sql.gz.age

# Or check DO Spaces
aws s3 ls s3://bo1-backups/postgres/ --endpoint-url https://nyc3.digitaloceanspaces.com
```

---

## Deployment Process

### Method 1: GitHub Actions (Recommended)

1. **Navigate to Actions**
   - Go to: `https://github.com/<org>/bo1/actions`
   - Select **"Deploy to Production"** workflow

2. **Trigger Deployment**
   - Click **"Run workflow"**
   - Type `deploy-to-production` to confirm
   - Click **"Run workflow"** (green button)

3. **Monitor Progress**

   The workflow executes:
   | Step | Duration | Description |
   |------|----------|-------------|
   | validate-confirmation | 10s | Verify typed confirmation |
   | security-scan | 2m | Bandit + Safety scans |
   | pre-deployment-checks | 1m | Verify secrets, staging health |
   | build-and-push | 3m | Build Docker images, push to GHCR |
   | deploy-to-production | 8m | Blue-green deployment |
   | create-release | 30s | Tag release in GitHub |
   | notify | 10s | ntfy.sh notification |

4. **Verify Deployment**
   - Check workflow logs for ✅ on all steps
   - Verify release tag created in Releases

### Method 2: Manual Deployment (Emergency Only)

```bash
# SSH to production server
ssh deploy@boardof.one
cd /opt/boardofone

# Pull latest code
git pull origin main

# Build and deploy
API_PORT=8001 FRONTEND_PORT=3001 docker-compose -f docker-compose.app.yml -p boardofone-green up -d --build

# Wait for health
for i in {1..15}; do
  curl --fail --silent http://localhost:8001/api/health && break
  sleep 3
done

# Run migrations
docker-compose -f docker-compose.app.yml -p boardofone-green exec -T api uv run alembic upgrade head

# Switch nginx
sudo cp /opt/boardofone/nginx/nginx-green.conf /etc/nginx/sites-available/boardofone
sudo nginx -t && sudo systemctl reload nginx

# Stop old environment
docker-compose -f docker-compose.app.yml -p boardofone stop
```

---

## Post-Deployment Verification

### Automated Checks (via workflow)

The deploy-production.yml workflow automatically validates:
- `/api/health` - API liveness
- `/api/health/db` - Database connectivity
- `/api/health/redis` - Redis connectivity
- Landing page HTTP status
- Login page HTTP status

### Manual Smoke Tests

```bash
# Health endpoints
curl https://boardof.one/api/health
curl https://boardof.one/api/ready

# Auth flow (manual browser test)
# 1. Navigate to https://boardof.one/login
# 2. Click Google login
# 3. Verify redirect to dashboard

# Create test session (if applicable)
# Verify SSE streaming works
```

### Monitoring Verification

1. **Grafana Dashboards**
   - Check API dashboard for normal latency
   - Check error rate < 0.5%
   - Check session completion rate

2. **Prometheus Alerts**
   - Verify no firing alerts
   - Check `bo1_rate_limiter_degraded` = 0

3. **Loki Logs**
   - Search for `level="error"` in last 5 minutes
   - Should be minimal/none

---

## Rollback Procedure

### When to Rollback

- SLO breach (availability < 99%, error rate > 5%)
- Critical bug in production
- Failed health checks after deployment
- Database migration failure

### Automatic Rollback (via workflow)

If deploy-production.yml detects:
- Health check failures
- High error rate (>5 errors in 100 log lines)
- Nginx config test failure

It automatically:
1. Keeps original (blue) environment running
2. Stops new (green) environment
3. Sends failure notification via ntfy.sh

### Manual Rollback

```bash
# SSH to production
ssh deploy@boardof.one
cd /opt/boardofone

# Identify current environment
docker ps | grep boardofone

# If green is active, switch back to blue
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-available/boardofone
sudo nginx -t && sudo systemctl reload nginx

# Restart blue if stopped
docker-compose -f docker-compose.app.yml -p boardofone up -d

# Stop green
docker-compose -f docker-compose.app.yml -p boardofone-green down
```

**Recovery time**: ~30 seconds

### Database Migration Rollback

If a migration needs to be rolled back:

```bash
# SSH to production
ssh deploy@boardof.one
cd /opt/boardofone

# Check current version
docker-compose -f docker-compose.app.yml -p boardofone exec -T api uv run alembic current

# Downgrade one revision
docker-compose -f docker-compose.app.yml -p boardofone exec -T api uv run alembic downgrade -1

# Verify
docker-compose -f docker-compose.app.yml -p boardofone exec -T api uv run alembic current
```

**Important**: Only roll back if migration is backward-compatible. For data-destructive migrations, restore from backup instead.

---

## Database Migration Rollback (from backup)

For severe data corruption or destructive migration failures:

```bash
# 1. Stop application
docker-compose -f docker-compose.app.yml down

# 2. Download backup from DO Spaces
aws s3 cp s3://bo1-backups/postgres/latest.sql.gz.age ./backups/postgres/ \
    --endpoint-url https://nyc3.digitaloceanspaces.com

# 3. Set decryption key (retrieve from secure storage)
export BACKUP_AGE_KEY_FILE=/path/to/secure/backup.key

# 4. Restore
./scripts/restore_postgres.sh ./backups/postgres/latest.sql.gz.age --force

# 5. Run migrations to current
docker-compose -f docker-compose.app.yml -p boardofone exec -T api uv run alembic upgrade head

# 6. Restart application
docker-compose -f docker-compose.app.yml up -d
```

See [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) for full recovery procedures.

---

## Emergency Procedures

### Complete Service Outage

1. **Immediate**: Check server reachability
   ```bash
   ping boardof.one
   ssh deploy@boardof.one
   ```

2. **Check Docker status**
   ```bash
   docker ps
   docker-compose -f docker-compose.infrastructure.yml -p infrastructure ps
   ```

3. **Restart all services**
   ```bash
   docker-compose -f docker-compose.infrastructure.yml -p infrastructure up -d
   docker-compose -f docker-compose.app.yml up -d
   ```

See [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) for detailed procedures.

### Vendor Outage (Anthropic)

1. Application has automatic circuit breaker fallback
2. Check `/api/v1/status` for vendor health
3. If prolonged, users see degraded mode banner automatically
4. No manual action required unless fallback fails

---

## Deployment Security Checklist

Before any production deployment:

| Check | Verified |
|-------|----------|
| `COOKIE_SECURE=true` in server .env | ☐ |
| `ENV=production` in server .env | ☐ |
| No HIGH/CRITICAL vulnerabilities in audit | ☐ |
| Recent backup exists (< 24h) | ☐ |
| Migrations are backward-compatible | ☐ |
| Feature flags configured for breaking changes | ☐ |
| GitHub secrets up to date | ☐ |

---

## Appendix: Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/api/health` | Liveness probe | `{"status": "healthy"}` |
| `/api/ready` | Readiness probe | `{"status": "ready", "postgres": "up", "redis": "up"}` |
| `/api/health/db` | Database connectivity | `{"status": "healthy"}` |
| `/api/health/redis` | Redis connectivity | `{"status": "healthy"}` |
| `/api/v1/status` | Vendor health status | JSON with all service states |

---

## Appendix: Key Commands Reference

```bash
# GitHub Actions deployment
# (Go to Actions tab → Deploy to Production → Run workflow)

# SSH to server
ssh deploy@boardof.one

# View running containers
docker ps

# View logs
docker-compose -f /opt/boardofone/docker-compose.app.yml -p boardofone logs -f --tail=50

# Check which environment is active
ls -la /etc/nginx/sites-available/boardofone

# Manual nginx switch to blue
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-available/boardofone
sudo nginx -t && sudo systemctl reload nginx

# Manual nginx switch to green
sudo cp /opt/boardofone/nginx/nginx-green.conf /etc/nginx/sites-available/boardofone
sudo nginx -t && sudo systemctl reload nginx

# Backup database
./scripts/backup_postgres.sh --upload

# Verify backup
./scripts/verify_backup.sh backups/postgres/latest.sql.gz.age
```
