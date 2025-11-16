# Sub-Problem Decomposition Status Report

**Date**: 2025-01-16
**Analyzed By**: Claude Code (Sonnet 4.5)
**Status**: CRITICAL GAP IDENTIFIED ⚠️

---

## Executive Summary

**Finding**: Board of One currently only deliberates on the **first sub-problem** after decomposition. Sub-problems 2-5 are decomposed but never deliberated on.

**Impact**: HIGH - Users creating complex problems with multiple sub-problems receive incomplete deliberations.

**Recommendation**: Implement multi-sub-problem iteration (Day 36.5) before Web API launch (Week 6).

---

## Current Implementation Analysis

### ✅ What Works Well

1. **Decomposition Quality Control**
   - Max 5 sub-problems enforced (`DecomposerAgent.validate_decomposition()`)
   - File: `bo1/agents/decomposer.py:296-297`
   ```python
   if len(sub_problems) > 5:
       errors.append(f"Too many sub-problems: {len(sub_problems)} (max 5)")
   ```

2. **Dependency Modeling**
   - `SubProblem.dependencies: list[str]` field exists
   - Dependencies validated (must reference valid sub-problem IDs)
   - File: `bo1/models/problem.py:60-63`

3. **Complexity Scoring**
   - 1-10 scale implemented and validated
   - Decomposer prompt provides detailed guidelines

4. **Per-Sub-Problem Expert Selection**
   - `PersonaSelectorAgent.recommend_personas(sub_problem=...)`
   - Designed to select different expert panels per sub-problem

### ❌ Critical Gaps

1. **Only First Sub-Problem Deliberated**
   - **Location**: `bo1/graph/nodes.py:149`
   ```python
   return {
       "current_sub_problem": sub_problems[0] if sub_problems else None,
       # ...
   }
   ```
   - No iteration logic to move to `sub_problems[1]`, `[2]`, etc.
   - Synthesis happens after ONLY the first sub-problem

2. **Dependencies Modeled But Not Executed**
   - Dependencies are validated but never consulted during execution
   - No logic to enforce "sp_002 waits for sp_001 if dependency exists"

3. **No Cross-Sub-Problem Meta-Synthesis**
   - Current synthesis uses contributions from ONE sub-problem only
   - No "meta-synthesis" to integrate insights across all sub-problems

4. **No Multi-Sub-Problem Progress Tracking**
   - No tracking of which sub-problems are complete/in-progress/pending
   - Cannot display "Sub-problem 2 of 4" to user

5. **HITL Not Per-Sub-Problem**
   - Context collection happens once (pre-decomposition)
   - Clarifications happen during deliberation but not targeted per sub-problem

---

## User Request Analysis

### Requirements Checklist

| Requirement | Current Status | Plan |
|-------------|---------------|------|
| Control sub-problem count (not 100) | ✅ Max 5 enforced | No change needed |
| Parallel vs Sequential execution | ❌ Not implemented | Phase 2 (Week 7-8, Web UI) |
| Dependency-aware execution | ❌ Dependencies ignored | Phase 2 (Week 7-8, Web UI) |
| User input per sub-problem | ⚠️ Partial (clarifications) | Phase 3 (Week 8-9, Web UI) |
| Different expert panels per sub-problem | ✅ Designed, ❌ Only runs once | Phase 1 (Day 36.5, Console) |
| All sub-problems in final synthesis | ❌ Only first | Phase 1 (Day 36.5, Console) |

---

## Proposed Solution

### Phase 1: Sequential Execution (Day 36.5 - Console)

**Goal**: Deliberate ALL sub-problems sequentially, one at a time.

**Implementation**:
1. Add `next_subproblem_node()` - Iterates through sub-problems
2. Add `meta_synthesize_node()` - Integrates all sub-problem syntheses
3. Add `route_after_synthesis()` - Routes to next sub-problem or meta-synthesis
4. Update console display - Show "Sub-problem 2 of 4" progress
5. Track results - `SubProblemResult` model stores each deliberation

**Example User Flow**:
```
Problem: "Should I invest $50K in SEO or paid ads?"

Decompose → 3 sub-problems:
  1. CAC targets and payback period
  2. Channel fit for target customer
  3. Execution capacity constraints

Deliberate Sub-Problem 1 → Synthesis 1
  ↓
Deliberate Sub-Problem 2 → Synthesis 2
  ↓
Deliberate Sub-Problem 3 → Synthesis 3
  ↓
Meta-Synthesis (integrates all 3) → Final Recommendation
```

