# Production Deployment Quickstart

This guide walks you through deploying Board of One to production with blue-green deployment support in **under 30 minutes**.

## Prerequisites

- ☐ Ubuntu 22.04 LTS server (2GB RAM minimum, 4GB recommended)
- ☐ Domain name pointing to your server (e.g., boardof.one)
- ☐ GitHub repository with Board of One code
- ☐ Root/sudo access to the server

---

## Step 1: Server Setup (10 minutes)

### 1.1 SSH into Your Server

```bash
ssh root@YOUR_SERVER_IP
```

### 1.2 Run Automated Setup Script

```bash
# Download and run the setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/bo1/main/deployment-scripts/setup-production-server.sh -o setup.sh

# Review the script (optional but recommended)
less setup.sh

# Run it
sudo bash setup.sh
```

**What this does:**
- ✅ Installs Docker + Docker Compose
- ✅ Installs nginx (host-level for blue-green)
- ✅ Creates deploy user with Docker permissions
- ✅ Sets up deployment directory (`/opt/boardofone`)
- ✅ Configures nginx for blue-green deployment
- ✅ Sets up firewall (ports 22, 80, 443)

**Expected output:**
```
✓ Production Server Setup Complete!
```

### 1.3 Verify Setup

```bash
bash /opt/boardofone/deployment-scripts/verify-server-setup.sh
```

All checks should pass (warnings are OK).

---

## Step 2: SSH Keys for GitHub Actions (5 minutes)

### 2.1 Generate SSH Keys (on your local machine)

```bash
cd /path/to/bo1
bash deployment-scripts/setup-github-ssh-keys.sh
```

This creates:
- Private key: `~/.ssh/boardofone-deploy/id_ed25519` (for GitHub)
- Public key: `~/.ssh/boardofone-deploy/id_ed25519.pub` (for server)

### 2.2 Add Public Key to Server

```bash
# Copy public key
cat ~/.ssh/boardofone-deploy/id_ed25519.pub

# SSH into server
ssh root@YOUR_SERVER_IP

# Add to authorized_keys
echo "PASTE_PUBLIC_KEY_HERE" >> /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
```

### 2.3 Test SSH Connection

```bash
# From your local machine
ssh -i ~/.ssh/boardofone-deploy/id_ed25519 deploy@YOUR_SERVER_IP

# Should connect without password
# Type 'exit' to disconnect
```

---

## Step 3: GitHub Secrets (5 minutes)

### 3.1 Go to GitHub Repository Settings

1. Navigate to: `https://github.com/YOUR_USERNAME/bo1/settings/secrets/actions`
2. Click **"New repository secret"**

### 3.2 Add These Secrets

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `PRODUCTION_HOST` | `YOUR_SERVER_IP` or `boardof.one` | Your server's IP address or domain |
| `PRODUCTION_USER` | `deploy` | Default deploy user |
| `PRODUCTION_SSH_KEY` | `<contents of private key>` | `cat ~/.ssh/boardofone-deploy/id_ed25519` |
| `PRODUCTION_SSH_PORT` | `22` | Default SSH port |

**For `PRODUCTION_SSH_KEY`:**

```bash
# Copy private key (entire file including BEGIN/END lines)
cat ~/.ssh/boardofone-deploy/id_ed25519

# Paste the entire output into GitHub secret
```

---

## Step 4: SSL Certificates (Automated)

**No action required!** ✅

SSL certificates are now **automatically obtained during deployment**:

1. **First Deployment**: GitHub Actions workflow will:
   - Detect that no Let's Encrypt certificate exists
   - Run `deployment-scripts/setup-letsencrypt.sh`
   - Obtain certificate from Let's Encrypt via certbot
   - Configure nginx to use the certificate

2. **Auto-Renewal**: Certbot timer automatically renews certificates every 60 days

3. **Result**: Production-grade HTTPS with no browser warnings

