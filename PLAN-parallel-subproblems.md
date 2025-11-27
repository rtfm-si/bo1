# Plan: Parallel Sub-Problem Execution

## Problem Statement

Currently, sub-problems run **sequentially** even when they're independent. This wastes time when sub-problems don't depend on each other's conclusions.

**Current**: SP1 → SP2 → SP3 → Meta-synthesis (~15-20 min for 3 sub-problems)
**Goal**: Independent sub-problems run in parallel (~5-7 min for 3 independent sub-problems)

---

## Current Architecture

### Already Exists
- `SubProblem.dependencies: list[str]` - field for tracking prerequisites (currently unused)
- `parallel_round_node` - pattern for parallel async execution via `asyncio.gather()`
- `SubProblemResult` - captures synthesis, votes, expert_summaries per sub-problem
- `sub_problem_results: list[SubProblemResult]` - accumulates across sub-problems

### Current Sequential Flow
```
decompose → [SP1 full deliberation] → [SP2 full deliberation] → [SP3] → meta_synthesis
```

---

## Proposed Architecture

### New Parallel Flow
```
decompose_node
    ↓
analyze_dependencies_node (NEW)
    ↓
┌─────────────────────────────────────────────┐
│ PARALLEL EXECUTION COORDINATOR (NEW)        │
├─────────────────────────────────────────────┤
│                                             │
│  Batch 1 (no deps):    SP1 ──┬── SP2        │
│                              │              │
│  Batch 2 (depends on 1): ────┴── SP3        │
│                                             │
└─────────────────────────────────────────────┘
    ↓
meta_synthesize_node (existing)
```

---

## Implementation Plan

### Phase 1: Decomposer Enhancement
**File**: `bo1/agents/decomposer.py`

Update the decomposer prompt to:
1. Identify dependencies between sub-problems during decomposition
2. Populate the `dependencies` field with sub-problem IDs
3. Return dependency graph as part of decomposition

**Prompt addition**:
```
For each sub-problem, identify if it depends on conclusions from other sub-problems.
- If sub-problem B needs the answer to sub-problem A before it can be properly addressed,
  list A's ID in B's dependencies.
- If sub-problems are independent (can be answered without knowing the others' conclusions),
  leave dependencies empty.

Example:
- "What is our current market position?" - no dependencies (independent research)
- "Should we expand to new markets?" - depends on market position analysis
- "What pricing strategy should we use?" - may depend on market position
```

---

### Phase 2: Dependency Analysis Node
**File**: `bo1/graph/nodes.py`

Add new node: `analyze_dependencies_node`

```python
async def analyze_dependencies_node(state: DeliberationGraphState) -> dict:
    """Analyze sub-problem dependencies and create execution batches.

    Returns:
        execution_batches: list[list[int]] - batches of sub-problem indices
        dependency_graph: dict[str, list[str]] - for visualization
    """
    sub_problems = state["problem"].sub_problems

    # Build dependency graph
    dep_graph = {sp.id: sp.dependencies for sp in sub_problems}

    # Topological sort into batches
    batches = topological_batch_sort(sub_problems)

    return {
        "execution_batches": batches,  # e.g., [[0, 1], [2]] - SP0 & SP1 parallel, then SP2
        "dependency_graph": dep_graph,
    }
```

---

### Phase 3: Parallel Sub-Problem Coordinator
**File**: `bo1/graph/nodes.py`

Add new node: `parallel_subproblems_node`

```python
async def parallel_subproblems_node(state: DeliberationGraphState) -> dict:
    """Execute independent sub-problems in parallel.

    Uses asyncio.gather() to run multiple sub-problem deliberations concurrently.
    Respects dependency ordering via execution_batches.
    """
    batches = state["execution_batches"]
    all_results = []

    for batch in batches:
        # Run all sub-problems in this batch concurrently
        batch_tasks = []
        for sp_index in batch:
            sub_problem = state["problem"].sub_problems[sp_index]
            # Create isolated deliberation task
            task = _deliberate_subproblem(
                sub_problem=sub_problem,
                problem=state["problem"],
                personas=state["personas"],
                previous_results=all_results,  # Pass completed results for context
            )
            batch_tasks.append(task)

        # Execute batch in parallel
        batch_results = await asyncio.gather(*batch_tasks)
        all_results.extend(batch_results)

    return {
        "sub_problem_results": all_results,
        "current_sub_problem": None,  # All complete
    }
```

---

