# Plan: Fix E2E Run Report Issues (ISS-001 through ISS-005)

_Updated: 2024-12-24 based on E2E run report analysis_

## Summary

- Fix session status handling so clarification-paused sessions aren't marked completed (ISS-002 - root cause)
- Fix SSE 409 for paused/clarification sessions by checking PostgreSQL as fallback (ISS-001)
- Run pending migration for strategic_objectives column (ISS-003)
- Suppress admin impersonate status call for non-admin users (ISS-005)
- ISS-004 is a consequence of ISS-002; fixing ISS-002 resolves it

## Root Cause Analysis

| Issue | Severity | Root Cause | File |
|-------|----------|------------|------|
| ISS-001 | Critical | SSE reads status from Redis which may be stale; PostgreSQL has correct paused/clarification_needed status | `streaming.py:1113-1121` |
| ISS-002 | Critical | `execution.py` marks session "completed" after graph returns, overwriting paused status set by `_handle_identify_gaps` | `execution.py:255` |
| ISS-003 | Major | Migration `z23_add_strategic_objectives` not deployed to production | Deploy action |
| ISS-004 | Major | Direct consequence of ISS-002 - no deliberation because sessions complete at identify_gaps | N/A |
| ISS-005 | Minor | Frontend calls admin endpoint for ALL users, causing 403 for non-admins | `+layout.svelte:38-48` |

---

## Implementation Steps

### Step 1: Fix ISS-002 - Graph completion overwrites clarification pause

**File**: `bo1/graph/execution.py` (lines 235-256)

**Problem**: The `wrapped_execution()` function marks sessions as "completed" without checking if the session was paused for clarification. The existing check for `pending_clarification` at line 241 only prevents marking as "failed" when there's no synthesis, but doesn't prevent the `completed` status update.

**Fix**: Add early return before `_update_session_status("completed")`:

```python
# Around line 239, BEFORE checking synthesis
state = result if isinstance(result, dict) else {}
pending_clarification = bool(state.get("pending_clarification"))
stop_reason = state.get("stop_reason")

# Don't mark as completed if paused for clarification
if pending_clarification or stop_reason == "clarification_needed":
    logger.info(
        f"[{session_id}] Graph paused for clarification - "
        f"keeping paused status (stop_reason={stop_reason})"
    )
    return result  # Early return - status already set by _handle_identify_gaps

# Existing synthesis validation...
has_synthesis = bool(state.get("synthesis"))
# ...
```

### Step 2: Fix ISS-001 - SSE 409 for paused sessions

**File**: `backend/api/streaming.py` (lines 1113-1127)

**Problem**: SSE endpoint reads status from Redis metadata, but `_handle_identify_gaps()` updates PostgreSQL. When Redis has stale data, the phase check fails.

**Fix**: When status=paused but phase is not clarification_needed, check PostgreSQL as fallback:

```python
if status == "paused":
    phase = metadata.get("phase") if metadata else None

    # Check PostgreSQL as source of truth if phase doesn't indicate clarification
    if phase != "clarification_needed":
        from bo1.state.repositories import session_repository
        db_session = session_repository.get(session_id)
        if db_session and db_session.get("phase") == "clarification_needed":
            phase = "clarification_needed"
            logger.info(
                f"SSE: Using PostgreSQL phase '{phase}' for {session_id} "
                f"(Redis phase was '{metadata.get('phase')}')"
            )

    if phase != "clarification_needed":
        raise HTTPException(
            status_code=409,
            detail=f"Session {session_id} is paused. Call /resume endpoint to continue.",
        )
    # Continue to streaming for clarification sessions
    logger.info(f"SSE connection allowed for paused session {session_id} (phase={phase})")
```

### Step 3: Add cache invalidation in _handle_identify_gaps

**File**: `backend/api/event_collector.py` (around line 791)

**Problem**: Session metadata cache may hold stale data after status update.

**Fix**: Invalidate cache after updating status:

```python
# After redis_manager.save_metadata(session_id, metadata) around line 791
from backend.api.dependencies import get_session_metadata_cache
get_session_metadata_cache().invalidate(session_id)
```

