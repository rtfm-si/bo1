# Plan: Fix Feature Explorer Issues (Jan 4, 2026)

## Summary
Fix 5 issues identified in the Feature Explorer E2E test report.

## Root Cause Analysis

### ISS-004: Session Sharing 500 (Critical)
**Cause:** `sessions.py` imports `SessionLocal` from `bo1.state.database` which no longer exists. Module was refactored to use `db_session()` context manager.
**Fix:** Remove `SessionLocal` imports and rely on repository methods which already use `db_session()`.

### ISS-001: 2FA Setup 403 (Major)
**Cause:** SuperTokens TOTP/MFA requires paid license. Error: "MFA feature is not enabled. Please subscribe to a SuperTokens core license key."
**Fix:** Update UI to indicate 2FA requires premium plan instead of showing enable button.

### ISS-002: Dataset Insights 422 (Minor)
**Cause:** Expected - returns 422 validation error when profiles don't exist.
**Fix:** Already handled - frontend gracefully handles 422 with message.

### ISS-003: Managed Competitors 503 (Minor)
**Cause:** Transient service unavailability (connection pool exhaustion during load).
**Fix:** Add retry logic and explicit timeout handling.

### ISS-005: @mention No Context (Minor)
**Cause:** Mentor prompt doesn't receive meeting context when @mention resolves to None.
**Fix:** Add logging and improve error messaging when mention resolution fails.

## Implementation Steps

### Step 1: Fix ISS-004 (Critical)
Remove unused SessionLocal imports from sessions.py:
- Lines 2055-2058: export_session
- Lines 2154-2158: create_share
- Lines 2221-2225: list_shares
- Lines 2307-2311: revoke_share

The repository methods already handle database connections.

### Step 2: Fix ISS-001 (Major)
Update Security settings page to check if 2FA is available via a new endpoint that returns the license status.

### Step 3: Fix ISS-005 (Minor)
Add logging to mention_resolver when meetings aren't found and improve mentor response.

## Tests

1. Test session sharing: Create share, list shares, revoke share
2. Test 2FA status endpoint returns license info
3. Verify @mention logs when resolution fails

## Dependencies & Risks

### Dependencies
- None - all fixes are self-contained

### Risks/Edge Cases
- ISS-001 requires UI change - might affect user expectations
- ISS-004 might have other code paths using SessionLocal
