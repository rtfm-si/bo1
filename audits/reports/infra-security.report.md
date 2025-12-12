# Infrastructure Security Audit Report

**Audit Date:** 2025-12-12
**Scope:** Network, Secrets, Containers, Logging, Backup & Recovery
**Manifest:** `audits/manifests/infra-security.manifest.xml`

---

## Executive Summary

Overall security posture is **Good** with proper production hardening in place. Key strengths include localhost-only port bindings in production, non-root container users, and CORS validation. Several improvements recommended for defense-in-depth.

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 4 |
| Low | 3 |
| Info | 2 |

---

## Findings

### [HIGH] H1: Development Ports Exposed to All Interfaces

**Location:** `docker-compose.yml` (lines 17-18, 38-39, 149, 204, 241, 279-280, 302-303)

**Issue:** Development docker-compose exposes Postgres (5432), Redis (6379), SuperTokens (3567), API (8000), and monitoring services to all interfaces (`0.0.0.0`).

**Evidence:**
```yaml
# docker-compose.yml (dev)
ports:
  - "5432:5432"   # Postgres - ALL interfaces
  - "6379:6379"   # Redis - ALL interfaces
  - "3567:3567"   # SuperTokens - ALL interfaces
  - "8000:8000"   # API - ALL interfaces
```

**Risk:** If development environment is exposed to network (e.g., cloud VM, public WiFi), database and auth services are accessible to attackers.

**Remediation:** Bind to localhost in dev compose:
```yaml
ports:
  - "127.0.0.1:5432:5432"
```

**Effort:** Low (15 min)

---

### [MEDIUM] M1: Hardcoded Fallback API Key in SuperTokens Config

**Location:** `backend/api/supertokens_config.py:128`

**Issue:** Fallback API key `dev_api_key_change_in_production` is hardcoded.

**Evidence:**
```python
api_key=os.getenv("SUPERTOKENS_API_KEY", "dev_api_key_change_in_production"),
```

**Risk:** If env var is missing, weak default API key is used. Already flagged in prior security audit.

**Remediation:** Remove fallback, fail startup if key missing:
```python
api_key=os.environ["SUPERTOKENS_API_KEY"]  # No fallback
```

**Effort:** Low (10 min)

---

### [MEDIUM] M2: Redis No Authentication in Development

**Location:** `docker-compose.yml` (lines 36-54)

**Issue:** Development Redis does not require password authentication.

**Evidence:**
```yaml
# docker-compose.yml - NO --requirepass flag
command: >
  redis-stack-server
  --appendonly yes
  --maxmemory 256mb
```

**Risk:** Any process with network access can read/write session data in dev.

**Remediation:** Add password even in dev:
```yaml
command: >
  redis-stack-server
  --appendonly yes
  --requirepass ${REDIS_PASSWORD:-devpassword}
```

**Effort:** Low (15 min)

---

### [MEDIUM] M3: Promtail Docker Socket Access

**Location:** `docker-compose.infrastructure.yml:164`

**Issue:** Promtail has read access to Docker socket (`/var/run/docker.sock:ro`).

**Evidence:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

**Risk:** Read access to Docker socket can expose sensitive container metadata and environment variables. A compromised Promtail could enumerate all containers.

**Remediation:** Use Docker logging driver instead of socket access, or run Promtail in a separate network with minimal privileges.

**Effort:** Medium (2-4 hours)

---

### [MEDIUM] M4: Missing Log Scrubbing for Sensitive Data

**Location:** `monitoring/promtail/promtail-config.yml`

**Issue:** Promtail pipeline has no filters for sensitive data (passwords, tokens, PII).

**Evidence:** No `drop` or `replace` stages for sensitive patterns in `pipeline_stages`.

**Risk:** Secrets accidentally logged (e.g., in error messages) would be stored in Loki.

**Remediation:** Add pipeline stages to scrub sensitive patterns:
```yaml
pipeline_stages:
  - replace:
      expression: '(password|api_key|token|secret)["\s]*[:=]["\s]*[^"\s,}]+'
      replace: '$1=REDACTED'
```

**Effort:** Low (30 min)

---

### [LOW] L1: No Backup Encryption

**Location:** `deployment-scripts/setup-droplet.sh:165-173`

