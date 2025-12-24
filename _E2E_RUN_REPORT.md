---
run_id: e2e-prod-20241224-191300
started_at_utc: 2024-12-24T19:13:00Z
ended_at_utc: 2024-12-24T19:17:30Z
env:
  base_url: https://boardof.one
  browser: chromium
  viewport: 1440x900
account:
  user: e2e.test@boardof.one
  user_id: 991cac1b-a2e9-4164-a7fe-66082180e035
scenario: golden_meeting_v1
---

# Board of One — Automated E2E Exploratory Run Report

## Summary

- Result: **FAIL**
- Total issues: 5
- Critical: 2 / Major: 2 / Minor: 1
- Top 3 problems:
  1. SSE stream returns 409 for paused sessions, frontend treats as fatal error
  2. SSE rate limit (5/min) too restrictive, causes 429 during reconnect attempts
  3. Dashboard API errors (500) on value-metrics and context endpoints

## Timeline

| Step | Action | Expected | Observed | Duration | Evidence |
|-----:|--------|----------|----------|----------|----------|
| 0.1 | E2E session endpoint | Cookies set | Session created successfully via new `/api/e2e/session` endpoint | 2s | screenshot: e2e-step1-authenticated.png |
| 1 | Verify auth | Dashboard loads | Authenticated as e2e.test@boardof.one | 3s | screenshot: e2e-step2-dashboard-new-meeting-dialog.png |
| 2 | New meeting nav | Creation page | Onboarding dialog appeared, navigated to /meeting/new | 5s | screenshot: e2e-step2-dashboard-new-meeting-dialog.png |
| 3 | Enter problem | Text accepted | Problem text entered (198 chars), Start button enabled | 3s | screenshot: e2e-step3-problem-entered.png |
| 4 | Start meeting | Meeting begins | Session created (201), started (202), SSE 409 errors began | 2s | screenshot: e2e-step4-meeting-started-sse-error.png |
| 5 | Wait completion | Meeting completes | Session progressed through decomposition (36s), then paused for clarification. Frontend shows "Meeting Failed" due to SSE 409 | 2m | screenshot: e2e-step5-meeting-failed-sse-409.png |
| 6 | View results | Report visible | **BLOCKED** - Could not proceed due to SSE failure | - | - |
| 7 | Create action | Action created | **BLOCKED** | - | - |
| 8 | Verify action | Action in list | **BLOCKED** | - | - |
| 9 | End session | Browser closed | Closed after capturing evidence | 1s | screenshot: e2e-final-state.png |

## Issues

### ISS-001 — SSE returns 409 for paused sessions, frontend shows "Meeting Failed"

- Severity: **Critical**
- Category: Backend/UX
- Where: `/api/v1/sessions/{id}/stream` + Meeting progress page
- Repro steps:
  1. Start a new meeting
  2. Wait for session to reach clarification_needed phase
  3. Backend pauses session and returns 409 on SSE stream
  4. Frontend shows "Meeting Failed" error instead of clarification UI
- Observed:
  - Backend correctly pauses session and returns 409 with message "Session is paused. Call /resume endpoint to continue."
  - Frontend treats 409 as a fatal connection error
  - Meeting progress visible (3 focus areas) but user cannot interact
- Expected:
  - Frontend should check session status when receiving 409
  - If paused, show clarification UI instead of error
- Evidence:
  - Screenshot: e2e-step5-meeting-failed-sse-409.png
  - Console: `[SSE] Connection error: Error: SSE connection failed: 409`
  - Network: `GET /api/v1/sessions/.../stream => 409`
  - API logs: `status=paused, phase=clarification_needed`
- Likely cause:
  - Frontend SSE client treats all non-200 responses as errors
  - Missing logic to distinguish "paused" 409 from actual conflicts
- Suggested improvements:
  - Frontend: When SSE returns 409, fetch session status via `/sessions/{id}` endpoint
  - Frontend: If status is "paused", show clarification prompt instead of error
  - Alternative: Backend could return 200 with SSE event `type: paused` instead of closing connection
