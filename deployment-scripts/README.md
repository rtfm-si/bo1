# Deployment Scripts

Automated scripts for setting up and deploying Board of One to production with blue-green deployment support.

## Quick Start

**Complete deployment in 30 minutes** → See [../docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md](../docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md)

---

## Scripts Overview

### 1. `setup-production-server.sh` ⚙️

**Purpose:** One-time server setup (Docker, nginx, deploy user, firewall)

**Run on:** Production server (as root/sudo)

**Usage:**
```bash
# On production server
sudo bash setup-production-server.sh
```

**What it does:**
- ✅ Installs Docker + Docker Compose
- ✅ Installs nginx (host-level for blue-green)
- ✅ Creates `deploy` user with Docker permissions
- ✅ Configures sudo permissions for nginx commands
- ✅ Sets up deployment directory (`/opt/boardofone`)
- ✅ Clones git repository
- ✅ Configures nginx for blue-green switching
- ✅ Sets up firewall (UFW: ports 22, 80, 443)
- ✅ Creates SSL directory

**Time:** ~10 minutes

**Prerequisites:**
- Ubuntu 22.04 LTS server
- Root/sudo access
- Internet connection

---

### 2. `setup-github-ssh-keys.sh` 🔑

**Purpose:** Generate SSH keys for GitHub Actions deployment

**Run on:** Your local machine

**Usage:**
```bash
# On your local machine
bash deployment-scripts/setup-github-ssh-keys.sh
```

**What it does:**
- ✅ Generates ED25519 SSH key pair
- ✅ Saves to `~/.ssh/boardofone-deploy/`
- ✅ Provides step-by-step instructions for:
  - Adding public key to production server
  - Adding private key to GitHub secrets
  - Testing SSH connection

**Output files:**
- `~/.ssh/boardofone-deploy/id_ed25519` (private - for GitHub)
- `~/.ssh/boardofone-deploy/id_ed25519.pub` (public - for server)

**Time:** ~5 minutes

**Next steps:**
1. Copy public key to server: `/home/deploy/.ssh/authorized_keys`
2. Copy private key to GitHub secret: `PRODUCTION_SSH_KEY`
3. Test: `ssh -i ~/.ssh/boardofone-deploy/id_ed25519 deploy@SERVER_IP`

---

### 3. `verify-server-setup.sh` ✅

**Purpose:** Verify production server is correctly configured

**Run on:** Production server (as root/sudo)

**Usage:**
```bash
# On production server
bash /opt/boardofone/deployment-scripts/verify-server-setup.sh
```

**What it checks:**
- ✅ Docker installation and service status
- ✅ Nginx installation and configuration
- ✅ Deploy user exists with correct permissions
- ✅ Sudo permissions for nginx commands
- ✅ Deployment directory structure
- ✅ Nginx blue-green configs exist
- ✅ SSL certificate directory
- ✅ Firewall configuration (UFW)
- ✅ Environment file (.env)
- ✅ Docker access for deploy user

**Output:**
```
✓ Passed:   25
⚠ Warnings: 3
✗ Failed:   0

✓ Server is ready for deployment!
```

**Time:** ~1 minute

**When to run:**
- After `setup-production-server.sh`
- Before first deployment
- When troubleshooting deployment issues

---

### 4. ~~`generate-supabase-keys.js`~~ 🔐 (OBSOLETE)

**Status:** DEPRECATED - Removed in SuperTokens migration

**Replacement:** Use `openssl` to generate SuperTokens API key

**Usage:**
```bash
# Generate SuperTokens API key (32+ character random string)
openssl rand -base64 32
```

**What you need for SuperTokens:**
- `SUPERTOKENS_API_KEY` (32+ character random string)
- `POSTGRES_PASSWORD` (strong random password)
- `REDIS_PASSWORD` (strong random password)
- `ADMIN_API_KEY` (strong random key)

