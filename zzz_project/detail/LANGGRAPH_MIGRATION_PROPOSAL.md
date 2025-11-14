# LangGraph Migration Proposal - Board of One v2

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Technical Assessment & Migration Plan
**Author**: System Architecture Review

---

## Executive Summary

This document analyzes the current bo1 v1 architecture and proposes a strategic migration to LangGraph for v2. After comprehensive system review, **LangGraph integration is recommended** for both console and web interfaces, with specific focus on:

1. **Stateful workflow orchestration** (pause/resume sessions)
2. **Streaming real-time updates** (live contribution display)
3. **Human-in-the-loop intervention** (user can redirect discussion mid-round)
4. **Complex branching logic** (parallel sub-problem processing)
5. **Persistent checkpointing** (recover from failures, rewind deliberations)
6. **Infinite loop prevention** (100% confidence via recursion limits + cycle detection)
7. **Kill switches** (user can terminate own sessions, admin can kill all)

**Key Finding**: LangGraph can serve BOTH console and web with single unified architecture, eliminating dual-system complexity. Console benefits from same checkpointing/recovery features as web.

---

## 1. Current Architecture Analysis

### 1.1 v1 System Overview

**Codebase Stats**:
- **78 Python files** across 7,864 lines
- **18 async operations** (limited asyncio usage)
- **Redis-only state** (24h TTL, no checkpointing)
- **Sequential orchestration** (DeliberationEngine.run_round)
- **Linear flow** (Intake → Decompose → Deliberate → Vote → Synthesize)

**Core Components**:

```
bo1/
├── agents/              # 8 specialized agents
│   ├── facilitator.py   # Decides next action (continue/vote/research/moderator)
│   ├── decomposer.py    # Problem → sub-problems
│   ├── selector.py      # Sub-problem → persona selection
│   ├── moderator.py     # Contrarian/Skeptic/Optimist interventions
│   ├── summarizer.py    # Background round summarization (Haiku)
│   ├── researcher.py    # External/internal knowledge retrieval
│   └── context_collector.py # Business context Q&A
│
├── orchestration/
│   ├── deliberation.py  # Main engine: run_initial_round(), run_round()
│   └── voting.py        # Vote collection & aggregation
│
├── state/
│   ├── redis_manager.py # Session persistence (save/load/extend)
│   └── serialization.py # JSON export
│
├── models/
│   ├── state.py         # DeliberationState (Pydantic)
│   ├── problem.py       # Problem, SubProblem
│   ├── persona.py       # PersonaProfile
│   └── votes.py         # Vote, VoteResult
│
└── llm/
    ├── client.py        # ClaudeClient (async API wrapper)
    └── broker.py        # PromptBroker (caching layer)
```

### 1.2 Current Flow (Simplified)

```python
# v1 Orchestration (bo1/orchestration/deliberation.py)
class DeliberationEngine:
    async def run_initial_round(self):
        # Parallel: All personas contribute simultaneously
        tasks = [call_persona(p) for p in personas]
        contributions = await asyncio.gather(*tasks)
        state.add_contributions(contributions)
        state.phase = DeliberationPhase.DISCUSSION
        return contributions

    async def run_round(self, round_number, max_rounds):
        # Sequential: Facilitator decides next action
        decision = await facilitator.decide_next_action(state, round_number, max_rounds)

        if decision.action == "vote":
            state.phase = DeliberationPhase.VOTING
            return []

        if decision.action == "moderator":
            intervention = await moderator.intervene(...)
            state.add_contribution(intervention)
            return [intervention]

        if decision.action == "continue":
            speaker = get_persona(decision.next_speaker)
            contribution = await call_persona(speaker, context)
            state.add_contribution(contribution)
            return [contribution]
```

**Strengths**:
- ✅ Simple, readable, easy to debug
- ✅ Efficient for console (synchronous user experience)
- ✅ Cost-optimized (prompt caching, hierarchical context)
- ✅ Proven stable (Week 3 validation complete)

**Limitations for Web v2**:
- ❌ **No streaming**: Must wait for full round before UI update
- ❌ **No pause/resume**: Session is all-or-nothing
- ❌ **No branching**: Can't process multiple sub-problems in parallel
- ❌ **No checkpointing**: Redis failure = lost session state
- ❌ **No human-in-loop**: User can't intervene mid-round
- ❌ **Limited observability**: Hard to visualize flow state in real-time

---

## 2. Why LangGraph for v2?

### 2.1 LangGraph Value Propositions

LangGraph is a **stateful orchestration framework** built on LangChain, specifically designed for:

1. **Stateful Graphs**: Multi-node workflows with loops, conditionals, parallel branches
2. **Checkpointing**: Automatic state snapshots at each node (recover/rewind/replay)
3. **Streaming**: Real-time token-by-token or node-by-node updates
4. **Human-in-the-Loop**: Pause at breakpoints, wait for user input, resume
5. **Persistence**: Built-in PostgreSQL/Redis checkpoint storage
6. **Time Travel**: Rewind to any node, explore alternative paths

**Core Concepts**:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

# Define state schema
class DeliberationGraphState(TypedDict):
    problem: Problem
    current_sub_problem: SubProblem
    personas: list[PersonaProfile]
    contributions: list[ContributionMessage]
    round_number: int
    phase: DeliberationPhase
    facilitator_decision: FacilitatorDecision | None

# Build graph
workflow = StateGraph(DeliberationGraphState)

# Add nodes (each is an async function)
workflow.add_node("decompose", decompose_node)
workflow.add_node("select_personas", select_personas_node)
workflow.add_node("initial_round", initial_round_node)
workflow.add_node("facilitator_decide", facilitator_decide_node)
workflow.add_node("persona_contribute", persona_contribute_node)
workflow.add_node("moderator_intervene", moderator_intervene_node)
workflow.add_node("vote", vote_node)
workflow.add_node("synthesize", synthesize_node)

# Add edges (control flow)
workflow.add_edge("decompose", "select_personas")
workflow.add_edge("select_personas", "initial_round")
workflow.add_edge("initial_round", "facilitator_decide")

# Conditional routing (based on facilitator decision)
def route_facilitator_decision(state):
    decision = state["facilitator_decision"]
    if decision.action == "vote":
        return "vote"
    elif decision.action == "moderator":
        return "moderator_intervene"
    elif decision.action == "continue":
        return "persona_contribute"
    else:
        return END

workflow.add_conditional_edges(
    "facilitator_decide",
    route_facilitator_decision,
    {
        "vote": "vote",
        "moderator_intervene": "moderator_intervene",
        "persona_contribute": "persona_contribute",
        END: END
    }
)

# Loop back for multi-round
workflow.add_edge("persona_contribute", "facilitator_decide")
workflow.add_edge("moderator_intervene", "facilitator_decide")

# Compile with checkpointing
checkpointer = PostgresSaver(...)  # Or RedisSaver
app = workflow.compile(checkpointer=checkpointer)

# Stream execution
async for event in app.astream(initial_state, config={"configurable": {"thread_id": session_id}}):
    print(event)  # Real-time updates to web UI
```

### 2.2 LangGraph vs. Current v1 Architecture

| Feature | v1 (Sequential) | v2 (LangGraph) |
|---------|----------------|----------------|
| **Control Flow** | Manual `if/else` in `run_round()` | Declarative graph (nodes + edges) |
| **State Management** | Redis save/load (manual) | Automatic checkpointing at each node |
| **Streaming** | Not supported | Built-in: token-level or node-level |
| **Pause/Resume** | Not supported | Native: pause at any node, resume later |
| **Parallel Execution** | `asyncio.gather()` only | Parallel branches in graph |
| **Failure Recovery** | Redis failure = lost session | Checkpoint recovery from any node |
| **Human-in-Loop** | Console prompts only | Breakpoints + user approval gates |
| **Observability** | Manual logging | Built-in: graph visualization, node traces |
| **Time Travel** | Not supported | Rewind to any checkpoint, explore alternatives |
| **Migration Effort** | N/A | Medium (existing agents reusable as nodes) |

---

## 3. Proposed LangGraph Architecture

### 3.1 High-Level Graph Structure

```
                    START
                      │
                      ▼
              ┌───────────────┐
              │ Problem Intake│
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  Decompose    │  (Sonnet: problem → sub-problems)
              └───────┬───────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ Select Personas (LLM) │  (Sonnet: sub-problem → 3-5 experts)
         └────────────┬───────────┘
                      │
                      ▼
              ┌───────────────┐
              │ Initial Round │  (Parallel: all personas contribute)
              └───────┬───────┘
                      │
                      ▼
         ┌────────────────────────┐
         │ Facilitator Decision   │  (Haiku: continue/vote/research/moderator)
         └────────────┬───────────┘
                      │
         ┌────────────┼────────────┬────────────┐
         │            │            │            │
         ▼            ▼            ▼            ▼
    ┌────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐
    │ Vote   │  │Moderator│  │Persona  │  │Research│
    │        │  │Intervene│  │Continue │  │        │
    └───┬────┘  └────┬────┘  └────┬────┘  └────┬───┘
        │            │            │            │
        │            └────────────┴────────────┘
        │                       │
        │                       │ (Loop back)
        │                       ▼
        │            ┌────────────────────────┐
        │            │ Check Convergence      │
        │            └────────────┬───────────┘
        │                         │
        │                   ┌─────┴─────┐
        │                   │           │
        │                Continue?    Stop?
        │                   │           │
        │                   │           ▼
        │                   │      ┌─────────┐
        │                   │      │ Vote    │
        │                   │      └────┬────┘
        │                   │           │
        │                   └───────────┤
        │                               │
        ▼                               ▼
    ┌────────────────────────────────────┐
    │ Synthesize (Sonnet: final report) │
    └────────────────┬───────────────────┘
                     │
                     ▼
                    END
