# SSE Connection Issues Analysis

**Date**: 2025-01-24
**Status**: Root causes identified, fixes documented
**Severity**: High (blocks real-time deliberation updates)

---

## Executive Summary

The SSE (Server-Sent Events) streaming connection for real-time deliberation updates is experiencing multiple failures:

1. **SSE 404 Errors**: Frontend attempting connection but getting 404 responses
2. **Authentication Failures**: SSE endpoint returns `{"message":"unauthorised"}` when auth is enabled
3. **Tab Updates Not Working**: Sub-problem tabs populate but show no event updates
4. **Session Persistence Issues**: Page refresh requires re-authentication with Google

**Root Cause**: The SSE client implementation (`SSEClient` class) correctly uses `credentials: 'include'` to send cookies, **BUT** the issue is **environmental configuration mismatch** - SuperTokens authentication is likely not properly configured or session cookies are not being persisted across requests due to cookie domain/secure settings.

**Impact**: Users cannot see real-time deliberation progress. System appears broken/frozen after session creation.

---

## Issue #1: SSE 404 Errors

### Symptoms
- Browser console shows: `Failed to load resource: the server responded with a status of 404 (Not Found)`
- URL attempted: `/api/v1/sessions/{session_id}/stream`

### Analysis

**GOOD NEWS**: The endpoint path is **CORRECT** in both frontend and backend:

**Frontend** (`frontend/src/routes/(app)/meeting/[id]/+page.svelte:473`):
```typescript
sseClient = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
    onOpen: () => { ... },
    onError: (err) => { ... },
    eventHandlers,
});
```

**Backend** (`backend/api/streaming.py:358-384`):
```python
@router.get(
    "/{session_id}/stream",
    summary="Stream deliberation events via SSE",
    # ...
)
async def stream_deliberation(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
```

**Router prefix** (`backend/api/main.py:201`):
```python
app.include_router(streaming.router, prefix="/api", tags=["streaming"])
```

**Router prefix in streaming.py** (`backend/api/streaming.py:26`):
```python
router = APIRouter(prefix="/v1/sessions", tags=["streaming"])
```

**Combined path**: `/api` + `/v1/sessions` + `/{session_id}/stream` = `/api/v1/sessions/{session_id}/stream` ✓

### Root Cause

The 404 errors are **NOT** caused by path mismatch. Likely causes:

1. **Session doesn't exist in Redis** - The session metadata must exist before SSE connection
2. **Race condition** - Frontend connects before backend creates session metadata
3. **Network/proxy issue** - nginx or intermediate proxy not routing correctly

### Evidence from Code

The endpoint has built-in validation (`streaming.py:414-420`):
```python
# Check if session metadata exists (created via POST /api/v1/sessions)
metadata = redis_manager.load_metadata(session_id)
if not metadata:
    raise HTTPException(
        status_code=404,
        detail=f"Session not found: {session_id}",
    )
```

**This means 404 occurs when session metadata doesn't exist in Redis**, not from URL mismatch.

### Proposed Fix

**Option A: Frontend - Add session creation verification**
```typescript
// Before connecting to SSE, verify session exists
async function startEventStream() {
    // Verify session exists first
    try {
        const session = await apiClient.getSession(sessionId);
        if (!session) {
            throw new Error('Session not found');
        }
    } catch (err) {
        console.error('[SSE] Session verification failed:', err);
        error = 'Session not found. Please try creating a new meeting.';
        return;
    }

    // Now connect to SSE stream
    sseClient = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
        // ...
    });
}
```

**Option B: Backend - Increase wait timeout**

The backend already waits up to 10 seconds for state initialization (`streaming.py:424-448`). If race condition persists, increase timeout:

```python
# Current: max_wait_seconds = 10
# Increase to: max_wait_seconds = 30
```

---

## Issue #2: SSE Authentication Failures

### Symptoms
- curl test shows: `{"message":"unauthorised"}`
- SSE connection fails with 401 when SuperTokens auth is enabled

### Analysis

**The SSE client implementation is CORRECT**:

