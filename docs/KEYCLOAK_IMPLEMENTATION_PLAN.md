# Keycloak Implementation Plan for Board of One

**Date:** 2025-11-20
**Goal:** Replace Supabase Auth with Keycloak for proper server-side OAuth with PKCE
**Estimated Time:** 2 days
**Security Level:** Enterprise-grade (best practice)

---

## Phase 1: Keycloak Setup (Day 1, Morning)

### Step 1.1: Add Keycloak to Docker Compose

**File:** `docker-compose.yml`

Add Keycloak service:

```yaml
  # ---------------------------------------------------------------------------
  # Keycloak: OAuth/OIDC Provider (replaces Supabase Auth)
  # ---------------------------------------------------------------------------
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    container_name: bo1-keycloak
    command: start-dev
    environment:
      # Admin credentials
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin_change_me}

      # Database (use our existing Postgres)
      - KC_DB=postgres
      - KC_DB_URL=jdbc:postgresql://postgres:5432/keycloak
      - KC_DB_USERNAME=bo1
      - KC_DB_PASSWORD=${POSTGRES_PASSWORD:-bo1_dev_password}

      # Hostname configuration
      - KC_HOSTNAME=localhost
      - KC_HOSTNAME_PORT=8080
      - KC_HOSTNAME_STRICT=false
      - KC_HOSTNAME_STRICT_HTTPS=false

      # HTTP settings (dev mode)
      - KC_HTTP_ENABLED=true
      - KC_HTTP_PORT=8080

      # Proxy settings
      - KC_PROXY=edge

      # Logging
      - KC_LOG_LEVEL=info

    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bo1-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "exec 3<>/dev/tcp/localhost/8080 && echo -e 'GET /health/ready HTTP/1.1\\r\\nHost: localhost\\r\\nConnection: close\\r\\n\\r\\n' >&3 && cat <&3 | grep -q '200 OK'"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Step 1.2: Create Keycloak Database

**File:** `migrations/versions/create_keycloak_db.sql`

```sql
-- Create keycloak database
CREATE DATABASE keycloak;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO bo1;
```

Run manually:
```bash
docker exec bo1-postgres psql -U bo1 -c "CREATE DATABASE keycloak;"
```

### Step 1.3: Start Keycloak

```bash
docker-compose up -d keycloak
docker logs -f bo1-keycloak  # Watch startup (takes 30 seconds)
```

**Verify:** Access http://localhost:8080 → Should see Keycloak admin login

---

## Phase 2: Keycloak Configuration (Day 1, Afternoon)

### Step 2.1: Create Realm

1. **Login to Keycloak admin**:
   - URL: http://localhost:8080
   - Username: `admin`
   - Password: `admin_change_me` (from env)

2. **Create Realm**:
   - Hover over "master" dropdown → "Create Realm"
   - Name: `boardofone`
   - Enabled: ON
   - Click "Create"

### Step 2.2: Configure Google OAuth Identity Provider

1. **Add Google Provider**:
   - Realm: `boardofone` → Identity Providers
   - Click "Add provider" → Select "Google"

2. **Configure Google**:
   - Alias: `google`
   - Display name: `Google`
   - Client ID: `490598945509-2jeduiqr471c7ocfbr4rm84uhjujk78h.apps.googleusercontent.com`
   - Client Secret: (from Google Cloud Console)
   - Click "Add"

3. **Update Google Cloud Console**:
   - Go to: https://console.cloud.google.com/apis/credentials
   - Edit OAuth 2.0 Client ID
   - Authorized redirect URIs, add:
     ```
     http://localhost:8080/realms/boardofone/broker/google/endpoint
     ```
   - Save

### Step 2.3: Create OIDC Client for Backend

1. **Create Client**:
   - Realm: `boardofone` → Clients → "Create client"
   - Client type: `OpenID Connect`
   - Client ID: `boardofone-backend`
   - Click "Next"

2. **Capability config**:
   - Client authentication: ON
   - Authorization: OFF
   - Authentication flow:
     - ✅ Standard flow (Authorization Code)
     - ✅ Direct access grants
     - ❌ Implicit flow
     - ❌ Service accounts roles
   - Click "Next"

3. **Login settings**:
   - Root URL: `http://localhost:8000`
   - Valid redirect URIs: `http://localhost:8000/api/auth/callback`
   - Valid post logout redirect URIs: `http://localhost:5173/*`
   - Web origins: `http://localhost:5173`
   - Click "Save"