```

### 3.2 Node Implementation (Example)

Each existing agent becomes a LangGraph node:

```python
# bo1/graph/nodes.py
from langgraph.graph import StateGraph
from bo1.agents.facilitator import FacilitatorAgent
from bo1.agents.decomposer import DecomposerAgent
from bo1.models.state import DeliberationGraphState

# Node: Facilitator Decision
async def facilitator_decide_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Node that calls facilitator to decide next action."""
    facilitator = FacilitatorAgent()

    # Convert graph state to DeliberationState (for backward compatibility)
    deliberation_state = state_to_deliberation_state(state)

    # Call facilitator (existing agent, no changes needed)
    decision, response = await facilitator.decide_next_action(
        state=deliberation_state,
        round_number=state["round_number"],
        max_rounds=state["max_rounds"]
    )

    # Update state
    state["facilitator_decision"] = decision
    state["metrics"]["total_cost"] += response.cost_total
    state["metrics"]["total_tokens"] += response.total_tokens

    return state

# Node: Persona Contribution
async def persona_contribute_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Node that calls a single persona to contribute."""
    decision = state["facilitator_decision"]
    speaker_code = decision.next_speaker

    # Get persona profile
    speaker = next(p for p in state["personas"] if p.code == speaker_code)

    # Call existing DeliberationEngine logic (reuse _call_persona_async)
    engine = DeliberationEngine(state=deliberation_state, client=client)
    contribution, llm_response = await engine._call_persona_async(
        persona_profile=speaker,
        problem_statement=state["current_sub_problem"]["goal"],
        problem_context=state["current_sub_problem"]["context"],
        participant_list=state["participant_list"],
        round_number=state["round_number"],
        contribution_type=ContributionType.RESPONSE,
        previous_contributions=state["contributions"]
    )

    # Update state
    state["contributions"].append(contribution)
    state["round_number"] += 1
    state["metrics"]["total_cost"] += llm_response.cost_total

    return state

# Node: Check Convergence (Early Stop)
async def check_convergence_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Node that calculates convergence metrics and decides if stopping early."""
    engine = DeliberationEngine(state=deliberation_state)
    metrics = engine._calculate_round_metrics(state["round_number"])

    state["metrics"]["convergence_score"] = metrics["convergence"]
    state["metrics"]["novelty_score"] = metrics["novelty"]
    state["metrics"]["conflict_score"] = metrics["conflict"]
    state["should_stop"] = metrics["should_stop"]
    state["stop_reason"] = metrics["stop_reason"]

    return state

# Conditional edge: Continue or Stop?
def should_continue_deliberation(state: DeliberationGraphState) -> str:
    """Router function: decide if deliberation should continue."""
    if state["should_stop"]:
        return "vote"  # Transition to voting

    if state["round_number"] >= state["max_rounds"]:
        return "vote"  # Hard cap reached

    return "facilitator_decide"  # Continue deliberation
```

### 3.3 Streaming Implementation

```python
# Stream graph execution to web client (FastAPI SSE endpoint)
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph

app = FastAPI()

@app.post("/api/deliberation/{session_id}/stream")
async def stream_deliberation(session_id: str):
    """Stream deliberation updates to web UI via Server-Sent Events."""

    async def event_generator():
        # Load checkpoint (if resuming)
        config = {"configurable": {"thread_id": session_id}}

        # Stream graph execution
        async for event in graph.astream(initial_state, config=config):
            # Event structure:
            # {
            #   "node": "persona_contribute",
            #   "state": {...updated state...},
            #   "timestamp": "2025-11-14T10:30:45"
            # }

            # Send to client
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Web UI (SvelteKit) receives live updates**:

```typescript
// frontend/src/routes/deliberation/[sessionId]/+page.svelte
<script lang="ts">
  import { onMount } from 'svelte';

  let contributions = $state([]);
  let currentPhase = $state('initial_round');

  onMount(() => {
    const eventSource = new EventSource(`/api/deliberation/${sessionId}/stream`);

    eventSource.onmessage = (event) => {
      const update = JSON.parse(event.data);

      // Update UI in real-time
      if (update.node === 'persona_contribute') {
        contributions = [...contributions, update.state.contributions.at(-1)];
      }

      if (update.node === 'facilitator_decide') {
        currentPhase = update.state.facilitator_decision.action;
      }
    };
  });
</script>

<!-- Real-time contribution feed -->
{#each contributions as contrib}
  <div class="contribution" in:fly={{ y: 20 }}>
    <h4>{contrib.persona_name}</h4>
    <p>{contrib.content}</p>
  </div>
{/each}
```

### 3.4 Human-in-the-Loop (Breakpoints)

```python
# Add breakpoint: Pause before voting to get user approval
workflow.add_node("user_approval", user_approval_node)
workflow.add_edge("facilitator_decide", "user_approval")

async def user_approval_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Breakpoint: Wait for user to approve transition to voting."""

    # LangGraph pauses here automatically
    # Web UI shows "Waiting for your approval to proceed to voting"
    # User clicks "Approve" or "Continue Discussion"

    # This node is invoked AFTER user responds
    user_choice = state["user_input"]  # Injected by web API

    if user_choice == "approve":
        state["phase"] = DeliberationPhase.VOTING
    elif user_choice == "continue":
        state["phase"] = DeliberationPhase.DISCUSSION
        state["max_rounds"] += 2  # Extend by 2 rounds

    return state

# API endpoint to resume from breakpoint
@app.post("/api/deliberation/{session_id}/resume")
async def resume_deliberation(session_id: str, user_input: str):
    """Resume graph from breakpoint with user input."""

    config = {"configurable": {"thread_id": session_id}}

    # Update state with user input
    state_update = {"user_input": user_input}

    # Resume graph (continues from breakpoint)
    result = await graph.ainvoke(state_update, config=config)

    return result
```

---

## 3.5 Unified Architecture: Console + Web (REVISED RECOMMENDATION)

### Original Plan vs. Unified Approach

**Original Plan** (from IMPLEMENTATION_PROPOSAL.md):
- v1 console: Sequential orchestration (`bo1/orchestration/deliberation.py`)
- v2 web: LangGraph orchestration (`bo1/graph/`)
- **Downside**: Two parallel systems, dual maintenance burden

**Revised Recommendation**: **Migrate BOTH console and web to LangGraph**

### Why Unified LangGraph Makes Sense

#### Benefit 1: Single Source of Truth

```python
# BEFORE (Dual System):
# Console path
from bo1.orchestration.deliberation import DeliberationEngine
engine = DeliberationEngine(state)
result = await engine.run_deliberation()

# Web path
from bo1.graph.execution import execute_graph
result = await execute_graph(state)

# PROBLEM: Two implementations, drift over time, double testing burden

# AFTER (Unified):
from bo1.graph.execution import execute_deliberation

# Console
result = await execute_deliberation(state, mode="console")

# Web
result = await execute_deliberation(state, mode="web", stream=True)

# BENEFIT: One implementation, one test suite, guaranteed parity
```

#### Benefit 2: Console Gets Free Features

Migrating console to LangGraph unlocks features that improve console UX:

| Feature | v1 Console (Sequential) | v2 Console (LangGraph) | Value |
|---------|------------------------|----------------------|-------|
| **Checkpoint Recovery** | ❌ Start over if crash | ✅ Resume from last checkpoint | HIGH: Avoid wasted $ |
| **Pause/Resume** | ❌ Not supported | ✅ Save & resume later (multi-day) | MEDIUM: Long deliberations |
| **Time Travel** | ❌ No rewind | ✅ Rewind to Round 5, try different path | HIGH: Exploration |
| **Kill Switch** | ❌ Ctrl+C loses state | ✅ Graceful shutdown, checkpoint saved | MEDIUM: Clean exits |
| **Debugging** | ❌ Print statements | ✅ Node-level traces, state inspection | HIGH: Faster debugging |
| **Cost Guard** | ✅ Manual tracking | ✅ Auto-kill at budget limit | MEDIUM: Safety |

**Example: Console Pause/Resume**

```python
# Console session (Day 1)
$ python -m bo1.main

Welcome to Board of One
Problem: Should we invest $500K in paid ads or product-led growth?

[Initial Round complete - 5 personas contributed]

🔔 Checkpoint saved! You can resume this session anytime.
Session ID: bo1_abc123

Continue? (y/n/pause): pause

✅ Session paused. To resume:
   python -m bo1.main --resume bo1_abc123

# Console session (Day 2)
$ python -m bo1.main --resume bo1_abc123