**Example:**
```bash
# Generate all required keys
openssl rand -base64 32  # For SUPERTOKENS_API_KEY
openssl rand -base64 24  # For POSTGRES_PASSWORD
openssl rand -base64 24  # For REDIS_PASSWORD
openssl rand -hex 32     # For ADMIN_API_KEY
```

---

## Complete Deployment Workflow

### 1️⃣ Initial Setup (One-Time)

```bash
# Step 1: Set up production server
ssh root@YOUR_SERVER_IP
sudo bash setup-production-server.sh

# Step 2: Generate SSH keys (on local machine)
bash deployment-scripts/setup-github-ssh-keys.sh

# Step 3: Add public key to server
ssh root@YOUR_SERVER_IP
echo "YOUR_PUBLIC_KEY" >> /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys

# Step 4: Add GitHub secrets
# Go to GitHub → Settings → Secrets → Actions
# Add: PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_SSH_KEY, PRODUCTION_SSH_PORT

# Step 5: Generate SuperTokens and other keys (on local machine)
openssl rand -base64 32  # For SUPERTOKENS_API_KEY
openssl rand -base64 24  # For POSTGRES_PASSWORD, REDIS_PASSWORD, ADMIN_API_KEY

# Step 6: Create .env on server
ssh deploy@YOUR_SERVER_IP
cd /opt/boardofone
cp .env.example .env
nano .env  # Add all secrets

# Step 7: Generate SSL certificate
sudo certbot --nginx -d boardof.one  # Let's Encrypt (recommended)
# OR
make generate-ssl  # Self-signed (testing only)

# Step 8: Verify setup
bash /opt/boardofone/deployment-scripts/verify-server-setup.sh
```

### 2️⃣ Deploy

```bash
# Go to GitHub Actions tab
# Run "Deploy to Production" workflow
# Type "deploy-to-production" to confirm

# Deployment takes 8-10 minutes:
# ✅ Build images
# ✅ Push to registry
# ✅ Start green environment
# ✅ Health checks
# ✅ Database migrations
# ✅ Traffic cutover (blue → green)
# ✅ Monitor for errors
# ✅ Promote green to blue
```

### 3️⃣ Verify

```bash
# Test endpoints
curl https://boardof.one/api/health
curl https://boardof.one/api/health/db
curl https://boardof.one/api/health/redis

# Check container status
ssh deploy@YOUR_SERVER_IP
docker ps

# View logs
docker-compose -f /opt/boardofone/docker-compose.prod.yml logs -f
```

---

## Troubleshooting

### Server Setup Failed

**Check logs:**
```bash
# View last 50 lines of system log
journalctl -xe | tail -50

# Check if services are running
systemctl status docker
systemctl status nginx
```

**Common issues:**
- Docker installation failed → Check internet connection
- Nginx config invalid → Run `sudo nginx -t`
- Deploy user creation failed → User may already exist

### SSH Connection Failed

**Test connection:**
```bash
# From local machine
ssh -i ~/.ssh/boardofone-deploy/id_ed25519 deploy@YOUR_SERVER_IP -v

# Check SSH debug output for errors
```

**Common issues:**
- Public key not in `authorized_keys` → Re-add with correct permissions
- Private key not in GitHub secrets → Copy entire file including BEGIN/END
- Firewall blocking port 22 → Check `sudo ufw status`

### Verification Failed

**Re-run with verbose output:**
```bash
bash /opt/boardofone/deployment-scripts/verify-server-setup.sh 2>&1 | tee verify.log
```

**Fix common issues:**
```bash
# Fix nginx config
sudo nginx -t  # Check what's wrong
sudo nano /etc/nginx/sites-enabled/boardofone.conf

# Fix deploy user permissions
sudo usermod -aG docker deploy
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# Fix directory ownership
sudo chown -R deploy:deploy /opt/boardofone
```

### Deployment Failed

**Check GitHub Actions logs:**
1. Go to Actions tab
2. Click failed workflow run
3. Expand failed step
4. View error message