4. **Get Client Secret**:
   - Go to "Credentials" tab
   - Copy "Client secret" → Save to `.env`:
     ```
     KEYCLOAK_CLIENT_SECRET=<secret>
     ```

### Step 2.4: Configure Session Settings

1. **Realm Settings → Sessions**:
   - SSO Session Idle: 1 hour
   - SSO Session Max: 10 hours
   - Offline Session Idle: 30 days
   - Access Token Lifespan: 5 minutes
   - Click "Save"

---

## Phase 3: Backend Integration (Day 2, Morning)

### Step 3.1: Update Environment Variables

**File:** `.env`

```bash
# Keycloak Configuration (replaces Supabase)
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=boardofone
KEYCLOAK_CLIENT_ID=boardofone-backend
KEYCLOAK_CLIENT_SECRET=<from Keycloak admin>

# Remove Supabase variables (or comment out)
# SUPABASE_URL=...
# SUPABASE_JWT_SECRET=...
```

**File:** `docker-compose.yml` (API service)

```yaml
    environment:
      # Keycloak Configuration
      - KEYCLOAK_URL=http://keycloak:8080  # Internal Docker URL
      - KEYCLOAK_BROWSER_URL=http://localhost:8080  # External browser URL
      - KEYCLOAK_REALM=boardofone
      - KEYCLOAK_CLIENT_ID=boardofone-backend
      - KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}
```

### Step 3.2: Install Keycloak Python Library

**File:** `pyproject.toml`

```toml
dependencies = [
    # ... existing dependencies ...
    "python-keycloak>=3.8.0,<4.0",  # Keycloak admin and auth
]
```

Run:
```bash
docker-compose exec api uv pip install python-keycloak
```

### Step 3.3: Create Keycloak Auth Module

**File:** `backend/api/keycloak_auth.py` (NEW)

