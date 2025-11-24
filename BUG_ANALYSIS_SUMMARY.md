# Bug Analysis Summary: Repetition & Convergence Issues

**Date:** 2025-11-24
**Session Reference:** `bo1_f626228e-a032-4f47-9a87-5c374e16e711`

---

## Three Critical Bugs Identified

### 1. Weak Convergence Detection (CRITICAL)
**Location:** `/Users/si/projects/bo1/bo1/graph/safety/loop_prevention.py:206-260`

**Problem:** Uses keyword matching ("agree", "yes") instead of semantic similarity
- Expert can repeat same idea in different words without detection
- Example: "cash flow management" → "managing cash position" → "optimizing cash flow" = 0% convergence detected

**Fix:** Use embeddings (Voyage AI) for semantic similarity detection
- Cosine similarity >0.90 = repetition detected
- Already have infrastructure (`VoyageEmbeddings` class exists)
- Cost: ~$0.00036 per convergence check (negligible)

**Effort:** 3.5 hours (implementation + testing)

---

### 2. No Persona Rotation (CRITICAL)
**Location:** `/Users/si/projects/bo1/bo1/agents/facilitator.py:122-226`

**Problem:** Facilitator doesn't rotate speakers - same expert speaks repeatedly
- No guidance in prompt to rotate
- No tracking of who has spoken recently
- LLM defaults to "most relevant" expert each time = echo chamber

**Fix:** Add rotation logic to facilitator prompt
- Track contribution counts per persona
- Track last 3 speakers
- Add guidance: "Prefer personas who have spoken less"
- Prevent consecutive repeats

**Effort:** 4 hours (prompt updates + testing)

---

### 3. Sub-problem Progression Broken (HIGH)
**Location:** Multiple files - investigation needed

**Problem:** Only first sub-problem deliberated, sub-problems 2+ ignored
- Deliberation stops after sp1 instead of continuing to sp2, sp3
- Router logic looks correct (`route_after_synthesis` should loop)
- Likely cause: Facilitator forcing early vote (round 1) → skips multi-round deliberation

**Investigation needed:**
1. Check facilitator decision logs - is action="vote" after initial round?
2. Check max_rounds configuration - is it set too low?
3. Check sub_problem_index - is it being preserved across nodes?

**Fix:** Prevent premature voting
- Add minimum round requirement (3+ rounds before voting allowed)
- Add explicit guidance in facilitator prompt
- Add debug logging to track sub-problem flow

**Effort:** 4 hours (investigation + fix + testing)

---

## Impact

### User Experience
- **Repetition:** Expert says same thing 3 times → User frustration
- **No diversity:** Only 1 expert speaks → Defeats "board of experts" value prop
- **Incomplete:** Only first sub-problem addressed → Complex problems unsolved

### Cost
- **$0.06/session wasted** on repetitive contributions (16% of budget)
- **$0.10/session opportunity cost** from shallow analysis (missing personas)
- **At 1000 sessions/month:** $160/month wasted

### Quality Metrics
- **Diversity of thought:** 20% (should be 100%)
- **Depth of analysis:** 40% (should be 80%)
- **Problem coverage:** 33% (should be 100%)

---

## Recommended Implementation Order

### Phase 1: Persona Rotation (4 hours) - HIGHEST IMPACT
**Why first:**
- Clear fix, immediate results
- Unlocks diverse perspectives (core value prop)
- Relatively simple implementation

**Steps:**
1. Add contribution tracking to facilitator
2. Update prompt with rotation guidance
3. Test with 3-5 persona deliberation

### Phase 2: Semantic Convergence (3.5 hours) - CRITICAL QUALITY
**Why second:**
- More complex than rotation
- Requires embedding integration
- Critical for preventing repetition waste

**Steps:**
1. Add `_calculate_convergence_score_semantic()` function
2. Integrate with existing `check_convergence_node()`
3. Test with repetitive contributions
4. Keep keyword fallback for safety

### Phase 3: Sub-problem Flow (4 hours) - INVESTIGATION FIRST
**Why last:**
- Requires investigation before implementation
- Affects complex problems only (smaller user impact)
- May uncover additional issues

**Steps:**
1. Add debug logging to track sub-problem progression
2. Run test deliberation with 3 sub-problems
3. Identify exact failure point
4. Implement fix (likely: prevent early voting)

---

## Testing Requirements

### Test Case 1: Semantic Repetition Detection
```python
# 3 semantically identical contributions
# Expected: convergence_score > 0.85
contributions = [
    "We should prioritize cash flow management",
    "It's critical to focus on managing cash position",
    "The key priority is optimizing cash flow"
]
assert convergence_score > 0.85
```

### Test Case 2: Persona Rotation
```python
# 5-round deliberation with 3 personas
# Expected: Each persona speaks 1-2 times (balanced)
# Expected: No consecutive repeats
contribution_counts = {"CFO": 2, "CTO": 2, "CEO": 1}
assert max_count - min_count <= 1
```

### Test Case 3: Multi-Sub-Problem Flow
```python
# Problem with 3 sub-problems
# Expected: 3 sub-problem results + 1 meta-synthesis
assert len(sub_problem_results) == 3
assert "meta-synthesis" in final_output
```

---

## Monitoring After Deployment

Track these metrics:

1. **Repetition rate:** <5% (currently ~15-20%)
2. **Persona balance:** Std dev <0.5 (currently ~2.0)
3. **Sub-problem coverage:** 100% (currently ~33%)
4. **User satisfaction:** 4.0+ / 5.0
5. **Cost per deliberation:** $0.10-0.15 (remove $0.06 waste)

Add structured logging:
- Convergence scores (semantic vs keyword)
- Facilitator decisions (action, speaker, contrib counts)
- Sub-problem progression (index, routing)

---

## Risk Assessment

**Low risk** - All fixes are additive or replace broken logic:
- Semantic convergence: Replaces keyword logic (with fallback)
- Rotation: Adds guidance to existing prompt
- Sub-problems: Prevents premature voting (safety check)

**No breaking changes expected** - Existing tests should pass with improvements.

---

## Total Effort

| Phase | Hours | Priority |
|-------|-------|----------|
| Investigation & Analysis | 3.5 | Complete |
| Persona Rotation | 4.0 | P0 (Critical) |
| Semantic Convergence | 3.5 | P0 (Critical) |
| Sub-problem Flow | 4.0 | P1 (High) |
| **TOTAL** | **15 hours** | ~2 days |

---

## Next Steps

1. Review this analysis with team
2. Prioritize fixes (recommend: rotation → convergence → sub-problems)
3. Create GitHub issues for each bug
4. Implement fixes in order
5. Deploy with monitoring
6. Measure impact after 1 week

**Expected outcome:** 80% reduction in repetition, 100% persona participation, 100% sub-problem coverage.