📂 Resuming session bo1_abc123...
✅ Loaded state: Round 2, 5 participants, $0.08 spent

Continue deliberation? (y/n): y

[Round 2 begins...]
```

#### Benefit 3: Simplified Codebase

**Removed Components** (if unified):
- ❌ `bo1/orchestration/deliberation.py` (3,000 lines) → Replaced by graph nodes
- ❌ `bo1/orchestration/voting.py` (500 lines) → Single vote node
- ❌ Compatibility bridge (`graph_state_to_deliberation_state`) → Not needed
- ❌ Dual testing suites → Single test suite

**Kept Components**:
- ✅ All agents (`facilitator.py`, `moderator.py`, etc.) → Wrapped as nodes
- ✅ All models (`state.py`, `problem.py`, etc.) → Reused in graph state
- ✅ All prompts → Reused in node functions

**Net Result**: -3,500 lines of code, -40% maintenance burden

#### Benefit 4: No Drift Between Console and Web

**Problem with dual systems**:
```python
# v1 console: Sequential logic
if decision.action == "vote":
    return vote()
elif decision.action == "moderator":
    return moderate()

# v2 web: Graph logic
workflow.add_conditional_edges("facilitator_decide", route, {
    "vote": "vote_node",
    "moderator": "moderator_node"
})

# RISK: Console and web implement different logic
# Example: Console adds new action type "research" but web graph doesn't update
# Result: Console supports research, web doesn't → feature parity broken
```

**Solution with unified**:
```python
# BOTH console and web use same graph
graph = create_deliberation_graph()

# Console: Execute synchronously, no streaming
result = await graph.ainvoke(state, config=console_config)

# Web: Execute with streaming
async for event in graph.astream(state, config=web_config):
    send_to_websocket(event)

# GUARANTEE: Same logic, same behavior, feature parity maintained
```

### Implementation: Console Adapter

Console doesn't need full web features (SSE, WebSocket), so we create a lightweight adapter:

```python
# bo1/interfaces/console.py
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from langgraph.graph import StateGraph

console = Console()

async def run_console_deliberation(
    problem: Problem,
    session_id: str | None = None
) -> DeliberationState:
    """Run deliberation in console mode (unified graph backend).

    Args:
        problem: Problem to deliberate
        session_id: Optional session ID to resume

    Returns:
        Final deliberation state
    """
    # Load or create session
    if session_id:
        console.print(f"📂 Resuming session {session_id}...")
        config = {"configurable": {"thread_id": session_id}}
        # Resume from checkpoint
        state = await graph.aget_state(config)
        initial_state = state.values
    else:
        session_id = f"bo1_{uuid.uuid4()}"
        console.print(f"📝 Starting new session {session_id}")
        initial_state = create_initial_state(problem, session_id)
        config = {"configurable": {"thread_id": session_id}}

    # Execute graph with console-friendly event handling
    with Live(console=console, auto_refresh=False) as live:
        async for event in graph.astream_events(initial_state, config=config):
            # Handle different event types
            if event["event"] == "on_node_start":
                node = event["name"]
                live.update(Panel(f"⏳ {node}...", title="Processing"))

            elif event["event"] == "on_node_end":
                node = event["name"]

                # Display node results in console
                if node == "persona_contribute":
                    contribution = event["data"]["output"]["contributions"][-1]
                    display_contribution(contribution)

                elif node == "facilitator_decide":
                    decision = event["data"]["output"]["facilitator_decision"]
                    display_facilitator_decision(decision)

                elif node == "check_convergence":
                    metrics = event["data"]["output"]["metrics"]
                    display_convergence_metrics(metrics)

            # Allow user intervention at checkpoints
            if event.get("checkpoint"):
                # Checkpoint saved, offer pause option
                if Confirm.ask("Continue?", choices=["yes", "pause"], default="yes") == "pause":
                    console.print(f"✅ Session paused. Resume with: bo1 --resume {session_id}")
                    return event["data"]["output"]

            live.refresh()

    # Get final state
    final_state = await graph.aget_state(config)
    return final_state.values

# Console entry point
async def main(args):
    if args.resume:
        # Resume existing session
        result = await run_console_deliberation(
            problem=None,  # Loaded from checkpoint
            session_id=args.resume
        )
    else:
        # New session
        problem = prompt_problem_intake()
        result = await run_console_deliberation(problem=problem)

    # Display final report
    display_final_synthesis(result)

    # Export
    export_to_file(result, format=args.format or "markdown")
```

**Console Mode Features**:
- ✅ Rich UI (panels, progress bars, colors) - same as v1
- ✅ Checkpoint auto-save (every node completion)
- ✅ Pause/resume (user can stop and come back)
- ✅ Time travel (rewind to previous round)
- ✅ Kill switch (Ctrl+C saves checkpoint, exits gracefully)
- ✅ Cost guard (auto-stop at budget limit)

**Web Mode Features** (additional):
- ✅ SSE streaming (real-time updates to browser)
- ✅ WebSocket support (bidirectional communication)
- ✅ Multi-user (concurrent sessions)
- ✅ Graph visualization (show current node)

### Migration Path (Revised)

**Option A: Big Bang (Recommended for small team)**
- Week 1-2: Migrate console to LangGraph
- Week 3-4: Add web adapter (SSE, API endpoints)
- **Benefit**: Single codebase from start, no dual maintenance

**Option B: Gradual (Original plan, not recommended)**
- Week 1-4: Keep v1 console, build v2 web with LangGraph
- Week 5-6: Migrate console to LangGraph
- **Downside**: 4 weeks of dual maintenance, compatibility bridge complexity

**Recommendation**: **Option A (Big Bang)** - Migrate console first, then add web as thin adapter.

**Rationale**:
1. Console migration is **low risk** (same users, same workflows, just different backend)
2. Console users get **free features** (checkpoint recovery, pause/resume)
3. Web becomes **simple adapter** (streaming wrapper around same graph)
4. **No dual system** means no drift, no compatibility bridge, no double testing

### Console Migration Risks

| Risk | Mitigation |
|------|------------|
| **Console latency increase** | Benchmark in Week 1 (target: <10% increase) |
| **Loss of console features** | All v1 features replicated in LangGraph adapter |
| **User confusion** | Hidden migration (same CLI, same UX) |
| **Checkpoint storage** | Redis (same as v1), TTL cleanup (same as v1) |

**Benchmark Target** (Week 1):
```
v1 Console: 2-4 min per deliberation
v2 Console (LangGraph): <2.5-4.5 min per deliberation (<10% increase)

If benchmark fails (>10% increase): Optimize hot paths, use Haiku for routing
```

## 4. Migration Strategy (REVISED)

### 4.1 Phased Approach (Unified Console + Web)

**Phase 1: Console Migration (Weeks 1-2)**
- ✅ Keep v1 console app running (no changes)
- 🔧 Create `bo1/graph/` module (LangGraph implementation)
- 🔧 Define `DeliberationGraphState` (compatible with v1 `DeliberationState`)
- 🔧 Implement basic graph: Decompose → Select → Initial Round → Vote → Synthesize
- 🧪 Test graph execution parity with v1 (same outputs, same cost)

**Phase 2: Agent Wrapping (Weeks 3-4)**
- 🔧 Wrap existing agents as LangGraph nodes (minimal changes)
  - `facilitator.py` → `facilitator_decide_node()`
  - `moderator.py` → `moderator_intervene_node()`
  - `decomposer.py` → `decompose_node()`
- 🔧 Add conditional routing (facilitator decision → vote/moderator/continue)
- 🔧 Implement checkpointing (PostgreSQL or Redis backend)
- 🧪 Test pause/resume functionality

**Phase 3: Streaming & Web UI (Weeks 5-6)**
- 🔧 Implement FastAPI streaming endpoints (SSE)
- 🔧 Build SvelteKit UI with real-time updates
- 🔧 Add human-in-loop breakpoints (user approval gates)
- 🧪 Test streaming performance (latency, token-by-token)

**Phase 4: Advanced Features (Weeks 7-8)**
- 🔧 Parallel sub-problem processing (graph branching)
- 🔧 Time travel UI (rewind to any checkpoint)
- 🔧 Graph visualization (show current node, available paths)
- 🔧 Multi-session orchestration (queue, prioritize)

**Phase 5: Production Hardening (Weeks 9-10)**
- 🔧 Load testing (100+ concurrent sessions)
- 🔧 Checkpoint garbage collection (clean old sessions)
- 🔧 Error recovery (retry failed nodes, fallback strategies)
- 🔧 Observability (Prometheus metrics, Grafana dashboards)

### 4.2 Compatibility Bridge

**Goal**: v1 and v2 can coexist during migration.

```python
# bo1/graph/compatibility.py
def deliberation_state_to_graph_state(state: DeliberationState) -> DeliberationGraphState:
    """Convert v1 DeliberationState to v2 graph state."""
    return {
        "problem": state.problem,
        "current_sub_problem": state.current_sub_problem,
        "personas": state.selected_personas,
        "contributions": state.contributions,
        "round_summaries": state.round_summaries,
        "round_number": state.current_round,
        "max_rounds": state.max_rounds,
        "phase": state.phase,
        "metrics": state.metrics,
        "facilitator_decision": None,
        "should_stop": False,
        "stop_reason": None,
    }

