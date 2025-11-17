# CI/CD Setup Complete! 🎉

## Files Created

### GitHub Actions Workflows
✅ `.github/workflows/ci.yml` - Continuous Integration
✅ `.github/workflows/deploy-staging.yml` - Auto-deploy to staging
✅ `.github/workflows/deploy-production.yml` - Manual production deployment

### Production Docker Files
✅ `backend/Dockerfile.prod` - Production API container
✅ `frontend/Dockerfile.prod` - Production frontend container
✅ `docker-compose.prod.yml` - Production orchestration

### Nginx Configuration
✅ `nginx/nginx.conf` - SSL, rate limiting, caching, security headers

### Deployment Scripts
✅ `deployment-scripts/setup-droplet.sh` - One-time droplet setup
✅ `deployment-scripts/deploy-manual.sh` - Manual deployment script
✅ `deployment-scripts/backup.sh` - Auto-generated during setup

### Environment & Documentation
✅ `.env.production.example` - Production environment template
✅ `DEPLOYMENT_GUIDE.md` - Complete deployment instructions

---

## Quick Start: DigitalOcean Setup Tonight

### 1. Create Droplet (5 minutes)
```bash
# In DigitalOcean console:
# - Ubuntu 22.04 LTS
# - $24/month (4GB RAM, 2 vCPUs)
# - Add your SSH key
# - Note the IP address
```

### 2. Configure DNS (5 minutes)
```bash
# In your domain registrar:
# Add A records pointing to droplet IP:
#   boardofone.com → YOUR_DROPLET_IP
#   www.boardofone.com → YOUR_DROPLET_IP
#   staging.boardofone.com → YOUR_DROPLET_IP
```

### 3. Run Setup Script (10 minutes)
```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Download and run setup
curl -fsSL https://raw.githubusercontent.com/yourusername/bo1/main/deployment-scripts/setup-droplet.sh | bash
```

### 4. Configure Secrets (5 minutes)
```bash
cd /opt/boardofone
cp .env.production.example .env.production
nano .env.production

# Set these values:
# - POSTGRES_PASSWORD (generate: openssl rand -base64 32)
# - ADMIN_API_KEY (generate: openssl rand -base64 32)
# - ANTHROPIC_API_KEY (from console.anthropic.com)
# - CORS_ORIGINS=https://boardofone.com

cp .env.production .env
```

### 5. Setup SSL (3 minutes)
```bash
# Wait for DNS propagation first (nslookup boardofone.com)
certbot --nginx -d boardofone.com -d www.boardofone.com -d staging.boardofone.com

# Follow prompts, select redirect HTTP to HTTPS
```

### 6. Configure GitHub Actions (10 minutes)
```bash
# In GitHub repository → Settings → Secrets → Actions

# Add secrets:
STAGING_HOST=YOUR_DROPLET_IP
STAGING_USER=root
STAGING_SSH_KEY=<paste contents of ~/.ssh/id_rsa>
STAGING_SSH_PORT=22

# For production (same values for single-droplet setup):
PRODUCTION_HOST=YOUR_DROPLET_IP
PRODUCTION_USER=root
PRODUCTION_SSH_KEY=<paste contents of ~/.ssh/id_rsa>
PRODUCTION_SSH_PORT=22

# Optional:
SLACK_WEBHOOK_URL=<your webhook>
NTFY_TOPIC=boardofone-alerts
```

### 7. Enable GitHub Container Registry (5 minutes)
```bash
# On GitHub:
# Settings → Developer settings → Personal access tokens
# Generate new token with write:packages, read:packages
# Copy token

# On droplet:
echo "YOUR_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### 8. First Deployment (10 minutes)
```bash
# On local machine:
git add .
git commit -m "feat: add CI/CD pipeline"
git push origin main

# This triggers staging deployment automatically!
# Check: GitHub → Actions tab
```

### Total Time: ~50 minutes

---

## What Happens on Git Push

### Push to Feature Branch
```bash
git push origin feature-branch
```
→ Runs CI tests (lint, typecheck, unit tests)
→ Must pass before merge allowed

### Push/Merge to Main
```bash
git push origin main
```
→ Runs full CI suite
→ Builds Docker images
→ Pushes to GitHub Container Registry
→ **Auto-deploys to staging** 🚀
→ Runs smoke tests
→ Notifies via Slack/ntfy.sh

### Manual Production Deploy
```bash
# In GitHub:
# Actions → Deploy to Production → Run workflow
# Type: "deploy-to-production" to confirm
# Click: Run workflow
```
→ Pre-deployment checks
→ Builds production images
→ **Blue-green deployment** (zero downtime)
→ Health checks (auto-rollback if failed)
→ Creates GitHub release
→ Notifies team

---

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│               DigitalOcean Droplet               │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────┐    ┌─────────────────────┐      │
│  │   Nginx    │───▶│  Frontend Container │      │
│  │  (SSL/TLS) │    │   (SvelteKit:3000)  │      │
│  │            │    └─────────────────────┘      │
│  │  Port 443  │                                  │
│  │  Port 80   │    ┌─────────────────────┐      │
│  │            │───▶│   API Container     │      │
│  └────────────┘    │  (FastAPI:8000)     │      │
│                    └─────────────────────┘      │
│                              │                   │
│         ┌────────────────────┴──────────┐       │
│         │                                │       │
│    ┌────▼────┐                    ┌─────▼────┐  │
│    │ PostgreSQL│                    │  Redis   │  │
│    │ (pgvector)│                    │  (cache) │  │
│    └──────────┘                    └──────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
         │                    ▲
         │  API Keys          │  Docker Images
         ▼                    │
   ┌─────────┐          ┌────┴──────┐
   │Anthropic│          │   GitHub  │
   │ Claude  │          │  Container│
   └─────────┘          │  Registry │
                        └───────────┘
```

