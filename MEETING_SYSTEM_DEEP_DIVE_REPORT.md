# Meeting System Deep Dive Test Report

**Date:** 2025-12-06
**Test Duration:** ~20 minutes
**Test Executor:** Claude Code (automated via API)

---

## Executive Summary

This deep-dive test uncovered a **critical P0 bug** that blocks all meeting sessions requiring clarification. The resume-from-checkpoint flow fails due to missing state initialization. Additionally, significant performance concerns were identified with LLM response times.

### Critical Findings

| Priority | Issue | Impact |
|----------|-------|--------|
| **P0** | Resume after clarification fails with "No current sub-problem in state" | 100% of clarification flows blocked |
| **P1** | Extremely slow LLM decomposition call (92 seconds) | Poor UX, potential timeouts |
| **P2** | Clarification always triggers regardless of context provided | Adds unnecessary friction |

---

## Test Execution Summary

### Session 1: `bo1_226ceb04-9dc2-46b3-a39d-49b67f6ed018`

**Problem Statement:** "Should our startup pivot from B2B to B2C, or pursue a hybrid model? We have 18 months runway, 500 B2B customers, and see 10x larger B2C market opportunity but would need to rebuild our sales motion."

**Flow:**
1. Session created successfully
2. Decomposition: 3 sub-problems generated (21.9s, $0.0150)
3. Complexity assessment: 0.79 complexity, 6 rounds, 5 experts recommended (6.7s, $0.0061)
4. Information gap analysis: 5 internal gaps (3 critical), 2 external gaps (8.0s, $0.0044)
5. **Paused for clarification** (3 critical questions)
6. User provided clarification answers via API
7. **Resume FAILED** with `ValueError: No current sub-problem in state`

### Session 2: `bo1_eb912da3-f03d-4171-a54b-9ec75d65c883`

**Problem Statement:** "What marketing strategy should we use for our mobile app launch?"
**Context Provided:** Company name, business model, target market, product description, business stage, industry, revenue, customers, team size, budget

**Flow:**
1. Session created successfully
2. Decomposition: 3 sub-problems generated (**92.1s** - extremely slow!, $0.0160)
3. Complexity assessment: 0.58 complexity, 5 rounds, 4 experts recommended (6.7s, $0.0062)
4. Information gap analysis: 4 internal gaps (2 critical), 2 external gaps (6.1s, $0.0034)
5. **Paused for clarification** (2 critical questions) - despite providing context!
6. User skipped clarification via API
7. **Resume FAILED** with same `ValueError: No current sub-problem in state`

---

## Bug Analysis

### P0 Bug: Resume After Clarification Fails

**Error:**
```
ValueError: No current sub-problem in state
  File "bo1/graph/nodes/selection.py", line 40, in select_personas_node
    raise ValueError("No current sub-problem in state")
```

**Root Cause Analysis:**

1. The graph flow when `ENABLE_PARALLEL_SUBPROBLEMS=false` is:
   ```
   identify_gaps → route_after_identify_gaps → select_personas
   ```

2. `select_personas_node` (selection.py:38-40) requires `current_sub_problem` to be set:
   ```python
   current_sp = state["current_sub_problem"]
   if not current_sp:
       raise ValueError("No current sub-problem in state")
   ```

3. In the **normal flow**, `current_sub_problem` is set by:
   - `analyze_dependencies_node` when `ENABLE_PARALLEL_SUBPROBLEMS=true` (subproblems.py:90-107, 130-147)
   - `next_subproblem_node` for subsequent sub-problems

4. **THE BUG:** When `ENABLE_PARALLEL_SUBPROBLEMS=false` (config.py:221-228), after resuming from clarification, the router goes directly to `select_personas` **without any node setting `current_sub_problem`**.

**Location:** `bo1/graph/config.py:221-228`

**Fix Required:** Either:
- Option A: Have `identify_gaps_node` set `current_sub_problem` to the first sub-problem when routing to `select_personas`
- Option B: Add an intermediate node between `identify_gaps` and `select_personas` that initializes `current_sub_problem`
- Option C: Route through `analyze_dependencies_node` even when `ENABLE_PARALLEL_SUBPROBLEMS=false`

**Affected Files:**
- `bo1/graph/nodes/context.py` (identify_gaps_node)
- `bo1/graph/config.py` (routing logic)

---

## Performance Analysis

### LLM Call Timing

