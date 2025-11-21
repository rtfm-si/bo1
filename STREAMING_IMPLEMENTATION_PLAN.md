# Streaming Implementation Plan: End-to-End Real-Time Events

**Objective**: Replicate the console interface's real-time experience in the web UI via SSE (Server-Sent Events)

---

## Part 1: Event Analysis - Console Interface Events

Based on analysis of `bo1/interfaces/console.py`, here are ALL events displayed to users:

### 1.1 Setup Phase Events

#### **Session Start/Resume**
- **When**: Initial session creation or resume from checkpoint
- **Display**: Session ID, welcome header, problem statement
- **Source**: `run_console_deliberation()` lines 191-210
- **Data**:
  - session_id
  - problem.title, problem.description, problem.context
  - For resume: round_number, phase, expert count, cost_so_far

### 1.2 Problem Decomposition Events

#### **Decomposition Started**
- **When**: `decompose_node` begins execution
- **Display**: "Problem Decomposition" header
- **Source**: Event name `decompose`, detected in console.py lines 230-231
- **Node**: `decompose_node` (nodes.py:34)

#### **Decomposition Complete**
- **When**: `decompose_node` completes
- **Display**: List of sub-problems with goals and rationale
- **Source**: `_display_sub_problems()` lines 308-327
- **Data**:
  - sub_problems: list[{id, goal, rationale, complexity_score, dependencies}]
  - count: number of sub-problems
- **Node Output**: `state.get("sub_problems", [])`

### 1.3 Persona Selection Events

#### **Persona Selection Started**
- **When**: `select_personas_node` begins
- **Display**: "Expert Panel Selected" header
- **Source**: Event name `select_personas`, detected lines 232-247
- **Node**: `select_personas_node` (nodes.py:117)

#### **Persona Selected** (per expert)
- **When**: Each persona is chosen
- **Display**: Name, code, expertise, selection rationale
- **Source**: `_display_personas()` lines 330-368
- **Data**:
  - persona: {code, name, display_name, domain_expertise}
  - rationale: Why this expert was chosen
  - expertise: List of domain areas
- **Node Output**: `state.get("personas", [])`, `state.get("persona_recommendations", [])`

#### **Sub-Problem Context** (multi-sub-problem only)
- **When**: Starting deliberation on a specific sub-problem
- **Display**: "Sub-Problem X of Y" with goal
- **Source**: Lines 237-247
- **Data**:
  - sub_problem_index
  - total_sub_problems
  - current_sub_problem.goal

### 1.4 Initial Round Events

#### **Initial Round Started**
- **When**: `initial_round_node` begins
- **Display**: "Initial Round - All Experts Contribute" header
- **Source**: Event name `initial_round`, lines 248-254
- **Node**: `initial_round_node` (nodes.py:187)

#### **Persona Contribution** (parallel, all experts)
- **When**: Each expert contributes in initial round
- **Display**: Expert name, round number, contribution text
- **Source**: `_display_contribution()` lines 371-383
- **Data**:
  - persona_name
  - persona_code
  - content: contribution text
  - round_number: 0 or 1
- **Node Output**: `state.get("contributions", [])`

### 1.5 Multi-Round Deliberation Events

#### **Facilitator Decision**
- **When**: `facilitator_decide_node` completes
- **Display**: Action, reasoning, next speaker (if continue)
- **Source**: `_display_facilitator_decision()` lines 386-407
- **Data**:
  - action: "continue" | "vote" | "moderator" | "research" | "clarify"
  - reasoning: Short explanation (truncated to 200 chars)
  - next_speaker: Persona code (if action=continue)
  - moderator_type: "contrarian" | "skeptic" | "optimist" (if action=moderator)
  - research_query: Query string (if action=research)
- **Node**: `facilitator_decide_node` (nodes.py:231)
- **Node Output**: `state.get("facilitator_decision", {})`

#### **Persona Contribution** (sequential)
- **When**: Single expert contributes in follow-up round
- **Display**: Same as initial round contribution
- **Source**: Event name `persona_contribute`, lines 260-265
- **Node**: `persona_contribute_node` (nodes.py:285)

#### **Moderator Intervention**
- **When**: Moderator intervenes to redirect conversation
- **Display**: "Moderator Intervention (Round X)" header, intervention text
- **Source**: Event name `moderator_intervene`, lines 268-275
- **Data**:
  - moderator_type: Type of intervention
  - content: Intervention message
  - round_number: Current round
- **Node**: `moderator_intervene_node` (nodes.py:394)

### 1.6 Convergence Check Events

#### **Convergence Check Result**
- **When**: After each contribution, `check_convergence_node` runs
- **Display**: Status (CONTINUING/STOPPING), reason, round progress
- **Source**: `_display_convergence_check()` lines 410-427
- **Data**:
  - should_stop: boolean
  - stop_reason: "max_rounds" | "consensus" | "hard_cap_15_rounds" | etc.
  - round_number: Current round
  - max_rounds: Configured maximum
  - convergence_score: 0.0-1.0 (optional)
- **Node**: `check_convergence_node` (safety/loop_prevention.py:135)
- **Node Output**: `state.get("should_stop")`, `state.get("stop_reason")`

### 1.7 Voting Phase Events

#### **Voting Started**
- **When**: `vote_node` begins after convergence
- **Display**: "Recommendations" header
- **Source**: Event name `vote`, lines 276-277
- **Node**: `vote_node` (nodes.py:491)

