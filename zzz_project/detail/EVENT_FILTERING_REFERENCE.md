# SSE Event Filtering Reference

**Purpose**: Technical reference for developers implementing real-time streaming (Week 6-7)
**Audience**: Backend/frontend engineers
**Last Updated**: 2025-01-16 (Week 6 Planning)

---

## Core Principle

**End users NEVER see internal orchestration mechanics**—only polished outputs.

Internal events (moderator triggers, balancer activations, convergence checks, etc.) are **IP-protected secrets** that must be filtered from the end-user event stream.

---

## Event Categories

### 1. End-User Events (ALLOWED)

**Safe to stream to end users** (polished, user-facing):

```typescript
const userFacingEvents = [
  // Session lifecycle
  "session_started",
  "session_paused",
  "session_resumed",
  "session_complete",
  "session_error",

  // Progress indicators
  "stage_transition",         // "framing_problem" → "gathering_perspectives"

  // Advisor activity
  "advisor_typing",           // "Maria is thinking..."
  "advisor_complete",         // Maria's contribution ready

  // Facilitator outputs
  "facilitator_summary",      // Where advisors align/diverge

  // Insights
  "insight_emerging",         // Risk/opportunity flags
  "decomposition_ready",      // Sub-problems identified
  "synthesis_ready",          // Final report ready

  // Errors (user-facing only)
  "error",                    // High-level errors (NOT stack traces)
];
```

### 2. Internal Events (BLOCKED from end users)

**IP-protected orchestration mechanics** (NEVER expose):

```typescript
const internalEvents = [
  // Graph execution (raw node names)
  "decompose_node_start",
  "decompose_node_end",
  "select_personas_node_start",
  "select_personas_node_end",
  "facilitator_decide_node_start",
  "facilitator_decide_node_end",
  "persona_contribute_node_start",
  "persona_contribute_node_end",
  "check_convergence_node_start",
  "check_convergence_node_end",
  "vote_node_start",
  "vote_node_end",
  "synthesize_node_start",
  "synthesize_node_end",

  // Moderator/balancer (IP)
  "moderator_intervene",         // IP: When/why moderator triggered
  "moderator_intervention_complete",
  "balancer_activate",           // IP: Balancer logic
  "balancer_adjustment_complete",

  // Convergence/weighting (IP)
  "convergence_check",           // IP: Convergence algorithm
  "convergence_score_updated",   // IP: Numeric scores (0.0-1.0)
  "weighting_updated",           // IP: Persona weighting
  "novelty_check",               // IP: Novelty detection

  // State management (internal)
  "checkpoint_saved",            // Internal state management
  "checkpoint_loaded",
  "state_snapshot",

  // Safety/loop prevention (IP)
  "loop_prevention_triggered",   // IP: Safety triggers
  "recursion_limit_warning",
  "timeout_warning",
  "cost_guard_triggered",

  // Metrics (internal only)
  "cost_updated",                // Internal cost tracking (end users see final cost only)
  "phase_cost_tracked",
  "token_usage_updated",
  "cache_hit",                   // Prompt caching stats
  "cache_miss",

  // Debugging
  "debug_log",
  "performance_metric",
];
```

### 3. Admin-Only Events (DEBUG mode)

**Full system visibility for troubleshooting** (admin dashboard only):

```typescript
const adminOnlyEvents = [
  ...internalEvents,             // All internal events

  // State inspection
  "graph_state_snapshot",        // Full state at each step

  // LLM metadata
  "llm_call_start",              // Model, temperature, max_tokens
  "llm_call_complete",           // Tokens, cost, latency
  "llm_call_error",              // Full error details + stack trace

  // Reasoning chains
  "reasoning_chain",             // Chain-of-thought outputs
  "facilitator_planning",        // Facilitator's internal plan

  // Infrastructure
  "redis_checkpoint_saved",      // Redis checkpoint details
  "redis_checkpoint_loaded",
  "postgres_query_executed",     // Database query logs
];
```

---

## Backend Implementation

### Event Filtering Function

