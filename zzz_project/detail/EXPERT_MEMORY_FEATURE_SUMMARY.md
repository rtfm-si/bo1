# Cross-Sub-Problem Expert Memory - Feature Summary

**Date**: 2025-01-16
**Feature**: Expert Memory Across Sub-Problems
**Status**: Designed and Integrated into Day 36.5
**Priority**: High (User Request)

---

## Executive Summary

**User Request**: "I think i'd like to bring this feature forward: Expert Reuse - If same expert recommended for multiple sub-problems, do they 'remember' previous sub-problem context?"

**Response**: ✅ **FEATURE INTEGRATED** into Day 36.5 (Multi-Sub-Problem Iteration)

This feature leverages the existing `SummarizerAgent` to create 50-100 token "memory summaries" of each expert's contributions to a sub-problem. When the same expert is selected for subsequent sub-problems, they receive this summary and build on their previous analysis.

---

## Key Benefits

### 1. Consistency Across Sub-Problems
**Without Memory**:
```
SP1 (CAC Analysis):
  Maria: "Target CAC <$150 based on $40 MRR and 18-month LTV"

SP2 (Channel Selection):
  Maria: "We need to understand our CAC constraints first..."
  [REDUNDANT - already analyzed]

SP3 (Budget Allocation):
  Maria: "What's our acceptable CAC again?"
  [CONTRADICTS - Maria already established this]
```

**With Memory**:
```
SP1 (CAC Analysis):
  Maria: "Target CAC <$150 based on $40 MRR and 18-month LTV"
  [Summary: "Maria recommended CAC <$150 based on $40 MRR..."]

SP2 (Channel Selection):
  Maria (with memory): "Given my $150 CAC target from SP1, paid ads fit better.
                        SEO's 6-month lag conflicts with our 18-month LTV requirement."
  [BUILDS ON - references specific constraint]

SP3 (Budget Allocation):
  Maria (with memory): "Based on my $150 CAC target (SP1) and paid-first recommendation (SP2),
                        I suggest $30K paid ads, $20K SEO."
  [INTEGRATES - coherent narrative across all 3]
```

### 2. Efficiency Gains
- Experts don't re-derive conclusions from previous sub-problems
- Can reference specific numbers/metrics from earlier analysis
- Reduces redundant deliberation time

### 3. Higher Quality Meta-Synthesis
- Meta-synthesis sees coherent expert narratives across sub-problems
- Easier to identify expert consensus vs dissent
- Cross-sub-problem insights naturally emerge

---

## Technical Implementation

### Leverages Existing Infrastructure ✅

**Good news**: `SummarizerAgent` is already fully implemented and being used for round-to-round context compression.

**Key Files**:
- `bo1/agents/summarizer.py` - Fully implemented, just need new method
- `bo1/prompts/summarizer_prompts.py` - Add expert summary prompt
- `bo1/orchestration/deliberation.py:554-598` - Background summarization pattern

### New Components

1. **Per-Expert Summarization** (`SummarizerAgent.summarize_expert_contributions()`)
   - Input: Expert's contributions to one sub-problem
   - Output: 50-100 token summary
   - Model: Haiku 4.5
   - Cost: ~$0.0008 per expert per sub-problem

2. **Expert Summary Prompt** (`EXPERT_SUMMARY_SYSTEM_PROMPT`)
   - Instructs: Capture position, evidence, confidence
   - Format: 50-100 tokens (strict)
   - Preserves: Numbers, metrics, key conditions

3. **Memory Injection** (`compose_persona_prompt(expert_memory=...)`)
   - New parameter: `expert_memory: str | None`
   - Adds `<your_previous_analysis>` section to prompt
   - Instructs expert to build on earlier analysis

4. **State Extension** (`SubProblemResult.expert_summaries`)
   - Stores: `{"maria": "Maria recommended CAC <$150...", "zara": "..."}`
   - Retrieved: When same expert selected for next sub-problem

### Data Flow

