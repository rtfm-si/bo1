# Clarification Resume Fix Plan

## Executive Summary

Two issues were identified in the meeting system:

1. **CRITICAL: Clarification Pause Doesn't Work** - When resuming after user answers clarification questions, the graph restarts from the entry point and re-runs decomposition, generating potentially DIFFERENT sub-problems that don't match the user's answers.

2. **LOW PRIORITY: Summary Timing** - Sub-problem syntheses appear while other sub-problems are still running. This is actually CORRECT behavior for parallel execution, not a bug.

---

## Issue 1: Clarification Resume Bug

### Root Cause

**Location:** `backend/api/control.py:638-669`

When resuming with clarification answers, the code does:

```python
resume_state = dict(checkpoint_state.values)
resume_state["clarification_answers"] = clarification_answers
coro = event_collector.collect_and_publish(session_id, graph, resume_state, config)
```

The bug: Passing `resume_state` as `initial_state` to `graph.astream()` **RESTARTS the graph from entry point** (`context_collection`), instead of resuming from where it paused.

### Broken Flow

```
1. Graph: context_collection → decompose → identify_gaps → END (paused)
2. User submits answers via POST /clarifications
3. Resume: collect_and_publish(session_id, graph, resume_state, config)
4. BUG: Graph RESTARTS from context_collection
5. decompose runs AGAIN → generates DIFFERENT sub-problems
6. Original clarification answers no longer match!
```

### Correct Flow (After Fix)

```
1. Graph: context_collection → decompose → identify_gaps → END (paused)
2. User submits answers via POST /clarifications
3. Resume: aupdate_state(config, {answers, should_stop=False}, as_node="identify_gaps")
4. Resume: astream(None, config) → resumes from AFTER identify_gaps
5. Router sees answers, routes to analyze_dependencies
6. Same sub-problems, answers match!
```

---

## Implementation Plan

### Step 1: Update State Schema

**File:** `bo1/graph/state.py` (around line 76)

Add `clarification_answers` field to TypedDict:

```python
class DeliberationGraphState(TypedDict, total=False):
    # ... existing fields ...

    # Human-in-the-loop clarification
    pending_clarification: dict[str, Any] | None
    clarification_answers: dict[str, str] | None  # ADD THIS
```

**Risk:** Low - Adding field is backwards compatible

---

### Step 2: Fix Resume Logic (CRITICAL)

**File:** `backend/api/control.py:638-669`

Replace current implementation:

```python
# BEFORE (broken)
clarification_answers = metadata.get("clarification_answers_pending")
if clarification_answers:
    checkpoint_state = await graph.aget_state(config)
    if checkpoint_state and checkpoint_state.values:
        resume_state = dict(checkpoint_state.values)
        resume_state["clarification_answers"] = clarification_answers
        # ... metrics fix ...
        coro = event_collector.collect_and_publish(session_id, graph, resume_state, config)

# AFTER (fixed)
clarification_answers = metadata.get("clarification_answers_pending")
if clarification_answers:
    # Update checkpoint state IN PLACE (doesn't restart graph)
    state_update = {
        "clarification_answers": clarification_answers,
        "should_stop": False,      # Reset stop flag so router continues
        "stop_reason": None,       # Clear stop reason
    }

    # Use aupdate_state with as_node to specify resume point
    # This tells LangGraph: "Resume from the edge AFTER identify_gaps"
    await graph.aupdate_state(config, state_update, as_node="identify_gaps")

    # Clear pending flag from metadata
    metadata.pop("clarification_answers_pending", None)
    redis_manager.save_metadata(session_id, metadata)

    logger.info(
        f"Resuming session {session_id} with {len(clarification_answers)} "
        f"clarification answer(s) - checkpoint updated at identify_gaps"
    )

    # Resume from checkpoint (None = use checkpoint, don't restart)
    coro = event_collector.collect_and_publish(session_id, graph, None, config)
```

**Risk:** Medium - Core resume mechanism change, needs thorough testing

---

### Step 3: Enhance Router Logging

**File:** `bo1/graph/config.py:158-164`

Add detailed logging:

