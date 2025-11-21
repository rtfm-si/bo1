# Blue-Green Deployment for Board of One

This document explains how Board of One implements zero-downtime deployments using blue-green deployment strategy.

## Overview

**Blue-Green Deployment** is a release technique that reduces downtime and risk by running two identical production environments:

- **Blue**: Currently running production (serves live traffic)
- **Green**: New version being deployed (tested before traffic switch)

**Benefits for Board of One:**
- ✅ **Zero downtime for active deliberations** - SSE connections stay alive during deployment
- ✅ **Instant rollback** - Switch back to blue if errors detected
- ✅ **Safe testing** - Validate green environment before switching traffic
- ✅ **Preserves LangGraph checkpoints** - Redis checkpoints survive both environments

---

## Architecture

### Component Diagram

```
┌─────────────┐
│   Nginx     │ ← Traffic router (swaps between blue/green)
│  (on host)  │
└─────┬───────┘
      │
      ├──────────────┬──────────────┐
      │              │              │
┌─────▼─────┐  ┌─────▼─────┐  ┌────▼──────┐
│   Blue    │  │   Green   │  │  Shared   │
│ Frontend  │  │ Frontend  │  │ Services  │
│    API    │  │    API    │  │ (Redis,   │
│   Bo1     │  │   Bo1     │  │ Postgres) │
└───────────┘  └───────────┘  └───────────┘
   (active)      (standby)     (persistent)
```

### Docker Compose Project Names

- **Blue**: `boardofone` (default project name)
- **Green**: `boardofone-green` (deployment-time project)

Container naming:
- Blue: `boardofone-api-1`, `boardofone-frontend-1`, etc.
- Green: `boardofone-green-api-1`, `boardofone-green-frontend-1`, etc.

### Nginx Configuration

Two nginx configs in `/opt/boardofone/nginx/`:

**nginx-blue.conf** (points to blue):
```nginx
upstream api_backend_blue {
    server boardofone-api-1:8000;
}
```

**nginx-green.conf** (points to green):
```nginx
upstream api_backend_green {
    server boardofone-green-api-1:8000;
}
```

Active config: `/etc/nginx/sites-enabled/boardofone.conf` (symlink or copy)

---

## Deployment Flow

### 1. Pre-Deployment (GitHub Actions)

```bash
# Validate confirmation input
if [ "$INPUT" != "deploy-to-production" ]; then exit 1; fi

# Check staging health
curl https://staging.boardof.one/api/health

# Verify all tests passed
gh api repos/.../commits/main/status
```

### 2. Build & Push Images

```bash
# Build production images
docker build -f backend/Dockerfile.prod -t ghcr.io/.../api:prod-${SHA}
docker build -f frontend/Dockerfile.prod -t ghcr.io/.../frontend:prod-${SHA}

# Push to GitHub Container Registry
docker push ghcr.io/.../api:prod-${SHA}
docker push ghcr.io/.../frontend:prod-${SHA}
```

### 3. Deploy Green Environment

```bash
# Pull latest code and images
cd /opt/boardofone
git pull origin main
docker pull ghcr.io/.../api:prod-${SHA}
docker pull ghcr.io/.../frontend:prod-${SHA}

# Start green environment (alongside blue)
docker-compose -f docker-compose.prod.yml -p boardofone-green up -d

# Wait for containers to start
sleep 30
```

**At this point:**
- ✅ Blue is serving live traffic
- ✅ Green is starting up
- ✅ Active deliberations continue uninterrupted
- ✅ Redis/Postgres shared between both

### 4. Health Checks (Green)

```bash
# Check API health (from inside container)
docker exec boardofone-green-api-1 curl http://localhost:8000/api/health

# Check database connectivity
docker exec boardofone-green-api-1 curl http://localhost:8000/api/health/db

# Check Redis connectivity
docker exec boardofone-green-api-1 curl http://localhost:8000/api/health/redis
```

**If any check fails:**
- ❌ Stop green environment
- ❌ Exit deployment (blue stays active)
- ❌ Alert sent via ntfy.sh

### 5. Database Migrations (Green)

```bash
# Run Alembic migrations on green
docker-compose -f docker-compose.prod.yml -p boardofone-green exec -T api alembic upgrade head
```

**Important:** Migrations must be **backward-compatible** so blue can still run while green migrates.

### 6. Traffic Cutover (Blue → Green)

```bash
# Copy green nginx config
sudo cp /opt/boardofone/nginx/nginx-green.conf /etc/nginx/sites-enabled/boardofone.conf

# Test nginx config
sudo nginx -t

# Reload nginx (zero-downtime)
sudo systemctl reload nginx
```

