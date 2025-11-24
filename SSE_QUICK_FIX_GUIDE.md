# SSE Connection Issues - Quick Fix Guide

**TL;DR**: SSE connections failing due to cookie configuration mismatch. Follow these steps to fix.

---

## Quick Diagnosis

Run these commands to check your configuration:

```bash
# 1. Check if SuperTokens auth is enabled
grep "ENABLE_SUPERTOKENS_AUTH" .env
# Should be: false (MVP mode) or true (production)

# 2. Check cookie settings
grep "COOKIE_" .env
# Local dev should have:
#   COOKIE_SECURE=false
#   COOKIE_DOMAIN=localhost
# Production should have:
#   COOKIE_SECURE=true
#   COOKIE_DOMAIN=boardof.one

# 3. Check API domain matches
grep "PUBLIC_API_URL" .env
grep "SUPERTOKENS_API_DOMAIN" .env
# Both should point to same domain (http://localhost:8000 or https://boardof.one)
```

---

## Fix #1: Session Persistence (Required First)

**Symptom**: Page refresh requires re-authentication

**Fix**: Update `.env` with correct cookie settings:

```bash
# Local Development
ENABLE_SUPERTOKENS_AUTH=false  # MVP mode - no auth
COOKIE_SECURE=false  # HTTP allowed
COOKIE_DOMAIN=localhost
SUPERTOKENS_API_DOMAIN=http://localhost:8000
SUPERTOKENS_WEBSITE_DOMAIN=http://localhost:5173

# Production
ENABLE_SUPERTOKENS_AUTH=true
COOKIE_SECURE=true  # HTTPS required
COOKIE_DOMAIN=boardof.one  # NOT www.boardof.one
SUPERTOKENS_API_DOMAIN=https://boardof.one
SUPERTOKENS_WEBSITE_DOMAIN=https://boardof.one
```

**Test**:
1. Restart backend: `make down && make up`
2. Clear browser cookies: DevTools → Application → Cookies → Clear all
3. Log in with Google
4. Refresh page
5. Should stay logged in (no redirect to /login)

---

## Fix #2: SSE Authentication

**Symptom**: SSE returns 401 "unauthorised"

**Fix**: Once cookies work (Fix #1), SSE auth will work automatically.

**If still failing in MVP mode**:
```bash
# Ensure MVP mode is enabled
echo "ENABLE_SUPERTOKENS_AUTH=false" >> .env

# Restart backend
make down && make up
```

**Test**:
```bash
# Should connect without auth in MVP mode
curl -N http://localhost:8000/api/v1/sessions/{session_id}/stream

# Should see: event: stream_connected
```

---

## Fix #3: Tab Updates Missing

**Symptom**: Sub-problem tabs appear but show no events

**Root Cause**: Events lack `sub_problem_index` in payload

**Fix**: Add to backend event emission (requires code changes)

1. Open `backend/api/events.py`
2. Add `sub_problem_index` parameter to all event functions
3. Update event emission calls to pass `sub_problem_index`

**Example**:
```python
# Before
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

# After
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

**Test**:
1. Create meeting with complex problem (3+ sub-problems)
2. Open DevTools console
3. Check event logs for `sub_problem_index: 0, 1, 2, etc.`
4. Click tabs - events should appear in correct tabs

---

## Verification Checklist

After applying fixes, verify:

- [ ] User logs in with Google OAuth
- [ ] Session persists after page refresh (no re-auth)
- [ ] SSE connection shows "Connected" status (green dot)
- [ ] Events appear in real-time
- [ ] Sub-problem tabs show correct events
- [ ] Page refresh mid-deliberation reconnects automatically

---

## Common Issues

### "Still getting 401 on SSE"

Check logs for cookie presence:
```bash
# Backend logs
docker logs -f boardofone-api-1 | grep "SSE"

# Should see authenticated user_id, not "unauthorized"
```

If no cookies in request:
1. Verify `COOKIE_DOMAIN` matches your domain exactly
2. Clear browser cookies completely
3. Log in again
4. Check cookies exist: DevTools → Application → Cookies

### "Events not showing in tabs"

Add debug logging:
```typescript
// frontend/src/routes/(app)/meeting/[id]/+page.svelte
// Add after line 393 (in handleSSEEvent function)
console.log('[Event Debug]', {
    type: eventType,
    sub_problem_index: payload.sub_problem_index,
    has_index: payload.sub_problem_index !== undefined,
});
```

If `sub_problem_index` is undefined, backend events need fixing (Fix #3).

### "Docker container can't reach API"

If using Docker, ensure API_URL uses `localhost`, not container name:
```yaml
# docker-compose.yml
services:
  frontend:
    environment:
      - PUBLIC_API_URL=http://localhost:8000  # NOT http://api:8000
```

---

## Emergency Rollback

If fixes break something:

```bash
# Restore .env from git
git checkout .env

# Restart all services
make down && make up

# Clear browser data
# DevTools → Application → Clear storage → Clear site data
```

---

## Need More Details?

See full analysis: `SSE_CONNECTION_ISSUES.md`