```
Sub-Problem 1 Complete
  ↓
Generate expert summaries (Maria, Zara, Chen, Tariq, Nina)
  ↓
Store in SubProblemResult.expert_summaries
  ↓
Move to Sub-Problem 2
  ↓
Select experts (Maria, Zara, Sarah, Yuki, Alex)
  ↓
Check previous sub-problems for Maria and Zara
  ↓
Inject memory summaries into Maria and Zara's prompts
  ↓
Maria and Zara build on their SP1 analysis
```

---

## Cost Analysis

### Per-Session Cost
```
Problem with 3 sub-problems, 5 experts per sub-problem:

Sub-problem 1:
  Deliberation: ~$0.12
  Expert summaries: 5 × $0.0008 = $0.004

Sub-problem 2:
  Deliberation: ~$0.12
  Expert summaries: 5 × $0.0008 = $0.004
  Memory injected: Maria, Zara (2 experts from SP1)

Sub-problem 3:
  Deliberation: ~$0.12
  Expert summaries: 5 × $0.0008 = $0.004
  Memory injected: Maria, Chen, Tariq, Nina (4 experts from SP1)

Total without expert memory: $0.36 (deliberations only)
Total with expert memory: $0.372 (deliberations + $0.012 summaries)

Cost increase: 3.3%
Value: Dramatically higher quality through expert continuity
```

### ROI Analysis
- **Cost increase**: 3.3% (~$0.012 per session)
- **Quality increase**: Prevents contradictions, enables cross-sub-problem integration
- **User perception**: Experts feel "smarter" and more coherent
- **Meta-synthesis quality**: Easier to synthesize when experts have consistent narratives

**Verdict**: 3.3% cost for significantly higher quality is excellent ROI.

---

## Roadmap Integration

### Day 36.5 Tasks (Added)

**15 new tasks** for expert memory (integrated with 68 multi-sub-problem tasks):

1. Model extension (`SubProblemResult.expert_summaries`)
2. `summarize_expert_contributions()` implementation
3. Expert summary prompts (system + request composition)
4. `next_subproblem_node()` summary generation
5. `compose_persona_prompt()` memory parameter
6. `persona_contribute_node()` memory injection
7. Cost tracking (`metrics.phase_costs["expert_memory"]`)
8. Unit tests (4 tests)
9. Integration tests (7 tests)
10. E2E test (expert memory scenario)

**Total Day 36.5**: 83 tasks (68 multi-sub-problem + 15 expert memory)

### Timeline Impact

**Original Day 36.5**: ~6 hours (multi-sub-problem iteration)
**With Expert Memory**: ~8 hours (+2 hours for memory integration)

**Rationale**: Expert memory is a natural extension of existing `SummarizerAgent` capabilities, so implementation is straightforward.

---

## Testing Strategy

### Unit Tests (`tests/agents/test_summarizer_expert_memory.py`)
- Summary generation (50-100 tokens)
- Preserves key numbers/metrics
- Cost <$0.001 per expert

### Integration Tests (`tests/integration/test_cross_subproblem_memory.py`)
- Expert in SP1+SP2 receives memory in SP2
- Expert only in SP2 does NOT receive memory
- Memory stored in `SubProblemResult.expert_summaries`
- Expert overlap detection (Maria in all 3, Zara in 2, etc.)

### E2E Test (`tests/e2e/test_expert_memory_growth_scenario.py`)
- **Scenario**: "Should I invest $50K in SEO or paid ads?"
- **3 sub-problems**: CAC, Channel, Budget
- **Expert overlap**: Maria (all 3), Zara (SP1+SP2), Chen (SP1+SP3)
- **Verifies**: Consistent recommendations, no contradictions, cost <5% increase

---

## Future Enhancements (Post-MVP)

### Cross-Session Expert Memory

**Goal**: Experts remember contributions across DIFFERENT user sessions.