```python
"""Keycloak OAuth integration for Board of One - BFF Pattern.

Architecture:
1. Backend generates PKCE challenge
2. Backend redirects browser to Keycloak
3. Keycloak redirects to Google OAuth
4. Google redirects to Keycloak
5. Keycloak redirects to backend callback with code
6. Backend exchanges code + verifier for tokens
7. Backend validates tokens, creates session
8. Backend sets httpOnly cookie, redirects to dashboard

Security:
- Tokens NEVER exposed to frontend
- PKCE prevents authorization code interception
- httpOnly cookies prevent XSS
- Server-side validation only
"""

import hashlib
import logging
import os
import secrets
from base64 import urlsafe_b64encode
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import RedirectResponse
from keycloak import KeycloakOpenID

from backend.api.session import SessionManager
from bo1.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Keycloak configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_BROWSER_URL = os.getenv("KEYCLOAK_BROWSER_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "boardofone")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "boardofone-backend")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

# Frontend/backend URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Cookie configuration
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "bo1_session")
OAUTH_STATE_COOKIE_NAME = "oauth_state"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "localhost")

# Initialize session manager and Keycloak client
session_manager = SessionManager()

keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_URL,
    client_id=KEYCLOAK_CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=KEYCLOAK_CLIENT_SECRET,
)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate code verifier (random 128 char string)
    code_verifier = secrets.token_urlsafe(96)  # 96 bytes = 128 chars base64url

    # Generate code challenge (SHA256 hash of verifier)
    verifier_bytes = code_verifier.encode("ascii")
    sha256_hash = hashlib.sha256(verifier_bytes).digest()
    code_challenge = urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")

    return code_verifier, code_challenge


@router.get("/auth/google/login")
async def google_oauth_login() -> RedirectResponse:
    """Initiate Google OAuth flow via Keycloak with PKCE.

    Flow:
    1. Generate PKCE code_verifier and code_challenge
    2. Generate random state parameter (CSRF protection)
    3. Store code_verifier in Redis with state as key
    4. Set temporary cookie with state
    5. Redirect to Keycloak authorize endpoint

    Returns:
        Redirect to Keycloak OAuth URL
    """
    try:
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()
        logger.info(f"Generated PKCE pair (verifier: {len(code_verifier)} chars)")

        # Store code_verifier in Redis and get state_id
        state_id = session_manager.create_oauth_state(
            code_verifier=code_verifier,
            redirect_uri=f"{FRONTEND_URL}/dashboard",
        )

        # Build Keycloak authorization URL
        auth_params = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "redirect_uri": f"{BACKEND_URL}/api/auth/callback",
            "response_type": "code",
            "scope": "openid email profile",
            "state": state_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "kc_idp_hint": "google",  # Directly go to Google (skip Keycloak login)
        }

        auth_url = (
            f"{KEYCLOAK_BROWSER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
            f"?{urlencode(auth_params)}"
        )

        logger.info(f"Redirecting to Keycloak OAuth URL (state: {state_id[:8]}...)")

        # Create redirect response
        response = RedirectResponse(url=auth_url, status_code=302)

        # Set temporary cookie with state (for CSRF validation)
        response.set_cookie(
            key=OAUTH_STATE_COOKIE_NAME,
            value=state_id,
            max_age=600,  # 10 minutes
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN != "localhost" else None,
        )

        return response

    except Exception as e:
        logger.error(f"OAuth login failed: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=auth_init_failed",
            status_code=302,
        )


@router.get("/auth/callback")
async def oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(None),
) -> RedirectResponse:
    """Handle OAuth callback from Keycloak and create session.

    Flow:
    1. Validate state parameter (CSRF check)
    2. Retrieve code_verifier from Redis
    3. Exchange code + verifier for tokens via Keycloak
    4. Validate tokens
    5. Check beta whitelist
    6. Create/update user in database
    7. Create session in Redis
    8. Set httpOnly session cookie
    9. Redirect to frontend dashboard

    Args:
        code: Authorization code from Keycloak
        state: State parameter (CSRF protection)
        error: Error from OAuth provider
        oauth_state: State from cookie (for validation)

    Returns:
        Redirect to frontend (dashboard or login with error)
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error: {error}")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=oauth_error",
                status_code=302,
            )

        # Validate required parameters
        if not code or not state:
            logger.error("Missing code or state parameter")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=missing_parameters",
                status_code=302,
            )

        # CSRF check: state from query must match state from cookie
        if state != oauth_state:
            logger.error(f"CSRF validation failed: state mismatch")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=csrf_validation_failed",
                status_code=302,
            )

        # Retrieve code_verifier from Redis
        oauth_state_data = session_manager.get_oauth_state(state)
        if not oauth_state_data:
            logger.error(f"OAuth state not found or expired: {state[:8]}...")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=state_expired",
                status_code=302,
            )

        code_verifier = oauth_state_data.get("code_verifier")
        if not code_verifier:
            logger.error("Code verifier missing from OAuth state")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=invalid_state",
                status_code=302,
            )

        # Delete OAuth state (one-time use)
        session_manager.delete_oauth_state(state)

        logger.info(f"Exchanging authorization code for tokens (code: {code[:10]}...)")

        # Exchange code + verifier for tokens via Keycloak
        try:
            token_response = keycloak_openid.token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=f"{BACKEND_URL}/api/auth/callback",
                code_verifier=code_verifier,
            )
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=token_exchange_failed",
                status_code=302,
            )

        # Extract tokens
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")

        if not access_token:
            logger.error("Token response missing access_token")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=invalid_token_response",
                status_code=302,
            )

        # Decode and validate token
        try:
            user_info = keycloak_openid.userinfo(access_token)
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=invalid_token",
                status_code=302,
            )

        user_id = user_info.get("sub")
        user_email = user_info.get("email")

        if not user_id or not user_email:
            logger.error("User info missing required fields")
            return RedirectResponse(
                url=f"{FRONTEND_URL}/login?error=missing_user_data",
                status_code=302,
            )

        logger.info(f"Successfully authenticated user: {user_email} (id: {user_id})")

        # Check beta whitelist if closed beta mode is enabled
        settings = get_settings()
        if settings.closed_beta_mode:
            user_email_lower = user_email.lower()
            if user_email_lower not in settings.beta_whitelist_emails:
                logger.warning(
                    f"User {user_email_lower} not in beta whitelist. "
                    f"Whitelist has {len(settings.beta_whitelist_emails)} emails."
                )
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/login?error=closed_beta",
                    status_code=302,
                )
            logger.info(f"User {user_email_lower} found in beta whitelist - access granted")

        # Create or update user in database
        from backend.api.auth import _ensure_user_exists
        _ensure_user_exists(
            user_id=user_id,
            email=user_email,
            auth_provider="google",
        )

        # Create session in Redis
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": token_response.get("expires_in", 300),
        }

        session_id = session_manager.create_session(
            user_id=user_id,
            email=user_email,
            tokens=tokens,
        )

        # Create redirect response to frontend dashboard
        response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard", status_code=302)

        # Set httpOnly session cookie
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=3600,  # 1 hour
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN != "localhost" else None,
        )

        # Delete OAuth state cookie
        response.delete_cookie(
            key=OAUTH_STATE_COOKIE_NAME,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN != "localhost" else None,
        )

        logger.info(f"Session created for {user_email}, redirecting to dashboard")
        return response

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{FRONTEND_URL}/login?error=callback_failed",
            status_code=302,
        )


@router.post("/auth/logout")
async def logout(
    request: Request,
    bo1_session: str | None = Cookie(None),
) -> dict[str, str]:
    """Sign out user and invalidate session."""
    try:
        if bo1_session:
            session_manager.delete_session(bo1_session)
            logger.info(f"User logged out: {bo1_session[:8]}...")

        return {"message": "Successfully signed out"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return {"message": "Signed out"}


@router.get("/auth/me")
async def get_current_user_info(
    request: Request,
    bo1_session: str | None = Cookie(None),
) -> dict[str, Any]:
    """Get current user info from session."""
    try:
        if not bo1_session:
            raise HTTPException(status_code=401, detail="Not authenticated")

        session = session_manager.get_session(bo1_session)
        if not session:
            raise HTTPException(status_code=401, detail="Session expired")

        return {
            "id": session.get("user_id"),
            "email": session.get("email"),
            "auth_provider": "google",
            "subscription_tier": "free",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user info") from e
```