### Step 4: Fix ISS-005 - Admin impersonate status 403 noise

**File**: `frontend/src/routes/(app)/+layout.svelte` (lines 38-48)

**Problem**: `checkImpersonation()` calls admin endpoint for ALL users.

**Fix**: Only call for admin users:

```svelte
async function checkImpersonation() {
    // Only admins can impersonate - skip for non-admins to avoid 403
    if (!$user?.is_admin) {
        return;
    }
    try {
        const status = await adminApi.getImpersonationStatus();
        if (status.is_impersonating && status.session) {
            impersonationSession = status.session;
            log.log('Active impersonation session detected:', status.session.target_email);
        }
    } catch {
        // Not an admin or no active session - ignore silently
    }
}
```

### Step 5: Deploy migration for ISS-003

**Action**: Run pending Alembic migration on production.

```bash
# On production server
alembic upgrade head
```

Migration file: `migrations/versions/z23_add_strategic_objectives.py`
- Adds `strategic_objectives` JSONB column to `user_context` table

---

## Tests

### Unit tests:
- `tests/graph/test_execution.py`:
  - `test_graph_execution_preserves_paused_status_for_clarification`
  - `test_graph_execution_does_not_mark_completed_when_pending_clarification`
  - `test_graph_execution_early_returns_on_stop_reason_clarification_needed`

- `tests/api/test_streaming.py`:
  - `test_sse_allows_paused_session_with_clarification_phase_from_postgres`
  - `test_sse_checks_postgres_when_redis_phase_stale`
  - `test_sse_rejects_paused_session_without_clarification_phase`

### Integration tests:
- `tests/api/test_clarification_flow.py`:
  - `test_full_clarification_flow_session_stays_paused`
  - `test_sse_connects_for_clarification_session`
  - `test_clarification_answers_resume_meeting`

### Manual validation:
1. Start a meeting with complex problem that triggers clarification questions
2. Verify PostgreSQL shows `status=paused, phase=clarification_needed`
3. Verify SSE connects successfully (no 409 errors in network tab)
4. Verify clarification questions appear in UI
5. Answer questions and verify meeting continues to persona selection
6. Check `/api/v1/context` returns 200 (not 500)
7. Check console has no 403 for `/api/admin/impersonate/status` (non-admin user)

---

## Dependencies & Risks

### Dependencies:
- Step 1 (ISS-002) must be deployed before testing ISS-001 fix
- Step 5 (migration) requires production database access

### Risks/edge cases:
- **Race condition**: Graph execution and `_handle_identify_gaps` may run concurrently
  - Mitigation: ISS-002 fix uses `stop_reason` from state which is set before graph returns
- **Cache staleness**: Session metadata cache has 5min TTL
  - Mitigation: Step 3 adds explicit cache invalidation
- **PostgreSQL fallback latency**: Extra DB query in SSE check
  - Mitigation: Only triggered when Redis phase doesn't match; one-time check per connection

### Rollback:
- All changes are additive and can be reverted independently
- No schema changes (migration already exists, just needs deployment)

---

## Verification Commands

```bash
# Run unit tests
pytest tests/graph/test_execution.py -v -k clarification
pytest tests/api/test_streaming.py -v -k paused

# Check session status after meeting pause
psql -c "SELECT id, status, phase FROM sessions ORDER BY created_at DESC LIMIT 5"

# Verify migration applied
alembic current
alembic history --verbose

# Check for 403 errors in frontend console (should be none for non-admin)
# Browser DevTools > Network > filter "impersonate"
```

---

## Success Criteria

After implementation, re-run E2E `golden_meeting_v1` scenario:
- [ ] SSE connects without 409 errors
- [ ] Clarification questions appear in UI
- [ ] Session status stays "paused" during clarification
- [ ] Meeting continues after answering questions
- [ ] Full deliberation cycle completes (personas, rounds, synthesis)
- [ ] Context API returns 200
- [ ] No 403 errors in console for non-admin users

---

# Plan: Fix Event Masking and Timeout Scaling

_Added: 2025-12-25 based on meeting investigation `bo1_35448e5b-0023-4cbc-a0a7-5cbae8ba4ddb`_

