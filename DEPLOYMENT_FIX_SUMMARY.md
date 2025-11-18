# Deployment Fix Summary - GitHub Actions Issues

## Issues Identified

### Issue 1: `POSTGRES_PASSWORD` Variable Not Set ❌
**Error**: `The "POSTGRES_PASSWORD" variable is not set. Defaulting to a blank string.`

**Root Cause**: The deployment workflow verified GitHub secrets existed but never created the `.env` file on the production server. Docker Compose tried to read `${POSTGRES_PASSWORD}` from environment variables, which were undefined.

**Fix Applied**:
- Added step to create `.env` file from GitHub secrets during deployment
- Added all required secrets to the SSH action environment variables
- Enhanced secret validation to check for all required secrets (not just `POSTGRES_PASSWORD`)

---

### Issue 2: nginx Port Conflict ❌
**Error**: `failed to bind host port 0.0.0.0:80/tcp: address already in use`

**Root Cause**: The deployment script created a `docker-compose.prod.override.yml` file that tried to start a containerized nginx on ports 80/443, but nginx was already running standalone on the host (installed by `setup-production-server.sh`).

**Architecture Reality**:
- **Host nginx** (standalone) listens on ports 80/443 and proxies to containers
- **Containers** expose services only to localhost:
  - API: 127.0.0.1:8000
  - Frontend: 127.0.0.1:3000
  - Supabase Auth: 127.0.0.1:9999
  - PostgreSQL: 127.0.0.1:5432
  - Redis: 127.0.0.1:6379

**Fix Applied**:
- Removed nginx service from `docker-compose.prod.override.yml`
- Override file now explicitly empty to prevent accidental inclusion
- Added clear comments explaining nginx runs on host, not in container

---

## Changes Made to `.github/workflows/deploy-production.yml`

### 1. Added Environment Variables (Lines 191-199)
```yaml
env:
  POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
  REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  VOYAGE_API_KEY: ${{ secrets.VOYAGE_API_KEY }}
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
  BRAVE_API_KEY: ${{ secrets.BRAVE_API_KEY }}
  SUPABASE_JWT_SECRET: ${{ secrets.SUPABASE_JWT_SECRET }}
  SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
  ADMIN_API_KEY: ${{ secrets.ADMIN_API_KEY }}
```

### 2. Updated SSH Action `envs` (Line 205)
```yaml
envs: GITHUB_SHA,REGISTRY,IMAGE_NAME_API,IMAGE_NAME_FRONTEND,POSTGRES_PASSWORD,REDIS_PASSWORD,ANTHROPIC_API_KEY,VOYAGE_API_KEY,TAVILY_API_KEY,BRAVE_API_KEY,SUPABASE_JWT_SECRET,SUPABASE_ANON_KEY,ADMIN_API_KEY
```

### 3. Added .env File Creation (Lines 220-284)
```bash
# Create .env file from GitHub secrets
cat > .env <<ENV_EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://bo1:${POSTGRES_PASSWORD}@postgres:5432/boardofone
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
# ... all other required environment variables
ENV_EOF

chmod 600 .env
```

### 4. Removed nginx from Override File (Lines 329-336)
```yaml
# docker-compose.prod.override.yml
version: '3.8'
services: {}  # Empty - nginx runs on host, not in container
```

### 5. Enhanced Secret Validation (Lines 159-221)
- Added validation for all required secrets (9 total)
- Clear error messages for each missing secret
- Instructions for generating passwords

---

## Required GitHub Secrets

Before deploying, ensure these secrets are set at:
`https://github.com/rtfm-si/bo1/settings/secrets/actions`

| Secret Name | Description | How to Generate |
|-------------|-------------|-----------------|
| `PRODUCTION_HOST` | Server IP address | `139.59.201.65` |
| `PRODUCTION_USER` | SSH username | `root` or `deploy` |
| `PRODUCTION_SSH_KEY` | Private SSH key | Output from `setup-github-ssh-keys.sh` |
| `PRODUCTION_SSH_PORT` | SSH port (optional) | `22` (default) |
| `POSTGRES_PASSWORD` | PostgreSQL password | `openssl rand -base64 32` |
| `REDIS_PASSWORD` | Redis password | `openssl rand -base64 32` |
| `ANTHROPIC_API_KEY` | Claude API key | From Anthropic Console |
| `VOYAGE_API_KEY` | Voyage AI API key | From Voyage AI Console |
| `TAVILY_API_KEY` | Tavily API key (optional) | From Tavily Console |
| `BRAVE_API_KEY` | Brave Search API key (optional) | From Brave Search Console |
| `SUPABASE_JWT_SECRET` | JWT signing secret | `openssl rand -base64 32` |
| `SUPABASE_ANON_KEY` | Supabase anon key | From Supabase project settings |
| `ADMIN_API_KEY` | Admin API key | `openssl rand -base64 32` |

---

## Immediate Fix Steps (Before Next Deployment)