#### **Persona Vote/Recommendation** (per expert)
- **When**: Each expert provides recommendation
- **Display**: Expert name, recommendation, confidence, reasoning, conditions
- **Source**: `_display_votes()` lines 430-463
- **Data**:
  - persona_name
  - recommendation: Free-form string (NOT binary)
  - confidence: 0.0-1.0
  - reasoning: Truncated to 150 chars
  - conditions: List of prerequisite conditions
- **Node Output**: `state.get("votes", [])` (actually recommendations)

### 1.8 Synthesis Events

#### **Synthesis Started**
- **When**: `synthesize_node` begins
- **Display**: "Final Synthesis" header
- **Source**: Event name `synthesize`, lines 278-279
- **Node**: `synthesize_node` (nodes.py:552)

#### **Synthesis Complete**
- **When**: Synthesis report generated
- **Display**: Full synthesis report text
- **Source**: `_display_synthesis()` lines 466-481
- **Data**:
  - synthesis: Complete markdown report with recommendations
- **Node Output**: `state.get("synthesis")`

### 1.9 Multi-Sub-Problem Events

#### **Sub-Problem Complete**
- **When**: `next_subproblem_node` saves result
- **Display**: Checkmark, cost, duration, expert panel
- **Source**: `_display_subproblem_completion()` lines 484-501
- **Data**:
  - sub_problem_index
  - cost: Sub-problem cost
  - duration_seconds: Time taken
  - expert_panel: List of persona codes
- **Node**: `next_subproblem_node` (nodes.py:653)

#### **Meta-Synthesis Started**
- **When**: `meta_synthesize_node` begins (all sub-problems complete)
- **Display**: "Cross-Sub-Problem Meta-Synthesis" header
- **Source**: Event name `meta_synthesize`, lines 280-285
- **Node**: `meta_synthesize_node` (nodes.py:802)

#### **Meta-Synthesis Complete**
- **When**: Meta-synthesis report generated
- **Display**: Integrated report in panel with magenta border
- **Source**: `_display_meta_synthesis()` lines 504-531
- **Data**:
  - synthesis: Meta-synthesis markdown report
  - sub_problem_results: Array of results

### 1.10 Completion Events

#### **Deliberation Complete**
- **When**: Graph execution reaches END
- **Display**: Summary panel, phase cost table, metrics
- **Source**: `_display_results()` lines 566-620
- **Data**:
  - phase: Final phase
  - round_number: Total rounds
  - total_cost: Final USD cost
  - total_tokens: Token count
  - stop_reason: Why it stopped
  - contributions: Summary of all contributions
  - session_id: For resume

#### **Phase Cost Breakdown**
- **When**: At completion
- **Display**: Rich table with phase, cost, percentage
- **Source**: `_display_phase_costs()` lines 534-563
- **Data**:
  - phase_costs: {phase_name: cost_usd}
  - Calculated percentages

### 1.11 Error Events

#### **Error**
- **When**: Exception in graph execution
- **Display**: Red error message with details
- **Source**: Lines 291-293
- **Data**:
  - error: Error message string
  - error_type: Exception class name

---

## Part 2: Current State Assessment

### 2.1 Current Backend Implementation (`backend/api/streaming.py`)

**Approach**: State polling with keepalive

**Current Events Emitted**:
1. `stream_connected` - Connection established
2. `: keepalive\n\n` - Every 15 seconds
3. `node_start` - Phase change detected (polls `current_node` from Redis)
4. `node_end` - Stream ended
5. `complete` - Task done (with final output, cost, rounds)
6. `error` - Exception occurred

**Gaps**:
- ❌ No decomposition events (sub-problems)
- ❌ No persona selection details (just node_start)
- ❌ No individual contributions streaming
- ❌ No facilitator decisions
- ❌ No convergence check results
- ❌ No voting/recommendation details
- ❌ No moderator interventions
- ❌ No synthesis content streaming
- ❌ No sub-problem completion events
- ❌ No meta-synthesis events
- ⚠️ Polls Redis every 2 seconds - inefficient
- ⚠️ Only tracks phase changes, not granular events

### 2.2 Current Event Formatters (`backend/api/events.py`)

**Existing Functions**:
1. `node_start_event()` - Generic node start
2. `node_end_event()` - Generic node end
3. `contribution_event()` - Has persona contribution (✅ good!)
4. `facilitator_decision_event()` - Has facilitator decision (✅ good!)
5. `convergence_event()` - Has convergence check (✅ good!)
6. `complete_event()` - Has completion
7. `error_event()` - Has error
8. `clarification_requested_event()` - Has clarification (✅ good!)
9. `clarification_answered_event()` - Has answer

**Missing Functions**:
- ❌ `decomposition_started_event()`
- ❌ `decomposition_complete_event()`
- ❌ `persona_selection_started_event()`
- ❌ `persona_selected_event()` (per expert)
- ❌ `persona_selection_complete_event()`
- ❌ `initial_round_started_event()`
- ❌ `moderator_intervention_event()`
- ❌ `voting_started_event()`
- ❌ `persona_vote_event()` (per expert)
- ❌ `synthesis_started_event()`
- ❌ `synthesis_complete_event()` (with full text)
- ❌ `subproblem_started_event()`
- ❌ `subproblem_complete_event()`
- ❌ `meta_synthesis_started_event()`
- ❌ `meta_synthesis_complete_event()`
- ❌ `phase_cost_breakdown_event()`

### 2.3 Current Frontend Implementation (`frontend/src/routes/(app)/meeting/[id]/+page.svelte`)

**Current Event Listeners**:
1. Default `onmessage` - Parses JSON, adds to events array
2. `phase_change` - Custom listener (but not used in current events.py!)
3. `persona_contribution` - Custom listener (but not used!)
4. `synthesis` - Custom listener (but not used!)
5. `complete` - Custom listener (✅ works)
6. `onerror` - Retry with backoff