**What you need to ensure:**
- ☐ Domain `boardof.one` points to your server IP (DNS A record)
- ☐ Port 80 is open (required for Let's Encrypt HTTP challenge)
- ☐ Certbot is installed on server (done by setup-production-server.sh)

**Manual Setup (Optional)**

If you want to set up Let's Encrypt before deployment:

```bash
# SSH into server
ssh deploy@YOUR_SERVER_IP
cd /opt/boardofone

# Run Let's Encrypt setup script
sudo bash deployment-scripts/setup-letsencrypt.sh
```

This obtains:
- Certificate: `/etc/letsencrypt/live/boardof.one/fullchain.pem`
- Private key: `/etc/letsencrypt/live/boardof.one/privkey.pem`
- Auto-renewal via certbot.timer service

---

## Step 5: Environment Configuration (5 minutes)

### 5.1 Create Production .env File

```bash
# SSH into server
ssh deploy@YOUR_SERVER_IP
cd /opt/boardofone

# Copy example .env
cp .env.example .env

# Edit with production values
nano .env
```

### 5.2 Required Environment Variables

**Critical values to set:**

```bash
# API Keys (get from providers)
ANTHROPIC_API_KEY=sk-ant-api03-...
VOYAGE_API_KEY=pa-...
TAVILY_API_KEY=tvly-...
BRAVE_API_KEY=BSA...

# Database (generate strong passwords)
POSTGRES_PASSWORD=<strong_random_password>
DATABASE_URL=postgresql://bo1:<POSTGRES_PASSWORD>@postgres:5432/boardofone

# Redis
REDIS_PASSWORD=<strong_random_password>

# Supabase Auth (generate with deployment-scripts/generate-supabase-keys.js)
SUPABASE_JWT_SECRET=<64_char_secret>
SUPABASE_ANON_KEY=<jwt_token>
SUPABASE_SERVICE_ROLE_KEY=<jwt_token>
SUPABASE_URL=http://supabase-auth:9999

# Admin API
ADMIN_API_KEY=<strong_random_key>

# Site Configuration
SITE_URL=https://boardof.one
CORS_ORIGINS=https://boardof.one

# Production Settings
DEBUG=false
LOG_LEVEL=INFO
ENABLE_SUPABASE_AUTH=true
CLOSED_BETA_MODE=true
```

**Generate Supabase keys:**

```bash
# On your local machine (requires Node.js)
cd /path/to/bo1
node deployment-scripts/generate-supabase-keys.js

# Copy the generated values to .env on server
```

### 5.3 Save and Exit

```
# In nano:
Ctrl+O (save)
Enter (confirm)
Ctrl+X (exit)
```

---

## Step 6: First Deployment (5 minutes)

### 6.1 Trigger Deployment from GitHub

1. Go to: `https://github.com/YOUR_USERNAME/bo1/actions`
2. Click **"Deploy to Production"** workflow
3. Click **"Run workflow"** button
4. Type: `deploy-to-production` (confirmation)
5. Click **"Run workflow"** (green button)

### 6.2 Watch Deployment Progress

**GitHub Actions will:**
1. ✅ Validate confirmation
2. ✅ Check staging health (may fail on first run - that's OK)
3. ✅ Build Docker images
4. ✅ Push to GitHub Container Registry
5. ✅ SSH into production server
6. ✅ Start green environment
7. ✅ Run health checks
8. ✅ Run database migrations
9. ✅ Switch nginx to green
10. ✅ Monitor for 2 minutes
11. ✅ Promote green to blue
12. ✅ Create GitHub release

**Expected time:** 8-10 minutes

### 6.3 Verify Deployment

```bash
# Test from your machine
curl https://boardof.one/api/health

# Expected response:
# {"status":"healthy","timestamp":"..."}

# Check database
curl https://boardof.one/api/health/db

# Check Redis
curl https://boardof.one/api/health/redis
```

---

## Step 7: Post-Deployment Verification

### 7.1 Check Running Containers

```bash
# SSH into server
ssh deploy@YOUR_SERVER_IP

# View running containers
docker ps

# Expected output:
# - bo1-postgres-prod
# - bo1-redis-prod
# - bo1-supabase-auth-prod
# - bo1-api-prod
# - bo1-frontend-prod
# - bo1-nginx-prod
# - bo1-app-prod
```

### 7.2 View Logs

```bash
# All services
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f --tail=50

# Just API
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f api

# Just frontend
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f frontend
```

### 7.3 Check Nginx Status

```bash
# Which environment is active?
cat /etc/nginx/sites-enabled/boardofone.conf | grep "upstream.*backend"

# Expected: api_backend_blue (after first deployment)
```

### 7.4 Test in Browser

1. Navigate to: `https://boardof.one`
2. You should see the Board of One landing page
3. Try logging in (if auth is configured)

---

## Troubleshooting

### Deployment Failed: Health Check Timeout

**Problem:** Green environment containers didn't start in time.

**Solution:**
```bash
# SSH into server
ssh deploy@YOUR_SERVER_IP

# Check container status
docker ps -a | grep boardofone

# View logs for failed container
docker logs boardofone-green-api-1

# Common issues:
# - Missing .env variables
# - Database connection failed (check POSTGRES_PASSWORD)
# - Redis connection failed (check REDIS_PASSWORD)
```

### Deployment Failed: Nginx Configuration Invalid

**Problem:** nginx-blue.conf or nginx-green.conf has syntax errors.

**Solution:**
```bash
# Test nginx config
sudo nginx -t

# View error details
sudo nginx -t 2>&1

# Fix config file
sudo nano /opt/boardofone/nginx/nginx-blue.conf

# Test again
sudo nginx -t
```

### SSH Connection Failed from GitHub Actions

**Problem:** GitHub Actions can't SSH into server.

**Check:**
1. Public key added to `/home/deploy/.ssh/authorized_keys`?
2. Correct permissions (600)?
3. Firewall allows port 22?
4. Private key in GitHub secrets matches public key on server?

**Test manually:**
```bash
# From local machine
ssh -i ~/.ssh/boardofone-deploy/id_ed25519 deploy@YOUR_SERVER_IP

# If this works, GitHub Actions should work too
```

### SSL Certificate Warnings

**Problem:** Browser shows "Not secure" warning.

**Solution:**
1. Make sure you used Let's Encrypt (not self-signed)
2. Check certificate paths in nginx config
3. Verify domain DNS points to server

```bash
# Test SSL certificate
openssl s_client -connect boardof.one:443 -servername boardof.one

# Check expiration
echo | openssl s_client -connect boardof.one:443 2>/dev/null | openssl x509 -noout -dates
```

---

## Next Deployments

After the initial setup, future deployments are easy:

1. **Push code to main branch**
2. **Go to GitHub Actions**
3. **Run "Deploy to Production"**
4. **Type confirmation**
5. **Wait 8-10 minutes**

Blue-green deployment handles everything automatically:
- ✅ Zero downtime
- ✅ Automatic health checks
- ✅ Automatic rollback if errors detected
- ✅ Active sessions preserved

---

## Monitoring & Maintenance

### View Active Sessions

```bash
# SSH into server
ssh deploy@YOUR_SERVER_IP

# Check Redis for active sessions
docker exec -it bo1-redis-prod redis-cli -a $REDIS_PASSWORD

# In redis-cli:
KEYS session:*
```

### Database Backups

```bash
# Backup PostgreSQL
docker exec bo1-postgres-prod pg_dump -U bo1 boardofone > backup-$(date +%Y%m%d).sql

# Restore from backup
cat backup-20250118.sql | docker exec -i bo1-postgres-prod psql -U bo1 boardofone
```

### Redis Backups

```bash
cd /opt/boardofone
make backup-redis

# Backups saved to: ./backups/
```

### View Metrics

```bash
# Container resource usage
docker stats

# Nginx access logs
sudo tail -f /var/log/nginx/boardofone-blue-access.log

# Nginx error logs
sudo tail -f /var/log/nginx/boardofone-blue-error.log
```

---

## Security Checklist

After deployment, verify:

- [ ] Firewall is active (`sudo ufw status`)
- [ ] Only ports 22, 80, 443 are open
- [ ] SSH password authentication disabled (key-only)
- [ ] Strong passwords in .env (30+ characters)
- [ ] HTTPS enabled (Let's Encrypt certificate)
- [ ] Admin API key is strong (not `admin123`)
- [ ] Closed beta mode enabled (if not ready for public)
- [ ] Supabase JWT secret is 64+ characters
- [ ] Database not exposed to public (127.0.0.1 only)
- [ ] Redis password protected

---

## Quick Reference Commands

```bash
# Deploy from GitHub Actions
# (Go to Actions tab → Deploy to Production → Run workflow)

# SSH into server
ssh deploy@YOUR_SERVER_IP

# View logs
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f

# Restart services
docker-compose -f /opt/boardofone/docker-compose.prod.yml restart

# Stop all services
docker-compose -f /opt/boardofone/docker-compose.prod.yml down

# Start all services
docker-compose -f /opt/boardofone/docker-compose.prod.yml up -d

# Check which environment is active
cat /etc/nginx/sites-enabled/boardofone.conf | grep upstream

# Manual rollback to blue
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
sudo nginx -t && sudo systemctl reload nginx

# View container status
docker ps

# Backup database
docker exec bo1-postgres-prod pg_dump -U bo1 boardofone > backup.sql

# Backup Redis
cd /opt/boardofone && make backup-redis
```

---

## Success!

Your production deployment is complete. 🎉

**Your site is now live at:** `https://boardof.one`

For detailed blue-green deployment flow, see: [docs/BLUE_GREEN_DEPLOYMENT.md](./BLUE_GREEN_DEPLOYMENT.md)

For troubleshooting, check GitHub Actions logs or server logs:
```bash
ssh deploy@YOUR_SERVER_IP
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f
```

**Questions?** Open an issue on GitHub or check the deployment logs.
