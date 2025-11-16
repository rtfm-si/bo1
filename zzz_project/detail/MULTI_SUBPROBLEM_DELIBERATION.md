# Multi-Sub-Problem Deliberation Specification

**Status**: Not Implemented (Critical Gap)
**Priority**: High (Required for Week 6+)
**Complexity**: 8/10

---

## Executive Summary

**CRITICAL GAP IDENTIFIED**: The current implementation only deliberates on the **first sub-problem** after decomposition. Sub-problems 2-5 are decomposed but never deliberated on.

This specification defines how Board of One should handle problems decomposed into multiple sub-problems (2-5), including:
- Sequential vs parallel execution based on dependencies
- Different expert panels per sub-problem
- User input collection per sub-problem (HITL)
- Cross-sub-problem synthesis
- Progress tracking and resume support

---

## Current Implementation Analysis

### What Works ✅

1. **Decomposition Quality Control**
   - Max 5 sub-problems enforced (`DecomposerAgent.validate_decomposition()`)
   - Complexity scoring (1-10 scale)
   - Dependency mapping (`SubProblem.dependencies: list[str]`)
   - Validation ensures dependencies reference valid sub-problem IDs

2. **Data Model**
   ```python
   class SubProblem(BaseModel):
       id: str
       goal: str
       context: str
       complexity_score: int  # 1-10
       dependencies: list[str]  # IDs of prerequisite sub-problems
       constraints: list[Constraint]
   ```

3. **Expert Selection Per Sub-Problem**
   - `PersonaSelectorAgent.recommend_personas(sub_problem=...)` designed for per-sub-problem selection
   - Different panels can be selected based on sub-problem nature

### Critical Gaps ❌

1. **Only First Sub-Problem Deliberated**
   - `decompose_node()` sets: `current_sub_problem = sub_problems[0]`
   - No iteration logic to move to sub_problems[1], [2], etc.
   - Synthesis happens after ONLY the first sub-problem

2. **Dependencies Not Executed**
   - Dependencies are validated but never consulted during execution
   - No logic to check if prerequisite sub-problems completed before starting dependent ones

3. **No Cross-Sub-Problem Synthesis**
   - Current synthesis uses contributions from ONE sub-problem only
   - No "meta-synthesis" to combine insights across all sub-problems

4. **No Progress Tracking**
   - No tracking of which sub-problems are complete/in-progress/pending
   - Cannot resume multi-sub-problem deliberations properly

5. **HITL Not Per-Sub-Problem**
   - Context collection happens once (pre-decomposition)
   - Clarifications can happen during deliberation but not targeted per sub-problem

---

## Design Principles

1. **User Sovereignty**: User chooses sequential (one at a time) vs parallel (all at once) execution
2. **Dependency Respect**: Dependencies MUST be enforced (cannot start sp_002 if it depends on sp_001 until sp_001 completes)
3. **Console vs Web Tradeoff**:
   - Console: Sequential only (HITL blocking is acceptable)
   - Web: Parallel + Sequential hybrid (non-blocking HITL with pause/resume)
4. **Synthesis Hierarchy**: Sub-problem synthesis → Cross-sub-problem meta-synthesis
5. **Cost Visibility**: Track costs per sub-problem, show total at end

---

## Proposed Architecture

### Sub-Problem Execution Modes

#### Mode 1: Sequential (Console-Friendly)
```
decompose → sp_001 deliberation → sp_001 synthesis
         → sp_002 deliberation → sp_002 synthesis
         → sp_003 deliberation → sp_003 synthesis
         → cross-sub-problem meta-synthesis → END
```

**Pros**:
- Simple HITL (user answers questions, deliberation proceeds immediately)
- Clear progress ("Sub-problem 2 of 4")
- Lower cognitive load (focus on one problem at a time)

**Cons**:
- Cannot parallelize independent sub-problems
- Longer total time if sub-problems are independent

