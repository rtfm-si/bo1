feature request
implement some kind of 'gated' features, where (user a) can see page 123 but user b cant

# Activate the venv

source .venv/bin/activate

ssh root@139.59.201.65

🎯 Ultra-Research Complete: GoTrue OAuth + BFF Implementation Plan

The subagent has completed deep research and found the root cause. Here's what you need to know:

---

🔴 Critical Finding: What We Were Doing Wrong

The PKCE Split-Brain Problem:

❌ Current (BROKEN):

1. Frontend generates code_verifier
2. Frontend → Supabase (with code_challenge)
3. Supabase → Frontend (with code)
4. Frontend → Backend (with code + verifier)
5. Backend → Supabase /token (with code + verifier)
6. Supabase: "Who are you? I don't know this verifier!" ❌

Why it fails: GoTrue stored the code_challenge when FRONTEND initiated
But BACKEND is trying to verify with the verifier
GoTrue sees different IP, different client → REJECTS

The OAuth spec requires:
"The entity that creates the code_challenge MUST be the same entity that exchanges the code with the verifier"

We violated this by splitting PKCE across frontend and backend!

---

✅ The Correct BFF Pattern

✅ Backend-Controlled (SECURE):

1. Browser → Backend /api/auth/google/login
2. Backend generates code_verifier + code_challenge
3. Backend stores verifier in Redis (keyed by session ID)
4. Backend sets temp cookie with session ID
5. Backend → Browser redirect to Supabase (with challenge)
6. Supabase → Google → Supabase → Backend /api/auth/callback
7. Backend receives code
8. Backend retrieves verifier from Redis
9. Backend → Supabase /token (code + verifier, same initiator!)
10. Supabase: "Valid! Here are your tokens" ✅
11. Backend stores tokens in Redis
12. Backend sets httpOnly session cookie
13. Backend redirects browser to /dashboard
14. Frontend: "I have a cookie but don't know what's in it" (SECURE!)

---

🔒 Security Comparison

| Attack Vector               | Current (localStorage) | BFF (httpOnly)                |
| --------------------------- | ---------------------- | ----------------------------- |
| XSS steals tokens           | 🔴 VULNERABLE          | 🟢 IMMUNE                     |
| CSRF attack                 | 🟡 POSSIBLE            | 🟢 PROTECTED (SameSite)       |
| Token in network logs       | 🔴 YES                 | 🟢 NO                         |
| Token in browser devtools   | 🔴 YES                 | 🟢 NO                         |
| Malicious browser extension | 🔴 CAN STEAL           | 🟢 CANNOT ACCESS              |
| Cost attack (stolen token)  | 🔴 UNLIMITED           | 🟢 LIMITED (1hr + rate limit) |

Bottom line: BFF makes your tokens invisible to JavaScript = XSS-proof.

---

📋 Implementation Overview

What changes:

- ✅ Backend: 2 new endpoints (/api/auth/google/login, /api/auth/callback)
- ✅ Backend: Session management with Redis
- ✅ Frontend: Remove 75 lines of PKCE code (simpler!)
- ✅ Frontend: Remove localStorage token storage
- ✅ Frontend: Simple redirect to backend for login
- ❌ Docker/Supabase config: NO CHANGES (already correct!)

Complexity: Medium (3-5 days)

Migration impact: Existing users logged out (acceptable for beta, only 4 users)

---

🚀 Next Decision Point

Do you want me to:

A) Show you the detailed implementation plan (code changes, step-by-step guide)
B) Start implementing immediately (I'll do Phase 1: backend changes first)
C) Explain a specific part in more detail (security, flow, testing, etc.)

The research agent created a complete implementation guide with:

- Before/after code for every file
- Security analysis for each threat
- Testing checklist
- Deployment guide