**Example**:
```
Session 1 (User A): "Should I invest in SEO?"
  Maria: "For SaaS companies, SEO works best with content marketing foundation..."

Session 2 (User B): "SEO vs paid ads for my SaaS?"
  Maria (with cross-session memory): "Consistent with patterns I've seen for SaaS companies,
                                      SEO works best when..."
```

**Implementation**:
- Store expert summaries in PostgreSQL `expert_memory` table
- Index by: `persona_code`, `problem_category` (e.g., "SaaS pricing", "growth marketing")
- Retrieve relevant memories via semantic similarity (pgvector)
- Privacy: Anonymize user-specific data

**Value**:
- Experts become "smarter" over time
- New users benefit from accumulated expert knowledge
- System quality improves continuously

**Post-MVP Timing**: Week 10-11 (Admin Dashboard + Analytics)

---

## User-Facing Changes

### Console Output (NEW)

```
═══ Sub-Problem 1 of 3 ═══
CAC targets and payback period

[Deliberation happens...]

✓ Sub-problem 1 complete
Cost: $0.12 | Duration: 45s
Expert panel: Maria (Finance), Chen (Analytics)
Expert memory: Generated summaries for 2 experts

═══ Sub-Problem 2 of 3 ═══
Channel fit for target customer

Expert memory: Maria building on SP1 analysis
Expert memory: Zara building on SP1 analysis

[Deliberation happens with memory...]
```

**Note**: Memory messages are **informative** (user transparency), not required for MVP. Can be hidden behind `--verbose` flag.

---

## Success Criteria

✅ **Expert Memory Complete** when:
- [ ] Experts in multiple sub-problems receive memory summaries
- [ ] Memory summaries are 50-100 tokens (cost-effective)
- [ ] Expert contributions build on previous analysis (no contradictions)
- [ ] Console displays memory injection (optional, for transparency)
- [ ] All tests pass (unit, integration, e2e)
- [ ] Cost increase <5% of total deliberation cost (~3.3% actual)

---

## Comparison to User Request

### User's Vision
> "eventually it would be nice for experts to remember across different problems as well as sub problems, but this one is absolutley post mvp"

### Our Implementation

**Phase 1 (Day 36.5 - MVP)**: ✅ Cross-sub-problem memory
- Experts remember within a single problem decomposition
- Cost: ~3% increase
- Value: Consistency, efficiency, quality

**Phase 2 (Post-MVP)**: Cross-session memory
- Experts remember across different user sessions
- Requires: PostgreSQL storage, semantic similarity, privacy safeguards
- Timeline: Week 10-11 or later

**User Alignment**: ✅ Perfect alignment with user's priorities (sub-problem memory NOW, cross-session memory POST-MVP)

---

## Questions for User

1. **Console Display**: Should we show "Expert memory: Maria building on SP1 analysis" in console?
   - **Proposal**: Yes (transparency), but can hide behind `--verbose` flag

2. **Memory Scope**: Use ALL previous sub-problems or just MOST RECENT?
   - **Proposal**: Most recent only (simpler, less context bloat)

3. **Atomic Optimization**: If only 1 expert contributed to previous sub-problem, skip memory?
   - **Proposal**: No, generate memory for ALL experts (consistency)

---

## References

### Specifications
- **Expert Memory**: `zzz_project/detail/CROSS_SUBPROBLEM_EXPERT_MEMORY.md`
- **Multi-Sub-Problem**: `zzz_project/detail/MULTI_SUBPROBLEM_DELIBERATION.md`
- **Roadmap**: `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` (Day 36.5)

### Implementation
- **SummarizerAgent**: `bo1/agents/summarizer.py`
- **Existing Round Summarization**: `bo1/orchestration/deliberation.py:554-598`
- **Graph State**: `bo1/graph/state.py` (includes `round_summaries`)

### Context
- **User Request**: Bring forward expert memory from Phase 3 to Phase 1
- **Alignment**: Leverages existing `SummarizerAgent`, minimal new code
- **Cost**: 3.3% increase for dramatically higher quality
- **Timeline**: +2 hours to Day 36.5 (now 8 hours total)
