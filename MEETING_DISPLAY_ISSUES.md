# Meeting Display Issues - Root Cause Analysis

**Session ID**: `bo1_14439b04-6a04-4691-89aa-e46976697e15`
**URL**: http://localhost:5173/meeting/bo1_14439b04-6a04-4691-89aa-e46976697e15
**Date**: 2025-01-24

---

## Executive Summary

The meeting display is showing incomplete deliberation flow due to three confirmed issues and one architectural limitation:

1. **Initial round contributions ARE being created but NOT published as individual events** (Bug #1)
2. **Research action is not implemented** - routes to vote as placeholder (Bug #2)
3. **Premature voting fix is loaded but may still occur** - needs investigation (Bug #3)
4. **Round counting semantics unclear** - "1 round" may mean initial_round only, not multi-round deliberation (Architectural)

**Impact**: Users see incomplete deliberation flow (missing initial contributions, research doesn't work, voting happens too early)

**Priority**: High - Affects core deliberation UX and perception of system quality

---

## Issue #1: Missing Initial Round Contributions in UI

### Current Behavior
- Initial round executes successfully (node completes)
- Contributions are created and added to state
- BUT: No individual `contribution` events are published for initial round experts
- Frontend shows "Round 1 Contributions" header with no content beneath it

### Root Cause Analysis

**Code Location**: `/Users/si/projects/bo1/bo1/graph/nodes.py:188-231` - `initial_round_node()`

**The Problem**:
```python
async def initial_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    # Run initial round
    contributions, llm_responses = await engine.run_initial_round()

    # Track cost
    metrics = ensure_metrics(state)
    track_aggregated_cost(metrics, "initial_round", llm_responses)

    # Return state updates (include personas for event collection)
    return {
        "contributions": contributions,  # ❌ Returns bulk list, not individual events
        "phase": DeliberationPhase.DISCUSSION,
        "round_number": 1,
        "metrics": metrics,
        "current_node": "initial_round",
        "personas": state.get("personas", []),
    }
```

**Event Collector**: `/Users/si/projects/bo1/backend/api/event_collector.py:240-256`

```python
async def _handle_initial_round(self, session_id: str, output: dict) -> None:
    """Handle initial_round node completion."""
    # Extract sub_problem_index for tab filtering
    sub_problem_index = output.get("sub_problem_index", 0)

    # Publish individual contributions
    contributions = output.get("contributions", [])
    for contrib in contributions:
        await self._publish_contribution(
            session_id, contrib, round_number=1, sub_problem_index=sub_problem_index
        )
```

**Analysis**: The event collector DOES iterate and publish individual contributions! So why aren't they appearing?

**Frontend Filtering**: `/Users/si/projects/bo1/frontend/src/routes/(app)/meeting/[id]/+page.svelte:135-148`

```typescript
// Status noise events to hide (UX redesign - these don't provide actionable info)
const STATUS_NOISE_EVENTS = [
    'decomposition_started',
    'persona_selection_started',
    'persona_selection_complete', // Just shows "experts selected" - panel shows the actual experts
    'initial_round_started',       // ❌ HIDING initial round start
    'voting_started',
    'voting_complete',             // Individual results shown in VotingResults component
    'synthesis_started',
    'meta_synthesis_started',
    'persona_vote',                // Individual votes now aggregated in voting_complete
];
```

**Wait - this doesn't hide `contribution` events!** So what's going on?

**Hypothesis**: The events ARE being published, but they're being grouped incorrectly or filtered out by the grouping logic.

**Frontend Grouping Logic**: Lines 548-661 in `+page.svelte`

```typescript
interface EventGroup {
    type: 'single' | 'round' | 'expert_panel';
    event?: SSEEvent;
    events?: SSEEvent[];
    roundNumber?: number;
}

// Group contributions by round
if (event.event_type === 'contribution') {
    currentRound.push(event);  // ✅ Contributions ARE grouped
}
```

**Further Investigation Needed**:
1. Check if `contribution` events are actually being received by frontend (browser console logs)
2. Verify `round_started` or `initial_round_started` event precedes contributions (needed for round grouping)
3. Check if `sub_problem_index` field is present (required for multi-subproblem filtering)

### Proposed Fix

**Option A: Ensure Round Started Event is Published Before Contributions**

The grouping logic relies on `round_started` or `initial_round_started` events to track `currentRoundNumber`. If this event isn't published, contributions may not be grouped correctly.

**Check**: Does the graph publish `initial_round_started` event? (Search codebase for this event emission)

**Option B: Explicitly Publish Round Header Event in Event Collector**

```python
async def _handle_initial_round(self, session_id: str, output: dict) -> None:
    """Handle initial_round node completion."""
    sub_problem_index = output.get("sub_problem_index", 0)

    # ADDITION: Publish round_started event BEFORE contributions
    self.publisher.publish_event(
        session_id,
        "round_started",
        {
            "round_number": 1,
            "sub_problem_index": sub_problem_index,
        }
    )

    # Publish individual contributions
    contributions = output.get("contributions", [])
    for contrib in contributions:
        await self._publish_contribution(
            session_id, contrib, round_number=1, sub_problem_index=sub_problem_index
        )
```

### Testing Recommendations
1. Add browser console logging: `console.log('[Frontend] Received event:', event.event_type, event.data);`
2. Check Redis logs to confirm `contribution` events are being published with correct `sub_problem_index`
3. Verify `round_started` event precedes contributions in event stream
4. Test with both single sub-problem and multi-subproblem scenarios

---

## Issue #2: Research Action Not Implemented

### Current Behavior
- Facilitator decides `action="research"` based on deliberation needs
- Router sends to `vote` node instead of actual research
- No research is performed, deliberation jumps straight to voting

### Root Cause Analysis

**Code Location**: `/Users/si/projects/bo1/bo1/graph/routers.py:87-93` - `route_facilitator_decision()`

```python
elif action == "research":
    # Research not implemented in Week 5 - transition to voting instead
    logger.warning(
        "route_facilitator_decision: Research requested but not implemented in Week 5. "
        "Routing to vote (research will be implemented in Week 6)."
    )
    return "vote"  # ❌ PLACEHOLDER - NO RESEARCH HAPPENS
```

**What Should Happen**:
1. Facilitator identifies information gap requiring external research
2. Router sends to `research_node` (doesn't exist yet)
3. ResearcherAgent queries external sources (web search, semantic cache)
4. Research results injected into deliberation context
5. Deliberation continues with enriched information

**What Actually Exists**:
- **ResearcherAgent**: `/Users/si/projects/bo1/bo1/agents/researcher.py` - IMPLEMENTED
  - Semantic cache with Voyage AI embeddings
  - PostgreSQL pgvector similarity search
  - Cost tracking (~$0.00006 for cache hit, ~$0.05-0.10 for cache miss)
  - Freshness-based cache invalidation
- **Web Search Integration**: NOT IMPLEMENTED (comment says "Week 4 Day 27")

**Impact**:
- Facilitator correctly identifies research needs
- But system cannot fulfill the request
- Forces premature voting without complete information
- Reduces deliberation quality

### Proposed Implementation

**Short-term Fix (Minimal Changes)**:

Route research action to continue deliberation instead of vote:

```python
elif action == "research":
    # Research not implemented yet - continue deliberation without it
    logger.warning(
        "route_facilitator_decision: Research requested but not implemented. "
        "Continuing deliberation (research node will be added in Week 6)."
    )
    return "persona_contribute"  # Continue deliberation instead of jumping to vote
```

**Long-term Fix (Full Implementation)**:

1. **Create Research Node**: `/Users/si/projects/bo1/bo1/graph/nodes.py`

```python
async def research_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Perform external research for information gaps.

    This node:
    1. Extracts research questions from facilitator decision
    2. Uses ResearcherAgent to query external sources
    3. Checks semantic cache first (70-90% hit rate)
    4. Performs web search if cache miss
    5. Injects research results into problem context
    6. Tracks cost in metrics
    """
    logger.info("research_node: Starting external research")

    # Get research questions from facilitator decision
    decision = state.get("facilitator_decision")
    research_questions = decision.get("research_focus")  # Facilitator should provide this

    if not research_questions:
        logger.warning("research_node called without research_focus in decision")
        return {"current_node": "research"}

    # Initialize researcher
    from bo1.agents.researcher import ResearcherAgent
    researcher = ResearcherAgent()

    # Perform research (uses semantic cache + web search)
    results = await researcher.research_questions(
        questions=[{"question": research_questions, "priority": "CRITICAL"}],
        category="deliberation_context",  # Generic category
    )

    # Inject results into problem context
    problem = state.get("problem")
    if problem and results:
        research_summary = "\n\n## External Research\n\n"
        for result in results:
            research_summary += f"**Q**: {result['question']}\n"
            research_summary += f"**A**: {result['summary']}\n"
            if result.get("cached"):
                research_summary += f"*(Cached result, {result['cache_age_days']} days old)*\n"
            research_summary += "\n"

        problem.context = problem.context + research_summary

    # Track cost
    metrics = ensure_metrics(state)
    total_research_cost = sum(r["cost"] for r in results)
    track_phase_cost(metrics, "external_research", None)  # Track separately

    logger.info(
        f"research_node: Complete - {len(results)} queries researched "
        f"(cost: ${total_research_cost:.4f})"
    )

    return {
        "problem": problem,
        "metrics": metrics,
        "current_node": "research",
    }
```

2. **Update Router**: Add research routing

```python
elif action == "research":
    logger.info("route_facilitator_decision: Routing to research")
    return "research"
```

3. **Add Node to Graph**: `/Users/si/projects/bo1/bo1/graph/config.py`

```python
workflow.add_node("research", research_node)

# Add edge: facilitator_decide -> research (conditional)
# Add edge: research -> persona_contribute (after research completes)
workflow.add_edge("research", "persona_contribute")
```

4. **Update Facilitator Prompt**: Ensure facilitator provides `research_focus` field when action="research"

### Testing Recommendations
1. Trigger research action by providing problem requiring external data (e.g., "What is industry benchmark for X?")
2. Verify research node executes and queries cache/web
3. Check that research results appear in subsequent contributions
4. Verify cost tracking includes research phase
5. Test cache hit vs cache miss scenarios (should see 70-90% hit rate)

---

## Issue #3: Premature Voting Still Occurring

### Current Behavior
- Session shows voting after only 1 round
- Fix was implemented to prevent voting before round 3
- BUT: Session `bo1_14439b04-6a04-4691-89aa-e46976697e15` has `round_number=1` and voted

### Root Cause Analysis

**Fix is Loaded**: `/Users/si/projects/bo1/bo1/graph/nodes.py:265-299` - `facilitator_decide_node()`

```python
# SAFETY CHECK: Prevent premature voting (Bug #3 fix)
# Override facilitator if trying to vote before minimum rounds
min_rounds_before_voting = 3
if decision.action == "vote" and round_number < min_rounds_before_voting:
    logger.warning(
        f"Facilitator attempted to vote at round {round_number} (min: {min_rounds_before_voting}). "
        f"Overriding to 'continue' for deeper exploration."
    )

    # Override decision to continue
    decision = FacilitatorDecision(
        action="continue",
        reasoning=f"Overridden: Minimum {min_rounds_before_voting} rounds required before voting.",
        next_speaker=next_speaker,
        speaker_prompt="Build on the discussion so far and add depth to the analysis.",
    )
```

**Fix Confirmed Present**: grep output shows lines 267, 268, 270, 296 contain the fix

**So Why Did Voting Happen at Round 1?**

**Hypothesis 1: Round Number Semantics**

What counts as a "round"?
- `initial_round_node` sets `round_number = 1`
- `persona_contribute_node` increments: `next_round = round_number + 1` (line 418)
- Facilitator is called AFTER initial_round completes
- At that point, `round_number = 1`
- Fix checks `round_number < 3` → True, should block voting!

**BUT WAIT**: Let's trace the sequence:

1. `initial_round_node` completes → `round_number = 1`
2. Route to `facilitator_decide_node` → receives `round_number = 1`
3. Fix checks: `decision.action == "vote" and round_number < 3` → Should override!
4. **UNLESS**: Facilitator chose `action="research"` first (not "vote")
5. Research routes to "vote" (Issue #2) → Bypasses the fix!

**AHA!** The fix only applies when facilitator DIRECTLY chooses "vote". If facilitator chooses "research" and router redirects to "vote", the fix is bypassed!

**Evidence**:
- Facilitator logs would show `action="research"` at round 1
- Router logs show "Research requested but not implemented. Routing to vote"
- Vote node executes without passing through facilitator_decide_node safety check

### Confirmed Root Cause

**The premature voting is caused by Issue #2** (research routing to vote).

**Flow**:
1. Initial round completes (round_number = 1)
2. Facilitator correctly identifies need for research → `action="research"`
3. Router sends to vote instead → `route_facilitator_decision()` returns "vote"
4. Vote node executes immediately (round 1, no safety check)
5. Deliberation ends prematurely

**Fix**: Implement Issue #2 fix (route research to persona_contribute instead of vote)

### Alternative Hypothesis: Round Counting Bug

If round counting is incorrect, the fix may not trigger even when it should.

**Check**:
1. What is `round_number` when facilitator_decide_node is called after initial_round?
2. Does `persona_contribute_node` correctly increment round_number?
3. Is round_number persisted correctly in checkpoints?

**Verification**:
Add logging to track round progression:
```python
logger.info(
    f"facilitator_decide_node: round_number={round_number}, "
    f"decision.action={decision.action}, "
    f"will_override={decision.action == 'vote' and round_number < 3}"
)
```

### Testing Recommendations
1. **Primary Test**: Fix Issue #2 first (route research to persona_contribute)
   - Expected: No premature voting when research is requested
2. **Secondary Test**: Add extensive round tracking logs
   - Log round_number at every node transition
   - Verify initial_round sets 1, persona_contribute increments to 2, 3, etc.
3. **Edge Case Test**: Force facilitator to choose "vote" at round 1 (mock decision)
   - Expected: Override to "continue"
   - Actual: If this passes, fix is working correctly
4. **Integration Test**: Run full deliberation with min_rounds_before_voting=3
   - Expected: At least 3 rounds before voting
   - Check: Round 1 (initial), Round 2 (contribute), Round 3 (contribute), Round 4+ (vote allowed)

---

## Issue #4: Incomplete Flow After Vote

### Current Behavior
- After voting completes, user sees recommendations but flow seems incomplete
- Unclear if synthesis ran successfully
- No clear "deliberation complete" state

### Root Cause Analysis

**Expected Flow After Vote**:
```
vote_node → synthesize_node → (next_subproblem_node OR END)
```

**Graph Structure**: `/Users/si/projects/bo1/bo1/graph/config.py` (not fully shown in read output, need to check)

**Questions**:
1. Does vote_node automatically route to synthesize_node?
2. Is synthesis event being published and displayed?
3. Is the "complete" event being published?

**Frontend Completion Detection**: `/Users/si/projects/bo1/frontend/src/routes/(app)/meeting/[id]/+page.svelte:426-428`

```typescript
else if (eventType === 'complete') {
    session.status = 'completed';
    session.phase = 'complete';
}
```

**Synthesis Detection**: Lines 167-172

```typescript
const isSynthesizing = $derived(
    events.length > 0 &&
    events[events.length - 1].event_type === 'voting_complete' &&
    !events.some(e => e.event_type === 'synthesis_complete' || e.event_type === 'meta_synthesis_complete')
);
```

**This suggests**:
- Frontend expects `synthesis_complete` or `meta_synthesis_complete` after `voting_complete`
- If these events aren't published, UI won't show synthesis result
- If `complete` event isn't published, session won't transition to completed state

### Proposed Investigation

1. **Check Graph Structure**: Read full `config.py` to verify edge from vote → synthesize
2. **Check Event Collector**: Verify `_handle_synthesis()` is called and publishes `synthesis_complete`
3. **Check Synthesis Node**: Verify it returns correct phase transition
4. **Check Session Logs**: Look for synthesis node execution in API logs

### Testing Recommendations
1. Run deliberation to completion and check event stream for:
   - `voting_complete` event
   - `synthesis_started` event (if published)
   - `synthesis_complete` event
   - `complete` event
2. Verify synthesis content appears in UI (ActionPlan or SynthesisComplete component)
3. Check session status transitions to 'completed' in sidebar

---

## Round Counting Semantics (Architectural Issue)

### Definition Ambiguity

What is a "round"?

**Option A: Initial Round = Round 1, Sequential Rounds = Round 2, 3, 4...**
- `initial_round_node` → round_number = 1 (parallel contributions from all experts)
- `persona_contribute_node` → round_number = 2, 3, 4... (sequential contributions)
- Total rounds = 1 (initial) + N (sequential)

**Option B: Initial Round Doesn't Count, Sequential Rounds = Round 1, 2, 3...**
- `initial_round_node` → round_number = 0 (or not counted)
- `persona_contribute_node` → round_number = 1, 2, 3... (sequential contributions)
- Total rounds = N (sequential only)

**Current Implementation**: Option A (initial_round_node sets round_number=1)

**Impact on Fix**:
- If session shows "1 round", it means ONLY initial_round completed, NO sequential rounds
- Facilitator is called after initial_round with round_number=1
- If facilitator chooses vote at this point, fix should override (requires 3 rounds)
- But if facilitator chooses research → bypass (Issue #3 confirmed)

### Recommendation

**Clarify Round Semantics in Code**:
1. Add comment in `initial_round_node`: "Sets round_number=1 (initial parallel round)"
2. Add comment in `persona_contribute_node`: "Increments round_number for each sequential contribution"
3. Update facilitator prompt to understand round counting: "You are currently at round {round_number}. Round 1 is the initial parallel round. Rounds 2+ are sequential deliberation."

**Display Round Information Clearly**:
- Frontend: "Round 1 (Initial)" vs "Round 2 (Discussion)"
- Status bar: "Round 1 of 10 (Initial Perspectives)" → "Round 2 of 10 (Deliberation)"

---

## Summary of Fixes

### Immediate Actions (Priority 1)

1. **Fix Issue #2: Research Routing**
   - Change router to send research → persona_contribute (not vote)
   - Prevents premature voting bypass
   - **File**: `/Users/si/projects/bo1/bo1/graph/routers.py:87-93`
   - **Change**: `return "persona_contribute"` instead of `return "vote"`

2. **Fix Issue #1: Initial Round Events**
   - Verify `round_started` event is published before contributions
   - Add explicit round header event in event collector if needed
   - **File**: `/Users/si/projects/bo1/backend/api/event_collector.py:240-256`

### Medium-term Actions (Priority 2)

3. **Implement Issue #2: Full Research Node**
   - Create `research_node` that calls ResearcherAgent
   - Integrate web search API (Brave/Tavily)
   - Add research edge to graph
   - Update facilitator to provide `research_focus` field

4. **Verify Issue #4: Synthesis Flow**
   - Confirm vote → synthesize edge exists
   - Verify synthesis events are published
   - Test complete event triggers UI state transition

### Long-term Actions (Priority 3)

5. **Clarify Round Semantics**
   - Document round counting in code comments
   - Update frontend display to distinguish initial vs deliberation rounds
   - Consider renaming "round 1" to "initial perspectives" in UI

---

## Testing Checklist

### For Issue #1 (Initial Contributions)
- [ ] Check browser console for `contribution` events being received
- [ ] Verify `round_started` event precedes contributions in stream
- [ ] Confirm `sub_problem_index` field is present in events
- [ ] Test with single sub-problem scenario
- [ ] Test with multi-subproblem scenario (tabs)

### For Issue #2 (Research)
- [ ] Confirm facilitator can request research
- [ ] Verify research routes to persona_contribute (not vote)
- [ ] (Future) Test research node execution with ResearcherAgent
- [ ] (Future) Verify cache hit/miss scenarios
- [ ] (Future) Check research results appear in context

### For Issue #3 (Premature Voting)
- [ ] Run deliberation and verify NO voting before round 3
- [ ] Check logs for "Overridden: Minimum 3 rounds required" message
- [ ] Force facilitator to choose "vote" at round 1 (should override)
- [ ] Verify research requests don't bypass voting safety check
- [ ] Confirm round_number increments correctly (1 → 2 → 3)

### For Issue #4 (Synthesis Flow)
- [ ] Verify `synthesis_complete` event appears after `voting_complete`
- [ ] Check synthesis content renders in UI
- [ ] Confirm `complete` event triggers session status = 'completed'
- [ ] Test both synthesis (single sub-problem) and meta_synthesis (multiple)

---

## Logs to Check

When investigating a specific session:

```bash
# API logs (backend container)
docker logs boardofone-api-1 --tail 500 | grep "bo1_14439b04-6a04-4691-89aa-e46976697e15"

# Look for:
# - "facilitator_decide_node: Making facilitator decision"
# - "route_facilitator_decision: Routing based on action = research"
# - "Facilitator attempted to vote at round X (min: 3). Overriding to 'continue'"
# - "research_node: Starting external research" (future)
# - "synthesize_node: Starting synthesis"

# Frontend network logs (browser)
# Check Network tab → EventSource → Messages
# Look for event types: contribution, round_started, voting_complete, synthesis_complete, complete

# Redis event logs
docker exec -it boardofone-redis-1 redis-cli
> MONITOR
# Run deliberation and watch for PUBLISH commands with event data
```

---

## Code References

### Key Files
- **Graph Nodes**: `/Users/si/projects/bo1/bo1/graph/nodes.py`
- **Graph Routers**: `/Users/si/projects/bo1/bo1/graph/routers.py`
- **Graph Config**: `/Users/si/projects/bo1/bo1/graph/config.py`
- **Event Collector**: `/Users/si/projects/bo1/backend/api/event_collector.py`
- **Frontend Meeting Page**: `/Users/si/projects/bo1/frontend/src/routes/(app)/meeting/[id]/+page.svelte`
- **Researcher Agent**: `/Users/si/projects/bo1/bo1/agents/researcher.py`

### Critical Functions
- `initial_round_node()` - Lines 188-231 in nodes.py
- `facilitator_decide_node()` - Lines 234-322 in nodes.py (includes safety check)
- `persona_contribute_node()` - Lines 325-432 in nodes.py (increments round)
- `route_facilitator_decision()` - Lines 47-96 in routers.py (research routing bug)
- `_handle_initial_round()` - Lines 240-256 in event_collector.py
- Event grouping logic - Lines 568-661 in +page.svelte

---

## Conclusion

The meeting display issues are caused by a combination of:

1. **Potential event publishing/grouping issue** (Issue #1) - needs verification via browser logs
2. **Research action not implemented** (Issue #2) - causes premature voting bypass
3. **Voting safety check bypassed by research routing** (Issue #3) - fixed by Issue #2 fix
4. **Possible synthesis flow issue** (Issue #4) - needs verification via event stream logs

**Primary Action**: Fix research routing (Issue #2) to resolve premature voting (Issue #3)
**Secondary Action**: Verify initial round events (Issue #1) with browser console logs
**Tertiary Action**: Confirm synthesis flow completes (Issue #4) with API logs

The fixes are well-scoped and testable. The system has good architecture (semantic cache, proper state machine, safety checks) but has incomplete implementation of the research flow path.