**Display Logic**:
- Shows event icons by type
- Displays persona_contribution.content
- Displays synthesis.content
- Displays phase_change.new_phase
- Generic JSON dump for unknown events

**Gaps**:
- ❌ No decomposition display
- ❌ No persona selection display (with rationale)
- ❌ No facilitator decision display
- ❌ No convergence check display
- ❌ No voting display (individual votes)
- ❌ No moderator intervention styling
- ❌ No sub-problem progress tracking
- ❌ No meta-synthesis distinction
- ❌ No phase cost breakdown table
- ❌ Event listeners don't match emitted events!

---

## Part 3: Architecture Design - Event Capture Strategy

### 3.1 Evaluation of Options

#### **Option A: LangGraph `astream_events()` - RECOMMENDED ✅**

**How it works**:
- LangGraph's `astream_events(version="v2")` yields events during graph execution
- Event types: `on_chain_start`, `on_chain_end`, `on_chain_stream`
- Each event includes: `event` (type), `name` (node name), `data` (output)
- Console interface ALREADY uses this (lines 217-289)

**Advantages**:
- ✅ Already implemented in console - proven to work
- ✅ Real-time - no polling needed
- ✅ Captures all node starts and completions
- ✅ Includes node output data immediately
- ✅ No state modifications needed
- ✅ Works with checkpointing

**Disadvantages**:
- ⚠️ Must process events in background task
- ⚠️ Requires event queue/buffer for SSE transmission
- ⚠️ No built-in backpressure handling

**Verdict**: **BEST OPTION** - Console proves this works perfectly.

#### **Option B: State Polling with Event Detection**

**Current approach** - polling Redis every 2 seconds to detect phase changes.

**Advantages**:
- ✅ Simple to implement
- ✅ Works with existing code

**Disadvantages**:
- ❌ High latency (2-second delay)
- ❌ Inefficient (constant Redis queries)
- ❌ Misses granular events (only sees phase changes)
- ❌ Can't detect multiple events in same phase
- ❌ No contribution content streamed

**Verdict**: Current approach - should be replaced.

#### **Option C: Custom Event Emitter in Nodes**

**How it works**: Add event emitter to each node, emit custom events.

**Advantages**:
- ✅ Full control over events
- ✅ Can add metadata easily

**Disadvantages**:
- ❌ Requires modifying all 13 nodes
- ❌ Duplicates LangGraph's built-in events
- ❌ More code to maintain
- ❌ Console wouldn't use it (inconsistent)

**Verdict**: Over-engineering - LangGraph already provides what we need.

### 3.2 Recommended Architecture: LangGraph `astream_events()` with Event Queue

```
┌─────────────────────────────────────────────────────────────────┐
│                       SessionManager                             │
│  - Manages background graph execution tasks                      │
│  - Tracks active_executions: {session_id: Task}                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Background Execution Task    │
              │  async def execute_session()  │
              └───────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
        ┌───────────────────┐   ┌─────────────────┐
        │ LangGraph Execution│   │ Event Collector │
        │ graph.astream_      │──>│  (queue)       │
        │   events()          │   │                │
        └───────────────────┘   └─────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              │  Redis PubSub       │
                              │  Channel per session│
                              │  Format: events:sid │
                              └──────────┬──────────┘
                                         │
                              ┌──────────▼──────────┐
                              │   SSE Endpoint      │
                              │   /stream           │
                              │   - Subscribes to   │
                              │     Redis channel   │
                              │   - Formats SSE     │
                              └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │ Frontend EventSource│
                              │  - Receives events  │
                              │  - Updates UI       │
                              └─────────────────────┘
```

**Key Components**:

1. **Event Collector** (NEW):
   - Wraps `graph.astream_events()`
   - Parses LangGraph events
   - Maps to SSE event types
   - Publishes to Redis pubsub channel `events:{session_id}`

2. **Redis PubSub** (NEW):
   - Each session has dedicated channel: `events:{session_id}`
   - Events published during execution
   - Multiple clients can subscribe (future: admin monitoring)
   - Auto-cleanup when task completes

3. **SSE Endpoint** (MODIFIED):
   - Subscribes to Redis channel `events:{session_id}`
   - Formats messages as SSE
   - Handles reconnection (last event ID)
   - Adds keepalive (every 15s)

4. **Frontend** (MODIFIED):
   - EventSource connection to `/api/v1/sessions/{id}/stream`
   - Event handlers for each event type
   - Rich UI rendering per event

### 3.3 Event Flow Example

```
User clicks "Start" in frontend
  │
  ▼
POST /api/v1/sessions/{id}/start
  │
  ▼
SessionManager.start_session(session_id, user_id, coro)
  │
  ├─> Creates background task
  │   └─> Executes graph.astream_events(state, config)
  │       │
  │       ├─> on_chain_start: "decompose"
  │       │   └─> publish_event("decomposition_started", {session_id})
  │       │
  │       ├─> on_chain_end: "decompose"
  │       │   └─> publish_event("decomposition_complete", {sub_problems: [...]})
  │       │
  │       ├─> on_chain_start: "select_personas"
  │       │   └─> publish_event("persona_selection_started", {session_id})
  │       │
  │       └─> ... (continues for all nodes)
  │
  └─> Returns 202 Accepted immediately

Frontend connects EventSource to GET /stream
  │
  ▼
Subscribe to Redis channel "events:{session_id}"
  │
  ▼
Receive events → Format as SSE → Stream to client
  │
  ▼
Frontend renders events in real-time
```

---

## Part 4: Implementation Plan

