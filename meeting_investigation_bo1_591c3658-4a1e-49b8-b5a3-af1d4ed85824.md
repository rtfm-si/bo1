# Meeting Investigation – bo1_591c3658-4a1e-49b8-b5a3-af1d4ed85824 (Updated)

## CRITICAL BUG ANALYSIS

### Root Cause: `unhashable type: 'list'` in `next_subproblem_node`

**Error Location:** `bo1/graph/nodes/synthesis.py:349`

```python
if current_sp_id in existing_result_ids:
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: unhashable type: 'list'
```

**Traceback Chain:**

1. Sub-problem 1 synthesis completed successfully
2. Router called `route_after_synthesis` → decided to go to `next_subproblem`
3. `next_subproblem_node` started executing
4. Guard check at line 343-349 tried to get `current_sub_problem.id`
5. `_get_subproblem_attr(current_sp, "id", None)` returned a **list** instead of a string
6. Trying to check `list in set` caused the unhashable type error

**Why `current_sub_problem.id` is a list:**
The session went through clarification recovery. During checkpoint restoration, `current_sub_problem` was either:

1. Not properly deserialized from the checkpoint
2. Set to a malformed dict where `id` field contains a list (possibly confusion with `dependencies`)
3. The entire `sub_problems` list was assigned to `current_sub_problem`

**Evidence:**

- Log: `"Recovered problem from PostgreSQL for bo1_591c3658-4a1e-49b8-b5a3-af1d4ed85824: 3 sub_problems"`
- But sub-problem 1 completed, meaning `current_sub_problem` was valid during deliberation
- Error only occurred in `next_subproblem_node` when preparing for sub-problem 2

### Secondary Issues

1. **ForeignKey violations** - `persona_code` not in `personas` table:

   - `finance_strategist`, `product_manager` - dynamically generated personas not in DB
   - Non-blocking (contributions still work in memory)

2. **Undefined metrics in frontend console:**
   - `exploration_score: undefined`, `focus_score: undefined`, `meeting_completeness_index: undefined`
   - Some fields in convergence event have `None` values from backend

---

## FIX PLAN (DO NOT IMPLEMENT - REVIEW ONLY)

### Fix 1: Defensive type check in `next_subproblem_node` (P0)

**File:** `bo1/graph/nodes/synthesis.py:343-349`

```python
# BEFORE (crashes if current_sp_id is a list)
current_sp_id = _get_subproblem_attr(current_sp, "id", None) if current_sp else None
if current_sp_id:
    existing_result_ids = {
        r.sub_problem_id if hasattr(r, "sub_problem_id") else r.get("sub_problem_id")
        for r in previous_results
    }
    if current_sp_id in existing_result_ids:
        ...

# AFTER (defensive: handle malformed current_sub_problem)
current_sp_id = _get_subproblem_attr(current_sp, "id", None) if current_sp else None

# Guard: Ensure current_sp_id is hashable (string expected)
if current_sp_id and not isinstance(current_sp_id, str):
    logger.error(
        f"next_subproblem_node: current_sub_problem.id is not a string! "
        f"Got type={type(current_sp_id).__name__}, value={current_sp_id}. "
        f"This indicates state corruption. Skipping guard check."
    )
    current_sp_id = None  # Skip guard check, proceed with normal flow

if current_sp_id:
    existing_result_ids = {
        r.sub_problem_id if hasattr(r, "sub_problem_id") else r.get("sub_problem_id")
        for r in previous_results
        if isinstance(r.sub_problem_id if hasattr(r, "sub_problem_id") else r.get("sub_problem_id"), str)
    }
    if current_sp_id in existing_result_ids:
        ...
```

### Fix 2: Investigate checkpoint state corruption root cause (P0)

**Files to investigate:**

- `backend/api/control.py:900-1000` - clarification resume flow
- `bo1/graph/state.py:430-466` - state deserialization

**Hypothesis:** After checkpoint restoration, `current_sub_problem` is being set incorrectly. Need to add logging to capture the actual value of `current_sub_problem` after restore.

**Debug logging to add:**

```python
# In next_subproblem_node, after getting current_sp
logger.info(
    f"next_subproblem_node: current_sub_problem type={type(current_sp).__name__}, "
    f"value={current_sp if isinstance(current_sp, dict) else repr(current_sp)[:200]}"
)
```

### Fix 3: Frontend undefined metrics (P1)

**File:** `frontend/src/lib/components/ui/DecisionMetrics.svelte`

