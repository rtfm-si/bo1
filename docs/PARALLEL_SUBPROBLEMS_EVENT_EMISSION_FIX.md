# Fix Event Emission in Parallel Sub-Problems

## Problem Statement

**Current Behavior**: When `ENABLE_PARALLEL_SUBPROBLEMS=true`, users see no UI updates for 3-5 minutes during deliberation, making meetings appear "stuck" or failed.

**Root Cause**: The `_deliberate_subproblem()` function executes sub-problem deliberations internally without emitting real-time events (contributions, rounds, persona selections, etc.). Events are only emitted when each sub-problem completes via `subproblem_complete`.

**Impact**:
- Poor UX - users think the meeting failed
- No visibility into deliberation progress
- Can't see which experts are contributing
- No way to monitor if deliberation is progressing or truly stuck

---

## Architecture Overview

### Current Event Flow (Sequential Sub-Problems)

```
Graph Execution
  └─> EventCollector wraps graph.astream_events()
      └─> Listens to ALL node completions
          └─> Emits: persona_selected, contribution_added, round_complete, etc.
              └─> Published to Redis PubSub
                  └─> SSE streams to frontend
                      └─> UI updates in real-time ✓
```

### Current Event Flow (Parallel Sub-Problems) - BROKEN

```
Graph Execution
  └─> EventCollector wraps graph.astream_events()
      └─> Enters parallel_subproblems_node
          └─> Spawns _deliberate_subproblem() tasks
              └─> Direct LLM calls (no event emission) ✗
              └─> Internal state updates (not published) ✗
              └─> Only emits subproblem_complete at end ✗
```

**Why This Happens**:
- `_deliberate_subproblem()` is a standalone async function, not a LangGraph node
- It doesn't go through the LangGraph event system
- EventCollector can't intercept its internal operations
- Events are lost in the parallel execution

---

## Solution Design

### Approach: Event Bridge Pattern

Create an **EventBridge** that `_deliberate_subproblem()` can use to emit events directly to Redis, bypassing the EventCollector limitation.

```
_deliberate_subproblem(session_id, event_bridge)
  └─> Selects personas
      └─> event_bridge.emit("persona_selected", {...})  ✓
  └─> Runs rounds
      └─> Expert contributes
          └─> event_bridge.emit("contribution_added", {...})  ✓
      └─> Round completes
          └─> event_bridge.emit("round_complete", {...})  ✓
  └─> Collects recommendations
      └─> event_bridge.emit("voting_started", {...})  ✓
  └─> Generates synthesis
      └─> event_bridge.emit("synthesis_complete", {...})  ✓
```

### Key Principle

**Don't change the graph structure** - just add event emission hooks at critical points within `_deliberate_subproblem()`.

---

## Implementation Plan

### Phase 1: Create EventBridge

**File**: `backend/api/event_bridge.py` (NEW)

```python
"""Event bridge for emitting events from non-graph contexts.

Allows parallel sub-problem execution to emit real-time events
without requiring LangGraph node wrapping.
"""

class EventBridge:
    """Bridge for emitting events from parallel sub-problem execution."""

    def __init__(self, session_id: str, publisher: EventPublisher):
        self.session_id = session_id
        self.publisher = publisher
        self.sub_problem_index: int | None = None

    def set_sub_problem_index(self, index: int) -> None:
        """Set the current sub-problem index for event tagging."""
        self.sub_problem_index = index

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit event with automatic sub-problem tagging.

        Args:
            event_type: Event type (e.g., "contribution_added")
            data: Event payload
        """
        # Add sub_problem_index to all events
        event_data = {**data}
        if self.sub_problem_index is not None:
            event_data["sub_problem_index"] = self.sub_problem_index

        # Publish to Redis + PostgreSQL
        self.publisher.publish_event(
            self.session_id,
            event_type,
            event_data
        )
```

**Why This Works**:
- Lightweight wrapper around EventPublisher
- Automatically tags events with `sub_problem_index`
- Can be passed into `_deliberate_subproblem()` as a parameter
- No changes to graph structure needed

---

### Phase 2: Update `_deliberate_subproblem` Signature

**File**: `bo1/graph/nodes.py` (line ~2217)

