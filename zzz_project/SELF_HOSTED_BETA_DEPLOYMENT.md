# Self-Hosted Closed Beta Deployment Guide

Complete guide for deploying Board of One to Digital Ocean with **self-hosted Supabase GoTrue** and email whitelist for ~10 beta testers.

---

## Overview

**Architecture:**
- **Self-Hosted Supabase (GoTrue)** - OAuth auth server (runs in Docker)
- **PostgreSQL** - Your existing database (no Supabase cloud needed!)
- **Redis** - Session management
- **Email Whitelist** - Only approved emails can access
- **Digital Ocean Droplet** - Cloud hosting

**Key Difference from Cloud Supabase:**
- ✅ **No vendor lock-in** - You control everything
- ✅ **Lower costs** - No Supabase subscription needed
- ✅ **Full control** - Runs in your Docker stack
- ✅ **Same OAuth providers** - Google, GitHub, LinkedIn

---

## Prerequisites

- Digital Ocean account (or any VPS)
- Domain name (optional but recommended)
- Google OAuth credentials (for Google sign-in)
- SSH access to server

---

## Part 1: OAuth Provider Setup

### 1.1 Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google+ API**
4. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Fill in:
   - **Application type:** Web application
   - **Name:** Board of One Beta
   - **Authorized redirect URIs:**
     ```
     # Production
     https://auth.yourdomain.com/callback

     # Development (optional)
     http://localhost:9999/callback
     ```
6. Copy **Client ID** and **Client Secret**

### 1.2 GitHub OAuth (Optional)

1. Go to **GitHub Settings → Developer settings → OAuth Apps**
2. Click **"New OAuth App"**
3. Fill in:
   - **Application name:** Board of One Beta
   - **Homepage URL:** `https://yourdomain.com`
   - **Authorization callback URL:**
     ```
     https://auth.yourdomain.com/callback
     ```
4. Copy **Client ID** and generate **Client Secret**

---

## Part 2: Digital Ocean Droplet Setup

### 2.1 Create Droplet

1. Log in to Digital Ocean
2. Click **Create → Droplets**
3. Choose:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic ($12/month recommended for beta) - 2 GB RAM, 1 vCPU
   - **Datacenter:** Choose closest to your users
   - **Authentication:** SSH key (recommended)
4. Click **Create Droplet**

5. Note the droplet's IP address

### 2.2 Connect and Install Dependencies

```bash
# Connect to server
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Install Git
apt install git -y
```

### 2.3 Clone Repository

```bash
cd /opt
git clone https://github.com/yourusername/bo1.git
cd bo1
```

---

## Part 3: Environment Configuration

### 3.1 Generate JWT Secret

```bash
openssl rand -base64 32
```

Copy this output - you'll use it as `SUPABASE_JWT_SECRET`.

### 3.2 Create .env File

```bash
cp .env.example .env
nano .env
```

### 3.3 Configure Environment Variables

```bash
# =============================================================================
# LLM API Keys
# =============================================================================
ANTHROPIC_API_KEY=your_anthropic_api_key_here
VOYAGE_API_KEY=your_voyage_api_key_here

# =============================================================================
# PostgreSQL (Local Docker)
# =============================================================================
POSTGRES_PASSWORD=generate_secure_password_here
DATABASE_URL=postgresql://bo1:${POSTGRES_PASSWORD}@postgres:5432/boardofone

# =============================================================================
# Redis (Local Docker)
# =============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# =============================================================================
# Admin API
# =============================================================================
ADMIN_API_KEY=generate_admin_key_with_openssl_rand_hex_32

# =============================================================================
# SELF-HOSTED SUPABASE (GoTrue)
# =============================================================================
ENABLE_SUPABASE_AUTH=true  # Enable authentication

# GoTrue runs at http://localhost:9999 (or https://auth.yourdomain.com in production)
SUPABASE_URL=http://supabase-auth:9999
SUPABASE_JWT_SECRET=paste_jwt_secret_from_step_3.1_here

# Google OAuth (from Part 1.1)
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret

# GitHub OAuth (optional, from Part 1.2)
GITHUB_OAUTH_ENABLED=false
GITHUB_OAUTH_CLIENT_ID=your_github_client_id
GITHUB_OAUTH_CLIENT_SECRET=your_github_client_secret

# =============================================================================
# CLOSED BETA WHITELIST
# =============================================================================
CLOSED_BETA_MODE=true  # Restrict to whitelisted emails only

# Add your 10 beta testers' emails (comma-separated, case-insensitive)
BETA_WHITELIST=alice@example.com,bob@company.com,charlie@startup.io

# =============================================================================
# Site Configuration
# =============================================================================
SITE_URL=https://yourdomain.com  # Your frontend URL
CORS_ORIGINS=https://yourdomain.com
```