Frontend logs show `exploration_score: undefined`. The backend sends `None` for some fields.

**Fix:** Ensure backend always sends numeric defaults (0.0) instead of `None` for metric fields:

```python
# In convergence event emission
{
    "exploration_score": metrics.exploration_score if metrics.exploration_score is not None else 0.0,
    "focus_score": metrics.focus_score if metrics.focus_score is not None else 0.0,
    "meeting_completeness_index": metrics.meeting_completeness_index if metrics.meeting_completeness_index is not None else 0.0,
}
```

### Fix 4: ForeignKey violations for dynamic personas (P2)

**Issue:** Dynamic personas (`finance_strategist`, `product_manager`) not in `personas` table.

**Options:**

1. Insert dynamic personas into `personas` table on first use
2. Make `persona_code` FK nullable for contributions
3. Use a lookup table for well-known dynamic persona codes

**Recommendation:** Option 1 - auto-insert with a "dynamic" flag.

---

## HITL MVP - Quick Design (User Request)

**Goal:** Let users inject context mid-meeting ("hang on a second...")

### Minimal Implementation:

1. **Frontend:** Add small "Raise hand" floating button in meeting view

   - Opens modal with textarea
   - Submits to new API endpoint

2. **Backend:** `POST /api/v1/sessions/{id}/context`

   - Accepts `{ "context": "user text" }`
   - Stores in `metadata["user_context_pending"]`
   - Pauses session (status=paused, phase=user_context)

3. **Graph:** New router check before each round
   - If `user_context_pending` exists, inject into problem.context
   - Clear flag and continue

**Estimated scope:** ~3-4 files, ~100 lines of code

---

# Original Investigation (Earlier Session)

## 1. Summary

- **Status**: `paused` (DB) - awaiting clarification response
- **UI shows**: "Meeting Complete" (INCORRECT)
- **Phase**: `identify_gaps` (Postgres) vs `clarification_needed` (Redis - expired)

**Critical Issues:**

- P0: Paused-for-clarification session displays as "Meeting Complete" - user cannot continue
- P0: Clarification questions never shown to user despite being stored in events
- P1: Phase mismatch between Postgres (`identify_gaps`) and Redis (`clarification_needed`)
- P1: After Redis TTL expires, session state is unrecoverable for clarification flow

**What worked:**

- Problem decomposition completed successfully (3 sub-problems)
- 5 events properly persisted to Postgres
- Clarification questions were generated and stored

## 2. Timeline Reconstruction

| Time (UTC) | Backend Event                                    | UI Visible         | Notes                                          |
| ---------- | ------------------------------------------------ | ------------------ | ---------------------------------------------- |
| 21:38:53   | Session created                                  | -                  |                                                |
| 21:38:55   | Graph execution started                          | -                  |                                                |
| 21:38:55   | `context_collection_complete`                    | No                 | Event stored but no UI entry                   |
| 21:39:51   | `working_status` (decomposing)                   | Partial            | "Breaking down..."                             |
| 21:39:51   | `discussion_quality_status`                      | Yes                | "Analyzing problem structure..." (still shows) |
| 21:39:51   | `decomposition_complete`                         | Yes                | 3 focus areas shown in tabs                    |
| 21:40:08   | `clarification_required`                         | **NO**             | 2 critical questions - NEVER SHOWN             |
| 21:40:08   | Redis: status=paused, phase=clarification_needed | -                  |                                                |
| 21:40:08   | Postgres: status=paused, phase=identify_gaps     | -                  | **MISMATCH**                                   |
| 21:40:08   | Graph execution completed                        | -                  | Scheduled cleanup in 60 min                    |
| ~22:40:08  | Redis TTL expires                                | -                  | Phase info lost                                |
| Now        | Page load                                        | "Meeting Complete" | Wrong - should show clarification form         |

## 3. UI & UX Issues

### P0: Clarification Form Not Shown

**Root cause:** Frontend condition at `eventDerivedState.svelte.ts:93-94`:

```typescript
const isPausedForClarification =
  session?.status === "paused" && session?.phase === "clarification_needed";
```

But session API returns `phase: 'identify_gaps'` from Postgres (Redis expired).

**Backend bug:** `event_collector.py:519-520` sets `phase='clarification_needed'` only in Redis, not Postgres. Postgres gets the graph execution phase (`identify_gaps`).

### P0: Header Shows "Meeting Complete" for Paused Sessions

