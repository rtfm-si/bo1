# Cross-Sub-Problem Expert Memory Specification

**Feature**: Expert Memory Across Sub-Problems
**Priority**: High (Day 36.5 - Integrated with Multi-Sub-Problem Iteration)
**Complexity**: 6/10
**Status**: Design Complete, Ready for Implementation

---

## Executive Summary

When an expert (e.g., Maria - Finance) is selected for multiple sub-problems, they should **remember** their contributions from earlier sub-problems. This creates continuity, prevents contradictions, and enables experts to build on their previous analysis.

**Example Scenario**:
```
Problem: "Should I invest $50K in SEO or paid ads?"

Sub-problem 1 (CAC Analysis):
  Selected experts: Maria (Finance), Chen (Analytics)
  Maria says: "Our target CAC should be <$150 based on $40 MRR and 18-month LTV."

Sub-problem 2 (Channel Selection):
  Selected experts: Maria (Finance), Tariq (Marketing), Nina (Customer Research)
  Maria says (WITH MEMORY): "Given our $150 CAC target from my earlier analysis,
                             paid ads fit better than SEO initially. SEO's 6-month
                             lag conflicts with our 18-month LTV payback requirement."

  Maria says (WITHOUT MEMORY): "We need to understand our CAC targets first..."
                               [redundant, contradicts earlier position]
```

**Key Insight**: This is a **natural extension** of existing `SummarizerAgent` capabilities. Instead of summarizing rounds, we summarize sub-problems.

---

## Design Principles

1. **Leverage Existing Infrastructure**: Use `SummarizerAgent` for sub-problem compression
2. **Per-Expert Summaries**: Summarize ONLY the contributions from experts who appear in multiple sub-problems
3. **Selective Memory**: Only inject memory if the same expert is selected again
4. **Cost-Conscious**: Use Haiku for summarization (~$0.001 per expert per sub-problem)
5. **Hierarchical Context**: Sub-problem summaries are shorter than full contributions (50-100 tokens each)

---

## Architecture

### Data Model Extension

Add to `SubProblemResult` (already defined in Day 36.5):

```python
class SubProblemResult(BaseModel):
    """Result of deliberating a single sub-problem."""
    sub_problem_id: str
    sub_problem_goal: str
    synthesis: str
    votes: list[dict]
    contribution_count: int
    cost: float
    duration_seconds: float
    expert_panel: list[str]  # Persona codes

    # NEW: Per-expert contribution summaries for memory
    expert_summaries: dict[str, str] = Field(
        default_factory=dict,
        description="Per-expert summaries (persona_code → 50-100 token summary)",
    )
```

### Summarization Flow

**After each sub-problem synthesis**:

1. Identify experts who contributed (`expert_panel`)
2. For each expert, create a 50-100 token summary of their contributions
3. Store in `expert_summaries` dict
4. Cost: ~$0.001 per expert (Haiku, fast)

**Before next sub-problem deliberation**:

1. Check if any selected experts appeared in previous sub-problems
2. If yes, inject their previous summaries into persona prompt
3. Expert sees: "In your previous analysis (Sub-problem 1), you argued that..."

---

## Implementation Details

### Step 1: Enhance `SummarizerAgent` with Per-Expert Summarization

Add new method to `bo1/agents/summarizer.py`:

```python
async def summarize_expert_contributions(
    self,
    persona_code: str,
    persona_name: str,
    sub_problem_goal: str,
    contributions: list[ContributionMessage],
    target_tokens: int = 75,
) -> LLMResponse:
    """Summarize a single expert's contributions to a sub-problem.

    This creates a memory snapshot for experts who appear in multiple sub-problems.

    Args:
        persona_code: Expert code (e.g., "maria")
        persona_name: Expert display name (e.g., "Maria Santos (Finance)")
        sub_problem_goal: The sub-problem they contributed to
        contributions: All contributions from this expert in this sub-problem
        target_tokens: Target summary length (default: 75 tokens)

    Returns:
        LLMResponse with 50-100 token summary of expert's position

    Example Output:
        "Maria analyzed CAC targets, recommending <$150 based on $40 MRR and
         18-month LTV. She emphasized cash flow risk and requested sensitivity
         analysis on timeline assumptions. Confidence: 0.85."
    """
    from bo1.prompts.summarizer_prompts import compose_expert_summary_request

    logger.info(
        f"Summarizing {persona_name}'s contributions to sub-problem "
        f"({len(contributions)} contributions, target: {target_tokens} tokens)"
    )

    # Compose request
    user_message = compose_expert_summary_request(
        persona_name=persona_name,
        sub_problem_goal=sub_problem_goal,
        contributions=contributions,
        target_tokens=target_tokens,
    )

    # Create prompt request
    request = PromptRequest(
        system=EXPERT_SUMMARY_SYSTEM_PROMPT,
        user_message=user_message,
        temperature=0.3,
        max_tokens=target_tokens + 25,
        phase="expert_summarization",
        agent_type="summarizer",
    )

    # Call LLM
    response = await self._call_llm(request)

    logger.info(
        f"{persona_name} summary: {response.token_usage.output_tokens} tokens, "
        f"${response.cost_total:.6f}"
    )

    return response
```

### Step 2: Create Expert Summary Prompt

Add to `bo1/prompts/summarizer_prompts.py`:

```python
EXPERT_SUMMARY_SYSTEM_PROMPT = """You are an expert summarizer for Board of One.

Your task is to create a concise summary of a SINGLE expert's contributions to a sub-problem.
This summary will be used as "memory" if the same expert is selected for future sub-problems.

**Target Length**: 50-100 tokens (strict)

**Summary Structure**:
1. What position did the expert take? (1-2 sentences)
2. What evidence or reasoning did they provide? (1-2 sentences)
3. What was their confidence level and key conditions/risks? (1 sentence)

**Example**:
Input:
  Expert: Maria Santos (Finance)
  Sub-problem: What should our target CAC be?
  Contributions:
    - "Our CAC should be <$150 based on $40 MRR..."
    - "I need to see sensitivity analysis on timeline..."
    - "Cash flow risk concerns me given 6-month SEO lag..."

Output:
  "Maria recommended CAC <$150 based on $40 MRR and 18-month LTV calculations.
   She emphasized cash flow risk from the 6-month SEO lag and requested sensitivity
   analysis on timeline assumptions. Confidence: 0.85, conditional on verifying LTV model."

**Important**:
- Be specific (include numbers, metrics, recommendations)
- Capture dissent or concerns (not just agreements)
- Preserve the expert's unique perspective
- Avoid generic statements ("Maria contributed valuable insights")
"""


def compose_expert_summary_request(
    persona_name: str,
    sub_problem_goal: str,
    contributions: list[ContributionMessage],
    target_tokens: int = 75,
) -> str:
    """Compose request for expert contribution summarization.

    Args:
        persona_name: Expert display name
        sub_problem_goal: Sub-problem they addressed
        contributions: Their contributions
        target_tokens: Target summary length

    Returns:
        Formatted prompt for summarization
    """
    # Format contributions
    formatted_contributions = []
    for i, contrib in enumerate(contributions, 1):
        formatted_contributions.append(
            f"Round {contrib.round_number}: {contrib.content}"
        )

    return f"""Summarize the following expert's contributions to create a memory snapshot.

<expert>
{persona_name}
</expert>

<sub_problem>
{sub_problem_goal}
</sub_problem>

<contributions>
{chr(10).join(formatted_contributions)}
</contributions>

<instructions>
Create a {target_tokens}-token summary capturing:
1. Their position/recommendation
2. Key evidence/reasoning
3. Confidence and conditions

Be specific. Include numbers and metrics.
</instructions>
"""
```

### Step 3: Generate Expert Summaries After Sub-Problem Synthesis

Update `next_subproblem_node()` in `bo1/graph/nodes.py`:

```python
async def next_subproblem_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Move to next sub-problem after synthesis.

    - Save current sub-problem result (synthesis, votes, costs)
    - Generate per-expert summaries for memory
    - Increment sub-problem index
    - Reset deliberation state for next sub-problem
    """
    from bo1.agents.summarizer import SummarizerAgent
    from bo1.models.state import SubProblemResult

    logger.info("next_subproblem_node: Saving sub-problem result and moving to next")

    # Extract current sub-problem data
    current_sp = state["current_sub_problem"]
    problem = state["problem"]
    contributions = state.get("contributions", [])
    votes = state.get("votes", [])
    personas = state.get("personas", [])
    synthesis = state.get("synthesis", "")

    # Calculate cost for this sub-problem
    # (Sum of all phase costs since last sub-problem)
    metrics = state.get("metrics")
    # TODO: Calculate sub-problem cost (track separately in metrics)
    sub_problem_cost = 0.0  # Placeholder

    # Generate per-expert summaries for memory
    expert_summaries: dict[str, str] = {}
    summarizer = SummarizerAgent()

    for persona in personas:
        # Get contributions from this expert
        expert_contributions = [
            c for c in contributions if c.persona_code == persona.code
        ]

        if expert_contributions:
            try:
                # Summarize expert's contributions
                response = await summarizer.summarize_expert_contributions(
                    persona_code=persona.code,
                    persona_name=persona.name,
                    sub_problem_goal=current_sp.goal,
                    contributions=expert_contributions,
                )

                expert_summaries[persona.code] = response.content

                logger.info(
                    f"Generated memory summary for {persona.name}: "
                    f"{response.token_usage.output_tokens} tokens"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to generate summary for {persona.name}: {e}. "
                    f"Expert will not have memory for next sub-problem."
                )

    # Create SubProblemResult
    result = SubProblemResult(
        sub_problem_id=current_sp.id,
        sub_problem_goal=current_sp.goal,
        synthesis=synthesis,
        votes=votes,
        contribution_count=len(contributions),
        cost=sub_problem_cost,
        duration_seconds=0.0,  # TODO: Track time
        expert_panel=[p.code for p in personas],
        expert_summaries=expert_summaries,  # NEW: Memory for experts
    )

    # Add to results
    sub_problem_results = list(state.get("sub_problem_results", []))
    sub_problem_results.append(result)

    # Increment index
    sub_problem_index = state.get("sub_problem_index", 0)
    next_index = sub_problem_index + 1

    # Check if more sub-problems
    if next_index < len(problem.sub_problems):
        next_sp = problem.sub_problems[next_index]

        logger.info(
            f"Moving to sub-problem {next_index + 1}/{len(problem.sub_problems)}: "
            f"{next_sp.goal}"
        )

        return {
            "current_sub_problem": next_sp,
            "sub_problem_index": next_index,
            "sub_problem_results": sub_problem_results,
            "round_number": 1,
            "contributions": [],
            "votes": [],
            "facilitator_decision": None,
            "should_stop": False,
            "stop_reason": None,
            "round_summaries": [],  # Reset for new sub-problem
            "current_node": "next_subproblem",
        }
    else:
        # All complete → meta-synthesis
        logger.info("All sub-problems complete, proceeding to meta-synthesis")
        return {
            "current_sub_problem": None,
            "sub_problem_results": sub_problem_results,
            "current_node": "next_subproblem",
        }
```

### Step 4: Inject Expert Memory Into Persona Prompts

Update persona prompt composition in `bo1/prompts/reusable_prompts.py`:

```python
def compose_persona_prompt(
    persona_system_role: str,
    problem_statement: str,
    participant_list: str,
    current_phase: str,
    problem_context: str = "",
    previous_contributions: list[dict] | None = None,
    round_number: int = 1,
    expert_memory: str | None = None,  # NEW: Cross-sub-problem memory
) -> str:
    """Compose full persona prompt with memory support.

    Args:
        ... (existing args)
        expert_memory: Summary of expert's contributions to previous sub-problems

    Returns:
        Complete system prompt with optional memory injection
    """
    parts = [persona_system_role]  # Bespoke identity

    # NEW: Inject expert memory if available
    if expert_memory:
        parts.append(f"""

<your_previous_analysis>
You previously contributed to an earlier sub-problem in this deliberation.
Here's a summary of your position from that analysis:

{expert_memory}

You should build on this earlier analysis, maintaining consistency with your
previous recommendations unless new information changes your view. If you
change your position, explain why.
</your_previous_analysis>
""")

    # Add problem context
    parts.append(f"\n<problem>\n{problem_statement}\n</problem>\n")

    # ... (rest of existing composition)

    return "".join(parts)
```

### Step 5: Wire Memory Into Persona Contribution Node

Update `persona_contribute_node()` in `bo1/graph/nodes.py`:

```python
async def persona_contribute_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Persona contributes to deliberation WITH MEMORY.

    If this expert contributed to previous sub-problems, inject their
    summary as "memory" so they can build on earlier analysis.
    """
    # ... (existing code to get speaker, persona, etc.)

    # NEW: Check if expert has memory from previous sub-problems
    expert_memory: str | None = None

    sub_problem_results = state.get("sub_problem_results", [])
    if sub_problem_results:
        # Check if this expert appeared in previous sub-problems
        for result in sub_problem_results:
            if speaker_code in result.expert_summaries:
                # Found memory from previous sub-problem
                prev_summary = result.expert_summaries[speaker_code]
                prev_goal = result.sub_problem_goal

                expert_memory = f"""Sub-problem: {prev_goal}
Your previous position: {prev_summary}"""

                logger.info(
                    f"{speaker_code} has memory from previous sub-problem: "
                    f"{result.sub_problem_id}"
                )
                break  # Use most recent memory

    # Call persona with memory
    llm_response, contribution_msg = await engine._call_persona_async(
        persona_profile=persona,
        problem_statement=problem.description if problem else "",
        problem_context=problem.context if problem else "",
        participant_list=participant_list,
        round_number=round_number,
        contribution_type=ContributionType.RESPONSE,
        previous_contributions=contributions,
        expert_memory=expert_memory,  # NEW: Inject memory
    )

    # ... (rest of existing code)
```

---

## Cost Analysis

### Per-Expert Summary Cost
- Model: Haiku 4.5
- Input: ~500 tokens (3-5 contributions)
- Output: ~75 tokens (target)
- Cost: ~$0.0008 per expert per sub-problem

### Example Scenario
```
Problem with 3 sub-problems, 5 experts per sub-problem:

Sub-problem 1:
  Experts: Maria, Zara, Chen, Tariq, Nina
  Summaries: 5 × $0.0008 = $0.004

Sub-problem 2:
  Experts: Maria, Zara, Sarah, Yuki, Alex
  Summaries: 5 × $0.0008 = $0.004
  Memory injected: Maria (appeared in SP1), Zara (appeared in SP1)

Sub-problem 3:
  Experts: Maria, Chen, Tariq, Nina, Sarah
  Summaries: 5 × $0.0008 = $0.004
  Memory injected: Maria (SP1), Chen (SP1), Tariq (SP1), Nina (SP1)

Total summarization cost: $0.012
Total memory injections: 6 experts had continuity across sub-problems

Cost increase: ~3% of total deliberation cost ($0.012 / $0.41)
Value: Significantly higher quality through expert continuity
```

---

## Benefits

### 1. Consistency
- Experts don't contradict earlier positions
- Analysis builds incrementally across sub-problems

### 2. Efficiency
- Experts don't re-derive conclusions from previous sub-problems
- Can reference specific numbers/metrics from earlier analysis

### 3. Cross-Sub-Problem Integration
- Finance expert can connect "CAC targets" (SP1) to "channel selection" (SP2)
- Operations expert can link "execution capacity" (SP3) to "timeline" (SP1)