```python
# backend/api/events.py

def is_internal_event(event_type: str) -> bool:
    """
    Returns True if event should be hidden from end users.

    Used to filter SSE stream (end users only see safe events).
    Admin dashboard bypasses this filter.
    """
    internal_events = {
        # Graph execution
        "decompose_node_start",
        "decompose_node_end",
        "select_personas_node_start",
        "select_personas_node_end",
        "facilitator_decide_node_start",
        "facilitator_decide_node_end",
        "persona_contribute_node_start",
        "persona_contribute_node_end",
        "check_convergence_node_start",
        "check_convergence_node_end",
        "vote_node_start",
        "vote_node_end",
        "synthesize_node_start",
        "synthesize_node_end",

        # IP-protected mechanics
        "moderator_intervene",
        "moderator_intervention_complete",
        "balancer_activate",
        "balancer_adjustment_complete",
        "convergence_check",
        "convergence_score_updated",
        "weighting_updated",
        "novelty_check",

        # Internal state
        "checkpoint_saved",
        "checkpoint_loaded",
        "state_snapshot",

        # Safety/loop prevention
        "loop_prevention_triggered",
        "recursion_limit_warning",
        "timeout_warning",
        "cost_guard_triggered",

        # Metrics
        "cost_updated",
        "phase_cost_tracked",
        "token_usage_updated",
        "cache_hit",
        "cache_miss",

        # Debugging
        "debug_log",
        "performance_metric",
    }

    return event_type in internal_events


def is_user_facing_event(event_type: str) -> bool:
    """Returns True if event should be shown to end users."""
    return not is_internal_event(event_type)
```

### SSE Streaming with Filtering

```python
# backend/api/deliberation.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.api.events import is_user_facing_event, map_node_to_visible_stage

router = APIRouter()

@router.get("/api/v1/sessions/{session_id}/stream")
async def stream_deliberation(
    session_id: str,
    user: User = Depends(get_current_user),  # Auth required
):
    """Stream deliberation events to end user (filtered)."""

    async def event_generator():
        config = {"configurable": {"thread_id": session_id}}

        async for event in graph.astream_events(state, config):
            event_type = event.get("type")

            # Filter internal events (IP protection)
            if not is_user_facing_event(event_type):
                continue  # Skip internal events

            # Map graph nodes to user-friendly stages
            if event_type.endswith("_node_start"):
                node_name = event_type.replace("_node_start", "")
                stage_data = map_node_to_visible_stage(node_name)

                yield format_sse_event({
                    "type": "stage_transition",
                    "data": stage_data,
                })
                continue

            # Pass through user-facing events
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/api/v1/admin/sessions/{session_id}/stream-debug")
async def stream_deliberation_debug(
    session_id: str,
    user: User = Depends(get_current_admin),  # Admin-only
):
    """Stream ALL events (including internal) for debugging."""

    async def event_generator():
        config = {"configurable": {"thread_id": session_id}}

        async for event in graph.astream_events(state, config):
            # NO FILTERING - admin sees everything
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

---

## Frontend Implementation

### SSE Store (End-User)

```typescript
// frontend/src/lib/stores/sse.ts

import { writable } from 'svelte/store';

export const sseStore = writable({
  connected: false,
  currentStage: null,
  advisors: [],
  insights: [],
  facilitatorSummary: null,
  decomposition: null,
  synthesis: null,
  error: null,
});

export function connectSSE(sessionId: string) {
  const eventSource = new EventSource(`/api/v1/sessions/${sessionId}/stream`);

  eventSource.addEventListener('stage_transition', (e) => {
    const data = JSON.parse(e.data);
    sseStore.update(state => ({
      ...state,
      currentStage: data.stage,
    }));
  });

  eventSource.addEventListener('advisor_typing', (e) => {
    const data = JSON.parse(e.data);
    sseStore.update(state => ({
      ...state,
      advisors: [
        ...state.advisors,
        { ...data, status: 'typing' },
      ],
    }));
  });

  eventSource.addEventListener('advisor_complete', (e) => {
    const data = JSON.parse(e.data);
    sseStore.update(state => ({
      ...state,
      advisors: state.advisors.map(a =>
        a.persona_code === data.persona_code
          ? { ...a, status: 'complete', contribution: data }
          : a
      ),
    }));
  });

  // ... other user-facing events

  eventSource.addEventListener('error', (e) => {
    console.error('SSE connection error:', e);
    sseStore.update(state => ({ ...state, connected: false }));
  });

  sseStore.update(state => ({ ...state, connected: true }));
  return eventSource;
}
```

### Admin Debug Store

```typescript
// frontend/src/lib/stores/adminDebugSSE.ts

import { writable } from 'svelte/store';

export const adminDebugStore = writable({
  connected: false,
  events: [],           // ALL events (no filtering)
  graphState: null,
  llmCalls: [],
  checkpoints: [],
});

export function connectAdminDebugSSE(sessionId: string) {
  const eventSource = new EventSource(`/api/v1/admin/sessions/${sessionId}/stream-debug`);

  eventSource.addEventListener('message', (e) => {
    const event = JSON.parse(e.data);

    // Log ALL events (no filtering)
    adminDebugStore.update(state => ({
      ...state,
      events: [...state.events, event],
    }));

    // Handle specific admin events
    if (event.type === 'graph_state_snapshot') {
      adminDebugStore.update(state => ({ ...state, graphState: event.data }));
    }

    if (event.type === 'llm_call_complete') {
      adminDebugStore.update(state => ({
        ...state,
        llmCalls: [...state.llmCalls, event.data],
      }));
    }

    // ... other admin-specific handling
  });

  adminDebugStore.update(state => ({ ...state, connected: true }));
  return eventSource;
}
```

---

## Testing Event Filtering

### Unit Tests

```python
# tests/api/test_event_filtering.py