### Phase 4: Sub-Problem Deliberation Function
**File**: `bo1/graph/nodes.py`

Extract current deliberation loop into reusable function:

```python
async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
) -> SubProblemResult:
    """Run complete deliberation for a single sub-problem.

    This encapsulates:
    - Persona selection for this sub-problem
    - Initial round
    - Multi-round deliberation (up to 6 rounds)
    - Voting
    - Synthesis

    Returns SubProblemResult with all outputs.
    """
    # Build expert memory from previous results (if any)
    expert_memory = _build_expert_memory(personas, previous_results)

    # Select personas for this sub-problem
    selected_personas = await _select_personas_for_subproblem(sub_problem, personas)

    # Run deliberation rounds
    contributions = []
    for round_num in range(1, 7):  # Max 6 rounds
        round_contributions = await _generate_parallel_contributions(
            experts=selected_personas,
            sub_problem=sub_problem,
            round_number=round_num,
            previous_contributions=contributions,
            expert_memory=expert_memory,
        )
        contributions.extend(round_contributions)

        # Check convergence
        if await _check_convergence(contributions, round_num):
            break

    # Collect votes/recommendations
    votes = await _collect_recommendations(selected_personas, contributions, sub_problem)

    # Generate synthesis
    synthesis = await _synthesize_subproblem(sub_problem, contributions, votes)

    return SubProblemResult(
        sub_problem_id=sub_problem.id,
        sub_problem_goal=sub_problem.goal,
        synthesis=synthesis,
        votes=votes,
        contribution_count=len(contributions),
        expert_panel=[p.code for p in selected_personas],
        expert_summaries=_extract_expert_summaries(contributions, selected_personas),
    )
```

---

### Phase 5: Graph Reconfiguration
**File**: `bo1/graph/config.py`

Update graph to support parallel execution:

```python
# Add new nodes
workflow.add_node("analyze_dependencies", analyze_dependencies_node)
workflow.add_node("parallel_subproblems", parallel_subproblems_node)

# New edges for parallel path
workflow.add_edge("decompose", "analyze_dependencies")
workflow.add_conditional_edges(
    "analyze_dependencies",
    route_subproblem_execution,  # NEW: decides parallel vs sequential
    {
        "parallel": "parallel_subproblems",
        "sequential": "select_personas",  # Fallback to current flow
    }
)
workflow.add_edge("parallel_subproblems", "meta_synthesize")
```

---

### Phase 6: Feature Flag
**File**: `bo1/feature_flags/features.py`

```python
# Enable parallel sub-problem execution
# When False, falls back to sequential execution (current behavior)
ENABLE_PARALLEL_SUBPROBLEMS: bool = os.getenv(
    "ENABLE_PARALLEL_SUBPROBLEMS", "true"
).lower() in ("true", "1", "yes")
```

---

### Phase 7: Event Streaming Updates
**File**: `backend/api/event_collector.py`

Update event handlers to support parallel sub-problem events:

```python
# New event types
"parallel_batch_started": {"batch_index": 0, "sub_problems": ["sp_001", "sp_002"]}
"subproblem_started": {"sub_problem_id": "sp_001", "parallel": True}
"subproblem_completed": {"sub_problem_id": "sp_001", "duration": 45.2}
"parallel_batch_completed": {"batch_index": 0, "results": [...]}
```

---

## Dependency Handling

### Topological Batch Sort Algorithm

```python
def topological_batch_sort(sub_problems: list[SubProblem]) -> list[list[int]]:
    """Sort sub-problems into execution batches respecting dependencies.

    Returns list of batches, where each batch contains indices of
    sub-problems that can run in parallel.

    Example:
        sub_problems = [
            SubProblem(id="sp_001", dependencies=[]),           # Independent
            SubProblem(id="sp_002", dependencies=[]),           # Independent
            SubProblem(id="sp_003", dependencies=["sp_001"]),   # Depends on sp_001
        ]

        Returns: [[0, 1], [2]]
        # Batch 1: sp_001 and sp_002 run in parallel
        # Batch 2: sp_003 runs after batch 1 completes
    """
    # Build ID to index mapping
    id_to_idx = {sp.id: i for i, sp in enumerate(sub_problems)}

    # Track in-degree (number of unresolved dependencies)
    in_degree = [len(sp.dependencies) for sp in sub_problems]

    batches = []
    remaining = set(range(len(sub_problems)))

    while remaining:
        # Find all sub-problems with no unresolved dependencies
        batch = [i for i in remaining if in_degree[i] == 0]

        if not batch:
            raise ValueError("Circular dependency detected in sub-problems")

        batches.append(batch)

        # Remove completed sub-problems and update in-degrees
        for idx in batch:
            remaining.remove(idx)
            sp_id = sub_problems[idx].id
            # Decrement in-degree for dependents
            for other_idx in remaining:
                if sp_id in sub_problems[other_idx].dependencies:
                    in_degree[other_idx] -= 1

    return batches
```