**Frontend SSE Client** (`frontend/src/lib/utils/sse.ts:37-45`):
```typescript
const response = await fetch(this.url, {
    method: 'GET',
    headers: {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
    },
    credentials: 'include', // ✓ CRITICAL: Send cookies
    signal: this.abortController.signal,
});
```

**Backend Auth Middleware** (`backend/api/streaming.py:385-388`):
```python
async def stream_deliberation(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user),  # ✓ Requires auth
) -> StreamingResponse:
```

**SuperTokens Session Verification** (`backend/api/middleware/auth.py:65-91`):
```python
async def get_current_user(
    session: SessionContainer = Depends(verify_session()),  # ✓ Validates session cookie
) -> dict[str, Any]:
    # MVP: Skip authentication, return hardcoded user
    if not ENABLE_SUPERTOKENS_AUTH:
        return {"user_id": DEFAULT_USER_ID, ...}

    # Production: Use SuperTokens session
    user_id = session.get_user_id()
    # ...
```

### Root Cause

**Environmental Configuration Issue** - One of:

1. **SuperTokens auth is disabled** (`ENABLE_SUPERTOKENS_AUTH=false` in MVP mode)
   - Should work fine in MVP mode (hardcoded user)
   - If getting 401, SuperTokens might be enabled but cookies not working