### 4. Higher Quality Meta-Synthesis
- Meta-synthesis sees coherent expert narratives across sub-problems
- Easier to identify expert consensus vs dissent

---

## Example User Flow

### Without Memory (Current Behavior)
```
SP1 (CAC Analysis):
  Maria: "Target CAC <$150 based on $40 MRR and 18-month LTV"

SP2 (Channel Selection):
  Maria: "We need to understand our CAC constraints first before choosing channels"
  [REDUNDANT - already analyzed in SP1]

SP3 (Budget Allocation):
  Maria: "What's our acceptable CAC again?"
  [CONTRADICTS - Maria already established this in SP1]
```

### With Memory (New Behavior)
```
SP1 (CAC Analysis):
  Maria: "Target CAC <$150 based on $40 MRR and 18-month LTV"
  [Summary generated: "Maria recommended CAC <$150 based on $40 MRR..."]

SP2 (Channel Selection):
  Maria (with memory): "Given my earlier analysis establishing $150 CAC target,
                        paid ads fit better initially. SEO's 6-month lag conflicts
                        with our 18-month LTV payback requirement from SP1."
  [BUILDS ON - references specific constraint from SP1]

SP3 (Budget Allocation):
  Maria (with memory): "Based on my $150 CAC target (SP1) and paid-first recommendation (SP2),
                        I suggest $30K paid ads, $20K SEO. This maintains our LTV economics
                        while building long-term SEO moat."
  [INTEGRATES - coherent narrative across all 3 sub-problems]
```

---

## Testing Strategy

### Unit Tests (`tests/agents/test_summarizer_expert_memory.py`)
- Test: `summarize_expert_contributions()` generates 50-100 token summary
- Test: Summary preserves key numbers/metrics
- Test: Summary captures expert's position accurately
- Test: Cost <$0.001 per expert summary

### Integration Tests (`tests/integration/test_cross_subproblem_memory.py`)
- Test: Expert appearing in SP1 and SP2 receives memory in SP2
- Test: Expert NOT appearing in SP1 does NOT receive memory in SP2
- Test: Memory injection works with 2 sub-problems (simplest case)
- Test: Memory injection works with 5 sub-problems (max complexity)
- Test: Expert summaries stored in `SubProblemResult.expert_summaries`

### End-to-End Test (`tests/e2e/test_expert_memory_growth_scenario.py`)
- **Scenario**: "Should I invest $50K in SEO or paid ads?"
- **Decomposition**: 3 sub-problems (CAC, Channel, Budget)
- **Expert Overlap**: Maria appears in all 3, Zara in SP1+SP2, Chen in SP1+SP3
- **Verify**:
  - [ ] Maria receives memory in SP2 (from SP1)
  - [ ] Maria receives memory in SP3 (from SP1 and SP2)
  - [ ] Maria's recommendations are consistent across SP1→SP2→SP3
  - [ ] Zara receives memory in SP2 (from SP1)
  - [ ] Chen receives memory in SP3 (from SP1)
  - [ ] Experts without overlap (Nina only in SP1) have no memory
  - [ ] Total cost increase <5% (~$0.012 for summaries)

---

## Future Enhancements (Post-MVP)

### Cross-Session Expert Memory
**Goal**: Experts remember contributions across DIFFERENT user sessions

**Example**:
```
Session 1 (User A): "Should I invest in SEO?"
  Maria: "For SaaS companies, SEO works best with..."

Session 2 (User B): "SEO vs paid ads for my SaaS?"
  Maria (with cross-session memory): "Consistent with my earlier analysis for
                                      SaaS companies, SEO works best when..."
```

**Implementation**:
- Store expert summaries in PostgreSQL `expert_memory` table
- Index by: persona_code, problem_category (SaaS pricing, growth, etc.)
- Retrieve relevant memories via semantic similarity search (pgvector)
- Cost: Minimal (summaries already generated, just need storage)

**Privacy**:
- Anonymize user-specific data (no names, company names, financials)
- Store only expert's generic analysis (principles, frameworks, patterns)
- User can opt-out of contributing to expert memory