```python
def route_after_identify_gaps(state: DeliberationGraphState) -> str:
    """Route based on whether critical information gaps require user input."""
    clarification_answers = state.get("clarification_answers")
    should_stop = state.get("should_stop")
    stop_reason = state.get("stop_reason")
    pending = state.get("pending_clarification")

    logger.info(
        f"route_after_identify_gaps: should_stop={should_stop}, "
        f"stop_reason={stop_reason}, has_answers={clarification_answers is not None}, "
        f"has_pending={pending is not None}"
    )

    if should_stop and stop_reason == "clarification_needed":
        logger.info("route_after_identify_gaps: Pausing for clarification")
        return "END"

    if clarification_answers:
        logger.info(
            f"route_after_identify_gaps: Resuming with {len(clarification_answers)} answers"
        )

    logger.info("route_after_identify_gaps: Continuing to deliberation")
    return "continue"
```

**Risk:** Low - Logging only

---

### Step 4: Inject Answers into Problem Context

**File:** `bo1/graph/nodes/context.py:181-185`

Enhance answer processing:

```python
# BEFORE
return {
    "current_node": "identify_gaps",
    "pending_clarification": None,
}

# AFTER
# Inject answers into problem context for use by downstream nodes
problem = state.get("problem")
if problem and clarification_answers:
    # Format answers as context addition
    answer_context = "\n\n## User Clarifications\n"
    for question, answer in clarification_answers.items():
        answer_context += f"- Q: {question}\n  A: {answer}\n"

    # Append to problem context (mutate the Problem object)
    problem.context = (problem.context or "") + answer_context
    logger.info(f"Injected {len(clarification_answers)} clarification answers into problem context")

return {
    "current_node": "identify_gaps",
    "pending_clarification": None,
    "problem": problem,              # Updated with clarification context
    "clarification_answers": None,   # Clear after processing
}
```

**Risk:** Low - Enhancement to existing logic

---

### Step 5: Handle Checkpoint Expiry Edge Case

**File:** `backend/api/control.py` (after aupdate_state call)

Add fallback for expired checkpoints:

```python
try:
    await graph.aupdate_state(config, state_update, as_node="identify_gaps")
except Exception as e:
    logger.warning(f"Failed to update checkpoint for {session_id}: {e}")

    # Attempt PostgreSQL reconstruction
    reconstructed = _reconstruct_state_from_postgres(session_id)
    if reconstructed:
        # Add clarification answers to reconstructed state
        reconstructed["clarification_answers"] = clarification_answers
        reconstructed["should_stop"] = False
        reconstructed["stop_reason"] = None

        logger.info(f"Reconstructed state from PostgreSQL for {session_id}")

        # Start with reconstructed state (will re-run decomposition)
        # This is the fallback - not ideal but better than failing
        coro = event_collector.collect_and_publish(session_id, graph, reconstructed, config)
    else:
        raise HTTPException(
            status_code=410,
            detail="Session checkpoint expired and cannot be reconstructed. Please start a new meeting."
        )
```

**Risk:** Medium - Fallback path needs testing

---

## Issue 2: Summary Timing (Non-Issue)

### Analysis

With `ENABLE_PARALLEL_SUBPROBLEMS=true` (enabled in .env):

1. Sub-problems execute in parallel within batches
2. Each sub-problem generates synthesis when it completes
3. `subproblem_complete` events emit as each finishes
4. Faster sub-problems complete before slower ones

**This is CORRECT behavior**, not a bug.

### Event Ordering Verification

The code ensures correct ordering:

1. `subproblem_complete` - emitted per sub-problem (lines 269-282 in subproblems.py)
2. `all_subproblems_complete` - emitted AFTER all complete (lines 448-456)
3. `meta_synthesis_complete` - emitted from separate node AFTER parallel_subproblems returns

### No Changes Needed

The `meta_synthesis` node only runs after `parallel_subproblems_node` returns, which only happens after ALL sub-problems complete.

---

## Testing Strategy

### Unit Tests