Save and exit (`Ctrl+X`, `Y`, `Enter`)

---

## Part 4: Add Supabase to Docker Compose

Your `docker-compose.yml` already has PostgreSQL and Redis. Now add GoTrue:

### 4.1 Edit docker-compose.yml

```bash
nano docker-compose.yml
```

### 4.2 Add GoTrue Service

Add this service to your `docker-compose.yml` (after the `api` service):

```yaml
  # ---------------------------------------------------------------------------
  # Supabase GoTrue: Self-hosted OAuth authentication server
  # ---------------------------------------------------------------------------
  supabase-auth:
    image: supabase/gotrue:latest
    container_name: bo1-supabase-auth
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      # Database
      - GOTRUE_DB_DRIVER=postgres
      - DATABASE_URL=${DATABASE_URL}

      # Site Configuration
      - GOTRUE_SITE_URL=${SITE_URL:-http://localhost:3000}
      - GOTRUE_URI_ALLOW_LIST=${SITE_URL:-http://localhost:3000}

      # JWT Configuration
      - GOTRUE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - GOTRUE_JWT_EXP=3600  # 1 hour
      - GOTRUE_JWT_DEFAULT_GROUP_NAME=authenticated

      # Auth Configuration
      - GOTRUE_DISABLE_SIGNUP=false
      - GOTRUE_MAILER_AUTOCONFIRM=true  # Auto-confirm emails (for beta)
      - API_EXTERNAL_URL=http://supabase-auth:9999

      # Google OAuth
      - GOTRUE_EXTERNAL_GOOGLE_ENABLED=${GOOGLE_OAUTH_ENABLED:-false}
      - GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}
      - GOTRUE_EXTERNAL_GOOGLE_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET}
      - GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI=https://auth.yourdomain.com/callback

      # GitHub OAuth (optional)
      - GOTRUE_EXTERNAL_GITHUB_ENABLED=${GITHUB_OAUTH_ENABLED:-false}
      - GOTRUE_EXTERNAL_GITHUB_CLIENT_ID=${GITHUB_OAUTH_CLIENT_ID}
      - GOTRUE_EXTERNAL_GITHUB_SECRET=${GITHUB_OAUTH_CLIENT_SECRET}
      - GOTRUE_EXTERNAL_GITHUB_REDIRECT_URI=https://auth.yourdomain.com/callback
    ports:
      - "9999:9999"
    networks:
      - bo1-network
    restart: unless-stopped
```

Save and exit.

---

## Part 5: Database Migration

### 5.1 Run Migrations

```bash
# Build containers
docker-compose build

# Start services
docker-compose up -d

# Run migrations to create beta_whitelist table
docker-compose exec api alembic upgrade head
```

This creates the `beta_whitelist` table and all auth-related tables.

---

## Part 6: Start Services

### 6.1 Start All Services

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps
```

You should see:
- `bo1-postgres` - Running
- `bo1-redis` - Running
- `bo1-api` - Running
- `bo1-supabase-auth` - Running

### 6.2 Verify GoTrue is Running

```bash
curl http://localhost:9999/health
```

Expected response:
```json
{
  "version": "2.x.x",
  "name": "GoTrue"
}
```

### 6.3 View Logs

```bash
# All services
docker-compose logs -f

# Just GoTrue
docker-compose logs -f supabase-auth

# Just API
docker-compose logs -f api
```

---

## Part 7: Domain + SSL Setup

### 7.1 Point Domain to Droplet

In your DNS provider (Cloudflare, Namecheap, etc.):

```
A    @       your-droplet-ip
A    auth    your-droplet-ip
A    api     your-droplet-ip
```

Wait for DNS propagation (5-10 minutes).

### 7.2 Install Nginx

```bash
apt install nginx -y
apt install certbot python3-certbot-nginx -y
```

### 7.3 Configure Nginx

Create three config files:

**API Reverse Proxy:**
```bash
nano /etc/nginx/sites-available/api
```

```nginx
server {
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Auth Reverse Proxy:**
```bash
nano /etc/nginx/sites-available/auth
```

```nginx
server {
    server_name auth.yourdomain.com;

    location / {
        proxy_pass http://localhost:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable sites:**
```bash
ln -s /etc/nginx/sites-available/api /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/auth /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 7.4 Get SSL Certificates

```bash
certbot --nginx -d api.yourdomain.com -d auth.yourdomain.com
```

Follow prompts. Certbot will auto-renew certificates.

---

## Part 8: Whitelist Management

### Option 1: Environment Variable (Static)

```bash
# Edit .env
nano /opt/bo1/.env

# Add emails to BETA_WHITELIST
BETA_WHITELIST=user1@example.com,user2@example.com,user3@example.com

# Restart services
docker-compose restart api supabase-auth
```

### Option 2: Admin API (Dynamic - Recommended)

```bash
# Add user (no restart needed!)
curl -X POST https://api.yourdomain.com/api/admin/beta-whitelist \
  -H "X-Admin-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "notes": "YC batch W25"}'

# List all beta users
curl -H "X-Admin-Key: your_admin_key" \
  https://api.yourdomain.com/api/admin/beta-whitelist

# Remove user
curl -X DELETE https://api.yourdomain.com/api/admin/beta-whitelist/olduser@example.com \
  -H "X-Admin-Key: your_admin_key"
```

---

## Part 9: Frontend Integration

### 9.1 Update Frontend Environment Variables

In your SvelteKit frontend (`.env`):

```bash
PUBLIC_API_URL=https://api.yourdomain.com
PUBLIC_SUPABASE_URL=https://auth.yourdomain.com
```

### 9.2 Frontend Auth Flow

Use `@supabase/supabase-js` to handle OAuth:

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://auth.yourdomain.com',
  'not-needed-for-oauth'  // No anon key needed for self-hosted
)

