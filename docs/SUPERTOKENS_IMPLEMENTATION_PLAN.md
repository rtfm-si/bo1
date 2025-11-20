# SuperTokens Implementation Plan for Board of One

**Date:** 2025-11-20
**Context:** Replacing Supabase GoTrue with SuperTokens for secure BFF (Backend-for-Frontend) OAuth authentication

---

## Why SuperTokens?

**Infrastructure Fit:**
- **RAM Usage**: ~50-100MB (vs Keycloak 1-2GB) - Critical for 4GB Digital Ocean droplet
- **Startup Time**: 2-3 seconds (vs Keycloak 15-30 seconds)
- **Docker Image**: ~50MB (vs Keycloak ~500MB)
- **Built for BFF Pattern**: Their primary design pattern, perfect fit
- **FastAPI SDK**: First-class Python/FastAPI support with pre-built middleware

**Security:**
- ✅ Authorization Code Flow with PKCE (server-side)
- ✅ httpOnly cookies (zero frontend token exposure)
- ✅ Automatic token refresh
- ✅ Session management with Redis
- ✅ CSRF protection built-in

---

## Architecture Overview

```
Frontend (SvelteKit)
    ↓ User clicks "Sign in with Google"
    ↓
Backend (FastAPI + SuperTokens SDK)
    ↓ Initiates OAuth with Google (server-side PKCE)
    ↓ Receives authorization code from Google
    ↓ Exchanges code for tokens (server-side)
    ↓ Creates session in SuperTokens Core
    ↓ Returns httpOnly session cookie to frontend
    ↓
Frontend receives cookie (JavaScript cannot access)
    ↓ Cookie automatically sent with all API requests
    ↓
Backend verifies session with SuperTokens middleware
    ↓ Validates JWT, checks whitelist
    ↓ Allows/denies API access
```

**Key Security Properties:**
1. **Tokens never reach frontend** - Exchanged server-side only
2. **httpOnly cookies** - JavaScript cannot access (XSS-proof)
3. **Automatic refresh** - No manual token management
4. **CSRF protection** - Built into SuperTokens
5. **Session revocation** - Instant logout across all devices

---

## Phase 1: Start SuperTokens Core (COMPLETED ✅)

SuperTokens Core is the auth server that manages sessions.

### Docker Service (DONE)
```yaml
supertokens:
  image: registry.supertokens.io/supertokens/supertokens-postgresql:9.2.2
  container_name: bo1-supertokens
  environment:
    - POSTGRESQL_CONNECTION_URI=postgresql://bo1:PASSWORD@postgres:5432/boardofone
    - POSTGRESQL_TABLE_SCHEMA=supertokens
    - API_KEYS=dev_api_key_change_in_production
  ports:
    - "3567:3567"
```

### Environment Variables (DONE)
```bash
SUPERTOKENS_CONNECTION_URI=http://supertokens:3567
SUPERTOKENS_API_KEY=dev_api_key_change_in_production
SUPERTOKENS_APP_NAME=Board of One
SUPERTOKENS_API_DOMAIN=http://localhost:8000
SUPERTOKENS_WEBSITE_DOMAIN=http://localhost:5173
```

### Start Service
```bash
docker compose up -d supertokens
docker compose ps  # Verify supertokens is healthy
docker logs bo1-supertokens  # Check for errors
```

---

## Phase 2: Backend Integration (FastAPI + SuperTokens SDK)

### 2.1 Create SuperTokens Configuration File

**File:** `backend/api/supertokens_config.py`