```python
# tests/graph/test_clarification_resume.py

async def test_aupdate_state_resumes_from_correct_node():
    """Verify that aupdate_state with as_node resumes from correct position."""
    # Create graph, run to identify_gaps, pause
    # Call aupdate_state with as_node="identify_gaps"
    # Resume with astream(None, config)
    # Verify decompose does NOT re-run (check logs or side effects)

async def test_clarification_answers_injected_into_context():
    """Verify answers are added to problem context."""
    state = create_test_state_with_pending_clarification()
    state["clarification_answers"] = {"Q1": "A1", "Q2": "A2"}

    result = await identify_gaps_node(state)

    assert "## User Clarifications" in result["problem"].context
    assert "Q1" in result["problem"].context
    assert "A1" in result["problem"].context

async def test_partial_answers_repause():
    """Verify partial answers re-pause with remaining questions."""
    state = create_test_state_with_3_questions()
    state["clarification_answers"] = {"Q1": "A1", "Q2": "A2"}  # Missing Q3

    result = await identify_gaps_node(state)

    assert result["should_stop"] is True
    assert len(result["pending_clarification"]["questions"]) == 1
```

### Integration Test

```python
async def test_full_clarification_flow():
    """Full E2E test of clarification pause and resume."""
    # Start session with problem that triggers clarification
    session_id = await create_session("Problem requiring clarification")

    # Wait for clarification_required event
    events = await poll_events(session_id, timeout=30)
    assert any(e["type"] == "clarification_required" for e in events)

    # Get sub-problem IDs from decomposition event
    decomp_event = next(e for e in events if e["type"] == "decomposition_complete")
    original_sp_ids = [sp["id"] for sp in decomp_event["data"]["sub_problems"]]

    # Submit answers
    await submit_clarification(session_id, {"Q1": "A1"})

    # Resume
    await resume_session(session_id)

    # Verify same sub-problems (no re-decomposition)
    state = await get_session_state(session_id)
    current_sp_ids = [sp["id"] for sp in state["problem"]["sub_problems"]]
    assert current_sp_ids == original_sp_ids

    # Verify answers in context
    assert "## User Clarifications" in state["problem"]["context"]
```

### Manual Testing Checklist

1. [ ] Create meeting with problem that triggers clarification
2. [ ] Verify `clarification_required` event received
3. [ ] Submit answers via UI
4. [ ] Click resume
5. [ ] Verify in logs: "Resuming session with X clarification answer(s)"
6. [ ] Verify in logs: NO "decompose_node: Starting" after resume
7. [ ] Verify deliberation proceeds with same sub-problems
8. [ ] Check synthesis includes user's clarification context

---

## Implementation Sequence

| Step | File | Change | Est. Time | Risk |
|------|------|--------|-----------|------|
| 1 | `bo1/graph/state.py` | Add field | 5 min | Low |
| 2 | `backend/api/control.py` | Fix resume with aupdate_state | 30 min | Medium |
| 3 | `bo1/graph/config.py` | Enhanced logging | 10 min | Low |
| 4 | `bo1/graph/nodes/context.py` | Inject answers to context | 15 min | Low |
| 5 | `backend/api/control.py` | Checkpoint expiry handling | 20 min | Medium |
| 6 | Tests | Unit + integration tests | 60 min | Low |

**Total Estimated Time:** 2-3 hours

---

## Rollback Plan

If issues arise after deployment:

1. **Quick Revert:** Restore original `control.py` resume logic (pass resume_state as initial_state)
2. **Feature Flag:** Add `USE_CHECKPOINT_RESUME=true/false` to toggle between old/new behavior
3. **Data Check:** Verify no sessions stuck in bad state (status=paused with corrupted checkpoint)

---

## Files to Modify

```
backend/api/control.py         # Lines 638-669: Resume logic (CRITICAL)
bo1/graph/state.py             # Line ~76: Add clarification_answers field
bo1/graph/config.py            # Lines 158-164: Router logging
bo1/graph/nodes/context.py     # Lines 181-185: Answer injection
tests/graph/test_clarification_resume.py  # New test file
```

---

## Verification After Fix

Run this to verify the fix works:

```bash
# Start services
make up

# Watch logs for key messages
docker logs -f boardofone-api-1 2>&1 | grep -E "(identify_gaps|route_after_identify_gaps|Resuming session|decompose_node)"

# In another terminal, create a test meeting and trigger clarification flow
# Then check logs for:
# 1. "Resuming session X with Y clarification answer(s)"
# 2. "route_after_identify_gaps: Resuming with Y answers"
# 3. NO "decompose_node: Starting" after resume
```