- Workaround:
  - None available to end users

### ISS-002 — SSE rate limit too restrictive (5/min causes 429 during retries)

- Severity: **Critical**
- Category: Backend/Performance
- Where: `/api/v1/sessions/{id}/stream` rate limiter
- Repro steps:
  1. SSE connection fails (e.g., due to 409)
  2. Frontend retries with exponential backoff
  3. After 5 attempts within 1 minute, 429 rate limit kicks in
  4. All further reconnection attempts fail
- Observed:
  - `ratelimit 5 per 1 minute (172.19.0.1) exceeded at endpoint: /api/v1/sessions/.../stream`
  - User cannot recover from transient errors
- Expected:
  - SSE endpoint should allow reconnection attempts
  - Rate limit should be per-session, not global per-IP
- Evidence:
  - Console: `[SSE] Connection error: Error: SSE connection failed: 429`
  - API logs: `slowapi | ratelimit 5 per 1 minute exceeded`
- Likely cause:
  - Rate limit configured too aggressively for SSE which requires reconnection
- Suggested improvements:
  - Increase rate limit to 20/min for SSE stream endpoint
  - Or implement per-session rate limiting instead of per-IP
  - Frontend: Implement longer backoff after 429 (e.g., 30s)
- Workaround:
  - Wait 1 minute before refreshing page

### ISS-003 — Dashboard API 500 errors on value-metrics and context endpoints

- Severity: **Major**
- Category: Backend
- Where: `/api/v1/user/value-metrics`, `/api/v1/context`
- Repro steps:
  1. Login as e2e.test@boardof.one
  2. Navigate to dashboard
  3. Observe network errors
- Observed:
  - `GET /api/v1/user/value-metrics => 500`
  - `GET /api/v1/context => 500`
  - Dashboard still loads but with missing data
- Expected:
  - Endpoints should return 200 with empty/default data for new users
- Evidence:
  - Network: `GET /api/v1/user/value-metrics => [500]`
  - Network: `GET /api/v1/context => [500]`
  - Console: `Data fetch failed: ApiClientError: Failed to get value metrics`
- Likely cause:
  - Missing null/empty handling for users without value metrics or context
- Suggested improvements:
  - Return empty array/object with 200 for users without data
  - Add proper error handling for missing user data
- Workaround:
  - Errors don't block dashboard usage, just hide some widgets

### ISS-004 — Event persistence verification failed (Redis/PostgreSQL mismatch)

- Severity: **Major**
- Category: Backend/Data
- Where: `backend/api/event_collector.py`
- Repro steps:
  1. Start meeting
  2. Let it progress through decomposition
  3. Check API logs
- Observed:
  - `[VERIFY] Mismatch for session: Redis=9, PostgreSQL=7`
  - `[DB_WRITE_ERROR] EVENT PERSISTENCE VERIFICATION FAILED`
- Expected:
  - Event counts should match between Redis and PostgreSQL
- Evidence:
  - API logs: `Mismatch for bo1_301e07c4-a1ee-4db7-967d-2baa04f9b99b (attempt 2/2): Redis=9, PostgreSQL=7`
- Likely cause:
  - Race condition in event persistence
  - Some events written to Redis but not synced to PostgreSQL before verification
- Suggested improvements:
  - Increase verification retry delay
  - Or implement eventual consistency model with background sync
- Workaround:
  - Events are in Redis; meeting can continue even if PostgreSQL sync fails

### ISS-005 — Onboarding dialog blocks direct navigation

- Severity: **Minor**
- Category: UX
- Where: Dashboard onboarding tour
- Repro steps:
  1. Login as new user
  2. Click "Start New Meeting" card on dashboard
  3. Onboarding dialog appears instead of navigation
  4. Must dismiss or complete tour to navigate
- Observed:
  - "beforeunload" dialog: "The onboarding tour is in progress. Leave the tour and navigate away?"
- Expected:
  - Direct navigation should work without modal interruption