```python
"""SuperTokens configuration for Board of One authentication."""
import os
from typing import List

from fastapi import FastAPI
from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe import session, thirdparty
from supertokens_python.recipe.thirdparty import Google
from supertokens_python.recipe.thirdparty.provider import ProviderInput


def get_app_info() -> InputAppInfo:
    """Get SuperTokens app configuration from environment."""
    return InputAppInfo(
        app_name=os.getenv("SUPERTOKENS_APP_NAME", "Board of One"),
        api_domain=os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000"),
        website_domain=os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:5173"),
        api_base_path="/api/auth",  # All auth endpoints under /api/auth
        website_base_path="/auth",  # Frontend auth pages under /auth
    )


def get_supertokens_config() -> SupertokensConfig:
    """Get SuperTokens Core connection configuration."""
    return SupertokensConfig(
        connection_uri=os.getenv("SUPERTOKENS_CONNECTION_URI", "http://supertokens:3567"),
        api_key=os.getenv("SUPERTOKENS_API_KEY", "dev_api_key_change_in_production"),
    )


def get_oauth_providers() -> List[ProviderInput]:
    """Get configured OAuth providers (Google, LinkedIn, GitHub)."""
    providers = []

    # Google OAuth
    if os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() == "true":
        providers.append(
            ProviderInput(
                config=Google(
                    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
                    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
                    scope=["openid", "email", "profile"],
                )
            )
        )

    # LinkedIn OAuth (future)
    # if os.getenv("LINKEDIN_OAUTH_ENABLED", "false").lower() == "true":
    #     providers.append(...)

    # GitHub OAuth (future)
    # if os.getenv("GITHUB_OAUTH_ENABLED", "false").lower() == "true":
    #     providers.append(...)

    return providers


async def override_thirdparty_apis(original_implementation):
    """Override ThirdParty APIs to add custom logic (whitelist validation)."""
    original_sign_in_up_post = original_implementation.sign_in_up_post

    async def sign_in_up_post(
        provider, redirect_uri_info, oauth_tokens, session, tenant_id, user_context
    ):
        """Override sign in/up to add closed beta whitelist validation."""
        result = await original_sign_in_up_post(
            provider, redirect_uri_info, oauth_tokens, session, tenant_id, user_context
        )

        # Check if closed beta mode is enabled
        if os.getenv("CLOSED_BETA_MODE", "false").lower() == "true":
            whitelist = os.getenv("BETA_WHITELIST", "").split(",")
            whitelist = [email.strip().lower() for email in whitelist if email.strip()]

            # Get user email from result
            user_email = result.user.email.lower()

            # Validate against whitelist
            if user_email not in whitelist:
                # Reject user - not on whitelist
                raise Exception(f"Email {user_email} not whitelisted for closed beta")

        return result

    original_implementation.sign_in_up_post = sign_in_up_post
    return original_implementation


def init_supertokens():
    """Initialize SuperTokens with all recipes and configurations."""
    init(
        supertokens_config=get_supertokens_config(),
        app_info=get_app_info(),
        framework="fastapi",
        recipe_list=[
            # ThirdParty recipe for OAuth (Google, LinkedIn, GitHub)
            thirdparty.init(
                sign_in_and_up_feature=thirdparty.SignInAndUpFeature(
                    providers=get_oauth_providers()
                ),
                override=thirdparty.InputOverrideConfig(
                    apis=override_thirdparty_apis
                ),
            ),
            # Session recipe for session management (httpOnly cookies)
            session.init(
                cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
                cookie_domain=os.getenv("COOKIE_DOMAIN", "localhost"),
                cookie_same_site="lax",  # CSRF protection
            ),
        ],
        mode="asgi",  # FastAPI uses ASGI
    )


def add_supertokens_middleware(app: FastAPI):
    """Add SuperTokens middleware to FastAPI app."""
    app.add_middleware(get_middleware())
```

### 2.2 Update FastAPI Main App

**File:** `backend/api/main.py`

```python
# At the top, after imports
from backend.api.supertokens_config import init_supertokens, add_supertokens_middleware

# In create_app() function, BEFORE adding routes:
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    # ... existing setup ...

    # Initialize SuperTokens BEFORE adding routes
    init_supertokens()

    # Add SuperTokens middleware
    add_supertokens_middleware(app)

    # Add CORS AFTER SuperTokens middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,  # REQUIRED for cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "rid", "fdi-version", "anti-csrf"],  # SuperTokens headers
    )

    # ... rest of setup ...
```

### 2.3 Add SuperTokens Routes

SuperTokens SDK automatically creates routes when you import them:

```python
# In backend/api/main.py, after init_supertokens():
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe.thirdparty.asyncio import get_provider
```

**Auto-generated endpoints:**
- `POST /api/auth/signinup` - OAuth callback
- `GET /api/auth/authorisationurl` - Get OAuth URL
- `POST /api/auth/signout` - Sign out
- `POST /api/auth/session/refresh` - Refresh session

---

## Phase 3: Protected Routes with Session Verification

### 3.1 Update Middleware to Use SuperTokens

**File:** `backend/api/middleware/auth.py`

```python
"""Authentication middleware using SuperTokens."""
from fastapi import Request, HTTPException
from supertokens_python.recipe.session.framework.fastapi import verify_session
from supertokens_python.recipe.session import SessionContainer


async def require_auth(request: Request) -> SessionContainer:
    """
    Verify SuperTokens session from httpOnly cookie.

    Use this in protected routes:

    @router.get("/api/deliberations")
    async def get_deliberations(session: SessionContainer = Depends(require_auth)):
        user_id = session.get_user_id()
        # ... your logic

    Raises HTTPException(401) if session is invalid/expired.
    """
    return await verify_session()(request)


def get_user_id_from_session(session: SessionContainer) -> str:
    """Extract user ID from session."""
    return session.get_user_id()


def get_user_email_from_session(session: SessionContainer) -> str:
    """Extract user email from session metadata."""
    # SuperTokens stores email in session claims
    return session.get_access_token_payload().get("email", "")
```