**Console Output**:
```
═══ Sub-Problem 1 of 3 ═══
CAC targets and payback period

[Deliberation happens...]

✓ Sub-problem 1 complete
Cost: $0.12 | Duration: 45s
Expert panel: Maria (Finance), Chen (Analytics)

═══ Sub-Problem 2 of 3 ═══
Channel fit for target customer

[Deliberation happens...]

✓ Sub-problem 2 complete
Cost: $0.14 | Duration: 52s
Expert panel: Tariq (Marketing), Nina (Customer Research)

═══ Sub-Problem 3 of 3 ═══
Execution capacity constraints

[Deliberation happens...]

✓ Sub-problem 3 complete
Cost: $0.11 | Duration: 38s
Expert panel: Yuki (Operations), Zara (Time Management)

═══ Cross-Sub-Problem Meta-Synthesis ═══
Integrating insights from 3 deliberations...

[Meta-synthesis report:]

Executive Summary:
Invest $30K in paid ads (LinkedIn + Google) for immediate wins,
then layer in $20K SEO investment starting Month 4.

Sub-Problem Insights:
1. CAC Analysis: Target CAC <$150, payback <6 months achievable with paid
2. Channel Fit: LinkedIn works best for B2B SaaS (your target market)
3. Execution: Solo founder → paid ads easier to execute than SEO content

Unified Action Plan:
1. Month 1-3: Paid ads ($30K) - hire freelance ads manager
2. Month 4-6: SEO foundation ($10K) - technical SEO, content calendar
3. Month 7-12: Scale both ($10K) - based on CAC performance

Total Cost: $0.42 | Total Duration: 2m 15s
```

### Phase 2: Dependency-Aware Parallel (Week 7-8 - Web UI)

**Goal**: Respect dependencies, enable parallel execution of independent sub-problems.

**Example Dependency Graph**:
```
sp_001 (CAC targets) ──────────┐
                               ↓
                           sp_002 (Channel selection)
                               ↓
sp_003 (Budget allocation) ────┘
                               ↓
                           sp_004 (Implementation plan)
```

**User notes**: This requires web UI because:
- Need non-blocking HITL (user can answer clarifications asynchronously)
- Need dependency graph visualization
- Console is sequential-only by design (blocking HITL is acceptable)

### Phase 3: Per-Sub-Problem HITL (Week 8-9 - Web UI)

**Goal**: Collect context/clarifications specific to each sub-problem.

**Example**:
- Sub-problem 1 (CAC): "What's your current monthly revenue?"
- Sub-problem 2 (Channel): "What's your target customer's job title?"
- Sub-problem 3 (Execution): "How many hours/week can you dedicate to marketing?"

---

## Roadmap Updates

### Day 36.5: Multi-Sub-Problem Iteration (NEW)

**Added to roadmap** at: `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md:1588-1767`

**Tasks**: 68 tasks (unit tests, integration tests, e2e tests, implementation)

**Deliverables**:
- `bo1/graph/nodes.py` - `next_subproblem_node()`, `meta_synthesize_node()`
- `bo1/graph/routers.py` - `route_after_synthesis()`
- `bo1/prompts/reusable_prompts.py` - `META_SYNTHESIS_PROMPT_TEMPLATE`
- `bo1/models/state.py` - `SubProblemResult` model
- Tests: Unit, integration, end-to-end

**Validation Criteria**:
- [ ] 2-5 sub-problems deliberated sequentially
- [ ] Each sub-problem gets different expert panel
- [ ] Meta-synthesis integrates all sub-problems
- [ ] Cost tracked per sub-problem
- [ ] Console shows clear progress
- [ ] Pause/resume works across sub-problems
- [ ] Atomic problems (1 sub-problem) skip meta-synthesis

---

## Testing Strategy

### End-to-End Scenario: Growth Investment

**Problem**: "Should I invest $50K in SEO or paid ads?"

**Expected Decomposition**: 3 sub-problems
1. CAC targets and payback period (finance experts)
2. Channel fit for target customer (marketing experts)
3. Execution capacity constraints (operations experts)

**Expected Behavior**:
- 3 separate deliberations with different expert panels
- Meta-synthesis addresses integration ("Start with paid ads, layer in SEO")
- Total cost <$0.50 (3 × ~$0.12 + meta-synthesis ~$0.05)

