# Production Environment Setup

This guide covers the environment variables and secrets needed for production deployment.

## Required GitHub Secrets

Add these secrets at: `https://github.com/rtfm-si/bo1/settings/secrets/actions`

| Secret Name | Description | How to Generate |
|-------------|-------------|-----------------|
| `PRODUCTION_HOST` | Server IP address | `139.59.201.65` |
| `PRODUCTION_USER` | SSH username | `root` or `deploy` |
| `PRODUCTION_SSH_KEY` | Private SSH key | `cat ~/.ssh/id_rsa_github_actions` |
| `PRODUCTION_SSH_PORT` | SSH port (optional) | `22` (default) |
| `POSTGRES_PASSWORD` | PostgreSQL password | `openssl rand -base64 32` |

## Production Server .env File

The `.env` file on the production server must contain:

```bash
# Required secrets
POSTGRES_PASSWORD=<generated-password>
REDIS_PASSWORD=<generated-password>

# Database URL (uses POSTGRES_PASSWORD)
DATABASE_URL=postgresql://bo1:${POSTGRES_PASSWORD}@postgres:5432/boardofone

# API Keys
ANTHROPIC_API_KEY=<your-key>
VOYAGE_API_KEY=<your-key>
TAVILY_API_KEY=<your-key>
BRAVE_API_KEY=<your-key>

# Supabase Auth
SUPABASE_JWT_SECRET=<generated-secret>
SUPABASE_ANON_KEY=<generated-key>
SUPABASE_SERVICE_ROLE_KEY=<generated-key>

# OAuth (if enabled)
GOOGLE_OAUTH_CLIENT_ID=<your-id>
GOOGLE_OAUTH_CLIENT_SECRET=<your-secret>
# ... other OAuth providers

# Application Settings
SITE_URL=https://boardof.one
CORS_ORIGINS=https://boardof.one
ADMIN_API_KEY=<generated-key>
```

## Production-Specific Overrides

For server-specific configurations (like SSL certificate paths), use `docker-compose.prod.override.yml`:

```yaml
# /opt/boardofone/docker-compose.prod.override.yml
# This file is NOT tracked in git

services:
  nginx:
    volumes:
      - /etc/letsencrypt/live/boardof.one:/etc/nginx/ssl:ro  # Production SSL
```

This file is automatically created by the deployment script if it doesn't exist.

## Initial Setup

1. **Generate passwords and keys:**
   ```bash
   openssl rand -base64 32  # POSTGRES_PASSWORD
   openssl rand -base64 32  # REDIS_PASSWORD
   openssl rand -base64 32  # SUPABASE_JWT_SECRET
   ```

2. **Add GitHub Secrets:**
   - Go to repository settings → Secrets and variables → Actions
   - Add all required secrets listed above

3. **SSH into production server:**
   ```bash
   ssh root@139.59.201.65
   cd /opt/boardofone
   ```

4. **Create .env file:**
   ```bash
   cp .env.example .env
   nano .env  # Fill in all values
   ```

5. **Verify setup:**
   ```bash
   bash /opt/boardofone/deployment-scripts/verify-server-setup.sh
   ```

## Deployment

Once secrets are configured, deploy via GitHub Actions:

1. Go to **Actions** tab → **Deploy to Production**
2. Click **Run workflow**
3. Type `deploy-to-production` to confirm
4. Monitor deployment progress

## Troubleshooting

### "POSTGRES_PASSWORD variable is not set"
- Check `.env` file on production server has `POSTGRES_PASSWORD=<value>`
- Add `POSTGRES_PASSWORD` to GitHub Secrets

### "Your local changes would be overwritten by merge"
- Fixed automatically by deployment script (uses `git stash`)
- Production-specific changes go in `docker-compose.prod.override.yml`

### SSL Certificate Issues
- Production uses Let's Encrypt at `/etc/letsencrypt/live/boardof.one`
- Override file maps this path to nginx container
- Never commit SSL paths to git (use override file)