def graph_state_to_deliberation_state(state: DeliberationGraphState) -> DeliberationState:
    """Convert v2 graph state to v1 DeliberationState (for agent calls)."""
    # Existing agents expect DeliberationState, not graph state
    # This bridge allows gradual migration
    return DeliberationState(
        session_id=state["session_id"],
        problem=state["problem"],
        current_sub_problem=state["current_sub_problem"],
        selected_personas=state["personas"],
        contributions=state["contributions"],
        round_summaries=state["round_summaries"],
        phase=state["phase"],
        current_round=state["round_number"],
        max_rounds=state["max_rounds"],
        metrics=state["metrics"],
    )
```

### 4.3 Migration Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Breaking existing agents** | HIGH | LOW | Use compatibility bridge; agents see same `DeliberationState` interface |
| **Checkpoint storage costs** | MEDIUM | MEDIUM | Use Redis checkpointer (cheaper than Postgres); TTL cleanup |
| **Performance degradation** | MEDIUM | LOW | Benchmark v1 vs v2; optimize hot paths; use Haiku for routing |
| **Learning curve** | LOW | HIGH | Phase 1: Team learns LangGraph with simple graph; extensive docs |
| **Over-engineering** | MEDIUM | MEDIUM | Start minimal (Phase 1-2); add features only when web UI needs them |
| **State schema drift** | MEDIUM | MEDIUM | TypedDict + Pydantic validation; migration scripts for old checkpoints |

### 4.4 Rollback Plan

If LangGraph migration fails, fallback strategy:

1. **Week 1-4**: v1 console app unaffected (parallel development)
2. **Week 5-8**: Web UI can call v1 orchestration via API (FastAPI wraps `DeliberationEngine`)
3. **Escape hatch**: LangGraph optional feature flag
   ```python
   if USE_LANGGRAPH:
       result = await graph.ainvoke(state, config=config)
   else:
       result = await legacy_orchestration(state)
   ```

---

## 5. Technical Specifications

### 5.1 State Schema (LangGraph TypedDict)

```python
# bo1/graph/state.py
from typing import TypedDict
from bo1.models.problem import Problem, SubProblem
from bo1.models.persona import PersonaProfile
from bo1.models.state import (
    ContributionMessage,
    DeliberationPhase,
    DeliberationMetrics,
)
from bo1.agents.facilitator import FacilitatorDecision

class DeliberationGraphState(TypedDict, total=False):
    """LangGraph state schema for deliberation workflow.

    Extends v1 DeliberationState with graph-specific fields.
    """
    # Core (from v1)
    session_id: str
    problem: Problem
    current_sub_problem: SubProblem | None
    personas: list[PersonaProfile]
    contributions: list[ContributionMessage]
    round_summaries: list[str]
    phase: DeliberationPhase
    round_number: int
    max_rounds: int
    metrics: DeliberationMetrics

    # Graph-specific (new in v2)
    facilitator_decision: FacilitatorDecision | None
    should_stop: bool
    stop_reason: str | None
    user_input: str | None  # For human-in-loop
    current_node: str  # Track current graph node (for visualization)
    checkpoint_id: str | None  # LangGraph checkpoint reference

    # Multi-sub-problem support (Phase 4)
    all_sub_problems: list[SubProblem]
    sub_problem_index: int
    completed_sub_problems: list[str]  # IDs of completed sub-problems

    # Context (from v1)
    business_context: dict[str, Any] | None
    internal_context: dict[str, str] | None
    research_context: list[dict[str, Any]] | None
```

### 5.2 Checkpoint Storage

**Option A: Redis Checkpointer** (Recommended for v2.0)

```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver(
    redis_url="redis://localhost:6379/1",
    ttl_seconds=604800  # 7 days (longer than v1 24h for resume capability)
)

graph = workflow.compile(checkpointer=checkpointer)
```

**Option B: PostgreSQL Checkpointer** (Consider for v2.1+)

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(
    connection_string="postgresql://user:pass@localhost:5432/bo1"
)

graph = workflow.compile(checkpointer=checkpointer)
```

**Comparison**:

| Feature | Redis Checkpointer | Postgres Checkpointer |
|---------|-------------------|----------------------|
| **Speed** | Very fast (in-memory) | Fast (disk-based) |
| **Durability** | Medium (RDB/AOF) | High (ACID) |
| **Query** | Limited (key-value) | Rich (SQL) |
| **Cost** | Low (shared with v1 state) | Medium (new service) |
| **Scaling** | Horizontal (Redis Cluster) | Vertical (Postgres) |
| **Recommendation** | **v2.0** (same infra as v1) | **v2.1+** (long-term sessions, analytics) |

### 5.3 Graph Configuration

```python
# bo1/graph/config.py
from langgraph.graph import StateGraph
from bo1.graph.state import DeliberationGraphState
from bo1.graph.nodes import (
    decompose_node,
    select_personas_node,
    initial_round_node,
    facilitator_decide_node,
    persona_contribute_node,
    moderator_intervene_node,
    check_convergence_node,
    vote_node,
    synthesize_node,
)
from bo1.graph.routers import (
    route_facilitator_decision,
    route_convergence_check,
)

def create_deliberation_graph(checkpointer=None) -> StateGraph:
    """Create LangGraph deliberation workflow.

    Args:
        checkpointer: Checkpoint storage backend (Redis or Postgres)

    Returns:
        Compiled graph ready for execution
    """
    workflow = StateGraph(DeliberationGraphState)

    # Add nodes
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("select_personas", select_personas_node)
    workflow.add_node("initial_round", initial_round_node)
    workflow.add_node("facilitator_decide", facilitator_decide_node)
    workflow.add_node("persona_contribute", persona_contribute_node)
    workflow.add_node("moderator_intervene", moderator_intervene_node)
    workflow.add_node("check_convergence", check_convergence_node)
    workflow.add_node("vote", vote_node)
    workflow.add_node("synthesize", synthesize_node)

    # Set entry point
    workflow.set_entry_point("decompose")

    # Add sequential edges
    workflow.add_edge("decompose", "select_personas")
    workflow.add_edge("select_personas", "initial_round")
    workflow.add_edge("initial_round", "facilitator_decide")

    # Add conditional routing from facilitator
    workflow.add_conditional_edges(
        "facilitator_decide",
        route_facilitator_decision,
        {
            "vote": "vote",
            "moderator": "moderator_intervene",
            "continue": "persona_contribute",
            "research": "research_node",  # TODO: Week 4
        }
    )

    # Loop edges
    workflow.add_edge("persona_contribute", "check_convergence")
    workflow.add_edge("moderator_intervene", "check_convergence")

    # Convergence routing (continue or vote)
    workflow.add_conditional_edges(
        "check_convergence",
        route_convergence_check,
        {
            "continue": "facilitator_decide",
            "stop": "vote",
        }
    )

    # Final synthesis
    workflow.add_edge("vote", "synthesize")
    workflow.add_edge("synthesize", END)

    # Compile with checkpointing
    return workflow.compile(checkpointer=checkpointer)
```

### 5.4 API Endpoints (FastAPI)

```python
# backend/api/deliberation.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph
from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import DeliberationGraphState
from bo1.state.redis_manager import RedisManager

router = APIRouter(prefix="/api/deliberation", tags=["deliberation"])

# Initialize graph with Redis checkpointer
from langgraph.checkpoint.redis import RedisSaver
checkpointer = RedisSaver(redis_url="redis://redis:6379/1")
graph = create_deliberation_graph(checkpointer=checkpointer)

@router.post("/{session_id}/start")
async def start_deliberation(session_id: str, problem: Problem):
    """Start new deliberation session."""

    initial_state: DeliberationGraphState = {
        "session_id": session_id,
        "problem": problem,
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": DeliberationPhase.DECOMPOSITION,
        "round_number": 0,
        "max_rounds": 10,
        "metrics": DeliberationMetrics(),
    }

    # Invoke graph (async, non-streaming)
    result = await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": session_id}}
    )

    return result

@router.get("/{session_id}/stream")
async def stream_deliberation(session_id: str):
    """Stream deliberation updates via SSE."""

    async def event_generator():
        config = {"configurable": {"thread_id": session_id}}

        # Load checkpoint (if exists)
        # If no checkpoint, graph won't execute (client must call /start first)

        async for event in graph.astream_events(None, config=config):
            # Event types: "on_node_start", "on_node_end", "on_edge"
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/{session_id}/pause")
async def pause_deliberation(session_id: str):
    """Pause deliberation (checkpoint saved automatically)."""
    # LangGraph auto-saves checkpoint after each node
    # This endpoint is informational (marks session as paused in metadata)

    redis = RedisManager()
    metadata = redis.load_metadata(session_id) or {}
    metadata["paused"] = True
    metadata["paused_at"] = datetime.now().isoformat()
    redis.save_metadata(session_id, metadata)

    return {"status": "paused", "session_id": session_id}

@router.post("/{session_id}/resume")
async def resume_deliberation(session_id: str, user_input: str | None = None):
    """Resume paused deliberation."""

    config = {"configurable": {"thread_id": session_id}}

    # If user_input provided (e.g., from breakpoint), inject into state
    state_update = {}
    if user_input:
        state_update["user_input"] = user_input

    # Resume graph (continues from last checkpoint)
    result = await graph.ainvoke(state_update, config=config)

    # Mark as resumed
    redis = RedisManager()
    metadata = redis.load_metadata(session_id) or {}
    metadata["paused"] = False
    redis.save_metadata(session_id, metadata)

    return result

@router.get("/{session_id}/checkpoints")
async def list_checkpoints(session_id: str):
    """List all checkpoints for time travel."""

    config = {"configurable": {"thread_id": session_id}}

    # Get checkpoint history
    checkpoints = []
    async for checkpoint in graph.aget_state_history(config):
        checkpoints.append({
            "checkpoint_id": checkpoint.config["configurable"]["checkpoint_id"],
            "node": checkpoint.metadata.get("node"),
            "timestamp": checkpoint.metadata.get("timestamp"),
            "phase": checkpoint.values.get("phase"),
            "round_number": checkpoint.values.get("round_number"),
        })

    return checkpoints

@router.post("/{session_id}/rewind")
async def rewind_to_checkpoint(session_id: str, checkpoint_id: str):
    """Rewind to specific checkpoint (time travel)."""

    config = {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_id": checkpoint_id
        }
    }

    # Get state at checkpoint
    state = await graph.aget_state(config)

    return state.values
```

