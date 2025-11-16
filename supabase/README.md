# Supabase Auth Setup for Board of One

This directory contains configuration for self-hosted Supabase authentication.

## Overview

Board of One uses **self-hosted Supabase** (GoTrue auth server) for user authentication. This provides:

- Full control over auth infrastructure
- No vendor lock-in
- Reduced costs (auth only, no database/storage/edge functions)
- Support for OAuth providers: Google, LinkedIn, GitHub

## Status

**MVP (v1.0)**: Supabase auth is **disabled by default**. The API uses a hardcoded user ID (`test_user_1`) for development.

**v2.0+**: Enable Supabase auth by setting `ENABLE_SUPABASE_AUTH=true` in `.env`.

## Directory Structure

```
supabase/
├── README.md           # This file
├── config/
│   └── auth.yml        # GoTrue auth server configuration
└── migrations/         # Auth schema migrations (if needed)
```

## Quick Start (v2.0+)

### 1. Generate JWT Secret

```bash
openssl rand -base64 32
```

Copy the output to your `.env` file as `SUPABASE_JWT_SECRET`.

### 2. Configure OAuth Providers

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:9999/callback` (dev)
5. Copy Client ID and Client Secret to `.env`:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`

#### LinkedIn OAuth
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Add redirect URL: `http://localhost:9999/callback` (dev)
4. Copy Client ID and Client Secret to `.env`:
   - `LINKEDIN_OAUTH_CLIENT_ID`
   - `LINKEDIN_OAUTH_CLIENT_SECRET`

