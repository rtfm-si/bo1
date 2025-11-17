# Closed Beta Deployment Guide

Complete guide for deploying Board of One to Digital Ocean with Supabase OAuth and email whitelist access control for ~10 beta testers.

---

## Overview

This guide configures:
- **Supabase OAuth** - Social login (Google, GitHub, LinkedIn)
- **Email Whitelist** - Only approved emails can access the platform
- **Digital Ocean Droplet** - Cloud hosting
- **PostgreSQL + Redis** - Database and session management

**User Experience:**
1. User clicks "Sign in with Google"
2. Supabase handles OAuth flow
3. Backend checks: Is email whitelisted?
   - ✅ Yes → Grant access
   - ❌ No → Show "Join waitlist" message
4. User accesses full platform

---

## Prerequisites

- Digital Ocean account
- Supabase account (free tier works)
- Domain name (optional but recommended)
- Google OAuth credentials (for Google sign-in)

---

## Part 1: Self-Hosted Supabase Setup

Board of One uses **self-hosted Supabase (GoTrue)** for authentication - no vendor lock-in, full control!

### 1.1 Generate JWT Secret

On your local machine or server:

```bash
openssl rand -base64 32
```

Copy this output - you'll use it as `SUPABASE_JWT_SECRET`.

### 1.2 Configure OAuth Providers

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google+ API**
4. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Fill in:
   - **Application type:** Web application
   - **Authorized redirect URIs:**
     ```
     https://your-project-id.supabase.co/auth/v1/callback
     ```
6. Copy **Client ID** and **Client Secret**

7. In Supabase Dashboard:
   - Go to **Authentication → Providers**
   - Enable **Google**
   - Paste your **Client ID** and **Client Secret**
   - Click **Save**

#### GitHub OAuth (Optional)

1. Go to **GitHub Settings → Developer settings → OAuth Apps**
2. Click **"New OAuth App"**
3. Fill in:
   - **Application name:** Board of One Beta
   - **Homepage URL:** `https://yourdomain.com`
   - **Authorization callback URL:**
     ```
     https://your-project-id.supabase.co/auth/v1/callback
     ```
4. Copy **Client ID** and generate **Client Secret**

5. In Supabase Dashboard:
   - Go to **Authentication → Providers**
   - Enable **GitHub**
   - Paste your **Client ID** and **Client Secret**
   - Click **Save**

---

## Part 2: Digital Ocean Droplet Setup

### 2.1 Create Droplet

1. Log in to Digital Ocean
2. Click **Create → Droplets**
3. Choose:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic ($6/month) - Good for beta testing
   - **CPU:** Regular (1 GB RAM, 1 vCPU)
   - **Datacenter:** Choose closest to your users
   - **Authentication:** SSH key (recommended) or password
4. Click **Create Droplet**

5. Note the droplet's IP address (e.g., `123.45.67.89`)

### 2.2 Connect to Droplet

```bash
ssh root@your-droplet-ip
```

### 2.3 Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Install Git
apt install git -y

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### 2.4 Clone Repository

```bash
cd /opt
git clone https://github.com/yourusername/bo1.git
cd bo1
```

---

## Part 3: Environment Configuration

### 3.1 Create .env File

```bash
cp .env.example .env
nano .env
```

### 3.2 Configure .env

Update these critical values:

```bash
# =============================================================================
# LLM API Keys
# =============================================================================
ANTHROPIC_API_KEY=your_anthropic_api_key_here
VOYAGE_API_KEY=your_voyage_api_key_here

# =============================================================================
# PostgreSQL (Use Supabase database)
# =============================================================================
DATABASE_URL=postgresql://postgres.your-project-id:your-db-password@aws-0-us-west-1.pooler.supabase.com:6543/postgres

# =============================================================================
# Redis (Local)
# =============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# =============================================================================
# Admin API
# =============================================================================
ADMIN_API_KEY=your_random_secure_admin_key_here  # Generate: openssl rand -hex 32

# =============================================================================
# Supabase Auth (CRITICAL FOR BETA)
# =============================================================================
ENABLE_SUPABASE_AUTH=true  # Enable authentication

SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_from_supabase
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_from_supabase
SUPABASE_JWT_SECRET=your_jwt_secret_from_supabase

# Google OAuth (from Part 1.3)
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret_here

# GitHub OAuth (optional)
GITHUB_OAUTH_CLIENT_ID=your_github_client_id_here
GITHUB_OAUTH_CLIENT_SECRET=your_github_client_secret_here

# =============================================================================
# CLOSED BETA WHITELIST (THIS IS KEY!)
# =============================================================================
CLOSED_BETA_MODE=true  # Restrict to whitelisted emails only

# Add your 10 beta testers' emails here (comma-separated, case-insensitive)
BETA_WHITELIST=alice@example.com,bob@company.com,charlie@startup.io,diana@test.com,eve@corp.com
```

Save and exit (`Ctrl+X`, `Y`, `Enter`)

---

## Part 4: Database Migration

### 4.1 Run Migrations

```bash
# Build containers
make build

# Run migrations to create beta_whitelist table
make shell
alembic upgrade head
exit
```

This creates the `beta_whitelist` table for dynamic email management.

---

## Part 5: Deployment

### 5.1 Start Services

```bash
# Start all containers (PostgreSQL, Redis, API)
make up

# Check status
make status

# View logs
make logs
```

### 5.2 Test API

```bash
# Health check
curl http://localhost:8000/health

# Check API docs
curl http://localhost:8000/docs
```

---

## Part 6: Whitelist Management

You have **two options** for managing beta testers:

### Option 1: Environment Variable (.env)

Add emails to `BETA_WHITELIST` in `.env`:

```bash
BETA_WHITELIST=alice@example.com,bob@company.com,charlie@startup.io
```

Restart API:
```bash
docker-compose restart bo1
```

**Pros:** Simple, version controlled
**Cons:** Requires restart to add users

### Option 2: Admin API (Recommended)

Add/remove emails dynamically without restart:

```bash
# List all whitelisted emails
curl -H "X-Admin-Key: your_admin_key" \
  http://localhost:8000/api/admin/beta-whitelist

# Add email
curl -X POST http://localhost:8000/api/admin/beta-whitelist \
  -H "X-Admin-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "notes": "YC batch W25"}'

# Remove email
curl -X DELETE http://localhost:8000/api/admin/beta-whitelist/olduser@example.com \
  -H "X-Admin-Key: your_admin_key"
```

**Pros:** Instant, no restart, track notes
**Cons:** Requires admin API key

---

## Part 7: Frontend Integration

### 7.1 Update Frontend URLs

In your SvelteKit frontend (`frontend/.env`):

```bash
PUBLIC_API_URL=http://your-droplet-ip:8000
PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
PUBLIC_SUPABASE_ANON_KEY=your_anon_key_from_supabase
```

### 7.2 Deploy Frontend

Deploy to Vercel/Netlify with environment variables above.

---

## Part 8: Domain Setup (Optional)

### 8.1 Add Domain to Digital Ocean

1. Go to **Networking → Domains**
2. Add your domain
3. Create DNS records:
   ```
   A    @    your-droplet-ip
   A    www  your-droplet-ip
   ```

### 8.2 Install Nginx + SSL

```bash
# Install Nginx
apt install nginx -y

# Install Certbot (for SSL)
apt install certbot python3-certbot-nginx -y

# Configure Nginx
nano /etc/nginx/sites-available/boardofone
```

Add:

```nginx
server {
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and restart:

```bash
ln -s /etc/nginx/sites-available/boardofone /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Get SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Part 9: Testing the Flow

### 9.1 Test Whitelisted User