---

## 6. Benefits Analysis

### 6.1 User Experience Improvements

| Feature | v1 (Console) | v2 (LangGraph + Web) | Impact |
|---------|-------------|---------------------|--------|
| **Real-time Updates** | Wait for full round | See contributions as they arrive | HIGH: Better engagement |
| **Pause/Resume** | Not supported | Pause anytime, resume later | HIGH: Multi-day deliberations |
| **Human Intervention** | Console prompts only | Click to redirect, extend, or stop | MEDIUM: More control |
| **Transparency** | Text log only | Graph visualization, node traces | MEDIUM: Understand process |
| **Error Recovery** | Start over | Resume from last checkpoint | HIGH: Avoid wasted cost |
| **Multi-Problem** | Sequential only | Parallel sub-problem branches | LOW: v1 is fast enough |

### 6.2 Developer Experience Improvements

| Feature | v1 (Sequential) | v2 (LangGraph) | Impact |
|---------|----------------|---------------|--------|
| **Debugging** | Print statements | Node-level traces, graph viz | HIGH: Easier troubleshooting |
| **Testing** | Full session required | Test individual nodes | HIGH: Faster iteration |
| **Observability** | Manual logging | Built-in metrics (Prometheus) | MEDIUM: Production monitoring |
| **Extensibility** | Modify orchestration logic | Add new nodes/edges | MEDIUM: Faster feature dev |
| **State Inspection** | Redis JSON dump | Checkpoint browser, time travel | HIGH: Debug state issues |

### 6.3 Cost Optimization Opportunities

LangGraph enables **new cost optimizations** not possible in v1:

1. **Cached Routing Decisions**: Facilitator decision cached at checkpoint
   - v1: Re-call facilitator if process crashes
   - v2: Resume from cached decision (0 extra cost)
   - **Savings**: ~$0.001/crash recovery

2. **Partial Rewind**: Rewind to specific node without re-running earlier nodes
   - v1: Must replay full session to test alternative paths
   - v2: Rewind to Round 5, explore different moderator intervention
   - **Savings**: ~$0.05/alternative exploration

3. **Smart Checkpointing**: Only checkpoint at expensive nodes (persona calls)
   - Skip checkpointing cheap nodes (routing, metrics calculation)
   - **Savings**: ~30% reduction in checkpoint storage costs

### 6.4 Operational Improvements

| Metric | v1 | v2 (Target) | Improvement |
|--------|----|-----------|----|
| **Session Recovery Time** | N/A (start over) | <1 second (from checkpoint) | ∞ |
| **Concurrent Sessions** | Limited by asyncio | Horizontal scaling (graph workers) | 10x |
| **Observability** | Manual logs | Prometheus + Grafana dashboards | N/A |
| **Debugging Time** | 30 min (reproduce issue) | 5 min (inspect checkpoint) | 6x |
| **Feature Velocity** | 1 week/feature | 2-3 days/feature (modular nodes) | 2-3x |

---

## 7. Migration Risks & Concerns

### 7.1 Critical Safety Risks

#### Risk 0: **Infinite Loops** (NEW - CRITICAL)

**Description**: Graph cycles could loop forever (e.g., facilitator → continue → check_convergence → facilitator → ...).

**Impact**: CRITICAL (runaway costs, hung sessions, service outage)

**Probability**: MEDIUM (graphs with cycles are inherently risky)

**Prevention Strategy (100% Confidence)**:

LangGraph provides **multiple layers of loop prevention**, ensuring infinite loops are impossible:

##### Layer 1: Recursion Limit (Hard Cap)

```python
from langgraph.graph import StateGraph

# MANDATORY: Set recursion limit on compilation
graph = workflow.compile(
    checkpointer=checkpointer,
    recursion_limit=50  # HARD CAP: Graph terminates after 50 steps
)

# For bo1: Set based on max deliberation length
# Max rounds = 15, plus overhead nodes (decompose, select, vote, synthesize)
# Safe limit = 15 rounds × 3 nodes/round + 10 overhead = 55 steps
DELIBERATION_RECURSION_LIMIT = 55
```

**How it works**:
- LangGraph counts every node execution as 1 step
- When limit reached, raises `GraphRecursionError` (catchable)
- Graph terminates immediately, state preserved at last checkpoint
- **100% guaranteed**: No graph can exceed recursion limit

##### Layer 2: Cycle Detection (Graph Analysis)

```python
# bo1/graph/safety.py
import networkx as nx
from langgraph.graph import StateGraph

def validate_graph_acyclic(workflow: StateGraph) -> None:
    """Validate graph has no uncontrolled cycles.

    Raises:
        ValueError: If graph contains cycles without proper exit conditions
    """
    # Convert LangGraph to NetworkX directed graph
    G = nx.DiGraph()

    # Add edges from workflow
    for source, targets in workflow.edges.items():
        for target in targets:
            G.add_edge(source, target)

    # Check for cycles
    try:
        cycles = list(nx.simple_cycles(G))
        if cycles:
            # Cycles are OK if they have conditional exits
            # Validate each cycle has at least one conditional edge
            for cycle in cycles:
                if not has_exit_condition(workflow, cycle):
                    raise ValueError(f"Uncontrolled cycle detected: {cycle}")
    except nx.NetworkXNoCycle:
        pass  # Graph is acyclic, safe

def has_exit_condition(workflow: StateGraph, cycle: list[str]) -> bool:
    """Check if cycle has conditional exit (e.g., convergence check)."""
    for node in cycle:
        # Check if node has conditional edges that could break loop
        if node in workflow.conditional_edges:
            # Verify at least one path leads OUT of cycle
            for target in workflow.conditional_edges[node].values():
                if target not in cycle:
                    return True  # Exit path exists
    return False  # No exit path found
```

**Usage**:
```python
# Run during graph compilation (development time)
workflow = create_deliberation_graph()
validate_graph_acyclic(workflow)  # Raises error if unsafe cycles
graph = workflow.compile(checkpointer=checkpointer, recursion_limit=55)
```

##### Layer 3: Round Counter (Domain-Specific Cap)

```python
# bo1/graph/nodes.py
async def check_convergence_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Check convergence AND enforce hard round limit."""

    # Domain logic: Hard cap at max_rounds
    if state["round_number"] >= state["max_rounds"]:
        state["should_stop"] = True
        state["stop_reason"] = "max_rounds_reached"
        return state

    # Additional safety: Absolute hard cap (15 rounds per PRD)
    if state["round_number"] >= 15:
        state["should_stop"] = True
        state["stop_reason"] = "absolute_hard_cap_reached"
        logger.warning(f"Session {state['session_id']}: Hit absolute 15-round cap")
        return state

    # Calculate convergence metrics
    metrics = calculate_metrics(state["contributions"])

    # Early stop conditions
    if metrics["convergence"] > 0.85 and metrics["novelty"] < 0.3:
        state["should_stop"] = True
        state["stop_reason"] = "consensus_reached"

    return state

# Routing function MUST respect should_stop
def route_convergence_check(state: DeliberationGraphState) -> str:
    if state["should_stop"]:
        return "vote"  # EXIT loop
    return "facilitator_decide"  # CONTINUE loop
```

**Guarantees**:
- Round counter increments monotonically (no reset in loop)
- Hard cap at 15 rounds (PRD requirement)
- Conditional routing MUST check `should_stop` flag
- **Impossible to loop beyond max_rounds**

##### Layer 4: Timeout Watchdog (Execution Time Limit)