#### GitHub OAuth
1. Go to [GitHub Settings > Developer > OAuth Apps](https://github.com/settings/developers)
2. Create a new OAuth app
3. Authorization callback URL: `http://localhost:9999/callback` (dev)
4. Copy Client ID and Client Secret to `.env`:
   - `GITHUB_OAUTH_CLIENT_ID`
   - `GITHUB_OAUTH_CLIENT_SECRET`

### 3. Update Environment Variables

Add to your `.env` file:

```bash
# Enable Supabase Auth
ENABLE_SUPABASE_AUTH=true

# Supabase Configuration
SUPABASE_URL=http://localhost:9999
SUPABASE_JWT_SECRET=<your-generated-jwt-secret>
SUPABASE_ANON_KEY=<generated-anon-jwt>
SUPABASE_SERVICE_ROLE_KEY=<generated-service-role-jwt>

# OAuth Providers
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=<your-google-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<your-google-client-secret>

GITHUB_OAUTH_ENABLED=true
GITHUB_OAUTH_CLIENT_ID=<your-github-client-id>
GITHUB_OAUTH_CLIENT_SECRET=<your-github-client-secret>

LINKEDIN_OAUTH_ENABLED=true
LINKEDIN_OAUTH_CLIENT_ID=<your-linkedin-client-id>
LINKEDIN_OAUTH_CLIENT_SECRET=<your-linkedin-client-secret>
```

### 4. Add Supabase Services to Docker Compose

Add the following services to `docker-compose.yml`:

```yaml
# GoTrue Auth Server
supabase-auth:
  image: supabase/gotrue:latest
  container_name: bo1-supabase-auth
  depends_on:
    - postgres
  environment:
    - GOTRUE_DB_DRIVER=postgres
    - GOTRUE_DB_DATABASE_URL=${DATABASE_URL}
    - GOTRUE_SITE_URL=${SITE_URL:-http://localhost:3000}
    - GOTRUE_URI_ALLOW_LIST=${SITE_URL:-http://localhost:3000}
    - GOTRUE_JWT_SECRET=${SUPABASE_JWT_SECRET}
    - GOTRUE_JWT_EXP=3600
    - GOTRUE_DISABLE_SIGNUP=false
    - GOTRUE_MAILER_AUTOCONFIRM=true
    # Google OAuth
    - GOTRUE_EXTERNAL_GOOGLE_ENABLED=${GOOGLE_OAUTH_ENABLED:-false}
    - GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}
    - GOTRUE_EXTERNAL_GOOGLE_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET}
    - GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI=${SUPABASE_URL:-http://localhost:9999}/callback
    # GitHub OAuth
    - GOTRUE_EXTERNAL_GITHUB_ENABLED=${GITHUB_OAUTH_ENABLED:-false}
    - GOTRUE_EXTERNAL_GITHUB_CLIENT_ID=${GITHUB_OAUTH_CLIENT_ID}
    - GOTRUE_EXTERNAL_GITHUB_SECRET=${GITHUB_OAUTH_CLIENT_SECRET}
    - GOTRUE_EXTERNAL_GITHUB_REDIRECT_URI=${SUPABASE_URL:-http://localhost:9999}/callback
    # LinkedIn OAuth
    - GOTRUE_EXTERNAL_LINKEDIN_ENABLED=${LINKEDIN_OAUTH_ENABLED:-false}
    - GOTRUE_EXTERNAL_LINKEDIN_CLIENT_ID=${LINKEDIN_OAUTH_CLIENT_ID}
    - GOTRUE_EXTERNAL_LINKEDIN_SECRET=${LINKEDIN_OAUTH_CLIENT_SECRET}
    - GOTRUE_EXTERNAL_LINKEDIN_REDIRECT_URI=${SUPABASE_URL:-http://localhost:9999}/callback
  ports:
    - "9999:9999"
  networks:
    - bo1-network
  restart: unless-stopped
```

### 5. Start Services

```bash
docker-compose up -d
```

Verify GoTrue is running:
```bash
curl http://localhost:9999/health
```

### 6. Test Authentication

#### Using the Frontend (SvelteKit)

The frontend will handle OAuth flows automatically. Users click "Sign in with Google/LinkedIn/GitHub" and are redirected to the OAuth provider.

#### Using cURL (for testing)

1. Get authorization URL:
```bash
curl -X POST http://localhost:9999/authorize \
  -H "Content-Type: application/json" \
  -d '{"provider": "google"}'
```

2. Visit the URL in a browser, complete OAuth flow

3. Exchange code for JWT:
```bash
curl -X POST http://localhost:9999/token \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "authorization_code", "code": "<code-from-callback>"}'
```

4. Use JWT in API requests:
```bash
curl -X GET http://localhost:8000/api/sessions \
  -H "Authorization: Bearer <your-jwt-token>"
```

## JWT Token Structure

### Access Token (1 hour expiry)
```json
{
  "aud": "authenticated",
  "exp": 1234567890,
  "sub": "user-uuid",
  "email": "user@example.com",
  "role": "authenticated",
  "user_metadata": {
    "subscription_tier": "free"
  }
}
```

### Refresh Token (30 days expiry)
Used to get new access tokens without re-authenticating.

## Security Considerations

### Development
- Use `http://localhost:9999` for Supabase URL
- Store secrets in `.env` (git-ignored)
- OAuth redirect URLs: `http://localhost:9999/callback`

### Production
- Use `https://auth.boardofone.com` for Supabase URL
- Store secrets in environment variables or secrets manager
- Update OAuth redirect URLs to production domain
- Enable email confirmation (`GOTRUE_MAILER_AUTOCONFIRM=false`)
- Configure rate limits (10 signups/hour per IP)
- Use HTTPS for all auth endpoints

## Troubleshooting

### GoTrue not starting
- Check PostgreSQL is running and accessible
- Verify `DATABASE_URL` is correct
- Check GoTrue logs: `docker logs bo1-supabase-auth`

### OAuth callback fails
- Verify redirect URIs match in OAuth provider settings
- Check client IDs and secrets are correct
- Ensure OAuth provider is enabled in `.env`

### JWT verification fails
- Verify `SUPABASE_JWT_SECRET` matches GoTrue configuration
- Check token is not expired (1 hour expiry)
- Ensure `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct

## References

- [Supabase GoTrue Documentation](https://github.com/supabase/gotrue)
- [GoTrue Environment Variables](https://github.com/supabase/gotrue#configuration)
- [Google OAuth Setup](https://console.cloud.google.com/)
- [LinkedIn OAuth Setup](https://www.linkedin.com/developers/apps)
- [GitHub OAuth Setup](https://github.com/settings/developers)

## Support

For issues or questions:
- Check logs: `docker logs bo1-supabase-auth`
- Review this README
- Consult Supabase GoTrue documentation