### 3.2 Update Routes to Use Session Verification

**Example:** `backend/api/deliberations.py`

```python
from fastapi import APIRouter, Depends
from supertokens_python.recipe.session import SessionContainer
from backend.api.middleware.auth import require_auth, get_user_id_from_session

router = APIRouter()

@router.get("/api/deliberations")
async def get_deliberations(session: SessionContainer = Depends(require_auth)):
    """Get all deliberations for authenticated user."""
    user_id = get_user_id_from_session(session)

    # Query deliberations for this user_id
    # ...
    return {"deliberations": [...]}


@router.post("/api/deliberations")
async def create_deliberation(
    problem: str,
    session: SessionContainer = Depends(require_auth)
):
    """Create new deliberation for authenticated user."""
    user_id = get_user_id_from_session(session)

    # Create deliberation with user_id
    # ...
    return {"id": "...", "status": "created"}
```

---

## Phase 4: Frontend Integration (SvelteKit)

### 4.1 Install SuperTokens Web SDK

```bash
cd frontend
npm install supertokens-web-js
```

### 4.2 Initialize SuperTokens in Frontend

**File:** `frontend/src/lib/supertokens.ts`

```typescript
import SuperTokens from "supertokens-web-js";
import Session from "supertokens-web-js/recipe/session";
import ThirdParty from "supertokens-web-js/recipe/thirdparty";

export function initSuperTokens() {
    SuperTokens.init({
        appInfo: {
            apiDomain: "http://localhost:8000",
            apiBasePath: "/api/auth",
            appName: "Board of One",
        },
        recipeList: [
            Session.init(),
            ThirdParty.init(),
        ],
    });
}
```

### 4.3 Update Login Page

**File:** `frontend/src/routes/(auth)/login/+page.svelte`

```svelte
<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { initSuperTokens } from '$lib/supertokens';
    import ThirdParty from "supertokens-web-js/recipe/thirdparty";

    onMount(() => {
        initSuperTokens();
    });

    async function handleGoogleSignIn() {
        try {
            // Get authorization URL from SuperTokens backend
            const authUrl = await ThirdParty.getAuthorisationURLWithQueryParamsAndSetState({
                thirdPartyId: "google",
                frontendRedirectURI: "http://localhost:5173/auth/callback",
            });

            // Redirect browser to Google OAuth
            window.location.href = authUrl;
        } catch (error) {
            console.error("Failed to initiate Google sign-in:", error);
        }
    }
</script>

<div class="login-container">
    <h1>Sign in to Board of One</h1>
    <button on:click={handleGoogleSignIn}>
        Sign in with Google
    </button>
</div>
```

### 4.4 Create OAuth Callback Handler

**File:** `frontend/src/routes/(auth)/callback/+page.svelte`

```svelte
<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { initSuperTokens } from '$lib/supertokens';
    import ThirdParty from "supertokens-web-js/recipe/thirdparty";

    let error: string | null = null;

    onMount(async () => {
        initSuperTokens();

        try {
            // Handle OAuth callback
            await ThirdParty.signInAndUp();

            // Success! Redirect to dashboard
            goto('/dashboard');
        } catch (err: any) {
            console.error("OAuth callback error:", err);
            error = err.message || "Authentication failed";

            // Wait 3 seconds, then redirect to login
            setTimeout(() => goto('/login'), 3000);
        }
    });
</script>

{#if error}
    <div class="error-container">
        <h2>Authentication Failed</h2>
        <p>{error}</p>
        <p>Redirecting to login...</p>
    </div>
{:else}
    <div class="loading-container">
        <p>Completing sign in...</p>
    </div>
{/if}
```

### 4.5 Update Auth Store

**File:** `frontend/src/lib/stores/auth.ts`

