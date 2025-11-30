# Sub-Problem Deliberation as LangGraph Subgraphs

**Date**: 2025-11-29 (Updated)
**Author**: Claude Code Analysis
**Status**: Implementation Plan v2 (Enhanced)
**Estimated Effort**: 4-5 days
**Risk Level**: Medium (well-scoped refactor with clear rollback path)

---

## Executive Summary

Convert `_deliberate_subproblem()` (446 lines of standalone async code) into a proper **LangGraph subgraph** with **real-time intra-node streaming** via `get_stream_writer()`. This enables:

1. **Real-time event streaming** via `get_stream_writer()` (PRIMARY approach, not fallback)
2. **Per-expert progress events** (not just per-node) - `contribution_started` before `contribution`
3. **Per-subproblem checkpointing** (resume from any round, not just start)
4. **Single event system** (no more EventBridge vs EventCollector duality)
5. **Better testability** (LangGraph's testing utilities apply)
6. **Eliminates 619 lines** of duplicated logic

### Key Insight (v2)

The fundamental UX problem is **not** just that subgraphs don't stream events—it's that `asyncio.gather()` blocks until ALL experts finish (20-40 seconds with no UI update). Even with subgraphs, node-level events only fire when nodes complete.

**Solution**: Use `get_stream_writer()` inside nodes to emit granular events:
- `contribution_started` - When expert begins generating (instant feedback)
- `contribution` - When expert finishes (with content)
- `batch_started` / `batch_complete` - For multi-batch execution

---

## Table of Contents

1. [Current Architecture](#1-current-architecture)
2. [Target Architecture](#2-target-architecture)
3. [Implementation Phases](#3-implementation-phases)
4. [Detailed Design](#4-detailed-design)
5. [Intra-Node Streaming (NEW)](#5-intra-node-streaming-critical)
6. [Event Parity Checklist (NEW)](#6-event-parity-checklist)
7. [Error Handling & Partial Failures (NEW)](#7-error-handling--partial-failures)
8. [Migration Strategy](#8-migration-strategy)
9. [Testing Plan](#9-testing-plan)
10. [Rollback Plan](#10-rollback-plan)
11. [Risk Assessment](#11-risk-assessment)
12. [Performance Considerations (NEW)](#12-performance-considerations)

---

## 1. Current Architecture

### Problem

When `ENABLE_PARALLEL_SUBPROBLEMS=true`, the system executes `_deliberate_subproblem()` via `asyncio.gather()`. This function:

- Is **not a LangGraph node** (standalone async function)
- Bypasses `astream_events()` entirely
- Requires manual `EventBridge` for event emission
- Creates **3-5 minute UI blackouts** (known issue P0)

### Current Flow

```
parallel_subproblems_node (LangGraph node)
    │
    ├─ asyncio.gather(*[
    │      _deliberate_subproblem(sp1, event_bridge),
    │      _deliberate_subproblem(sp2, event_bridge),
    │      _deliberate_subproblem(sp3, event_bridge),
    │  ])
    │
    └─ Returns: sub_problem_results

Where _deliberate_subproblem() is 446 lines that:
1. Selects personas (manual event via EventBridge)
2. Runs rounds 1-6 (manual events via EventBridge)
3. Collects recommendations (manual event)
4. Generates synthesis (manual event)
```

### Why EventBridge Fails

The `EventBridge` pattern (Option A) has fundamental issues:

1. **Dual event systems**: Main graph uses `EventCollector` → `astream_events`, subproblems use `EventBridge` → direct Redis
2. **Event schema drift**: Two places to update when event format changes
3. **No checkpointing**: EventBridge doesn't trigger LangGraph checkpoints
4. **Testing complexity**: Need to mock both EventCollector AND EventBridge

---

## 2. Target Architecture

### Solution: Subgraph per Sub-Problem

Each sub-problem deliberation becomes a **compiled LangGraph subgraph** that:

- Uses the same nodes as the main graph (persona selection, rounds, voting, synthesis)
- Streams events through `astream_events(subgraphs=True)`
- Gets checkpointing automatically from parent graph
- Runs in parallel via `asyncio.gather()` with unique `thread_id`s

### Target Flow

```
parallel_subproblems_node (LangGraph node)
    │
    │  For each batch in execution_batches:
    │    │
    │    ├─ Create subproblem_graph for each sp in batch
    │    │
    │    ├─ asyncio.gather(*[
    │    │      subproblem_graph.ainvoke(state, config={"thread_id": f"{session_id}:sp:{i}"}),
    │    │      ...
    │    │  ])
    │    │
    │    └─ Collect results, pass to next batch
    │
    └─ Returns: sub_problem_results

Where subproblem_graph is a compiled LangGraph:

    select_personas_sp → initial_round_sp → facilitator_decide_sp
         │                                         │
         │                    ┌────────────────────┼────────────────────┐
         │                    ▼                    ▼                    ▼
         │              parallel_round_sp   moderator_sp          vote_sp
         │                    │                    │                    │
         │                    └────────────────────┼────────────────────┘
         │                                         │
         │                                         ▼
         │                              check_convergence_sp
         │                                    │       │
         │                                    │       └──→ vote_sp → synthesize_sp → END
         │                                    │
         │                                    └──→ facilitator_decide_sp (loop)
         │
         └─ Events stream via astream_events(subgraphs=True)
```

### Key Design Decision: Shared vs Separate State

**Option: Separate State with Transformation**

The subgraph uses `SubProblemGraphState` (subset of `DeliberationGraphState`), and `parallel_subproblems_node` transforms state in/out.

**Rationale**:
- Cleaner separation of concerns
- Subgraph state is self-contained
- Easier to test in isolation
- Matches LangGraph's recommended pattern for subgraphs with different schemas

---

## 3. Implementation Phases

### Phase 1: Define SubProblemGraphState (2 hours)

Create a focused state type for sub-problem deliberation.

**File**: `bo1/graph/subproblem/state.py`

```python
class SubProblemGraphState(TypedDict, total=False):
    """State for sub-problem deliberation subgraph."""

    # Identifiers
    session_id: str
    sub_problem_index: int

    # Problem context
    sub_problem: SubProblem
    parent_problem: Problem  # For context only

    # Participants
    personas: list[PersonaProfile]
    all_available_personas: list[PersonaProfile]  # For selection

    # Discussion
    contributions: list[ContributionMessage]
    round_summaries: list[str]
    round_number: int
    max_rounds: int

    # Control
    should_stop: bool
    stop_reason: str | None
    facilitator_decision: dict[str, Any] | None

    # Metrics
    metrics: DeliberationMetrics

    # Phase tracking
    current_phase: str  # "exploration", "challenge", "convergence"
    experts_per_round: list[list[str]]

    # Expert memory (from previous sub-problems)
    expert_memory: dict[str, str]

    # Outputs
    votes: list[dict[str, Any]]
    synthesis: str | None
    expert_summaries: dict[str, str]
```

### Phase 2: Create Subgraph Nodes (4 hours)

Adapt existing node logic for the subproblem context. Most nodes can be reused with minor modifications.

**File**: `bo1/graph/subproblem/nodes.py`

**Nodes to create/adapt**:

| Node | Source | Changes |
|------|--------|---------|
| `select_personas_sp_node` | `select_personas_node` | Uses `sub_problem` instead of `current_sub_problem`, adds `expert_memory` |
| `initial_round_sp_node` | `initial_round_node` | Minor state key changes |
| `facilitator_decide_sp_node` | `facilitator_decide_node` | Uses subgraph routing |
| `parallel_round_sp_node` | `parallel_round_node` | Identical, different state type |
| `check_convergence_sp_node` | `check_convergence_node` | Identical, different state type |
| `vote_sp_node` | `vote_node` | Minor state key changes |
| `synthesize_sp_node` | `synthesize_node` | Generates `expert_summaries` for memory |

**Key insight**: Most node logic is identical. The primary changes are:
1. State type annotation (`SubProblemGraphState` vs `DeliberationGraphState`)
2. Accessing `sub_problem` directly instead of `current_sub_problem`
3. Adding `sub_problem_index` to all event data

### Phase 3: Build Subgraph (2 hours)

**File**: `bo1/graph/subproblem/config.py`

```python
from langgraph.graph import END, StateGraph
from bo1.graph.subproblem.state import SubProblemGraphState
from bo1.graph.subproblem.nodes import (
    select_personas_sp_node,
    initial_round_sp_node,
    facilitator_decide_sp_node,
    parallel_round_sp_node,
    check_convergence_sp_node,
    vote_sp_node,
    synthesize_sp_node,
)
from bo1.graph.subproblem.routers import (
    route_facilitator_sp,
    route_convergence_sp,
)


def create_subproblem_graph() -> CompiledGraph:
    """Create compiled subgraph for single sub-problem deliberation.

    This graph is designed to be executed in parallel for independent
    sub-problems, with events streaming via astream_events(subgraphs=True).

    Returns:
        Compiled LangGraph ready for execution as a subgraph
    """
    workflow = StateGraph(SubProblemGraphState)

    # Add nodes
    workflow.add_node("select_personas", select_personas_sp_node)
    workflow.add_node("initial_round", initial_round_sp_node)
    workflow.add_node("facilitator_decide", facilitator_decide_sp_node)
    workflow.add_node("parallel_round", parallel_round_sp_node)
    workflow.add_node("check_convergence", check_convergence_sp_node)
    workflow.add_node("vote", vote_sp_node)
    workflow.add_node("synthesize", synthesize_sp_node)

    # Linear edges
    workflow.add_edge("select_personas", "initial_round")
    workflow.add_edge("initial_round", "facilitator_decide")
    workflow.add_edge("parallel_round", "check_convergence")

    # Conditional edges
    workflow.add_conditional_edges(
        "facilitator_decide",
        route_facilitator_sp,
        {
            "parallel_round": "parallel_round",
            "vote": "vote",
        },
    )

    workflow.add_conditional_edges(
        "check_convergence",
        route_convergence_sp,
        {
            "facilitator_decide": "facilitator_decide",
            "vote": "vote",
        },
    )

    workflow.add_edge("vote", "synthesize")
    workflow.add_edge("synthesize", END)

    # Entry point
    workflow.set_entry_point("select_personas")

    # Compile WITHOUT checkpointer (parent provides it)
    return workflow.compile()
```

### Phase 4: Update parallel_subproblems_node (4 hours)

Replace `asyncio.gather(*[_deliberate_subproblem(...)])` with subgraph execution.

**File**: `bo1/graph/nodes.py` (modify existing)

```python
async def parallel_subproblems_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute sub-problems in parallel using subgraphs.

    Each sub-problem runs as a compiled LangGraph subgraph, enabling:
    - Native event streaming via astream_events(subgraphs=True)
    - Per-subproblem checkpointing
    - Consistent event schema with main graph
    """
    from bo1.graph.subproblem.config import create_subproblem_graph
    from bo1.graph.subproblem.state import (
        SubProblemGraphState,
        create_subproblem_initial_state,
        result_from_subgraph_state,
    )

    problem = state["problem"]
    session_id = state["session_id"]
    execution_batches = state.get("execution_batches", [[i] for i in range(len(problem.sub_problems))])

    # Load all available personas
    from bo1.data import get_active_personas
    all_personas_dicts = get_active_personas()
    all_personas = [PersonaProfile.model_validate(p) for p in all_personas_dicts]

    all_results: list[SubProblemResult] = []

    # Create the subgraph once (stateless, reusable)
    subproblem_graph = create_subproblem_graph()

    for batch_idx, batch in enumerate(execution_batches):
        logger.info(f"Executing batch {batch_idx + 1}/{len(execution_batches)}: {batch}")

        # Build expert memory from previous results
        expert_memory = _build_expert_memory(all_results)

        # Create tasks for each sub-problem in this batch
        async def run_subproblem(sp_index: int) -> SubProblemResult:
            sub_problem = problem.sub_problems[sp_index]

            # Create initial state for subgraph
            sp_state = create_subproblem_initial_state(
                session_id=session_id,
                sub_problem=sub_problem,
                sub_problem_index=sp_index,
                parent_problem=problem,
                all_available_personas=all_personas,
                expert_memory=expert_memory,
            )

            # Execute subgraph with unique thread_id for checkpointing
            config = {
                "configurable": {
                    "thread_id": f"{session_id}:subproblem:{sp_index}",
                },
                "recursion_limit": 50,  # Subgraph has fewer nodes
            }

            final_state = await subproblem_graph.ainvoke(sp_state, config=config)

            return result_from_subgraph_state(final_state)

        # Execute batch in parallel
        batch_tasks = [run_subproblem(sp_idx) for sp_idx in batch]
        batch_results = await asyncio.gather(*batch_tasks)

        all_results.extend(batch_results)

    return {
        "sub_problem_results": all_results,
        "current_sub_problem": None,
        "phase": DeliberationPhase.SYNTHESIS,
    }
```

### Phase 5: Update EventCollector for Subgraphs (3 hours)

Modify `EventCollector.collect_and_publish()` to handle subgraph events.

**File**: `backend/api/event_collector.py` (modify existing)

**Key Changes**:

1. Use `astream_events(..., subgraphs=True)` - **CRITICAL RESEARCH NEEDED**

According to [LangGraph streaming documentation](https://docs.langchain.com/oss/python/langgraph/streaming), `subgraphs=True` works with `.stream()` and `.astream()`, but we need to verify it works with `.astream_events()`.

**If `astream_events` supports `subgraphs`**:

```python
async for event in graph.astream_events(
    initial_state,
    config=config,
    version="v2",
    # subgraphs=True,  # Need to verify this parameter exists
):
    # Events from subgraphs will have namespace info
    namespace = event.get("namespace", ())

    if namespace:
        # This is a subgraph event
        # Extract sub_problem_index from namespace or event data
        ...
```

**If `astream_events` doesn't support `subgraphs`** (fallback approach):

Use `get_stream_writer()` in subgraph nodes to emit custom events:

```python
from langgraph.config import get_stream_writer

async def select_personas_sp_node(state: SubProblemGraphState) -> dict:
    writer = get_stream_writer()

    # ... persona selection logic ...

    # Emit custom event
    writer({
        "event_type": "persona_selected",
        "sub_problem_index": state["sub_problem_index"],
        "data": {...},
    })

    return state_updates
```

Then in EventCollector:

```python
async for event in graph.astream(
    initial_state,
    config=config,
    stream_mode=["updates", "custom"],
    subgraphs=True,
):
    if event[0] == "custom":
        # Handle custom event from subgraph
        await self._handle_custom_event(session_id, event[1])
```

### Phase 6: Delete Legacy Code (1 hour)

Once subgraph approach is working:

1. Delete `_deliberate_subproblem()` from `bo1/graph/nodes.py` (~50 lines, calls engine.py)
2. Delete `bo1/graph/deliberation/engine.py` (~476 lines)
3. Delete `backend/api/event_bridge.py` (~93 lines)
4. Update `bo1/graph/deliberation/__init__.py` to remove `deliberate_subproblem` export
5. Remove `EventBridge` imports from `parallel_subproblems_node`

**Total code removed**: ~619 lines
**Total code added**: ~400 lines (subgraph module)
**Net reduction**: ~219 lines

---

## 4. Detailed Design

### 4.1 State Transformation

**Parent → Subgraph** (in `parallel_subproblems_node`):

```python
def create_subproblem_initial_state(
    session_id: str,
    sub_problem: SubProblem,
    sub_problem_index: int,
    parent_problem: Problem,
    all_available_personas: list[PersonaProfile],
    expert_memory: dict[str, str],
) -> SubProblemGraphState:
    """Transform parent state into subgraph initial state."""
    max_rounds = get_adaptive_max_rounds(sub_problem.complexity_score)

    return SubProblemGraphState(
        session_id=session_id,
        sub_problem_index=sub_problem_index,
        sub_problem=sub_problem,
        parent_problem=parent_problem,
        personas=[],  # Will be selected by first node
        all_available_personas=all_available_personas,
        contributions=[],
        round_summaries=[],
        round_number=0,
        max_rounds=max_rounds,
        should_stop=False,
        stop_reason=None,
        facilitator_decision=None,
        metrics=DeliberationMetrics(),
        current_phase="exploration",
        experts_per_round=[],
        expert_memory=expert_memory,
        votes=[],
        synthesis=None,
        expert_summaries={},
    )
```

**Subgraph → Result** (after subgraph completes):

```python
def result_from_subgraph_state(state: SubProblemGraphState) -> SubProblemResult:
    """Extract SubProblemResult from final subgraph state."""
    return SubProblemResult(
        sub_problem_id=state["sub_problem"].id,
        sub_problem_goal=state["sub_problem"].goal,
        synthesis=state["synthesis"] or "",
        votes=state["votes"],
        contribution_count=len(state["contributions"]),
        cost=state["metrics"].total_cost,
        duration_seconds=state["metrics"].duration_seconds,
        expert_panel=[p.code for p in state["personas"]],
        expert_summaries=state["expert_summaries"],
    )
```

### 4.2 Event Identification

Subgraph events need `sub_problem_index` for frontend tab filtering. Two approaches:

**Approach A: State-based** (preferred)

Every subgraph node includes `sub_problem_index` in returned state. EventCollector reads it from output:

```python
# In any subgraph node
return {
    "sub_problem_index": state["sub_problem_index"],  # Always include
    ...other_updates,
}
```

**Approach B: Namespace-based**

Parse `thread_id` from config: `f"{session_id}:subproblem:{index}"` → extract `index`.

### 4.3 Checkpointing Strategy

LangGraph automatically propagates checkpointer to subgraphs ([source](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)).

**Thread ID scheme**:

```
Parent:     {session_id}
Subgraph 0: {session_id}:subproblem:0
Subgraph 1: {session_id}:subproblem:1
...
```

This enables:
- Resuming parent graph from `parallel_subproblems_node`
- Resuming individual subgraphs from any round
- Querying subgraph checkpoints independently

### 4.4 Parallel Execution

Subgraphs execute in parallel via `asyncio.gather()`:

```python
batch_tasks = [
    subproblem_graph.ainvoke(state_i, config=config_i)
    for i, (state_i, config_i) in enumerate(batch_configs)
]
results = await asyncio.gather(*batch_tasks)
```

**Thread safety**: Each subgraph has unique `thread_id`, so checkpoints don't conflict.

---

## 5. Intra-Node Streaming (CRITICAL)

### The Real Problem

Even with subgraphs, **node-level events only fire when nodes complete**. The `parallel_round_node` uses `asyncio.gather()` which blocks until ALL 3-5 experts finish. This means:

- Expert 1 finishes in 8 seconds → no event
- Expert 2 finishes in 12 seconds → no event
- Expert 3 finishes in 15 seconds → no event
- Expert 4 finishes in 20 seconds → no event
- `asyncio.gather()` returns → ALL events fire at once (20 seconds of silence)

**This is the root cause of poor UX**, and subgraphs alone don't fix it.

### Solution: `get_stream_writer()` for Granular Events

LangGraph's `get_stream_writer()` enables emitting custom events from **inside** nodes:

```python
from langgraph.config import get_stream_writer

async def parallel_round_sp_node(state: SubProblemGraphState) -> dict:
    """Parallel round with real-time per-expert streaming."""
    writer = get_stream_writer()
    sub_problem_index = state["sub_problem_index"]
    round_number = state["round_number"]

    # Emit round start immediately
    writer({
        "event_type": "round_started",
        "sub_problem_index": sub_problem_index,
        "round_number": round_number,
        "phase": current_phase,
        "experts": [e.code for e in selected_experts],
    })

    # Generate contributions with per-expert streaming
    contributions = []

    async def generate_with_streaming(expert: PersonaProfile) -> ContributionMessage:
        # Emit start event IMMEDIATELY
        writer({
            "event_type": "contribution_started",
            "sub_problem_index": sub_problem_index,
            "round_number": round_number,
            "persona_code": expert.code,
            "persona_name": expert.display_name,
        })

        # Generate contribution (5-15 seconds)
        contribution = await _generate_single_contribution(expert, state, current_phase)

        # Emit completion event with content
        writer({
            "event_type": "contribution",
            "sub_problem_index": sub_problem_index,
            "round_number": round_number,
            "persona_code": expert.code,
            "persona_name": expert.display_name,
            "archetype": expert.archetype,
            "domain_expertise": expert.domain_expertise,
            "content": contribution.content,
        })

        return contribution

    # Execute in parallel - events stream as each expert completes
    tasks = [generate_with_streaming(expert) for expert in selected_experts]
    contributions = await asyncio.gather(*tasks)

    return {
        "contributions": all_contributions + list(contributions),
        "round_number": round_number + 1,
        ...
    }
```

### Streaming Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Streaming with get_stream_writer()                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  parallel_round_sp_node                                                 │
│    │                                                                    │
│    ├─ writer(round_started) ─────────────────────────→ SSE: round_started
│    │                                                                    │
│    ├─ asyncio.gather([                                                  │
│    │      generate_with_streaming(expert1),                             │
│    │      generate_with_streaming(expert2),                             │
│    │      generate_with_streaming(expert3),                             │
│    │  ])                                                                │
│    │                                                                    │
│    │    expert1 starts:                                                 │
│    │      writer(contribution_started) ──────────────→ SSE: contribution_started
│    │    expert2 starts:                                                 │
│    │      writer(contribution_started) ──────────────→ SSE: contribution_started
│    │    expert3 starts:                                                 │
│    │      writer(contribution_started) ──────────────→ SSE: contribution_started
│    │                                                                    │
│    │    expert1 finishes (8s):                                          │
│    │      writer(contribution) ──────────────────────→ SSE: contribution
│    │    expert3 finishes (12s):                                         │
│    │      writer(contribution) ──────────────────────→ SSE: contribution
│    │    expert2 finishes (15s):                                         │
│    │      writer(contribution) ──────────────────────→ SSE: contribution
│    │                                                                    │
│    └─ return state updates                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### EventCollector Changes

Update `collect_and_publish()` to use `stream_mode=["updates", "custom"]`:

```python
async def collect_and_publish(self, session_id, graph, initial_state, config):
    """Execute graph and publish events including custom stream events."""

    async for chunk in graph.astream(
        initial_state,
        config=config,
        stream_mode=["updates", "custom"],
        subgraphs=True,
    ):
        namespace, data = chunk

        if isinstance(data, dict) and "event_type" in data:
            # Custom event from get_stream_writer()
            event_type = data.pop("event_type")
            self.publisher.publish_event(session_id, event_type, data)

        elif isinstance(data, dict):
            # Regular state update - extract and publish node events
            await self._handle_state_update(session_id, namespace, data)
```

### Python Version Note

`get_stream_writer()` requires Python 3.11+ for proper context variable propagation. For Python < 3.11, add `writer` parameter to function signature and pass config:

```python
# Python < 3.11 workaround
async def parallel_round_sp_node(state: SubProblemGraphState, config: RunnableConfig) -> dict:
    writer = config.get("writer")  # Injected by LangGraph
    if writer:
        writer({...})
```

---

## 6. Event Parity Checklist

### Current EventBridge Events (engine.py)

All these events MUST be replicated in the subgraph approach:

| Event Type | Current Location | Subgraph Location | Emission Point |
|------------|------------------|-------------------|----------------|
| `persona_selected` | `engine.py:137` | `select_personas_sp_node` | Per persona, via `writer()` |
| `persona_selection_complete` | `engine.py:148` | `select_personas_sp_node` | After all personas selected |
| `round_started` | `engine.py:236` | `parallel_round_sp_node` | Start of round loop |
| `contribution_started` | **NEW** | `parallel_round_sp_node` | Before LLM call |
| `contribution` | `engine.py:272` | `parallel_round_sp_node` | After LLM call completes |
| `voting_started` | `engine.py:312` | `vote_sp_node` | Before collecting recommendations |
| `voting_complete` | `engine.py:352` | `vote_sp_node` | After all recommendations |
| `synthesis_started` | `engine.py:365` | `synthesize_sp_node` | Before synthesis LLM call |
| `synthesis_complete` | `engine.py:418` | `synthesize_sp_node` | After synthesis |
| `subproblem_complete` | `parallel_subproblems_node` | Same | After subgraph returns |

### New Events (v2 Additions)

| Event Type | Purpose | Emission Point |
|------------|---------|----------------|
| `contribution_started` | Show "Expert X is thinking..." | Before each LLM call in parallel round |
| `batch_started` | Show "Batch 1 of 2: Sub-problems A, B" | Start of each batch in `parallel_subproblems_node` |
| `batch_complete` | Show "Batch 1 complete" | After `asyncio.gather()` for batch |
| `convergence_checked` | Show convergence score | After `check_convergence_sp_node` |

### Verification Test

```python
@pytest.mark.asyncio
async def test_event_parity():
    """Verify all EventBridge events are emitted by subgraph."""
    REQUIRED_EVENTS = {
        "persona_selected",
        "persona_selection_complete",
        "round_started",
        "contribution_started",  # NEW
        "contribution",
        "voting_started",
        "voting_complete",
        "synthesis_started",
        "synthesis_complete",
    }

    events = []
    async for chunk in graph.astream(..., stream_mode=["updates", "custom"], subgraphs=True):
        if isinstance(chunk[1], dict) and "event_type" in chunk[1]:
            events.append(chunk[1]["event_type"])

    emitted_types = set(events)
    missing = REQUIRED_EVENTS - emitted_types
    assert not missing, f"Missing events: {missing}"
```

---

## 7. Error Handling & Partial Failures

### Scenario: One Subproblem Fails Mid-Execution

With `asyncio.gather(*tasks)`, if one task fails, the default behavior raises immediately and cancels other tasks. This is NOT what we want.

### Solution: `return_exceptions=True` + Result Processing

```python
async def parallel_subproblems_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute sub-problems with graceful partial failure handling."""
    writer = get_stream_writer()

    for batch_idx, batch in enumerate(execution_batches):
        # Emit batch start
        writer({
            "event_type": "batch_started",
            "batch_index": batch_idx,
            "total_batches": len(execution_batches),
            "sub_problem_indices": batch,
        })

        # Execute batch with exception handling
        batch_tasks = [run_subproblem(sp_idx) for sp_idx in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process results, handling failures
        for sp_idx, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Sub-problem {sp_idx} failed: {result}")

                # Emit failure event
                writer({
                    "event_type": "subproblem_failed",
                    "sub_problem_index": sp_idx,
                    "error": str(result),
                    "error_type": type(result).__name__,
                })

                # Create placeholder result for failed sub-problem
                failed_result = SubProblemResult(
                    sub_problem_id=problem.sub_problems[sp_idx].id,
                    sub_problem_goal=problem.sub_problems[sp_idx].goal,
                    synthesis=f"[FAILED: {result}]",
                    votes=[],
                    contribution_count=0,
                    cost=0.0,
                    duration_seconds=0.0,
                    expert_panel=[],
                    expert_summaries={},
                    failed=True,  # NEW field
                    error=str(result),
                )
                all_results.append(failed_result)
            else:
                all_results.append(result)

        # Emit batch complete
        writer({
            "event_type": "batch_complete",
            "batch_index": batch_idx,
            "succeeded": sum(1 for r in batch_results if not isinstance(r, Exception)),
            "failed": sum(1 for r in batch_results if isinstance(r, Exception)),
        })

    # Continue to meta-synthesis even with partial failures
    return {
        "sub_problem_results": all_results,
        "partial_failure": any(r.failed for r in all_results if hasattr(r, 'failed')),
    }
```

### SubProblemResult Model Update

```python
# bo1/models/state.py
class SubProblemResult(BaseModel):
    """Result from a sub-problem deliberation."""
    sub_problem_id: str
    sub_problem_goal: str
    synthesis: str
    votes: list[dict[str, Any]]
    contribution_count: int
    cost: float
    duration_seconds: float
    expert_panel: list[str]
    expert_summaries: dict[str, str]

    # NEW: Error tracking
    failed: bool = False
    error: str | None = None
```

### Retry Strategy for Transient Failures

```python
async def run_subproblem_with_retry(sp_index: int, max_retries: int = 2) -> SubProblemResult:
    """Run subproblem with retry for transient failures."""
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await run_subproblem(sp_index)
        except (APITimeoutError, APIConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                writer({
                    "event_type": "subproblem_retry",
                    "sub_problem_index": sp_index,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                })
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            # Non-retryable error
            raise

    raise last_error
```

---

## 8. Migration Strategy

### 8.1 Feature Flag Approach

Add `USE_SUBGRAPH_DELIBERATION` flag to enable gradual rollout:

```python
# bo1/feature_flags.py
USE_SUBGRAPH_DELIBERATION = os.getenv("USE_SUBGRAPH_DELIBERATION", "false").lower() == "true"
```

```python
# bo1/graph/nodes.py
async def parallel_subproblems_node(state):
    from bo1.feature_flags import USE_SUBGRAPH_DELIBERATION

    if USE_SUBGRAPH_DELIBERATION:
        return await _parallel_subproblems_subgraph(state)
    else:
        return await _parallel_subproblems_legacy(state)
```

### 8.2 Rollout Plan (Updated)

| Day | Action |
|-----|--------|
| 1 | Implement Phase 1-3 (state, nodes, graph) |
| 2 | Implement Phase 4 (update parallel_subproblems_node) |
| 3 | Implement Phase 5 (EventCollector), write tests |
| 4 | Integration testing, fix issues |
| 5 | Enable in staging (`USE_SUBGRAPH_DELIBERATION=true`) |
| 6 | Monitor staging, fix any issues |
| 7 | Enable in production |
| 8 | Delete legacy code (Phase 6) after 1 week stable |

---

## 9. Testing Plan

### 9.1 Unit Tests

**File**: `tests/graph/subproblem/test_state.py`

```python
def test_create_subproblem_initial_state():
    """State creation with all required fields."""

def test_result_from_subgraph_state():
    """Result extraction preserves all data."""

def test_expert_memory_building():
    """Memory correctly aggregates previous results."""
```

**File**: `tests/graph/subproblem/test_nodes.py`

```python
@pytest.mark.asyncio
async def test_select_personas_sp_node():
    """Persona selection works in subgraph context."""

@pytest.mark.asyncio
async def test_parallel_round_sp_node():
    """Multi-expert round produces contributions."""

@pytest.mark.asyncio
async def test_synthesize_sp_node_generates_expert_summaries():
    """Synthesis includes expert memory for next subproblem."""
```

### 9.2 Integration Tests

**File**: `tests/graph/subproblem/test_integration.py`

```python
@pytest.mark.asyncio
async def test_subgraph_executes_to_completion():
    """Full subgraph execution produces valid result."""
    graph = create_subproblem_graph()
    state = create_subproblem_initial_state(...)

    final = await graph.ainvoke(state, config={"thread_id": "test"})

    assert final["synthesis"] is not None
    assert len(final["contributions"]) > 0
    assert len(final["votes"]) > 0

@pytest.mark.asyncio
async def test_subgraph_events_stream():
    """Events stream from subgraph execution."""
    graph = create_subproblem_graph()
    events = []

    async for event in graph.astream_events(state, config=config, version="v2"):
        events.append(event)

    event_names = [e["name"] for e in events if e["event"] == "on_chain_end"]
    assert "select_personas" in event_names
    assert "synthesize" in event_names

@pytest.mark.asyncio
async def test_parallel_execution_with_subgraphs():
    """Multiple subgraphs execute in parallel."""
    results = await parallel_subproblems_node(state_with_3_subproblems)

    assert len(results["sub_problem_results"]) == 3
    # Verify all have unique synthesis
    syntheses = [r.synthesis for r in results["sub_problem_results"]]
    assert len(set(syntheses)) == 3
```

### 9.3 Event Streaming Tests

### 9.4 Parallelism Verification Test (NEW)

```python
@pytest.mark.asyncio
async def test_parallel_execution_is_truly_parallel():
    """Verify subproblems execute in parallel, not sequentially."""
    import time

    # Mock LLM to take 2 seconds per call
    mock_latency = 2.0

    start = time.time()
    results = await parallel_subproblems_node(state_with_3_independent_subproblems)
    elapsed = time.time() - start

    # Sequential would take ~6+ seconds (3 subproblems × 2 seconds each)
    # Parallel should take ~2-3 seconds
    assert elapsed < 4.0, f"Execution took {elapsed:.1f}s - not parallel!"
    assert len(results["sub_problem_results"]) == 3
```

### 9.5 Intra-Node Streaming Test (NEW)

```python
@pytest.mark.asyncio
async def test_contribution_started_events_fire_immediately():
    """Verify contribution_started fires before contribution completes."""
    events_with_timestamps = []

    async for chunk in graph.astream(..., stream_mode=["updates", "custom"], subgraphs=True):
        if isinstance(chunk[1], dict) and "event_type" in chunk[1]:
            events_with_timestamps.append((time.time(), chunk[1]["event_type"]))

    # Find contribution_started and contribution events
    started_events = [(t, e) for t, e in events_with_timestamps if e == "contribution_started"]
    complete_events = [(t, e) for t, e in events_with_timestamps if e == "contribution"]

    # Started events should come first
    assert len(started_events) > 0, "No contribution_started events"
    assert started_events[0][0] < complete_events[0][0], "Started event should precede completion"
```

**File**: `tests/api/test_subgraph_events.py`

```python
@pytest.mark.asyncio
async def test_event_collector_captures_subgraph_events():
    """EventCollector publishes events from subgraph nodes."""
    collector = EventCollector(mock_publisher)

    await collector.collect_and_publish(
        session_id="test",
        graph=graph_with_subgraphs,
        initial_state=state,
        config=config,
    )

    published_events = mock_publisher.published

    # Should have events from subgraph
    sp_events = [e for e in published_events if e["data"].get("sub_problem_index") == 0]
    assert any(e["type"] == "persona_selected" for e in sp_events)
    assert any(e["type"] == "contribution" for e in sp_events)
    assert any(e["type"] == "synthesis_complete" for e in sp_events)
```

---

## 10. Rollback Plan

### Immediate Rollback (< 5 minutes)

```bash
# Set feature flag to false
export USE_SUBGRAPH_DELIBERATION=false

# Restart API
docker-compose restart api
```

### Code Rollback (if feature flag insufficient)

```bash
git revert <commit-hash>
make deploy
```

### Data Considerations

- Checkpoints created with subgraph thread_ids (`{session_id}:subproblem:{i}`) will be orphaned
- These expire after 7 days (Redis TTL)
- No manual cleanup needed

---

## 11. Risk Assessment

### High Risk: `astream_events` Subgraph Support

**Risk**: `astream_events()` may not support `subgraphs=True` parameter.

**Mitigation**:
1. Test locally before implementation
2. Fallback to `get_stream_writer()` for custom events
3. Worst case: Use `astream(stream_mode=["updates", "custom"], subgraphs=True)`

**Research Required**: Test this in a minimal example before starting implementation.

### Medium Risk: Event Schema Changes

**Risk**: Subgraph events have different format than main graph events.

**Mitigation**:
1. Use same extractors for both paths
2. Add `sub_problem_index` consistently
3. Integration tests verify event format

### Low Risk: Performance Regression

**Risk**: Subgraph compilation adds overhead.

**Mitigation**:
1. Create subgraph once, reuse for all sub-problems
2. Subgraph is stateless (no checkpointer at compile time)
3. Benchmark before/after

### Low Risk: Checkpoint Bloat

**Risk**: More checkpoints with subgraph approach.

**Mitigation**:
1. Existing 7-day TTL handles cleanup
2. Subgraph checkpoints are smaller (subset of state)
3. Monitor Redis memory usage

---

## 12. File Structure (Updated)

```
bo1/graph/subproblem/
├── __init__.py           # Exports: create_subproblem_graph, SubProblemGraphState
├── state.py              # SubProblemGraphState TypedDict + helpers
├── nodes.py              # Subgraph node implementations
├── routers.py            # Conditional edge functions
└── config.py             # create_subproblem_graph()

tests/graph/subproblem/
├── __init__.py
├── test_state.py
├── test_nodes.py
├── test_routers.py
└── test_integration.py
```

---

## 13. Success Criteria (Updated)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **UI Blackout** | < 3 seconds between events (was 3-5 minutes) | Frontend event gap monitoring |
| **Event Granularity** | `contribution_started` fires within 100ms of LLM call start | Timestamp analysis |
| **Event Parity** | 100% of EventBridge events replicated | Automated parity test |
| **Event Consistency** | 100% of events have `sub_problem_index` | Schema validation |
| **Code Reduction** | Net ~200 lines removed | `wc -l` before/after |
| **Test Coverage** | 80%+ on new subgraph module | pytest-cov |
| **Parallel Speedup** | 3 subproblems complete in < 1.5× single time | Timing test |
| **Checkpointing** | Subgraphs resumable from any round | Manual test |
| **Partial Failure** | Failed subproblems don't crash batch | Error injection test |
| **Memory Usage** | < 20% increase during parallel execution | Resource monitoring |

---

## 14. Open Questions (Resolved)

1. **Does `astream_events` support `subgraphs=True`?**
   - **RESOLVED**: Use `astream(stream_mode=["updates", "custom"], subgraphs=True)` instead
   - `get_stream_writer()` is the PRIMARY approach for granular events
   - See Section 5 for implementation details

2. **How does `EventCollector` identify subgraph events?**
   - **RESOLVED**: Use `event_type` field in custom events from `get_stream_writer()`
   - All events include `sub_problem_index` automatically

3. **Should subgraph moderator_intervene be included?**
   - **RESOLVED**: Omit initially for simplicity
   - Current parallel execution doesn't use moderator
   - Can add later if convergence issues arise

4. **How to handle partial failures?** (NEW)
   - **RESOLVED**: Use `asyncio.gather(return_exceptions=True)`
   - Create placeholder results for failed subproblems
   - Continue to meta-synthesis with partial results
   - See Section 7 for implementation

5. **What about checkpoint bloat?** (NEW)
   - **RESOLVED**: Accept increased checkpoints (subgraph state is smaller)
   - Monitor Redis memory usage
   - Existing 7-day TTL handles cleanup

---

## 15. References

- [LangGraph Subgraphs Documentation](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- [LangGraph Streaming Documentation](https://docs.langchain.com/oss/python/langgraph/streaming)
- [Subgraph Events Discussion](https://github.com/langchain-ai/langgraph/discussions/2484)
- [Custom Streaming with get_stream_writer](https://stackoverflow.com/questions/79179756/how-to-custom-stream-events-in-langgraph)

---

## Appendix A: Minimal Test for astream_events + Subgraphs

Run this before starting implementation to verify `astream_events` works with subgraphs:

```python
# test_subgraph_streaming.py
import asyncio
from langgraph.graph import StateGraph, END
from typing import TypedDict


class ChildState(TypedDict):
    value: int


class ParentState(TypedDict):
    value: int
    child_result: int | None


def child_node(state: ChildState) -> dict:
    return {"value": state["value"] * 2}


def parent_node(state: ParentState) -> dict:
    return {"value": state["value"] + 1}


# Build child graph
child = StateGraph(ChildState)
child.add_node("double", child_node)
child.set_entry_point("double")
child.add_edge("double", END)
child_graph = child.compile()


# Build parent with child as node
async def call_child(state: ParentState) -> dict:
    result = await child_graph.ainvoke({"value": state["value"]})
    return {"child_result": result["value"]}


parent = StateGraph(ParentState)
parent.add_node("increment", parent_node)
parent.add_node("call_child", call_child)
parent.set_entry_point("increment")
parent.add_edge("increment", "call_child")
parent.add_edge("call_child", END)
parent_graph = parent.compile()


async def test():
    print("Testing astream_events with subgraph...")

    events = []
    async for event in parent_graph.astream_events(
        {"value": 5, "child_result": None},
        version="v2",
    ):
        events.append(event)
        if event["event"] == "on_chain_end":
            print(f"  {event['name']}: {event.get('data', {}).get('output', {})}")

    print(f"\nTotal events: {len(events)}")
    print("Child events captured:", any("double" in str(e) for e in events))


if __name__ == "__main__":
    asyncio.run(test())
```

Run with: `python test_subgraph_streaming.py`

If child events don't appear, try `get_stream_writer()` approach.

---

## Appendix B: get_stream_writer Test (Primary Approach)

Test the `get_stream_writer()` approach which is the PRIMARY method for intra-node events:

```python
# test_stream_writer.py
import asyncio
from langgraph.graph import StateGraph, END
from langgraph.config import get_stream_writer
from typing import TypedDict


class State(TypedDict):
    value: int
    results: list[int]


async def parallel_work_node(state: State) -> dict:
    """Simulate parallel work with per-item streaming."""
    writer = get_stream_writer()
    results = []

    async def do_work(item: int) -> int:
        # Emit start event
        writer({
            "event_type": "work_started",
            "item": item,
        })

        # Simulate work
        await asyncio.sleep(0.5 + item * 0.1)

        # Emit complete event
        writer({
            "event_type": "work_complete",
            "item": item,
            "result": item * 2,
        })

        return item * 2

    # Run in parallel
    tasks = [do_work(i) for i in range(3)]
    results = await asyncio.gather(*tasks)

    return {"results": list(results)}


# Build graph
graph = StateGraph(State)
graph.add_node("parallel_work", parallel_work_node)
graph.set_entry_point("parallel_work")
graph.add_edge("parallel_work", END)
compiled = graph.compile()


async def test():
    print("Testing get_stream_writer for intra-node events...")
    print()

    custom_events = []
    state_updates = []

    async for chunk in compiled.astream(
        {"value": 1, "results": []},
        stream_mode=["updates", "custom"],
    ):
        namespace, data = chunk

        if isinstance(data, dict) and "event_type" in data:
            custom_events.append(data)
            print(f"  CUSTOM: {data['event_type']} - item={data.get('item')}")
        else:
            state_updates.append(data)
            print(f"  UPDATE: {list(data.keys()) if isinstance(data, dict) else type(data)}")

    print()
    print(f"Custom events: {len(custom_events)}")
    print(f"State updates: {len(state_updates)}")

    # Verify order: started events should come before complete events
    started = [e for e in custom_events if e["event_type"] == "work_started"]
    completed = [e for e in custom_events if e["event_type"] == "work_complete"]

    print(f"Started events: {len(started)}")
    print(f"Complete events: {len(completed)}")

    assert len(started) == 3, "Should have 3 started events"
    assert len(completed) == 3, "Should have 3 complete events"
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test())
```

Run with: `python test_stream_writer.py`

Expected output:
```
Testing get_stream_writer for intra-node events...

  CUSTOM: work_started - item=0
  CUSTOM: work_started - item=1
  CUSTOM: work_started - item=2
  CUSTOM: work_complete - item=0
  CUSTOM: work_complete - item=1
  CUSTOM: work_complete - item=2
  UPDATE: ['results']

Custom events: 6
State updates: 1
Started events: 3
Complete events: 3

✓ All tests passed!
```

---

## 16. Performance Considerations

### 16.1 Checkpoint Frequency

With subgraphs, checkpoint count increases significantly:

**Current (no subgraphs)**:
- ~15 checkpoints per session (one per main graph node)

**With subgraphs (3 sub-problems, 4 rounds each)**:
- Main graph: ~5 checkpoints
- Per subproblem: ~8 nodes × 3 subproblems = 24 checkpoints
- **Total: ~29 checkpoints** (2× increase)

**Mitigation**:
- Subgraph state is smaller (no full problem context)
- Redis TTL handles cleanup
- Consider checkpoint interval config if problematic

### 16.2 Memory Usage During Parallel Execution

Running 3 subgraphs in parallel means 3× state objects in memory:

```
Estimated memory per subproblem:
- SubProblemGraphState: ~50KB
- Persona profiles (5): ~10KB
- Contributions (15-20): ~100KB
- Total: ~160KB per subproblem

Peak memory: 3 × 160KB = ~500KB additional
```

**This is negligible** compared to LLM response handling.

### 16.3 Rate Limiting Considerations

With parallel execution, API rate limits become relevant:

```
Parallel subproblems: 3
Experts per round: 4
Rounds per subproblem: 4
Total LLM calls per batch: 3 × 4 = 12 concurrent calls
```

**Mitigation**:
- Anthropic rate limits are per-minute, not per-second
- Add semaphore if needed: `asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)`

```python
# Optional rate limiting
LLM_SEMAPHORE = asyncio.Semaphore(10)  # Max 10 concurrent calls

async def generate_with_rate_limit(expert, state, phase):
    async with LLM_SEMAPHORE:
        return await _generate_single_contribution(expert, state, phase)
```

### 16.4 Event Publishing Overhead

`get_stream_writer()` events go through Redis PubSub. With granular events:

```
Events per subproblem:
- persona_selected: 4
- persona_selection_complete: 1
- round_started: 4
- contribution_started: 16 (4 experts × 4 rounds)
- contribution: 16
- voting_started: 1
- voting_complete: 1
- synthesis_started: 1
- synthesis_complete: 1
Total: ~45 events per subproblem

3 subproblems = ~135 events (up from ~20 with old approach)
```

**This is still fast** - Redis PubSub handles thousands of messages/second.

### 16.5 Subgraph Compilation Caching

Create the subgraph once at module level, not per invocation:

```python
# bo1/graph/subproblem/config.py

# Module-level singleton - compiled once
_SUBPROBLEM_GRAPH = None

def get_subproblem_graph() -> CompiledGraph:
    """Get or create the subproblem graph (singleton)."""
    global _SUBPROBLEM_GRAPH
    if _SUBPROBLEM_GRAPH is None:
        _SUBPROBLEM_GRAPH = _create_subproblem_graph()
    return _SUBPROBLEM_GRAPH
```

### 16.6 Cost Aggregation

Ensure metrics flow from subgraphs to parent:

```python
def result_from_subgraph_state(state: SubProblemGraphState) -> SubProblemResult:
    """Extract result with full cost tracking."""
    return SubProblemResult(
        ...
        cost=state["metrics"].total_cost,
        phase_costs=state["metrics"].phase_costs,  # Preserve breakdown
    )

# In meta_synthesize_node
def aggregate_costs(results: list[SubProblemResult]) -> dict:
    """Aggregate costs from all subproblems."""
    total = sum(r.cost for r in results)
    by_phase = defaultdict(float)
    for r in results:
        for phase, cost in r.phase_costs.items():
            by_phase[phase] += cost
    return {"total": total, "by_phase": dict(by_phase)}
```

---

## 17. Implementation Checklist

### Pre-Implementation

- [ ] Run `test_stream_writer.py` to verify `get_stream_writer()` works
- [ ] Run `test_subgraph_streaming.py` to verify subgraph streaming
- [ ] Review current EventBridge events in `engine.py` for parity

### Phase 1: State & Nodes (Day 1)

- [ ] Create `bo1/graph/subproblem/__init__.py`
- [ ] Create `SubProblemGraphState` in `state.py`
- [ ] Create `create_subproblem_initial_state()` helper
- [ ] Create `result_from_subgraph_state()` helper
- [ ] Adapt nodes to use `get_stream_writer()` for events

### Phase 2: Graph & Integration (Day 2)

- [ ] Create `create_subproblem_graph()` in `config.py`
- [ ] Create routers in `routers.py`
- [ ] Update `parallel_subproblems_node` with feature flag
- [ ] Add batch-level events (`batch_started`, `batch_complete`)

### Phase 3: Event Handling (Day 3)

- [ ] Update `EventCollector` to use `astream(stream_mode=["updates", "custom"])`
- [ ] Handle custom events from `get_stream_writer()`
- [ ] Add `contribution_started` events
- [ ] Verify all events have `sub_problem_index`

### Phase 4: Testing (Day 4)

- [ ] Unit tests for state helpers
- [ ] Unit tests for subgraph nodes
- [ ] Integration tests for full subgraph execution
- [ ] Event parity tests
- [ ] Parallelism verification test
- [ ] Partial failure test

### Phase 5: Deployment (Day 5)

- [ ] Enable `USE_SUBGRAPH_DELIBERATION=true` in staging
- [ ] Monitor event gaps in frontend
- [ ] Monitor Redis memory usage
- [ ] Verify checkpointing works
- [ ] Enable in production after 24h stable

### Post-Implementation

- [ ] Delete `bo1/graph/deliberation/engine.py`
- [ ] Delete `backend/api/event_bridge.py`
- [ ] Remove feature flag after 1 week stable
- [ ] Update CLAUDE.md to remove P0 issue