---

## Security Features Implemented

✅ **SSL/TLS** - Let's Encrypt certificates
✅ **Rate Limiting** - nginx (10 req/s API, 2 req/min session creation)
✅ **Security Headers** - HSTS, CSP, X-Frame-Options
✅ **Firewall** - ufw (only 22, 80, 443 open)
✅ **Container Isolation** - Internal network, localhost-only ports
✅ **Input Validation** - All implemented in Week 6 (Day 42.5)
✅ **SQL Injection Protection** - Parameterized queries
✅ **XSS Prevention** - Input sanitization
✅ **Non-root Containers** - appuser (UID 1000)
✅ **Secrets Management** - .env files (not committed to git)
✅ **CORS Restrictions** - Domain whitelist only

---

## Monitoring & Alerts

### Built-in Health Checks
- API: `/api/health` (every 30s)
- Database: `/api/health/db`
- Redis: `/api/health/redis`
- Anthropic: `/api/health/anthropic`

### Automated Backups
- PostgreSQL: Daily at 2 AM (7-day retention)
- Redis: Daily at 2 AM (7-day retention)
- Location: `/opt/boardofone/backups/`

### Alert Channels (Optional)
- **Slack**: Deployment status, failures
- **ntfy.sh**: Mobile notifications for critical alerts
- Setup in GitHub Secrets: `SLACK_WEBHOOK_URL`, `NTFY_TOPIC`

---

## Cost Breakdown

### Infrastructure
- DigitalOcean Droplet (4GB): **$24/month**
- Domain (annual): **~$1/month**
- SSL (Let's Encrypt): **Free**

### API Usage (Estimated for Closed Beta)
- Anthropic Claude: **$50-200/month**
  - ~200 deliberations/month
  - ~$0.10-0.15 per deliberation
- Voyage AI Embeddings: **$5-10/month**
  - Research cache queries
  - ~$0.00006 per query

### Total: **~$80-240/month** for closed beta

### Scaling Plan
- 0-100 users: $24 droplet ✅ (current)
- 100-500 users: $48 droplet (8GB RAM)
- 500+ users: Load balancer + multiple droplets

---

## Testing the Pipeline

### Test CI (No Deployment)
```bash
git checkout -b test-ci
# Make a change
git commit -m "test: CI pipeline"
git push origin test-ci

# Check GitHub Actions → CI workflow
# Should pass lint, typecheck, tests
```

### Test Staging Deployment
```bash
git checkout main
git merge test-ci
git push origin main

# Check GitHub Actions → Deploy to Staging
# Should deploy to staging.boardofone.com
```

### Test Production Deployment
```bash
# In GitHub UI:
# Actions → Deploy to Production → Run workflow
# Requires manual confirmation: "deploy-to-production"
```

---

## Troubleshooting

### CI Fails: "Python dependency error"
```bash
# Locally, ensure uv.lock is up to date
uv sync
git add uv.lock
git commit -m "chore: update uv.lock"
git push
```

### Deployment Fails: "Cannot connect to droplet"
```bash
# Verify SSH key in GitHub Secrets
cat ~/.ssh/id_rsa | pbcopy  # macOS
# Paste into STAGING_SSH_KEY secret
```

### Deployment Fails: "Health check failed"
```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Check logs
cd /opt/boardofone
docker-compose -f docker-compose.prod.yml logs api

# Check .env file
cat .env | grep ANTHROPIC_API_KEY
# Should NOT be empty
```

### SSL Certificate Issues
```bash
# Check certificate status
certbot certificates

# Renew if needed
certbot renew --force-renewal

# Restart nginx
systemctl reload nginx
```

---

## Next Steps (After Deployment)

1. ✅ **Complete Week 7 Frontend** (Days 45-49)
   - Create Session Page
   - Real-time Deliberation View
   - Authentication Integration (optional for MVP)
   - Dashboard

2. ✅ **Invite Beta Users** (5-10 people)
   - Friends, colleagues, or online communities
   - Collect feedback via Google Form or Typeform

3. ✅ **Monitor & Iterate**
   - Watch logs: `docker-compose -f docker-compose.prod.yml logs -f`
   - Check costs: Anthropic usage dashboard
   - Fix bugs, improve UX

4. 📊 **Add Monitoring** (Week 9)
   - Prometheus + Grafana
   - Cost anomaly detection
   - Error rate tracking

5. 🚀 **Public Beta Launch**
   - Announce on Twitter, Reddit, HackerNews
   - Product Hunt launch
   - SEO optimization

---

## Resources

- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Roadmap**: [zzz_project/MVP_IMPLEMENTATION_ROADMAP.md](./zzz_project/MVP_IMPLEMENTATION_ROADMAP.md)
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **DigitalOcean Docs**: https://docs.digitalocean.com/
- **Let's Encrypt**: https://letsencrypt.org/

---

## Support

Questions or issues?
- Open GitHub Issue
- Check DEPLOYMENT_GUIDE.md
- Review GitHub Actions logs

**Good luck with your deployment tonight! 🚀**
