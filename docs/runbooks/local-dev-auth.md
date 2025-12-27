# Local Development Authentication Setup

This runbook covers setting up authentication for local development.

## Prerequisites

1. **Docker & Docker Compose** - All services run in containers
2. **Google Cloud Console access** - For OAuth credentials

## Quick Start (5 minutes)

### 1. Copy Environment Template

```bash
cp .env.local.example .env
```

### 2. Generate Secrets

```bash
# Generate required secrets (copy output to .env)
echo "REDIS_PASSWORD=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 32)"
echo "SUPERTOKENS_API_KEY=$(openssl rand -hex 32)"
```

### 3. Set Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create or select a project
3. Click **Create Credentials** → **OAuth client ID**
4. Select **Web application**
5. Configure:
   - **Name**: `Bo1 Local Dev`
   - **Authorized JavaScript origins**: `http://localhost:5173`
   - **Authorized redirect URIs**: `http://localhost:8000/api/auth/callback/google`
6. Copy Client ID and Client Secret to `.env`:
   ```
   GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
   ```

### 4. Start Services

```bash
make up
```

### 5. Verify Setup

```bash
make auth-check
```

### 6. Test Login

1. Open http://localhost:5173
2. Click "Sign in with Google"
3. Complete OAuth flow
4. Verify you're redirected to the dashboard

## Troubleshooting

### "SuperTokens Core not reachable"

SuperTokens container isn't running or hasn't started yet.

```bash
# Check container status
docker-compose ps supertokens

# View logs
docker-compose logs supertokens

# Restart if needed
docker-compose restart supertokens
```

### "OAuth redirect_uri_mismatch"

Google OAuth redirect URI doesn't match.

**Fix**: In Google Cloud Console, ensure redirect URI is exactly:
```
http://localhost:8000/api/auth/callback/google
```

### "Session cookie not set"

Browser may have stale cookies from production.

**Fix**: Clear cookies for localhost:
1. Open DevTools (F12)
2. Application → Cookies → localhost
3. Delete all `sAccessToken`, `sRefreshToken`, `csrf_token` cookies

### "403 Forbidden on callback"

CORS or CSRF issue.

**Fix**: Ensure CORS origins include frontend:
```bash
# In .env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Login works but session doesn't persist

Cookie domain mismatch.

**Fix**: Ensure cookie settings are correct for localhost:
```bash
# In .env
COOKIE_SECURE=false
COOKIE_DOMAIN=localhost
```

### "Not whitelisted for closed beta"

Closed beta mode is enabled but your email isn't in the whitelist.

**Fix**: Either disable closed beta or add your email:
```bash
# Option 1: Disable closed beta
CLOSED_BETA_MODE=false

# Option 2: Add email to whitelist (requires admin API key)
curl -X POST http://localhost:8000/api/admin/beta-whitelist \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com"}'
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPERTOKENS_API_KEY` | Yes | - | API key for SuperTokens Core |
| `SUPERTOKENS_CONNECTION_URI` | No | `http://supertokens:3567` | SuperTokens Core URL |
| `SUPERTOKENS_API_DOMAIN` | No | `http://localhost:8000` | Backend API domain |
| `SUPERTOKENS_WEBSITE_DOMAIN` | No | `http://localhost:5173` | Frontend domain |
| `COOKIE_SECURE` | No | `false` | Use secure cookies (HTTPS only) |
| `COOKIE_DOMAIN` | No | `localhost` | Cookie domain |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes* | - | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes* | - | Google OAuth client secret |
| `GOOGLE_OAUTH_ENABLED` | No | `true` | Enable Google OAuth |
| `CLOSED_BETA_MODE` | No | `false` | Require email whitelist |

*Required if Google OAuth is enabled

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│  Frontend   │────▶│  Backend    │────▶│ SuperTokens     │
│  :5173      │     │  API :8000  │     │ Core :3567      │
└─────────────┘     └─────────────┘     └─────────────────┘
       │                   │                     │
       │                   │                     │
       ▼                   ▼                     ▼
   Browser             PostgreSQL           PostgreSQL
   (cookies)           (users)              (supertokens schema)
```

1. User clicks "Sign in with Google" on frontend
2. Frontend redirects to `/api/auth/authorisationurl?thirdPartyId=google`
3. Backend returns Google OAuth URL
4. User authenticates with Google
5. Google redirects to `/api/auth/callback/google`
6. Backend exchanges code for tokens via SuperTokens
7. SuperTokens creates session, sets httpOnly cookies
8. User is redirected to frontend with session active

## See Also

- `.env.example` - Full environment variable documentation
- `backend/api/supertokens_config.py` - SuperTokens initialization
- `backend/api/startup_validation.py` - Auth validation logic
