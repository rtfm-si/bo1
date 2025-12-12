# Incident Response Playbook

## Severity Classification

| Severity | Impact | Response Time | Examples |
|----------|--------|---------------|----------|
| **P0 - Critical** | Service completely unavailable | < 15 min | Database down, auth broken, data breach |
| **P1 - High** | Major feature broken, 50%+ users affected | < 1 hour | LLM provider outage, payment failures |
| **P2 - Medium** | Feature degraded, workaround available | < 4 hours | Slow queries, partial feature failure |
| **P3 - Low** | Minor issue, minimal user impact | < 24 hours | UI bugs, non-critical errors |

## On-Call Response

### Initial Assessment (First 5 minutes)
1. **Acknowledge the alert** in ntfy.sh
2. **Check Grafana dashboards**:
   - API health: http://localhost:3200/d/api-dashboard
   - Infrastructure: http://localhost:3200/d/infrastructure
3. **Verify scope**: Single user or all users?
4. **Classify severity** using table above
5. **Start incident log** (timestamp all actions)

### Quick Diagnostics
```bash
# Check service health
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ready

# Check container status
docker-compose ps

# View recent logs
docker-compose logs --tail=100 api
docker-compose logs --tail=100 bo1

# Check database connectivity
docker-compose exec postgres pg_isready -U bo1 -d boardofone

# Check Redis connectivity
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping
```

---

## Response Procedures

### Service Outage (P0)

**Symptoms**: `/api/health` returns 5xx, containers crashing

1. **Identify failing service**:
   ```bash
   docker-compose ps
   docker-compose logs --tail=50 <service>
   ```

2. **Attempt restart**:
   ```bash
   docker-compose restart <service>
   ```

3. **If restart fails, full stack restart**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Check for resource exhaustion**:
   ```bash
   docker stats --no-stream
   df -h
   ```

5. **Rollback if recent deployment**:
   ```bash
   # Check recent deployments
   git log --oneline -5

   # Rollback to previous version
   git checkout <previous-tag>
   docker-compose build
   docker-compose up -d
   ```

### Database Issues (P0/P1)

**Symptoms**: Connection errors, slow queries, data inconsistency

1. **Check PostgreSQL status**:
   ```bash
   docker-compose exec postgres pg_isready -U bo1 -d boardofone
   docker-compose logs --tail=100 postgres
   ```

2. **Check connection count**:
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'boardofone';
   ```

3. **Kill runaway queries** (if queries > 60s):
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE duration > interval '60 seconds'
   AND state = 'active';
   ```

4. **If disk full**:
   ```bash
   # Check disk usage
   docker-compose exec postgres df -h

   # Vacuum to reclaim space
   docker-compose exec postgres vacuumdb -U bo1 -d boardofone --full
   ```

5. **Restore from backup** (last resort):
   ```bash
   make restore-db BACKUP_FILE=./backups/postgres/latest.sql.gz
   ```

### Redis Issues (P1)

**Symptoms**: Rate limiting failures, session issues, cache misses

1. **Check Redis status**:
   ```bash
   docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping
   docker-compose exec redis redis-cli -a $REDIS_PASSWORD info
   ```

2. **Check memory usage**:
   ```bash
   docker-compose exec redis redis-cli -a $REDIS_PASSWORD info memory
   ```

3. **Clear specific cache** (if corrupted data):
   ```bash
   docker-compose exec redis redis-cli -a $REDIS_PASSWORD KEYS "cache:*"
   docker-compose exec redis redis-cli -a $REDIS_PASSWORD DEL "cache:corrupted_key"
   ```

4. **Full flush** (nuclear option):
   ```bash
   docker-compose exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB
   ```

### LLM Provider Outage (P1)

**Symptoms**: Deliberations timing out, 429/503 errors from Anthropic/OpenAI

1. **Check vendor status**:
   - Anthropic: https://status.anthropic.com
   - OpenAI: https://status.openai.com

2. **System auto-handles**: Vendor health detection with fallback enabled

3. **Manual intervention** (if needed):
   ```bash
   # Check current vendor status
   curl http://localhost:8000/api/v1/status

   # View circuit breaker state
   docker-compose logs api | grep "circuit_breaker"
   ```

4. **If prolonged outage**: Communicate to users via status banner

### Authentication Issues (P1)

**Symptoms**: Login failures, session errors, OAuth callback failures

1. **Check SuperTokens status**:
   ```bash
   curl http://localhost:3567/hello
   docker-compose logs supertokens
   ```

2. **Verify OAuth configuration**:
   - Google Cloud Console: Check OAuth consent screen status
   - Verify redirect URIs match environment