### Phase 1: Backend Event Infrastructure (1-2 days)

#### **Step 1.1: Create Event Publisher** (`backend/api/event_publisher.py`)

```python
"""Event publisher using Redis PubSub for real-time SSE streaming."""

import json
import logging
from typing import Any
from redis import Redis

logger = logging.getLogger(__name__)

class EventPublisher:
    """Publishes deliberation events to Redis PubSub for SSE streaming."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def publish_event(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any]
    ) -> None:
        """Publish event to session's Redis channel.

        Args:
            session_id: Session identifier
            event_type: SSE event type (e.g., "decomposition_started")
            data: Event payload (will be JSON serialized)
        """
        channel = f"events:{session_id}"

        # Add timestamp and session_id to all events
        from datetime import datetime, UTC
        payload = {
            "event_type": event_type,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data
        }

        message = json.dumps(payload)
        self.redis.publish(channel, message)
        logger.debug(f"Published {event_type} to {channel}")
```

**Files to create**:
- `backend/api/event_publisher.py`

**Files to modify**:
- `backend/api/dependencies.py` - Add `get_event_publisher()` singleton

#### **Step 1.2: Expand Event Formatters** (`backend/api/events.py`)

Add missing SSE event formatting functions (see Part 2.2 for full list):

```python
def decomposition_started_event(session_id: str) -> str:
    """Create SSE event for decomposition start."""
    return format_sse_event(
        "decomposition_started",
        {
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

def decomposition_complete_event(
    session_id: str,
    sub_problems: list[dict[str, Any]]
) -> str:
    """Create SSE event for decomposition completion."""
    return format_sse_event(
        "decomposition_complete",
        {
            "session_id": session_id,
            "sub_problems": sub_problems,  # [{id, goal, rationale, complexity_score}]
            "count": len(sub_problems),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

# ... Add remaining 15+ event formatters (see Part 2.2)
```

**Files to modify**:
- `backend/api/events.py` - Add 15+ new event formatters

#### **Step 1.3: Create Event Collector** (`backend/api/event_collector.py`)

```python
"""Event collector that wraps LangGraph astream_events and publishes to Redis."""

import logging
from typing import Any, AsyncGenerator
from backend.api.event_publisher import EventPublisher

logger = logging.getLogger(__name__)

class EventCollector:
    """Collects LangGraph events and publishes them to Redis for SSE streaming."""

    def __init__(self, publisher: EventPublisher):
        self.publisher = publisher

    async def collect_and_publish(
        self,
        session_id: str,
        graph: Any,  # CompiledStateGraph
        initial_state: Any,  # DeliberationGraphState
        config: dict[str, Any]
    ) -> Any:  # Final state
        """Execute graph and publish all events to Redis.

        Args:
            session_id: Session identifier
            graph: Compiled LangGraph
            initial_state: Initial graph state (or None to resume)
            config: Graph execution config

        Returns:
            Final deliberation state
        """
        final_state = None

        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event")
            event_name = event.get("name", "")

            # Process node completions (on_chain_end has output data)
            if event_type == "on_chain_end" and "data" in event:
                output = event.get("data", {}).get("output", {})

                # Map node names to SSE events
                if event_name == "decompose" and isinstance(output, dict):
                    await self._handle_decomposition(session_id, output)

                elif event_name == "select_personas" and isinstance(output, dict):
                    await self._handle_persona_selection(session_id, output)

                elif event_name == "initial_round" and isinstance(output, dict):
                    await self._handle_initial_round(session_id, output)

                elif event_name == "facilitator_decide" and isinstance(output, dict):
                    await self._handle_facilitator_decision(session_id, output)

                elif event_name == "persona_contribute" and isinstance(output, dict):
                    await self._handle_contribution(session_id, output)

                elif event_name == "moderator_intervene" and isinstance(output, dict):
                    await self._handle_moderator(session_id, output)

                elif event_name == "check_convergence" and isinstance(output, dict):
                    await self._handle_convergence(session_id, output)

                elif event_name == "vote" and isinstance(output, dict):
                    await self._handle_voting(session_id, output)

                elif event_name == "synthesize" and isinstance(output, dict):
                    await self._handle_synthesis(session_id, output)

                elif event_name == "next_subproblem" and isinstance(output, dict):
                    await self._handle_subproblem_complete(session_id, output)

                elif event_name == "meta_synthesize" and isinstance(output, dict):
                    await self._handle_meta_synthesis(session_id, output)

                # Capture final state
                if isinstance(output, dict):
                    final_state = output

        return final_state

    async def _handle_decomposition(self, session_id: str, output: dict) -> None:
        """Handle decompose node completion."""
        sub_problems = output.get("sub_problems", [])

        # Convert SubProblem objects to dicts
        sub_problems_dicts = [
            {
                "id": sp.id,
                "goal": sp.goal,
                "rationale": sp.rationale,
                "complexity_score": sp.complexity_score,
                "dependencies": sp.dependencies
            }
            for sp in sub_problems
        ]

        self.publisher.publish_event(
            session_id,
            "decomposition_complete",
            {"sub_problems": sub_problems_dicts, "count": len(sub_problems)}
        )

    # ... Add remaining 10+ handler methods (similar pattern)
```

**Files to create**:
- `backend/api/event_collector.py`

#### **Step 1.4: Modify Control Endpoint** (`backend/api/control.py`)

Replace direct `graph.ainvoke()` with `EventCollector.collect_and_publish()`:

```python
# In start_deliberation() endpoint (line 170):

from backend.api.event_collector import EventCollector
from backend.api.dependencies import get_event_publisher

# Replace:
# coro = graph.ainvoke(state, config=config)

# With:
collector = EventCollector(get_event_publisher())
coro = collector.collect_and_publish(session_id, graph, state, config)
```

**Files to modify**:
- `backend/api/control.py` - Lines 170-173 (start endpoint)
- `backend/api/control.py` - Lines 328-329 (resume endpoint)

### Phase 2: Backend SSE Streaming (1 day)

#### **Step 2.1: Modify Streaming Endpoint** (`backend/api/streaming.py`)

Replace polling logic with Redis pubsub subscription:

```python
async def stream_session_events(session_id: str) -> AsyncGenerator[str, None]:
    """Stream deliberation events via Redis PubSub."""
    from backend.api.dependencies import get_redis_manager

    redis_manager = get_redis_manager()
    redis_client = redis_manager.redis  # Get underlying Redis client

    # Create pubsub connection
    pubsub = redis_client.pubsub()
    channel = f"events:{session_id}"

    try:
        # Subscribe to session's event channel
        pubsub.subscribe(channel)

        # Send initial connection event
        yield node_start_event("stream_connected", session_id)

        logger.info(f"SSE client subscribed to {channel}")

        # Stream events from Redis pubsub
        while True:
            message = pubsub.get_message(timeout=1.0)

            if message and message["type"] == "message":
                # Parse event payload
                payload = json.loads(message["data"])
                event_type = payload["event_type"]
                data = payload["data"]

                # Format as SSE using event formatters from events.py
                sse_event = format_sse_for_type(event_type, session_id, data)
                yield sse_event

                # If complete event, close stream
                if event_type == "complete":
                    break

            # Keepalive every 15 seconds
            # (Use asyncio timer, check if 15s elapsed since last message)

    except Exception as e:
        logger.error(f"SSE stream error for {session_id}: {e}")
        yield error_event(session_id, str(e))
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        logger.info(f"SSE client disconnected from {channel}")
```

**Files to modify**:
- `backend/api/streaming.py` - Rewrite `stream_session_events()` function (lines 30-160)

#### **Step 2.2: Add Helper Function for Event Mapping**

```python
def format_sse_for_type(event_type: str, session_id: str, data: dict) -> str:
    """Map event type to SSE formatter function."""
    from backend.api import events

    # Map event_type to formatter function
    formatters = {
        "decomposition_started": lambda: events.decomposition_started_event(session_id),
        "decomposition_complete": lambda: events.decomposition_complete_event(
            session_id, data["sub_problems"]
        ),
        "persona_selection_started": lambda: events.persona_selection_started_event(session_id),
        # ... Add remaining 20+ mappings
    }

    formatter = formatters.get(event_type)
    if formatter:
        return formatter()
    else:
        # Fallback: Generic event
        return events.format_sse_event(event_type, data)
```

**Files to modify**:
- `backend/api/streaming.py` - Add helper function

### Phase 3: Frontend Event Handling (1-2 days)

#### **Step 3.1: Create Event Type Definitions** (`frontend/src/lib/api/sse-events.ts`)

```typescript
// SSE event type definitions
export interface SSEEvent {
  type: string;
  data: any;
  timestamp: string;
}

export interface DecompositionCompleteEvent extends SSEEvent {
  type: 'decomposition_complete';
  data: {
    session_id: string;
    sub_problems: Array<{
      id: string;
      goal: string;
      rationale: string;
      complexity_score: number;
      dependencies: string[];
    }>;
    count: number;
  };
}

export interface PersonaSelectedEvent extends SSEEvent {
  type: 'persona_selected';
  data: {
    session_id: string;
    persona: {
      code: string;
      name: string;
      display_name: string;
      domain_expertise: string[];
    };
    rationale: string;
  };
}

// ... Add remaining 20+ event interfaces
```

**Files to create**:
- `frontend/src/lib/api/sse-events.ts`

#### **Step 3.2: Create Event Components** (`frontend/src/lib/components/events/`)

Create specialized components for each event type:

```svelte
<!-- DecompositionComplete.svelte -->
<script lang="ts">
  import type { DecompositionCompleteEvent } from '$lib/api/sse-events';

  export let event: DecompositionCompleteEvent;
</script>

<div class="event-card decomposition">
  <h3>Problem Decomposition</h3>
  <p>Decomposed into {event.data.count} sub-problems:</p>

  <ol>
    {#each event.data.sub_problems as sp, i}
      <li>
        <strong>{sp.goal}</strong>
        {#if sp.rationale}
          <p class="rationale">{sp.rationale}</p>
        {/if}
      </li>
    {/each}
  </ol>
</div>

<style>
  .event-card {
    padding: 1rem;
    border-left: 4px solid var(--primary);
    margin-bottom: 1rem;
  }

  .rationale {
    font-size: 0.9em;
    color: var(--text-secondary);
  }
</style>
```

**Files to create** (17 components):
1. `frontend/src/lib/components/events/DecompositionComplete.svelte`
2. `frontend/src/lib/components/events/PersonaSelection.svelte`
3. `frontend/src/lib/components/events/InitialRoundStarted.svelte`
4. `frontend/src/lib/components/events/PersonaContribution.svelte`
5. `frontend/src/lib/components/events/FacilitatorDecision.svelte`
6. `frontend/src/lib/components/events/ModeratorIntervention.svelte`
7. `frontend/src/lib/components/events/ConvergenceCheck.svelte`
8. `frontend/src/lib/components/events/VotingStarted.svelte`
9. `frontend/src/lib/components/events/PersonaVote.svelte`
10. `frontend/src/lib/components/events/SynthesisComplete.svelte`
11. `frontend/src/lib/components/events/SubProblemComplete.svelte`
12. `frontend/src/lib/components/events/MetaSynthesis.svelte`
13. `frontend/src/lib/components/events/DeliberationComplete.svelte`
14. `frontend/src/lib/components/events/ErrorEvent.svelte`
15. `frontend/src/lib/components/events/index.ts` (barrel export)