---

## Expert Memory Across Parallel Sub-Problems

### Challenge
In sequential execution, experts have memory of their positions from previous sub-problems. In parallel execution, sub-problems in the same batch can't reference each other.

### Solution
1. **Within-batch**: No cross-memory (sub-problems are independent by definition)
2. **Across-batches**: Pass completed `SubProblemResult.expert_summaries` to next batch

```python
async def _deliberate_subproblem(..., previous_results: list[SubProblemResult]):
    # Build memory only from COMPLETED batches
    expert_memory = {}
    for result in previous_results:
        for expert_code, summary in result.expert_summaries.items():
            if expert_code not in expert_memory:
                expert_memory[expert_code] = []
            expert_memory[expert_code].append({
                "sub_problem": result.sub_problem_goal,
                "position": summary,
            })

    # Pass to persona contributions
    ...
```

---

## Cost & Resource Management

### Parallel Execution Limits
```python
# Limit concurrent sub-problems to avoid rate limits
MAX_PARALLEL_SUBPROBLEMS = 3  # Anthropic rate limits

# Within each parallel sub-problem, experts still run in parallel
# So 3 sub-problems × 5 experts = 15 concurrent API calls max
```

### Cost Tracking
```python
# Track costs per sub-problem
sub_problem_costs = {}

async def _deliberate_subproblem(...) -> SubProblemResult:
    cost_tracker = CostTracker()
    # ... deliberation ...
    return SubProblemResult(
        ...,
        cost=cost_tracker.total_cost,
    )
```

---

## Testing Strategy

### Unit Tests
1. `test_topological_batch_sort()` - dependency graph sorting
2. `test_circular_dependency_detection()` - error handling
3. `test_independent_subproblems_single_batch()` - all parallel case
4. `test_dependent_subproblems_multiple_batches()` - mixed case

### Integration Tests
1. `test_parallel_subproblem_execution()` - end-to-end with mocked LLM
2. `test_expert_memory_across_batches()` - memory propagation
3. `test_fallback_to_sequential()` - feature flag disabled

### Performance Tests
1. Compare execution time: parallel vs sequential (same problem)
2. Verify no race conditions in state updates
3. Verify event ordering in parallel mode

---

## Migration & Rollback

### Feature Flag Rollback
```python
if not ENABLE_PARALLEL_SUBPROBLEMS:
    # Route to existing sequential flow
    return "sequential"
```

### Gradual Rollout
1. Deploy with flag disabled (default: sequential)
2. Enable for internal testing
3. Enable for beta users
4. Enable globally

---

## Files to Modify

| File | Changes |
|------|---------|
| `bo1/agents/decomposer.py` | Update prompt to identify dependencies |
| `bo1/graph/nodes.py` | Add `analyze_dependencies_node`, `parallel_subproblems_node`, `_deliberate_subproblem()` |
| `bo1/graph/config.py` | Add new nodes and conditional edges |
| `bo1/graph/routers.py` | Add `route_subproblem_execution()` |
| `bo1/feature_flags/features.py` | Add `ENABLE_PARALLEL_SUBPROBLEMS` |
| `backend/api/event_collector.py` | Handle parallel sub-problem events |
| `bo1/models/problem.py` | (No changes - `dependencies` field exists) |

---

## Estimated Effort

- Phase 1 (Decomposer): 1-2 hours
- Phase 2 (Dependency Analysis): 1 hour
- Phase 3-4 (Parallel Coordinator): 3-4 hours
- Phase 5 (Graph Config): 1 hour
- Phase 6 (Feature Flag): 15 minutes
- Phase 7 (Events): 1-2 hours
- Testing: 2-3 hours

**Total: ~10-12 hours**

---

## Expected Impact

- **Time reduction**: 50-70% for problems with 2+ independent sub-problems
- **Cost**: Same or slightly lower (no duplicate context loading)
- **Quality**: Same (each sub-problem gets full deliberation)
- **User experience**: Faster results, parallel progress indicators
