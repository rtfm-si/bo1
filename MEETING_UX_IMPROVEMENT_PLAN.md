# Meeting UX Improvement Plan

**Date**: 2025-11-27
**Status**: Investigation Complete, Ready for Implementation
**Version**: 2.0 (Updated with speed optimizations and quality improvements)

This document outlines identified issues with the meeting view and sub-problem system, their root causes, and implementation plans. **Updated to include speed optimizations based on CONSENSUS_BUILDING_RESEARCH.md and prompt quality improvements from PROMPT_ENGINEERING_FRAMEWORK.md.**

## Key Insight: 90% Quality at 3 Minutes > 100% Quality at 15 Minutes

Research shows:
- **Most value comes from rounds 1-3** (90% of insights)
- **Problem drift** is the #1 cause of diminishing returns after round 5
- **Target: 2-3 minutes per sub-problem** (industry standard)
- **Current: 6 rounds max** - can be reduced to 3-4 for simple problems

---

## Table of Contents

### Original Issues (1-10)
1. [SSE Errors on Completed Streams](#1-sse-errors-on-completed-streams)
2. [Hidden Events: discussion_quality_status](#2-hidden-events-discussion_quality_status)
3. [Sub-Problem Tab Content Issues](#3-sub-problem-tab-content-issues)
4. [Expert Panel Not Showing at Sub-Problem Start](#4-expert-panel-not-showing-at-sub-problem-start)
5. [Sub-Problem Conclusion XML Tags](#5-sub-problem-conclusion-xml-tags)
6. [Discussion Quality State Management](#6-discussion-quality-state-management)
7. [Next Speaker Messages](#7-next-speaker-messages)
8. [Summary Scope (Sub-Problem vs Entire Problem)](#8-summary-scope-sub-problem-vs-entire-problem)
9. [Actions Display Per Sub-Problem](#9-actions-display-per-sub-problem)
10. [Sub-Problem Decomposition Quality](#10-sub-problem-decomposition-quality)

### NEW: Speed Optimizations (11-16)
11. [Adaptive Round Limits Based on Complexity](#11-adaptive-round-limits-based-on-complexity)
12. [Early Termination via Semantic Convergence](#12-early-termination-via-semantic-convergence)
13. [Problem Drift Detection](#13-problem-drift-detection)
14. [Deadlock Detection](#14-deadlock-detection)
15. [Reduce Per-Round Latency](#15-reduce-per-round-latency)
16. [Phase-Based Time Boxing](#16-phase-based-time-boxing)

### NEW: Prompt Quality Improvements (17-19)
17. [Prompt Structure Audit](#17-prompt-structure-audit)
18. [Facilitator Decision Prompt Improvements](#18-facilitator-decision-prompt-improvements)
19. [Use Haiku for Supporting Tasks](#19-use-haiku-for-supporting-tasks)

### NEW: Missing Items & UX (20-21)
20. [Verify Original 10 Issues Coverage](#20-verify-original-10-issues-coverage)
21. [Additional UX Issues Identified](#21-additional-ux-issues-identified)

### CRITICAL: Context & Quality (22)
22. [Context Passing Gaps](#critical-context-passing-gaps-issue-22) **← MAJOR QUALITY FIX**

### Implementation & Metrics
- [Revised Implementation Priority](#revised-implementation-priority)
- [Success Metrics](#success-metrics)
- [Appendix: Research References](#appendix-research-references)

---

## 1. SSE Errors on Completed Streams

### Problem
When a user refreshes the page after a meeting completes, the frontend attempts to connect to an SSE stream that's already finished. This causes:
- SSE errors in the console
- Retry attempts (3x with exponential backoff)
- Confusing "Failed to connect" error messages

### Root Cause
**File**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte:361-471`

The frontend connects to SSE unconditionally after loading historical events, even if the session is already completed. The backend doesn't distinguish between "stream closed normally" and "network error".

**Key Issues**:
1. No check for session completion before starting SSE (line 301)
2. Backend closes stream silently without sending explicit "stream_closed" event
3. Frontend's `onError` handler treats all disconnects as failures

### Solution

#### Frontend Changes (`+page.svelte`)

```typescript
// After line 291 (after loadHistoricalEvents)
// Add session completion check
if (session?.status === 'completed' || session?.status === 'failed') {
    // Don't attempt SSE connection for finished sessions
    store.setConnectionStatus('connected'); // Show as connected (data is loaded)
    return;
}
```

#### Add onStall Handler (line 435)

```typescript
sseClient = new SSEClient(`/api/v1/sessions/${sessionId}/stream`, {
    onOpen: () => { /* ... */ },
    onError: (err) => { /* ... */ },
    onStall: async () => {
        // When stalled for 30s, check if session completed
        try {
            const currentSession = await api.getSession(sessionId);
            if (currentSession?.status === 'completed') {
                sseClient?.close();
                store.setConnectionStatus('connected');
                return; // Don't retry - session finished
            }
        } catch { /* ignore */ }
    },
    eventHandlers: { /* ... */ }
});
```

#### Backend Changes (`streaming.py`)

Add explicit stream close event before closing:

```python
# Before line 316 (where we break on complete)
if event_type == "complete":
    yield format_sse_event("stream_closed", {"reason": "session_complete"})
    break
```

---

## 2. Hidden Events: discussion_quality_status

### Problem
`discussion_quality_status` events are displayed in the meeting timeline, adding noise.

### Root Cause
**File**: `frontend/src/routes/(app)/meeting/[id]/lib/eventGrouping.ts:20-30`

The event type is NOT included in `STATUS_NOISE_EVENTS` array.

### Solution

Add to `STATUS_NOISE_EVENTS`:

```typescript
// eventGrouping.ts line 20
export const STATUS_NOISE_EVENTS = [
    'decomposition_started',
    'persona_selection_started',
    'persona_selection_complete',
    'initial_round_started',
    'facilitator_decision',
    'voting_started',
    'voting_complete',
    'convergence',
    'complete',
    'discussion_quality_status',  // ADD THIS
];
```

---

## 3. Sub-Problem Tab Content Issues

### Problem
Multiple content display issues in sub-problem tabs:
- Tab 1 shows decomposition for ALL sub-problems (should be on Summary tab)
- Each tab shows meeting summary meant for other sub-problems
- Actions from all sub-problems appear in each tab

### Root Cause

**Decomposition Issue**:
- **File**: `backend/api/event_extractors.py:284-297`
- `decomposition_complete` event has `sub_problem_index: 0` (hardcoded default)
- Decomposition inherently applies to ALL sub-problems, not sub-problem 0

**Actions Issue**:
- Actions are embedded in `meta_synthesis_complete` event
- This event is global, not per-sub-problem

### Solution

#### 3A: Move Decomposition to Summary Tab

**File**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte`

Add filtering in sub-problem tab event display:

```typescript
// Around line 1160, modify the filter
{@const subGroupedEvents = groupedEvents.filter(group => {
    if (group.type === 'single' && group.event) {
        // SKIP decomposition in sub-problem tabs - it belongs on Summary
        if (group.event.event_type === 'decomposition_complete') {
            return false;
        }
        const eventSubIndex = group.event.data.sub_problem_index as number | undefined;
        return eventSubIndex === tabIndex;
    }
    // ... rest of filter
})}
```

#### 3B: Show Decomposition in Conclusion/Summary Tab

In the Conclusion tab section (line 1132-1153), add decomposition display:

```svelte
{#if showConclusionTab}
    <!-- Problem Decomposition Overview -->
    {#if decompositionEvent}
        <DecompositionComplete event={decompositionEvent} />
    {/if}
    <!-- Rest of conclusion content -->
{/if}
```

#### 3C: Filter Actions Per Sub-Problem

**File**: `frontend/src/lib/components/events/ActionPlan.svelte`

Actions are in `meta_synthesis_complete.recommended_actions`. Currently shows ALL actions.

Option 1: Show all actions but highlight which sub-problem each addresses
Option 2: Filter actions to only show ones relevant to active sub-problem

Recommended: Option 1 (keep all actions visible, add sub-problem badge)

---

## 4. Expert Panel Not Showing at Sub-Problem Start

### Problem
Expert panel selection only displays for multi sub-problem scenarios, not for single sub-problem meetings.

### Root Cause
**File**: `backend/api/event_extractors.py:235-256`

```python
def extract_subproblem_info(output: dict[str, Any]) -> dict[str, Any]:
    # ...
    # Only return data if this is a multi-sub-problem scenario
    if not (problem and hasattr(problem, "sub_problems") and len(problem.sub_problems) > 1):
        return {}  # <-- RETURNS EMPTY FOR SINGLE SUB-PROBLEM
```

This blocks `subproblem_started` event for single sub-problem scenarios.

**File**: `backend/api/event_collector.py:313-321`

```python
subproblem_data = registry.extract("subproblem_started", output)
if subproblem_data:  # <-- ONLY PUBLISHES IF NOT EMPTY
    self.publisher.publish_event(session_id, "subproblem_started", subproblem_data)
```

### Solution

Remove the multi-sub-problem gate in `extract_subproblem_info`:

```python
def extract_subproblem_info(output: dict[str, Any]) -> dict[str, Any]:
    sub_problem_index = output.get("sub_problem_index", 0)
    current_sub_problem = output.get("current_sub_problem")
    problem = output.get("problem")

    # REMOVE this check - always emit subproblem_started
    # if not (problem and hasattr(problem, "sub_problems") and len(problem.sub_problems) > 1):
    #     return {}

    if not current_sub_problem:
        return {}

    return {
        "sub_problem_index": sub_problem_index,
        "sub_problem_id": getattr(current_sub_problem, "id", ""),
        "goal": getattr(current_sub_problem, "goal", ""),
        "total_sub_problems": len(problem.sub_problems) if problem and hasattr(problem, "sub_problems") else 1,
    }
```

---

## 5. Sub-Problem Conclusion XML Tags

### Problem
Sub-problem conclusions display raw XML tags like `<thinking>`, `<executive_summary>`, etc.

### Root Cause
**File**: `frontend/src/lib/components/events/SubProblemProgress.svelte:75-100`

The component displays synthesis as raw text without parsing:

```svelte
{event.data.synthesis}  <!-- DISPLAYS RAW XML TAGS -->
```

Compare with `SynthesisComplete.svelte:18-19` which DOES parse XML:

```svelte
const isXML = $derived(isXMLFormatted(event.data.synthesis));
const sections = $derived(isXML ? parseSynthesisXML(event.data.synthesis) : null);
```

### Solution

Update `SubProblemProgress.svelte` to use XML parser:

```svelte
<script lang="ts">
    import { parseSynthesisXML, isXMLFormatted } from '$lib/utils/xml-parser';

    // ... existing code ...

    // Add XML parsing
    const isXML = $derived(event.data.synthesis ? isXMLFormatted(event.data.synthesis) : false);
    const sections = $derived(isXML ? parseSynthesisXML(event.data.synthesis) : null);
</script>

<!-- In template, replace raw synthesis display -->
{#if hasSynthesis}
    <div class="mb-4 p-3 bg-white/50 dark:bg-neutral-800/50 rounded-lg">
        <h4 class="text-sm font-semibold mb-2">Conclusion</h4>
        {#if sections}
            {#if sections.executive_summary}
                <div class="text-sm text-neutral-700 dark:text-neutral-300 prose prose-sm">
                    {sections.executive_summary}
                </div>
            {/if}
            {#if sections.recommendation}
                <div class="mt-2 p-2 bg-green-50 dark:bg-green-900/20 rounded text-sm">
                    <span class="font-medium">Recommendation:</span> {sections.recommendation}
                </div>
            {/if}
        {:else}
            <!-- Fallback for non-XML synthesis -->
            <div class="text-sm text-neutral-700 dark:text-neutral-300 prose prose-sm">
                {event.data.synthesis}
            </div>
        {/if}
    </div>
{/if}
```

---

## 6. Discussion Quality State Management

### Problem
Discussion quality metrics show values from sub-problem 1 for ALL sub-problems. The quality indicators don't update per sub-problem.

### Root Cause
**File**: `bo1/graph/nodes.py:2251-2387`

The `_deliberate_subproblem()` function hardcodes `sub_problem_index=0`:

```python
async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    user_id: str | None = None,  # NOTE: No sub_problem_index parameter!
) -> SubProblemResult:
    # ...
    mini_state = DeliberationGraphState(
        # ...
        sub_problem_index=0,  # <-- ALWAYS 0!
    )
```

This means ALL convergence/quality events are published with `sub_problem_index: 0`.

### Solution

#### Step 1: Add parameter to function signature (nodes.py:2251)

```python
async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    sub_problem_index: int,  # ADD THIS
    user_id: str | None = None,
) -> SubProblemResult:
```

#### Step 2: Use parameter in mini_state creation (nodes.py:2387)

```python
mini_state = DeliberationGraphState(
    # ...
    sub_problem_index=sub_problem_index,  # USE PARAMETER
)
```

#### Step 3: Pass index at call site (nodes.py:2651)

```python
task = _deliberate_subproblem(
    sub_problem=sub_problem,
    problem=problem,
    all_personas=all_personas,
    previous_results=all_results,
    sub_problem_index=sp_index,  # ADD THIS
    user_id=user_id,
)
```

---

## 7. Next Speaker Messages

### Problem
"Next speaker" or "hold on, more content is coming" messages don't appear frequently or quickly enough. The yellow label system used at meeting start should be used throughout.

### Current State
- **File**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte:554-693`
- Thinking indicators exist but only show AFTER all contributions in a round are revealed
- `facilitator_decision` events contain `next_speaker` but are filtered as STATUS_NOISE_EVENTS
- Between-rounds messages rotate every 3 seconds (too slow for perceived responsiveness)

### Solution

#### 7A: Use Yellow Badge for Next Speaker Announcements

Create a new component for consistent "next speaker" display:

**File**: `frontend/src/lib/components/ui/NextSpeakerBadge.svelte`

```svelte
<script lang="ts">
    interface Props {
        speakerName: string;
        message?: string;
    }

    let { speakerName, message = 'is preparing insights...' }: Props = $props();
</script>

<div class="flex items-center gap-2 py-2 px-3 bg-yellow-50 dark:bg-yellow-900/20
            border border-yellow-200 dark:border-yellow-800 rounded-lg animate-pulse">
    <div class="w-2 h-2 bg-yellow-500 rounded-full"></div>
    <span class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
        {speakerName} {message}
    </span>
</div>
```

#### 7B: Show Next Speaker After Each Contribution

When a contribution is revealed, immediately show who's next:

```svelte
<!-- In the round contributions reveal loop -->
{#each visibleContributions as contribution, i}
    <ExpertPerspectiveCard event={contribution} />

    <!-- Show next speaker indicator -->
    {#if i === visibleContributions.length - 1 && pendingContributions.length > 0}
        <NextSpeakerBadge
            speakerName={pendingContributions[0].data.persona_name}
        />
    {/if}
{/each}
```

#### 7C: Reduce Message Rotation Interval

Change from 3000ms to 1500ms for more dynamic feel:

```typescript
// Line 679
betweenRoundsInterval = setInterval(() => {
    betweenRoundsMessageIndex = (betweenRoundsMessageIndex + 1) % betweenRoundsMessages.length;
}, 1500);  // Changed from 3000
```

---

## 8. Summary Scope (Sub-Problem vs Entire Problem)

### Problem
Unclear if "previous summary" shown is for the sub-problem or entire problem.

### Current Behavior
- `synthesis_complete` event per sub-problem contains that sub-problem's synthesis
- `meta_synthesis_complete` contains cross-problem synthesis
- `subproblem_complete` contains per-sub-problem conclusion

### Verification Steps

Check backend logs for:
```bash
ssh root@139.59.201.65
docker logs boardofone-api-1 2>&1 | grep -i "synthesis\|subproblem_complete"
```

### Solution

Add clear labels to distinguish summary types:

```svelte
<!-- For sub-problem synthesis -->
<div class="border-l-4 border-blue-500 pl-3">
    <span class="text-xs text-blue-600 uppercase font-bold">Sub-Problem {index + 1} Synthesis</span>
    <!-- synthesis content -->
</div>

<!-- For meta synthesis -->
<div class="border-l-4 border-purple-500 pl-3">
    <span class="text-xs text-purple-600 uppercase font-bold">Overall Meeting Synthesis</span>
    <!-- meta synthesis content -->
</div>
```

---

## 9. Actions Display Per Sub-Problem

### Problem
Actions from ALL sub-problems appear in each sub-problem tab.

### Root Cause
Actions are stored in `meta_synthesis_complete` event which is global, not per-sub-problem.

### Solution

#### Option A: Filter Actions by Sub-Problem Reference

The `recommended_actions` array includes rationale that references sub-problems:

```json
{
    "action": "...",
    "rationale": "Market viability analysis (sub-problem 1) confirmed..."
}
```

Parse rationale to identify which sub-problem an action relates to:

```typescript
function filterActionsForSubProblem(actions: Action[], subProblemIndex: number): Action[] {
    return actions.filter(action => {
        const match = action.rationale.match(/sub-problem\s*(\d+)/gi);
        if (!match) return true; // Show actions without sub-problem reference in all tabs
        return match.some(m => parseInt(m.replace(/\D/g, '')) === subProblemIndex + 1);
    });
}
```

#### Option B: Add Sub-Problem Index to Actions (Backend Change)

Modify `META_SYNTHESIS_ACTION_PLAN_PROMPT` to include sub-problem indices:

```json
{
    "action": "...",
    "sub_problem_indices": [0, 2],  // ADD THIS FIELD
    "rationale": "..."
}
```

---

## 10. Sub-Problem Decomposition Quality

### Problem
Sub-problems are too loosely defined. They need:
- Specific, focused questions
- Clear deliverables
- Defined risks to mitigate
- Alternatives to consider
- Targeted expert requirements

### Current Decomposition Structure
**File**: `bo1/models/problem.py:51-87`

```python
class SubProblem(BaseModel):
    id: str
    goal: str  # Just a string - too vague
    context: str
    complexity_score: int
    dependencies: list[str]
    constraints: list[Constraint]
```

### Solution: Enhanced Sub-Problem Structure

#### Step 1: Extend SubProblem Model

```python
class SubProblemFocus(BaseModel):
    """Specific areas to address in this sub-problem"""
    key_questions: list[str]  # Specific questions to answer
    risks_to_mitigate: list[str]  # Risks that must be addressed
    alternatives_to_consider: list[str]  # Options to evaluate
    required_expertise: list[str]  # Types of experts needed
    success_criteria: list[str]  # How we know this is solved

class SubProblem(BaseModel):
    id: str
    goal: str  # High-level goal
    focus: SubProblemFocus  # NEW: Detailed focus areas
    context: str
    complexity_score: int
    dependencies: list[str]
    constraints: list[Constraint]
```

#### Step 2: Update Decomposition Prompt

**File**: `bo1/prompts/decomposer_prompts.py`

Add to system prompt:

```
For each sub-problem, you must define:

1. **goal**: A clear, specific question that can be answered (not a vague topic)
   - BAD: "Think about market position"
   - GOOD: "What pricing strategy maximizes revenue while maintaining competitiveness?"

2. **focus.key_questions**: 3-5 specific questions experts must answer
   - Example: ["What is the market size?", "Who are the key competitors?", "What's our differentiation?"]

3. **focus.risks_to_mitigate**: 2-4 risks that must be addressed
   - Example: ["Market saturation risk", "Technology obsolescence", "Regulatory changes"]

4. **focus.alternatives_to_consider**: 2-3 alternatives to evaluate
   - Example: ["Premium pricing vs volume pricing", "Direct sales vs channel partners"]

5. **focus.required_expertise**: Types of experts needed for this specific sub-problem
   - Example: ["Financial analyst", "Market researcher", "Legal counsel"]

6. **focus.success_criteria**: How we know this sub-problem is resolved
   - Example: ["Clear pricing recommendation with rationale", "Risk mitigation plan"]
```

#### Step 3: Use Focus in Persona Selection

**File**: `bo1/agents/persona_selector.py`

Include `focus.required_expertise` in persona selection prompt:

```python
prompt = f"""
Select experts for this sub-problem:
Goal: {sub_problem.goal}

Required expertise areas: {', '.join(sub_problem.focus.required_expertise)}

Ensure selected experts can address:
- Questions: {sub_problem.focus.key_questions}
- Risks: {sub_problem.focus.risks_to_mitigate}
"""
```

#### Step 4: Use Focus in Facilitation

**File**: `bo1/graph/nodes.py` (facilitator_decide_node)

Use `focus.key_questions` to track which questions have been addressed:

```python
# Track which key questions have been answered
questions_addressed = []
for question in current_sub_problem.focus.key_questions:
    if is_question_addressed(question, contributions):
        questions_addressed.append(question)

# Include in facilitator prompt
facilitator_prompt = f"""
Key questions for this sub-problem:
{format_questions(current_sub_problem.focus.key_questions)}

Questions addressed so far:
{format_questions(questions_addressed)}

Questions still needing attention:
{format_questions(remaining_questions)}

Call on experts who can address remaining questions.
"""
```

#### Step 5: Validate Synthesis Addresses Focus

**File**: `bo1/graph/nodes.py` (synthesize_node)

Include focus areas in synthesis prompt:

```python
synthesis_prompt = f"""
This sub-problem's focus was:
- Key Questions: {current_sub_problem.focus.key_questions}
- Risks to Mitigate: {current_sub_problem.focus.risks_to_mitigate}
- Alternatives Considered: {current_sub_problem.focus.alternatives_to_consider}

Your synthesis MUST:
1. Answer each key question explicitly
2. Address each identified risk
3. Evaluate the alternatives
4. Meet the success criteria: {current_sub_problem.focus.success_criteria}
"""
```

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours each)
1. [Issue #2] Hide `discussion_quality_status` events - 1 line change
2. [Issue #5] Fix XML tags in conclusions - copy pattern from SynthesisComplete
3. [Issue #4] Enable expert panel for single sub-problems - remove gate

### Phase 2: State Management Fixes (2-4 hours each)
4. [Issue #6] Fix sub_problem_index in _deliberate_subproblem - 3 line changes
5. [Issue #1] SSE connection for completed sessions - add completion check

### Phase 3: UI/UX Improvements (4-8 hours each)
6. [Issue #3] Sub-problem tab content filtering
7. [Issue #7] Next speaker messaging system
8. [Issue #9] Actions per sub-problem

### Phase 4: Architecture Enhancement (1-2 days)
9. [Issue #8] Summary scope clarity
10. [Issue #10] Enhanced sub-problem decomposition

---

## Testing Plan

### Manual Testing Checklist

For each issue:
1. Create a new meeting with 3+ sub-problems
2. Observe behavior during active deliberation
3. Refresh page mid-meeting
4. Refresh page after completion
5. Switch between sub-problem tabs
6. Verify content in Conclusion tab

### Automated Tests to Add

```python
# tests/test_subproblem_events.py
def test_subproblem_index_propagated():
    """Verify sub_problem_index is correct in all events"""

def test_expert_panel_shown_single_subproblem():
    """Verify expert panel displayed for single sub-problem meetings"""

def test_quality_metrics_per_subproblem():
    """Verify quality metrics update per sub-problem"""
```

---

## Related Files Reference

| Issue | Primary Files |
|-------|---------------|
| #1 SSE | `+page.svelte:361-471`, `streaming.py:254-354`, `sse.ts:24-191` |
| #2 Events | `eventGrouping.ts:20-30` |
| #3 Tabs | `+page.svelte:1160-1171`, `DecompositionComplete.svelte` |
| #4 Panel | `event_extractors.py:235-256`, `event_collector.py:313-321` |
| #5 XML | `SubProblemProgress.svelte:75-100`, `xml-parser.ts` |
| #6 Quality | `nodes.py:2251-2387` (3 locations) |
| #7 Speaker | `+page.svelte:554-693`, `FacilitatorDecision.svelte` |
| #8 Summary | `SynthesisComplete.svelte`, `SubProblemProgress.svelte` |
| #9 Actions | `ActionPlan.svelte`, `meta_synthesize_node` |
| #10 Decomp | `decomposer.py`, `decomposer_prompts.py`, `problem.py` |

---

## NEW: Speed Optimizations (From CONSENSUS_BUILDING_RESEARCH.md)

### 11. Adaptive Round Limits Based on Complexity

**Current State**: Fixed 6 rounds for all sub-problems
**Problem**: Simple problems (complexity 1-5) don't need 6 rounds

**Research Finding**:
- Complexity 1-3: 2-3 rounds optimal
- Complexity 4-5: 3-4 rounds optimal
- Complexity 6-7: 4-5 rounds optimal
- Complexity 8+: 5-6 rounds optimal

**Solution** (`bo1/graph/safety/loop_prevention.py`):

```python
def get_adaptive_max_rounds(complexity_score: int) -> int:
    """Calculate max rounds based on sub-problem complexity."""
    if complexity_score <= 3:
        return 3  # Simple: quick resolution
    elif complexity_score <= 5:
        return 4  # Moderate: standard debate
    elif complexity_score <= 7:
        return 5  # Complex: extended discussion
    else:
        return 6  # Very complex: full deliberation
```

**Impact**: 30-50% reduction in deliberation time for simple problems

---

### 12. Early Termination via Semantic Convergence

**Current State**: Convergence threshold 0.90 + MIN_NOVELTY_THRESHOLD 0.40
**Problem**: Even when experts agree, we continue for minimum rounds

**Research Finding**:
- If convergence > 0.85 AND novelty < 0.30 for 2+ rounds → safe to exit
- ~0.5% of discussions benefit from extended debate past convergence

**Solution** (`bo1/graph/safety/loop_prevention.py:check_convergence_node`):

```python
# Add early exit logic
def should_exit_early(state: DeliberationGraphState) -> bool:
    """Check if we can safely exit before max rounds."""
    round_num = state.get("round_number", 0)

    # Never exit before round 2 (need minimum exploration)
    if round_num < 2:
        return False

    convergence = calculate_semantic_convergence(state)
    novelty = calculate_novelty_score(state)

    # High convergence + low novelty = agents repeating themselves
    if convergence > 0.85 and novelty < 0.30:
        logger.info(f"[EARLY_EXIT] Convergence {convergence:.2f}, novelty {novelty:.2f}")
        return True

    return False
```

**Impact**: 20-30% reduction in average deliberation time

---

### 13. Problem Drift Detection

**Research Finding**: Problem drift is the #1 cause of diminishing returns (~0.8% of discussions suffer)

**Current State**: No drift detection
**Problem**: Experts can wander off-topic, wasting rounds

**Solution** (`bo1/graph/nodes.py:parallel_round_node`):

```python
async def check_contribution_relevance(
    contribution: str,
    sub_problem_goal: str
) -> tuple[bool, float]:
    """Check if contribution addresses the sub-problem goal.

    Returns: (is_relevant, relevance_score 0-10)
    """
    prompt = f"""
    Sub-problem goal: {sub_problem_goal}

    Contribution: {contribution[:500]}

    Rate relevance (0-10) and respond JSON:
    {{"relevant": true/false, "score": 0-10, "drift_warning": "string if score < 6"}}
    """

    # Use Haiku for fast, cheap relevance check
    response = await broker.call(PromptRequest(
        system="You evaluate discussion relevance.",
        user_message=prompt,
        model="haiku",
        max_tokens=100,
    ))

    result = parse_json(response.content)
    return result["relevant"], result["score"]
```

**When drift detected (score < 6)**:
- Trigger facilitator redirect
- Log warning for analysis
- Include reminder of sub-problem goal in next prompt

**Impact**: Prevent wasted rounds, maintain focus

---

### 14. Deadlock Detection

**Research Finding**: Output repetition, circular arguments indicate deadlock

**Current State**: No deadlock detection
**Problem**: Experts can argue in circles without progress

**Solution** (`bo1/graph/safety/loop_prevention.py`):

```python
def detect_deadlock(state: DeliberationGraphState) -> dict:
    """Detect if deliberation is stuck in deadlock."""
    contributions = state.get("contributions", [])

    if len(contributions) < 6:
        return {"deadlock": False}

    recent = contributions[-6:]

    # Check for argument repetition (embedding similarity)
    repetition_rate = calculate_repetition_rate(recent)

    if repetition_rate > 0.6:  # 60% of arguments are repeats
        return {
            "deadlock": True,
            "type": "repetition",
            "resolution": "force_voting"  # Skip to voting
        }

    # Check for circular disagreement (A refutes B, B refutes A)
    if detect_circular_refutation(recent):
        return {
            "deadlock": True,
            "type": "circular",
            "resolution": "facilitator_intervention"
        }

    return {"deadlock": False}
```

**Impact**: Prevent infinite loops, force decisions when stuck

---

### 15. Reduce Per-Round Latency

**Current State**: Sequential contribution display with delays
**Problem**: User perceives slow progress

**Solutions**:

**15A: Reduce contribution reveal delay** (`+page.svelte`)
```typescript
// Current: 800-1200ms delay between contributions
// New: 400-600ms delay
const MIN_DELAY = 400;  // Was 800
const MAX_DELAY = 600;  // Was 1200
```

**15B: Start streaming next round while revealing current**
- Backend can start generating round N+1 while frontend reveals round N
- Requires: Redis queue for pre-generated contributions

**15C: Use Haiku 4.5 for initial rounds, Sonnet for synthesis**
```python
# Current: All calls use Sonnet
# New: Use model hierarchy
ROUND_MODEL_MAP = {
    1: "haiku",   # Initial exploration - speed over depth
    2: "haiku",   # Building on initial
    3: "sonnet",  # Deeper analysis
    4: "sonnet",  # Convergence
    5: "sonnet",  # Final insights
    6: "sonnet",  # Synthesis prep
}
```

**Impact**: 40-60% reduction in perceived wait time

---

### 16. Phase-Based Time Boxing

**Research Finding**: Different phases need different time allocations

**Solution**: Add phase timeouts with graceful degradation

```python
# bo1/graph/config.py
PHASE_TIMEOUTS = {
    "decomposition": 15,      # 15 seconds
    "persona_selection": 10,  # 10 seconds
    "initial_round": 45,      # 45 seconds (parallel)
    "discussion_round": 30,   # 30 seconds per round
    "voting": 20,             # 20 seconds (parallel)
    "synthesis": 30,          # 30 seconds
    "meta_synthesis": 45,     # 45 seconds
}

# Total target for 3-subproblem meeting: ~5-7 minutes
# Single subproblem: ~2-3 minutes
```

---

## NEW: Prompt Quality Improvements (From PROMPT_ENGINEERING_FRAMEWORK.md)

### 17. Prompt Structure Audit

**Current State**: Prompts use XML structure, `<thinking>` tags, evidence protocol ✓
**Identified Improvements**:

**17A: Add explicit sub-problem focus to persona prompts**

Current persona prompt is generic. Add sub-problem-specific guidance:

```python
# bo1/prompts/reusable_prompts.py - Add to persona system prompt
SUB_PROBLEM_FOCUS_TEMPLATE = """
<current_focus>
You are addressing this specific sub-problem:
Goal: {sub_problem_goal}

Key questions to answer:
{key_questions}

Your contribution MUST directly address this goal.
Do NOT discuss topics outside this scope.
</current_focus>
"""
```

**17B: Add output length guidance**

Current prompts don't specify length. Add explicit limits:

```python
# In COMMUNICATION_PROTOCOL
<contribution>
Your public statement to the board (150-250 words):
- Lead with your key insight
- One concrete recommendation
- One supporting reason
- One caveat or condition
</contribution>
```

**17C: Reduce synthesis token budget**

Current: `max_tokens=3000` for synthesis
Research shows: Shorter, focused synthesis is more actionable

```python
# nodes.py:synthesize_node
request = PromptRequest(
    # ...
    max_tokens=1500,  # Was 3000 - force conciseness
)
```

---

### 18. Facilitator Decision Prompt Improvements

**Current Issue**: Facilitator sometimes continues discussion unnecessarily

**Solution**: Add explicit stopping criteria to facilitator prompt

```python
# reusable_prompts.py - FACILITATOR_SYSTEM_TEMPLATE

<stopping_criteria>
TRANSITION TO VOTING when ANY of these are true:
1. 3+ rounds completed AND all personas have contributed at least twice
2. Same arguments being repeated (no new insights in last 2 contributions)
3. Clear consensus emerging (>70% alignment on recommendation)
4. All key questions from sub-problem focus have been addressed
5. Time pressure: round 5+ AND no major new insights

DO NOT extend discussion just to be thorough. Users prefer faster results.
</stopping_criteria>
```

---

### 19. Use Haiku for Supporting Tasks

**Current State**: All LLM calls use Sonnet
**Problem**: Expensive and slow for simple tasks

**Solution**: Model selection by task

| Task | Current | Recommended | Savings |
|------|---------|-------------|---------|
| Decomposition | Sonnet | Sonnet | - |
| Persona selection | Sonnet | Sonnet | - |
| Contributions (round 1-2) | Sonnet | **Haiku 4.5** | 90% |
| Contributions (round 3+) | Sonnet | Sonnet | - |
| Convergence check | Sonnet | **Haiku** | 90% |
| Problem drift check | N/A | **Haiku** | New |
| Voting/recommendations | Sonnet | Sonnet | - |
| Synthesis | Sonnet | Sonnet | - |
| Meta-synthesis | Sonnet | Sonnet | - |

**Implementation** (`bo1/llm/broker.py`):

```python
def get_model_for_phase(phase: str, round_number: int = 0) -> str:
    """Select appropriate model for task."""
    # Fast phases use Haiku
    if phase in ["convergence_check", "drift_check", "format_validation"]:
        return "haiku"

    # Early exploration can use Haiku
    if phase == "contribution" and round_number <= 2:
        return "haiku"

    # Everything else uses Sonnet
    return "sonnet"
```

**Impact**: 40-60% cost reduction, 30% latency reduction

---

## NEW: Missing Items from Original Request

### 20. Verify Original 10 Issues Coverage

| Issue | Status | Notes |
|-------|--------|-------|
| 1. SSE errors | ✅ Covered | Section 1 |
| 2. discussion_quality_status visible | ✅ Covered | Section 2 |
| 3. Sub-problem decomposition in wrong tab | ✅ Covered | Section 3 |
| 4a. Meeting complete summary per tab | ✅ Covered | Section 3 |
| 4b. Sub-problem complete (full text) | ✅ Covered | Section 5 (XML tags) |
| 4c. Actions from all sub-problems | ✅ Covered | Section 9 |
| 5. Expert panel not showing | ✅ Covered | Section 4 |
| 6. Conclusion XML tags | ✅ Covered | Section 5 |
| 7. Previous summary scope | ✅ Covered | Section 8 |
| 8. Next speaker messages | ✅ Covered | Section 7 |
| 9. Discussion quality state | ✅ Covered | Section 6 |
| 10. Decomposition quality | ✅ Covered | Section 10 |

### 21. Additional UX Issues Identified

**21A: Loading States During Transitions**

Between sub-problems, users see blank screen. Add skeleton loaders:

```svelte
<!-- +page.svelte - Add between sub-problems -->
{#if isTransitioningSubProblem}
    <div class="animate-pulse">
        <div class="h-4 bg-neutral-200 rounded w-3/4 mb-2"></div>
        <div class="h-4 bg-neutral-200 rounded w-1/2"></div>
        <p class="text-sm text-neutral-500 mt-2">
            Preparing next sub-problem...
        </p>
    </div>
{/if}
```

**21B: Progress Indicator Accuracy**

Current progress bar doesn't account for variable rounds. Fix:

```typescript
// Calculate actual progress based on adaptive rounds
const totalExpectedRounds = subProblems.reduce((sum, sp) =>
    sum + getAdaptiveMaxRounds(sp.complexity_score), 0
);
const completedRounds = /* actual completed */;
const progress = completedRounds / totalExpectedRounds;
```

**21C: Mobile Responsiveness**

Meeting page has issues on mobile. Priority fixes:
- Tab overflow (use horizontal scroll)
- Expert cards too wide (stack on mobile)
- Quality metrics sidebar (collapse to bottom on mobile)

---

## Revised Implementation Priority

### Phase 0: Speed Quick Wins (Highest Impact, Low Effort)

1. **[Issue #15A] Reduce reveal delay** - 10 min, immediate UX improvement
2. **[Issue #2] Hide discussion_quality_status** - 1 line change
3. **[Issue #17C] Reduce synthesis tokens** - 1 line change, faster synthesis
4. **[Issue #19] Use Haiku for early rounds** - 30 min, 40% cost reduction

### Phase 1: Core Fixes (Original Issues)

5. **[Issue #5] Fix XML tags in conclusions** - 30 min
6. **[Issue #4] Enable expert panel for single sub-problems** - 15 min
7. **[Issue #6] Fix sub_problem_index propagation** - 30 min
8. **[Issue #1] SSE completion check** - 1 hour

### Phase 1.5: CRITICAL QUALITY FIX ⚠️

**DO THIS BEFORE SPEED OPTIMIZATIONS - Affects output quality!**

9. **[Issue #22] Context passing for dependent sub-problems** - 6 hours
   - Build dependency context injection
   - Build sub-problem outcomes context for ALL experts
   - Modify parallel_round_node to inject context
   - Test with multi-sub-problem meeting with dependencies

### Phase 2: Speed Optimizations

10. **[Issue #11] Adaptive round limits** - 2 hours
11. **[Issue #12] Early termination logic** - 4 hours
12. **[Issue #13] Problem drift detection** - 4 hours
13. **[Issue #14] Deadlock detection** - 2 hours

### Phase 3: UX Polish

14. **[Issue #3] Tab content filtering** - 4 hours
15. **[Issue #7] Next speaker messages** - 4 hours
16. **[Issue #18] Facilitator stopping criteria** - 2 hours
17. **[Issue #21A-C] Loading states & mobile** - 4 hours

### Phase 4: Quality Architecture

18. **[Issue #10] Enhanced decomposition structure** - 1-2 days
19. **[Issue #17A-B] Prompt improvements** - 4 hours
20. **[Issue #9] Actions per sub-problem** - 4 hours

---

## Success Metrics

### Speed Targets

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Single sub-problem meeting | ~5-8 min | **2-3 min** | Adaptive rounds + early exit |
| 3 sub-problem meeting | ~15-20 min | **5-8 min** | Parallel + Haiku |
| Time to first contribution | ~30s | **15s** | Haiku for initial |
| Time between contributions | ~2-3s | **<1s** | Reduced delays |

### Quality Targets

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Problem drift rate | Unknown | **<1%** | Drift detection |
| Deadlock rate | Unknown | **0%** | Deadlock detection |
| Consensus at vote | ~70% | **>75%** | Better facilitation |
| Synthesis actionability | Medium | **High** | Shorter, focused synthesis |

### Cost Targets

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Cost per sub-problem | ~$0.15-0.20 | **$0.08-0.12** | Haiku for early rounds |
| Total meeting cost | ~$0.50-1.00 | **$0.25-0.40** | Model hierarchy |

---

---

## CRITICAL: Context Passing Gaps (Issue 22)

### Investigation Findings

**What IS Working:**

| Component | Status | Location |
|-----------|--------|----------|
| Round summaries generated | ✅ | `nodes.py:610-650` |
| Hierarchical context | ✅ | `compose_persona_prompt_hierarchical()` |
| Per-expert memory across sub-problems | ✅ | `nodes.py:512-528` |

**Round Context Flow (Working):**
```
Round 1 contributions → Summarized → Round 2 sees summary
Round 2 contributions → Summarized → Round 3 sees summaries [1,2] + full Round 2
```

**What is MISSING:**

| Gap | Impact | Severity |
|-----|--------|----------|
| Full synthesis not passed to dependent sub-problems | Experts can't reference conclusions | **HIGH** |
| Non-participating experts get no context | New experts in SP2 don't know SP1 outcome | **HIGH** |
| Dependency context not injected | SP2 marked as depending on SP1, but SP1 conclusion not provided | **HIGH** |

### Root Cause Analysis

**Current Expert Memory Flow** (`nodes.py:512-528`):
```python
# ONLY passes the expert's OWN summary from previous sub-problems
for result in sub_problem_results:
    if speaker_code in result.expert_summaries:  # Only if THIS expert participated
        prev_summary = result.expert_summaries[speaker_code]
        memory_parts.append(f"Sub-problem: {prev_goal}\nYour position: {prev_summary}")
```

**Problems:**
1. If Expert A did NOT participate in sub-problem 1, they get **NO context**
2. The **full synthesis** (the actual conclusion) is stored in `result.synthesis` but **never passed**
3. **Dependency declarations** in decomposition are ignored for context injection

### Solution: Enhanced Dependency Context Injection

#### 22A: Pass Full Synthesis to Dependent Sub-Problems

**File**: `bo1/graph/nodes.py` - Modify `persona_contribute_node` and `parallel_round_node`

```python
def build_dependency_context(
    current_sp: SubProblem,
    sub_problem_results: list[SubProblemResult],
    problem: Problem
) -> str | None:
    """Build context from dependent sub-problems.

    Args:
        current_sp: Current sub-problem
        sub_problem_results: Completed sub-problem results
        problem: Full problem with all sub-problems

    Returns:
        Formatted context string or None
    """
    if not current_sp.dependencies:
        return None

    context_parts = []
    context_parts.append("<dependent_conclusions>")
    context_parts.append("This sub-problem depends on conclusions from earlier sub-problems:\n")

    for dep_id in current_sp.dependencies:
        # Find the dependency sub-problem
        dep_sp = next((sp for sp in problem.sub_problems if sp.id == dep_id), None)
        if not dep_sp:
            continue

        # Find the result for this dependency
        dep_result = next((r for r in sub_problem_results if r.sub_problem_id == dep_id), None)
        if not dep_result:
            continue

        # Extract key recommendation from synthesis (parse XML if needed)
        recommendation = extract_recommendation_from_synthesis(dep_result.synthesis)

        context_parts.append(f"""
**{dep_sp.goal}** (Resolved)
Key Conclusion: {recommendation}
""")

    context_parts.append("</dependent_conclusions>")

    return "\n".join(context_parts)
```

#### 22B: Pass Sub-Problem Summaries to ALL Experts

Even if an expert didn't participate in sub-problem 1, they need to know what was decided:

```python
def build_subproblem_context_for_all(
    sub_problem_results: list[SubProblemResult]
) -> str | None:
    """Build context from all completed sub-problems for any expert.

    This ensures new experts in sub-problem 2 understand what happened in SP1.
    """
    if not sub_problem_results:
        return None

    context_parts = []
    context_parts.append("<previous_subproblem_outcomes>")

    for result in sub_problem_results:
        # Extract recommendation (not full synthesis - too long)
        recommendation = extract_recommendation_from_synthesis(result.synthesis)

        context_parts.append(f"""
Sub-problem: {result.sub_problem_goal}
Conclusion: {recommendation}
Expert Panel: {', '.join(result.expert_panel)}
""")

    context_parts.append("</previous_subproblem_outcomes>")

    return "\n".join(context_parts)
```

#### 22C: Integrate into Persona Prompts

**Modify**: `compose_persona_prompt_hierarchical()` or create new function:

```python
def compose_persona_prompt_with_subproblem_context(
    persona_system_role: str,
    problem_statement: str,
    participant_list: str,
    round_summaries: list[str],
    current_round_contributions: list[dict[str, str]],
    round_number: int,
    current_phase: str,
    # NEW parameters
    expert_memory: str | None,
    subproblem_context: str | None,
    dependency_context: str | None,
) -> str:
    """Compose persona prompt with full context hierarchy."""

    # ... existing hierarchical context ...

    # Add sub-problem context (for ALL experts)
    if subproblem_context:
        context_parts.insert(0, subproblem_context)

    # Add dependency context (if this SP depends on others)
    if dependency_context:
        context_parts.insert(0, dependency_context)

    # Add expert-specific memory (their own previous positions)
    if expert_memory:
        context_parts.append(f"""
<your_previous_positions>
{expert_memory}
</your_previous_positions>
""")

    # ... rest of prompt composition ...
```

### Impact Assessment

| Metric | Before | After |
|--------|--------|-------|
| Context coherence across sub-problems | Low | High |
| New expert onboarding | None | Full |
| Dependency resolution | Declared but unused | Actively injected |
| Risk of contradictory recommendations | High | Low |

### Implementation Priority

**CRITICAL - Do this before other Phase 2 work:**

1. **Implement `build_dependency_context()`** - 2 hours
2. **Implement `build_subproblem_context_for_all()`** - 1 hour
3. **Modify `parallel_round_node` to inject context** - 2 hours
4. **Test with multi-sub-problem meeting** - 1 hour

**Total: ~6 hours for a major quality improvement**

---

## Appendix: Research References

- **CONSENSUS_BUILDING_RESEARCH.md**: Semantic convergence, problem drift, deadlock detection, time boxing
- **PROMPT_ENGINEERING_FRAMEWORK.md**: XML structure, thinking tags, evidence protocol, model selection
- Academic: "Multi-Agent Debate for LLM Judges with Adaptive Stability Detection" (2024)
- Academic: "Literature Review of Multi-Agent Debate for Problem-Solving" (arXiv 2506.00066v1)
- Production: MetaGPT cost optimization patterns
