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

### "The running SuperTokens core version is not compatible with this python SDK"

SuperTokens Core and Python SDK have strict version compatibility requirements based on CDI (Core Driver Interface) versions.

**Current compatibility:**
- Python SDK 0.30.x requires CDI 5.3 → SuperTokens Core 10.x+
- Python SDK 0.29.x requires CDI 5.2 → SuperTokens Core 9.x

**Fix**: Update SuperTokens Core to match the Python SDK version:

1. Check installed Python SDK version:
   ```bash
   docker exec bo1-api uv pip show supertokens-python | grep Version
   ```

2. Update `supertokens.Dockerfile` to compatible Core version:
   ```dockerfile
   # For Python SDK 0.30.x - use Core 10.1.4+
   FROM registry.supertokens.io/supertokens/supertokens-postgresql:10.1.4
   ```

3. Rebuild and restart:
   ```bash
   docker-compose build supertokens
   docker-compose up -d supertokens
   docker-compose restart api
   ```

See [SuperTokens Compatibility Table](https://supertokens.com/docs/references/compatibility-table) for details.

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

## Additional OAuth Providers

### GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Configure:
   - **Application name**: `Bo1 Local Dev`
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8000/api/auth/callback/github`
4. Copy Client ID and generate a Client Secret
5. Add to `.env`:
   ```bash
   GITHUB_OAUTH_ENABLED=true
   GITHUB_OAUTH_CLIENT_ID=your_client_id
   GITHUB_OAUTH_CLIENT_SECRET=your_client_secret
   ```

### LinkedIn OAuth Setup

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Under **Auth** tab, configure:
   - **Authorized redirect URLs**: `http://localhost:8000/api/auth/callback/linkedin`
4. Request the following products: **Sign In with LinkedIn using OpenID Connect**
5. Copy Client ID and Client Secret
6. Add to `.env`:
   ```bash
   LINKEDIN_OAUTH_ENABLED=true
   LINKEDIN_OAUTH_CLIENT_ID=your_client_id
   LINKEDIN_OAUTH_CLIENT_SECRET=your_client_secret
   ```

### Production OAuth Configuration

For production, update callback URLs in each provider's dashboard:
- **Google**: `https://boardof.one/api/auth/callback/google`
- **GitHub**: `https://boardof.one/api/auth/callback/github`
- **LinkedIn**: `https://boardof.one/api/auth/callback/linkedin`

Ensure `SUPERTOKENS_API_DOMAIN=https://boardof.one` is set in production.

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
| `GITHUB_OAUTH_CLIENT_ID` | Yes** | - | GitHub OAuth client ID |
| `GITHUB_OAUTH_CLIENT_SECRET` | Yes** | - | GitHub OAuth client secret |
| `GITHUB_OAUTH_ENABLED` | No | `false` | Enable GitHub OAuth |
| `LINKEDIN_OAUTH_CLIENT_ID` | Yes*** | - | LinkedIn OAuth client ID |
| `LINKEDIN_OAUTH_CLIENT_SECRET` | Yes*** | - | LinkedIn OAuth client secret |
| `LINKEDIN_OAUTH_ENABLED` | No | `false` | Enable LinkedIn OAuth |
| `CLOSED_BETA_MODE` | No | `false` | Require email whitelist |

*Required if Google OAuth is enabled
**Required if GitHub OAuth is enabled
***Required if LinkedIn OAuth is enabled

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

## Common OAuth Errors

### "invalid_client" Error

The OAuth app client ID or secret is incorrect.

**Fix**: Double-check your credentials in `.env` match exactly what's shown in the provider's dashboard.

### "invalid_grant" Error

The authorization code has expired or already been used.

**Fix**: This is usually transient. Try the login flow again. If persistent, check that your server time is synchronized.

### "access_denied" Error

The user denied permission or the app doesn't have required scopes.

**Fix**:
- Ensure your OAuth app has the required scopes enabled
- For LinkedIn: Verify "Sign In with LinkedIn using OpenID Connect" product is approved
- For GitHub: Check the app has `read:user` and `user:email` scopes

### Provider-specific callback URL formats

Each provider has specific requirements for callback URLs:

| Provider | Format | Notes |
|----------|--------|-------|
| Google | `http://localhost:8000/api/auth/callback/google` | Supports localhost |
| GitHub | `http://localhost:8000/api/auth/callback/github` | Supports localhost |
| LinkedIn | `http://localhost:8000/api/auth/callback/linkedin` | May require HTTPS in some cases |

## See Also

- `.env.example` - Full environment variable documentation
- `backend/api/supertokens_config.py` - SuperTokens initialization
- `backend/api/startup_validation.py` - Auth validation logic
- `supertokens.Dockerfile` - SuperTokens Core version configuration