## Problem Analysis

**Meeting**: `bo1_35448e5b-0023-4cbc-a0a7-5cbae8ba4ddb`

### Issue 1: Internal Events Leaking to Users
- `state_transition` (33 events) shown to users - should be masked
- `parallel_round_start` (6 events) - also internal, consider masking

### Issue 2: Timeout Too Short for Multi-Sub-Problem Meetings
- 3 sub-problems defined
- sp_001: completed in ~4.5 min (synthesis at 15:39:21)
- sp_002: started at 15:40:09, timeout at 15:43:30 (3.5 min, incomplete)
- sp_003: never started
- **Math**: 3 × 4.5 min = 13.5 min needed, but timeout = 10 min (600s)

---

## Fix 1: Mask Internal Events (Frontend)

**File**: `frontend/src/routes/(app)/meeting/[id]/lib/eventGrouping.ts`

Add to `STATUS_NOISE_EVENTS` (line 24-40):
```typescript
export const STATUS_NOISE_EVENTS = [
  'state_transition',       // ADD: internal graph node transitions
  'parallel_round_start',   // ADD: internal round orchestration
  // ... existing entries
];
```

**Impact**: Immediate, no backend changes needed.

---

## Fix 2: Liveness-Based Timeout Architecture

**Current**: 600s (10 min) wall-clock timeout - kills meetings regardless of progress

**Proposed**: Three-tier timeout with liveness tracking

| Timeout | Value | Purpose |
|---------|-------|---------|
| **Hard ceiling** | 1800s (30 min) | Absolute safety stop, never exceeded |
| **Liveness timeout** | 600s (10 min) | Kill if no meaningful events |
| **Round timeout** | 600s (10 min) | Kill stuck individual round |

### Implementation

**File**: `backend/api/constants.py`
```python
# Timeout architecture
GRAPH_HARD_TIMEOUT_SECONDS = int(os.environ.get("GRAPH_HARD_TIMEOUT_SECONDS", "1800"))  # 30 min
GRAPH_LIVENESS_TIMEOUT_SECONDS = int(os.environ.get("GRAPH_LIVENESS_TIMEOUT_SECONDS", "600"))  # 10 min
```

**File**: `backend/api/event_collector.py`
```python
# Track last meaningful event time
MEANINGFUL_EVENTS = {
    "contribution",
    "persona_selected",
    "synthesis_complete",
    "voting_complete",
    "subproblem_started",
    "decomposition_complete",
}

# In _handle_xxx methods, update last_meaningful_event_time when event_type in MEANINGFUL_EVENTS
# In timeout check, compare: now - last_meaningful_event_time > LIVENESS_TIMEOUT
```

**Behavior**:
1. Meeting starts, clock begins
2. Each meaningful event resets liveness timer
3. If no meaningful event for 10 min → kill (stuck)
4. If meaningful events flowing → continue up to 30 min hard ceiling
5. At 30 min → hard stop regardless of progress

**Benefits**:
- 3 sub-problem meetings (like this one) can complete if progressing
- Stuck meetings still get killed after 10 min of silence
- Hard ceiling prevents runaway cost

---

## Fix 3: Partial Completion Handling (Future)

If `synthesis_complete` exists for ANY sub-problem:
1. Show partial results instead of "Meeting Failed"
2. Status: "Partial" (1 of 3 topics completed)
3. User can view completed synthesis
4. Offer "Resume" for remaining topics

---

## Execution Order

1. **Immediate** (5 min): Add `state_transition`, `parallel_round_start` to noise filter
2. **Short-term** (1-2 hrs): Implement liveness-based timeout architecture
3. **UX** (later): Partial completion handling

---

## Acceptance Criteria

- [ ] `state_transition` events not visible in meeting UI
- [ ] `parallel_round_start` events not visible in meeting UI
- [ ] Meetings with steady progress can run up to 30 min
- [ ] Stuck meetings (no meaningful events for 10 min) get killed
- [ ] 3 sub-problem meetings complete successfully
- [ ] Partial synthesis visible even if meeting times out (future)
