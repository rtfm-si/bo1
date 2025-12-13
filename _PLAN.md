# Plan: [ADMIN][P3] Implement Admin Impersonation ("View as User")

## Summary

- Add admin impersonation capability to view app as any user
- Secure implementation with audit logging and visual indicator
- Time-limited sessions with automatic expiry
- Non-destructive: read-only by default, optional write mode

## Implementation Steps

1. **Create impersonation schema migration**
   - `migrations/versions/ah1_add_admin_impersonation.py`
   - Table `admin_impersonation_sessions`: id, admin_user_id, target_user_id, started_at, expires_at, is_write_mode, reason
   - Index on admin_user_id + expires_at for cleanup

2. **Add impersonation service**
   - `backend/services/admin_impersonation.py`
   - `start_impersonation(admin_id, target_user_id, reason, write_mode=False, duration_minutes=30)`
   - `end_impersonation(admin_id)`
   - `get_active_impersonation(admin_id)` → returns target_user_id if active
   - `is_impersonating(admin_id)` → bool
   - Store session token in Redis with TTL

3. **Create impersonation API endpoints**
   - `POST /api/admin/impersonate/{user_id}` - start impersonation (body: reason, write_mode, duration)
   - `DELETE /api/admin/impersonate` - end impersonation
   - `GET /api/admin/impersonate/status` - check if currently impersonating
   - Require admin role on all endpoints

4. **Add impersonation middleware**
   - `backend/api/middleware/impersonation.py`
   - Check Redis for active impersonation session
   - Swap request.state.user_id to target when impersonating
   - Set request.state.is_impersonation = True
   - Set request.state.impersonation_write_mode for write checks
   - Block mutations if write_mode=False

5. **Modify auth dependency to respect impersonation**
   - Update `get_current_user()` to check impersonation state
   - Return target user's context when impersonating
   - Preserve admin identity in separate field for audit

6. **Add audit logging**
   - Log impersonation start/end to api_audit_log
   - Log all actions taken while impersonating with flag
   - Include admin_user_id in audit entries during impersonation

7. **Add frontend impersonation banner**
   - `frontend/src/lib/components/admin/ImpersonationBanner.svelte`
   - Fixed banner at top when impersonating: "Viewing as [user email] - [End Session]"
   - Different color for write mode (warning amber vs info blue)
   - Show remaining time

8. **Add admin user list impersonate button**
   - Add "View as User" button to admin users page
   - Modal to enter reason and select read-only vs write mode
   - Duration selector (15m, 30m, 1h)

## Tests

- Unit tests:
  - `tests/services/test_admin_impersonation.py` - start, end, get_active, expiry
  - `tests/api/test_admin_impersonate.py` - endpoint access control, CRUD

- Integration tests:
  - Start impersonation, verify subsequent requests see target user data
  - End impersonation, verify requests revert to admin view
  - Read-only mode blocks mutations (POST/PUT/PATCH/DELETE return 403)
  - Write mode allows mutations with audit trail
  - Expired session auto-reverts to admin view
  - Non-admin cannot access impersonation endpoints

- Manual validation:
  - Admin starts impersonation, sees target user's meetings/datasets
  - Banner visible with "End Session" button
  - Ending session returns to admin view
  - All impersonated actions appear in audit log

## Dependencies & Risks

- Dependencies:
  - Admin auth middleware (existing)
  - Redis for session tokens
  - api_audit_log table (existing)

- Risks:
  - Security: must validate admin role before impersonation
  - Audit gap: ensure ALL requests during impersonation are logged
  - Session confusion: clear impersonation on admin logout
  - SSE streams: may need special handling for long-running connections