**Current**:
```python
async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    sub_problem_index: int,
    user_id: str | None = None,
) -> SubProblemResult:
```

**Updated**:
```python
async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    sub_problem_index: int,
    user_id: str | None = None,
    event_bridge: EventBridge | None = None,  # NEW
) -> SubProblemResult:
```

---

### Phase 3: Add Event Emission Points

**File**: `bo1/graph/nodes.py` - Inside `_deliberate_subproblem()`

#### 3.1 Persona Selection Event

**Location**: After persona selection (~line 2296)

```python
# Track persona selection cost
track_phase_cost(metrics, "persona_selection", response)

# NEW: Emit persona selection event
if event_bridge:
    event_bridge.emit("persona_selected", {
        "personas": [
            {"code": p.code, "name": p.name, "archetype": p.archetype}
            for p in personas
        ],
        "count": len(personas)
    })

logger.info(f"_deliberate_subproblem: Selected {len(personas)} personas for {sub_problem.id}")
```

#### 3.2 Round Start Events

**Location**: Before each round execution

```python
# NEW: Emit round start event
if event_bridge:
    event_bridge.emit("round_started", {
        "round": current_round,
        "phase": phase.value,
        "expert_count": len(selected_experts)
    })
```

#### 3.3 Contribution Events

**Location**: After each expert contribution

**Challenge**: Contributions happen inside `parallel_round_node` which is a separate function. We need to either:

**Option A**: Pass event_bridge to parallel_round_node
**Option B**: Emit batch events (e.g., "round_complete" with all contributions)

**Recommended: Option B** (simpler, less invasive)

```python
# After round completes
if event_bridge:
    event_bridge.emit("round_complete", {
        "round": current_round,
        "contributions": [
            {
                "persona_name": c.persona_name,
                "persona_code": c.persona_code,
                "content_preview": c.content[:200]
            }
            for c in round_contributions
        ],
        "contribution_count": len(round_contributions)
    })
```

#### 3.4 Voting Events

**Location**: Before/after voting (~line 2360+)

```python
# Before voting
if event_bridge:
    event_bridge.emit("voting_started", {
        "expert_count": len(personas)
    })

# After voting
if event_bridge:
    event_bridge.emit("voting_complete", {
        "votes_collected": len(recommendations),
        "consensus_level": "high"  # Calculate based on agreement
    })
```

#### 3.5 Synthesis Events

**Location**: Before/after synthesis generation

```python
# Before synthesis
if event_bridge:
    event_bridge.emit("synthesis_started", {})

# After synthesis
if event_bridge:
    event_bridge.emit("synthesis_complete", {
        "synthesis": synthesis,
        "word_count": len(synthesis.split())
    })
```

---

### Phase 4: Wire EventBridge into parallel_subproblems_node

**File**: `bo1/graph/nodes.py` (line ~2650+)

**Current**:
```python
task = retry_with_backoff(
    _deliberate_subproblem,
    sub_problem=sub_problem,
    problem=problem,
    all_personas=all_personas,
    previous_results=all_results,
    sub_problem_index=sp_index,
    user_id=user_id,
    max_retries=3,
    initial_delay=2.0,
    backoff_factor=2.0,
)
```

**Updated**:
```python
# Create event bridge for this sub-problem
from backend.api.event_bridge import EventBridge
from backend.api.dependencies import get_event_publisher

event_bridge = EventBridge(
    session_id=state.get("session_id"),  # Need to add to state
    publisher=get_event_publisher()
)
event_bridge.set_sub_problem_index(sp_index)

task = retry_with_backoff(
    _deliberate_subproblem,
    sub_problem=sub_problem,
    problem=problem,
    all_personas=all_personas,
    previous_results=all_results,
    sub_problem_index=sp_index,
    user_id=user_id,
    event_bridge=event_bridge,  # NEW
    max_retries=3,
    initial_delay=2.0,
    backoff_factor=2.0,
)
```

**Challenge**: Need to pass `session_id` and `event_publisher` into parallel_subproblems_node.

**Solution**: Add to graph state or pass via config.

---

### Phase 5: Update Graph State

**File**: `bo1/graph/state.py`

Add `session_id` to graph state (if not already present):

```python
class DeliberationGraphState(TypedDict, total=False):
    # ... existing fields ...
    session_id: str  # Add if missing
```