1. Go to `https://yourdomain.com/login` (or your frontend)
2. Click **"Sign in with Google"**
3. Select Google account with whitelisted email
4. **Expected:** Login successful, access granted

### 9.2 Test Non-Whitelisted User

1. Go to login page
2. Click **"Sign in with Google"**
3. Select Google account NOT in whitelist
4. **Expected:** Error message:
   ```
   Thanks for your interest! We're currently in closed beta.
   Join our waitlist at https://boardof.one/waitlist
   ```

### 9.3 Test Admin API

```bash
# Add yourself to whitelist
curl -X POST http://yourdomain.com/api/admin/beta-whitelist \
  -H "X-Admin-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"email": "youremail@gmail.com", "notes": "Product owner"}'

# Verify
curl -H "X-Admin-Key: your_admin_key" \
  http://yourdomain.com/api/admin/beta-whitelist
```

---

## Part 10: Monitoring & Maintenance

### 10.1 View Logs

```bash
# All logs
make logs

# App logs only
make logs-app

# Follow logs in real-time
docker-compose logs -f bo1
```

### 10.2 Check Active Sessions

```bash
curl -H "X-Admin-Key: your_admin_key" \
  http://yourdomain.com/api/admin/sessions/active
```

### 10.3 Backup Data

```bash
# Backup Redis
make backup-redis

# Backup PostgreSQL (Supabase auto-backs up)
# Or manually via Supabase dashboard
```

---

## Troubleshooting

### Issue: Users get "Invalid or expired token" error

**Solution:** Check Supabase JWT secret matches `.env`

```bash
# In Supabase: Settings → API → JWT Secret
# In .env: SUPABASE_JWT_SECRET should match exactly
```

### Issue: Whitelist not working

**Solution:** Verify `CLOSED_BETA_MODE=true` in `.env` and emails are lowercase

```bash
# Check current whitelist
curl -H "X-Admin-Key: your_admin_key" \
  http://localhost:8000/api/admin/beta-whitelist
```

### Issue: OAuth redirect fails

**Solution:** Update Supabase redirect URLs

1. Go to Supabase **Authentication → URL Configuration**
2. Add:
   ```
   Site URL: https://yourdomain.com
   Redirect URLs: https://yourdomain.com/auth/callback
   ```

---

## Security Checklist

- [ ] Changed `ADMIN_API_KEY` from default
- [ ] Enabled firewall: `ufw allow 22,80,443/tcp && ufw enable`
- [ ] SSL certificate installed (HTTPS only)
- [ ] Supabase JWT secret is secure (32+ characters)
- [ ] `CLOSED_BETA_MODE=true` in production
- [ ] Database password is strong
- [ ] SSH key authentication (not password)
- [ ] Regular backups enabled

---

## Quick Reference Commands

```bash
# Start services
make up

# Stop services
make down

# View logs
make logs

# Add beta tester
curl -X POST http://localhost:8000/api/admin/beta-whitelist \
  -H "X-Admin-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com"}'

# List beta testers
curl -H "X-Admin-Key: your_admin_key" \
  http://localhost:8000/api/admin/beta-whitelist

# Remove beta tester
curl -X DELETE http://localhost:8000/api/admin/beta-whitelist/user@example.com \
  -H "X-Admin-Key: your_admin_key"

# Check active deliberations
curl -H "X-Admin-Key: your_admin_key" \
  http://localhost:8000/api/admin/sessions/active
```

---

## Next Steps After Beta

When ready to open to public:

1. Set `CLOSED_BETA_MODE=false` in `.env`
2. Remove `BETA_WHITELIST` entries (optional - won't be checked)
3. Restart API: `docker-compose restart bo1`

All users can now authenticate without whitelist check.

---

## Support

- **Backend logs:** `make logs-app`
- **Database issues:** Check Supabase dashboard
- **Auth issues:** Verify Supabase provider config
- **Whitelist issues:** Use admin API to debug

**Questions?** Open an issue on GitHub or contact support.
