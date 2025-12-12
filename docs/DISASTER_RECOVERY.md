# Disaster Recovery Runbook

## Overview

This runbook provides step-by-step procedures for recovering Board of One (bo1) infrastructure after various failure scenarios.

## Related Documentation

- [SYSTEM_SHUTDOWN.md](./SYSTEM_SHUTDOWN.md) - Graceful shutdown procedures
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) - Incident handling playbook
- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) - Deployment procedures

## Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| On-call Engineer | TODO: Add | Primary |
| Engineering Lead | TODO: Add | 15min no response |
| Platform Lead | TODO: Add | Critical incidents |

### Vendor Support

- **DigitalOcean**: https://cloud.digitalocean.com/support
- **Anthropic**: support@anthropic.com
- **Supabase**: https://supabase.com/dashboard/support
- **Resend**: support@resend.com

## Backup Inventory

### PostgreSQL Database

| Item | Details |
|------|---------|
| Image | `pgvector/pgvector:0.8.1-pg16` |
| Volume | `postgres-data` |
| Database | `boardofone` |
| User | `bo1` |
| Backup Method | pg_dump with age encryption |
| Backup Location | DO Spaces bucket |
| Encryption | age (modern, audited) |
| Retention | Tiered: 7 daily, 30 weekly (Sunday), 90 monthly (1st) |
| RPO Target | 1 hour |
| RTO Target | 4 hours |

### Redis Cache

| Item | Details |
|------|---------|
| Image | `redis/redis-stack-server:7.4.0-v1` |
| Volume | `redis-data` |
| Persistence | AOF (appendonly) + RDB snapshots |
| RDB Schedule | Every 60s if 1000+ changes |
| Auth | Password protected |
| RPO Target | Acceptable loss (cache) |
| RTO Target | 30 minutes |

### DO Spaces Object Storage

| Item | Details |
|------|---------|
| Contents | User uploads, charts, exports |
| Bucket | TODO: Add bucket name |
| Region | TODO: Add region |
| Versioning | TODO: Enable |
| RPO Target | Near-zero (built-in replication) |
| RTO Target | Immediate (no recovery needed) |

### Application Configuration

| Item | Location |
|------|----------|
| Environment Variables | `.env` (not committed) |
| Docker Compose | `docker-compose.yml`, `docker-compose.infrastructure.yml` |
| Prometheus Config | `monitoring/prometheus.yml` |
| Grafana Dashboards | `monitoring/grafana/` |
| Secrets | GitHub Secrets, server `.env` |

## Backup Encryption

### Overview

