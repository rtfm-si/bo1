# Architecture Flow Audit Report

**Date:** 2025-12-22
**Scope:** LangGraph topology, state transitions, inter-service communication, event propagation
**Files Analyzed:** bo1/graph/config.py, bo1/graph/state.py, bo1/graph/nodes/, bo1/orchestration/, backend/api/event_collector.py, backend/api/streaming.py

---

## 1. Flow Diagram (Text-Based)

```
Entry Point: context_collection
    ↓
decompose → identify_gaps → [clarification_needed → END | continue]
    ↓ (if continue)
[PARALLEL_SUBPROBLEMS enabled?]
    Yes → analyze_dependencies → [parallel_subproblems → meta_synthesis → END]
    No → select_personas ↓
    ↓
initial_round → facilitator_decide
    ↓
[facilitator decision routing]
    ├─ continue → parallel_round → cost_guard → check_convergence
    │                                              ↓
    │                                         [converged?]
    │                                              ├─ No → facilitator_decide (loop)
    │                                              └─ Yes → vote
    ├─ vote → synthesize → [next_subproblem | meta_synthesis | END]
    ├─ research → parallel_round
    ├─ moderator_intervene → cost_guard → check_convergence
    ├─ clarify → [answered → parallel_round | paused → END]
    └─ analyze_data → parallel_round

State Checkpointing: RedisSaver (production) | MemorySaver (tests)
Event Pipeline: Node → EventCollector → Redis PubSub → SSE stream → Frontend
```

---

## 2. State Transitions (Validation Status)

### Core Transition Flow

| Transition | Validation | Status |
|-----------|-----------|---------|
| `context_collection` → `decompose` | Edge defined (line 156) | ✅ Valid |
| `decompose` → `identify_gaps` | Edge defined (line 159) | ✅ Valid |
| `identify_gaps` → `END` or `analyze_dependencies`/`select_personas` | Conditional router (lines 173-203) | ✅ Valid |
| `select_personas` → `initial_round` | Edge defined (line 206) | ✅ Valid |
| `initial_round` → `facilitator_decide` | Edge defined (line 209) | ✅ Valid |
| `facilitator_decide` → 6 destinations | Conditional router (lines 213-225) | ✅ Valid |
| `parallel_round` → `cost_guard` → `check_convergence` | Edge chain (lines 244-257) | ✅ Valid |
| `check_convergence` → `facilitator_decide` or `vote` | Conditional router (lines 260-267) | ✅ Valid |
| `vote` → `synthesize` → `END`/`next_subproblem`/`meta_synthesis` | Edge + conditional router (lines 270-288) | ✅ Valid |

### Parallel Sub-Problem Execution (Feature Flag)

| Transition | Validation | Status |
|-----------|-----------|---------|
| `analyze_dependencies` → `parallel_subproblems` or `select_personas` | Conditional router (lines 184-190) | ✅ Valid |
| `parallel_subproblems` → `meta_synthesis` | Edge defined (line 193) | ✅ Valid |

### Edge Cases

| Scenario | Handling | Status |
|----------|----------|--------|
| Clarification needed | `identify_gaps` → `END`, resumes via checkpoint update | ✅ Valid |
| Context insufficient | `check_convergence` emits event, pauses (line 826-866 event_collector.py) | ✅ Valid |
| Cost budget exceeded | `cost_guard` routes to `vote` (forced synthesis) | ✅ Valid |
| Max rounds exceeded | `check_convergence` stops deliberation | ✅ Valid |
| Sub-problem failure | `route_after_synthesis` validates all results before meta-synthesis (lines 229-280 routers.py) | ✅ Valid |

---

## 3. Identified Bottlenecks and Circular Dependencies

### Bottlenecks

1. **Sequential persona execution in `initial_round_node`**
   - Location: `bo1/orchestration/persona_executor.py`
   - Pattern: Each LLM call waits for previous completion (no parallelism)
   - Impact: ~3-5 personas × ~2s/call = 6-10s blocking time (slowest phase)
   - Mitigation: Parallel execution in `parallel_round_node` for subsequent rounds

2. **Recommendation collection serial-then-parallel pattern**
   - Location: `bo1/orchestration/voting.py` lines 137-148
   - Pattern: First persona creates prompt cache sequentially, remaining hit cache in parallel
   - Impact: First recommendation adds ~2s overhead before parallel batch
   - Rationale: Cache optimization saves 90% cost on remaining calls (worth the delay)

