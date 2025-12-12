# System Shutdown Procedure

**Last Updated**: 2025-12-12

This document provides procedures for safely shutting down the Board of One platform for planned maintenance, emergency situations, and restart operations.

## Related Documentation

- [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) - Backup and restore procedures
- [INCIDENT_RESPONSE.md](./INCIDENT_RESPONSE.md) - Emergency response playbook
- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) - Deployment and restart validation

---

## Pre-Shutdown Checklist

Before initiating shutdown:

| Step | Action | Command/Location |
|------|--------|------------------|
| 1 | Announce maintenance window | Email users, status page |
| 2 | Check active sessions | `curl -H "Authorization: Bearer $ADMIN_API_KEY" http://localhost:8000/api/admin/sessions` |
| 3 | Verify recent backup exists | `make backup-db` or check DO Spaces |
| 4 | Confirm rollback plan | Review [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) |
| 5 | Notify on-call engineer | Per escalation contacts |

### Check Active Sessions

```bash
# Count active sessions
curl -s -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/api/admin/sessions | jq '.count'

# List sessions with status
curl -s -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/api/admin/sessions | jq '.sessions[] | {id, status, started_at}'
```

---

## Graceful Shutdown Sequence

Use this procedure for planned maintenance.

### Step 1: Enable Maintenance Mode

```bash
# Option A: Nginx 503 maintenance page
sudo cp /etc/nginx/maintenance.html /var/www/html/
sudo sed -i 's/# return 503/return 503/' /etc/nginx/sites-enabled/boardofone
sudo nginx -s reload

# Option B: Feature flag (if implemented)
curl -X POST -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/api/admin/features/maintenance_mode \
  -d '{"enabled": true}'
```

### Step 2: Wait for Active Sessions

Allow in-flight deliberations to complete (monitor until count = 0):

```bash
# Poll active sessions
while true; do
  count=$(curl -s -H "Authorization: Bearer $ADMIN_API_KEY" \
    http://localhost:8000/api/admin/sessions | jq '.count')
  echo "Active sessions: $count"
  [ "$count" = "0" ] && break
  sleep 30
done
```

### Step 3: Stop Frontend

```bash
docker-compose stop frontend
```

### Step 4: Stop Backend API

The API has a graceful shutdown handler that drains in-flight requests (30s timeout):

```bash
docker-compose stop api bo1
```

### Step 5: Stop Background Jobs

```bash
docker-compose stop worker  # if using Celery/background workers
```

### Step 6: Flush Redis Before Stop

```bash
# Ensure AOF is synced
docker-compose exec redis redis-cli -a $REDIS_PASSWORD BGSAVE
docker-compose exec redis redis-cli -a $REDIS_PASSWORD BGREWRITEAOF
sleep 5

docker-compose stop redis
```

### Step 7: Stop PostgreSQL

```bash
# Checkpoint before stop
docker-compose exec postgres psql -U bo1 -d boardofone -c "CHECKPOINT;"

docker-compose stop postgres
```

### Verification

```bash
# Confirm all containers stopped
docker-compose ps
```

---

## Emergency Shutdown

Use when immediate shutdown is required (e.g., security incident, runaway costs).

### Immediate Stop (Data Loss Risk)

```bash
# Kill all active sessions first (minimizes data loss)
curl -X POST -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/api/admin/sessions/kill-all \
  -d '{"reason": "Emergency shutdown - [reason]"}'

# Stop all containers (waits for graceful stop, 10s default)
docker-compose down
```

### Force Stop (Last Resort)

Use only if `docker-compose down` hangs:

```bash
# Force kill all containers
docker-compose kill

# Remove containers
docker-compose rm -f
```

**Warning**: Force stop may result in:
- Incomplete deliberations
- Unsaved session state
- Redis AOF corruption (rare)

---

## Data Preservation

### Before Shutdown

```bash
# Create backup
make backup-db

# Verify backup integrity
make verify-backup BACKUP_FILE=backups/bo1_YYYYMMDD_HHMMSS.sql.gz.age
```

### Redis Data

Redis uses AOF persistence with fsync every second. Data loss window is ~1 second max. To ensure persistence:

```bash
# Force AOF rewrite
docker-compose exec redis redis-cli -a $REDIS_PASSWORD BGREWRITEAOF

# Wait for completion
docker-compose exec redis redis-cli -a $REDIS_PASSWORD LASTSAVE
```

### PostgreSQL Data

PostgreSQL data is persistent in the `postgres-data` volume. Checkpoint ensures all WAL is flushed:

```bash
docker-compose exec postgres psql -U bo1 -d boardofone -c "CHECKPOINT;"
```

---

## Restart Procedure

### Start Order

Services must start in dependency order:

```bash
# 1. Database first
docker-compose up -d postgres
sleep 10

# Verify database is ready
docker-compose exec postgres pg_isready -U bo1 -d boardofone

# 2. Redis
docker-compose up -d redis
sleep 5

# Verify Redis is ready
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# 3. Backend services
docker-compose up -d supertokens api bo1
sleep 10

# 4. Frontend
docker-compose up -d frontend
```

### Health Verification

```bash
# Liveness probe (basic health)
curl http://localhost:8000/api/health
# Expected: {"status": "healthy"}

# Readiness probe (all dependencies)
curl http://localhost:8000/api/ready
# Expected: {"status": "ready", "postgres": "ok", "redis": "ok"}

# Frontend health
curl http://localhost:3000
```

### Disable Maintenance Mode

```bash
# Nginx: revert maintenance config
sudo sed -i 's/return 503/# return 503/' /etc/nginx/sites-enabled/boardofone
sudo nginx -s reload

# Or feature flag
curl -X POST -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/api/admin/features/maintenance_mode \
  -d '{"enabled": false}'
```

### Post-Restart Validation

| Check | Command | Expected |
|-------|---------|----------|
| API health | `curl /api/health` | `{"status": "healthy"}` |
| API ready | `curl /api/ready` | All dependencies "ok" |
| Frontend loads | Browser test | Login page renders |
| Can create session | Test deliberation | Session starts |
| Monitoring active | Grafana dashboards | Metrics flowing |

---

## Shutdown Checklist Summary

### Planned Maintenance

- [ ] Announce maintenance window
- [ ] Verify backup exists
- [ ] Check/wait for active sessions to complete
- [ ] Enable maintenance mode
- [ ] Stop frontend
- [ ] Stop API (graceful drain)
- [ ] Flush and stop Redis
- [ ] Checkpoint and stop Postgres
- [ ] Perform maintenance
- [ ] Start: Postgres → Redis → Backend → Frontend
- [ ] Verify health endpoints
- [ ] Disable maintenance mode
- [ ] Announce completion

### Emergency Shutdown

- [ ] Kill all active sessions
- [ ] `docker-compose down`
- [ ] If hanging: `docker-compose kill`
- [ ] Investigate root cause
- [ ] Follow restart procedure
- [ ] Post-incident review

---

## Troubleshooting

### Container Won't Stop

```bash
# Check what's blocking
docker-compose logs --tail=20 <service>

# Force stop individual container
docker-compose kill <service>
```

### Database Won't Start After Shutdown

```bash
# Check postgres logs
docker-compose logs postgres

# If WAL corruption suspected
docker-compose exec postgres pg_resetwal /var/lib/postgresql/data
```

### Redis Data Missing After Restart

```bash
# Check AOF file
docker-compose exec redis ls -la /data/

# If AOF corrupted, try RDB restore
docker-compose exec redis redis-check-aof --fix /data/appendonly.aof
```

See [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) for detailed recovery procedures.