**Test File**: `tests/e2e/test_growth_investment_scenario.py`

---

## Cost Analysis

### Current (Broken) Behavior
- 1 sub-problem deliberated
- Cost: ~$0.12 per deliberation
- **User Problem**: Incomplete recommendations (only 1/3 of problem addressed)

### Fixed Behavior (Phase 1)
- All sub-problems deliberated sequentially
- Cost per sub-problem: ~$0.12
- Meta-synthesis cost: ~$0.05
- **Total**: 3 × $0.12 + $0.05 = **$0.41 per multi-sub-problem session**
- **User Benefit**: Complete recommendations across all sub-problems

### Fixed Behavior with Caching (Phase 1 + Research Cache)
- Sub-problem 1: ~$0.12 (no cache hits)
- Sub-problem 2: ~$0.08 (70% cache hit on research)
- Sub-problem 3: ~$0.06 (85% cache hit - similar questions)
- Meta-synthesis: ~$0.05
- **Total**: **$0.31 per session** (24% savings from research cache)

---

## References

### Specification Documents
- **Full Specification**: `zzz_project/detail/MULTI_SUBPROBLEM_DELIBERATION.md`
- **Roadmap Updates**: `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` (Day 36.5)

### Key Files Analyzed
- `bo1/models/problem.py` - SubProblem, Problem models
- `bo1/agents/decomposer.py` - Decomposition logic, validation
- `bo1/prompts/decomposer_prompts.py` - Decomposition prompt (1-5 guideline)
- `bo1/graph/nodes.py` - Node implementations (decompose, select_personas, synthesis)
- `bo1/graph/state.py` - DeliberationGraphState definition
- `bo1/graph/routers.py` - Routing logic

### Implementation Locations
- Decomposition: `bo1/agents/decomposer.py:118-228`
- Validation: `bo1/agents/decomposer.py:272-326`
- Current sub-problem assignment: `bo1/graph/nodes.py:149`
- Synthesis (single sub-problem): `bo1/graph/nodes.py:605-707`

---

## Next Steps

### Immediate (Before Day 36.5)
1. Review this report
2. Confirm approach (sequential → Phase 1, parallel → Phase 2)
3. Decide: Implement Day 36.5 before or after Web API Day 36?

### Recommendation
**Implement Day 36.5 BEFORE Web API Day 36** because:
- Core deliberation logic fix (not web-specific)
- Console users benefit immediately
- Web API will inherit fixed behavior
- Testing is easier without web API complexity

### Alternative
**Implement Day 36.5 AFTER Web API Day 42** if:
- Web API launch is higher priority
- Can tolerate single-sub-problem limitation for 1-2 weeks
- Risk: Web API demos will show incomplete deliberations

---

## Open Questions

1. **Priority**: Should Day 36.5 be implemented before or after Web API (Days 36-42)?
2. **User Notification**: Should we warn users if their problem decomposes into >3 sub-problems?
   - Current: Silent (max 5, validated)
   - Proposed: Display warning "This will run 4 deliberations, costing ~$0.48 total. Continue?"
3. **Atomic Optimization**: Confirm we skip meta-synthesis for 1 sub-problem (atomic)?
   - Proposed: Yes, route directly to END after synthesis if atomic
4. **Cost Caps**: Confirm cost guard applies to TOTAL across all sub-problems (not per-sub-problem)?
   - Proposed: Yes, accumulate in `metrics.total_cost`

---

## Success Criteria

**Phase 1 Complete** when:
- [ ] User can deliberate 2-5 sub-problems sequentially
- [ ] Each sub-problem gets different expert panel
- [ ] Meta-synthesis integrates insights from all sub-problems
- [ ] Cost tracked per sub-problem and displayed
- [ ] Pause/resume works across sub-problems
- [ ] Console shows clear progress ("Sub-problem 2 of 4")
- [ ] All tests pass (unit, integration, e2e)

**Phase 2 Complete** when:
- [ ] Independent sub-problems deliberated in parallel (web only)
- [ ] Dependencies enforced (sp_002 waits for sp_001 if dependency exists)
- [ ] Dependency graph visualized in web UI
- [ ] User can choose sequential vs parallel mode

**Phase 3 Complete** when:
- [ ] Context collection happens per sub-problem (not just once)
- [ ] Clarifications targeted to specific sub-problem
- [ ] User can pause individual sub-problems in parallel execution