#### Mode 2: Parallel with Dependencies (Web-Optimized)
```
decompose → [sp_001 || sp_003] (parallel, no dependencies)
         → sp_002 (waits for sp_001 to complete)
         → sp_004 (waits for sp_002 and sp_003)
         → cross-sub-problem meta-synthesis → END
```

**Pros**:
- Faster for independent sub-problems
- User can answer clarifications asynchronously (pause/resume per sub-problem)
- Better utilization of LLM concurrency

**Cons**:
- Complex dependency graph execution
- User may get multiple clarification requests simultaneously
- Requires web UI for non-blocking HITL

#### Mode 3: Hybrid (Recommended for MVP)
```
User chooses:
- "One at a time" → Sequential mode
- "All at once (where possible)" → Parallel with dependencies

Default: Sequential (simpler, works in console)
```

---

## Implementation Roadmap

### Phase 1: Sequential Execution (Week 6 - Console)

**Goal**: Deliberate all sub-problems sequentially, one at a time.

**Changes Required**:

1. **Add Sub-Problem Iterator Node** (`bo1/graph/nodes.py`)
   ```python
   async def next_subproblem_node(state: DeliberationGraphState) -> dict[str, Any]:
       """Move to next sub-problem after synthesis.

       - Find current_sub_problem in problem.sub_problems
       - Move to next in list
       - If no more sub-problems → route to meta-synthesis
       - Reset round_number, contributions, votes for new sub-problem
       """
       problem = state["problem"]
       current_sp = state["current_sub_problem"]

       # Find index of current sub-problem
       current_idx = next(
           (i for i, sp in enumerate(problem.sub_problems) if sp.id == current_sp.id),
           -1
       )

       # Move to next
       next_idx = current_idx + 1
       if next_idx < len(problem.sub_problems):
           next_sp = problem.sub_problems[next_idx]
           logger.info(f"Moving to sub-problem {next_idx + 1}/{len(problem.sub_problems)}: {next_sp.goal}")

           # Reset deliberation state for new sub-problem
           return {
               "current_sub_problem": next_sp,
               "round_number": 1,
               "contributions": [],
               "votes": [],
               "facilitator_decision": None,
               "should_stop": False,
               "stop_reason": None,
               "current_node": "next_subproblem",
           }
       else:
           # All sub-problems complete → meta-synthesis
           logger.info("All sub-problems complete, proceeding to meta-synthesis")
           return {
               "current_sub_problem": None,
               "current_node": "next_subproblem",
           }
   ```

2. **Track Sub-Problem Results** (State Extension)
   ```python
   class SubProblemResult(BaseModel):
       """Result of deliberating a single sub-problem."""
       sub_problem_id: str
       synthesis: str
       votes: list[dict]
       contributions: list[ContributionMessage]
       cost: float
       duration_seconds: float

   # Add to DeliberationGraphState
   sub_problem_results: list[SubProblemResult] = []
   ```

3. **Router Logic** (`bo1/graph/routers.py`)
   ```python
   def route_after_synthesis(state: DeliberationGraphState) -> str:
       """Route after sub-problem synthesis.

       - If more sub-problems → "next_subproblem"
       - If all complete → "meta_synthesis"
       """
       problem = state["problem"]
       current_sp = state["current_sub_problem"]

       if current_sp is None:
           # Already moved to meta-synthesis
           return "meta_synthesis"

       # Find current index
       current_idx = next(
           (i for i, sp in enumerate(problem.sub_problems) if sp.id == current_sp.id),
           -1
       )

       if current_idx + 1 < len(problem.sub_problems):
           return "next_subproblem"
       else:
           return "meta_synthesis"
   ```

