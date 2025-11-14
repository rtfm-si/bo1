# LangGraph Training Documentation

This document provides an overview of LangGraph concepts for Board of One developers.

---

## What is LangGraph?

LangGraph is a library for building stateful, multi-actor applications with LLMs. It enables:

- **Stateful workflows** - Maintain state across multiple LLM calls
- **Checkpointing** - Save and resume execution at any point
- **Human-in-the-loop** - Pause for user input during execution
- **Conditional routing** - Different paths based on state
- **Built-in safety** - Recursion limits prevent infinite loops

---

## Core Concepts

### 1. StateGraph

The StateGraph is the main class for defining workflows.

```python
from langgraph.graph import StateGraph
from typing import TypedDict

# Define state schema
class MyState(TypedDict):
    message: str
    count: int

# Create graph
workflow = StateGraph(MyState)
```

**Key Points**:
- State must be a TypedDict for type safety
- State is immutable - nodes return new state
- State updates are merged automatically

---

### 2. Nodes

Nodes are functions that process state and perform actions.

```python
def my_node(state: MyState) -> MyState:
    """Example node function."""
    return {
        "message": state["message"] + " processed",
        "count": state["count"] + 1
    }

# Add to graph
workflow.add_node("my_node", my_node)
```

**Node Rules**:
- Must accept state as first parameter
- Must return dict with state updates
- Can be sync or async functions
- Should be pure functions (no side effects)

---

### 3. Edges

Edges connect nodes and define execution flow.

```python
# Direct edge: always goes to next node
workflow.add_edge("node1", "node2")

# Conditional edge: routing based on state
def route_decision(state: MyState) -> str:
    if state["count"] > 10:
        return "finish"
    else:
        return "continue"

workflow.add_conditional_edges(
    "check_node",
    route_decision,
    {
        "finish": END,
        "continue": "node1"
    }
)
```

**Edge Types**:
- **Direct edges** - Always go to specified node
- **Conditional edges** - Routing function determines next node
- **END** - Special node that terminates execution

---

### 4. Checkpoints

Checkpoints enable pause/resume functionality.

```python
from langgraph.checkpoint.redis import RedisSaver

# Create checkpointer
checkpointer = RedisSaver(
    redis_url="redis://localhost:6379",
    ttl_seconds=604800  # 7 days
)

# Compile with checkpointer
graph = workflow.compile(checkpointer=checkpointer)

# Execute with thread_id (enables checkpointing)
config = {"configurable": {"thread_id": "session-123"}}
result = graph.invoke(initial_state, config=config)

# Resume later
state_snapshot = graph.get_state(config)
result = graph.invoke(state_snapshot.values, config=config)
```

**Checkpoint Features**:
- Automatic state persistence after each node
- Can resume from any checkpoint
- TTL for automatic cleanup
- Supports Redis, PostgreSQL, or in-memory storage

---

### 5. Recursion Limits

LangGraph prevents infinite loops with recursion limits.

```python
# Set recursion limit during compilation
graph = workflow.compile(
    checkpointer=checkpointer,
    recursion_limit=55  # Max 55 node executions
)
```

**When to Use**:
- Prevents runaway loops in conditional routing
- Acts as safety net (should never hit in normal execution)
- For Board of One: 55 = 15 rounds × 3 nodes/round + 10 overhead

---

## Board of One Usage

### Deliberation Graph Structure

```
decompose → select_personas → initial_round → facilitator
                                                    ↓
                          ┌────────────────────────┼──────┐
                          ↓                        ↓      ↓
                      continue                moderator  vote
                          ↓                        ↓      ↓
                      persona                intervention |
                          ↓                        ↓      |
                      check_convergence ←──────────┘      |
                          ↓                               |
                      (continue/stop)                     |
                          ↓                               |
                      facilitator ←───────────────────────┘
                                                          ↓
                                                      synthesize → END
```

### State Schema

```python
from typing import TypedDict

class DeliberationGraphState(TypedDict):
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
    facilitator_decision: FacilitatorDecision | None
    should_stop: bool
    stop_reason: str | None
    user_input: str | None
    current_node: str
```

### Example Node: Facilitator Decision