**Root cause:** `MeetingHeader.svelte:23-25`:

```typescript
const isComplete = $derived(sessionStatus === "completed");
const isTerminated = $derived(sessionStatus === "terminated");
const isActive = $derived(
  sessionStatus === "active" || sessionStatus === "paused"
);
```

Header title logic (line 90-94):

```svelte
{#if isComplete}
    Meeting Complete
{:else if isTerminated}
    Meeting Ended Early
{:else}
    Meeting in Progress
```

When `status === 'paused'`, `isComplete` is false, `isTerminated` is false, so it should show "Meeting in Progress". But the console log shows `Session is completed` - investigating...

Actually the issue is in the **tab panel** - the Summary tab shows "Decision Breakdown Complete" and "No synthesis available" which misleads the user into thinking the meeting is done.

### P1: Misleading Metrics Panel

Current display:

- Focus Areas: 3 ✓
- Discussion Rounds: 0
- Risks Identified: 0
- Research Triggered: 0
- Expert Contributions: 0

All zeros are confusing - the meeting paused before any deliberation occurred, but this isn't communicated.

### P1: "No synthesis available" Message

Shows in Summary tab, but no indication that synthesis hasn't started because clarification is needed.

### Missing UI Elements

1. **Clarification questions** - Should show:
   - "What is the current cost structure per decision/query?" (CRITICAL)
   - "What specific features and capabilities does your product currently have?" (CRITICAL)
2. **"Waiting for your input" banner** - No indication that user action is required
3. **Resume/Continue button** - No way to respond and continue the meeting

## 4. Performance & Gaps

| Phase                         | Duration | Notes                 |
| ----------------------------- | -------- | --------------------- |
| Start → Decomposition         | 56s      | Normal                |
| Decomposition → Clarification | 17s      | Normal                |
| Clarification → User Action   | ∞        | **User not informed** |

No performance issues detected in backend execution.

## 5. Console & Log Errors

### Browser Console

- `[DecisionMetrics] No convergence events yet, count: 0` - Expected, no rounds occurred
- `[Events] Session is completed, skipping SSE connection` - **BUG**: Logs `completed` but status is `paused`

Wait - the log says "Session is `completed`" but DB shows `paused`. Let me re-check...

Actually looking at line 522: `console.log(\`[Events] Session is ${session.status}, skipping SSE connection\`);`

The console output shows "Session is completed" which means the session object has `status: 'completed'` somehow. This could be:

1. A caching issue
2. The session endpoint returning wrong status
3. A frontend mutation of status

### Backend Logs

- No errors for this session
- Clean execution flow
- Proper event persistence (5 events)

### Network

- All API calls returned 200
- No failed requests

## 6. Recommendations

### P0 - Immediate Fixes

1. **Persist clarification phase to Postgres**

   - `backend/api/event_collector.py`: When setting `phase='clarification_needed'` in Redis, also update Postgres sessions table
   - Add migration if `phase` column doesn't exist or doesn't support this value

2. **Add fallback clarification detection**

   - `frontend/src/routes/(app)/meeting/[id]/lib/eventDerivedState.svelte.ts`:

   ```typescript
   const needsClarification = $derived.by(() => {
     // Primary: phase-based detection
     if (
       session?.status === "paused" &&
       session?.phase === "clarification_needed"
     ) {
       return (
         clarificationRequiredEvent !== undefined &&
         clarificationQuestions !== undefined
       );
     }
     // Fallback: event-based detection when phase not available
     if (
       session?.status === "paused" &&
       clarificationRequiredEvent !== undefined
     ) {
       return clarificationQuestions !== undefined;
     }
     return false;
   });
   ```

3. **Fix header for paused status**
   - Show "Waiting for Input" or "Action Required" when `status === 'paused'`

### P1 - UX Improvements

4. **Add clarification pending banner**

   - When `needsClarification` is true, show prominent banner: "This meeting needs your input to continue"

5. **Improve Summary tab for incomplete meetings**

   - Don't show "Decision Breakdown Complete" if clarification is pending
   - Show "Clarification Required" with the questions inline

6. **Fix misleading console log**
   - Line 522 logs "completed" but should log actual status

### P2 - Future Improvements

7. **Extend Redis TTL for paused sessions**

   - Currently 60 min; consider 24h+ for paused sessions awaiting user input

8. **Add session recovery mechanism**
   - When loading paused session with missing Redis data, check events for `clarification_required` to reconstruct state