4. **Meta-Synthesis Node** (`bo1/graph/nodes.py`)
   ```python
   async def meta_synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
       """Create cross-sub-problem meta-synthesis.

       Inputs:
       - All sub-problem results (synthesis reports, votes, costs)
       - Original problem statement

       Output:
       - Comprehensive synthesis that:
         * Summarizes each sub-problem recommendation
         * Identifies tensions/trade-offs between sub-problems
         * Provides unified action plan
         * Highlights dependencies and sequencing
       """
       from bo1.prompts.reusable_prompts import META_SYNTHESIS_PROMPT_TEMPLATE

       problem = state["problem"]
       sub_problem_results = state.get("sub_problem_results", [])

       # Format all sub-problem syntheses
       formatted_results = []
       total_cost = 0.0
       for result in sub_problem_results:
           sp = problem.get_sub_problem(result.sub_problem_id)
           formatted_results.append(f"""
## Sub-Problem {result.sub_problem_id}: {sp.goal if sp else 'Unknown'}

### Synthesis
{result.synthesis}

### Expert Votes
{format_votes(result.votes)}

### Cost: ${result.cost:.4f}
""")
           total_cost += result.cost

       # Create meta-synthesis prompt
       meta_prompt = META_SYNTHESIS_PROMPT_TEMPLATE.format(
           original_problem=problem.description,
           sub_problem_count=len(sub_problem_results),
           all_sub_problem_syntheses="\n\n".join(formatted_results),
       )

       # Call LLM (Sonnet for high-quality synthesis)
       broker = PromptBroker()
       request = PromptRequest(
           system=meta_prompt,
           user_message="Generate the comprehensive meta-synthesis now.",
           prefill="<thinking>",
           model="sonnet",
           temperature=0.7,
           max_tokens=4000,
           phase="meta_synthesis",
           agent_type="meta_synthesizer",
       )

       response = await broker.call(request)
       meta_synthesis = "<thinking>" + response.content

       # Add disclaimer and cost summary
       meta_synthesis += f"""
---

## Deliberation Summary

- **Sub-problems deliberated**: {len(sub_problem_results)}
- **Total cost**: ${total_cost:.4f}
- **Total time**: {sum(r.duration_seconds for r in sub_problem_results):.1f}s

⚠️ This content is AI-generated for learning and knowledge purposes only, not professional advisory.
Always verify recommendations using licensed legal/financial professionals for your location.
"""

       return {
           "synthesis": meta_synthesis,
           "phase": DeliberationPhase.COMPLETE,
           "current_node": "meta_synthesis",
       }
   ```

5. **Update Graph Configuration** (`bo1/graph/config.py`)
   ```python
   # After synthesize_node
   workflow.add_node("next_subproblem", next_subproblem_node)
   workflow.add_node("meta_synthesis", meta_synthesize_node)

   # Conditional edge from synthesize
   workflow.add_conditional_edges(
       "synthesize",
       route_after_synthesis,
       {
           "next_subproblem": "next_subproblem",
           "meta_synthesis": "meta_synthesis",
       }
   )

   # Loop back to persona selection for next sub-problem
   workflow.add_edge("next_subproblem", "select_personas")

   # Meta-synthesis is terminal
   workflow.add_edge("meta_synthesis", END)
   ```

6. **Console Display Updates** (`bo1/interfaces/console.py`)
   ```python
   # Show sub-problem progress
   console.print(f"\n[bold cyan]Sub-Problem {current_idx + 1} of {total}[/bold cyan]")
   console.print(f"[dim]{current_sp.goal}[/dim]\n")

   # After each sub-problem synthesis
   console.print(f"\n[green]✓ Sub-problem {current_idx + 1} complete[/green]")
   console.print(f"[dim]Cost: ${result.cost:.4f} | Duration: {result.duration_seconds:.1f}s[/dim]\n")

   # Before meta-synthesis
   console.print(f"\n[bold magenta]═══ Cross-Sub-Problem Meta-Synthesis ═══[/bold magenta]\n")
   console.print(f"[dim]Synthesizing insights from {len(results)} sub-problems...[/dim]\n")
   ```