#### **Step 3.3: Modify Meeting Page** (`frontend/src/routes/(app)/meeting/[id]/+page.svelte`)

Replace generic event rendering with specialized components:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import * as EventComponents from '$lib/components/events';

  // ... existing code ...

  function getEventComponent(event: StreamEvent) {
    const componentMap = {
      'decomposition_complete': EventComponents.DecompositionComplete,
      'persona_selected': EventComponents.PersonaSelection,
      'persona_contribution': EventComponents.PersonaContribution,
      'facilitator_decision': EventComponents.FacilitatorDecision,
      'moderator_intervention': EventComponents.ModeratorIntervention,
      'convergence': EventComponents.ConvergenceCheck,
      'persona_vote': EventComponents.PersonaVote,
      'synthesis_complete': EventComponents.SynthesisComplete,
      'complete': EventComponents.DeliberationComplete,
      'error': EventComponents.ErrorEvent,
      // ... Add remaining mappings
    };

    return componentMap[event.type] || null;
  }
</script>

<!-- In the events list -->
{#each events as event (event.timestamp)}
  {@const EventComponent = getEventComponent(event)}

  {#if EventComponent}
    <svelte:component this={EventComponent} {event} />
  {:else}
    <!-- Fallback for unknown events -->
    <div class="event-card generic">
      <pre>{JSON.stringify(event, null, 2)}</pre>
    </div>
  {/if}
{/each}
```

**Files to modify**:
- `frontend/src/routes/(app)/meeting/[id]/+page.svelte` - Lines 320-374

#### **Step 3.4: Update Event Listeners**

Replace current listeners with comprehensive set:

```typescript
// Add listener for each event type
eventSource.addEventListener('decomposition_started', handleDecompositionStarted);
eventSource.addEventListener('decomposition_complete', handleDecompositionComplete);
eventSource.addEventListener('persona_selection_started', handlePersonaSelectionStarted);
eventSource.addEventListener('persona_selected', handlePersonaSelected);
// ... Add remaining 20+ listeners
```

**Files to modify**:
- `frontend/src/routes/(app)/meeting/[id]/+page.svelte` - Lines 109-144

### Phase 4: Testing & Polish (1 day)

#### **Step 4.1: Unit Tests**

Test files to create:

1. `tests/api/test_event_publisher.py`
   - Test event publishing to Redis
   - Test channel naming
   - Test JSON serialization

2. `tests/api/test_event_collector.py`
   - Test LangGraph event parsing
   - Test event handler methods
   - Test error handling

3. `tests/api/test_streaming.py`
   - Test SSE formatting
   - Test Redis pubsub subscription
   - Test keepalive
   - Test reconnection

#### **Step 4.2: Integration Tests**

Test files to create:

1. `tests/integration/test_end_to_end_streaming.py`
   - Start deliberation
   - Connect SSE stream
   - Verify all expected events received
   - Verify event order
   - Verify event data accuracy

#### **Step 4.3: Manual Testing Checklist**

- [ ] Start new session, verify all events appear in order
- [ ] Verify decomposition shows sub-problems correctly
- [ ] Verify persona selection shows rationale
- [ ] Verify contributions display in real-time
- [ ] Verify facilitator decisions show reasoning
- [ ] Verify moderator interventions render differently
- [ ] Verify convergence checks show progress
- [ ] Verify voting shows all recommendations
- [ ] Verify synthesis displays full report
- [ ] Verify multi-sub-problem flow works
- [ ] Verify meta-synthesis renders correctly
- [ ] Verify completion shows cost breakdown
- [ ] Test pause/resume maintains event stream
- [ ] Test kill stops stream immediately
- [ ] Test reconnection after network drop
- [ ] Test multiple concurrent sessions don't interfere

---

## Part 5: Complete SSE Event Schema

### Event Types Summary (25 total)

| # | Event Name | When Emitted | Data Fields | Frontend Component |
|---|---|---|---|---|
| 1 | `session_started` | Session initialization | session_id, problem_statement | SessionHeader |
| 2 | `decomposition_started` | decompose node start | session_id | LoadingIndicator |
| 3 | `decomposition_complete` | decompose node end | sub_problems[], count | DecompositionComplete |
| 4 | `persona_selection_started` | select_personas node start | session_id | LoadingIndicator |
| 5 | `persona_selected` | Each persona chosen | persona{code,name,expertise}, rationale | PersonaCard |
| 6 | `persona_selection_complete` | select_personas node end | personas[], count | PersonaPanel |
| 7 | `subproblem_started` | Starting deliberation on sub-problem | sub_problem_index, goal | SubProblemHeader |
| 8 | `initial_round_started` | initial_round node start | round_number=1 | RoundHeader |
| 9 | `contribution` | Persona contributes | persona_code, persona_name, content, round | ContributionCard |
| 10 | `facilitator_decision` | facilitator_decide node end | action, reasoning, next_speaker, round | FacilitatorCard |
| 11 | `moderator_intervention` | moderator_intervene node end | moderator_type, content, round | ModeratorCard |
| 12 | `convergence` | check_convergence node end | should_stop, stop_reason, score, round | ConvergenceIndicator |
| 13 | `round_started` | New round begins | round_number | RoundHeader |
| 14 | `voting_started` | vote node start | round_number | VotingHeader |
| 15 | `persona_vote` | Each expert votes | persona_code, recommendation, confidence, reasoning, conditions | VoteCard |
| 16 | `voting_complete` | vote node end | votes[], count | VotingSummary |
| 17 | `synthesis_started` | synthesize node start | - | LoadingIndicator |
| 18 | `synthesis_complete` | synthesize node end | synthesis (markdown text) | SynthesisPanel |
| 19 | `subproblem_complete` | next_subproblem node end | sub_problem_index, cost, duration, expert_panel | SubProblemSummary |
| 20 | `meta_synthesis_started` | meta_synthesize node start | sub_problem_count | LoadingIndicator |
| 21 | `meta_synthesis_complete` | meta_synthesize node end | synthesis (markdown text) | MetaSynthesisPanel |
| 22 | `phase_cost_breakdown` | Deliberation complete | phase_costs{} | CostTable |
| 23 | `complete` | Graph reaches END | final_output, total_cost, total_rounds | CompletionCard |
| 24 | `error` | Exception occurs | error, error_type | ErrorAlert |
| 25 | `clarification_requested` | facilitator action=clarify | question, reason, round | ClarificationPrompt |

### Detailed Event Schemas

#### 1. `session_started`
```json
{
  "event_type": "session_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:00Z",
  "data": {
    "problem_statement": "Should we invest $500K in AI automation?",
    "max_rounds": 10,
    "user_id": "user_xyz"
  }
}
```

#### 2. `decomposition_started`
```json
{
  "event_type": "decomposition_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:01Z",
  "data": {}
}
```

#### 3. `decomposition_complete`
```json
{
  "event_type": "decomposition_complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:05Z",
  "data": {
    "sub_problems": [
      {
        "id": "sp_001",
        "goal": "Assess ROI and payback period",
        "rationale": "Financial viability is critical",
        "complexity_score": 7,
        "dependencies": []
      },
      {
        "id": "sp_002",
        "goal": "Evaluate implementation risks",
        "rationale": "Risk mitigation required",
        "complexity_score": 8,
        "dependencies": ["sp_001"]
      }
    ],
    "count": 2
  }
}
```

#### 4. `persona_selection_started`
```json
{
  "event_type": "persona_selection_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:06Z",
  "data": {}
}
```

#### 5. `persona_selected`
```json
{
  "event_type": "persona_selected",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:08Z",
  "data": {
    "persona": {
      "code": "CFO",
      "name": "Zara Kim",
      "display_name": "Zara Kim (CFO)",
      "domain_expertise": ["financial analysis", "budgeting", "risk assessment"]
    },
    "rationale": "Financial analysis expertise needed for ROI assessment",
    "order": 1
  }
}
```

#### 6. `persona_selection_complete`
```json
{
  "event_type": "persona_selection_complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:10Z",
  "data": {
    "personas": ["CFO", "CTO", "OPER"],
    "count": 3
  }
}
```

#### 7. `subproblem_started`
```json
{
  "event_type": "subproblem_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:11Z",
  "data": {
    "sub_problem_index": 0,
    "sub_problem_id": "sp_001",
    "goal": "Assess ROI and payback period",
    "total_sub_problems": 2
  }
}
```

#### 8. `initial_round_started`
```json
{
  "event_type": "initial_round_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:12Z",
  "data": {
    "round_number": 1,
    "experts": ["CFO", "CTO", "OPER"]
  }
}
```

#### 9. `contribution`
```json
{
  "event_type": "contribution",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:15Z",
  "data": {
    "persona_code": "CFO",
    "persona_name": "Zara Kim",
    "content": "From a financial perspective, the $500K investment shows a projected 24-month payback period...",
    "round": 1,
    "contribution_type": "initial"
  }
}
```

#### 10. `facilitator_decision`
```json
{
  "event_type": "facilitator_decision",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:31:00Z",
  "data": {
    "action": "continue",
    "reasoning": "CTO raised valid concerns about scalability that need addressing",
    "next_speaker": "CFO",
    "round": 2
  }
}
```

#### 11. `moderator_intervention`
```json
{
  "event_type": "moderator_intervention",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:32:00Z",
  "data": {
    "moderator_type": "contrarian",
    "content": "I notice the discussion is focusing heavily on benefits. What about the risks of NOT implementing AI?",
    "trigger_reason": "Discussion lacks balance",
    "round": 3
  }
}
```

#### 12. `convergence`
```json
{
  "event_type": "convergence",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:33:00Z",
  "data": {
    "converged": false,
    "score": 0.73,
    "threshold": 0.85,
    "should_stop": false,
    "stop_reason": null,
    "round": 3,
    "max_rounds": 10
  }
}
```

#### 13. `round_started`
```json
{
  "event_type": "round_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:33:05Z",
  "data": {
    "round_number": 4
  }
}
```

#### 14. `voting_started`
```json
{
  "event_type": "voting_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:35:00Z",
  "data": {
    "experts": ["CFO", "CTO", "OPER"],
    "count": 3
  }
}
```

#### 15. `persona_vote`
```json
{
  "event_type": "persona_vote",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:35:05Z",
  "data": {
    "persona_code": "CFO",
    "persona_name": "Zara Kim",
    "recommendation": "Invest $500K in AI automation with phased rollout",
    "confidence": 0.85,
    "reasoning": "ROI analysis shows 24-month payback with 40% efficiency gains",
    "conditions": [
      "Secure executive buy-in",
      "Establish KPIs for measuring success",
      "Budget for training and change management"
    ]
  }
}
```

#### 16. `voting_complete`
```json
{
  "event_type": "voting_complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:35:15Z",
  "data": {
    "votes_count": 3,
    "consensus_level": "strong"
  }
}
```

#### 17. `synthesis_started`
```json
{
  "event_type": "synthesis_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:35:16Z",
  "data": {}
}
```

#### 18. `synthesis_complete`
```json
{
  "event_type": "synthesis_complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:35:25Z",
  "data": {
    "synthesis": "# Final Recommendation\n\nAfter thorough deliberation...",
    "word_count": 1250
  }
}
```

#### 19. `subproblem_complete`
```json
{
  "event_type": "subproblem_complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:35:26Z",
  "data": {
    "sub_problem_index": 0,
    "sub_problem_id": "sp_001",
    "goal": "Assess ROI and payback period",
    "cost": 0.0452,
    "duration_seconds": 180.5,
    "expert_panel": ["CFO", "CTO", "OPER"],
    "contribution_count": 12
  }
}
```

#### 20. `meta_synthesis_started`
```json
{
  "event_type": "meta_synthesis_started",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:40:00Z",
  "data": {
    "sub_problem_count": 2,
    "total_contributions": 24,
    "total_cost": 0.0904
  }
}
```

#### 21. `meta_synthesis_complete`
```json
{
  "event_type": "meta_synthesis_complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:40:15Z",
  "data": {
    "synthesis": "# Comprehensive Meta-Synthesis\n\nIntegrating insights from 2 deliberations...",
    "word_count": 2100
  }
}
```

#### 22. `phase_cost_breakdown`
```json
{
  "event_type": "phase_cost_breakdown",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:40:16Z",
  "data": {
    "phase_costs": {
      "problem_decomposition": 0.0023,
      "persona_selection": 0.0015,
      "initial_round": 0.0187,
      "round_2_deliberation": 0.0089,
      "round_3_deliberation": 0.0095,
      "facilitator_decision": 0.0042,
      "voting": 0.0134,
      "synthesis": 0.0189,
      "meta_synthesis": 0.0230
    },
    "total_cost": 0.1004
  }
}
```

#### 23. `complete`
```json
{
  "event_type": "complete",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:40:17Z",
  "data": {
    "session_id": "bo1_abc123",
    "final_output": "Synthesis complete",
    "total_cost": 0.1004,
    "total_rounds": 5,
    "total_contributions": 24,
    "total_tokens": 45200,
    "duration_seconds": 615,
    "stop_reason": "consensus"
  }
}
```

#### 24. `error`
```json
{
  "event_type": "error",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:30:30Z",
  "data": {
    "session_id": "bo1_abc123",
    "error": "Redis connection timeout",
    "error_type": "ConnectionError",
    "node": "select_personas",
    "recoverable": true
  }
}
```

#### 25. `clarification_requested`
```json
{
  "event_type": "clarification_requested",
  "session_id": "bo1_abc123",
  "timestamp": "2025-01-21T10:31:30Z",
  "data": {
    "session_id": "bo1_abc123",
    "question": "What is your current monthly churn rate?",
    "reason": "CFO needs this to calculate lifetime value",
    "round": 2,
    "question_id": "q_001"
  }
}
```

---

## Implementation Timeline

### Day 1-2: Backend Event Infrastructure
- Create EventPublisher class
- Expand event formatters in events.py (15+ new functions)
- Create EventCollector class with 10+ handler methods
- Modify control.py endpoints

### Day 3: Backend SSE Streaming
- Rewrite stream_session_events() with Redis pubsub
- Add event mapping helper
- Test Redis pubsub locally

### Day 4-5: Frontend Event Handling
- Create SSE event type definitions
- Create 15+ event component files
- Modify meeting page with event routing
- Update event listeners

### Day 6: Testing & Polish
- Write unit tests (3 files)
- Write integration tests (1 file)
- Manual testing checklist (16 items)
- Bug fixes and polish

**Total Estimate**: 6 days

---

## Success Criteria

✅ All 25 event types stream in real-time (no polling)
✅ Events match console display exactly
✅ Multi-sub-problem flow works correctly
✅ Meta-synthesis displays properly
✅ Cost breakdown table renders at end
✅ Pause/resume preserves stream
✅ Kill stops stream immediately
✅ Reconnection works after network drop
✅ Multiple concurrent sessions don't interfere
✅ All unit tests pass
✅ Integration test passes end-to-end

---

## Future Enhancements

1. **Event Replay**: Store events in PostgreSQL, allow users to replay past deliberations
2. **Admin Monitoring**: Subscribe to all sessions' event channels for real-time monitoring
3. **Event Filtering**: Allow users to filter events by type (e.g., only show contributions)
4. **Event Search**: Full-text search across deliberation events
5. **Event Export**: Export event stream as JSON/CSV for analysis
6. **Backpressure Handling**: If client can't keep up, buffer or drop low-priority events
7. **Event Acknowledgement**: Client sends ack for critical events (voting, synthesis)
8. **Delta Updates**: Stream only changes to state, not full objects
9. **Binary Protocol**: Use MessagePack instead of JSON for efficiency
10. **WebSockets**: Consider upgrading to WebSockets for bidirectional communication

---

## References

- **Console Implementation**: `bo1/interfaces/console.py` (lines 217-289)
- **LangGraph Nodes**: `bo1/graph/nodes.py` (all 13 nodes)
- **LangGraph Config**: `bo1/graph/config.py` (graph structure)
- **Current SSE Endpoint**: `backend/api/streaming.py` (current polling approach)
- **Event Formatters**: `backend/api/events.py` (existing formatters)
- **Frontend Page**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte`
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.graph.CompiledGraph.astream_events
