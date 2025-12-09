# Architecture Flow Audit Report
**Date:** 2025-12-08

## Flow Diagram (Text-Based)

```
context_collection → decompose → identify_gaps → [conditional]
                                                    ├── END (if clarification_needed)
                                                    └── analyze_dependencies → [conditional]
                                                                                  ├── parallel_subproblems → meta_synthesis → END
                                                                                  └── select_personas → initial_round → facilitator_decide
                                                                                                                           ↓
                                                      ┌──────────────────────────────────────────────────────────────────────┐
                                                      │                   DELIBERATION LOOP                                  │
                                                      │  facilitator_decide → [vote | parallel_round | research |           │
                                                      │                        moderator_intervene | clarification | END]   │
                                                      │  parallel_round → cost_guard → check_convergence →                  │
                                                      │                                [facilitator_decide | vote]           │
                                                      │  vote → synthesize → [next_subproblem | meta_synthesis | END]       │
                                                      └──────────────────────────────────────────────────────────────────────┘
```

## State Transitions Validation

| Transition | Status | Notes |
|------------|--------|-------|
| context_collection → decompose | ✅ Valid | Business context flows before decomposition |
| decompose → identify_gaps | ✅ Valid | Gap analysis post-decomposition |
| identify_gaps → analyze_deps/select_personas | ✅ Valid | Conditional based on ENABLE_PARALLEL_SUBPROBLEMS |
| select_personas → initial_round | ✅ Valid | Linear setup complete |
| initial_round → facilitator_decide | ✅ Valid | Week 5 multi-round loop |
| facilitator_decide → multiple targets | ✅ Valid | Router handles 6 actions |
| parallel_round → cost_guard | ✅ Valid | Budget check before convergence |
| cost_guard → check_convergence/vote | ✅ Valid | Force synthesis if budget exceeded |
| check_convergence → facilitator_decide/vote | ✅ Valid | Loop or terminate |
| synthesize → next_subproblem/meta_synthesis/END | ✅ Valid | Sub-problem routing with validation |

## Identified Issues

### Issue 1: Event Collector Node Handler Gap
**Severity:** Low
**Location:** `backend/api/event_collector.py:45-60`
**Details:** `context_collection` and `analyze_dependencies` nodes have no event handlers in NODE_HANDLERS registry. No SSE events emitted for these phases.
**Impact:** UI shows no feedback during context collection and dependency analysis.

### Issue 2: Clarification Flow Asymmetry
**Severity:** Low
**Location:** `bo1/graph/config.py:251-259`
**Details:** `clarification` node routes to `parallel_round` on continue, but other mid-loop nodes (research, moderator) have different patterns.
**Impact:** Minor inconsistency; works correctly but could confuse future maintainers.

### Issue 3: No Event for Dependency Analysis
**Severity:** Low
**Location:** `bo1/graph/nodes/subproblems.py`
**Details:** When parallel mode is selected, there's no event published for `dependency_analysis_complete`.
**Impact:** UI doesn't know if dependencies were analyzed or which batches will execute.

## Bottlenecks

1. **Contribution Summarization** - Each contribution triggers Haiku call for summary (~100ms each)
2. **Sequential Sub-problem Execution** - When parallel_mode=False, sub-problems run serially
3. **Event Verification Delay** - 2 second sleep in `_verify_event_persistence` adds latency to completion

## Recommendations

1. Add `context_collection` and `analyze_dependencies` event handlers for UI feedback
2. Emit `dependency_analysis_complete` event with execution_batches info
3. Consider batching contribution summarization for rounds with 3-5 experts
4. Remove or make configurable the 2s verification delay for low-latency needs