If you need to fix the server immediately without waiting for a new GitHub Actions deployment:

### 1. SSH into Production Server
```bash
ssh root@139.59.201.65
cd /opt/boardofone
```

### 2. Stop Running Containers
```bash
docker-compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml down || true
docker-compose -f docker-compose.prod.yml down
```

### 3. Remove Old Override File
```bash
rm -f docker-compose.prod.override.yml
```

### 4. Create New Override File (No nginx)
```bash
cat > docker-compose.prod.override.yml <<'EOF'
# Production-specific overrides (not tracked in git)
# NOTE: nginx runs standalone on host (not containerized)
# Containers expose ports only to localhost for host nginx to proxy
version: '3.8'
services: {}
EOF
```

### 5. Create .env File Manually
```bash
# Generate passwords
POSTGRES_PW=$(openssl rand -base64 32)
REDIS_PW=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
ADMIN_KEY=$(openssl rand -base64 32)

# Create .env file (fill in your actual API keys)
cat > .env <<EOF
# Database
POSTGRES_PASSWORD=${POSTGRES_PW}
DATABASE_URL=postgresql://bo1:${POSTGRES_PW}@postgres:5432/boardofone

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=${REDIS_PW}
REDIS_URL=redis://:${REDIS_PW}@redis:6379/0

# LLM API Keys (REPLACE WITH YOUR ACTUAL KEYS)
ANTHROPIC_API_KEY=your_anthropic_key_here
VOYAGE_API_KEY=your_voyage_key_here
TAVILY_API_KEY=your_tavily_key_here
BRAVE_API_KEY=your_brave_key_here

# Supabase Auth
ENABLE_SUPABASE_AUTH=true
CLOSED_BETA_MODE=true
SUPABASE_URL=http://supabase-auth:9999
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_JWT_SECRET=${JWT_SECRET}

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
CORS_ORIGINS=https://boardof.one
ADMIN_API_KEY=${ADMIN_KEY}
SITE_URL=https://boardof.one

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
MAX_COST_PER_SESSION=1.00
MAX_COST_PER_SUBPROBLEM=0.15
ENABLE_PROMPT_CACHING=true
ENABLE_CONVERGENCE_DETECTION=true
ENABLE_DRIFT_DETECTION=true
ENABLE_EARLY_STOPPING=true
EOF

chmod 600 .env

# Print generated secrets (SAVE THESE!)
echo "======================================="
echo "IMPORTANT: Save these secrets!"
echo "======================================="
echo "POSTGRES_PASSWORD=${POSTGRES_PW}"
echo "REDIS_PASSWORD=${REDIS_PW}"
echo "SUPABASE_JWT_SECRET=${JWT_SECRET}"
echo "ADMIN_API_KEY=${ADMIN_KEY}"
echo "======================================="
```

### 6. Add Secrets to GitHub
Copy the generated passwords and add them to GitHub Secrets:
1. Go to: https://github.com/rtfm-si/bo1/settings/secrets/actions
2. Add each secret listed in the "Required GitHub Secrets" section above
3. Use the generated passwords from step 5

### 7. Start Services
```bash
docker-compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d
```

### 8. Verify Services
```bash
# Check containers are running
docker ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test health endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/db
curl http://localhost:8000/api/health/redis
```

### 9. Test nginx
```bash
# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check external access
curl https://boardof.one/api/health
```

---

## Next Deployment

After adding all GitHub secrets, the next deployment will:
1. ✅ Automatically create the `.env` file from secrets
2. ✅ Use the corrected override file (no nginx)
3. ✅ Validate all secrets before deploying
4. ✅ Properly separate host nginx from containerized services

Deploy via:
1. Go to **Actions** tab → **Deploy to Production**
2. Click **Run workflow**
3. Type `deploy-to-production` to confirm
4. Monitor deployment progress

---

## Verification Checklist

After deployment (automated or manual):
- [ ] All containers running: `docker ps`
- [ ] No port conflicts: `docker-compose logs | grep "address already in use"`
- [ ] No password warnings: `docker-compose logs | grep "POSTGRES_PASSWORD"`
- [ ] API health: `curl http://localhost:8000/api/health`
- [ ] Database health: `curl http://localhost:8000/api/health/db`
- [ ] Redis health: `curl http://localhost:8000/api/health/redis`
- [ ] External access: `curl https://boardof.one/api/health`
- [ ] nginx config valid: `sudo nginx -t`
- [ ] nginx running: `sudo systemctl status nginx`

---

## Files Modified

1. `.github/workflows/deploy-production.yml` - Fixed deployment workflow
2. `DEPLOYMENT_FIX_SUMMARY.md` - This file (documentation)

---

## References

- Production Environment Setup: `deployment-scripts/PRODUCTION_ENV_SETUP.md`
- Production Deployment Guide: `docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md`
- Blue-Green Deployment: `docs/BLUE_GREEN_DEPLOYMENT.md`
- nginx Configuration: `nginx/nginx-blue.conf`