**Validation**:
- [ ] Test with 2 sub-problems (simplest case)
- [ ] Test with 5 sub-problems (max complexity)
- [ ] Verify each sub-problem gets different expert panel
- [ ] Verify meta-synthesis includes all sub-problems
- [ ] Verify cost tracking per sub-problem
- [ ] Verify pause/resume works mid-multi-sub-problem session

---

### Phase 2: Dependency-Aware Execution (Week 7-8 - Web)

**Goal**: Respect dependencies, enable parallel execution of independent sub-problems.

**Changes Required**:

1. **Dependency Graph Analysis**
   ```python
   def analyze_dependencies(sub_problems: list[SubProblem]) -> dict:
       """Analyze sub-problem dependencies to determine execution order.

       Returns:
       {
           "levels": [
               [sp_001, sp_003],  # Level 0: No dependencies
               [sp_002],          # Level 1: Depends on sp_001
               [sp_004],          # Level 2: Depends on sp_002, sp_003
           ],
           "can_parallelize": True,  # If any level has >1 sub-problem
       }
       """
   ```

2. **Parallel Execution Support**
   - Use `asyncio.gather()` for sub-problems at same dependency level
   - Track completion of each sub-problem
   - Block dependent sub-problems until prerequisites complete

3. **Web UI Enhancements**
   - Show dependency graph visualization
   - Progress bars for each sub-problem (in-progress, complete, pending)
   - Asynchronous clarification requests (user answers when ready, not blocking)

---

### Phase 3: Per-Sub-Problem HITL (Week 8-9 - Web)

**Goal**: Collect context/clarifications specific to each sub-problem.

**Changes Required**:

1. **Context Collection Per Sub-Problem**
   - After selecting personas for sub-problem, identify info gaps SPECIFIC to that sub-problem
   - Store clarifications in `session_clarifications` table with `sub_problem_id` field

2. **Pause/Resume Per Sub-Problem**
   - User can pause deliberation on sp_002 while sp_001 continues (if independent)
   - Resume individual sub-problems without restarting entire session

---

## Meta-Synthesis Prompt Template

```python
META_SYNTHESIS_PROMPT_TEMPLATE = """<system_role>
You are the meta-synthesizer for Board of One. Your role is to integrate insights from multiple
sub-problem deliberations into a cohesive, actionable recommendation.

You have access to synthesis reports from {sub_problem_count} expert deliberations on different
aspects of the user's problem.
</system_role>

<original_problem>
{original_problem}
</original_problem>

<sub_problem_deliberations>
{all_sub_problem_syntheses}
</sub_problem_deliberations>

<task>
Create a comprehensive meta-synthesis that:

1. **Executive Summary** (2-3 sentences)
   - What is the overall recommendation?
   - What are the key trade-offs?

2. **Sub-Problem Insights** (one paragraph per sub-problem)
   - Summarize each sub-problem's recommendation
   - Highlight confidence levels and conditions

3. **Integration Analysis**
   - Are there tensions between sub-problem recommendations?
   - Do recommendations from different sub-problems reinforce each other?
   - What sequencing or dependencies exist in implementation?

4. **Unified Action Plan**
   - Concrete next steps in priority order
   - Which sub-problem recommendations to implement first
   - What to do if recommendations conflict

5. **Risk Assessment**
   - What could go wrong?
   - What assumptions are being made?
   - When should the user revisit this decision?

Use <thinking> tags for analysis, then provide synthesis in clear markdown.
</task>
"""
```

---

## Testing Strategy

### Unit Tests
- `test_next_subproblem_node()` - Iteration logic
- `test_route_after_synthesis()` - Routing logic
- `test_analyze_dependencies()` - Dependency graph parsing

### Integration Tests
- `test_sequential_two_subproblems()` - Simplest multi-sub-problem case
- `test_sequential_five_subproblems()` - Max complexity
- `test_different_experts_per_subproblem()` - Persona selection variation
- `test_meta_synthesis_quality()` - Validates meta-synthesis includes all sub-problems