2. **Cookie settings incorrect**:
   - `COOKIE_SECURE=false` required for local dev (http://)
   - `COOKIE_SECURE=true` required for production (https://)
   - `COOKIE_DOMAIN` must match domain (e.g., `boardof.one` not `www.boardof.one`)

3. **Session cookies not being sent**:
   - Browser security might be blocking cookies (SameSite policy)
   - Cookies might have expired or been cleared

### Evidence from Code

**SuperTokens Configuration** (`backend/api/supertokens_config.py:163-186`):
```python
cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
cookie_domain = os.getenv("COOKIE_DOMAIN", "localhost")

init(
    supertokens_config=get_supertokens_config(),
    app_info=get_app_info(),
    framework="fastapi",
    recipe_list=[
        thirdparty.init(...),
        session.init(
            cookie_secure=cookie_secure,  # HTTPS only in production
            cookie_domain=cookie_domain,  # .boardof.one in production
            cookie_same_site="lax",  # CSRF protection
        ),
    ],
    mode="asgi",
)
```

**Key Points**:
- `cookie_same_site="lax"` allows cookies on cross-site navigation (e.g., OAuth redirects)
- `cookie_secure=true` requires HTTPS (cookies won't be sent over HTTP)
- `cookie_domain` must match the domain making the request

### Proposed Fix

**Step 1: Verify Environment Variables**

Check `.env` file for correct settings:

```bash
# Local development (HTTP)
ENABLE_SUPERTOKENS_AUTH=false  # MVP mode - no auth required
COOKIE_SECURE=false  # Allow cookies over HTTP
COOKIE_DOMAIN=localhost

# Production (HTTPS)
ENABLE_SUPERTOKENS_AUTH=true  # Full auth enabled
COOKIE_SECURE=true  # Require HTTPS
COOKIE_DOMAIN=boardof.one  # Match production domain
```

**Step 2: Add Session Debugging**

Add logging to SSE client to see if cookies are being sent:

```typescript
// frontend/src/lib/utils/sse.ts
async connect(): Promise<void> {
    console.log('[SSE] Connecting to:', this.url);
    console.log('[SSE] Credentials mode: include (will send cookies)');

    const response = await fetch(this.url, {
        method: 'GET',
        headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
        },
        credentials: 'include',
        signal: this.abortController.signal,
    });

    console.log('[SSE] Response status:', response.status);
    console.log('[SSE] Response headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
        const errorText = await response.text();
        console.error('[SSE] Connection failed:', errorText);
        throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
    }
    // ...
}
```

**Step 3: Test Cookie Presence**

Add backend logging to verify cookies are received:

```python
# backend/api/streaming.py
@router.get("/{session_id}/stream")
async def stream_deliberation(
    request: Request,  # Add Request parameter
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    # Log cookies for debugging
    logger.info(f"SSE connection request cookies: {request.cookies.keys()}")
    logger.info(f"Authenticated user: {user.get('user_id')}")
    # ...
```

**Step 4: Handle MVP Mode Correctly**

If using MVP mode (`ENABLE_SUPERTOKENS_AUTH=false`), the SSE endpoint should work without cookies. Verify MVP mode is actually enabled:

```bash
# Check environment variable
echo $ENABLE_SUPERTOKENS_AUTH

# Should output: false (or be unset, which defaults to true)
```

If you want MVP mode (no auth), ensure `.env` has:
```bash
ENABLE_SUPERTOKENS_AUTH=false
```

---

## Issue #3: Tab Updates Not Working

### Symptoms
- Sub-problem tabs appear correctly
- Clicking tabs shows sub-problem headers/metrics
- But no event updates appear within tabs
- Have to refresh page to see new events

### Analysis

**The tab filtering logic is CORRECT**:

**Sub-problem tab content filtering** (`frontend/src/routes/(app)/meeting/[id]/+page.svelte:1109-1120`):
```typescript
{@const subGroupedEvents = groupedEvents.filter(group => {
    if (group.type === 'single' && group.event) {
        const eventSubIndex = group.event.data.sub_problem_index as number | undefined;
        return eventSubIndex === tabIndex;
    } else if (group.type === 'round' || group.type === 'expert_panel') {
        if (group.events && group.events.length > 0) {
            const eventSubIndex = group.events[0].data.sub_problem_index as number | undefined;
            return eventSubIndex === tabIndex;
        }
    }
    return false;
})}
```

**Event indexing by sub-problem** (`+page.svelte:866-883`):
```typescript
$effect(() => {
    if (events.length !== lastEventCountForIndex) {
        const index = new Map<number, SSEEvent[]>();

        for (const event of events) {
            const subIndex = event.data.sub_problem_index as number | undefined;
            if (subIndex !== undefined) {
                const existing = index.get(subIndex) || [];
                existing.push(event);
                index.set(subIndex, existing);
            }
        }

        eventsBySubProblemCache = index;
        lastEventCountForIndex = events.length;
    }
});
```

### Root Cause

**Events are not arriving from SSE stream**, so tabs remain empty. This is a **symptom** of Issues #1 and #2 (404 or 401 errors preventing SSE connection).

**Alternative theory**: Events ARE arriving but lack `sub_problem_index` in their data payload.

### Evidence

Check backend event emission to verify `sub_problem_index` is included:

**Example: Contribution event** (`backend/api/events.py`):
```python
def contribution_event(
    session_id: str,
    persona_code: str,
    persona_name: str,
    content: str,
    round_number: int,
) -> str:
    data = {
        "session_id": session_id,
        "persona_code": persona_code,
        "persona_name": persona_name,
        "content": content,
        "round_number": round_number,
        "timestamp": get_timestamp(),
    }
    return format_sse_event("contribution", data)
```

**ISSUE**: The `sub_problem_index` is **NOT** included in contribution event data!

### Proposed Fix

**Step 1: Add sub_problem_index to all event payloads**

Modify `backend/api/events.py` to include `sub_problem_index` in all relevant events:

```python
def contribution_event(
    session_id: str,
    persona_code: str,
    persona_name: str,
    content: str,
    round_number: int,
    sub_problem_index: int | None = None,  # ADD THIS
) -> str:
    data = {
        "session_id": session_id,
        "persona_code": persona_code,
        "persona_name": persona_name,
        "content": content,
        "round_number": round_number,
        "sub_problem_index": sub_problem_index,  # ADD THIS
        "timestamp": get_timestamp(),
    }
    return format_sse_event("contribution", data)
```

**Step 2: Pass sub_problem_index when emitting events**

Find where events are emitted (likely in graph nodes) and pass `sub_problem_index`:

```python
# Example: In graph node that emits contribution events
from backend.api.events import contribution_event

# Get current sub_problem_index from state
sub_problem_index = state.get("current_sub_problem_index")

# Emit event with sub_problem_index
event_str = contribution_event(
    session_id=session_id,
    persona_code=persona.code,
    persona_name=persona.name,
    content=contribution.content,
    round_number=round_number,
    sub_problem_index=sub_problem_index,  # PASS THIS
)
```

**Step 3: Verify event data in browser console**

Add debug logging in frontend to see actual event data:

```typescript
// frontend/src/routes/(app)/meeting/[id]/+page.svelte
const handleSSEEvent = (eventType: string, event: MessageEvent) => {
    try {
        const payload = JSON.parse(event.data);

        // DEBUG: Log sub_problem_index for all events
        console.log(`[Event Debug] ${eventType}:`, {
            sub_problem_index: payload.sub_problem_index,
            persona: payload.persona_name || payload.persona_code,
            round: payload.round_number,
        });

        const sseEvent: SSEEvent = {
            event_type: eventType,
            session_id: payload.session_id || sessionId,
            timestamp: payload.timestamp || new Date().toISOString(),
            data: payload
        };

        addEvent(sseEvent);
        // ...
    } catch (err) {
        console.error(`Failed to parse ${eventType} event:`, err);
    }
};
```

---

## Issue #4: Session Persistence (Page Refresh Requires Re-auth)

### Symptoms
- User logs in with Google OAuth
- Page refresh loses authentication state
- User prompted to log in again

### Analysis

**The auth initialization is CORRECT**:

**Auth store initialization** (`frontend/src/lib/stores/auth.ts:61-120`):
```typescript
export async function initAuth(): Promise<void> {
    if (!browser) return;

    // Check if SuperTokens session exists (checks httpOnly cookie)
    const sessionExists = await Session.doesSessionExist();

    if (sessionExists) {
        // Get user info from backend
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
            credentials: 'include', // ✓ Send cookies
        });

        if (response.ok) {
            const userData = await response.json();
            authStore.set({
                user: userData,
                isAuthenticated: true,
                isLoading: false,
                error: null
            });
        } else {
            // Session exists but /me failed - sign out
            await signOut();
        }
    } else {
        // No session
        authStore.set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
        });
    }
}
```

**SuperTokens frontend initialization** (`frontend/src/lib/supertokens.ts:20-38`):
```typescript
export function initSuperTokens() {
    if (isInitialized) {
        return; // Already initialized
    }

    SuperTokens.init({
        appInfo: {
            apiDomain: env.PUBLIC_API_URL || "http://localhost:8000",
            apiBasePath: "/api/auth",
            appName: "Board of One",
        },
        recipeList: [
            Session.init(),  // ✓ Session management
            ThirdParty.init(),  // ✓ OAuth support
        ],
    });

    isInitialized = true;
}
```

### Root Cause

**Cookie configuration mismatch** - Possible causes:

1. **Cookie domain mismatch**:
   - Frontend domain: `localhost:5173` (dev) or `boardof.one` (prod)
   - Backend cookie domain: `localhost` (dev) or `boardof.one` (prod)
   - If mismatch, cookies won't persist across requests

2. **Cookie secure setting incorrect**:
   - Development: `COOKIE_SECURE=false` (HTTP)
   - Production: `COOKIE_SECURE=true` (HTTPS)
   - If set to `true` on HTTP, cookies won't be set

3. **Cookie SameSite policy too strict**:
   - Current: `cookie_same_site="lax"` ✓ (Correct for OAuth)
   - If changed to `strict`, OAuth redirects might lose session

4. **Browser blocking cookies**:
   - Private/incognito mode
   - Third-party cookie blocking
   - Browser extensions blocking cookies

### Proposed Fix

**Step 1: Verify Cookie Settings Match Environment**

**Local Development** (`.env`):
```bash
# Backend
COOKIE_SECURE=false
COOKIE_DOMAIN=localhost
SUPERTOKENS_API_DOMAIN=http://localhost:8000
SUPERTOKENS_WEBSITE_DOMAIN=http://localhost:5173

# Frontend (.env.local or docker-compose.yml)
PUBLIC_API_URL=http://localhost:8000
```

**Production** (`.env`):
```bash
# Backend
COOKIE_SECURE=true
COOKIE_DOMAIN=boardof.one
SUPERTOKENS_API_DOMAIN=https://boardof.one
SUPERTOKENS_WEBSITE_DOMAIN=https://boardof.one

# Frontend
PUBLIC_API_URL=https://boardof.one
```

**Step 2: Add Cookie Debugging**

Check if cookies are actually being set after login:

```typescript
// frontend/src/lib/stores/auth.ts
export async function initAuth(): Promise<void> {
    if (!browser) return;

    console.log('[Auth] Initializing auth...');
    console.log('[Auth] All cookies:', document.cookie);  // DEBUG: See all cookies

    const sessionExists = await Session.doesSessionExist();
    console.log('[Auth] Session exists:', sessionExists);

    if (sessionExists) {
        console.log('[Auth] Session cookies should be present');
        // ...
    } else {
        console.log('[Auth] No session found - cookies:', document.cookie);
    }
}
```

**IMPORTANT**: SuperTokens session cookies are **httpOnly**, so they **will NOT appear** in `document.cookie`. This is expected and secure. Instead, check:

```typescript
// Check network tab in browser DevTools
// Look for Set-Cookie headers in response to /api/auth/signin
// Example cookies:
// - sAccessToken (httpOnly, secure)
// - sRefreshToken (httpOnly, secure)
```

**Step 3: Test Cookie Persistence**

1. Log in with Google OAuth
2. Open DevTools → Application → Cookies → `http://localhost:8000` (or `https://boardof.one`)
3. Verify cookies are present:
   - `sAccessToken` (httpOnly: true, secure: matches HTTPS/HTTP)
   - `sRefreshToken` (httpOnly: true, secure: matches HTTPS/HTTP)
   - `sFrontToken` (httpOnly: false - visible to JS)
4. Refresh page
5. Check if cookies are still present
6. Check console for auth initialization logs

**Step 4: Fix Cookie Domain for Local Dev**

If using Docker, ensure frontend and backend share cookie domain:

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - COOKIE_DOMAIN=localhost  # NOT 'api' or '0.0.0.0'
      - COOKIE_SECURE=false
      - SUPERTOKENS_API_DOMAIN=http://localhost:8000
      - SUPERTOKENS_WEBSITE_DOMAIN=http://localhost:5173

  frontend:
    environment:
      - PUBLIC_API_URL=http://localhost:8000  # NOT http://api:8000
```

**Why**: Cookies set on `api:8000` won't be accessible from `localhost:5173`.

---

## Proposed Fixes - Prioritized Implementation Plan

### Priority 1: Fix Session Persistence (Issue #4)
**Impact**: Blocks all functionality after page refresh
**Effort**: Low (configuration fix)

1. Verify `.env` cookie settings match environment (HTTP vs HTTPS)
2. Test cookie presence after login (DevTools → Application → Cookies)
3. Add debug logging to auth initialization
4. If using Docker, ensure shared cookie domain (`localhost`)

**Test**:
```bash
1. Clear browser cookies
2. Log in with Google OAuth
3. Open DevTools → Application → Cookies
4. Verify sAccessToken and sRefreshToken are present
5. Refresh page
6. Verify cookies persist and auth state is restored
```

### Priority 2: Fix SSE Authentication (Issue #2)
**Impact**: Blocks real-time updates
**Effort**: Low (configuration fix)

1. Verify `ENABLE_SUPERTOKENS_AUTH` setting (false for MVP, true for prod)
2. Add cookie debugging to SSE endpoint
3. Test SSE connection with auth disabled (MVP mode)
4. Once cookies work (Priority 1), SSE auth should work automatically

**Test**:
```bash
# MVP mode (no auth)
ENABLE_SUPERTOKENS_AUTH=false

# Test SSE connection
curl -N http://localhost:8000/api/v1/sessions/{session_id}/stream
# Should connect (no 401 error)

# Production mode (with auth)
ENABLE_SUPERTOKENS_AUTH=true

# Test SSE connection with cookies
curl -N -b cookies.txt http://localhost:8000/api/v1/sessions/{session_id}/stream
# Should connect (no 401 error)
```

### Priority 3: Fix Tab Updates (Issue #3)
**Impact**: Medium (tab UI broken)
**Effort**: Medium (requires backend changes)

1. Add `sub_problem_index` to all event payloads in `backend/api/events.py`
2. Pass `sub_problem_index` when emitting events from graph nodes
3. Add debug logging to verify events have `sub_problem_index`
4. Test tab filtering logic with debug logs

**Test**:
```typescript
// Browser console
1. Open meeting page with multiple sub-problems
2. Check console for event logs showing sub_problem_index
3. Click different tabs
4. Verify events appear in correct tabs
```

### Priority 4: Improve Session Creation Validation (Issue #1)
**Impact**: Low (rare race condition)
**Effort**: Low (add validation)

1. Add session existence check before SSE connection
2. Increase backend wait timeout if needed (10s → 30s)
3. Add better error messaging for 404 errors

**Test**:
```typescript
// Simulate race condition
1. Create session
2. Immediately connect to SSE (before session metadata is written)
3. Should either wait or show clear error message
```

---

## Testing Plan

### Test Environment Setup

**Required**:
- Clean browser session (no cached cookies)
- Redis running and empty
- PostgreSQL running
- Backend API running
- Frontend dev server running

### Test Case 1: Session Persistence

**Steps**:
1. Clear all cookies (DevTools → Application → Cookies → Clear all)
2. Navigate to `/login`
3. Click "Sign in with Google"
4. Complete OAuth flow
5. Verify redirected to dashboard
6. Open DevTools → Application → Cookies
7. Verify `sAccessToken`, `sRefreshToken`, `sFrontToken` present
8. Refresh page (Cmd+R or Ctrl+R)
9. Verify still authenticated (no redirect to /login)
10. Open new tab with same domain
11. Verify still authenticated

**Expected Result**: Authentication persists across refresh and new tabs

**Debug Commands**:
```bash
# Backend logs - check cookie setting
docker logs boardofone-api-1 | grep "Set-Cookie"

# Frontend console - check auth initialization
# Should see: "[Auth] Session exists: true"
# Should NOT see: "[Auth] No session found"
```

### Test Case 2: SSE Connection

**Prerequisites**: Test Case 1 passed (session persists)

**Steps**:
1. Navigate to dashboard
2. Click "Start New Meeting"
3. Enter problem statement
4. Submit
5. Wait for redirect to `/meeting/{id}`
6. Open DevTools → Network tab
7. Filter by "stream"
8. Verify SSE connection established:
   - Status: 200 OK
   - Type: EventStream
   - Size: (pending, streaming)
9. Monitor console for SSE events:
   - `[SSE] Connected to session {id}`
   - Event logs showing incoming events

**Expected Result**: SSE connection established, events streaming

**Debug Commands**:
```bash
# Backend logs - check SSE connection
docker logs -f boardofone-api-1 | grep "SSE"

# Should see:
# - "SSE client subscribed to events:session_id"
# - Event emission logs

# Test SSE endpoint directly (with session cookies)
curl -N -b cookies.txt http://localhost:8000/api/v1/sessions/{id}/stream
```

### Test Case 3: Sub-Problem Tab Updates

**Prerequisites**: Test Case 2 passed (SSE connected)

**Steps**:
1. Create meeting with complex problem (should decompose into 3+ sub-problems)
2. Wait for decomposition complete
3. Verify sub-problem tabs appear
4. Click each tab
5. Verify events appear in correct tabs:
   - Expert panel selection
   - Round contributions
   - Convergence checks
   - Synthesis
6. Monitor browser console for event debugging:
   - Check `sub_problem_index` in event payloads
   - Verify tab filtering logic

**Expected Result**: Each tab shows only events for that sub-problem

**Debug Commands**:
```typescript
// Browser console - check event data
// Add to frontend code temporarily:
console.log('[Event Debug]', {
    event_type: event.event_type,
    sub_problem_index: event.data.sub_problem_index,
    has_index: event.data.sub_problem_index !== undefined
});

// Should see sub_problem_index: 0, 1, 2, etc. for each event
```

### Test Case 4: Full Deliberation Flow

**Prerequisites**: All previous tests passed

**Steps**:
1. Create new meeting
2. Let deliberation run to completion
3. Verify all events appear in correct order
4. Verify final synthesis appears
5. Refresh page mid-deliberation
6. Verify auth persists (no re-login)
7. Verify SSE reconnects automatically
8. Verify historical events loaded
9. Verify new events continue streaming

**Expected Result**: Full deliberation completes with no errors

---

## Additional Investigation

### Check nginx Configuration (Production Only)

If deploying to production with nginx, verify SSE proxy settings:

```nginx
# nginx.conf - SSE-specific settings
location /api/v1/sessions {
    proxy_pass http://api:8000;

    # SSE-specific headers
    proxy_http_version 1.1;
    proxy_set_header Connection '';  # Disable Connection: close
    proxy_buffering off;  # Critical for SSE
    proxy_cache off;  # Disable caching
    proxy_read_timeout 3600s;  # Long timeout for SSE

    # Preserve client cookies
    proxy_set_header Cookie $http_cookie;

    # Disable buffering for SSE streams
    chunked_transfer_encoding on;

    # Forward client IP
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**Critical settings**:
- `proxy_buffering off;` - Without this, nginx buffers SSE events
- `proxy_http_version 1.1;` - SSE requires HTTP/1.1
- `proxy_set_header Connection '';` - Keep connection alive
- `proxy_read_timeout 3600s;` - Prevent timeout for long deliberations

### Check CORS Configuration

Verify CORS allows credentials (cookies):

```python
# backend/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Specific origins, not "*"
    allow_credentials=True,  # ✓ Required for cookies
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["front-token"],  # SuperTokens front-token
)
```

**Critical**:
- `allow_credentials=True` - Required for cookies
- `allow_origins` - Must be specific origins, NOT `["*"]` (wildcard blocks credentials)

---

## Success Criteria

All fixes complete when:

1. ✓ User logs in with Google OAuth
2. ✓ Session persists across page refresh (no re-authentication)
3. ✓ SSE connection establishes successfully (no 404 or 401 errors)
4. ✓ Real-time events stream to frontend
5. ✓ Sub-problem tabs show events for correct sub-problem
6. ✓ Full deliberation completes from start to finish
7. ✓ Page refresh mid-deliberation reconnects SSE and loads historical events

---

## References

**Code Files Analyzed**:
- `backend/api/streaming.py` - SSE endpoint implementation
- `backend/api/middleware/auth.py` - SuperTokens authentication
- `backend/api/supertokens_config.py` - SuperTokens configuration
- `backend/api/main.py` - FastAPI app setup, CORS
- `frontend/src/lib/utils/sse.ts` - SSE client implementation
- `frontend/src/lib/supertokens.ts` - SuperTokens frontend init
- `frontend/src/lib/stores/auth.ts` - Auth state management
- `frontend/src/lib/api/client.ts` - API client with credentials
- `frontend/src/routes/(app)/meeting/[id]/+page.svelte` - Meeting page

**Key Documentation**:
- CLAUDE.md - Project architecture and constraints
- STREAMING_IMPLEMENTATION_PLAN.md - SSE streaming design
- SuperTokens BFF Pattern: https://supertokens.com/docs/thirdparty/common-customizations/sessions/with-jwt/about

**Environment Variables**:
```bash
# Authentication
ENABLE_SUPERTOKENS_AUTH=false  # MVP mode (or true for production)
COOKIE_SECURE=false  # HTTP (or true for HTTPS)
COOKIE_DOMAIN=localhost  # Or production domain

# SuperTokens
SUPERTOKENS_API_DOMAIN=http://localhost:8000
SUPERTOKENS_WEBSITE_DOMAIN=http://localhost:5173
SUPERTOKENS_CONNECTION_URI=http://supertokens:3567

# Frontend
PUBLIC_API_URL=http://localhost:8000
```