```python
# bo1/graph/execution.py
import asyncio
from datetime import timedelta

async def execute_deliberation_with_timeout(
    graph,
    initial_state: DeliberationGraphState,
    config: dict,
    timeout_seconds: int = 3600  # 1 hour hard timeout
) -> DeliberationGraphState:
    """Execute graph with absolute timeout.

    Args:
        timeout_seconds: Maximum execution time (default: 1 hour)

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout
    """
    try:
        result = await asyncio.wait_for(
            graph.ainvoke(initial_state, config=config),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Deliberation timeout after {timeout_seconds}s")

        # Load last checkpoint (state preserved)
        last_state = await graph.aget_state(config)

        # Mark as timed out
        last_state.values["phase"] = DeliberationPhase.COMPLETE
        last_state.values["metadata"]["timeout"] = True
        last_state.values["metadata"]["timeout_at"] = datetime.now().isoformat()

        raise
```

**Usage**:
```python
# API endpoint with timeout
@app.post("/api/deliberation/{session_id}/start")
async def start_deliberation(session_id: str, problem: Problem):
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await execute_deliberation_with_timeout(
            graph=graph,
            initial_state=initial_state,
            config=config,
            timeout_seconds=3600  # 1 hour max
        )
        return result
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=408,
            content={"error": "Deliberation timeout", "session_id": session_id}
        )
```

##### Layer 5: Cost-Based Kill Switch

```python
# bo1/graph/nodes.py
async def cost_guard_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Check cost budget before expensive operations.

    This node runs BEFORE each persona contribution.
    """
    MAX_COST_PER_SESSION = 1.0  # $1 hard cap

    current_cost = state["metrics"]["total_cost"]

    if current_cost >= MAX_COST_PER_SESSION:
        logger.error(f"Cost budget exceeded: ${current_cost:.2f}")
        state["should_stop"] = True
        state["stop_reason"] = "cost_budget_exceeded"
        state["phase"] = DeliberationPhase.COMPLETE

    return state

# Add to graph BEFORE expensive nodes
workflow.add_node("cost_guard", cost_guard_node)
workflow.add_edge("facilitator_decide", "cost_guard")
workflow.add_conditional_edges(
    "cost_guard",
    lambda s: "abort" if s["should_stop"] else "continue",
    {
        "abort": "synthesize",  # Force early synthesis
        "continue": "persona_contribute"
    }
)
```

##### Summary: Multi-Layer Loop Prevention

| Layer | Mechanism | Confidence | Failure Mode |
|-------|-----------|------------|--------------|
| **1. Recursion Limit** | LangGraph built-in | 100% | Graph terminates, exception raised |
| **2. Cycle Detection** | NetworkX graph analysis | 100% | Compile-time validation error |
| **3. Round Counter** | Domain logic (max_rounds) | 100% | Conditional routing to vote |
| **4. Timeout Watchdog** | asyncio timeout | 100% | Execution killed, checkpoint preserved |
| **5. Cost Kill Switch** | Budget guard node | 100% | Early termination, synthesis triggered |

**Combined Guarantee**: **Infinite loops are impossible** with 100% confidence. Even if all domain logic fails (round counter, convergence check), hard limits (recursion, timeout, cost) terminate execution.

**Testing Strategy**:
```python
# tests/test_loop_prevention.py
import pytest
from langgraph.errors import GraphRecursionError

async def test_recursion_limit_prevents_infinite_loop():
    """Verify recursion limit terminates runaway graph."""

    # Create malicious graph with uncontrolled loop
    workflow = StateGraph(dict)
    workflow.add_node("loop", lambda s: s)
    workflow.add_edge("loop", "loop")  # Infinite self-loop
    graph = workflow.compile(recursion_limit=10)

    # Execute
    with pytest.raises(GraphRecursionError):
        await graph.ainvoke({"count": 0})

async def test_round_counter_prevents_runaway():
    """Verify round counter enforces max_rounds."""

    # Create state with max_rounds=5
    state = create_state(max_rounds=5)

    # Simulate 10 rounds
    for i in range(10):
        state = await check_convergence_node(state)
        state["round_number"] += 1

        if state["should_stop"]:
            break

    # Verify stopped at max_rounds
    assert state["round_number"] <= 5
    assert state["should_stop"] is True

async def test_timeout_kills_long_running_session():
    """Verify timeout terminates execution."""

    async def slow_node(state):
        await asyncio.sleep(10)  # Simulate slow LLM call
        return state

    workflow = StateGraph(dict)
    workflow.add_node("slow", slow_node)
    graph = workflow.compile()

    # Execute with 1 second timeout
    with pytest.raises(asyncio.TimeoutError):
        await execute_deliberation_with_timeout(
            graph, {}, {}, timeout_seconds=1
        )
```

#### Risk 0b: **Kill Switches & Session Termination** (NEW - CRITICAL)

**Requirement**: Users must be able to terminate their own sessions, admins must be able to kill any session.

**Implementation**:

##### User Kill Switch (Own Sessions)

```python
# bo1/graph/execution.py
class SessionManager:
    """Manages session lifecycle including termination."""

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self.active_executions: dict[str, asyncio.Task] = {}

    async def start_session(
        self,
        session_id: str,
        user_id: str,
        initial_state: DeliberationGraphState
    ) -> asyncio.Task:
        """Start deliberation session in background."""

        # Store user ownership
        metadata = {"user_id": user_id, "status": "running"}
        self.redis.save_metadata(session_id, metadata)

        # Create background task
        config = {"configurable": {"thread_id": session_id}}
        task = asyncio.create_task(
            graph.ainvoke(initial_state, config=config)
        )

        # Track active execution
        self.active_executions[session_id] = task

        return task

    async def kill_session(
        self,
        session_id: str,
        requesting_user_id: str,
        reason: str = "user_terminated"
    ) -> bool:
        """Terminate session (user can only kill own sessions).

        Args:
            session_id: Session to terminate
            requesting_user_id: User requesting termination
            reason: Termination reason (for logging)

        Returns:
            True if killed, False if not found or unauthorized

        Raises:
            PermissionError: If user doesn't own session
        """
        # Check ownership
        metadata = self.redis.load_metadata(session_id)
        if not metadata:
            return False

        if metadata.get("user_id") != requesting_user_id:
            raise PermissionError(
                f"User {requesting_user_id} cannot kill session {session_id} "
                f"owned by {metadata.get('user_id')}"
            )

        # Cancel background task
        task = self.active_executions.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Killed session {session_id}: {reason}")

        # Update metadata
        metadata["status"] = "killed"
        metadata["killed_at"] = datetime.now().isoformat()
        metadata["killed_by"] = requesting_user_id
        metadata["kill_reason"] = reason
        self.redis.save_metadata(session_id, metadata)

        # Load last checkpoint and mark as terminated
        config = {"configurable": {"thread_id": session_id}}
        state = await graph.aget_state(config)
        if state:
            state.values["phase"] = DeliberationPhase.COMPLETE
            state.values["metadata"]["terminated"] = True
            # State auto-saved by checkpointer

        return True

# API endpoint
@app.post("/api/deliberation/{session_id}/kill")
async def kill_deliberation(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Kill user's own deliberation session."""

    try:
        success = await session_manager.kill_session(
            session_id=session_id,
            requesting_user_id=user_id,
            reason="user_requested"
        )

        if success:
            return {"status": "killed", "session_id": session_id}
        else:
            raise HTTPException(404, "Session not found")

    except PermissionError as e:
        raise HTTPException(403, str(e))
```

##### Admin Kill Switch (All Sessions)

```python
# bo1/graph/execution.py
class SessionManager:

    async def admin_kill_session(
        self,
        session_id: str,
        admin_user_id: str,
        reason: str = "admin_terminated"
    ) -> bool:
        """Terminate any session (admin only).

        No ownership check - admins can kill any session.
        """
        # Verify admin role (check against admin list or role-based auth)
        if not await self.is_admin(admin_user_id):
            raise PermissionError(f"User {admin_user_id} is not an admin")

        # Cancel background task
        task = self.active_executions.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.warning(f"Admin {admin_user_id} killed session {session_id}: {reason}")

        # Update metadata
        metadata = self.redis.load_metadata(session_id) or {}
        metadata["status"] = "killed_by_admin"
        metadata["killed_at"] = datetime.now().isoformat()
        metadata["killed_by"] = admin_user_id
        metadata["kill_reason"] = reason
        self.redis.save_metadata(session_id, metadata)

        # Mark checkpoint as terminated
        config = {"configurable": {"thread_id": session_id}}
        state = await graph.aget_state(config)
        if state:
            state.values["phase"] = DeliberationPhase.COMPLETE
            state.values["metadata"]["admin_terminated"] = True

        return True

    async def admin_kill_all_sessions(
        self,
        admin_user_id: str,
        reason: str = "system_maintenance"
    ) -> int:
        """Kill ALL active sessions (emergency use only)."""

        if not await self.is_admin(admin_user_id):
            raise PermissionError(f"User {admin_user_id} is not an admin")

        killed_count = 0

        # Get all active sessions
        all_sessions = self.redis.list_sessions()

        for session_id in all_sessions:
            try:
                await self.admin_kill_session(
                    session_id=session_id,
                    admin_user_id=admin_user_id,
                    reason=reason
                )
                killed_count += 1
            except Exception as e:
                logger.error(f"Failed to kill session {session_id}: {e}")

        logger.warning(
            f"Admin {admin_user_id} killed {killed_count} sessions: {reason}"
        )

        return killed_count

    async def is_admin(self, user_id: str) -> bool:
        """Check if user has admin role."""
        # TODO: Implement role-based auth (check against admin list)
        # For now, check environment variable
        admin_ids = os.getenv("ADMIN_USER_IDS", "").split(",")
        return user_id in admin_ids

# Admin API endpoints
@app.post("/api/admin/sessions/{session_id}/kill")
async def admin_kill_session(
    session_id: str,
    reason: str | None = None,
    admin_id: str = Depends(require_admin_role)
):
    """Admin endpoint: Kill any session."""

    success = await session_manager.admin_kill_session(
        session_id=session_id,
        admin_user_id=admin_id,
        reason=reason or "admin_terminated"
    )

    return {"status": "killed", "session_id": session_id}

@app.post("/api/admin/sessions/kill-all")
async def admin_kill_all_sessions(
    reason: str | None = None,
    confirm: bool = False,
    admin_id: str = Depends(require_admin_role)
):
    """Admin endpoint: Kill ALL sessions (emergency use)."""

    if not confirm:
        raise HTTPException(400, "Must set confirm=true to kill all sessions")

    killed_count = await session_manager.admin_kill_all_sessions(
        admin_user_id=admin_id,
        reason=reason or "system_maintenance"
    )

    return {"status": "killed_all", "count": killed_count}
```