**Common issues:**
- SSH connection failed → Check GitHub secrets
- Health check timeout → Check container logs
- Nginx config invalid → Verify nginx-blue.conf and nginx-green.conf exist
- Database migration failed → Check .env variables

---

## File Permissions Reference

**Critical permissions:**

```bash
# SSH directory and keys
/home/deploy/.ssh/                      # 700 (drwx------)
/home/deploy/.ssh/authorized_keys       # 600 (-rw-------)

# Deployment directory
/opt/boardofone/                        # 755 (drwxr-xr-x) owner: deploy
/opt/boardofone/.env                    # 600 (-rw-------) owner: deploy

# Nginx configs
/etc/nginx/sites-enabled/               # 755 (drwxr-xr-x)
/etc/nginx/sites-enabled/boardofone.conf # 644 (-rw-r--r--)

# SSL certificates
/etc/nginx/ssl/                         # 755 (drwxr-xr-x)
/etc/nginx/ssl/boardofone.crt           # 644 (-rw-r--r--)
/etc/nginx/ssl/boardofone.key           # 600 (-rw-------)

# Sudoers
/etc/sudoers.d/deploy-nginx             # 440 (-r--r-----)
```

---

## Environment Variables Reference

**Required in .env:**

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...
VOYAGE_API_KEY=pa-...
TAVILY_API_KEY=tvly-...
BRAVE_API_KEY=BSA...

# Database
POSTGRES_PASSWORD=<strong_random_password>
DATABASE_URL=postgresql://bo1:<POSTGRES_PASSWORD>@postgres:5432/boardofone

# Redis
REDIS_PASSWORD=<strong_random_password>

# SuperTokens Auth
SUPERTOKENS_API_KEY=<32_char_random_key>
SUPERTOKENS_CONNECTION_URI=http://supertokens:3567
SUPERTOKENS_API_DOMAIN=https://api.boardof.one
SUPERTOKENS_WEBSITE_DOMAIN=https://boardof.one
COOKIE_SECURE=true
COOKIE_DOMAIN=.boardof.one

# OAuth (Google)
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=<from_google_cloud_console>
GOOGLE_OAUTH_CLIENT_SECRET=<from_google_cloud_console>

# Closed Beta
CLOSED_BETA_MODE=true
BETA_WHITELIST=<comma_separated_emails>

# Admin
ADMIN_API_KEY=<strong_random_key>

# Site
SITE_URL=https://boardof.one
CORS_ORIGINS=https://boardof.one

# Production
DEBUG=false
LOG_LEVEL=INFO
```

**Required in GitHub Secrets:**

- `PRODUCTION_HOST` - Server IP or domain
- `PRODUCTION_USER` - Deploy username (default: deploy)
- `PRODUCTION_SSH_KEY` - Private SSH key (entire file)
- `PRODUCTION_SSH_PORT` - SSH port (default: 22)
- `GITHUB_TOKEN` - Auto-provided by GitHub Actions

---

## Documentation

- **Quickstart Guide:** [../docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md](../docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md)
- **Blue-Green Details:** [../docs/BLUE_GREEN_DEPLOYMENT.md](../docs/BLUE_GREEN_DEPLOYMENT.md)
- **Project Commands:** [../CLAUDE.md](../CLAUDE.md)

---

## Security Notes

🔒 **Never commit these to git:**
- Private SSH keys
- .env files with real secrets
- SSL private keys
- Database passwords

✅ **Only commit:**
- Setup scripts (this directory)
- nginx configs (public upstream definitions)
- .env.example (template with placeholders)
- Documentation

---

## Support

**Issues?** Check:
1. Verification script output
2. GitHub Actions logs
3. Server logs: `docker-compose logs -f`
4. Nginx logs: `/var/log/nginx/boardofone-*.log`

**Still stuck?** Open a GitHub issue with:
- Output from `verify-server-setup.sh`
- GitHub Actions workflow logs
- Server logs from time of failure
