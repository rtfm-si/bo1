# Board of One - Deployment Guide

Complete guide for deploying Board of One to DigitalOcean with GitHub Actions CI/CD.

## Prerequisites

### 1. Accounts & Services

- **DigitalOcean Account**: [Sign up](https://www.digitalocean.com/)
- **GitHub Account**: Repository with Actions enabled
- **Domain Name**: boardofone.com (configure DNS)
- **Anthropic API Key**: [Get key](https://console.anthropic.com/)
- **Voyage AI API Key**: [Get key](https://www.voyageai.com/) (optional for embeddings)

### 2. Local Setup

```bash
# Install required tools
brew install docker docker-compose  # macOS
# or
apt-get install docker docker-compose  # Linux

# Install GitHub CLI (optional but recommended)
brew install gh
gh auth login
```

---

## Part 1: DigitalOcean Droplet Setup

### Step 1: Create Droplet

1. Go to [DigitalOcean Console](https://cloud.digitalocean.com/)
2. Click "Create" → "Droplets"
3. Choose configuration:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic ($24/month - 4GB RAM, 2 vCPUs, 80GB SSD)
   - **Datacenter**: Choose closest to your users
   - **Authentication**: SSH key (create if needed)
   - **Hostname**: boardofone-prod
4. Click "Create Droplet"
5. Note the IP address (e.g., 123.456.789.0)

### Step 2: Configure DNS

1. Go to your domain registrar (Namecheap, Cloudflare, etc.)
2. Add A records:
   ```
   A     boardofone.com        → 123.456.789.0
   A     www.boardofone.com    → 123.456.789.0
   A     staging.boardofone.com → 123.456.789.0
   ```
3. Wait for DNS propagation (5-30 minutes)
4. Verify: `dig boardofone.com` or `nslookup boardofone.com`

### Step 3: SSH into Droplet

```bash
# Copy your SSH key to DigitalOcean if not done during creation
ssh-copy-id root@123.456.789.0

# SSH into droplet
ssh root@123.456.789.0
```

### Step 4: Run Setup Script

```bash
# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/yourusername/bo1/main/deployment-scripts/setup-droplet.sh | bash

# Or manually:
git clone https://github.com/yourusername/bo1.git /opt/boardofone
cd /opt/boardofone
chmod +x deployment-scripts/setup-droplet.sh
./deployment-scripts/setup-droplet.sh
```

### Step 5: Configure Environment Variables

```bash
cd /opt/boardofone

# Copy template and edit
cp .env.production.example .env.production
nano .env.production

# Set these values:
# - POSTGRES_PASSWORD (generate: openssl rand -base64 32)
# - ADMIN_API_KEY (generate: openssl rand -base64 32)
# - ANTHROPIC_API_KEY (from Anthropic console)
# - VOYAGE_API_KEY (from Voyage AI)
# - CORS_ORIGINS (your domain)
# - PUBLIC_API_URL (your domain)

# Copy to .env
cp .env.production .env
```

### Step 6: Setup SSL with Let's Encrypt

```bash
# Install certbot if not already installed
apt-get install -y certbot python3-certbot-nginx

# Obtain SSL certificate
certbot --nginx -d boardofone.com -d www.boardofone.com -d staging.boardofone.com

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose redirect HTTP → HTTPS (option 2)

# Auto-renewal is setup automatically
# Test renewal: certbot renew --dry-run
```

---

## Part 2: GitHub Actions Setup

### Step 1: Configure GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add the following secrets:

#### Staging Secrets
```
STAGING_HOST=123.456.789.0
STAGING_USER=root
STAGING_SSH_KEY=<contents of ~/.ssh/id_rsa>
STAGING_SSH_PORT=22
```

#### Production Secrets
```
PRODUCTION_HOST=123.456.789.0
PRODUCTION_USER=root
PRODUCTION_SSH_KEY=<contents of ~/.ssh/id_rsa>
PRODUCTION_SSH_PORT=22
```

#### Optional Secrets
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
NTFY_TOPIC=boardofone-alerts
CODECOV_TOKEN=<from codecov.io>
```

#### Get SSH Key Contents

```bash
# On your local machine
cat ~/.ssh/id_rsa

# Copy the entire output (including BEGIN and END lines)
# Paste into GitHub secret STAGING_SSH_KEY
```

### Step 2: Enable GitHub Container Registry

```bash
# Create Personal Access Token
# Go to: GitHub → Settings → Developer settings → Personal access tokens
# Click "Generate new token (classic)"
# Scopes: write:packages, read:packages, delete:packages
# Copy token (you'll only see it once)

# On droplet, login to GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

# Test pull
docker pull ghcr.io/yourusername/bo1/api:staging-latest
```

### Step 3: Update Workflow Files

Edit `.github/workflows/deploy-staging.yml` and `.github/workflows/deploy-production.yml`:

Replace:
```yaml
IMAGE_NAME_API: ${{ github.repository }}/api
IMAGE_NAME_FRONTEND: ${{ github.repository }}/frontend
```

With your repository path:
```yaml
IMAGE_NAME_API: yourusername/bo1/api
IMAGE_NAME_FRONTEND: yourusername/bo1/frontend
```

### Step 4: Test CI Pipeline

```bash
# On local machine
git add .
git commit -m "feat: setup CI/CD pipeline"
git push origin main

# Check GitHub Actions tab
# All tests should pass
```

---

## Part 3: First Deployment

### Option A: Automatic (via GitHub Actions)

```bash
# Push to main branch triggers staging deployment
git push origin main

# Check GitHub Actions → Deploy to Staging
# Should complete in 5-10 minutes

# Verify staging deployment
curl https://staging.boardofone.com/api/health
```

### Option B: Manual (for testing)

```bash
# On local machine
export DROPLET_IP=123.456.789.0
./deployment-scripts/deploy-manual.sh

# Follow prompts
```

### Verify Deployment

```bash
# SSH into droplet
ssh root@123.456.789.0

# Check running containers
cd /opt/boardofone
docker-compose -f docker-compose.prod.yml ps

# Should see:
# - boardofone-postgres (healthy)
# - boardofone-redis (healthy)
# - boardofone-api (healthy)
# - boardofone-frontend (healthy)

# Check logs
docker-compose -f docker-compose.prod.yml logs -f api

# Test API
curl http://localhost:8000/api/health
# Should return: {"status": "healthy"}

# Test externally
curl https://boardofone.com/api/health
```

---

## Part 4: Production Deployment

### Manual Production Deploy

1. Go to GitHub → Actions
2. Select "Deploy to Production" workflow
3. Click "Run workflow"
4. Enter confirmation: `deploy-to-production`
5. Click "Run workflow"
6. Monitor deployment (10-15 minutes)

### Blue-Green Deployment Process

The production deployment uses blue-green strategy:

1. **Build**: New Docker images built and pushed to registry
2. **Pre-checks**: Verify staging health, all tests passed
3. **Deploy Green**: Start new containers alongside old ones
4. **Health Check**: Verify green environment is healthy
5. **Traffic Cutover**: Nginx switches to green containers
6. **Monitor**: Watch for 2 minutes for errors
7. **Shutdown Blue**: Stop old containers if green is stable
8. **Rollback**: If issues, instant rollback to blue

### Rollback Procedure

If deployment fails or issues detected:

```bash
# SSH into droplet
ssh root@123.456.789.0
cd /opt/boardofone

# List running containers
docker ps

# If green deployment is running but broken, switch back to blue
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone
sudo nginx -t && sudo systemctl reload nginx

# Stop green
docker-compose -f docker-compose.prod.yml -p boardofone-green down

# Restart blue (previous version)
docker-compose -f docker-compose.prod.yml up -d
```

---

## Part 5: Monitoring & Maintenance

### View Logs

```bash
# SSH into droplet
ssh root@123.456.789.0
cd /opt/boardofone

# Follow all logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific service logs
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f postgres

# View nginx logs
tail -f /var/log/nginx/boardofone-access.log
tail -f /var/log/nginx/boardofone-error.log
```

### Health Checks

```bash
# API health
curl https://boardofone.com/api/health

# Database health
curl https://boardofone.com/api/health/db

# Redis health
curl https://boardofone.com/api/health/redis

# Anthropic API health
curl https://boardofone.com/api/health/anthropic
```

### Backups

```bash
# Backups run automatically at 2 AM daily
# Location: /opt/boardofone/backups/

# Manual backup
cd /opt/boardofone
./deployment-scripts/backup.sh

# List backups
ls -lh /opt/boardofone/backups/postgres/
ls -lh /opt/boardofone/backups/redis/

# Restore from backup
docker exec boardofone-postgres psql -U boardofone -d boardofone < backups/postgres/backup_20250117_020000.sql.gz
```

### Database Migrations

```bash
# SSH into droplet
ssh root@123.456.789.0
cd /opt/boardofone

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Check current version
docker-compose -f docker-compose.prod.yml exec api alembic current

# Rollback one version
docker-compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

---

## Troubleshooting

### Issue: API not responding

```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check API logs
docker-compose -f docker-compose.prod.yml logs api

# Restart API
docker-compose -f docker-compose.prod.yml restart api
```

### Issue: Database connection failed

```bash
# Check postgres status
docker-compose -f docker-compose.prod.yml ps postgres

# Check postgres logs
docker-compose -f docker-compose.prod.yml logs postgres

# Verify DATABASE_URL in .env
grep DATABASE_URL .env

# Test connection
docker-compose -f docker-compose.prod.yml exec postgres psql -U boardofone -d boardofone -c "SELECT 1;"
```

### Issue: SSL certificate errors

```bash
# Check certificate expiry
certbot certificates

# Renew certificate
certbot renew

# Force renewal
certbot renew --force-renewal

# Test nginx config
nginx -t
```

### Issue: Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker images
docker system prune -a -f

# Clean old backups (older than 30 days)
find /opt/boardofone/backups -mtime +30 -delete

# Clean logs
truncate -s 0 /var/log/nginx/*.log
```

---

## Security Checklist

- [ ] Strong passwords in `.env` (min 32 characters)
- [ ] SSH key authentication only (disable password login)
- [ ] Firewall enabled (ufw) - only ports 22, 80, 443 open
- [ ] SSL/TLS certificates installed (Let's Encrypt)
- [ ] Regular backups enabled (daily at 2 AM)
- [ ] Log rotation configured
- [ ] fail2ban installed (optional but recommended)
- [ ] Security updates enabled: `apt-get install unattended-upgrades`
- [ ] Rate limiting enabled in nginx
- [ ] CORS properly configured
- [ ] Admin API key changed from default

---

## Performance Tuning

### Database Connection Pool

Edit `.env`:
```bash
DB_POOL_SIZE=20  # Adjust based on traffic
DB_MAX_OVERFLOW=10
```

### Uvicorn Workers

Edit `.env`:
```bash
UVICORN_WORKERS=4  # 2-4 per CPU core
```

### Redis Memory Limit

Edit `docker-compose.prod.yml`:
```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Nginx Caching

Already configured in `nginx/nginx.conf` for static assets (1 day cache).

---

## Monitoring Setup (Optional)

### Setup Prometheus + Grafana

```bash
# Add to docker-compose.prod.yml
# (Full configuration in Week 9 roadmap)

# Access Grafana: https://boardofone.com:3001
# Default login: admin/admin
```

### Setup ntfy.sh Alerts

```bash
# Add to .env
NTFY_TOPIC=boardofone-alerts

# Test alert
curl -H "Title: Test Alert" -d "This is a test" https://ntfy.sh/boardofone-alerts

# Subscribe on mobile: https://ntfy.sh/boardofone-alerts
```

---

## Cost Estimation

**Monthly Costs:**
- DigitalOcean Droplet (4GB): $24/month
- Domain name: $10-15/year (~$1/month)
- SSL (Let's Encrypt): Free
- Anthropic API: Variable (~$50-200/month for closed beta)
- Voyage AI Embeddings: ~$5-10/month
- **Total: ~$80-240/month**

**Scaling Plan:**
- 0-100 users: Single $24 droplet (current setup)
- 100-500 users: Upgrade to $48 droplet (8GB RAM)
- 500+ users: Load balancer + multiple app servers

---

## Next Steps

1. ✅ Complete Week 7 frontend (Days 45-49)
2. ✅ Deploy to staging
3. ✅ Invite 5-10 beta testers
4. ✅ Monitor, fix bugs, iterate
5. ✅ Production deployment
6. 📊 Add monitoring (Week 9)
7. 📧 Add email notifications (Week 12)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/bo1/issues
- Documentation: https://boardofone.com/docs
- Email: support@boardofone.com