**Issue:** Database backups are stored as plain gzip files without encryption.

**Evidence:**
```bash
docker exec boardofone-postgres pg_dump -U boardofone boardofone | gzip > "${BACKUP_DIR}/postgres/backup_${DATE}.sql.gz"
```

**Risk:** If backup storage is compromised, all database contents are exposed.

**Remediation:** Encrypt backups with GPG or age:
```bash
pg_dump ... | gzip | gpg --symmetric --cipher-algo AES256 > backup.sql.gz.gpg
```

**Effort:** Low (30 min)

---

### [LOW] L2: Missing Disaster Recovery Documentation

**Location:** Referenced in `docs/PRODUCTION_SECURITY.md:130` but file does not exist

**Issue:** `docs/DISASTER_RECOVERY.md` is referenced but not created.

**Risk:** In an incident, operators may not know recovery procedures.

**Remediation:** Create disaster recovery runbook covering:
- Database restore from backup
- Redis data recovery
- Service failover procedures
- Contact escalation

**Effort:** Medium (2-4 hours)

---

### [LOW] L3: Backup Retention Only 7 Days

**Location:** `deployment-scripts/setup-droplet.sh:172-173`

**Issue:** Backups are deleted after 7 days.

**Evidence:**
```bash
find "${BACKUP_DIR}/postgres" -name "backup_*.sql.gz" -mtime +7 -delete
```

**Risk:** If data corruption is discovered after 7 days, no recovery is possible.

**Remediation:** Keep weekly backups for 30 days, monthly for 90 days:
```bash
# Keep daily for 7 days, weekly for 30, monthly for 90
```

**Effort:** Low (30 min)

---

### [INFO] I1: Grafana Default Credentials in .env.example

**Location:** `.env.example:153-154`

**Issue:** Example shows `admin/admin` defaults for Grafana.

**Evidence:**
```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=generate_secure_password_here
```

**Risk:** Documentation shows weak defaults that could be copy-pasted.

**Remediation:** Update example to show placeholder with generation command.

**Effort:** Trivial (5 min)

---

### [INFO] I2: Production Compose Uses Non-Root Users (Positive Finding)

**Location:** `backend/Dockerfile.prod:37`, `frontend/Dockerfile.prod:45`, `Dockerfile:99`

**Evidence:**
```dockerfile
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

**Status:** Production containers properly run as non-root. No action needed.

---

## Positive Security Controls

| Control | Status | Location |
|---------|--------|----------|
| Production ports bound to localhost | OK | `docker-compose.prod.yml` |
| Non-root container users | OK | All Dockerfiles (prod stage) |
| Redis authentication in prod | OK | `docker-compose.prod.yml:54` |
| CORS wildcard rejection in prod | OK | `backend/api/main.py:289-293` |
| .env in .gitignore | OK | `.gitignore:45-46` |
| Secret patterns in .gitignore | OK | `.gitignore:104-108` |
| Security headers middleware | OK | `backend/api/middleware/security_headers.py` |
| Rate limiting middleware | OK | `backend/api/middleware/rate_limit.py` |
| Automated daily backups | OK | `deployment-scripts/setup-droplet.sh:155-181` |

---

## Remediation Priority

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| 1 | H1: Dev port binding | Low | High |
| 2 | M1: Hardcoded API key fallback | Low | Medium |
| 3 | M2: Redis no auth in dev | Low | Medium |
| 4 | M4: Log scrubbing | Low | Medium |
| 5 | L1: Backup encryption | Low | Medium |
| 6 | L2: DR documentation | Medium | Medium |
| 7 | M3: Promtail socket | Medium | Low |
| 8 | L3: Backup retention | Low | Low |

---

## Verification Steps

After remediation:

1. **Port binding:** `docker-compose config | grep -A2 ports` - verify 127.0.0.1 prefix
2. **SuperTokens key:** Start API without SUPERTOKENS_API_KEY - should fail
3. **Redis auth:** `redis-cli ping` without password - should fail
4. **Log scrubbing:** Search Loki for "password=" - should find none
5. **Backup encryption:** `file backup.sql.gz.gpg` - should show "GPG encrypted"

---

*Report generated by Claude Code infrastructure security audit*