- Evidence:
  - Console: `Blocked confirm('The onboarding tour is in progress...')`
- Likely cause:
  - Onboarding tour has beforeunload handler
- Suggested improvements:
  - Allow navigation to key flows (new meeting) without tour completion
  - Or auto-dismiss tour when user clicks primary CTA
- Workaround:
  - Accept the dialog to proceed

## Positive Observations

1. **E2E Session Injection Works**: New `/api/e2e/session` endpoint successfully creates authenticated sessions without OAuth flow
2. **Meeting Creation Flow Works**: Problem text entry, validation, and session creation all function correctly
3. **Backend Deliberation Runs**: LLM calls complete successfully (decomposition in 36s, $0.0454 cost)
4. **Focus Areas Generated**: 3 sub-problems correctly identified from the problem statement
5. **Session State Preserved**: Paused session with clarification correctly persists in Redis

## Recommendations (Prioritized)

1. **[P0] Fix SSE 409 handling**: Frontend must distinguish paused-session 409 from errors and show clarification UI
2. **[P0] Increase SSE rate limit**: Change from 5/min to 20/min or implement per-session limits
3. **[P1] Fix dashboard 500 errors**: Handle missing user data gracefully
4. **[P1] Investigate event persistence mismatch**: Ensure Redis→PostgreSQL sync reliability
5. **[P2] Improve onboarding UX**: Don't block navigation to primary user flows

## Appendix

### Console excerpts

```txt
[ERROR] [SSE] Connection error: Error: SSE connection failed: 409
    at Jl.connect (https://boardof.one/_app/immutable/chunks/Dhp7w3sM.js:850:14156)
[ERROR] [SSE] Max retries reached
[ERROR] Failed to load resource: the server responded with a status of 429 ()
[ERROR] Data fetch failed: ApiClientError: Failed to get value metrics
```

### Network failures

| Method | URL | Status | Notes |
|--------|-----|--------|-------|
| GET | /api/v1/user/value-metrics | 500 | Missing user data handling |
| GET | /api/v1/context | 500 | Missing context handling |
| GET | /api/v1/sessions/.../stream | 409 | Session paused |
| GET | /api/v1/sessions/.../stream | 429 | Rate limit exceeded |
| GET | /api/admin/impersonate/status | 403 | Expected (non-admin user) |

### Backend logs excerpt

```txt
19:13:45 | INFO  | Started session bo1_301e07c4-a1ee-4db7-967d-2baa04f9b99b
19:14:22 | INFO  | LLM call complete | model=claude-sonnet-4-5-20250929 cost=$0.0454
19:14:31 | WARN  | ratelimit 5 per 1 minute exceeded at endpoint: /stream
19:14:47 | INFO  | Updated Redis metadata: status=paused, phase=clarification_needed
19:14:49 | ERROR | EVENT PERSISTENCE VERIFICATION FAILED
19:14:49 | INFO  | Graph execution completed successfully
```

### Session details

- Session ID: `bo1_301e07c4-a1ee-4db7-967d-2baa04f9b99b`
- Final status: `paused`
- Phase: `clarification_needed`
- Focus areas: 3
- Cost: $0.0654
- Duration: ~64 seconds until pause

### Screenshots

| Filename | Description |
|----------|-------------|
| e2e-step1-authenticated.png | E2E user authenticated via session injection |
| e2e-step2-dashboard-new-meeting-dialog.png | Dashboard with onboarding dialog |
| e2e-step3-problem-entered.png | New meeting form with problem entered |
| e2e-step4-meeting-started-sse-error.png | Meeting started, SSE errors began |
| e2e-step5-meeting-failed-sse-409.png | Meeting Failed alert, SSE 409 |
| e2e-step5-meeting-progress-sse-fail.png | Meeting progress visible despite error |
| e2e-final-state.png | Final state before browser close |

---

*Report generated by Automated E2E Explorer*
*Scenario: golden_meeting_v1*
*Environment: Production (https://boardof.one)*