// Sign in with Google
await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: 'https://yourdomain.com/auth/callback'
  }
})
```

---

## Part 10: Testing

### 10.1 Test OAuth Flow

1. Go to `https://yourdomain.com/login`
2. Click **"Sign in with Google"**
3. Select Google account with whitelisted email
4. **Expected:** Redirect to auth.yourdomain.com → OAuth flow → Login successful

### 10.2 Test Whitelist Rejection

1. Sign in with non-whitelisted email
2. **Expected:** 403 error with message:
   ```json
   {
     "error": "closed_beta",
     "message": "Thanks for your interest! We're in closed beta..."
   }
   ```

### 10.3 Verify Services

```bash
# Check all containers
docker-compose ps

# Test API health
curl https://api.yourdomain.com/health

# Test GoTrue health
curl https://auth.yourdomain.com/health

# Check logs
docker-compose logs -f supabase-auth
```

---

## Troubleshooting

### Issue: GoTrue not starting

```bash
# Check logs
docker-compose logs supabase-auth

# Common issues:
# - DATABASE_URL wrong format
# - PostgreSQL not running
# - SUPABASE_JWT_SECRET missing
```

### Issue: OAuth redirect fails

**Solution:** Update OAuth provider redirect URIs to match `https://auth.yourdomain.com/callback`

### Issue: Whitelist not working

```bash
# Check whitelist entries
curl -H "X-Admin-Key: your_key" \
  https://api.yourdomain.com/api/admin/beta-whitelist

# Verify CLOSED_BETA_MODE=true
docker-compose exec api env | grep CLOSED_BETA
```

### Issue: "Invalid JWT" error

**Solution:** Verify `SUPABASE_JWT_SECRET` matches in both `.env` and GoTrue container

```bash
# Check GoTrue env vars
docker-compose exec supabase-auth env | grep JWT_SECRET
```

---

## Security Checklist

- [ ] Changed `ADMIN_API_KEY` from default
- [ ] Strong `POSTGRES_PASSWORD` set
- [ ] `SUPABASE_JWT_SECRET` is 32+ characters
- [ ] Firewall enabled: `ufw allow 22,80,443/tcp && ufw enable`
- [ ] SSL certificates installed (HTTPS only)
- [ ] `CLOSED_BETA_MODE=true` in production
- [ ] OAuth redirect URIs use HTTPS in production
- [ ] SSH key authentication (not password)

---

## Quick Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart after .env change
docker-compose restart api supabase-auth

# Add beta tester (dynamic)
curl -X POST https://api.yourdomain.com/api/admin/beta-whitelist \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -d '{"email": "user@example.com"}'

# Check GoTrue health
curl https://auth.yourdomain.com/health
```

---

## Cost Breakdown

**Digital Ocean Droplet:** $12/month (2 GB RAM)
**Domain:** ~$12/year
**SSL:** Free (Let's Encrypt)
**Supabase:** $0 (self-hosted!)

**Total:** ~$13/month

---

## Next Steps

1. Deploy frontend to Vercel/Netlify
2. Add monitoring (Sentry, LogRocket)
3. Set up automated backups
4. Configure email notifications (when ready to disable auto-confirm)
5. Add more OAuth providers (LinkedIn, etc.)

---

## When Ready to Open Beta

Just flip one flag:

```bash
# In .env
CLOSED_BETA_MODE=false

# Restart
docker-compose restart api
```

All users can now authenticate without whitelist check!