Update graph invocation to pass session_id:

**File**: `backend/api/control.py` or wherever graph is invoked

```python
initial_state = {
    "problem": problem,
    "session_id": session_id,  # NEW
    # ... other fields
}
```

---

## Alternative: Simpler Approach (If Above is Too Complex)

### Option B: Periodic Heartbeat Events

Instead of emitting every single event, just emit periodic "progress" events:

```python
# In _deliberate_subproblem, every 30 seconds
if event_bridge:
    event_bridge.emit("deliberation_progress", {
        "current_round": current_round,
        "max_rounds": max_rounds,
        "contributions_so_far": len(all_contributions),
        "status": "in_progress"
    })
```

**Pros**:
- Much simpler to implement
- Minimal code changes
- Still provides user feedback

**Cons**:
- Less granular than full event emission
- Users don't see individual contributions

---

## Testing Strategy

### Unit Tests

**File**: `tests/graph/test_event_bridge.py` (NEW)

```python
def test_event_bridge_emits_with_sub_problem_index():
    """Test EventBridge automatically tags events with sub_problem_index."""
    publisher = Mock()
    bridge = EventBridge("session_123", publisher)
    bridge.set_sub_problem_index(2)

    bridge.emit("contribution_added", {"content": "test"})

    publisher.publish_event.assert_called_once_with(
        "session_123",
        "contribution_added",
        {"content": "test", "sub_problem_index": 2}
    )
```

### Integration Tests

1. Start a multi-subproblem deliberation with `ENABLE_PARALLEL_SUBPROBLEMS=true`
2. Monitor SSE stream
3. Verify events are emitted during execution:
   - `persona_selected` within first 10s
   - `round_complete` every 20-30s
   - `voting_started` after rounds complete
   - `synthesis_complete` at end
4. Check PostgreSQL for event persistence

### Frontend Verification

1. Open meeting page
2. Verify events display in real-time
3. Check that sub-problem tabs update correctly
4. Ensure no "stuck" appearance

---

## Migration Path

### Step 1: Implement EventBridge (No Breaking Changes)

Add EventBridge but make it optional (`event_bridge: EventBridge | None = None`). Existing code works without it.

### Step 2: Add Event Emission Points (Backward Compatible)

Wrap all emissions in `if event_bridge:` checks. Code works with or without bridge.

### Step 3: Wire Into parallel_subproblems_node

Only affects parallel execution path. Sequential execution unchanged.

### Step 4: Test & Deploy

Enable for one user, verify, then roll out.

---

## Rollback Plan

If issues arise:

1. Set `event_bridge=None` when calling `_deliberate_subproblem()`
2. Temporary: `ENABLE_PARALLEL_SUBPROBLEMS=false`
3. Events stop emitting but functionality preserved

---

## Success Criteria

✅ Users see events within 10s of meeting start
✅ Events appear during parallel execution (not just at end)
✅ Frontend shows progress indicators for all sub-problems
✅ No regression in sequential sub-problem execution
✅ Event sequence matches sequential execution order
✅ All events saved to PostgreSQL with correct `sub_problem_index`

---

## Estimated Effort

- **Phase 1 (EventBridge)**: 1-2 hours
- **Phase 2 (Signature Update)**: 30 mins
- **Phase 3 (Event Emission Points)**: 2-3 hours
- **Phase 4 (Wire Into Graph)**: 1-2 hours
- **Phase 5 (State Updates)**: 1 hour
- **Testing**: 2-3 hours

**Total**: ~8-12 hours

---

## Future Enhancements

1. **Event Batching**: Batch multiple contributions into single event to reduce Redis load
2. **Progress Estimation**: Calculate % complete based on rounds/max_rounds
3. **ETA Display**: Show estimated time remaining
4. **Granular Contribution Events**: Emit each expert's contribution individually (not batched)

---

## Notes

- Keep event payload sizes small (<5KB per event)
- Consider rate limiting (max 1 event per second per sub-problem)
- Use existing EventPublisher to maintain consistency
- Don't duplicate event persistence logic
- Preserve backward compatibility with sequential execution

---

**Document Created**: 2025-11-28
**Status**: Implementation Plan - Ready for Review
**Priority**: High (Poor UX blocking production use)