| Phase | Duration | Cost | Model | Tokens |
|-------|----------|------|-------|--------|
| Decomposition (Session 1) | 21.9s | $0.0150 | claude-haiku-4-5 | 6,778 |
| Decomposition (Session 2) | **92.1s** | $0.0160 | claude-haiku-4-5 | 7,027 |
| Complexity Assessment | 6.7s | $0.0062 | claude-haiku-4-5 | 4,196 |
| Information Gap Analysis | 6-8s | $0.0034-$0.0044 | claude-haiku-4-5 | 1,244-1,404 |

**Performance Concern:** The 92.1s decomposition call is extremely slow for Haiku. This is 4x longer than the similar Session 1 decomposition. Possible causes:
- API rate limiting or throttling
- Network latency issues
- Large prompt causing extended processing

### Dead Time Analysis

- Session creation to start: ~0.5s (acceptable)
- LLM calls dominate the time budget
- No obvious dead time between operations

### Prompt Quality Scoring (1-10)

| Prompt Type | Score | Notes |
|-------------|-------|-------|
| Decomposition | **8/10** | Generated relevant sub-problems. Good structure with dependencies. |
| Complexity Assessment | **7/10** | Reasonable complexity scores. Could benefit from more nuanced analysis. |
| Information Gap Analysis | **6/10** | Too aggressive - finds "critical" gaps even with comprehensive context provided. |
| Clarification Questions | **9/10** | Questions are specific, actionable, and prioritized correctly. |

### Response Quality Scoring (1-10)

| Response Type | Score | Notes |
|---------------|-------|-------|
| Sub-problems | **8/10** | Well-structured, appropriate scope, good dependency mapping. |
| Complexity Score | **7/10** | Consistent with problem characteristics. |
| Gap Analysis | **5/10** | Over-sensitive - identified "critical" gaps despite rich context. |

---

## Graph Flow Analysis

### Observed Node Sequence

```
context_collection_node (Complete)
    ↓
decompose_node (3 sub-problems generated)
    ↓
identify_gaps_node (Found critical gaps)
    ↓
route_after_identify_gaps → END (Paused for clarification)
    ↓
[User provides clarification / skips]
    ↓
RESUME → select_personas_node → CRASH
```

### Expected Node Sequence (Fix Required)

```
context_collection_node
    ↓
decompose_node
    ↓
identify_gaps_node [SET current_sub_problem HERE]
    ↓
route_after_identify_gaps → select_personas
    ↓
initial_round_node
    ↓
[Rest of deliberation...]
```

---

## SSE Events Captured

Session 1 SSE events received before failure:
1. `node_start` - stream_connected
2. `working_status` - "Breaking down your decision into key areas..."
3. `discussion_quality_status` - "Analyzing problem structure..."
4. `decomposition_complete` - 3 sub-problems
5. `clarification_required` - 3 critical questions

**Event Quality:** Good real-time feedback during decomposition phase. However, no events after resume attempt (crash happened too fast).

---

## Recommendations

### Immediate (P0)

1. **Fix the `current_sub_problem` initialization bug**
   - Modify `identify_gaps_node` to set `current_sub_problem` to `problem.sub_problems[0]` before returning
   - Or route through `analyze_dependencies_node` even in non-parallel mode

### Short-term (P1)

2. **Investigate LLM latency spikes**
   - Add latency monitoring/alerting for calls >30s
   - Consider retry logic for slow calls
   - Check if prompt caching is working correctly

3. **Tune information gap sensitivity**
   - Current threshold finds "critical" gaps even with comprehensive context
   - Consider reducing sensitivity or making it configurable
   - Allow users to pre-set their tolerance for context gaps

### Medium-term (P2)

4. **Add integration tests for resume flows**
   - Test clarification → resume path
   - Test skip clarification → resume path
   - Ensure `current_sub_problem` is always set before `select_personas`

5. **Performance monitoring**
   - Track LLM call durations over time
   - Alert on p95 latency spikes
   - Implement budget alerts per session

---

## Test Artifacts

| Artifact | Location |
|----------|----------|
| SSE Events (Session 1) | `/tmp/sse_events.txt` |
| SSE Events (Session 2) | `/tmp/sse_events2.txt` |
| API Logs | Docker logs `bo1-api` |

---

## Conclusion

The meeting system has a **critical blocking bug** in the clarification resume flow that must be fixed before production use. Every session that triggers clarification (which appears to be most sessions) will fail when resumed.

Secondary concerns around LLM latency and over-sensitive gap detection should be addressed after the P0 fix.

**Estimated Fix Time:** 1-2 hours for P0 bug, pending understanding of intended behavior around `current_sub_problem` lifecycle.

---

*Report generated by Claude Code deep-dive test automation*