**Value**:
- Experts become "smarter" over time (learn from previous deliberations)
- New users benefit from accumulated expert knowledge
- System quality improves continuously

---

## Roadmap Integration

### Day 36.5 Tasks (Updated)

Add to existing Day 36.5 (Multi-Sub-Problem Iteration):

#### Expert Memory Implementation

- [ ] Add `expert_summaries: dict[str, str]` to `SubProblemResult` model
- [ ] Implement `summarize_expert_contributions()` in `SummarizerAgent`
- [ ] Create `EXPERT_SUMMARY_SYSTEM_PROMPT` in `summarizer_prompts.py`
- [ ] Create `compose_expert_summary_request()` in `summarizer_prompts.py`
- [ ] Update `next_subproblem_node()` to generate expert summaries
- [ ] Update `compose_persona_prompt()` to accept `expert_memory` parameter
- [ ] Update `persona_contribute_node()` to inject expert memory
- [ ] Track expert summary costs in `metrics.phase_costs["expert_memory"]`

#### Testing (Expert Memory)

- [ ] Unit tests: `test_summarize_expert_contributions()`
  - [ ] Test: Summary is 50-100 tokens
  - [ ] Test: Summary preserves key numbers/metrics
  - [ ] Test: Cost <$0.001 per expert
- [ ] Integration tests: `test_cross_subproblem_memory.py`
  - [ ] Test: Expert in SP1+SP2 receives memory in SP2
  - [ ] Test: Expert only in SP2 does NOT receive memory
  - [ ] Test: Memory stored in `SubProblemResult.expert_summaries`
- [ ] End-to-end test: `test_expert_memory_growth_scenario.py`
  - [ ] Test: Maria's recommendations consistent across SP1→SP2→SP3
  - [ ] Test: Expert overlap detection works (Maria in all 3, Zara in 2, etc.)
  - [ ] Test: Total cost increase <5%

**Estimated Additional Tasks**: 15 tasks
**Estimated Additional Time**: +2 hours to Day 36.5
**Estimated Additional Cost**: +3% per multi-sub-problem session (~$0.012)

---

## Success Criteria

✅ **Expert Memory Complete** when:
- [ ] Experts appearing in multiple sub-problems receive memory summaries
- [ ] Memory summaries are 50-100 tokens (cost-effective)
- [ ] Expert contributions build on previous sub-problem analysis
- [ ] No contradictions between expert positions across sub-problems
- [ ] Console displays "Expert memory: Maria has context from SP1" (optional)
- [ ] All tests pass (unit, integration, e2e)
- [ ] Cost increase <5% of total deliberation cost

---

## Open Questions

1. **Memory Scope**: Should we use ALL previous sub-problems or just the MOST RECENT?
   - **Proposal**: Most recent only (simpler, less context bloat)
   - **Alternative**: All previous (more complete, but longer prompts)

2. **Memory Display**: Should we show users that experts have memory?
   - **Proposal**: Yes, console shows "✓ Maria building on SP1 analysis"
   - **Rationale**: Transparency, helps users understand expert continuity

3. **Memory Opt-Out**: Should users be able to disable expert memory?
   - **Proposal**: No opt-out for MVP (always enabled, 3% cost increase acceptable)
   - **Future**: Add `--no-expert-memory` flag for pure isolation

4. **Conflict Resolution**: What if expert changes position between sub-problems?
   - **Handled**: Prompt instructs "If you change your position, explain why"
   - **Example**: "My earlier $150 CAC target assumed 18-month LTV, but SP2 revealed
                    12-month churn, so I now recommend $100 CAC."

---

## References

- **SummarizerAgent Implementation**: `bo1/agents/summarizer.py`
- **Round Summarization**: `bo1/orchestration/deliberation.py:554-598`
- **Multi-Sub-Problem Specification**: `zzz_project/detail/MULTI_SUBPROBLEM_DELIBERATION.md`
- **Roadmap**: `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` (Day 36.5)