3. **Check session table**:
   ```sql
   SELECT COUNT(*) FROM supertokens.session_info;
   ```

4. **Restart auth service**:
   ```bash
   docker-compose restart supertokens
   ```

### Performance Degradation (P2)

**Symptoms**: Slow API responses, timeouts, high latency alerts

1. **Check resource usage**:
   ```bash
   docker stats --no-stream
   ```

2. **Identify slow endpoints** in Grafana:
   - Check p95 latency dashboard
   - Look for recent spikes

3. **Check database performance**:
   ```sql
   SELECT query, calls, mean_time, total_time
   FROM pg_stat_statements
   ORDER BY total_time DESC
   LIMIT 10;
   ```

4. **Kill runaway sessions**:
   ```bash
   # Use admin endpoint
   curl -X POST http://localhost:8000/api/admin/sessions/kill-all \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -d '{"reason": "Performance degradation incident"}'
   ```

### Data Incident / Security Breach (P0)

**Symptoms**: Unauthorized access detected, data exposure

1. **Immediate containment**:
   ```bash
   # Block external access
   docker-compose down api frontend
   ```

2. **Preserve evidence**:
   ```bash
   # Snapshot logs
   docker-compose logs > incident-logs-$(date +%Y%m%d-%H%M%S).txt

   # Backup current database state
   make backup-db
   ```

3. **Assess scope**:
   - Which users affected?
   - What data accessed?
   - How did breach occur?

4. **Document timeline** with all actions taken

5. **Escalation**: Follow legal/compliance notification requirements

---

## Escalation Matrix

| Severity | First Contact | Escalate After | Final Escalation |
|----------|---------------|----------------|------------------|
| P0 | On-call engineer | 15 min | Leadership |
| P1 | On-call engineer | 1 hour | Tech lead |
| P2 | On-call engineer | 4 hours | - |
| P3 | Ticket/async | 24 hours | - |

## Communication Templates

### Status Update (Internal)
```
INCIDENT: [Brief description]
SEVERITY: P[0-3]
STATUS: [Investigating/Identified/Monitoring/Resolved]
IMPACT: [Who/what affected]
CURRENT ACTION: [What we're doing now]
ETA: [Estimated resolution time]
```

### User Communication (External)
```
We're currently experiencing issues with [service/feature].
Our team is actively working on a resolution.

Status: https://[status-page-url]
Updates: Every [30 min / 1 hour]

We apologize for any inconvenience.
```

### Post-Incident Summary
```
## Incident Report: [Title]

**Date**: [Date]
**Duration**: [Start time - End time]
**Severity**: P[0-3]
**Impact**: [User/business impact]

### Timeline
- [HH:MM] Alert triggered
- [HH:MM] Investigation started
- [HH:MM] Root cause identified
- [HH:MM] Fix deployed
- [HH:MM] Service restored

### Root Cause
[Brief description of what caused the incident]

### Resolution
[What was done to fix it]

### Action Items
- [ ] [Preventive measure 1]
- [ ] [Preventive measure 2]

### Lessons Learned
[What we learned from this incident]
```

---

## Monitoring & Alerting

### Alert Channels
- **ntfy.sh**: Real-time push notifications
- **Grafana**: Dashboard alerts
- **Prometheus**: Metric thresholds

### Key Metrics to Monitor
| Metric | Warning | Critical |
|--------|---------|----------|
| API p95 latency | > 500ms | > 2000ms |
| Error rate | > 1% | > 5% |
| Database connections | > 80% | > 95% |
| Memory usage | > 80% | > 95% |
| Backup age | > 26h | > 48h |

### Health Check URLs
```
Liveness:  GET /api/health
Readiness: GET /api/ready
Status:    GET /api/v1/status
```

---

## Recovery Procedures

### Full System Recovery
```bash
# 1. Stop all services
docker-compose down

# 2. Restore database
make restore-db BACKUP_FILE=./backups/postgres/latest.sql.gz

# 3. Start infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d

# 4. Wait for healthy
sleep 30

# 5. Start application
docker-compose up -d

# 6. Run migrations
uv run alembic upgrade head

# 7. Verify health
curl http://localhost:8000/api/ready
```

### Backup Locations
- **PostgreSQL**: `./backups/postgres/` (local), DO Spaces (remote)
- **Redis**: `./backups/redis/` (local), auto-persisted via AOF

### Recovery Time Objectives
| Component | RTO | RPO |
|-----------|-----|-----|
| Application | 15 min | 0 |
| Database | 30 min | 24h |
| Redis cache | 5 min | 0 (rebuild) |