### Step 3.4: Update Main API Router

**File:** `backend/api/main.py`

```python
# Replace Supabase auth import with Keycloak auth
from backend.api import keycloak_auth  # instead of: from backend.api import auth

# Replace auth router
app.include_router(keycloak_auth.router, prefix="/api", tags=["auth"])
```

---

## Phase 4: Testing & Validation (Day 2, Afternoon)

### Step 4.1: Start All Services

```bash
docker-compose down
docker-compose up -d
docker-compose logs -f keycloak api frontend
```

### Step 4.2: Manual Testing Checklist

- [ ] Keycloak admin accessible at http://localhost:8080
- [ ] Realm `boardofone` exists
- [ ] Client `boardofone-backend` configured
- [ ] Google identity provider configured
- [ ] Frontend login page loads (http://localhost:5173/login)
- [ ] Click "Sign in with Google" redirects to Google
- [ ] Google OAuth consent completes
- [ ] Redirects back to dashboard with session cookie
- [ ] Cookie is httpOnly (check DevTools → Application → Cookies)
- [ ] No tokens in localStorage (check DevTools → Storage)
- [ ] Can access protected endpoints
- [ ] Logout clears session
- [ ] Session expires after 1 hour

### Step 4.3: Verify Security

```bash
# 1. Check session in Redis
docker exec bo1-redis redis-cli KEYS "session:*"
docker exec bo1-redis redis-cli GET "session:<session_id>"

# 2. Check no tokens in frontend
# Open DevTools → Console:
localStorage.getItem('bo1_access_token')  # Should be null
sessionStorage.getItem('bo1_access_token')  # Should be null

# 3. Check httpOnly cookie
# Open DevTools → Application → Cookies → http://localhost:5173
# Look for bo1_session cookie
# Verify: HttpOnly = ✓, SameSite = Lax
```

### Step 4.4: Test Whitelist

1. Try signing in with non-whitelisted email
2. Should redirect to `/login?error=closed_beta`
3. Verify whitelist check in logs

---

## Phase 5: Production Deployment Considerations

### Step 5.1: Environment Variables for Production

**File:** `.env.production`

```bash
# Keycloak (production)
KEYCLOAK_URL=http://keycloak:8080  # Internal
KEYCLOAK_BROWSER_URL=https://auth.boardof.one  # External
KEYCLOAK_REALM=boardofone
KEYCLOAK_CLIENT_ID=boardofone-backend
KEYCLOAK_CLIENT_SECRET=<strong-secret>
KEYCLOAK_ADMIN_PASSWORD=<strong-password>

# Application
FRONTEND_URL=https://boardof.one
BACKEND_URL=https://api.boardof.one
COOKIE_SECURE=true  # HTTPS only
COOKIE_DOMAIN=.boardof.one  # Allows subdomains
```

### Step 5.2: Update Google OAuth Redirect URIs

Add production redirect URI in Google Cloud Console:
```
https://auth.boardof.one/realms/boardofone/broker/google/endpoint
```

### Step 5.3: Keycloak Production Configuration

1. **Create production realm export**:
   ```bash
   docker exec bo1-keycloak /opt/keycloak/bin/kc.sh export \
     --dir /tmp/export \
     --realm boardofone
   ```

2. **Import on production server**:
   ```bash
   docker exec bo1-keycloak /opt/keycloak/bin/kc.sh import \
     --dir /tmp/export \
     --realm boardofone
   ```

3. **Enable HTTPS**:
   - Update Nginx to proxy Keycloak
   - Configure SSL certificates
   - Set `KC_HOSTNAME_STRICT_HTTPS=true`

---

## Migration Checklist

### From Supabase to Keycloak

- [ ] Backup existing user data from Supabase
- [ ] Export user list to CSV
- [ ] Import users into Keycloak (if needed)
- [ ] Update all environment variables
- [ ] Remove Supabase containers
- [ ] Test complete OAuth flow
- [ ] Verify all users can log in
- [ ] Monitor logs for errors
- [ ] Update documentation

---

## Rollback Plan

If Keycloak implementation fails:

1. **Revert Docker Compose**:
   ```bash
   git checkout main docker-compose.yml
   ```

2. **Restore Supabase**:
   ```bash
   docker-compose up -d supabase-auth
   ```

3. **Revert Backend Code**:
   ```bash
   git checkout main backend/api/auth.py
   git checkout main backend/api/main.py
   ```

4. **Restart Services**:
   ```bash
   docker-compose restart api frontend
   ```

---

## Success Criteria

✅ Google OAuth login works end-to-end
✅ Tokens never exposed to frontend
✅ httpOnly cookies working
✅ PKCE implemented correctly
✅ Whitelist checking functional
✅ Session management working
✅ Logout working
✅ No security vulnerabilities
✅ All tests passing
✅ Documentation updated

---

## Next Steps After Keycloak Implementation

1. **Add more OAuth providers**:
   - LinkedIn (30 minutes)
   - GitHub (30 minutes)

2. **Implement token refresh**:
   - Auto-refresh before expiry
   - Seamless UX

3. **Add admin features**:
   - User management UI
   - Audit logs
   - Session management

4. **Production hardening**:
   - Rate limiting
   - IP allowlisting
   - MFA (if needed)

---

## Resources

- Keycloak Docs: https://www.keycloak.org/documentation
- Python Keycloak Library: https://python-keycloak.readthedocs.io/
- OAuth 2.0 PKCE: https://oauth.net/2/pkce/
- Keycloak Docker: https://www.keycloak.org/server/containers

---

**Ready to implement? Start with Phase 1 and work through sequentially.**