3. **Event persistence flush delay**
   - Location: `backend/api/event_collector.py` line 1480
   - Pattern: Events batched in Redis, flushed asynchronously to PostgreSQL
   - Impact: `_verify_event_persistence` waits 5s for flush completion
   - Mitigation: Deterministic flush tracking implemented (lines 1478-1485)

### Circular Dependencies

**None detected.** All conditional edges have terminal paths.

Validation:
- Max recursion limit: 20 (DELIBERATION_RECURSION_LIMIT)
- Max rounds cap: 6 for parallel architecture (state.py line 414-417)
- Cost guard force-synthesis route (config.py lines 249-257)

---

## 4. Inter-Service Communication Patterns

### API ↔ Graph Flow

1. **Initiation:** FastAPI `/start` endpoint → `create_deliberation_graph()` → `graph.ainvoke()`
2. **Event streaming:** Graph nodes update state → LangGraph checkpoint → EventCollector.collect_and_publish()
3. **Event extraction:** EventCollector._dispatch_node_handler() → event_extractors.extract() → Redis PubSub publish
4. **SSE delivery:** Redis PubSub → streaming.py stream_session_events() → Frontend

**Key Pattern:** Event-driven, asynchronous via Redis PubSub (decouples graph execution from client connections)

### Graph ↔ LLM Flow

1. **Prompt routing:** Node → PromptBroker.call() → model selection via get_model_for_phase()
2. **Response handling:** ClaudeClient → ResponseParser → ContributionMessage
3. **Cost tracking:** LLMResponse.token_usage → CostTracker.track() → buffered write to PostgreSQL

**Key Pattern:** PromptBroker centralizes retry/timeout logic, ResponseParser handles XML extraction

### Event Propagation Pipeline

1. **Node completion:** LangGraph fires `on_chain_end` event with node output
2. **Handler dispatch:** EventCollector.NODE_HANDLERS registry maps node_name → handler method (event_collector.py lines 71-92)
3. **Event extraction:** EventExtractorRegistry.extract() pulls relevant fields from state
4. **SSE formatting:** format_sse_for_type() → Redis PubSub → streaming.py yields SSE strings

**Optimization:** Batch summarization in parallel (event_collector.py lines 690-711, reduces LLM calls)

---

## 5. Recommendations

1. **Parallelize initial_round_node persona execution**
   - Current: Sequential execution blocks for 6-10s (largest UX gap)
   - Proposal: Apply parallel pattern from `parallel_round_node` to initial round
   - Expected gain: 60-70% reduction in initial round latency (3-4s vs 10s)

2. **Add state transition visibility to SSE stream**
   - Current: Clients infer state from event types (brittle)
   - Proposal: Emit explicit `state_transition` events with from/to node names
   - Benefit: Enables client-side progress visualization, simplifies debugging

3. **Implement graph execution timeout**
   - Current: No top-level timeout (relies on recursion limit + cost guard)
   - Proposal: Add configurable wall-clock timeout in `collect_and_publish()` (default 10 min)
   - Benefit: Prevents runaway sessions from blocking resources

4. **Consolidate router validation logic**
   - Current: Routers duplicate validation (e.g., `route_after_synthesis` lines 200-204, `route_facilitator_decision` lines 101-109)
   - Proposal: Extract shared validation helpers (e.g., `validate_state_has_field()`)
   - Benefit: Reduces error-prone duplication, improves maintainability

5. **Add circuit breaker for Redis PubSub failures**
   - Current: SSE streaming fails if Redis connection drops (streaming.py line 401)
   - Proposal: Fallback to PostgreSQL-based polling with exponential backoff
   - Benefit: Graceful degradation during Redis outages

---

## Validation Summary

- **State transitions:** All edges and routers validated against config.py topology
- **Bottlenecks:** 3 identified (sequential initial round, cache warmup delay, flush wait) - all have mitigation
- **Circular dependencies:** None (max_rounds and recursion_limit prevent infinite loops)
- **Inter-service communication:** Event-driven architecture with proper decoupling
- **Recommendations:** 5 actionable improvements prioritized by impact

**Overall Status:** ✅ Architecture flow is sound with identified optimization opportunities