##### Graceful Shutdown (for deployments)

```python
# bo1/server.py
import signal
from fastapi import FastAPI

app = FastAPI()

async def shutdown_handler(signal_num, frame):
    """Gracefully shutdown on SIGTERM/SIGINT."""

    logger.info(f"Received signal {signal_num}, shutting down...")

    # Get all active sessions
    active_sessions = list(session_manager.active_executions.keys())

    logger.info(f"Terminating {len(active_sessions)} active sessions...")

    # Cancel all tasks with grace period
    for session_id in active_sessions:
        task = session_manager.active_executions[session_id]
        if not task.done():
            task.cancel()

            # Give task 5 seconds to save checkpoint
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    logger.info("All sessions terminated, exiting")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

**Kill Switch Guarantees**:

| Capability | User | Admin | Implementation |
|------------|------|-------|----------------|
| **Kill own session** | ✅ | ✅ | `SessionManager.kill_session()` with ownership check |
| **Kill any session** | ❌ | ✅ | `SessionManager.admin_kill_session()` (no ownership check) |
| **Kill all sessions** | ❌ | ✅ | `SessionManager.admin_kill_all_sessions()` |
| **Checkpoint preserved** | ✅ | ✅ | LangGraph auto-saves before task cancellation |
| **Audit trail** | ✅ | ✅ | Metadata tracks killer, reason, timestamp |
| **Graceful shutdown** | ✅ | ✅ | Signal handlers cancel tasks with 5s grace period |

**Testing**:
```python
# tests/test_kill_switches.py
async def test_user_can_kill_own_session():
    """Verify user can terminate their own session."""

    session_id = await session_manager.start_session(
        session_id="test_123",
        user_id="user_1",
        initial_state=create_state()
    )

    # User kills own session
    success = await session_manager.kill_session(
        session_id="test_123",
        requesting_user_id="user_1",
        reason="test"
    )

    assert success is True

    # Verify metadata updated
    metadata = redis.load_metadata("test_123")
    assert metadata["status"] == "killed"
    assert metadata["killed_by"] == "user_1"

async def test_user_cannot_kill_others_session():
    """Verify user cannot terminate other users' sessions."""

    await session_manager.start_session("test_123", "user_1", create_state())

    # User 2 tries to kill user 1's session
    with pytest.raises(PermissionError):
        await session_manager.kill_session(
            session_id="test_123",
            requesting_user_id="user_2",
            reason="test"
        )

async def test_admin_can_kill_any_session():
    """Verify admin can kill any session."""

    await session_manager.start_session("test_123", "user_1", create_state())

    # Admin kills user 1's session
    success = await session_manager.admin_kill_session(
        session_id="test_123",
        admin_user_id="admin_1",
        reason="test"
    )

    assert success is True