```python
from bo1.graph.state import DeliberationGraphState
from bo1.agents.facilitator import FacilitatorAgent

def facilitator_decide_node(
    state: DeliberationGraphState
) -> DeliberationGraphState:
    """Facilitator decides next action."""
    # Extract current state
    contributions = state["contributions"]
    round_number = state["round_number"]

    # Call existing agent
    agent = FacilitatorAgent()
    decision = agent.decide_next_action(
        contributions=contributions,
        round_number=round_number
    )

    # Return state updates
    return {
        "facilitator_decision": decision,
        "phase_costs": {
            **state.get("phase_costs", {}),
            f"round_{round_number}_facilitator": decision.cost
        }
    }
```

### Example Router: Conditional Routing

```python
def route_facilitator_decision(
    state: DeliberationGraphState
) -> str:
    """Route based on facilitator decision."""
    decision = state["facilitator_decision"]

    if decision.action == "vote":
        return "vote"
    elif decision.action == "moderator":
        return "moderator_intervene"
    elif decision.action == "continue":
        return "persona_contribute"
    else:
        raise ValueError(f"Unknown action: {decision.action}")
```

---

## Loop Prevention (5 Layers)

### Layer 1: Recursion Limit

```python
graph = workflow.compile(recursion_limit=55)
```

Built-in LangGraph feature. Raises `GraphRecursionError` if exceeded.

### Layer 2: Cycle Detection

```python
def validate_graph_acyclic(graph):
    """Validate no uncontrolled cycles in graph."""
    import networkx as nx

    # Convert to NetworkX DiGraph
    G = nx.DiGraph()
    # ... add nodes and edges

    # Find cycles
    cycles = list(nx.simple_cycles(G))

    # Check each cycle has exit condition
    for cycle in cycles:
        if not has_exit_condition(cycle):
            raise ValueError(f"Uncontrolled cycle: {cycle}")
```

Run at compile time to catch dangerous loops.

### Layer 3: Round Counter

```python
def check_convergence_node(state: DeliberationGraphState):
    """Check if deliberation should stop."""
    round_number = state["round_number"]
    max_rounds = state["max_rounds"]

    # Absolute hard cap
    if round_number >= 15:
        return {
            "should_stop": True,
            "stop_reason": "hard_cap_reached"
        }

    # User-specified max
    if round_number >= max_rounds:
        return {
            "should_stop": True,
            "stop_reason": "max_rounds_reached"
        }

    # ... check convergence metrics
```

Domain logic enforces round limits.

### Layer 4: Timeout Watchdog

```python
import asyncio

async def execute_deliberation_with_timeout(graph, state, config):
    """Execute graph with timeout."""
    try:
        result = await asyncio.wait_for(
            graph.ainvoke(state, config=config),
            timeout=3600  # 1 hour
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Deliberation timed out: {config}")
        # Checkpoint auto-saved, can resume later
        raise
```

Prevents sessions from running indefinitely.

### Layer 5: Cost Kill Switch

```python
def cost_guard_node(state: DeliberationGraphState):
    """Check if cost budget exceeded."""
    total_cost = state["metrics"]["total_cost"]
    max_cost = state.get("max_cost_per_session", 1.00)

    if total_cost >= max_cost:
        return {
            "should_stop": True,
            "stop_reason": "cost_budget_exceeded"
        }

    return {}
```

Prevents runaway costs.

---

## Streaming Events

LangGraph supports real-time event streaming for UI updates.

```python
async def stream_deliberation(graph, state, config):
    """Stream events to client."""
    async for event in graph.astream_events(state, config=config):
        event_type = event["event"]

        if event_type == "on_node_start":
            yield {"type": "node_start", "node": event["name"]}

        elif event_type == "on_node_end":
            yield {"type": "node_end", "node": event["name"]}

        elif event_type == "error":
            yield {"type": "error", "message": str(event["error"])}
```

**Use Cases**:
- Real-time progress updates in web UI
- Server-Sent Events (SSE) for browser
- WebSocket connections
- Console live display (Rich library)

---

## Testing LangGraph Applications

### Unit Testing Nodes

```python
def test_facilitator_node():
    """Test facilitator node in isolation."""
    # Setup state
    state = {
        "contributions": [...],
        "round_number": 2,
        # ... other fields
    }

    # Call node
    result = facilitator_decide_node(state)

    # Verify
    assert "facilitator_decision" in result
    assert result["facilitator_decision"].action in ["vote", "continue", "moderator"]
```