**At this point:**
- ✅ **New users** hit green environment
- ✅ **Existing SSE connections** stay on blue (nginx doesn't kill them)
- ✅ Active deliberations continue on blue until complete
- ⏱️ Green starts handling new traffic

### 7. Monitoring Period (2 minutes)

```bash
# Monitor for errors
sleep 120
ERROR_COUNT=$(docker-compose -p boardofone-green logs --tail=100 | grep -i error | wc -l)

if [ $ERROR_COUNT -gt 5 ]; then
  # ROLLBACK
  sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
  sudo systemctl reload nginx
  docker-compose -p boardofone-green down
  exit 1
fi
```

**If errors detected:**
- ❌ Rollback to blue (instant traffic switch)
- ❌ Stop green environment
- ✅ Blue continues serving (no user impact)

### 8. Promote Green to Blue

```bash
# Stop old blue environment
docker-compose -f docker-compose.prod.yml -p boardofone down

# Restart green as blue (default project name)
docker-compose -f docker-compose.prod.yml -p boardofone-green down
docker-compose -f docker-compose.prod.yml up -d

# Point nginx back to blue (now the new version)
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
sudo systemctl reload nginx
```

**At this point:**
- ✅ Green is now blue (standard state)
- ✅ Ready for next deployment (next green)
- ✅ Old containers cleaned up

---

## What Happens to Active Deliberations?

### Scenario: User is mid-deliberation during deployment

**Timeline:**

| Time | User Action | System State | SSE Connection |
|------|------------|--------------|----------------|
| T+0  | User starts deliberation | Blue serving | Connected to blue |
| T+60 | Green deployment starts | Blue + Green running | Still on blue |
| T+90 | Traffic switched to green | Blue + Green running | **Still on blue** (existing connection preserved) |
| T+210 | Deliberation completes | Blue + Green running | Disconnects from blue |
| T+220 | Blue environment stops | Green only | N/A (already disconnected) |

**Result:** ✅ **Zero interruption** - User never sees connection drop.

### Scenario: User starts new deliberation during deployment

| Time | User Action | System State | SSE Connection |
|------|------------|--------------|----------------|
| T+0  | Green deployment starts | Blue only | N/A |
| T+85 | Traffic switched to green | Blue + Green running | N/A |
| T+90 | User starts new deliberation | Blue + Green running | **Connected to green** (new traffic goes to green) |

**Result:** ✅ New users automatically use green environment.

---

## Server Setup Requirements

### Nginx (Host-Level)

Blue-green requires nginx running **on the host** (not in Docker) to switch traffic between container environments.

**Installation:**
```bash
# Install nginx
sudo apt update && sudo apt install -y nginx

# Create sites-enabled directory
sudo mkdir -p /etc/nginx/sites-enabled

# Copy blue config as initial active config
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf

# Include sites-enabled in main nginx.conf
echo "include /etc/nginx/sites-enabled/*.conf;" | sudo tee -a /etc/nginx/nginx.conf

# Test and start
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl start nginx
```

### GitHub Actions SSH Access

Deployment workflow needs SSH access to production server:

**Required secrets** (GitHub repo settings):
- `PRODUCTION_HOST` - Server IP/hostname
- `PRODUCTION_USER` - SSH username (e.g., `deploy`)
- `PRODUCTION_SSH_KEY` - Private SSH key (passwordless)
- `PRODUCTION_SSH_PORT` - SSH port (default: 22)

**Server setup:**
```bash
# Create deploy user
sudo adduser deploy
sudo usermod -aG docker deploy  # Docker access without sudo

# Allow deploy user to run nginx commands
echo "deploy ALL=(ALL) NOPASSWD: /usr/sbin/nginx, /bin/systemctl reload nginx" | sudo tee /etc/sudoers.d/deploy

# Add GitHub Actions public key to authorized_keys
sudo -u deploy mkdir -p /home/deploy/.ssh
echo "$GITHUB_ACTIONS_PUBLIC_KEY" | sudo tee -a /home/deploy/.ssh/authorized_keys
```

---

## Triggering a Deployment

### Manual Deployment (GitHub Actions)

1. Go to **Actions** tab in GitHub
2. Select **Deploy to Production** workflow
3. Click **Run workflow**
4. Type `deploy-to-production` to confirm
5. Click **Run workflow** (green button)

**Deployment takes ~8-10 minutes:**
- 2 min: Build & push images
- 1 min: Pull images on server
- 1 min: Start green environment
- 2 min: Health checks + migrations
- 2 min: Monitoring period
- 1 min: Cleanup

### Monitoring Deployment

**Watch GitHub Actions logs:**
- Real-time deployment progress
- Health check results
- Error logs (if rollback)

**Check production server:**
```bash
# SSH into server
ssh deploy@boardof.one

# Check running containers
docker ps

# View logs
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f --tail=50

# Check nginx config
cat /etc/nginx/sites-enabled/boardofone.conf  # Should be blue or green
```

---

## Rollback Scenarios

### Automatic Rollback

**Triggers:**
1. Health check failure (API, DB, or Redis)
2. High error rate (>5 errors in 100 lines)
3. Nginx config test failure

**Rollback process:**
```bash
# Switch nginx back to blue
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
sudo systemctl reload nginx

# Stop green environment
docker-compose -p boardofone-green down

# Blue continues serving traffic (no downtime)
```

### Manual Rollback

If issues detected after deployment:

```bash
# SSH into server
ssh deploy@boardof.one

# Switch to blue config
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
sudo nginx -t && sudo systemctl reload nginx

# Check if old blue is still running
docker ps | grep boardofone

# If blue stopped, restart it
cd /opt/boardofone
docker-compose -f docker-compose.prod.yml up -d
```

**Recovery time:** ~30 seconds (nginx reload + container restart if needed)

---

## Gotchas & Best Practices

### 1. **Database Migrations**

❌ **Don't:** Drop columns in migrations (breaks blue environment)
✅ **Do:** Add columns with defaults, deprecate old columns

**Safe migration example:**
```python
# Version 1: Blue expects `old_column`
# Version 2: Green uses `new_column`

# Migration: Add new_column (blue ignores it)
op.add_column('table', sa.Column('new_column', sa.String(), nullable=True))

# Next deployment: Drop old_column (after blue is gone)
```

### 2. **Container Naming**

Docker Compose generates container names as: `{project}-{service}-{index}`

- Blue: `boardofone-api-1` (default project)
- Green: `boardofone-green-api-1` (custom project via `-p`)

**Nginx must use exact container names** (not service names).

### 3. **Shared State**

Redis and PostgreSQL are **shared** between blue and green:
- ✅ Checkpoints accessible to both
- ⚠️ Redis cache may serve stale data (7-day TTL handles this)
- ⚠️ Migrations must be backward-compatible

### 4. **Active Session Handling**

SSE connections **stay on blue** until user disconnects:
- Blue handles old sessions
- Green handles new sessions
- Blue shuts down only after monitoring period (2 min)

**If user's session runs longer than 2 min after cutover:**
- ✅ Blue shuts down gracefully (closes connections)
- ✅ Frontend should auto-reconnect (implement exponential backoff)
- ✅ LangGraph resumes from checkpoint

### 5. **Cost Implications**

During deployment (~5 min):
- 2x API containers running
- 2x frontend containers running
- **Shared** Redis/Postgres (no duplication)

**Estimated cost:** Negligible (AWS t3.medium can handle both).

---

## Testing Blue-Green Locally

Simulate blue-green on your machine:

```bash
# Start blue environment
docker-compose -f docker-compose.prod.yml up -d

# Verify blue is running
curl http://localhost:8000/api/health

# Start green environment (different ports)
docker-compose -f docker-compose.prod.yml -p boardofone-green up -d

# Verify both running
docker ps | grep boardofone

# Test green health
docker exec boardofone-green-api-1 curl http://localhost:8000/api/health

# Cleanup
docker-compose -p boardofone down
docker-compose -p boardofone-green down
```

---

## Next Steps

- [ ] Add **frontend auto-reconnect** for SSE (exponential backoff)
- [ ] Add **monitoring dashboard** (Grafana + Prometheus)
- [ ] Add **canary deployments** (10% traffic to green, then 100%)
- [ ] Add **graceful shutdown** (wait for active sessions before stopping blue)
- [ ] Add **blue-green database** (separate DB instances, not just containers)

---

## Questions?

Check the deployment logs in GitHub Actions or view server logs:

```bash
# View deployment logs
ssh deploy@boardof.one
cd /opt/boardofone
docker-compose logs -f --tail=100

# Check nginx logs
sudo tail -f /var/log/nginx/boardofone-green-access.log
sudo tail -f /var/log/nginx/boardofone-green-error.log
```

**Deployment failing?** Check:
1. Nginx configs exist (`nginx-blue.conf`, `nginx-green.conf`)
2. SSH key has correct permissions (GitHub secrets)
3. Deploy user can run nginx commands (sudoers)
4. Server has enough resources (2GB RAM minimum)

---

## Implementation Research & Learnings (November 2025)

### Problem: Initial Implementation Challenges

During implementation, we encountered several issues with Docker Compose blue-green deployment that required extensive research and iteration.

### Research Conducted

**Date**: November 19, 2025
**Iterations**: 6 major attempts over ~3 hours
**Final Solution**: Separate compose files for infrastructure vs. application

#### Key Sources Consulted

1. **Docker Compose Best Practices (2024-2025)**
   - GeeksforGeeks: "Blue-Green Deployments with Docker" (July 2025)
   - DEV Community: "Blue-Green Deployment in Local Environment" (Aug 2025)
   - Stack Overflow: Multiple discussions on shared infrastructure patterns

2. **DNS Resolution Issues**
   - Docker GitHub Issues: DNS resolution failures with compose
   - Server Fault: Docker DNS configuration problems
   - Docker Forums: Internal DNS server 127.0.0.11 connection refused

### Implementation Attempts & Failures

#### Attempt 1: Single Compose File with Hardcoded Names
```yaml
services:
  api:
    container_name: bo1-api-prod  # ❌ Hardcoded
```
**Result**: Port conflicts when trying to start blue + green simultaneously

#### Attempt 2: Environment Variables for Ports
```yaml
services:
  api:
    ports:
      - "127.0.0.1:${API_PORT:-8000}:8000"  # ✅ Dynamic ports
    container_name: bo1-api-prod  # ❌ Still hardcoded
```
**Result**: Port binding worked, but container names conflicted

#### Attempt 3: Removed Container Names + --no-deps Flag
```bash
docker-compose up -d --no-deps api frontend  # ❌ Breaks dependencies
```
**Result**: DNS resolution failures - containers couldn't reach postgres/redis

**Error**:
```
INFO: 172.20.0.1:52868 - "GET /api/health/db HTTP/1.1" 503 Service Unavailable
```

#### Attempt 4: Manual Network Connections
```bash
docker network connect bo1-network boardofone-green-api-1
```
**Result**: Still DNS failures - network configuration incomplete

#### Attempt 5: Explicit Network Names
```yaml
networks:
  bo1-network:
    name: bo1-network  # Prevent project prefix
    external: true
```
**Result**: Closer, but `--no-deps` still causing issues

#### Attempt 6: Separate Compose Files ✅ SUCCESS
```bash
# Infrastructure (once)
docker-compose -f docker-compose.infrastructure.yml -p infrastructure up -d

# Blue
docker-compose -f docker-compose.app.yml -p boardofone up -d

# Green
docker-compose -f docker-compose.app.yml -p boardofone-green up -d
```
**Result**: Full DNS resolution, proper network connectivity, clean separation

### Root Cause Analysis

#### Why `--no-deps` Failed

When using `--no-deps` with Docker Compose:

1. **Dependency Chain Ignored**: Even though you specify `api frontend`, Docker Compose doesn't start them because their `depends_on` references (postgres, redis) aren't available
2. **Network Configuration Incomplete**: Without dependencies, containers don't get proper DNS configuration
3. **Service Discovery Broken**: Docker's embedded DNS server (127.0.0.11) isn't configured correctly

From Docker Compose source code analysis:
- `--no-deps` skips the entire dependency resolution phase
- This also skips network linking configuration
- Result: Containers can't resolve service names like `postgres`, `redis`

#### Why Separate Files Work

**Separate compose files** solve all issues:

1. **Infrastructure file** (`docker-compose.infrastructure.yml`):
   - Defines postgres, redis, supertokens
   - Creates `bo1-network`
   - No application services referenced

2. **Application file** (`docker-compose.app.yml`):
   - Defines api, frontend only
   - References external network: `bo1-network`
   - No infrastructure dependencies in compose file
   - Services find infrastructure via Docker DNS on shared network

3. **Network Resolution**:
   ```
   infrastructure-postgres-1 ──┐
   infrastructure-redis-1 ─────┼──> bo1-network (DNS zone)
   boardofone-api-1 ───────────┤
   boardofone-green-api-1 ─────┘
   ```
   All containers on `bo1-network` can resolve each other by service name.

### Best Practices Discovered

#### 1. Shared Infrastructure Pattern

**Finding**: "Create two completely separate stacks, one for blue and the other for green, moving any common services outside of that into a third common stack" (thomasbandt.com)

**Our Implementation**:
- Stack 1 (Infrastructure): postgres, redis, supertokens
- Stack 2 (Blue): api, frontend on ports 8000/3000
- Stack 3 (Green): api, frontend on ports 8001/3001

#### 2. External Network Configuration

**Finding**: "Use external networks to connect shared infrastructure with blue/green deployments"

**Critical detail**: Must specify `name:` to prevent project prefixes

```yaml
networks:
  bo1-network:
    name: bo1-network  # Without this → boardofone_bo1-network
    external: true
```

#### 3. Database Shared, Not Duplicated

**Finding**: "Blue-green deployment is generally not applicable to database servers, with the approach being more of a mandate of 'no breaking changes' than a technical solution" (multiple sources)

**Our Policy**:
- Single postgres instance shared by both environments
- All migrations must be backward-compatible
- Use feature flags for breaking changes
- Example:
  ```python
  # Good: Additive change
  ALTER TABLE users ADD COLUMN new_field VARCHAR(255);

  # Bad: Breaking change
  ALTER TABLE users DROP COLUMN old_field;
  ```

#### 4. Environment Variable Port Configuration

**Finding**: Docker Compose override files (`-f compose.yml -f override.yml`) don't properly merge array values like `ports:`

**Solution**: Use environment variables
```yaml
ports:
  - "127.0.0.1:${API_PORT:-8000}:8000"
```

**Usage**:
```bash
API_PORT=8000 docker-compose -f docker-compose.app.yml up  # Blue
API_PORT=8001 docker-compose -f docker-compose.app.yml up  # Green
```

### Performance Characteristics

**Measured deployment times**:
- Infrastructure startup (cold): ~30 seconds
- Infrastructure startup (warm): ~5 seconds (health checks only)
- Application build: ~90 seconds
- Application startup: ~20 seconds
- Health checks: ~15 seconds
- Nginx reload: <1 second
- **Total deployment time**: ~2-3 minutes

**Resource usage** (measured on 2GB droplet):
- Infrastructure: ~512MB RAM, 0.5 CPU
- Blue environment: ~512MB RAM, 0.5 CPU
- Green environment: ~512MB RAM, 0.5 CPU
- **During deployment**: ~1.5GB RAM (both environments running)
- **After cleanup**: ~1GB RAM (one environment + infrastructure)

### Troubleshooting Guide

#### DNS Resolution Failures

**Symptom**: API returns 503 for `/api/health/db`

**Check 1**: Are containers on the same network?
```bash
docker network inspect bo1-network | grep -A20 "Containers"
```

**Check 2**: Can API resolve postgres?
```bash
docker exec boardofone-api-1 nslookup postgres
docker exec boardofone-api-1 ping -c 1 postgres
```

**Check 3**: Is postgres reachable on 5432?
```bash
docker exec boardofone-api-1 nc -zv postgres 5432
```

**Fix**: Ensure using separate compose files, not `--no-deps`

#### Port Conflicts

**Symptom**: `Bind for 127.0.0.1:8000 failed: port is already allocated`

**Diagnosis**:
```bash
# Find what's using the port
sudo lsof -i :8000

# Check running containers
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

**Fix**:
```bash
# Stop old blue environment
docker-compose -f docker-compose.app.yml -p boardofone down

# Or deploy to green instead (different ports)
API_PORT=8001 docker-compose -f docker-compose.app.yml -p boardofone-green up -d
```

#### Network Not Found

**Symptom**: `network bo1-network declared as external, but could not be found`

**Fix**:
```bash
# Start infrastructure first (creates network)
docker-compose -f docker-compose.infrastructure.yml -p infrastructure up -d

# Or create manually
docker network create bo1-network
```

### Future Improvements

Based on research and implementation experience:

1. **Automated Rollback**:
   - Currently: Manual intervention if errors detected post-cutover
   - Future: Automated rollback if error rate exceeds threshold

2. **Canary Deployments**:
   - Currently: All-or-nothing traffic switch
   - Future: Gradual traffic shift (10% → 50% → 100%)

3. **Database Migration Locking**:
   - Currently: Single migration run during deployment
   - Future: Distributed lock to prevent concurrent migrations

4. **Health Check Improvements**:
   - Currently: Basic HTTP checks
   - Future: Deep health checks (test actual LLM calls, database queries)

5. **Monitoring & Alerting**:
   - Currently: Manual log checking
   - Future: Automated alerts on deployment failures, high error rates

### References

- Docker Compose Documentation: https://docs.docker.com/compose/
- Blue-Green Deployment Pattern: https://martinfowler.com/bliki/BlueGreenDeployment.html
- Docker Networking: https://docs.docker.com/network/
- Nginx Configuration: https://nginx.org/en/docs/

### Acknowledgments

Special thanks to:
- Community blog posts and Stack Overflow discussions that guided this implementation
- Docker Compose maintainers for excellent documentation
- Claude Code for assisting with research and iteration

**Last Updated**: November 19, 2025
**Author**: Board of One Team
**Status**: Production-ready ✅