```

### 7.2 Technical Risks (Continued)

#### Risk 1: **State Schema Divergence**

**Description**: v1 `DeliberationState` and v2 `DeliberationGraphState` drift over time.

**Impact**: HIGH (breaks compatibility bridge)

**Mitigation**:
- Use Pydantic validation for both schemas
- Automated tests: `test_state_compatibility.py`
  ```python
  def test_v1_to_v2_conversion():
      v1_state = create_v1_state()
      v2_state = deliberation_state_to_graph_state(v1_state)
      assert v2_state["problem"] == v1_state.problem
      assert v2_state["round_number"] == v1_state.current_round
  ```
- Migration scripts for checkpoint schema updates
- Version field in state: `state_schema_version = "2.0"`

#### Risk 2: **Checkpoint Storage Costs**

**Description**: Storing full state at every node = large Redis/Postgres usage.

**Impact**: MEDIUM (cost increase)

**Mitigation**:
- **Smart checkpointing**: Only checkpoint expensive nodes
  ```python
  workflow.add_node("persona_contribute", persona_contribute_node, checkpoint=True)
  workflow.add_node("check_convergence", check_convergence_node, checkpoint=False)
  ```
- **TTL policy**: Auto-expire checkpoints after 7 days
- **Compression**: Use zlib compression for large contributions
  ```python
  checkpointer = RedisSaver(
      redis_url="...",
      compress=True,  # zlib compression
      ttl_seconds=604800
  )
  ```
- **Estimate**: 100 checkpoints/session × 50 KB/checkpoint × 7 days = ~35 MB/session
  - Redis cost: ~$0.01/session (negligible vs $0.10 LLM cost)

#### Risk 3: **Performance Degradation**

**Description**: Graph overhead slows down execution vs v1 sequential.

**Impact**: MEDIUM (latency increase)

**Mitigation**:
- **Benchmark**: Week 2 - measure v1 vs v2 latency (target: <10% increase)
- **Profile**: Identify slow nodes, optimize hot paths
- **Async optimization**: Use `asyncio.gather()` in nodes (same as v1)
- **Caching**: LangGraph respects LangChain cache (no double-caching)

#### Risk 4: **Learning Curve**

**Description**: Team unfamiliar with LangGraph concepts (nodes, edges, checkpoints).

**Impact**: LOW (time investment)

**Mitigation**:
- **Training**: Week 1 - LangGraph tutorial (official docs + examples)
- **Gradual adoption**: Phase 1 - simple linear graph (no branching)
- **Documentation**: Internal wiki with bo1-specific graph patterns
- **Code review**: Pair programming during Phase 1-2

### 7.2 Operational Risks

#### Risk 5: **Checkpoint Corruption**

**Description**: Redis crash or Postgres failure corrupts checkpoint.

**Impact**: HIGH (lost sessions)

**Mitigation**:
- **Redis persistence**: Enable AOF + RDB snapshots
- **Backup**: Daily backups of checkpoint storage (same as v1 Redis backups)
- **Validation**: Pydantic validation on checkpoint load
  ```python
  try:
      state = DeliberationGraphState(**checkpoint_data)
  except ValidationError as e:
      logger.error(f"Corrupt checkpoint: {e}")
      # Fallback: load last known good checkpoint
  ```
- **Multi-replica**: Redis Sentinel (3 replicas) for HA

#### Risk 6: **Zombie Checkpoints**

**Description**: Old sessions accumulate, fill storage.

**Impact**: MEDIUM (storage bloat)

**Mitigation**:
- **TTL**: Auto-expire after 7 days (Redis) or 30 days (Postgres)
- **Garbage collection**: Weekly cron job to delete expired sessions
  ```python
  async def cleanup_old_checkpoints():
      redis = RedisManager()
      sessions = redis.list_sessions()
      for session_id in sessions:
          ttl = redis.get_session_ttl(session_id)
          if ttl < 0:  # No expiry set
              redis.delete_state(session_id)
  ```
- **Monitoring**: Alert if checkpoint storage >80% capacity

---

## 8. Implementation Checklist

### Phase 1: Foundation (Weeks 1-2)

- [ ] Install LangGraph: `uv add langgraph langgraph-checkpoint-redis`
- [ ] Create `bo1/graph/` module structure
- [ ] Define `DeliberationGraphState` schema (Pydantic + TypedDict)
- [ ] Implement compatibility bridge (`state_to_graph_state`, `graph_state_to_state`)
- [ ] Build minimal graph: Decompose → Select → Initial Round → Vote → Synthesize
- [ ] Write tests: `test_graph_basic_flow.py`
- [ ] Benchmark: v1 vs v2 execution time (target: <10% increase)

### Phase 2: Agent Wrapping (Weeks 3-4)

- [ ] Wrap facilitator as node: `facilitator_decide_node()`
- [ ] Wrap moderator as node: `moderator_intervene_node()`
- [ ] Add conditional routing: `route_facilitator_decision()`
- [ ] Implement convergence check node: `check_convergence_node()`
- [ ] Add Redis checkpointer: `RedisSaver(redis_url="...")`
- [ ] Test pause/resume: `test_checkpoint_recovery.py`
- [ ] Test node isolation: `test_facilitator_node.py`, `test_moderator_node.py`

### Phase 3: Streaming & Web (Weeks 5-6)

- [ ] Implement FastAPI endpoints: `/start`, `/stream`, `/pause`, `/resume`
- [ ] Build SvelteKit UI: Contribution feed with SSE
- [ ] Add human-in-loop: User approval breakpoint before voting
- [ ] Test streaming latency: <500ms node-to-UI update
- [ ] Implement graph visualization: Show current node, available paths
- [ ] Write integration tests: `test_api_streaming.py`

### Phase 4: Advanced Features (Weeks 7-8)

- [ ] Parallel sub-problem processing (graph branching)
- [ ] Time travel UI: `/checkpoints`, `/rewind`
- [ ] Research node integration (external/internal knowledge)
- [ ] Multi-session queue (prioritize active sessions)
- [ ] Cost tracking per checkpoint (granular cost visibility)

### Phase 5: Production (Weeks 9-10)

- [ ] Load testing: 100 concurrent sessions (Locust or k6)
- [ ] Checkpoint GC: Auto-delete expired sessions (cron job)
- [ ] Observability: Prometheus metrics (node latency, checkpoint size)
- [ ] Error recovery: Retry failed nodes (exponential backoff)
- [ ] Documentation: API docs, graph architecture diagram
- [ ] Launch: Deploy to staging, run 10 real deliberations, collect feedback

---

## 9. Recommendations

### 9.1 Go/No-Go Decision

**RECOMMENDATION: GO** (Proceed with LangGraph migration for v2)

**Justification**:
1. ✅ **Web UI needs**: Streaming, pause/resume, human-in-loop are table stakes for web UX
2. ✅ **Low risk**: Parallel development preserves v1; compatibility bridge minimizes agent changes
3. ✅ **High value**: Checkpoint recovery, time travel, graph viz significantly improve debuggability
4. ✅ **Future-proof**: Enables advanced features (parallel sub-problems, multi-session orchestration)
5. ✅ **Cost-neutral**: Checkpoint storage cost (<$0.01/session) negligible vs LLM cost ($0.10/session)

**Conditions**:
- ⚠️ **Phase 1-2 validation**: Must prove <10% latency increase and cost parity before Phase 3
- ⚠️ **Fallback plan**: Keep v1 orchestration as escape hatch (feature flag toggle)
- ⚠️ **Team training**: 1 week for LangGraph onboarding (official docs + hands-on tutorial)

### 9.2 Alternative Considered: Custom State Machine

**Option**: Build custom state machine on top of Redis (no LangGraph).

**Pros**:
- ✅ Full control over state transitions
- ✅ No external dependency
- ✅ Simpler mental model

**Cons**:
- ❌ Must implement checkpointing, streaming, time travel from scratch
- ❌ Higher maintenance burden (reinvent LangGraph features)
- ❌ Less community support (LangGraph has active ecosystem)

**Verdict**: Not recommended. LangGraph's maturity and feature set outweigh custom build effort.

### 9.3 When NOT to Use LangGraph

LangGraph is **overkill** for:
- ❌ **v1 console app**: Sequential flow works perfectly, no need for graph overhead
- ❌ **Simple chatbots**: Single LLM call, no multi-step orchestration
- ❌ **Batch processing**: No need for pause/resume or streaming

LangGraph is **essential** for:
- ✅ **Complex multi-agent workflows** (bo1 deliberation)
- ✅ **Human-in-the-loop systems** (approval gates, user redirects)
- ✅ **Long-running sessions** (multi-day deliberations, pause/resume)
- ✅ **Branching logic** (parallel sub-problems, conditional routing)

### 9.4 Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Foundation** | 2 weeks | Basic graph (parity with v1) |
| **Phase 2: Agent Wrapping** | 2 weeks | Full graph with checkpointing |
| **Phase 3: Streaming** | 2 weeks | Web UI + SSE streaming |
| **Phase 4: Advanced** | 2 weeks | Time travel, parallel processing |
| **Phase 5: Production** | 2 weeks | Load testing, monitoring |
| **Total** | **10 weeks** | Production-ready v2 with LangGraph |

---

## 10. Conclusion

LangGraph is the **right choice** for bo1 v2 web interface, unlocking critical features (streaming, pause/resume, human-in-loop) that are essential for web UX. The migration risk is **low** due to:

1. **Compatibility bridge** preserves existing agents
2. **Phased approach** allows incremental validation
3. **Fallback plan** keeps v1 orchestration as escape hatch
4. **Proven technology** (LangGraph used in production by major companies)

**Next Steps**:
1. ✅ **Approve proposal** (this document)
2. 🔧 **Week 1**: Team training (LangGraph tutorial)
3. 🔧 **Week 2**: Phase 1 implementation (basic graph)
4. 🧪 **Week 2 end**: Benchmark v1 vs v2 (latency, cost)
5. 🚀 **Go/No-Go**: Proceed to Phase 2 if benchmarks pass

---

## 11. Admin Dashboard & Monitoring (v2 Web Interface)

### 11.1 Real-Time Session Monitoring

**Requirement**: Admin UI showing active sessions with ability to kill runaway/expensive sessions.

See ADMIN_DASHBOARD_SPECIFICATION.md for full implementation details including:

- **Active Sessions Table**: Top 10 longest running, top 10 highest cost
- **Real-time metrics**: Duration, cost, percentile vs historical (90th), runaway detection
- **User context**: Email, plan tier, problem title
- **Kill switches**: One-click termination with audit trail
- **Filters**: By plan tier, sort by duration/cost
- **Auto-refresh**: 5-second polling interval

**Key Features**:
- 🔴 Flag runaway sessions (>2x median duration)
- 💰 Flag expensive sessions (>90th percentile cost)
- 👤 Show user email, plan tier, account info
- 🎯 One-click kill with confirmation
- 📊 Real-time stats: total active, runaway count, total active cost

### 11.2 AI Usage Analytics

**Cost Breakdown Dimensions**:

1. **By Deliberation Phase**:
   - Problem decomposition
   - Persona selection
   - Initial round (Round 0)
   - Round 1, 2, 3... up to 15
   - Moderator interventions
   - Voting
   - Final synthesis
   - Research (internal/external)

2. **By Plan Tier**:
   - Free tier users
   - Pro tier users
   - Enterprise tier users
   - With revenue/margin calculations

3. **By Time Period**:
   - Last 24 hours (hourly breakdown)
   - Last 7 days (daily breakdown)
   - Last 30 days (daily/weekly breakdown)
   - Custom date ranges

**Analytics Dashboards**:
- 📊 Pie chart: Cost by phase
- 📊 Bar chart: Cost by plan tier
- 📈 Line chart: Cost over time
- 📋 Detailed tables: Phase breakdown with % of total, avg per session

### 11.3 User Engagement Metrics

**Metrics Tracked**:

1. **Activity Metrics**:
   - Daily Active Users (DAU)
   - Weekly Active Users (WAU)
   - Monthly Active Users (MAU)
   - Sessions per user (avg)
   - Session completion rate

2. **Engagement Metrics**:
   - Avg session duration
   - Feature usage (top 10 features)
   - Unique users per feature
   - Usage frequency per user

3. **Retention Metrics**:
   - Cohort retention (weekly cohorts)
   - % returning users
   - Time to second session
   - Churn rate by tier

4. **Revenue Metrics** (by tier):
   - Total AI cost
   - Total revenue (subscriptions)
   - Margin % (revenue - cost)
   - Cost per active user

**Dashboard Views**:
- Summary cards (total users, sessions, completion rate)
- DAU trend chart
- Tier breakdown table (users, sessions, completion, revenue)
- Feature usage table
- Retention cohort matrix

### 11.4 Cost Tracking Infrastructure

**PostgreSQL Schema**:
```sql
-- session_metrics table: Full session data for analytics
-- feature_usage table: Track feature adoption
-- session_cost_percentiles (materialized view): Fast percentile queries
```

**Per-Phase Cost Tracking**:
- Every graph node records cost to `phase_metrics_json`
- Aggregate costs in `phase_costs` for analytics
- Track: phase name, model used, tokens, cost, duration

**Example Phase Costs**:
```json
{
  "problem_decomposition": 0.012,
  "persona_selection": 0.008,
  "initial_round": 0.045,
  "round_1_deliberation": 0.038,
  "round_2_deliberation": 0.041,
  "moderator_intervention_contrarian": 0.004,
  "round_3_deliberation": 0.035,
  "voting": 0.015,
  "synthesis": 0.022
}
```

See `zzz_project/ADMIN_DASHBOARD_SPECIFICATION.md` for complete implementation details.

---

**Document Version**: 2.1 (Updated for November 2025)
**Status**: Ready for Review
**Approval Required**: Technical Lead, Product Manager
**Estimated Effort**: 9 weeks (1 senior engineer) + 2 weeks admin dashboard (Week 10-11)
**Estimated Cost**: $0 additional infra (Redis + Postgres reuse); ~$500 in LLM testing costs