### End-to-End Tests
- **Scenario**: "Should I invest $50K in SEO or paid ads?" (3 sub-problems: CAC targets, channel fit, execution capacity)
  - Verify: 3 separate deliberations with different expert panels
  - Verify: Meta-synthesis integrates all 3
  - Verify: Cost tracked per sub-problem

---

## Open Questions

1. **Sub-Problem Limits**: Should we warn if >3 sub-problems? (UX: too much deliberation)
   - **Answer (2025-01-16)**: Keep max at 5 as designed. Decomposer prompt already guides toward 1-5 with rationale.

2. **Cost Caps**: Should cost limit apply per sub-problem or total across all?
   - **Answer (2025-01-16)**: Total across all. Cost guard checks `total_cost` which accumulates across sub-problems.

3. **Expert Reuse**: If same expert recommended for multiple sub-problems, do they "remember" previous sub-problem context?
   - **INTEGRATED INTO PHASE 1** (2025-01-16): Experts receive 50-100 token summaries of their previous sub-problem contributions.
   - **See**: `zzz_project/detail/CROSS_SUBPROBLEM_EXPERT_MEMORY.md` for full specification.
   - **Cost**: ~$0.012 per multi-sub-problem session (3% increase).
   - **Value**: Prevents contradictions, enables experts to build on earlier analysis.

4. **Atomic Sub-Problem Optimization**: If only 1 sub-problem, skip next_subproblem and meta_synthesis nodes?
   - **Answer (2025-01-16)**: Yes, route directly to END after synthesis if `len(problem.sub_problems) == 1`.

5. **User Override**: Should user be able to skip certain sub-problems? ("Just deliberate sp_001 and sp_003, skip sp_002")
   - **Deferred**: Not for MVP. Add in Week 8-9 as "sub-problem selection" feature in web UI.

6. **Dependency Execution**: When should parallel execution be implemented?
   - **Answer (2025-01-16)**: Phase 2 (Week 7-8) for web UI only. Console remains sequential.
   - **Rationale**: Parallel execution requires non-blocking HITL (web UI), dependency graph visualization, and complex coordination.

---

## Roadmap Impact

**Week 6 (Days 36-42)**: Implement Phase 1 (Sequential) before Web API launch
- Day 37: Add iteration logic (next_subproblem_node, router)
- Day 38: Implement meta-synthesis node + prompt
- Day 39: Console display updates + progress tracking
- Day 40: Testing (2 sub-problems, 5 sub-problems)

**Week 7-8**: Implement Phase 2 (Dependencies + Parallel) for web UI
- Requires web UI for non-blocking HITL
- Dependency graph visualization
- Parallel execution support

**Week 9**: Implement Phase 3 (Per-sub-problem HITL)
- Context collection per sub-problem
- Pause/resume per sub-problem

---

## Success Criteria

✅ **Phase 1 Complete** when:
- [ ] User can deliberate 2-5 sub-problems sequentially
- [ ] Each sub-problem gets different expert panel
- [ ] Meta-synthesis integrates insights from all sub-problems
- [ ] Cost tracked per sub-problem
- [ ] Pause/resume works across sub-problems
- [ ] Console shows clear progress ("Sub-problem 2 of 4")

✅ **Phase 2 Complete** when:
- [ ] Independent sub-problems deliberated in parallel (web only)
- [ ] Dependencies enforced (sp_002 waits for sp_001 if dependency exists)
- [ ] Dependency graph visualized in web UI

✅ **Phase 3 Complete** when:
- [ ] Context collection happens per sub-problem (not just once)
- [ ] Clarifications targeted to specific sub-problem
- [ ] User can pause individual sub-problems in parallel execution

---

## References

- `bo1/models/problem.py` - SubProblem, Problem models
- `bo1/agents/decomposer.py` - Decomposition logic
- `bo1/graph/nodes.py` - Node implementations
- `bo1/graph/routers.py` - Routing logic
- `zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` - Week 6-9 timeline