**Mission: Implement BFF (Backend-for-Frontend) OAuth pattern with httpOnly cookies for Board of One**

       ## Context

       You are implementing a SECURITY-CRITICAL authentication overhaul for Board of One, a SaaS platform handling:
       - Confidential business strategy data
       - PII (personally identifiable information)
       - Cost attack vector (users can burn LLM budget)

       **Current State (BROKEN & INSECURE):**
       - Tokens stored in localStorage (XSS vulnerable)
       - PKCE split across frontend/backend (causes "unsupported_grant_type" error)
       - Google OAuth login fails with "Invalid or expired authorization code"

       **Target State (SECURE):**
       - BFF pattern: Backend handles ALL OAuth
       - Tokens stored in Redis (never exposed to frontend)
       - httpOnly cookies for session (XSS-proof)
       - CSRF protection via SameSite cookies

       ## Previous Research Findings

       A research agent already investigated and found:

       ### **Root Cause of Current Failure**
       - Frontend generates PKCE `code_verifier`
       - Backend tries to use it to exchange code with Supabase
       - **Supabase GoTrue rejects this** because OAuth spec requires: "The entity that creates the code_challenge MUST
       be the same entity that exchanges the code"
       - This is why we get "unsupported_grant_type" error

       ### **The Correct Flow (BFF Pattern)**

       ```
       1. Browser → Backend /api/auth/google/login
          - Backend generates PKCE verifier + challenge
          - Backend stores verifier in Redis with temp session ID
          - Backend sets temp cookie
          - Backend redirects to Supabase /authorize

       2. Supabase → Google → Supabase → Backend /api/auth/callback
          - Supabase sends code to backend callback
          - Backend retrieves verifier from Redis
          - Backend exchanges code + verifier for tokens via Supabase /token
          - Backend stores tokens in Redis
          - Backend sets httpOnly session cookie
          - Backend redirects to frontend /dashboard

       3. Frontend → Backend /api/* (all API calls)
          - Browser sends httpOnly cookie automatically
          - Backend looks up session in Redis
          - Backend validates user
          - Backend processes request
       ```

       ## Your Implementation Tasks

       ### **PHASE 1: Backend Session Management**

       **File: `backend/api/session.py` (NEW FILE)**

       Create session management utilities:

       1. **Session schema in Redis**:
          ```python
          # Key: session:{session_id}
          # Value: {
          #   "user_id": "uuid",
          #   "email": "user@example.com",
          #   "access_token": "jwt...",
          #   "refresh_token": "jwt...",
          #   "expires_at": timestamp,
          #   "created_at": timestamp
          # }
          # TTL: 3600 seconds (1 hour)
          ```

       2. **OAuth flow state in Redis**:
          ```python
          # Key: oauth_state:{state_id}
          # Value: {
          #   "code_verifier": "random_string",
          #   "redirect_uri": "http://localhost:5173/dashboard",
          #   "created_at": timestamp
          # }
          # TTL: 600 seconds (10 minutes, just for OAuth flow)
          ```

       3. **Functions needed**:
          - `create_oauth_state(code_verifier: str) -> str` - Returns state_id
          - `get_oauth_state(state_id: str) -> dict | None`
          - `delete_oauth_state(state_id: str)`
          - `create_session(user_id: str, email: str, tokens: dict) -> str` - Returns session_id
          - `get_session(session_id: str) -> dict | None`
          - `delete_session(session_id: str)`
          - `refresh_session(session_id: str) -> dict` - Refreshes tokens

       **Dependencies**: Uses existing Redis from `bo1.state.redis_manager`

       ---

       ### **PHASE 2: Backend Auth Endpoints**

       **File: `backend/api/auth.py` (MAJOR REFACTOR)**

       #### **Endpoint 1: `GET /api/auth/google/login`**

       What it does:
       1. Generate PKCE code_verifier (128 char random string)
       2. Generate code_challenge (SHA256 hash of verifier, base64url encoded)
       3. Generate random state parameter (for CSRF protection)
       4. Store verifier in Redis oauth_state with state as key
       5. Build Supabase authorize URL with params:
          - `provider=google`
          - `code_challenge={challenge}`
          - `code_challenge_method=S256`
          - `state={state}`
          - `redirect_to=http://localhost:8000/api/auth/callback` (BACKEND callback!)
       6. Set temporary httpOnly cookie `oauth_state={state}` (to verify callback came from our flow)
       7. Redirect browser to Supabase authorize URL

       **Security notes**:
       - Cookie must be httpOnly, SameSite=Lax, Secure (in prod), Max-Age=600
       - State parameter prevents CSRF attacks
       - PKCE prevents authorization code interception

       #### **Endpoint 2: `GET /api/auth/callback`**

       What it does:
       1. Extract `code` and `state` from query params
       2. Extract `oauth_state` from cookie
       3. Validate: cookie state matches query state (CSRF check)
       4. Retrieve code_verifier from Redis using state
       5. Delete oauth_state from Redis (one-time use)
       6. Exchange code + verifier for tokens:
          ```python
          POST {SUPABASE_URL}/token
          Content-Type: application/x-www-form-urlencoded

          grant_type=authorization_code
          code={code}
          code_verifier={verifier}
          redirect_uri=http://localhost:8000/api/auth/callback
          ```
       7. Parse response to get access_token, refresh_token, user data
       8. Check if user email is in beta whitelist (if CLOSED_BETA_MODE=true)
       9. Create/update user in database (public.users table)
       10. Create session in Redis with tokens
       11. Set httpOnly session cookie `bo1_session={session_id}`
       12. Delete oauth_state cookie
       13. Redirect browser to frontend `/dashboard`

       **Error handling**:
       - If code exchange fails: Redirect to `/login?error=auth_failed`
       - If not in whitelist: Redirect to `/login?error=closed_beta`
       - If database error: Log and redirect to `/login?error=server_error`

       **Security notes**:
       - Session cookie: httpOnly, SameSite=Lax, Secure (prod), Max-Age=3600
       - Clear oauth_state cookie after use
       - Log all auth events

       #### **Endpoint 3: `POST /api/auth/logout`**

       What it does:
       1. Extract session_id from cookie
       2. Delete session from Redis
       3. Clear bo1_session cookie (set Max-Age=0)
       4. Return 200 OK

       #### **Endpoint 4: `POST /api/auth/refresh` (for automatic token refresh)**

       What it does:
       1. Extract session_id from cookie
       2. Get session from Redis
       3. Check if access_token is expired or near expiry (<5 min remaining)
       4. If expired: Use refresh_token to get new access_token from Supabase
       5. Update session in Redis with new tokens
       6. Return success (session cookie remains same)

       ---

       ### **PHASE 3: Backend Middleware Updates**

       **File: `backend/api/middleware/auth.py`**

       Update `verify_jwt()` function:

       **Current** (tries to parse Authorization header):
       ```python
       async def verify_jwt(authorization: str = Header(None)) -> dict[str, Any]:
           # Expects: Authorization: Bearer <token>
           # Gets token from header, validates with PyJWT
       ```

       **New** (reads from session cookie):
       ```python
       async def verify_jwt(request: Request) -> dict[str, Any]:
           # 1. Extract bo1_session cookie from request
           # 2. If no cookie: raise 401 Unauthorized
           # 3. Get session from Redis
           # 4. If no session: raise 401 Unauthorized (expired/invalid)
           # 5. Extract access_token from session
           # 6. Validate token with PyJWT (existing code works!)
           # 7. Check whitelist (existing code works!)
           # 8. Return user dict
       ```

       **Key changes**:
       - Change from `Header(None)` to `Request` parameter
       - Extract cookie instead of header
       - Look up session in Redis
       - Rest of validation logic stays the same!

       ---

       ### **PHASE 4: Frontend Simplification**

       **File: `frontend/src/routes/(auth)/login/+page.svelte`**

       **DELETE** (75+ lines):
       - PKCE generation functions (`generateRandomString`, `sha256`, `base64UrlEncode`)
       - Code verifier storage in sessionStorage
       - Code challenge generation
       - All PKCE logic

       **REPLACE** with simple redirect:
       ```svelte
       <script lang="ts">
         async function handleGoogleSignIn() {
           // Simply redirect to backend login endpoint
           // Backend handles everything (PKCE, redirect, etc.)
           window.location.href = 'http://localhost:8000/api/auth/google/login';
         }
       </script>
       ```

       **That's it!** Login page becomes ~20 lines instead of ~100.

       ---

       **File: `frontend/src/routes/(auth)/callback/+page.svelte`**

       **DELETE ENTIRE FILE** - Not needed anymore!

       Backend handles callback, sets session cookie, redirects to dashboard.

       Frontend callback page is unnecessary.

       **UPDATE** `frontend/src/routes/+layout.svelte` to remove callback route if defined.

       ---

       **File: `frontend/src/lib/stores/auth.ts`**

       **Major refactor**:

       1. **Delete all localStorage token storage**:
          ```typescript
          // DELETE THESE:
          localStorage.setItem('bo1_access_token', data.access_token);
          localStorage.setItem('bo1_refresh_token', data.refresh_token);
          localStorage.getItem('bo1_access_token');
          ```

       2. **Delete `handleOAuthCallback()` function** - Not needed

       3. **Simplify `initAuth()`**:
          ```typescript
          export async function initAuth(): Promise<void> {
            // Just call backend /api/sessions or /api/auth/me
            // Backend checks session cookie automatically
            // If valid session: returns user data
            // If invalid: returns 401

            try {
              const response = await fetch('/api/auth/me', {
                credentials: 'include' // Send cookies
              });

              if (response.ok) {
                const user = await response.json();
                authStore.set({ user, isAuthenticated: true, isLoading: false });
              } else {
                authStore.set({ user: null, isAuthenticated: false, isLoading: false });
              }
            } catch (error) {
              authStore.set({ user: null, isAuthenticated: false, isLoading: false, error });
            }
          }
          ```

       4. **Simplify `logout()`**:
          ```typescript
          export async function logout(): Promise<void> {
            await fetch('/api/auth/logout', {
              method: 'POST',
              credentials: 'include'
            });

            authStore.set({ user: null, isAuthenticated: false, isLoading: false });
            goto('/login');
          }
          ```

       **Result**: Frontend auth code becomes ~50% smaller and much simpler!

       ---

       ### **PHASE 5: Configuration Updates**

       **File: `backend/.env`** (or docker-compose.yml environment)

       Add:
       ```bash
       # Session configuration
       SESSION_COOKIE_NAME=bo1_session
       SESSION_TTL_SECONDS=3600
       OAUTH_SESSION_TTL_SECONDS=600
       COOKIE_SECURE=false  # Set to true in production (HTTPS only)
       COOKIE_DOMAIN=localhost  # Change to .boardof.one in production
       ```

       **File: `frontend/.env`**

       Remove (no longer needed):
       ```bash
       # DELETE THESE:
       VITE_SUPABASE_URL=...
       VITE_GOOGLE_OAUTH_CLIENT_ID=...
       ```

       Keep:
       ```bash
       PUBLIC_API_URL=http://localhost:8000  # For API calls
       ```

       ---

       ## Implementation Instructions

       ### **Order of Implementation**

       1. **First**: Create `backend/api/session.py` with Redis session utilities
       2. **Second**: Test session creation/retrieval manually
       3. **Third**: Implement `/api/auth/google/login` endpoint
       4. **Fourth**: Implement `/api/auth/callback` endpoint
       5. **Fifth**: Test full OAuth flow (manual browser test)
       6. **Sixth**: Update middleware `verify_jwt()`
       7. **Seventh**: Simplify frontend login page
       8. **Eighth**: Delete frontend callback page
       9. **Ninth**: Update frontend auth store
       10. **Tenth**: Test complete flow end-to-end

       ### **Testing Checklist**

       After each phase:

       - [ ] Phase 1: Can create/get/delete sessions in Redis
       - [ ] Phase 2: Can click "Sign in with Google" and get redirected
       - [ ] Phase 3: OAuth completes and redirects to dashboard with session cookie
       - [ ] Phase 4: Can access protected endpoints with session cookie
       - [ ] Phase 5: Frontend shows logged-in state
       - [ ] Phase 6: Can logout and session is destroyed
       - [ ] Phase 7: Tokens NOT in localStorage (check DevTools)
       - [ ] Phase 8: Session cookie is httpOnly (check DevTools → Cannot see value)
       - [ ] Phase 9: Whitelist check works (test with non-whitelisted email)
       - [ ] Phase 10: Complete flow works multiple times

       ### **Critical Security Checks**

       Before declaring success:

       - [ ] No tokens in localStorage (inspect in DevTools)
       - [ ] No tokens in sessionStorage
       - [ ] Session cookie is httpOnly (should say "⚠️ HttpOnly" in DevTools)
       - [ ] Session cookie is SameSite=Lax
       - [ ] CSRF protection works (state parameter validated)
       - [ ] Whitelist checking works
       - [ ] Token refresh works automatically
       - [ ] Logout clears session properly

       ---

       ## Error Handling

       Common issues and fixes:

       **Issue: "CORS error"**
       - Fix: Add CORS middleware for localhost:5173
       - Allow credentials: true

       **Issue: "Cookie not being set"**
       - Fix: Check response has `Set-Cookie` header
       - Fix: Check frontend uses `credentials: 'include'`

       **Issue: "Session not found in Redis"**
       - Fix: Check Redis is running (`docker ps | grep redis`)
       - Fix: Check TTL hasn't expired
       - Fix: Check session_id matches cookie value

       **Issue: "Still getting 'unsupported_grant_type'"**
       - Fix: Ensure `grant_type` is in form body, not JSON
       - Fix: Use `data=` not `json=` in httpx.post()
       - Fix: Verify Content-Type is application/x-www-form-urlencoded

       ---

       ## Output Requirements

       When you're done, provide:

       1. **Summary of changes**: List every file modified/created/deleted
       2. **Testing results**: Did you test each phase? What worked? What failed?
       3. **Code snippets**: Show key parts of implementation
       4. **Next steps**: What should user do to verify it works?
       5. **Security validation**: Confirm httpOnly cookies, no localStorage tokens, etc.

       ---

       ## Important Constraints

       - **DON'T**: Make breaking changes to existing endpoints (unless necessary)
       - **DON'T**: Delete existing user data in database
       - **DO**: Test after each phase
       - **DO**: Log errors verbosely for debugging
       - **DO**: Use existing Redis connection from `bo1.state.redis_manager`
       - **DO**: Use existing database connection for user creation
       - **DO**: Preserve existing JWT validation logic (it's already good!)

       ---

       ## Ultra-Think Before Coding

       Before writing code, think through:

       1. **State management**: Where is state stored at each step?
       2. **Error paths**: What happens if Redis fails? Supabase fails? Network fails?
       3. **Security**: Could an attacker bypass any step?
       4. **Race conditions**: What if user clicks login twice?
       5. **Session cleanup**: How do expired sessions get cleaned up?

       Start implementing now. Be thorough, test as you go, and report back with results.