def test_is_internal_event():
    """Internal events are correctly identified."""
    assert is_internal_event("moderator_intervene") == True
    assert is_internal_event("balancer_activate") == True
    assert is_internal_event("convergence_check") == True
    assert is_internal_event("weighting_updated") == True

def test_is_user_facing_event():
    """User-facing events are correctly identified."""
    assert is_user_facing_event("advisor_typing") == True
    assert is_user_facing_event("stage_transition") == True
    assert is_user_facing_event("synthesis_ready") == True

def test_internal_events_never_user_facing():
    """Ensure no overlap between internal and user-facing events."""
    internal = ["moderator_intervene", "balancer_activate", "convergence_check"]
    for event_type in internal:
        assert is_user_facing_event(event_type) == False
```

### Integration Tests

```python
# tests/integration/test_sse_filtering.py

async def test_end_user_sse_stream_filters_internal_events():
    """End-user SSE stream should NOT contain internal events."""
    session_id = "test-session-123"
    events = []

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            f"/api/v1/sessions/{session_id}/stream",
            headers={"Authorization": f"Bearer {user_token}"},
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event["type"])

    # Verify: NO internal events in stream
    internal_events = ["moderator_intervene", "balancer_activate", "convergence_check"]
    for event_type in internal_events:
        assert event_type not in events

    # Verify: User-facing events ARE present
    assert "stage_transition" in events
    assert "advisor_complete" in events


async def test_admin_debug_stream_includes_all_events():
    """Admin debug stream should include ALL events (no filtering)."""
    session_id = "test-session-123"
    events = []

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            f"/api/v1/admin/sessions/{session_id}/stream-debug",
            headers={"Authorization": f"Bearer {admin_token}"},
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    events.append(event["type"])

    # Verify: Internal events ARE present (admin sees everything)
    assert "moderator_intervene" in events
    assert "convergence_check" in events
    assert "weighting_updated" in events

    # Verify: User-facing events also present
    assert "stage_transition" in events
    assert "advisor_complete" in events
```

---

## Admin Dashboard UX Audit

### Detecting IP Leaks

Add to admin dashboard home (Week 10-11):

```python
# backend/api/admin.py

@router.get("/api/v1/admin/ux-audit")
async def ux_audit(user: User = Depends(get_current_admin)):
    """Audit UX for IP leaks (internal events exposed to end users)."""

    # Query recent SSE events sent to end users (last 24h)
    recent_events = await get_recent_user_facing_events(hours=24)

    # Flag any internal events that leaked
    leaks = []
    for event in recent_events:
        if is_internal_event(event["type"]):
            leaks.append({
                "session_id": event["session_id"],
                "event_type": event["type"],
                "timestamp": event["timestamp"],
                "user_id": event["user_id"],
            })

    return {
        "total_events": len(recent_events),
        "leaks": leaks,
        "leak_count": len(leaks),
        "status": "🚨 IP LEAK DETECTED" if leaks else "✅ No leaks",
    }
```

Display in admin dashboard:

```svelte
<!-- frontend/src/routes/(admin)/admin/+page.svelte -->

{#if uxAudit.leak_count > 0}
  <div class="alert alert-danger">
    <h3>🚨 IP LEAK: Internal events exposed to end users!</h3>
    <p>{uxAudit.leak_count} internal events sent to end-user SSE stream in last 24h.</p>
    <details>
      <summary>View leaked events</summary>
      <ul>
        {#each uxAudit.leaks as leak}
          <li>
            Session: {leak.session_id}<br>
            Event: {leak.event_type}<br>
            Time: {leak.timestamp}
          </li>
        {/each}
      </ul>
    </details>
  </div>
{:else}
  <div class="alert alert-success">
    ✅ No IP leaks detected (last 24h)
  </div>
{/if}
```

---

## Success Criteria

- [ ] End-user SSE stream contains ZERO internal events
- [ ] Admin debug stream contains ALL events (100% visibility)
- [ ] UX audit detects leaks within 24 hours
- [ ] Tests prevent regressions (integration tests fail if filtering breaks)

---

**Implementation Timeline**: Week 6, Day 45-46 (SSE streaming + filtering)

**Dependencies**:
- SSE endpoint implementation
- Admin authentication/authorization
- Event typing (TypeScript definitions)

---

**END OF REFERENCE**