Database backups are encrypted using [age](https://age-encryption.org/), a modern file encryption tool. This protects backups at rest against unauthorized access.

### Key Management

#### Generate Encryption Key

```bash
# Generate a new keypair
make generate-backup-key

# Keys are stored in:
#   backups/keys/backup.key  - Private key (keep SECURE)
#   backups/keys/backup.pub  - Public key (can be shared)
```

#### Key Storage Requirements

**CRITICAL**: Store the private key separately from backups.

| Environment | Private Key Storage | Public Key Storage |
|-------------|--------------------|--------------------|
| Development | `backups/keys/backup.key` (gitignored) | Environment variable |
| Production | Password manager / HSM / Secrets Manager | GitHub Secrets |

**Never**:
- Store private key in same location as backups
- Commit private key to git
- Store private key in DO Spaces with backups

**Always**:
- Keep at least 2 copies of private key in separate locations
- Test restoration with the key monthly
- Rotate keys annually (keep old key for archive access)

### Create Encrypted Backup

```bash
# Set encryption public key
export BACKUP_AGE_RECIPIENT="age1..."  # from backups/keys/backup.pub

# Create encrypted backup
make backup-db-encrypted

# Or use script directly for automated backups
BACKUP_AGE_RECIPIENT="age1..." ./scripts/backup_postgres.sh --upload
```

Output format depends on backup tier:
- Daily (Mon-Sat, not 1st): `boardofone-YYYYMMDD-HHMMSS.sql.gz.age`
- Weekly (Sunday, not 1st): `boardofone-YYYYMMDD-HHMMSS-weekly.sql.gz.age`
- Monthly (1st of month): `boardofone-YYYYMMDD-HHMMSS-monthly.sql.gz.age`

### Backup Retention Tiers

| Tier | Schedule | Retention | Filename Pattern |
|------|----------|-----------|------------------|
| Daily | Mon-Sat (not 1st) | 7 days | `dbname-YYYYMMDD-HHMMSS.sql.gz*` |
| Weekly | Sunday (not 1st) | 30 days | `dbname-YYYYMMDD-HHMMSS-weekly.sql.gz*` |
| Monthly | 1st of month | 90 days | `dbname-YYYYMMDD-HHMMSS-monthly.sql.gz*` |

Configure retention via environment variables:
```bash
BACKUP_RETENTION_DAILY=7    # Days to keep daily backups
BACKUP_RETENTION_WEEKLY=30  # Days to keep weekly backups
BACKUP_RETENTION_MONTHLY=90 # Days to keep monthly backups
```

### Restore Encrypted Backup

```bash
# Set decryption key path
export BACKUP_AGE_KEY_FILE=./backups/keys/backup.key

# Restore
./scripts/restore_postgres.sh backups/postgres/boardofone-20241212-120000.sql.gz.age

# Or verify without restore
./scripts/verify_backup.sh backups/postgres/boardofone-20241212-120000.sql.gz.age
```

### Unencrypted Backups (Backward Compatible)

If no encryption key is configured, scripts produce unencrypted `.sql.gz` files:

```bash
# No encryption key set - produces unencrypted backup
./scripts/backup_postgres.sh
# Output: boardofone-YYYYMMDD-HHMMSS.sql.gz

# Restore unencrypted backup (no key needed)
./scripts/restore_postgres.sh backups/postgres/boardofone-20241212-120000.sql.gz
```

### GPG Alternative

For environments with existing GPG infrastructure:

```bash
# Encrypt with GPG
export BACKUP_GPG_RECIPIENT="your-key-id"
./scripts/backup_postgres.sh
# Output: boardofone-YYYYMMDD-HHMMSS.sql.gz.gpg

# Restore (uses default GPG keyring)
./scripts/restore_postgres.sh backups/postgres/boardofone-20241212-120000.sql.gz.gpg
```

### Key Loss Recovery

If the decryption key is lost:
1. Backups encrypted with that key are **unrecoverable**
2. Generate new key: `make generate-backup-key`
3. Create new encrypted backup immediately
4. Update key escrow locations
5. Document incident per security policy

---

## Recovery Procedures

### Scenario 1: Database Recovery (Full)

**Symptoms**: Database corruption, complete data loss, failed upgrade

**Prerequisites**:
- Access to backup storage
- PostgreSQL client tools
- Sufficient disk space (2x database size)

**Procedure**:

```bash
# 1. Stop application services
docker compose stop api bo1 frontend

# 2. Stop database
docker compose stop postgres

# 3. Remove corrupted volume (DESTRUCTIVE)
docker volume rm bo1_postgres-data

# 4. Recreate container with fresh volume
docker compose up -d postgres

# 5. Wait for healthy status
docker compose exec postgres pg_isready -U bo1 -d boardofone

# 6. Restore from backup
# Download backup from DO Spaces
aws s3 cp s3://bo1-backups/postgres/latest.sql.gz.age ./backups/postgres/ \
    --endpoint-url https://nyc3.digitaloceanspaces.com

# Set decryption key (retrieve from secure storage)
export BACKUP_AGE_KEY_FILE=/path/to/secure/backup.key

# Restore encrypted backup
./scripts/restore_postgres.sh ./backups/postgres/latest.sql.gz.age --force

# Or for unencrypted backups:
# ./scripts/restore_postgres.sh ./backups/postgres/latest.sql.gz --force

# 7. Run migrations to ensure schema is current
docker compose exec api uv run alembic upgrade head

# 8. Verify data integrity
docker compose exec postgres psql -U bo1 boardofone -c "SELECT count(*) FROM users;"

# 9. Restart application services
docker compose up -d api bo1 frontend

# 10. Verify application health
curl http://localhost:8000/api/ready
```

**Rollback**: If restoration fails, escalate to Platform Lead.

### Scenario 2: Database Recovery (Point-in-Time)

**Symptoms**: Accidental data deletion, need to recover specific timepoint

**Procedure**:

```bash
# 1. Identify target recovery time
# Review logs for incident time

# 2. List available backups (local)
ls -la backups/postgres/

# List remote backups (DO Spaces)
aws s3 ls s3://bo1-backups/backups/postgres/ \
    --endpoint-url https://nyc3.digitaloceanspaces.com

# Available backup tiers:
#   - Daily backups: last 7 days
#   - Weekly backups (-weekly suffix): last 30 days (Sundays)
#   - Monthly backups (-monthly suffix): last 90 days (1st of month)

# 3. Download specific backup from remote if needed
aws s3 cp s3://bo1-backups/backups/postgres/boardofone-20241201-000000-monthly.sql.gz.age \
    ./backups/postgres/ --endpoint-url https://nyc3.digitaloceanspaces.com

# 4. Create recovery database
docker compose exec postgres createdb -U bo1 boardofone_recovery

# 5. Restore to recovery database (modify restore script target)
POSTGRES_DB=boardofone_recovery ./scripts/restore_postgres.sh \
    ./backups/postgres/boardofone-20241201-000000-monthly.sql.gz.age

# 6. Verify recovery data
docker compose exec postgres psql -U bo1 boardofone_recovery -c "SELECT count(*) FROM users;"

# 7. Extract needed data or swap databases
# Option A: Copy specific tables
# Option B: Rename databases (requires maintenance window)
```

### Scenario 3: Database Recovery (Single Table)

**Symptoms**: Need to restore specific table without full restore

**Procedure**:

```bash
# 1. Extract table from backup
# pg_restore -t tablename backup.dump > table_data.sql

# 2. Review data before import
# less table_data.sql

# 3. Import to temporary table
# docker compose exec postgres psql -U bo1 boardofone -c "..."

# 4. Verify and merge data
```

### Scenario 4: Redis Recovery

**Symptoms**: Redis data loss, corruption, OOM

**Procedure**:

```bash
# 1. Check Redis status
docker compose exec redis redis-cli -a $REDIS_PASSWORD INFO persistence

# 2. Stop Redis
docker compose stop redis

# 3. Option A: Recover from RDB snapshot
# RDB file is at /data/dump.rdb in container
# Copy backup RDB file to volume

# 4. Option B: Recover from AOF
# AOF file is at /data/appendonly.aof
# redis-check-aof --fix /data/appendonly.aof

# 5. Restart Redis
docker compose up -d redis

# 6. Verify Redis health
docker compose exec redis redis-cli -a $REDIS_PASSWORD PING

# 7. Application may need session re-establishment
# LangGraph state will be rebuilt from database if needed
```

**Note**: Redis primarily stores cache and session data. Most state can be rebuilt from PostgreSQL. User sessions will be invalidated requiring re-login.

### Scenario 5: Application Rollback

**Symptoms**: Bad deployment, application bugs, performance regression

**Procedure**:

```bash
# 1. Identify last known good version
git log --oneline -10

# 2. For blue-green deployment, switch traffic
# See docs/BLUE_GREEN_DEPLOYMENT.md

# 3. For immediate rollback without blue-green:

# Stop current services
docker compose down api frontend bo1

# Checkout previous version
git checkout <previous-commit>

# Rebuild and deploy
docker compose build api frontend bo1
docker compose up -d api frontend bo1

# 4. Verify health
curl http://localhost:8000/api/ready
curl http://localhost:5173/

# 5. Run smoke tests
# pytest tests/smoke/ -v
```

### Scenario 6: Complete Environment Rebuild

**Symptoms**: Catastrophic failure, server loss, need clean slate

**Prerequisites**:
- Fresh server with Docker installed
- Access to Git repository
- Access to backup storage
- All secrets and API keys

**Procedure**:

```bash
# 1. Clone repository
git clone https://github.com/your-org/bo1.git
cd bo1

# 2. Create .env file with all secrets
cat > .env << 'EOF'
POSTGRES_PASSWORD=<secure-password>
REDIS_PASSWORD=<secure-password>
SUPERTOKENS_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
ADMIN_API_KEY=<key>
ENCRYPTION_KEY=<key>
# Add all other required variables
EOF

# 3. Start infrastructure
docker compose -f docker-compose.infrastructure.yml up -d

# 4. Wait for services to be healthy
docker compose -f docker-compose.infrastructure.yml ps

# 5. Restore database from backup
# See Scenario 1 steps 4-8

# 6. Start application services
docker compose up -d

# 7. Run migrations
docker compose exec api uv run alembic upgrade head

# 8. Verify all services
curl http://localhost:8000/api/ready
curl http://localhost:5173/

# 9. Restore monitoring
# Grafana dashboards are in Git, just restart
docker compose --profile monitoring up -d

# 10. Verify external integrations
# - Test Anthropic API connectivity
# - Test email sending (Resend)
# - Test SuperTokens auth flow
```

### Scenario 7: Vendor Outage (Anthropic)

**Symptoms**: LLM calls failing, timeouts, rate limits

**Procedure**:

1. Check Anthropic status: https://status.anthropic.com
2. Application has automatic fallback via circuit breaker
3. Monitor `/api/v1/status` endpoint for vendor health
4. If extended outage:
   - Enable degraded mode notification banner (automatic via ServiceStatusBanner)
   - Consider OpenAI fallback if configured
5. Communicate to users via banner/email

### Scenario 8: Vendor Outage (DigitalOcean)

**Symptoms**: Server unreachable, storage unavailable

**Procedure**:

1. Check DO status: https://status.digitalocean.com
2. If regional outage, consider failover to different region (requires pre-configured infrastructure)
3. For Spaces outage: uploads will fail but existing data remains
4. Monitor and wait for DO resolution
5. After resolution, verify all volumes mounted correctly

## Verification Procedures

### Monthly Backup Restore Test

```bash
# 1. Download latest backup to test environment
# 2. Restore to isolated test database
# 3. Run data integrity checks:
docker compose exec postgres psql -U bo1 boardofone_test << 'EOF'
-- Check table counts
SELECT 'users' as table_name, count(*) from users
UNION ALL
SELECT 'sessions', count(*) from sessions
UNION ALL
SELECT 'actions', count(*) from actions;

-- Check for orphaned records
SELECT count(*) FROM sessions WHERE user_id NOT IN (SELECT id FROM users);

-- Check recent data exists
SELECT max(created_at) FROM sessions;
EOF

# 4. Document results in incident log
```

### Quarterly DR Drill

1. Schedule maintenance window (2 hours)
2. Notify users in advance
3. Execute full recovery scenario on staging
4. Document time to recovery
5. Review and update this runbook
6. Update RTO/RPO targets if needed

## Automated Monitoring

### Backup Health Alerts

- TODO: Configure alert for backup job failures
- TODO: Configure alert for backup age > 24h
- TODO: Configure alert for backup size anomalies

### Recovery Readiness

| Check | Frequency | Owner |
|-------|-----------|-------|
| Backup exists | Daily (automated) | Monitoring |
| Backup restorable | Monthly (manual) | On-call |
| Full DR drill | Quarterly | Platform Lead |
| Runbook review | Quarterly | Team |

## Communication Templates

### Outage Notification (Internal)

```
Subject: [INCIDENT] Bo1 Service Disruption

Status: INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED
Impact: [Description of user impact]
Start Time: [UTC timestamp]
Current Actions: [What we're doing]
Next Update: [Time]
```

### Outage Notification (External)

```
We're currently experiencing issues with [service area].

What's happening: [Brief description]
What we're doing: [Recovery actions]
Expected resolution: [Time estimate or "investigating"]

We'll update this page as we learn more.
```

## Deployment Security Checklist

Before any production deployment, verify the following security configurations:

### Required Environment Variables

| Variable | Required Value | Purpose |
|----------|---------------|---------|
| `ENV` | `production` | Enables production security checks |
| `COOKIE_SECURE` | `true` | Forces HTTPS-only session cookies |
| `COOKIE_DOMAIN` | `.boardof.one` | Restricts cookies to production domain |

### Pre-Deployment Verification

```bash
# On production server, verify .env contains:
grep -E "^(ENV|COOKIE_SECURE|COOKIE_DOMAIN)=" /opt/boardofone/.env

# Expected output:
# ENV=production
# COOKIE_SECURE=true
# COOKIE_DOMAIN=.boardof.one
```

### Startup Validation

The API performs automatic security validation on startup:
- **COOKIE_SECURE check**: If `ENV=production` and `COOKIE_SECURE!=true`, startup fails
- **Audit logging**: Cookie configuration is logged for audit trail

If deployment fails with "COOKIE_SECURE must be true in production", check:
1. `.env` file on server has `COOKIE_SECURE=true`
2. GitHub secrets include `COOKIE_SECURE=true`
3. Docker container receives the environment variable

### Post-Deployment Verification

```bash
# Verify cookies are set with Secure flag
curl -I https://boardof.one/api/auth/session/refresh 2>&1 | grep -i "set-cookie"
# Should show: Secure; HttpOnly; SameSite=Lax
```

---

## Appendix: Key Commands Reference

```bash
# Check all service health
docker compose ps
docker compose -f docker-compose.infrastructure.yml ps

# View logs
docker compose logs -f api
docker compose logs --tail=100 postgres

# Database access
docker compose exec postgres psql -U bo1 boardofone

# Redis access
docker compose exec redis redis-cli -a $REDIS_PASSWORD

# Application health
curl http://localhost:8000/api/health  # Liveness
curl http://localhost:8000/api/ready   # Readiness

# Force container restart
docker compose restart api

# Rebuild and restart
docker compose up -d --build api
```

---

**Last Updated**: 2025-12-12
**Next Review**: 2025-03-12
**Owner**: Platform Team