### Integration Testing Graphs

```python
async def test_full_graph():
    """Test complete graph execution."""
    # Setup
    graph = create_deliberation_graph()
    initial_state = create_initial_state(problem)
    config = {"configurable": {"thread_id": "test-123"}}

    # Execute
    result = await graph.ainvoke(initial_state, config=config)

    # Verify
    assert result["phase"] == DeliberationPhase.COMPLETE
    assert len(result["contributions"]) > 0
    assert result["synthesis_report"] is not None
```

### Testing Checkpoints

```python
async def test_checkpoint_recovery():
    """Test pause and resume."""
    graph = create_deliberation_graph()
    config = {"configurable": {"thread_id": "test-resume"}}

    # Execute partially (pause after decompose)
    initial_state = {...}
    result1 = await graph.ainvoke(initial_state, config=config)

    # Simulate pause - get checkpoint
    snapshot = graph.get_state(config)

    # Resume from checkpoint
    result2 = await graph.ainvoke(snapshot.values, config=config)

    # Verify continued from checkpoint
    assert result2["round_number"] > result1["round_number"]
```

---

## Performance Tips

### 1. Minimize State Size

```python
# BAD: Store full LLM responses
state["all_responses"] = [response1, response2, ...]  # 100KB+

# GOOD: Store summaries
state["round_summaries"] = ["Round 1 summary", ...]  # 1KB
```

### 2. Use Async for I/O

```python
# BAD: Synchronous LLM calls
result = llm.call(prompt)

# GOOD: Async LLM calls
result = await llm.acall(prompt)
```

### 3. Parallel Node Execution

```python
# LangGraph doesn't support parallel nodes yet
# Workaround: Use asyncio.gather() inside node

async def initial_round_node(state):
    """Call all personas in parallel."""
    contributions = await asyncio.gather(
        *[call_persona(code) for code in state["personas"]]
    )
    return {"contributions": contributions}
```

### 4. Optimize Checkpointing

```python
# Checkpoint after expensive nodes only
graph = workflow.compile(
    checkpointer=checkpointer,
    checkpoint_strategy="selective"  # Not yet implemented
)

# Current: Checkpoints after every node (safe but slower)
```

---

## Debugging

### Print State at Each Node

```python
def debug_node(state: MyState) -> MyState:
    """Debug helper node."""
    print(f"[DEBUG] Current state: {state}")
    return {}

# Add after each node
workflow.add_node("node1", node1)
workflow.add_node("debug1", debug_node)
workflow.add_edge("node1", "debug1")
```

### Visualize Graph

```python
# LangGraph supports graph visualization
from langgraph.graph import visualize

# Generate Mermaid diagram
diagram = visualize(graph)
print(diagram)

# Save to file
with open("graph.mmd", "w") as f:
    f.write(diagram)
```

### Step-by-Step Execution

```python
# Execute one node at a time
for step in graph.stream(initial_state, config=config):
    print(f"Step: {step}")
    input("Press Enter to continue...")
```

---

## Best Practices

1. **Keep nodes pure** - No side effects, return only state updates
2. **Use type hints** - TypedDict for state, type annotations for functions
3. **Test nodes in isolation** - Unit test each node before integration
4. **Validate state** - Use Pydantic models for complex state
5. **Handle errors gracefully** - Try/except in nodes, log errors
6. **Document routing logic** - Clear comments for conditional edges
7. **Use meaningful node names** - `facilitator_decide` not `node7`
8. **Checkpoint strategically** - After expensive operations
9. **Monitor recursion** - Alert if approaching limit
10. **Clean up old checkpoints** - TTL or manual cleanup

---

## Resources

### Official Documentation
- [LangGraph Introduction](https://langchain-ai.github.io/langgraph/)
- [LangGraph API Reference](https://langchain-ai.github.io/langgraph/reference/)
- [LangGraph Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)

### Board of One Specific
- `CLAUDE.md` - Architecture overview
- `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` - Week 4-5 (LangGraph migration)
- `examples/hello_world_graph.py` - Simple example
- `bo1/graph/` - Graph implementation

---

**Last Updated**: 2025-11-14 (Week 4, Day 22)
