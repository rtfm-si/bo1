# Architecture Flow Audit Report

**Date:** 2026-01-03 (Re-audit - no new issues since 2025-12-30)
**Scope:** LangGraph topology, state transitions, inter-service communication, event propagation
**Files Analyzed:** bo1/graph/config.py, bo1/graph/state.py, bo1/graph/routers.py, backend/api/event_collector.py, backend/api/streaming.py

---

## 1. Flow Diagram (Text-Based)

```
Entry Point: context_collection
    ↓
decompose → identify_gaps → [clarification_needed → END | continue]
    ↓ (if continue)
[ENABLE_PARALLEL_SUBPROBLEMS?]
    Yes → analyze_dependencies → [parallel_subproblems → meta_synthesis | select_personas]
    No → select_personas
    ↓
select_personas → initial_round → facilitator_decide
    ↓
[facilitator decision routing]
    ├─ continue → parallel_round → cost_guard → check_convergence
    │                                              ↓
    │                                         [converged?]
    │                                              ├─ No → facilitator_decide (loop)
    │                                              └─ Yes → vote
    ├─ vote → synthesize → [next_subproblem | END (atomic)]
    ├─ research → parallel_round
    ├─ data_analysis → parallel_round
    ├─ moderator_intervene → cost_guard → check_convergence
    └─ clarification → [parallel_round | END]

next_subproblem → [select_personas (more SPs) | meta_synthesis (all done) | END]
meta_synthesis → END

Checkpointing: Redis primary (AsyncRedisSaver), PostgreSQL fallback
Event Pipeline: Node → EventCollector → Redis PubSub → SSE stream → Frontend
```

---

## 2. State Transitions Validation

| Transition | Status | Notes |
|-----------|--------|-------|
| context_collection → decompose | ✅ | Business context flows into decomposition |
| decompose → identify_gaps | ✅ | Gap analysis post-decomposition |
| identify_gaps → END/continue | ✅ | route_after_identify_gaps handles clarification pause |
| select_personas → initial_round | ✅ | Direct edge |
| initial_round → facilitator_decide | ✅ | Direct edge |
| facilitator_decide → 6 destinations | ✅ | route_facilitator_decision with fallback |
| parallel_round → cost_guard | ✅ | Budget check before convergence |
| moderator_intervene → cost_guard | ✅ | Same path as parallel_round |
| cost_guard → check_convergence/vote | ✅ | route_cost_guard handles budget exceeded |
| check_convergence → facilitator_decide/vote | ✅ | route_convergence_check |
| vote → synthesize | ✅ | Direct edge |
| synthesize → next_subproblem/END | ✅ | route_after_synthesis (atomic optimization) |
| next_subproblem → select_personas/meta_synthesis/END | ✅ | route_after_next_subproblem validates results |

**All transitions validated. No orphaned nodes.**

---

## 3. Issues Identified

### ARCH-001: State Bloat (60+ flat fields)
- **Location:** `bo1/graph/state.py` DeliberationGraphState
- **Issue:** Flat TypedDict with 60+ fields; nested accessors exist but aren't used
- **Impact:** Complex serialization, hard to reason about state subsets
- **Severity:** Medium

### ARCH-002: Cross-layer coupling in routers
- **Location:** `bo1/graph/routers.py:305-334` route_after_next_subproblem
- **Issue:** Router imports `get_event_publisher` from `backend.api.dependencies` and publishes `meeting_failed` event directly
- **Impact:** Graph layer depends on API layer; harder to test routers in isolation
- **Severity:** Low

### ARCH-003: Dual event publishing pattern
- **Location:** `backend/api/event_collector.py:1274-1286` _handle_subproblem_complete
- **Issue:** Some nodes publish events internally, EventCollector handlers marked NO-OP to avoid duplicates
- **Impact:** Confusing ownership; requires documentation comments to explain
- **Severity:** Low

### ARCH-004: Feature flag conditional graph topology
- **Location:** `bo1/graph/config.py:83-86, 163-194`
- **Issue:** `ENABLE_PARALLEL_SUBPROBLEMS` changes graph structure at construction time
- **Impact:** Two different graph topologies in production; testing complexity
- **Severity:** Low

### ARCH-005: Large checkpoint serialization
- **Location:** `bo1/graph/state.py:548-633` serialize_state_for_checkpoint
- **Issue:** Serializes 6 Pydantic model types with corruption detection logic
- **Impact:** Checkpoint size grows with contributions; includes repair logic for corrupted data
- **Severity:** Low

---

## 4. Recommendations

1. **Migrate to nested state accessors** - Use `get_problem_state()`, `get_phase_state()` etc. that already exist in state.py
2. **Move event publishing out of routers** - Extract `meeting_failed` event to EventCollector error handler
3. **Document parallel subproblems flag impact** - Add architecture decision record for the two topologies
4. **Consider state pruning before checkpoint** - `prune_contributions_for_phase()` exists but only at synthesis

---

## 5. Bottlenecks

1. **initial_round_node uses `_generate_parallel_contributions`** - Already parallelized (verified in rounds.py)
2. **Event persistence flush** - Deterministic tracking implemented with `wait_for_all_flushes()`
3. **SSE fallback to PostgreSQL polling** - Circuit breaker + polling fallback already implemented

**No critical bottlenecks identified.**

---

## 6. Circular Dependencies

**None detected.** Graph is a proper DAG with:
- Max recursion limit: 20 (DELIBERATION_RECURSION_LIMIT)
- Max rounds: 6 for parallel architecture
- Cost guard force-synthesis route prevents infinite loops

---

**Overall Status:** ✅ Architecture is sound. Minor cleanup opportunities identified.