```typescript
import { writable, derived } from 'svelte/store';
import Session from "supertokens-web-js/recipe/session";

export interface User {
    id: string;
    email: string;
}

function createAuthStore() {
    const { subscribe, set, update } = writable<User | null>(null);

    return {
        subscribe,

        async checkSession() {
            try {
                // SuperTokens automatically verifies session
                const sessionExists = await Session.doesSessionExist();

                if (sessionExists) {
                    // Get user info from backend
                    const response = await fetch('/api/auth/me', {
                        credentials: 'include',  // Send cookies
                    });

                    if (response.ok) {
                        const user = await response.json();
                        set(user);
                    } else {
                        set(null);
                    }
                } else {
                    set(null);
                }
            } catch (error) {
                console.error('Session check failed:', error);
                set(null);
            }
        },

        async signOut() {
            try {
                await Session.signOut();
                set(null);
            } catch (error) {
                console.error('Sign out failed:', error);
            }
        },

        async refreshSession() {
            // SuperTokens automatically refreshes when needed
            // Just verify session still exists
            await this.checkSession();
        }
    };
}

export const auth = createAuthStore();
export const isAuthenticated = derived(auth, $auth => $auth !== null);
```

### 4.6 Update Root Layout to Check Session

**File:** `frontend/src/routes/+layout.svelte`

```svelte
<script lang="ts">
    import { onMount } from 'svelte';
    import { initSuperTokens } from '$lib/supertokens';
    import { auth } from '$lib/stores/auth';

    onMount(() => {
        // Initialize SuperTokens
        initSuperTokens();

        // Check if user has valid session
        auth.checkSession();
    });
</script>

<slot />
```

---

## Phase 5: Testing & Validation

### 5.1 Start All Services

```bash
docker compose down
docker compose up -d postgres redis supertokens
docker compose up -d api frontend
docker compose ps  # All should be healthy
```

### 5.2 Test OAuth Flow

1. **Open browser:** http://localhost:5173/login
2. **Click "Sign in with Google"**
3. **Verify redirect to Google:** Should see Google account picker
4. **Select account and authorize**
5. **Verify redirect to callback:** Should redirect to /auth/callback
6. **Verify redirect to dashboard:** Should redirect to /dashboard

### 5.3 Verify Session Cookie

1. **Open browser DevTools → Application → Cookies**
2. **Check for cookies:**
   - `sAccessToken` (httpOnly, secure in production)
   - `sRefreshToken` (httpOnly, secure in production)
3. **Verify JavaScript cannot access:**
   ```javascript
   document.cookie  // Should NOT show sAccessToken/sRefreshToken
   ```

### 5.4 Test Protected API Endpoints

```bash
# Without session - should return 401
curl http://localhost:8000/api/deliberations

# With session cookie - should return data
curl http://localhost:8000/api/deliberations \
  -H "Cookie: sAccessToken=..." \
  --cookie-jar cookies.txt
```

### 5.5 Test Sign Out

1. **Click "Sign Out" button**
2. **Verify cookies cleared** (DevTools → Application → Cookies)
3. **Verify redirect to login**
4. **Try accessing /dashboard** - should redirect to /login

### 5.6 Test Closed Beta Whitelist

1. **Set `CLOSED_BETA_MODE=true` in .env**
2. **Set `BETA_WHITELIST=allowed@example.com`**
3. **Restart API:** `docker compose restart api`
4. **Try signing in with whitelisted email** - should succeed
5. **Try signing in with non-whitelisted email** - should fail with error

---

## Phase 6: Cleanup (Remove Supabase Auth)

### 6.1 Remove Supabase Service from Docker Compose

**File:** `docker-compose.yml`

```yaml
# DELETE the entire supabase-auth service section
```

### 6.2 Remove Supabase Environment Variables

**File:** `.env`

```bash
# DELETE these lines:
ENABLE_SUPABASE_AUTH=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
SITE_URL=...
```

### 6.3 Remove Old Auth Code

```bash
# Remove old Supabase auth implementation
rm backend/api/auth.py  # Old Supabase OAuth code
rm backend/api/session.py  # Old Redis session manager
rm frontend/src/routes/(auth)/callback/+page.svelte  # Old callback handler (replaced)
```

### 6.4 Remove Supabase from Dependencies

**File:** `pyproject.toml`

```toml
# REMOVE this line:
"supabase>=2.0.0,<3.0",
```

Then run:
```bash
uv sync
```

---

## Production Deployment Checklist

### Environment Variables (Production)

```bash
# SuperTokens Core
SUPERTOKENS_CONNECTION_URI=http://supertokens:3567
SUPERTOKENS_API_KEY=<generate_strong_random_key>

# SuperTokens App Config
SUPERTOKENS_APP_NAME=Board of One
SUPERTOKENS_API_DOMAIN=https://api.boardof.one
SUPERTOKENS_WEBSITE_DOMAIN=https://boardof.one

# OAuth Providers
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=<production_client_id>
GOOGLE_OAUTH_CLIENT_SECRET=<production_client_secret>

# Session Security
COOKIE_SECURE=true  # HTTPS only
COOKIE_DOMAIN=.boardof.one  # Works for api.boardof.one and boardof.one
COOKIE_SAME_SITE=lax

# Closed Beta
CLOSED_BETA_MODE=true
BETA_WHITELIST=user1@example.com,user2@example.com
```

### Google OAuth Configuration

1. **Go to:** https://console.cloud.google.com/apis/credentials
2. **Update Authorized redirect URIs:**
   - Add: `https://api.boardof.one/api/auth/callback/google`
3. **Save changes**

### SSL/HTTPS Configuration

SuperTokens requires HTTPS in production. Ensure:
- Nginx handles SSL termination
- `COOKIE_SECURE=true` in production
- `KC_PROXY=edge` tells SuperTokens it's behind a reverse proxy

---

## Cost Comparison

### Development (4GB Digital Ocean Droplet)

**With Keycloak:**
- Keycloak: 1.5GB RAM (37.5%)
- Postgres: 512MB
- Redis: 256MB
- API: 256MB
- Frontend: 128MB
- App: Remaining ~1.4GB
**Total: 2.65GB used (66% utilization, tight fit)**

**With SuperTokens:**
- SuperTokens: 100MB RAM (2.5%) ✅
- Postgres: 512MB
- Redis: 256MB
- API: 256MB
- Frontend: 128MB
- App: Remaining ~2.75GB ✅
**Total: 1.25GB used (31% utilization, comfortable headroom)**

---

## Troubleshooting

### Issue: SuperTokens Core won't start

**Check logs:**
```bash
docker logs bo1-supertokens
```

**Common causes:**
- Database connection string wrong
- PostgreSQL not ready (wait 10 seconds, try again)
- Port 3567 already in use

### Issue: OAuth redirect fails

**Check:**
1. `SUPERTOKENS_API_DOMAIN` matches your backend URL
2. `SUPERTOKENS_WEBSITE_DOMAIN` matches your frontend URL
3. Google OAuth redirect URI configured correctly
4. Browser can resolve localhost (use http://127.0.0.1:8000 if DNS issues)

### Issue: Session not persisting

**Check:**
1. `allow_credentials=True` in CORS middleware
2. `credentials: 'include'` in frontend fetch calls
3. Cookies visible in DevTools (Application → Cookies)
4. `COOKIE_DOMAIN` set to correct domain

### Issue: Whitelist validation not working

**Check:**
1. `CLOSED_BETA_MODE=true` set
2. `BETA_WHITELIST` contains comma-separated emails
3. Emails are lowercase (validator lowercases both)
4. API restarted after changing .env

---

## Migration Path

### Option A: Hard Cutover (Fastest, 30 minutes downtime)

1. Announce 30-minute maintenance window
2. Stop all services
3. Remove Supabase containers
4. Deploy SuperTokens configuration
5. Start all services
6. Test OAuth flow
7. All users must re-authenticate (one-time)

### Option B: Parallel Run (Safer, zero downtime)

1. Deploy SuperTokens alongside Supabase (both running)
2. Add feature flag: `USE_SUPERTOKENS=false`
3. Test SuperTokens thoroughly in production
4. Set `USE_SUPERTOKENS=true` (instant switch)
5. Monitor for 24 hours
6. If stable, remove Supabase containers
7. If issues, set `USE_SUPERTOKENS=false` (instant rollback)

**Recommended:** Option A (hard cutover) - Simpler, users expect re-auth after auth system changes.

---

## Next Steps After Implementation

1. **Add LinkedIn OAuth:** Similar to Google, add LinkedIn provider
2. **Add GitHub OAuth:** Similar to Google, add GitHub provider
3. **Email/Password Auth:** Add EmailPassword recipe for non-social login
4. **Password Reset:** Add password reset flow
5. **Email Verification:** Add email verification for email/password users
6. **2FA:** Add TOTP 2FA recipe for enhanced security

---

## Resources

- **SuperTokens Docs:** https://supertokens.com/docs
- **FastAPI Recipe:** https://supertokens.com/docs/thirdparty/pre-built-ui/setup/backend
- **Google OAuth:** https://supertokens.com/docs/thirdparty/common-customizations/sign-in-and-up/provider-config
- **Session Management:** https://supertokens.com/docs/session/introduction
- **BFF Pattern:** https://supertokens.com/docs/thirdparty/common-customizations/sessions/about

---

**Estimated Implementation Time:** 4-6 hours (vs 2 days for Keycloak)

**Next Action:** Start Phase 2 (Backend Integration)
