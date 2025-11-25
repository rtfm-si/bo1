# Meeting System Analysis & Remediation Plan
**Board of One - Multi-Agent Deliberation System**

**Date:** November 25, 2025
**Status:** Critical Issues Identified
**Priority:** HIGH - Production System Degradation

---

## Executive Summary

This analysis identifies **5 critical issues** affecting the boardof.one multi-agent deliberation system, impacting user experience and deliberation quality. The issues range from UI/UX problems (stale sidebar metrics, component loading failures) to fundamental deliberation logic flaws (expert dominance, shallow discussion).

**Key Findings:**
- **Issue #1** (UI Updates): Frontend component loading race conditions causing placeholder cards
- **Issue #2** (Sidebar Disconnect): Metrics showing "overall" data instead of active sub-problem context
- **Issue #3** (Sub-problem Failures): Silent failures in event streaming and state management
- **Issue #4** (Shallow Discussion): Prompts fail to encourage genuine debate and critical thinking
- **Issue #5** (Expert Dominance): Facilitator decision logic allows single expert to dominate 10+ rounds

**Impact:** These issues compound to create a poor user experience where meetings appear to stall, experts repeat themselves without depth, and the UI doesn't reflect what's happening in the deliberation.

---

## Issue #1: UI Not Updating - Cards Load as Placeholders

### Root Cause Analysis

**What's Broken:**
The meeting UI (`/meeting/[id]/+page.svelte`) uses dynamic component loading via `getComponentForEvent()` but encounters race conditions during SSE event streams that cause placeholder cards to appear without content.

**Why It Happens:**

1. **Race Condition in Event Loading** (Lines 388-396):
   ```typescript
   // Historical events loaded via REST API
   const response = await apiClient.getSessionEvents(sessionId);
   for (const event of response.events) {
       addEvent(sseEvent);
   }
   // Then SSE stream starts immediately
   await startEventStream();
   ```
   The SSE stream can start firing events before historical events are fully processed by Svelte's reactive system, causing duplicate detection logic to skip new events.

2. **Deduplication Key Conflicts** (Lines 292-305):
   ```typescript
   const eventKey = `${subProblemIndex}-${newEvent.timestamp}-${newEvent.event_type}-${personaOrId}`;
   if (seenEventKeys.has(eventKey)) {
       console.debug('[Events] Skipping duplicate event:', eventKey);
       return;
   }
   ```
   Events with identical timestamps (possible in rapid parallel operations) get deduplicated incorrectly.

3. **Component Cache Miss** (Lines 63-100):
   ```typescript
   async function getComponentForEvent(eventType: string): Promise<SvelteComponent> {
       if (componentCache.has(eventType)) {
           return componentCache.get(eventType)!;
       }
       // ... load component asynchronously
   }
   ```
   When events arrive in rapid succession (100-200ms apart), the async component loading can't keep up, causing the template to render with `GenericEvent` fallback or empty placeholders.

4. **Missing Error Boundaries**:
   The `{#await}` blocks (lines 1301-1311) have a catch clause that renders `GenericEvent`, but if the event data is malformed, even the GenericEvent component might fail silently.

**Evidence from Code:**
- `/frontend/src/routes/(app)/meeting/[id]/+page.svelte:342-363` - Sequencing issue in `onMount()`
- `/backend/api/streaming.py:260-360` - SSE stream starts immediately after subscription
- Console log statement at line 319: `[EVENT RECEIVED] Convergence event:` indicates events ARE arriving but not rendering

### Best Practices (Research-Based)

From `PROMPT_ENGINEERING_FRAMEWORK.md`:
> **Phase 3: Multi-Persona Deliberation**
> - Streaming: Real-time updates via SSE
> - Memory: Checkpoint state in Postgres for HITL and recovery

The issue is that the frontend assumes SSE events are the source of truth, but doesn't properly handle the transition from historical state to live stream.

### Implementation Plan

**Priority:** P0 (Blocks user experience)
**Effort:** 2-3 days
**Risk:** Medium (frontend changes, needs thorough testing)

#### Solution 1: Fix Event Loading Sequence

**File:** `/frontend/src/routes/(app)/meeting/[id]/+page.svelte`

**Changes:**
```typescript
// Lines 342-363 - onMount() refactor
onMount(() => {
    (async () => {
        try {
            // STEP 1: Load session metadata
            await loadSession();

            // STEP 2: Load and process ALL historical events
            await loadHistoricalEvents();

            // STEP 3: Wait for Svelte to finish reactive updates
            await tick(); // Svelte's tick() ensures reactive state is settled

            // STEP 4: NOW start SSE stream (historical events fully processed)
            await startEventStream();

            console.log('[Events] Initialization sequence complete');
        } catch (err) {
            console.error('[Events] Initialization failed:', err);
            error = err instanceof Error ? err.message : 'Failed to initialize session';
            isLoading = false;
        }
    })();
});
```

**Rationale:** Adding `await tick()` between loading historical events and starting the SSE stream ensures Svelte's reactive system has fully processed the historical events before new ones arrive, preventing race conditions.

#### Solution 2: Improve Deduplication Logic

**File:** `/frontend/src/routes/(app)/meeting/[id]/+page.svelte`

**Changes:**
```typescript
// Lines 292-305 - Enhanced deduplication with sequence numbers
let eventSequence = $state(0);

function addEvent(newEvent: SSEEvent) {
    // Use sequence number + sub_problem_index for unique keys
    const subProblemIndex = newEvent.data.sub_problem_index ?? 'global';
    const personaOrId = newEvent.data.persona_code || newEvent.data.sub_problem_id || '';

    // Include sequence number to handle identical timestamps
    const eventKey = `${subProblemIndex}-${eventSequence}-${newEvent.event_type}-${personaOrId}`;

    // Increment sequence for next event
    eventSequence++;

    // Skip if already seen (shouldn't happen with sequence number)
    if (seenEventKeys.has(eventKey)) {
        console.warn('[Events] Duplicate detected (should be rare):', eventKey);
        return;
    }

    // Enforce max size
    if (seenEventKeys.size >= MAX_SEEN_EVENTS) {
        const keys = Array.from(seenEventKeys);
        seenEventKeys = new Set(keys.slice(-MAX_SEEN_EVENTS));
        console.debug(`[Events] Pruned deduplication set to ${MAX_SEEN_EVENTS} entries`);
    }

    seenEventKeys.add(eventKey);
    events = [...events, newEvent];

    // Debug convergence events
    if (newEvent.event_type === 'convergence') {
        console.log('[EVENT RECEIVED] Convergence event:', {
            sequence: eventSequence - 1,
            event_type: newEvent.event_type,
            sub_problem_index: newEvent.data.sub_problem_index,
            score: newEvent.data.score,
            data: newEvent.data
        });
    }
}
```

**Rationale:** Using a sequence number instead of timestamp eliminates the possibility of duplicate keys for events that arrive in the same millisecond.

#### Solution 3: Add Error Boundaries and Loading States

**File:** `/frontend/src/routes/(app)/meeting/[id]/+page.svelte`

**Changes:**
```typescript
// Lines 1301-1311 - Enhanced error handling
{#await getComponentForEvent(event.event_type)}
    <!-- Loading skeleton with timeout fallback -->
    <div class="animate-pulse bg-slate-100 dark:bg-slate-800 rounded-lg p-3">
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
    </div>
{:then EventComponent}
    {#if EventComponent}
        <EventComponent event={event as any} />
    {:else}
        <!-- Component loaded but null - use GenericEvent -->
        <GenericEvent event={event} />
        <div class="text-xs text-red-600 mt-2">
            Component failed to load for: {event.event_type}
        </div>
    {/if}
{:catch error}
    <!-- Component import failed - show error with details -->
    <GenericEvent event={event} />
    <div class="text-xs text-red-600 mt-2">
        Error loading component: {error.message || 'Unknown error'}
    </div>
{/await}
```

**Rationale:** Explicit null checks and error messages help diagnose component loading failures in production.

#### Solution 4: Preload Critical Components

**File:** `/frontend/src/routes/(app)/meeting/[id]/+page.svelte`

**Changes:**
```typescript
// Lines 36-50 - Preload common components on mount
onMount(() => {
    // Preload critical components before any events arrive
    const criticalComponents = [
        'contribution',
        'facilitator_decision',
        'convergence',
        'voting_complete',
        'synthesis_complete',
        'decomposition_complete'
    ];

    // Fire all preloads in parallel
    Promise.all(criticalComponents.map(type => getComponentForEvent(type)))
        .then(() => console.log('[Events] Critical components preloaded'))
        .catch(err => console.warn('[Events] Component preload failed:', err));

    // Continue with normal initialization...
});
```

**Rationale:** Preloading the most common components ensures they're in cache before events arrive, eliminating async loading delays.

### Success Metrics

- **No placeholder cards**: All events should render with proper components within 500ms
- **100% event display rate**: Every event published should appear in UI (verify via console logs)
- **Component cache hit rate >90%**: After first event of each type, subsequent events use cached component

### Testing Checklist

- [ ] Load meeting with 50+ historical events - verify all render correctly
- [ ] Connect to active meeting mid-stream - verify new events render immediately
- [ ] Rapid event stream (5+ events/second) - verify no dropped events
- [ ] Browser refresh during active meeting - verify state recovery
- [ ] Multiple sub-problems - verify events render in correct tabs

---

## Issue #2: Side Panels Disconnected from Current View

### Root Cause Analysis

**What's Broken:**
The right sidebar (`DecisionMetrics` component) shows "overall" aggregated metrics across ALL sub-problems, but users expect it to show context for the ACTIVE tab they're viewing.

**Why It Happens:**

1. **DecisionMetrics Receives All Events** (`/frontend/src/lib/components/ui/DecisionMetrics.svelte:10-16`):
   ```typescript
   interface Props {
       events: SSEEvent[];  // ALL events, not filtered
       currentPhase: string | null;
       currentRound: number | null;
   }
   ```
   The component receives the complete event array without any sub-problem context.

2. **No Sub-Problem Awareness** (Lines 18-43):
   ```typescript
   const convergenceEvents = $derived(
       events.filter(e => e.event_type === 'convergence')
   );
   const contributions = $derived(
       events.filter(e => e.event_type === 'contribution')
   );
   ```
   All filters operate on the full event array, aggregating across all sub-problems.

3. **Meeting Page Doesn't Pass Context** (`/meeting/[id]/+page.svelte:1517-1521`):
   ```typescript
   <DecisionMetrics
       events={events}  // Passes ALL events
       currentPhase={session.phase}
       currentRound={session.round_number ?? null}
   />
   ```
   No information about which tab is active or which sub-problem should be displayed.

**User Impact:**
- In multi-sub-problem meetings, users see convergence metrics for "overall" deliberation
- When viewing Sub-Problem 2 tab, sidebar still shows aggregated data including Sub-Problem 1
- Makes it impossible to understand the specific sub-problem's status
- "Sidebar shows 'overall'" as reported by user

### Best Practices

From research on UX patterns for tabbed interfaces:
- **Context-aware sidebars**: Sidebar content should match the active tab's context
- **Progressive disclosure**: Show overall metrics in a separate "Summary" view, not mixed with detail views
- **Visual consistency**: Users expect sidebar to reflect what they're currently viewing

### Implementation Plan

**Priority:** P1 (Confusing but not blocking)
**Effort:** 1-2 days
**Risk:** Low (UI-only change)

#### Solution 1: Pass Active Sub-Problem Context to DecisionMetrics

**File:** `/frontend/src/routes/(app)/meeting/[id]/+page.svelte`

**Changes:**
```typescript
// Lines 1517-1521 - Pass active tab context
<DecisionMetrics
    events={events}
    currentPhase={session.phase}
    currentRound={session.round_number ?? null}
    activeSubProblemIndex={activeSubProblemTab ? parseInt(activeSubProblemTab.replace('subproblem-', '')) : null}
    totalSubProblems={subProblemTabs.length}
/>
```

**File:** `/frontend/src/lib/components/ui/DecisionMetrics.svelte`

**Changes:**
```typescript
// Lines 9-14 - Add sub-problem context
interface Props {
    events: SSEEvent[];
    currentPhase: string | null;
    currentRound: number | null;
    activeSubProblemIndex?: number | null;  // NEW: Which sub-problem is active
    totalSubProblems?: number;               // NEW: Total count for context
}

let {
    events,
    currentPhase,
    currentRound,
    activeSubProblemIndex = null,
    totalSubProblems = 1
}: Props = $props();

// Lines 17-39 - Filter events by active sub-problem
const filteredEvents = $derived.by(() => {
    // If single sub-problem OR no active tab, show all events
    if (totalSubProblems <= 1 || activeSubProblemIndex === null) {
        return events;
    }

    // Filter to active sub-problem only
    return events.filter(e => {
        const eventSubIndex = e.data.sub_problem_index as number | undefined;
        return eventSubIndex === activeSubProblemIndex;
    });
});

// Update all derived metrics to use filteredEvents instead of events
const convergenceEvents = $derived(
    filteredEvents.filter(e => e.event_type === 'convergence')
);
const contributions = $derived(
    filteredEvents.filter(e => e.event_type === 'contribution')
);
const votes = $derived(
    filteredEvents.filter(e => e.event_type === 'persona_vote')
);
const interventions = $derived(
    filteredEvents.filter(e => e.event_type === 'moderator_intervention').length
);
```

**Rationale:** This makes the sidebar context-aware - when a user clicks a sub-problem tab, the metrics update to show only that sub-problem's data.

#### Solution 2: Add "Overall" Tab for Aggregated View

**File:** `/frontend/src/routes/(app)/meeting/[id]/+page.svelte`

**Changes:**
```typescript
// Lines 1179-1204 - Add "Overall" tab before sub-problem tabs
{#if subProblemTabs.length > 1}
    <div class="h-full flex flex-col">
        <div class="border-b border-slate-200 dark:border-slate-700">
            <div class="flex overflow-x-auto px-4 pt-3">
                <!-- NEW: Overall tab -->
                <button
                    type="button"
                    class={[
                        'flex-shrink-0 px-4 py-2 border-b-2 -mb-px transition-all text-sm font-medium',
                        activeSubProblemTab === 'overall'
                            ? 'border-brand-600 text-brand-700 dark:border-brand-400 dark:text-brand-400'
                            : 'border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:border-slate-300 dark:hover:border-slate-600',
                    ].join(' ')}
                    onclick={() => activeSubProblemTab = 'overall'}
                >
                    <div class="flex items-center gap-2">
                        <span>Overall</span>
                        <span class="text-xs text-slate-500">({subProblemTabs.length} sub-problems)</span>
                    </div>
                </button>

                <!-- Existing sub-problem tabs -->
                {#each subProblemTabs as tab}
                    <!-- ... existing tab code -->
                {/each}
            </div>
        </div>

        <!-- Tab content with conditional rendering -->
        {#if activeSubProblemTab === 'overall'}
            <!-- Overall view shows aggregated metrics -->
            <div class="flex-1 overflow-y-auto p-4 space-y-4">
                <div class="bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
                    <h3 class="text-base font-semibold text-slate-900 dark:text-white mb-3">
                        Overall Progress
                    </h3>
                    <p class="text-sm text-slate-600 dark:text-slate-400 mb-4">
                        This meeting is analyzing {subProblemTabs.length} interconnected sub-problems.
                        Select a tab above to view detailed deliberation for each sub-problem.
                    </p>
                    <div class="grid grid-cols-2 gap-4">
                        {#each subProblemTabs as tab, index}
                            <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                                <div class="flex items-center justify-between mb-2">
                                    <h4 class="text-sm font-medium text-slate-900 dark:text-white">
                                        Sub-Problem {index + 1}
                                    </h4>
                                    <span class="text-xs px-2 py-1 rounded-full {
                                        tab.status === 'complete' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                                        tab.status === 'active' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                                        'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                    }">
                                        {tab.status}
                                    </span>
                                </div>
                                <p class="text-xs text-slate-600 dark:text-slate-400 mb-3">
                                    {tab.goal}
                                </p>
                                <div class="text-xs space-y-1 text-slate-500 dark:text-slate-400">
                                    <div>Experts: {tab.metrics.expertCount}</div>
                                    <div>Rounds: {tab.metrics.currentRound}/{tab.metrics.maxRounds}</div>
                                    <div>Duration: {tab.metrics.duration}</div>
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>
        {:else}
            <!-- Existing sub-problem detail view -->
        {/if}
    </div>
{/if}
```

**Rationale:** Provides a dedicated "Overall" view for users who want to see the big picture, while keeping individual sub-problem views focused.

#### Solution 3: Add Context Indicator in Sidebar

**File:** `/frontend/src/lib/components/ui/DecisionMetrics.svelte`

**Changes:**
```typescript
// Lines 105-116 - Add context header
<div class="space-y-4">
    <!-- NEW: Context indicator -->
    {#if totalSubProblems > 1}
        <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-3">
            <p class="text-xs text-blue-800 dark:text-blue-200">
                {#if activeSubProblemIndex !== null}
                    Showing metrics for <strong>Sub-Problem {activeSubProblemIndex + 1}</strong>
                {:else}
                    Showing overall metrics across all sub-problems
                {/if}
            </p>
        </div>
    {/if}

    <!-- Existing convergence metrics -->
    {#if convergenceScore !== null}
        <!-- ... -->
    {/if}
</div>
```

**Rationale:** Makes it crystal clear what context the metrics represent, preventing user confusion.

### Success Metrics

- **Context accuracy**: Sidebar metrics always match active tab (verify convergence score changes when switching tabs)
- **User feedback**: "Sidebar shows relevant data for what I'm viewing"
- **No confusion**: Users understand whether they're viewing sub-problem or overall metrics

### Testing Checklist

- [ ] Single sub-problem meeting - sidebar shows all data (no filtering)
- [ ] Multi sub-problem meeting - sidebar updates when switching tabs
- [ ] Overall tab selected - sidebar shows aggregated data with clear indicator
- [ ] Sub-problem tab selected - sidebar shows only that sub-problem's data
- [ ] Metrics are accurate (manually verify convergence scores match expected sub-problem)

---

## Issue #3: Sub-Problems Frequently Fail to Start and Complete

### Root Cause Analysis

**What's Broken:**
Sub-problems fail silently during execution, causing meetings to stall without visible errors. Events don't stream properly, and the UI shows "Preparing..." indefinitely.

**Why It Happens:**

1. **Silent Facilitator Decision Failures** (`/bo1/graph/nodes.py:234-300`):
   ```python
   async def facilitator_decide_node(state: DeliberationGraphState) -> dict[str, Any]:
       # ... decision logic ...

       # SAFETY CHECK: Prevent premature voting (Bug #3 fix)
       min_rounds_before_voting = 3
       if decision.action == "vote" and round_number < min_rounds_before_voting:
           # Override to continue
           decision = FacilitatorDecision(
               action="continue",
               reasoning=override_reason,
               next_speaker=next_speaker,
               speaker_prompt="Build on the discussion so far and add depth to the analysis.",
           )
   ```

   When the facilitator decision is overridden, the `next_speaker` might be invalid (persona code that doesn't exist), causing downstream nodes to fail.

2. **Missing Event Publication** (`/backend/api/event_collector.py:144-148`):
   ```python
   elif event_name == "facilitator_decide" and isinstance(output, dict):
       await self._handle_facilitator_decision(session_id, output)
   ```

   If `_handle_facilitator_decision()` fails (e.g., due to malformed state), no error event is published, leaving the UI stuck waiting.

3. **Race Condition in Research Node** (`/bo1/graph/nodes.py` - not shown in excerpt but referenced in config):
   ```python
   # research -> facilitator_decide (Week 6: Let facilitator decide next action after research)
   # Previously routed directly to persona_contribute, which caused crashes because
   # facilitator_decision still had action="research" with no next_speaker
   workflow.add_edge("research", "facilitator_decide")
   ```

   This was fixed but indicates a pattern of routing issues causing silent failures.

4. **Sub-Problem Index Not Propagated** (`/backend/api/event_collector.py:84-85`):
   ```python
   # Add sub_problem_index from state to event data
   # This is CRITICAL for frontend tab filtering (meeting page line 872)
   sub_problem_index = output.get("sub_problem_index", 0)
   data["sub_problem_index"] = sub_problem_index
   ```

   If `output` doesn't contain `sub_problem_index`, it defaults to 0, causing events to be misattributed to the first sub-problem.

**Evidence:**
- User report: "Sub-problems frequently fail to start and complete"
- Frontend code comment (line 872): "Without this field, events don't appear in sub-problem tabs"
- Multiple router fixes in commit history (`route_facilitator_decision` fixed to handle research)

### Best Practices

From `CONSENSUS_BUILDING_RESEARCH.md`:
> **Priority 1: Immediate Improvements (Next Sprint)**
> - Add deadlock detection logic
> - Track contribution counts per persona
> - Ensure convergence checks prevent infinite loops

The sub-problem failures are a form of "deadlock" where the system stops progressing without clear error signaling.

### Implementation Plan

**Priority:** P0 (Blocks meeting completion)
**Effort:** 3-4 days
**Risk:** High (affects core deliberation logic)

#### Solution 1: Robust Facilitator Decision Validation

**File:** `/bo1/graph/nodes.py`

**Changes:**
```python
# Lines 234-300 - Enhanced facilitator_decide_node
async def facilitator_decide_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Make facilitator decision with comprehensive validation."""
    logger.info("facilitator_decide_node: Making facilitator decision")

    # Convert graph state to v1 DeliberationState for facilitator
    v1_state = graph_state_to_deliberation_state(state)

    # Create facilitator agent
    facilitator = FacilitatorAgent()

    # Get current round number and max rounds
    round_number = state.get("round_number", 1)
    max_rounds = state.get("max_rounds", 10)

    # Call facilitator to decide next action
    decision, llm_response = await facilitator.decide_next_action(
        state=v1_state,
        round_number=round_number,
        max_rounds=max_rounds,
    )

    # VALIDATION: Ensure decision is complete and valid
    if decision.action == "continue":
        # Validate next_speaker exists in personas
        personas = state.get("personas", [])
        persona_codes = [p.code for p in personas]

        if not decision.next_speaker:
            logger.error("facilitator_decide_node: 'continue' action without next_speaker!")
            # Fallback: select first persona
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = f"ERROR RECOVERY: Selected {decision.next_speaker} due to missing next_speaker"

        elif decision.next_speaker not in persona_codes:
            logger.error(
                f"facilitator_decide_node: Invalid next_speaker '{decision.next_speaker}' "
                f"(valid: {persona_codes})"
            )
            # Fallback: select first persona
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = f"ERROR RECOVERY: Selected {decision.next_speaker} due to invalid speaker"

    elif decision.action == "moderator":
        # Validate moderator_type exists
        if not decision.moderator_type:
            logger.error("facilitator_decide_node: 'moderator' action without moderator_type!")
            # Fallback: default to contrarian
            decision.moderator_type = "contrarian"
            decision.reasoning = "ERROR RECOVERY: Using contrarian moderator due to missing type"

    elif decision.action == "research":
        # Validate research_query exists
        if not decision.research_query:
            logger.error("facilitator_decide_node: 'research' action without research_query!")
            # Fallback: skip research, continue with discussion
            decision.action = "continue"
            decision.next_speaker = persona_codes[0] if persona_codes else "unknown"
            decision.reasoning = "ERROR RECOVERY: Skipping research due to missing query"

    # Track cost in metrics
    metrics = ensure_metrics(state)
    if llm_response:
        track_phase_cost(metrics, "facilitator_decision", llm_response)

    # Convert decision to dict for state storage
    decision_dict = asdict(decision)

    logger.info(
        f"facilitator_decide_node: Decision validated - action={decision.action}, "
        f"next_speaker={decision.next_speaker if decision.action == 'continue' else 'N/A'}"
    )

    # Return state updates
    return {
        "facilitator_decision": decision_dict,
        "metrics": metrics,
        "current_node": "facilitator_decide",
        "round_number": state.get("round_number", 1),
        "personas": state.get("personas", []),
        "sub_problem_index": state.get("sub_problem_index", 0),
    }
```

**Rationale:** Comprehensive validation prevents invalid decisions from propagating through the graph, with fallback logic to recover gracefully.

#### Solution 2: Ensure Sub-Problem Index Propagation

**File:** `/bo1/graph/nodes.py` (multiple nodes)

**Changes:**
```python
# Pattern to apply to ALL node functions:

async def {node_name}_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Node implementation with guaranteed sub_problem_index propagation."""

    # Get sub_problem_index from state at START of node
    sub_problem_index = state.get("sub_problem_index", 0)

    # ... node logic ...

    # ALWAYS include sub_problem_index in return dict
    return {
        "sub_problem_index": sub_problem_index,  # CRITICAL: Always propagate
        # ... other state updates ...
    }
```

**Files to update:**
- `decompose_node` (line 108)
- `select_personas_node` (line 184)
- `initial_round_node` (line 230)
- `facilitator_decide_node` (as above)
- `persona_contribute_node`
- `moderator_intervene_node`
- `check_convergence_node`
- `vote_node`
- `synthesize_node`

**Rationale:** Ensures `sub_problem_index` never gets lost during state updates, preventing events from being misattributed.

#### Solution 3: Add Error Event Publication

**File:** `/backend/api/event_collector.py`

**Changes:**
```python
# Lines 50-96 - Wrap event publication in try/except
async def _publish_node_event(
    self,
    session_id: str,
    output: dict[str, Any],
    event_type: str,
    registry_key: str | None = None,
) -> None:
    """Generic event publisher with error handling."""
    try:
        # Derive registry key from event_type if not provided
        if registry_key is None:
            registry_key = event_type.replace("_complete", "").replace("_started", "")

        # Validate output has required fields
        if "sub_problem_index" not in output:
            logger.warning(
                f"[EVENT WARNING] Missing sub_problem_index in {event_type} output, "
                f"defaulting to 0. This may cause UI issues."
            )

        # Get registry and extract data
        registry = get_event_registry()
        data = registry.extract(registry_key, output)

        if data:
            # Add sub_problem_index from state to event data
            sub_problem_index = output.get("sub_problem_index", 0)
            data["sub_problem_index"] = sub_problem_index

            logger.info(
                f"[EVENT DEBUG] Publishing {event_type} | sub_problem_index={sub_problem_index} | "
                f"data keys: {list(data.keys())}"
            )
            self.publisher.publish_event(session_id, event_type, data)
        else:
            logger.error(
                f"[EVENT ERROR] Extractor returned no data for {event_type} "
                f"(registry_key={registry_key}). Output keys: {list(output.keys())}"
            )
            # Publish error event so UI knows something went wrong
            self.publisher.publish_event(
                session_id,
                "error",
                {
                    "error": f"Event extraction failed for {event_type}",
                    "error_type": "EventExtractionError",
                    "sub_problem_index": output.get("sub_problem_index", 0),
                }
            )
    except Exception as e:
        logger.error(f"Failed to publish {event_type} for session {session_id}: {e}", exc_info=True)
        # Publish error event instead of swallowing the error
        self.publisher.publish_event(
            session_id,
            "error",
            {
                "error": str(e),
                "error_type": type(e).__name__,
                "sub_problem_index": output.get("sub_problem_index", 0),
            }
        )
```

**Rationale:** Never let event publication fail silently - always notify the UI when something goes wrong so it can display an error instead of hanging.

#### Solution 4: Add Heartbeat Events for Long Operations

**File:** `/bo1/graph/nodes.py`

**Changes:**
```python
# Add to vote_node, synthesize_node, and meta_synthesize_node

async def synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Synthesize sub-problem results with progress heartbeat."""
    logger.info("synthesize_node: Starting synthesis")

    # Publish "synthesis_started" event FIRST
    # (EventCollector already does this, but verify it's working)

    # Convert graph state to v1 DeliberationState for facilitator
    v1_state = graph_state_to_deliberation_state(state)

    # Create facilitator agent
    facilitator = FacilitatorAgent()

    # Long-running operation - send heartbeat every 5 seconds
    import asyncio
    from bo1.state.redis_manager import RedisManager

    redis_manager = RedisManager()
    session_id = state.get("session_id")

    async def send_heartbeat():
        """Send heartbeat events during long synthesis."""
        while True:
            await asyncio.sleep(5)
            if session_id:
                # Publish heartbeat event (frontend can show "Still working...")
                redis_manager.publish_event(
                    session_id,
                    "synthesis_progress",
                    {
                        "message": "Synthesis in progress...",
                        "sub_problem_index": state.get("sub_problem_index", 0),
                    }
                )

    # Start heartbeat task
    heartbeat_task = asyncio.create_task(send_heartbeat())

    try:
        # Perform synthesis
        synthesis, llm_response = await facilitator.synthesize_deliberation(
            state=v1_state,
            votes=list(v1_state.votes.values()),
            vote_aggregation=v1_state.vote_aggregation,
        )

        # Cancel heartbeat
        heartbeat_task.cancel()

        # ... rest of synthesis logic ...

    except Exception as e:
        heartbeat_task.cancel()
        raise
```

**Rationale:** For operations that take >5 seconds (synthesis, voting), send periodic heartbeat events so the UI knows the system is still working, not stuck.

### Success Metrics

- **0 silent failures**: All sub-problem failures produce error events visible in UI
- **100% sub_problem_index propagation**: Every event has correct sub_problem_index field
- **<1% facilitator decision errors**: Invalid decisions caught and recovered via fallback logic

### Testing Checklist

- [ ] Multi sub-problem meeting (3+ sub-problems) - all complete successfully
- [ ] Facilitator override scenario - verify fallback logic selects valid persona
- [ ] Research trigger followed by contribution - verify no crashes
- [ ] Sub-problem with invalid persona selection - verify error event published
- [ ] Long synthesis (30+ seconds) - verify heartbeat events appear in UI

---

## Issue #4: Lack of Genuine Discussion - Experts Don't Challenge Each Other

### Root Cause Analysis

**What's Broken:**
Expert contributions feel superficial and agreeable rather than critically engaging with each other's points. They don't draw conclusions, make recommendations, or challenge assumptions.

**Why It Happens:**

1. **Generic Persona Prompts Lack Specific Behaviors** (`/bo1/prompts/reusable_prompts.py` - not shown but referenced):
   From the research file `PROMPT_ENGINEERING_FRAMEWORK.md` lines 470-487:
   ```xml
   <system_role>
   You are {{PERSONA_NAME}}, {{PERSONA_DESCRIPTION}}.

   Your role in this deliberation:
   - Provide expertise from your unique perspective: {{EXPERTISE_AREAS}}
   - Challenge assumptions and ask probing questions
   - Support claims with reasoning and evidence
   - Acknowledge limitations of your perspective
   - Build on others' contributions constructively
   - Maintain your professional character and communication style: {{COMMUNICATION_STYLE}}

   Behavioral guidelines:
   - ALWAYS: {{ALWAYS_BEHAVIORS}}
   - NEVER: {{NEVER_BEHAVIORS}}
   - WHEN UNCERTAIN: {{UNCERTAINTY_PROTOCOL}}
   </system_role>
   ```

   The current prompts likely don't emphasize **"Challenge assumptions"** and **"Build on others' contributions"** strongly enough.

2. **No Explicit Disagreement Incentives** (`CONSENSUS_BUILDING_RESEARCH.md` lines 293-304):
   > **Stanford Simulacra (Generative Agents)**
   > **Quote:** "Don't accurately reflect the full spectrum of human behavior, which includes conflict and disagreement."
   > **Implication:** Pure LLM agents default to agreement. Need explicit mechanisms to surface disagreement.

   The system doesn't have prompts that explicitly encourage disagreement or contrarian views beyond the moderator interventions.

3. **Missing "Recommendation" Format in Prompts**:
   From `CLAUDE.md` lines 29-36:
   ```
   **CRITICAL**: Use recommendations (free-form), NOT binary votes.

   - `Recommendation` model - `recommendation` field (string), NOT `decision` enum
   - Use `collect_recommendations()` NOT `collect_votes()`
   - Use `aggregate_recommendations_ai()` NOT `aggregate_votes_ai()`
   - Prompt: `RECOMMENDATION_SYSTEM_PROMPT` with `<recommendation>` XML tags
   ```

   Experts should be prompted to **provide recommendations** in their contributions, not just observations.

4. **Facilitator Doesn't Explicitly Prompt for Depth** (`/bo1/agents/facilitator.py` lines 175-207):
   ```python
   # Build user message
   user_message = f"""Current round: {round_number} of {max_rounds}
   Total contributions so far: {len(state.contributions)}
   Personas participating: {", ".join([p.code for p in state.selected_personas])}

   Analyze the discussion and decide the next action."""
   ```

   The facilitator prompt doesn't ask for depth assessment or specify what "building on discussion" means.

**Evidence:**
- User report: "Expert responses don't feel like proper discussion - not challenging each other, not drawing conclusions/recommendations"
- Research finding: LLMs default to excessive politeness and agreement without explicit prompts
- Prompt framework recommends `<thinking>` tags to make reasoning visible, but contributions don't use them

### Best Practices

From `PROMPT_ENGINEERING_FRAMEWORK.md` lines 498-519:
> **Communication Protocol:**
> ```xml
> Format your contributions as:
>
> <thinking>
> Your private reasoning process:
> - What aspects of the problem relate to your expertise?
> - What questions or concerns arise from your perspective?
> - What evidence or frameworks support your view?
> - What are you uncertain about?
> </thinking>
>
> <contribution>
> Your public statement to the group (2-4 paragraphs):
> - Lead with your key insight or concern
> - Provide reasoning and evidence
> - Reference others' contributions if building on or challenging them
> - End with questions or areas needing further exploration
> </contribution>
> ```

From `CONSENSUS_BUILDING_RESEARCH.md` lines 319-343:
> **Balance Needed:**
> - **Early debate:** Encourage divergent thinking, multiple perspectives
> - **Late debate:** Encourage convergent thinking, synthesis
>
> **Recommendation:**
> ```python
> # Adjust moderator triggers based on debate phase
> def should_moderator_intervene_enhanced(state: DeliberationState) -> str:
>     current_phase = determine_debate_phase(state)
>
>     if current_phase == "early":  # Iterations 1-5
>         # Encourage divergence: trigger contrarian if too much agreement
>         if detect_premature_consensus(state):
>             return "contrarian"
> ```

### Implementation Plan

**Priority:** P1 (Core product value)
**Effort:** 4-5 days
**Risk:** Medium (affects LLM prompt quality, needs A/B testing)

#### Solution 1: Enhanced Persona Prompts with Critical Thinking

**File:** `/bo1/prompts/reusable_prompts.py` (or wherever persona prompts are defined)

**Changes:**
```python
def compose_persona_contribution_prompt(
    persona: PersonaProfile,
    problem_statement: str,
    previous_contributions: list[ContributionMessage],
    speaker_prompt: str,
    round_number: int,
) -> str:
    """Compose prompt for persona contribution with critical thinking emphasis."""

    # Determine debate phase
    if round_number <= 3:
        phase_instruction = """
        <debate_phase>EARLY - DIVERGENT THINKING</debate_phase>
        <phase_goals>
        - Explore multiple perspectives
        - Challenge initial assumptions
        - Raise concerns and risks
        - Identify gaps in analysis
        - DON'T seek consensus yet - surface disagreements
        </phase_goals>
        """
    elif round_number <= 7:
        phase_instruction = """
        <debate_phase>MIDDLE - DEEP ANALYSIS</debate_phase>
        <phase_goals>
        - Provide evidence for claims
        - Challenge weak arguments
        - Request clarification on unclear points
        - Build on strong ideas from others
        - Identify trade-offs and constraints
        </phase_goals>
        """
    else:
        phase_instruction = """
        <debate_phase>LATE - CONVERGENT THINKING</debate_phase>
        <phase_goals>
        - Synthesize key insights
        - Recommend specific actions
        - Acknowledge remaining uncertainties
        - Build consensus on critical points
        - Propose next steps
        </phase_goals>
        """

    # Format previous contributions for context
    discussion_history = "\n\n".join([
        f"[{c.persona_code}]: {c.content}"
        for c in previous_contributions[-5:]  # Last 5 contributions
    ])

    system_prompt = f"""You are {persona.name}, {persona.description}.

<expertise>
{persona.expertise_areas}
</expertise>

<communication_style>
{persona.communication_style}
</communication_style>

{phase_instruction}

<critical_thinking_protocol>
You MUST engage critically with the discussion:

1. **Challenge Assumptions**: If someone makes an assumption, question it
2. **Demand Evidence**: If a claim lacks support, ask for evidence
3. **Identify Gaps**: Point out what's missing from the analysis
4. **Build or Refute**: Explicitly agree/disagree with previous speakers
5. **Recommend Actions**: End with specific, actionable recommendations

**Format your response with explicit structure:**
- Start with: "Based on [previous speaker's] point about X..."
- Include: "I disagree/agree with [persona] because..."
- End with: "My recommendation is to [specific action]..."
</critical_thinking_protocol>

<forbidden_patterns>
- Generic agreement ("I agree with the previous speakers...")
- Vague observations without conclusions
- Listing facts without analysis
- Ending without a recommendation or question
</forbidden_patterns>

<problem_context>
{problem_statement}
</problem_context>

<previous_discussion>
{discussion_history}
</previous_discussion>

<your_focus>
{speaker_prompt}
</your_focus>
"""

    user_message = f"""Provide your contribution following this structure:

<thinking>
(Private reasoning - not shown to other experts)
- Which previous points relate to my expertise?
- What do I disagree with or find concerning?
- What evidence supports my position?
- What am I uncertain about?
</thinking>

<contribution>
(Public statement to the group - 2-4 paragraphs)

[Start by referencing a specific previous contribution]
[Provide your analysis with clear reasoning]
[Challenge weak points or build on strong ones]
[End with specific recommendations or questions]
</contribution>

Remember: This is round {round_number}. Focus on {phase_instruction.split('</debate_phase>')[0].split('>')[-1]} thinking."""

    return system_prompt, user_message
```

**Rationale:**
- Phase-specific instructions align with research on divergent→convergent thinking
- Explicit "critical thinking protocol" overcomes LLM politeness bias
- Forbidden patterns prevent generic, non-substantive contributions
- Required structure ensures every contribution engages with previous speakers

#### Solution 2: Facilitator Prompts for Depth and Challenge

**File:** `/bo1/agents/facilitator.py`

**Changes:**
```python
# Lines 122-241 - Enhanced facilitator prompts

async def decide_next_action(
    self, state: DeliberationState, round_number: int, max_rounds: int
) -> tuple[FacilitatorDecision, LLMResponse | None]:
    """Decide what should happen next with quality assessment."""

    # ... existing validation logic ...

    # NEW: Assess discussion quality before making decision
    quality_assessment = self._assess_discussion_quality(state, round_number)

    # Build discussion history with quality notes
    discussion_history = self._format_discussion_history(state)

    # Build phase objectives with quality emphasis
    phase_objectives = self._get_phase_objectives_enhanced(
        state.phase, round_number, max_rounds, quality_assessment
    )

    # Compose facilitator prompt with quality focus
    system_prompt = compose_facilitator_prompt_enhanced(
        current_phase=state.phase,
        discussion_history=discussion_history,
        phase_objectives=phase_objectives,
        quality_assessment=quality_assessment,
        contribution_counts=contribution_counts,
        last_speakers=last_speakers,
    )

    # ... rest of decision logic ...

def _assess_discussion_quality(
    self, state: DeliberationState, round_number: int
) -> dict[str, Any]:
    """Assess the quality and depth of discussion."""

    recent_contributions = state.contributions[-6:]  # Last 2 rounds

    # Check for superficial patterns
    has_disagreement = any(
        "disagree" in c.content.lower() or "however" in c.content.lower()
        for c in recent_contributions
    )

    has_recommendations = any(
        "recommend" in c.content.lower() or "suggest" in c.content.lower()
        for c in recent_contributions
    )

    has_evidence = any(
        "because" in c.content.lower() or "data shows" in c.content.lower()
        for c in recent_contributions
    )

    has_questions = any(
        "?" in c.content
        for c in recent_contributions
    )

    # Build quality report
    quality_issues = []
    if not has_disagreement and round_number <= 5:
        quality_issues.append("PREMATURE_CONSENSUS - No disagreement detected in early rounds")
    if not has_recommendations:
        quality_issues.append("NO_RECOMMENDATIONS - Experts not providing actionable guidance")
    if not has_evidence:
        quality_issues.append("WEAK_REASONING - Claims lack supporting evidence")
    if not has_questions and round_number <= 7:
        quality_issues.append("NO_INQUIRY - Experts not asking probing questions")

    return {
        "has_disagreement": has_disagreement,
        "has_recommendations": has_recommendations,
        "has_evidence": has_evidence,
        "has_questions": has_questions,
        "quality_issues": quality_issues,
        "depth_score": sum([has_disagreement, has_recommendations, has_evidence, has_questions]) / 4.0
    }

def _get_phase_objectives_enhanced(
    self, phase: str, round_number: int, max_rounds: int, quality_assessment: dict
) -> str:
    """Get objectives for current phase with quality focus."""

    base_objectives = self._get_phase_objectives(phase, round_number, max_rounds)

    # Add quality-specific guidance
    quality_guidance = "\n\n**QUALITY CHECK:**\n"

    if quality_assessment["quality_issues"]:
        quality_guidance += f"⚠️ Issues detected:\n"
        for issue in quality_assessment["quality_issues"]:
            quality_guidance += f"  - {issue}\n"

        # Provide specific remediation instructions
        if "PREMATURE_CONSENSUS" in quality_assessment["quality_issues"]:
            quality_guidance += "\n**Action:** Trigger contrarian moderator to surface disagreements\n"
        if "NO_RECOMMENDATIONS" in quality_assessment["quality_issues"]:
            quality_guidance += "\n**Action:** Prompt next speaker to provide specific recommendations\n"
        if "WEAK_REASONING" in quality_assessment["quality_issues"]:
            quality_guidance += "\n**Action:** Trigger skeptic moderator to demand evidence\n"
        if "NO_INQUIRY" in quality_assessment["quality_issues"]:
            quality_guidance += "\n**Action:** Select persona who hasn't asked probing questions yet\n"
    else:
        quality_guidance += f"✓ Discussion quality is good (depth score: {quality_assessment['depth_score']:.1%})\n"

    return base_objectives + quality_guidance
```

**Rationale:**
- Facilitator actively monitors discussion quality and intervenes when shallow
- Quality assessment drives moderator triggers (contrarian for premature consensus, skeptic for weak evidence)
- Explicit remediation instructions ensure facilitator takes corrective action

#### Solution 3: Add "Recommendation" to Contribution Schema

**File:** `/bo1/models/state.py` (or wherever ContributionMessage is defined)

**Changes:**
```python
from pydantic import BaseModel, Field

class ContributionMessage(BaseModel):
    """A contribution from a persona during deliberation."""

    persona_code: str
    persona_name: str
    content: str  # Main contribution text
    round_number: int
    timestamp: str

    # NEW: Explicit recommendation field
    recommendation: str | None = Field(
        default=None,
        description="Specific, actionable recommendation from this expert"
    )

    # NEW: References to other contributions
    references: list[str] = Field(
        default_factory=list,
        description="Persona codes of other experts whose contributions this builds on/challenges"
    )

    # NEW: Thinking process (not displayed but logged)
    thinking: str | None = Field(
        default=None,
        description="Expert's private reasoning process"
    )
```

**File:** `/bo1/agents/persona.py` (or wherever persona contribution is generated)

**Changes:**
```python
async def generate_contribution(
    self,
    persona: PersonaProfile,
    problem_statement: str,
    previous_contributions: list[ContributionMessage],
    speaker_prompt: str,
    round_number: int,
) -> ContributionMessage:
    """Generate persona contribution with explicit recommendation extraction."""

    # ... call LLM with enhanced prompt ...

    response = await self.broker.call_with_prompt(
        prompt_request=prompt_request,
        temperature=1.0,
        max_tokens=1500,
    )

    # Parse response to extract structured components
    content = response.content

    # Extract <thinking> block (if present)
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', content, re.DOTALL)
    thinking = thinking_match.group(1).strip() if thinking_match else None

    # Extract <contribution> block
    contrib_match = re.search(r'<contribution>(.*?)</contribution>', content, re.DOTALL)
    contribution_text = contrib_match.group(1).strip() if contrib_match else content

    # Extract recommendation (look for explicit recommendation statements)
    recommendation_patterns = [
        r'[Mm]y recommendation is to (.*?)(?:\.|$)',
        r'I recommend (.*?)(?:\.|$)',
        r'We should (.*?)(?:\.|$)',
        r'My advice is to (.*?)(?:\.|$)',
    ]

    recommendation = None
    for pattern in recommendation_patterns:
        match = re.search(pattern, contribution_text, re.IGNORECASE)
        if match:
            recommendation = match.group(1).strip()
            break

    # Extract references to other personas (mentioned by code or name)
    references = []
    for prev_contrib in previous_contributions:
        if (prev_contrib.persona_code in contribution_text or
            prev_contrib.persona_name in contribution_text):
            references.append(prev_contrib.persona_code)

    # Build structured contribution
    return ContributionMessage(
        persona_code=persona.code,
        persona_name=persona.name,
        content=contribution_text,
        round_number=round_number,
        timestamp=datetime.now(UTC).isoformat(),
        recommendation=recommendation,
        references=references,
        thinking=thinking,
    )
```

**Rationale:**
- Explicit `recommendation` field makes it clear when experts provide actionable guidance
- `references` field tracks engagement with other contributions (can be displayed in UI as "🔗 Responding to X")
- `thinking` field enables logging of reasoning process without cluttering UI

#### Solution 4: Display Recommendations Prominently in UI

**File:** `/frontend/src/lib/components/events/ExpertPerspectiveCard.svelte`

**Changes:**
```typescript
<script lang="ts">
    import type { SSEEvent } from '$lib/api/sse-events';

    interface Props {
        event: SSEEvent;
    }

    let { event }: Props = $props();

    const data = event.data as any;
    const personaName = data.persona_name || 'Expert';
    const personaCode = data.persona_code || '';
    const content = data.content || '';
    const recommendation = data.recommendation || null;  // NEW
    const references = data.references || [];  // NEW
</script>

<div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
    <div class="flex items-start gap-3 mb-3">
        <!-- Existing persona avatar and name -->
    </div>

    <!-- NEW: Show references if present -->
    {#if references.length > 0}
        <div class="mb-3 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span>
                Responding to {references.join(', ')}
            </span>
        </div>
    {/if}

    <!-- Existing content -->
    <div class="text-sm text-slate-700 dark:text-slate-300 prose prose-sm">
        {content}
    </div>

    <!-- NEW: Highlight recommendation if present -->
    {#if recommendation}
        <div class="mt-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-3">
            <div class="flex items-start gap-2">
                <svg class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                    <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">
                        Recommendation
                    </h4>
                    <p class="text-sm text-blue-800 dark:text-blue-200">
                        {recommendation}
                    </p>
                </div>
            </div>
        </div>
    {/if}
</div>
```

**Rationale:** Makes recommendations visually distinct and prominent, encouraging experts to provide them.

### Success Metrics

- **80%+ contributions have recommendations**: Most expert contributions end with specific advice
- **50%+ contributions reference others**: Experts actively engage with previous speakers
- **Disagreement rate >30% in early rounds**: Early debate shows healthy conflict
- **User feedback**: "Experts challenge each other and provide actionable advice"

### Testing Checklist

- [ ] Early rounds (1-3) - verify experts disagree and challenge assumptions
- [ ] Middle rounds (4-7) - verify experts provide evidence and build on points
- [ ] Late rounds (8+) - verify experts converge on recommendations
- [ ] Check contributions for recommendation field - should be present in 80%+
- [ ] UI displays recommendations prominently in blue callout boxes
- [ ] Facilitator triggers moderators when quality issues detected

---

## Issue #5: Single Expert Dominance - One Expert Speaks 10+ Rounds

### Root Cause Analysis

**What's Broken:**
A single expert can dominate the discussion for 10+ consecutive rounds without the facilitator rotating speakers or using metrics (novelty, repetition, consensus) to prevent this.

**Why It Happens:**

1. **Facilitator Rotation Logic is Weak** (`/bo1/agents/facilitator.py` lines 180-200):
   ```python
   # Compute contribution statistics for rotation guidance
   contribution_counts: dict[str, int] = {}
   last_speakers: list[str] = []

   if state.contributions:
       # Count contributions per persona
       for contrib in state.contributions:
           persona_code = contrib.persona_code
           contribution_counts[persona_code] = contribution_counts.get(persona_code, 0) + 1

       # Get last N speakers (most recent last)
       last_speakers = [c.persona_code for c in state.contributions[-5:]]

   # Compose facilitator prompt with rotation guidance
   system_prompt = compose_facilitator_prompt(
       current_phase=state.phase,
       discussion_history=discussion_history,
       phase_objectives=phase_objectives,
       contribution_counts=contribution_counts if contribution_counts else None,
       last_speakers=last_speakers if last_speakers else None,
   )
   ```

   The facilitator receives contribution counts and last speakers, BUT the prompt doesn't enforce hard limits or provide clear rotation rules.

2. **Metrics Not Used in Decision Logic** (`/bo1/graph/safety/loop_prevention.py` - check_convergence_node):
   From the code architecture, convergence node calculates novelty, repetition, and consensus scores, but these aren't passed to the facilitator for decision-making. The facilitator makes decisions blindly without seeing these critical signals.

3. **No Hard Cap on Consecutive Contributions** (Missing from codebase):
   There's no code that says "if persona X has spoken 3+ times in a row, MUST select different persona."

4. **Facilitator Overrides Can Break Rotation** (`/bo1/graph/nodes.py` lines 268-298):
   ```python
   # SAFETY CHECK: Prevent premature voting (Bug #3 fix)
   min_rounds_before_voting = 3
   if decision.action == "vote" and round_number < min_rounds_before_voting:
       # Override decision to continue
       # Select a persona who hasn't spoken much
       personas = state.get("personas", [])
       contributions = state.get("contributions", [])

       # Count contributions per persona
       contribution_counts: dict[str, int] = {}
       for contrib in contributions:
           persona_code = contrib.persona_code
           contribution_counts[persona_code] = contribution_counts.get(persona_code, 0) + 1

       # Find persona with fewest contributions
       min_contributions = min(contribution_counts.values()) if contribution_counts else 0
       candidates = [
           p.code for p in personas if contribution_counts.get(p.code, 0) == min_contributions
       ]

       next_speaker = candidates[0] if candidates else personas[0].code if personas else "unknown"
   ```

   This override logic is good, but it ONLY triggers when preventing premature voting. It should be applied on EVERY "continue" decision.

**Evidence:**
- User report: "One expert dominates 10+ rounds"
- Research finding from `CONSENSUS_BUILDING_RESEARCH.md` line 222: "Stubborn agents (fixed opinions) have dominant influence on group consensus, creating leader-follower dynamics."

### Best Practices

From `CONSENSUS_BUILDING_RESEARCH.md` lines 758-792:
> **Technique: Novelty Scoring**
> ```python
> def calculate_novelty_score(new_contribution: str,
>                            past_contributions: list[str]) -> float:
>     """
>     Calculate how novel this contribution is vs. past contributions.
>     Returns: 0-1 score (0 = pure repetition, 1 = completely novel)
>     """
>     # ... uses embeddings to detect repetition ...
> ```
>
> **Stopping Criterion:**
> - If average novelty < 0.2 for 3 consecutive contributions → stop debate
> - Agents are just repeating themselves → diminishing returns

From `PROMPT_ENGINEERING_FRAMEWORK.md` - rotation should be explicit in prompts.

### Implementation Plan

**Priority:** P0 (Breaks core deliberation quality)
**Effort:** 3-4 days
**Risk:** Medium (affects facilitator logic, needs testing)

#### Solution 1: Enforce Hard Rotation Limits in Facilitator

**File:** `/bo1/agents/facilitator.py`

**Changes:**
```python
# Lines 122-241 - Enhanced with hard rotation limits

async def decide_next_action(
    self, state: DeliberationState, round_number: int, max_rounds: int
) -> tuple[FacilitatorDecision, LLMResponse | None]:
    """Decide what should happen next with mandatory rotation enforcement."""

    # ... existing checks for research and moderators ...

    # NEW: Check for expert dominance BEFORE calling LLM
    rotation_override = self._check_rotation_limits(state)

    if rotation_override:
        logger.info(f"🔄 Rotation override: {rotation_override['reason']}")

        return (
            FacilitatorDecision(
                action="continue",
                reasoning=rotation_override["reason"],
                next_speaker=rotation_override["next_speaker"],
                speaker_prompt=rotation_override["prompt"],
            ),
            None,  # Skip LLM call, use rule-based override
        )

    # ... rest of facilitator logic (LLM call, etc.) ...

def _check_rotation_limits(self, state: DeliberationState) -> dict[str, str] | None:
    """Check if rotation rules require overriding facilitator decision.

    Returns:
        dict with rotation override info if limits exceeded, None otherwise
    """
    contributions = state.contributions
    personas = state.selected_personas

    if not contributions or not personas:
        return None

    # Rule 1: No expert can speak more than 3 times in a row
    last_speakers = [c.persona_code for c in contributions[-3:]]
    if len(last_speakers) == 3 and len(set(last_speakers)) == 1:
        dominant_expert = last_speakers[0]

        # Select different expert (least contributions first)
        contribution_counts = self._count_contributions(contributions)
        other_experts = [p.code for p in personas if p.code != dominant_expert]

        # Sort by contribution count (ascending)
        other_experts.sort(key=lambda code: contribution_counts.get(code, 0))

        next_speaker = other_experts[0] if other_experts else dominant_expert

        return {
            "reason": f"ROTATION LIMIT: {dominant_expert} spoke 3 times consecutively, "
                     f"rotating to {next_speaker} to ensure balanced participation",
            "next_speaker": next_speaker,
            "prompt": "Provide a fresh perspective on the discussion so far. "
                     "Challenge points you disagree with or build on strong arguments."
        }

    # Rule 2: No expert can speak more than 40% of total rounds (dominance threshold)
    contribution_counts = self._count_contributions(contributions)
    total_contributions = len(contributions)
    dominance_threshold = 0.4  # 40%

    for persona_code, count in contribution_counts.items():
        contribution_ratio = count / total_contributions

        if contribution_ratio > dominance_threshold:
            # This expert is dominating - exclude them from next round
            other_experts = [
                p.code for p in personas
                if contribution_counts.get(p.code, 0) < count * 0.7  # At least 30% fewer contributions
            ]

            if other_experts:
                # Select least-contributing expert
                other_experts.sort(key=lambda code: contribution_counts.get(code, 0))
                next_speaker = other_experts[0]

                return {
                    "reason": f"DOMINANCE LIMIT: {persona_code} has spoken {count}/{total_contributions} "
                             f"times ({contribution_ratio:.0%}), exceeding 40% threshold. "
                             f"Rotating to {next_speaker} for balance.",
                    "next_speaker": next_speaker,
                    "prompt": "We haven't heard much from your perspective. What concerns or "
                             "opportunities do you see that haven't been discussed?"
                }

    # Rule 3: Every expert must speak at least once per 2 rounds (minimum participation)
    if total_contributions >= 4:  # After 2 full rounds
        silent_experts = [
            p.code for p in personas
            if contribution_counts.get(p.code, 0) == 0 or
               contribution_counts.get(p.code, 0) < total_contributions / (len(personas) * 2)
        ]

        if silent_experts:
            # Randomly select one silent expert (avoid predictability)
            import random
            next_speaker = random.choice(silent_experts)

            return {
                "reason": f"PARTICIPATION ENFORCEMENT: {next_speaker} has been relatively quiet. "
                         f"Ensuring all perspectives are heard.",
                "next_speaker": next_speaker,
                "prompt": "Your expertise is needed here. What are your thoughts on the points raised so far? "
                         "What risks or opportunities do you see from your perspective?"
            }

    return None  # No rotation override needed

def _count_contributions(self, contributions: list) -> dict[str, int]:
    """Count contributions per persona."""
    counts: dict[str, int] = {}
    for contrib in contributions:
        persona_code = contrib.persona_code
        counts[persona_code] = counts.get(persona_code, 0) + 1
    return counts
```

**Rationale:**
- Rule 1 (3 consecutive) prevents immediate dominance
- Rule 2 (40% threshold) prevents long-term dominance
- Rule 3 (minimum participation) ensures all experts contribute
- Rules are enforced BEFORE LLM call, making them mandatory

#### Solution 2: Pass Metrics to Facilitator Decision

**File:** `/bo1/graph/safety/loop_prevention.py` (check_convergence_node)

**Changes:**
```python
async def check_convergence_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Check convergence with enhanced metrics for facilitator."""
    logger.info("check_convergence_node: Checking if discussion should stop")

    # ... existing convergence calculation ...

    # NEW: Calculate per-expert novelty scores
    contributions = state.get("contributions", [])
    contribution_counts = {}
    expert_novelty_scores = {}

    # Group contributions by expert
    expert_contributions = {}
    for contrib in contributions:
        code = contrib.persona_code
        if code not in expert_contributions:
            expert_contributions[code] = []
        expert_contributions[code].append(contrib.content)

    # Calculate novelty for each expert's recent contributions
    for code, expert_contribs in expert_contributions.items():
        if len(expert_contribs) >= 2:
            # Check if expert's last 2 contributions are repetitive
            recent_novelty = calculate_novelty_score_semantic([
                {"content": c} for c in expert_contribs[-2:]
            ])
            expert_novelty_scores[code] = recent_novelty

        contribution_counts[code] = len(expert_contribs)

    # Identify repetitive experts (novelty < 0.3)
    repetitive_experts = [
        code for code, novelty in expert_novelty_scores.items()
        if novelty < 0.3
    ]

    # ... existing should_stop logic ...

    # Return enhanced state with expert-level metrics
    return {
        "should_stop": should_stop,
        "stop_reason": stop_reason,
        "round_number": state.get("round_number", 0) + 1,
        "convergence_score": convergence_score,
        "novelty_score": novelty_score,
        "conflict_score": conflict_score,
        "drift_events": drift_events,
        # NEW: Expert-level metrics for facilitator
        "contribution_counts": contribution_counts,
        "expert_novelty_scores": expert_novelty_scores,
        "repetitive_experts": repetitive_experts,
        "metrics": state.get("metrics"),
        "sub_problem_index": state.get("sub_problem_index", 0),
    }
```

**File:** `/bo1/agents/facilitator.py`

**Changes:**
```python
# Use expert metrics in facilitator prompt
system_prompt = compose_facilitator_prompt_with_metrics(
    current_phase=state.phase,
    discussion_history=discussion_history,
    phase_objectives=phase_objectives,
    contribution_counts=state.contribution_counts,  # From convergence node
    expert_novelty_scores=state.expert_novelty_scores,  # NEW
    repetitive_experts=state.repetitive_experts,  # NEW
    last_speakers=last_speakers,
)

def compose_facilitator_prompt_with_metrics(
    current_phase: str,
    discussion_history: str,
    phase_objectives: str,
    contribution_counts: dict[str, int] | None,
    expert_novelty_scores: dict[str, float] | None,
    repetitive_experts: list[str] | None,
    last_speakers: list[str] | None,
) -> str:
    """Compose facilitator prompt with expert-level metrics."""

    prompt = f"""You are the Facilitator for this deliberation. Your role is to guide the discussion
toward productive outcomes by selecting the right expert to speak next.

<current_phase>{current_phase}</current_phase>

<phase_objectives>
{phase_objectives}
</phase_objectives>

<expert_participation_report>
{_format_participation_report(contribution_counts, expert_novelty_scores, repetitive_experts)}
</expert_participation_report>

<recent_speakers>
Last 5 speakers: {", ".join(last_speakers) if last_speakers else "None yet"}
</recent_speakers>

<rotation_rules>
**CRITICAL ROTATION CONSTRAINTS:**

1. **Balance**: Prefer experts who have spoken less
2. **Novelty**: Avoid experts with novelty < 0.3 (repeating themselves)
3. **Diversity**: Don't select same expert as last speaker unless critical
4. **Fresh Perspectives**: Select experts who can challenge current direction

If an expert is repetitive (novelty < 0.3), DO NOT select them. They need a break.
</rotation_rules>

<discussion_history>
{discussion_history}
</discussion_history>

Analyze the discussion and decide who should speak next. Focus on expert rotation and fresh perspectives.
"""

    return prompt

def _format_participation_report(
    contribution_counts: dict[str, int] | None,
    expert_novelty_scores: dict[str, float] | None,
    repetitive_experts: list[str] | None,
) -> str:
    """Format expert participation metrics for facilitator."""

    if not contribution_counts:
        return "No contributions yet (initial round)"

    report = "Expert Participation Metrics:\n\n"

    # Sort by contribution count (descending)
    sorted_experts = sorted(contribution_counts.items(), key=lambda x: x[1], reverse=True)

    for code, count in sorted_experts:
        novelty = expert_novelty_scores.get(code, 1.0) if expert_novelty_scores else 1.0
        is_repetitive = code in repetitive_experts if repetitive_experts else False

        report += f"- {code}: {count} contributions, novelty={novelty:.2f}"

        if is_repetitive:
            report += " ⚠️ REPETITIVE - avoid selecting"
        elif novelty < 0.5:
            report += " 🟡 Low novelty - consider fresh perspective"

        report += "\n"

    return report
```

**Rationale:** Facilitator now has visibility into which experts are repetitive and can avoid selecting them.

#### Solution 3: Display Contribution Counts in UI

**File:** `/frontend/src/lib/components/ui/DecisionMetrics.svelte`

**Changes:**
```typescript
// Lines 214-243 - Enhanced contribution stats with dominance warning
{#if contributionsByExpert.length > 0}
    {@const totalContributions = contributionsByExpert.reduce((sum, e) => sum + e.count, 0)}
    {@const dominanceThreshold = totalContributions * 0.4}
    {@const dominantExperts = contributionsByExpert.filter(e => e.count > dominanceThreshold)}

    <div class="bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 p-4" transition:fade>
        <h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" />
            </svg>
            Contributions
        </h3>

        <!-- NEW: Dominance warning -->
        {#if dominantExperts.length > 0}
            <div class="mb-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800 p-2">
                <div class="flex items-start gap-2">
                    <svg class="w-4 h-4 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p class="text-xs text-orange-800 dark:text-orange-200">
                        {dominantExperts.map(e => e.name).join(', ')} {dominantExperts.length === 1 ? 'is' : 'are'} dominating the discussion. System should rotate speakers.
                    </p>
                </div>
            </div>
        {/if}

        <div class="space-y-2">
            {#each contributionsByExpert as { name, count }}
                {@const maxCount = Math.max(...contributionsByExpert.map(c => c.count))}
                {@const isDominant = count > dominanceThreshold}
                <div class="flex items-center gap-2">
                    <div class="flex-1">
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-xs text-slate-700 dark:text-slate-300 truncate flex items-center gap-1">
                                {name}
                                {#if isDominant}
                                    <svg class="w-3 h-3 text-orange-600 dark:text-orange-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                                    </svg>
                                {/if}
                            </span>
                            <span class="text-xs font-medium {isDominant ? 'text-orange-600 dark:text-orange-400' : 'text-slate-600 dark:text-slate-400'}">
                                {count}
                            </span>
                        </div>
                        <div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                            <div
                                class="{isDominant ? 'bg-orange-500' : 'bg-blue-500'} h-1.5 rounded-full transition-all duration-300"
                                style="width: {(count / maxCount) * 100}%"
                            ></div>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    </div>
{/if}
```

**Rationale:** Makes dominance visible to users so they can see if the system is properly rotating speakers.

### Success Metrics

- **No expert >40% of total contributions**: Hard limit enforced
- **No expert >3 consecutive contributions**: Hard limit enforced
- **All experts speak at least 1x per 2 rounds**: Participation enforced
- **Average novelty per expert >0.4**: Experts stay fresh, not repetitive
- **User feedback**: "Discussion feels balanced, all experts contribute meaningfully"

### Testing Checklist

- [ ] Meeting with 5 experts, 10 rounds - verify no expert speaks >4 times
- [ ] Meeting where facilitator tries to select same expert 3x - verify override
- [ ] Expert with novelty <0.3 - verify facilitator skips them
- [ ] UI shows dominance warning when expert >40%
- [ ] All experts speak at least once by round 6 (3 full rotation cycles)

---

## Cross-Cutting Issues and Recommendations

### Issue: Poor Console Logging Hindering Debugging

**Observation:** User mentioned "console seems to have a decent grasp of the meeting flow" but UI doesn't reflect it.

**Recommendation:** Enhance logging throughout the stack:

```python
# Backend: Structured logging with context
logger.info(
    "[FACILITATOR] Decision made",
    extra={
        "session_id": session_id,
        "round": round_number,
        "action": decision.action,
        "next_speaker": decision.next_speaker,
        "sub_problem_index": sub_problem_index,
    }
)

# Frontend: Consistent event logging
console.log('[EVENT]', {
    type: event.event_type,
    subProblem: event.data.sub_problem_index,
    timestamp: event.timestamp,
    data: event.data
});
```

### Issue: Lack of End-to-End Testing

**Recommendation:** Add integration tests that validate the full flow:

```python
# tests/integration/test_multi_subproblem_flow.py

async def test_multi_subproblem_deliberation_completes():
    """Test that multi-subproblem deliberation completes without hanging."""

    # Create session with 3 sub-problems
    session = await create_session(
        problem="Should we expand to EU markets?",
        decompose_to_subproblems=True,
    )

    # Collect all events
    events = []
    async for event in stream_session_events(session.id):
        events.append(event)

        # Timeout after 5 minutes
        if len(events) > 0 and (datetime.now() - events[0].timestamp).seconds > 300:
            pytest.fail("Deliberation exceeded 5 minute timeout")

        if event.event_type == "complete":
            break

    # Verify all sub-problems completed
    subproblem_started = [e for e in events if e.event_type == "subproblem_started"]
    subproblem_complete = [e for e in events if e.event_type == "subproblem_complete"]

    assert len(subproblem_started) == 3, "All 3 sub-problems should start"
    assert len(subproblem_complete) == 3, "All 3 sub-problems should complete"

    # Verify meta synthesis occurred
    meta_synthesis = [e for e in events if e.event_type == "meta_synthesis_complete"]
    assert len(meta_synthesis) == 1, "Meta synthesis should occur once"

    # Verify no expert dominated
    contributions = [e for e in events if e.event_type == "contribution"]
    contribution_counts = {}
    for contrib in contributions:
        code = contrib.data["persona_code"]
        contribution_counts[code] = contribution_counts.get(code, 0) + 1

    max_contributions = max(contribution_counts.values())
    total_contributions = len(contributions)

    assert max_contributions / total_contributions < 0.4, "No expert should dominate >40%"
```

---

## Implementation Priority and Timeline

### Phase 1: Critical Bugs (Week 1-2)
**Priority: P0 - Blocks user experience**

1. **Issue #1** (UI not updating) - 2-3 days
   - Fix event loading sequence
   - Improve deduplication
   - Add error boundaries
   - Preload components

2. **Issue #3** (Sub-problems failing) - 3-4 days
   - Validate facilitator decisions
   - Ensure sub_problem_index propagation
   - Add error event publication
   - Add heartbeat events

3. **Issue #5** (Expert dominance) - 3-4 days
   - Enforce rotation limits
   - Pass metrics to facilitator
   - Display contribution counts

**Estimated Timeline:** 10-14 days
**Risk:** Medium (requires careful testing)

### Phase 2: Core Product Value (Week 3-4)
**Priority: P1 - Affects product quality**

4. **Issue #2** (Sidebar disconnect) - 1-2 days
   - Pass active sub-problem context
   - Add "Overall" tab
   - Add context indicator

5. **Issue #4** (Shallow discussion) - 4-5 days
   - Enhanced persona prompts
   - Facilitator depth assessment
   - Add recommendation field
   - Update UI to display recommendations

**Estimated Timeline:** 6-8 days
**Risk:** Medium (prompt changes need A/B testing)

### Phase 3: Monitoring and Observability (Week 5)
**Priority: P2 - Enables continuous improvement**

6. Add comprehensive logging
7. Build integration test suite
8. Set up metrics dashboard
9. A/B test new prompts

**Estimated Timeline:** 5-7 days
**Risk:** Low (tooling and tests)

---

## Success Metrics

### User Experience Metrics
- **Meeting completion rate**: 95%+ (vs current ~70% estimated)
- **Average meeting duration**: 5-8 minutes for 3 sub-problems
- **User satisfaction**: "Meetings feel productive and experts provide actionable advice"

### Technical Metrics
- **Event display latency**: <500ms from SSE to UI render
- **Sub_problem_index propagation**: 100% of events have correct field
- **Expert dominance rate**: 0% exceed 40% threshold
- **Recommendation rate**: 80%+ contributions have explicit recommendations

### Quality Metrics
- **Early disagreement rate**: >30% in rounds 1-3
- **Late consensus rate**: >70% convergence in rounds 8+
- **Novelty maintenance**: >0.4 average novelty per expert
- **Balanced participation**: All experts speak at least 1x per 2 rounds

---

## Appendix: Key Code Locations

### Backend Files
- `/bo1/graph/config.py` - Graph construction and routing
- `/bo1/graph/nodes.py` - Node implementations (facilitator_decide_node, etc.)
- `/bo1/graph/routers.py` - Routing logic between nodes
- `/bo1/graph/safety/loop_prevention.py` - Convergence checking
- `/bo1/graph/quality_metrics.py` - Novelty, conflict, drift metrics
- `/bo1/agents/facilitator.py` - Facilitator decision logic
- `/backend/api/event_collector.py` - Event extraction and publishing
- `/backend/api/event_publisher.py` - Redis PubSub publishing
- `/backend/api/streaming.py` - SSE endpoint and streaming

### Frontend Files
- `/frontend/src/routes/(app)/meeting/[id]/+page.svelte` - Main meeting UI
- `/frontend/src/lib/components/ui/DecisionMetrics.svelte` - Sidebar metrics
- `/frontend/src/lib/components/events/ExpertPerspectiveCard.svelte` - Contribution cards

### Configuration Files
- `/bo1/data/personas.json` - Persona definitions
- `/bo1/prompts/reusable_prompts.py` - System prompts

---

---

## ARCHITECTURAL REDESIGN: Multi-Expert-Per-Round System

### Critical Flaw in Current Architecture

**The Fundamental Problem:**

The current system operates on a **1 expert per round** model (serial, turn-based), which creates three insurmountable issues:

1. **Mathematically Impossible Rotation Rules**: With 5 experts and 1 speaker per round, the facilitator's rotation logic states "every expert should speak 1x per 2 rounds." This is mathematically impossible:
   - 5 experts × 1 contribution per 2 rounds = 2.5 contributions needed per 2 rounds
   - But only 2 rounds × 1 speaker = 2 contributions actually happen
   - Result: Rule can never be satisfied, creating silent failures and infinite loops

2. **Unrealistic Meeting Dynamics**: Real expert panels have multiple people contributing in each round/phase. The serial model feels like a queue system, not a collaborative deliberation.

3. **Conflicting Logic Patterns**: The facilitator attempts to enforce rotation, prevent dominance, and ensure participation using rules designed for parallel contribution, but implemented in a serial architecture.

**Evidence in Code:**

```python
# bo1/agents/facilitator.py:212-219
# Rule 3: Every expert must speak at least once per 2 rounds (minimum participation)
if total_contributions >= 4:  # After 2 full rounds
    silent_experts = [
        p.code for p in personas
        if contribution_counts.get(p.code, 0) == 0 or
        contribution_counts.get(p.code, 0) < total_contributions / (len(personas) * 2)
    ]
```

This rule assumes `total_contributions / (len(personas) * 2)` yields a meaningful threshold, but with 5 experts and serial execution:
- After 2 rounds: 2 contributions ÷ (5 experts × 2) = 0.2 contributions expected per expert
- Since you can't have 0.2 contributions, this creates edge cases

**Current Flow (SERIAL):**
```
Round 1: Expert A speaks (1 contribution)
Round 2: Expert B speaks (1 contribution)
Round 3: Expert C speaks (1 contribution)
Round 4: Expert D speaks (1 contribution)
Round 5: Expert E speaks (1 contribution)
Round 6: Back to Expert A...
```

This creates a **meeting that drags on** (each expert waits 4+ rounds to speak again) and feels **artificial**.

---

### New Architecture Design

**Core Principle:** Move from **serial, 1-expert-per-round** to **parallel, multi-expert-per-round with semantic deduplication**.

#### Design Overview

**New Flow (PARALLEL ROUNDS WITH PHASES):**
```
Round 1 (Exploration Phase):
  ├─ Expert A contributes
  ├─ Expert B contributes
  ├─ Expert C contributes
  └─ [All contributions run in parallel, async/await gather]

Round 2 (Challenge Phase):
  ├─ Expert D challenges A's point
  ├─ Expert E challenges B's assumption
  ├─ Expert A responds with evidence
  └─ [Facilitator selects 2-3 experts who can challenge/build on Round 1]

Round 3 (Convergence Phase):
  ├─ Expert A: Recommendation
  ├─ Expert B: Recommendation (agrees with A)
  ├─ Expert C: Alternative recommendation
  └─ [All experts provide final positions]

Vote & Synthesis
```

**Key Changes:**

1. **Multiple Experts Per Round**: 2-5 experts contribute per round (not 1)
2. **Phase-Based Structure**: Exploration → Challenge → Convergence (from MEETING_FIXES.md)
3. **Semantic Deduplication**: Voyage AI embeddings prevent repetition in real-time
4. **Exploration Scoring**: LLM judge ensures depth before allowing convergence
5. **Dynamic Expert Selection**: Facilitator picks experts based on novelty, contribution balance, and aspect coverage

---

### Component 1: Round Structure (Multi-Expert Contributions)

**Rationale:**

Research shows multi-agent debates are more effective when:
- Multiple agents contribute per turn (CAMEL, Director Models)
- Phases are explicit (Exploration → Challenge → Convergence from Delphi Method)
- Turn budgets are hard-capped (80 tokens from MEETING_FIXES.md prevents rambling)

**Implementation Approach:**

**A. New Node: `parallel_round_node`**

Replaces: `persona_contribute_node` (which handles 1 expert)

```python
# bo1/graph/nodes.py (NEW NODE)

async def parallel_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute a round with multiple experts contributing in parallel.

    Flow:
    1. Facilitator selects 2-5 experts based on:
       - Phase (exploration = more experts, convergence = fewer)
       - Contribution balance (avoid dominance)
       - Aspect coverage (select experts who can fill gaps)
    2. All selected experts generate contributions in parallel (asyncio.gather)
    3. Semantic deduplication filters contributions
    4. Round summary generated (Haiku summarization)
    5. Exploration score calculated
    """

    # Get phase and round
    round_number = state.get("round_number", 1)
    current_phase = determine_phase(round_number, state.get("max_rounds", 10))

    # Facilitator selects experts for this round
    selected_experts = await select_experts_for_round(
        state=state,
        phase=current_phase,
        round_number=round_number
    )

    logger.info(f"Round {round_number} ({current_phase}): {len(selected_experts)} experts selected")

    # Generate contributions in parallel
    contributions = await generate_parallel_contributions(
        experts=selected_experts,
        state=state,
        phase=current_phase
    )

    # Semantic deduplication (filter repetitive contributions)
    filtered_contributions = await semantic_deduplication_filter(
        contributions=contributions,
        state=state
    )

    logger.info(f"Semantic filter: {len(contributions)} → {len(filtered_contributions)} contributions")

    # Generate round summary (for memory efficiency)
    round_summary = await generate_round_summary(
        contributions=filtered_contributions,
        round_number=round_number
    )

    # Calculate exploration score
    exploration_score = await calculate_exploration_score(
        contributions=filtered_contributions,
        state=state
    )

    # Update state
    all_contributions = list(state.get("contributions", []))
    all_contributions.extend(filtered_contributions)

    round_summaries = list(state.get("round_summaries", []))
    round_summaries.append(round_summary)

    return {
        "contributions": all_contributions,
        "round_summaries": round_summaries,
        "round_number": round_number + 1,
        "exploration_score": exploration_score,
        "current_node": "parallel_round",
    }
```

**B. Expert Selection Logic**

```python
async def select_experts_for_round(
    state: DeliberationGraphState,
    phase: str,
    round_number: int
) -> list[PersonaProfile]:
    """Select 2-5 experts for this round based on phase and balance.

    Phase-based counts:
    - Exploration (rounds 1-3): 3-5 experts (broad exploration)
    - Challenge (rounds 4-6): 2-3 experts (focused debate)
    - Convergence (rounds 7+): 2-3 experts (synthesis)
    """

    personas = state.get("personas", [])
    contributions = state.get("contributions", [])

    # Count contributions per expert
    contribution_counts = {}
    for contrib in contributions:
        contribution_counts[contrib.persona_code] = contribution_counts.get(contrib.persona_code, 0) + 1

    # Calculate novelty scores per expert (from check_convergence_node)
    expert_novelty_scores = state.get("expert_novelty_scores", {})

    # Phase-specific selection
    if phase == "exploration":
        # Select 3-5 experts, prioritize those who haven't spoken much
        target_count = 4
        candidates = sorted(
            personas,
            key=lambda p: (
                contribution_counts.get(p.code, 0),  # Fewest contributions first
                -expert_novelty_scores.get(p.code, 1.0)  # Higher novelty preferred
            )
        )
        selected = candidates[:target_count]

    elif phase == "challenge":
        # Select 2-3 experts who can challenge assumptions
        target_count = 3

        # Identify experts who disagree (low novelty = repetitive, skip them)
        candidates = [
            p for p in personas
            if expert_novelty_scores.get(p.code, 1.0) > 0.4  # Not repetitive
        ]

        # Prioritize experts who haven't spoken recently
        recent_speakers = [c.persona_code for c in contributions[-3:]]
        candidates = [p for p in candidates if p.code not in recent_speakers]

        selected = candidates[:target_count]

    elif phase == "convergence":
        # Select 2-3 experts representing different viewpoints
        target_count = 3

        # Use all experts if <= 3, otherwise select balanced set
        if len(personas) <= 3:
            selected = personas
        else:
            # Select least-contributing experts to ensure all voices heard
            selected = sorted(
                personas,
                key=lambda p: contribution_counts.get(p.code, 0)
            )[:target_count]

    else:
        # Default: select 3 experts
        selected = personas[:3]

    return selected
```

**C. Parallel Contribution Generation**

```python
async def generate_parallel_contributions(
    experts: list[PersonaProfile],
    state: DeliberationGraphState,
    phase: str
) -> list[ContributionMessage]:
    """Generate contributions from multiple experts in parallel."""

    # Create tasks for all experts
    tasks = []
    for expert in experts:
        task = generate_single_contribution(
            expert=expert,
            state=state,
            phase=phase
        )
        tasks.append(task)

    # Run all in parallel
    contributions = await asyncio.gather(*tasks)

    return contributions


async def generate_single_contribution(
    expert: PersonaProfile,
    state: DeliberationGraphState,
    phase: str
) -> ContributionMessage:
    """Generate contribution from single expert (existing logic from persona_contribute_node)."""

    # This is essentially the existing persona_contribute_node logic
    # but adapted to work with the parallel flow

    from bo1.orchestration.deliberation import DeliberationEngine

    problem = state.get("problem")
    contributions = state.get("contributions", [])
    round_number = state.get("round_number", 1)
    personas = state.get("personas", [])

    participant_list = ", ".join([p.name for p in personas])

    v1_state = graph_state_to_deliberation_state(state)
    engine = DeliberationEngine(state=v1_state)

    # Get phase-specific speaker prompt
    speaker_prompt = get_phase_prompt(phase, round_number)

    contribution_msg, llm_response = await engine._call_persona_async(
        persona_profile=expert,
        problem_statement=problem.description if problem else "",
        problem_context=problem.context if problem else "",
        participant_list=participant_list,
        round_number=round_number,
        contribution_type=ContributionType.RESPONSE,
        previous_contributions=contributions,
        speaker_prompt=speaker_prompt,
    )

    return contribution_msg


def get_phase_prompt(phase: str, round_number: int) -> str:
    """Get phase-specific speaker prompts (from MEETING_FIXES.md)."""

    if phase == "exploration":
        return (
            "EXPLORATION PHASE: Surface new perspectives, risks, and opportunities. "
            "Challenge assumptions. Identify gaps in analysis. "
            "Max 80 tokens. No agreement statements without new information."
        )

    elif phase == "challenge":
        return (
            "CHALLENGE PHASE: Directly challenge a previous point OR provide new evidence. "
            "Must either disagree with a specific claim or add novel data. "
            "Max 80 tokens. No summaries or meta-commentary."
        )

    elif phase == "convergence":
        return (
            "CONVERGENCE PHASE: Provide your strongest recommendation, key risk, and "
            "reason it outweighs alternatives. Be specific. "
            "Max 80 tokens. No further debate."
        )

    else:
        return "Provide your contribution based on your expertise."
```

**Integration Points:**

- **Graph Config**: Replace `persona_contribute` node with `parallel_round` node
- **Facilitator**: Update `facilitator_decide_node` to route to `parallel_round` instead
- **State**: Add `exploration_score`, `expert_novelty_scores` fields

**Success Metrics:**

- Average round time reduced by 40% (fewer serial rounds needed)
- User feedback: "Meetings feel more natural and dynamic"
- Expert participation balance: Gini coefficient < 0.3 (balanced distribution)
- Meeting completion: 3-5 rounds total (vs current 8-12)

**Example Scenario:**

```
Problem: Should we expand to EU markets?
Experts: 5 selected (Market Analyst, Legal, Finance, Ops, Strategy)

Round 1 (Exploration): 4 experts speak
  - Market Analyst: EU demand is strong, UK specifically
  - Legal: GDPR compliance is non-negotiable
  - Finance: $500K budget seems high, pilot first
  - Strategy: Staged approach recommended
  [Semantic dedup: All 4 contributions unique, kept]
  [Exploration score: 0.6/1.0 - missing risks, stakeholder impact]

Round 2 (Challenge): 3 experts speak
  - Ops: Challenges Finance - $500K needed for proper launch, cutting corners risky
  - Legal: Challenges Market Analyst - UK market may not represent EU (Brexit)
  - Finance: Responds with evidence - pilot in UK reduces risk, $150K sufficient
  [Semantic dedup: All 3 contributions unique, kept]
  [Exploration score: 0.75/1.0 - risks now covered]

Round 3 (Convergence): 3 experts speak
  - Market Analyst: Recommend UK pilot, 5-10 customers
  - Finance: Recommend $150K budget with $50K contingency
  - Strategy: Recommend pilot + compliance-first approach
  [Semantic dedup: All 3 contributions unique, kept]
  [Exploration score: 0.85/1.0 - sufficient depth]
  [Convergence detected, move to vote]

Total: 3 rounds, 10 contributions from 5 experts, balanced participation
```

---

### Component 2: Semantic Deduplication (Prevent Repetition)

**Rationale:**

Research shows semantic similarity is more effective than keyword matching for detecting repetition. The current system has no real-time deduplication, causing experts to repeat points.

**Implementation Approach:**

```python
# bo1/graph/quality_metrics.py (NEW FUNCTION)

async def semantic_deduplication_filter(
    contributions: list[ContributionMessage],
    state: DeliberationGraphState,
    similarity_threshold: float = 0.80
) -> list[ContributionMessage]:
    """Filter contributions that are semantically repetitive.

    Uses Voyage AI embeddings to detect if a contribution is too similar
    to previous contributions in this deliberation.

    Args:
        contributions: List of new contributions from this round
        state: Current deliberation state (for history)
        similarity_threshold: Similarity above this = repetitive (default 0.80)

    Returns:
        Filtered list of contributions (only novel ones kept)
    """

    from bo1.llm.embeddings import generate_embedding, cosine_similarity

    # Get all previous contributions
    previous_contributions = state.get("contributions", [])

    # Generate embeddings for previous contributions (cache these!)
    previous_embeddings = []
    for contrib in previous_contributions:
        # Check if embedding already cached in state
        if hasattr(contrib, "embedding") and contrib.embedding:
            previous_embeddings.append(contrib.embedding)
        else:
            # Generate and cache
            embedding = generate_embedding(contrib.content, input_type="document")
            contrib.embedding = embedding  # Cache for future rounds
            previous_embeddings.append(embedding)

    # Filter new contributions
    filtered = []
    for contrib in contributions:
        # Generate embedding for this contribution
        contrib_embedding = generate_embedding(contrib.content, input_type="query")

        # Check similarity to ALL previous contributions
        max_similarity = 0.0
        most_similar_persona = None

        for i, prev_embedding in enumerate(previous_embeddings):
            similarity = cosine_similarity(contrib_embedding, prev_embedding)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_persona = previous_contributions[i].persona_code

        # Keep if sufficiently novel
        if max_similarity < similarity_threshold:
            # Novel contribution - keep it
            contrib.embedding = contrib_embedding  # Cache embedding
            filtered.append(contrib)
            logger.info(
                f"✅ NOVEL: {contrib.persona_code} - max_sim={max_similarity:.3f} "
                f"(vs {most_similar_persona})"
            )
        else:
            # Repetitive contribution - filter out
            logger.warning(
                f"❌ REPETITIVE: {contrib.persona_code} - max_sim={max_similarity:.3f} "
                f"(too similar to {most_similar_persona}). Filtering out."
            )

    return filtered
```

**Thresholds:**

- `similarity > 0.90`: Nearly identical (definitely filter)
- `similarity > 0.80`: Very similar (filter by default)
- `similarity > 0.70`: Somewhat similar (warn expert, but keep)
- `similarity < 0.70`: Novel (keep)

**Integration Points:**

- **parallel_round_node**: Call semantic filter after generating contributions
- **State**: Add `embedding` field to `ContributionMessage` model (cache embeddings)
- **Metrics**: Track deduplication rate (% contributions filtered)

**Success Metrics:**

- Deduplication rate: 5-15% (if higher, prompts need work; if lower, threshold too high)
- Meeting length reduced by 20-30% (fewer repetitive rounds)
- Novelty score maintained above 0.5 throughout meeting

---

### Component 3: Exploration Scoring (Ensure Depth)

**Rationale:**

From MEETING_CODIFICATION.md, exploration score ensures meetings don't converge too early without exploring critical aspects. Current system has no depth check.

**Implementation Approach:**

```python
# bo1/graph/quality_metrics.py (NEW FUNCTION)

async def calculate_exploration_score(
    contributions: list[ContributionMessage],
    state: DeliberationGraphState
) -> float:
    """Calculate exploration score based on aspect coverage.

    Uses LLM judge to assess which critical aspects have been discussed.

    Score calculation:
    - For each aspect: 0 (not mentioned), 0.5 (shallow), 1.0 (deep)
    - Exploration score = average across all aspects

    Returns:
        Float 0-1 (0 = no exploration, 1 = deep exploration of all aspects)
    """

    from bo1.llm.broker import PromptBroker, PromptRequest

    # Define critical aspects (from MEETING_CODIFICATION.md)
    aspects = [
        "problem_clarity",
        "objectives",
        "options_alternatives",
        "risks_failure_modes",
        "constraints",
        "stakeholders_impact",
        "dependencies_unknowns"
    ]

    # Format contributions for judge
    all_contributions = state.get("contributions", [])
    discussion_text = "\n\n".join([
        f"[{c.persona_code}]: {c.content}"
        for c in all_contributions
    ])

    # LLM judge prompt
    system_prompt = """You are a deliberation quality judge. Assess how deeply each critical aspect has been explored.

For each aspect, classify as:
- "none": Not mentioned at all
- "shallow": Mentioned briefly but not analyzed
- "deep": Analyzed with evidence, trade-offs, or examples

Output ONLY valid JSON in this format:
{
  "aspects": {
    "problem_clarity": "deep|shallow|none",
    "objectives": "deep|shallow|none",
    "options_alternatives": "deep|shallow|none",
    "risks_failure_modes": "deep|shallow|none",
    "constraints": "deep|shallow|none",
    "stakeholders_impact": "deep|shallow|none",
    "dependencies_unknowns": "deep|shallow|none"
  },
  "overall_score": 0.0-1.0,
  "missing_critical": ["aspect1", "aspect2"]
}"""

    user_message = f"""Assess this deliberation:

<problem_statement>
{state.get("problem").description if state.get("problem") else "Unknown"}
</problem_statement>

<discussion>
{discussion_text[:3000]}
</discussion>

Analyze how deeply each aspect has been explored. Output JSON only."""

    broker = PromptBroker()
    request = PromptRequest(
        system=system_prompt,
        user_message=user_message,
        prefill="{",
        model="haiku",  # Fast, cheap judge
        temperature=0.3,
        max_tokens=500,
        phase="exploration_scoring",
        agent_type="judge"
    )

    response = await broker.call(request)

    # Parse JSON
    import json
    try:
        result = json.loads("{" + response.content)

        # Calculate score
        aspect_scores = result.get("aspects", {})
        score_map = {"none": 0.0, "shallow": 0.5, "deep": 1.0}

        scores = [score_map.get(aspect_scores.get(aspect, "none"), 0.0) for aspect in aspects]
        exploration_score = sum(scores) / len(scores)

        logger.info(
            f"Exploration score: {exploration_score:.2f} "
            f"(missing: {result.get('missing_critical', [])})"
        )

        return exploration_score

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse exploration score JSON: {e}")
        return 0.5  # Default to medium score on parse failure
```

**Hard Rules:**

From MEETING_CODIFICATION.md:

```python
# bo1/graph/routers.py (UPDATE route_convergence_check)

def route_convergence_check(state: DeliberationGraphState) -> str:
    """Route based on convergence AND exploration score."""

    exploration_score = state.get("exploration_score", 0.0)
    convergence_score = state.get("convergence_score", 0.0)
    round_number = state.get("round_number", 0)

    # Hard rule: Cannot end before min rounds
    if round_number < 3:
        return "facilitator_decide"

    # Hard rule: Cannot end if exploration < 0.60
    if exploration_score < 0.60:
        logger.info(
            f"Exploration too shallow ({exploration_score:.2f} < 0.60). "
            f"Continuing deliberation."
        )
        return "facilitator_decide"

    # Hard rule: Check required aspects
    missing_aspects = state.get("missing_critical_aspects", [])
    if "risks_failure_modes" in missing_aspects or "options_alternatives" in missing_aspects:
        logger.info(
            f"Critical aspects missing: {missing_aspects}. "
            f"Continuing deliberation."
        )
        return "facilitator_decide"

    # Normal convergence check
    if state.get("should_stop", False):
        return "vote"
    else:
        return "facilitator_decide"
```

**Integration Points:**

- **parallel_round_node**: Calculate exploration score after each round
- **route_convergence_check**: Enforce exploration threshold before allowing vote
- **State**: Add `exploration_score`, `missing_critical_aspects` fields

**Success Metrics:**

- No meetings end with exploration_score < 0.60
- Average exploration score at convergence: 0.75+
- User feedback: "Meetings explore all important angles"

---

### Component 4: Focus/Drift Prevention

**Rationale:**

From MEETING_CODIFICATION.md, focus score tracks whether contributions stay on-topic. Current drift detection exists but isn't enforced.

**Implementation Approach:**

```python
# bo1/graph/quality_metrics.py (ENHANCE detect_contribution_drift)

def calculate_focus_score(
    contributions: list[ContributionMessage],
    problem_statement: str
) -> float:
    """Calculate focus score for recent contributions.

    Checks if contributions are:
    - on_topic_core: Directly addresses the problem
    - on_topic_context: Provides relevant background
    - off_topic: Tangents or unrelated

    Returns:
        Float 0-1 representing focus (1 = all on-topic)
    """

    # Check last 6 contributions (2 rounds)
    recent = contributions[-6:] if len(contributions) >= 6 else contributions

    if not recent:
        return 1.0  # No contributions yet, perfect focus

    # Simple heuristic: check for topic drift keywords
    problem_keywords = set(problem_statement.lower().split())

    on_topic_count = 0
    off_topic_count = 0

    for contrib in recent:
        contrib_keywords = set(contrib.content.lower().split())
        overlap = len(problem_keywords & contrib_keywords)

        # High overlap = on-topic
        if overlap >= 5:
            on_topic_count += 1
        elif overlap >= 2:
            on_topic_count += 0.5  # Partial credit for context
        else:
            off_topic_count += 1

    focus_score = on_topic_count / len(recent)

    return focus_score
```

**Enforcement:**

```python
# bo1/graph/nodes.py (UPDATE parallel_round_node)

async def parallel_round_node(state: DeliberationGraphState) -> dict[str, Any]:
    """..."""

    # After generating contributions, check focus
    focus_score = calculate_focus_score(
        contributions=filtered_contributions,
        problem_statement=state.get("problem").description
    )

    # Warn if focus dropping
    if focus_score < 0.60:
        logger.warning(
            f"⚠️ FOCUS DRIFT DETECTED: score={focus_score:.2f}. "
            f"Next round will emphasize refocusing."
        )

        # Set flag for facilitator to refocus
        return {
            # ... normal state updates ...
            "focus_score": focus_score,
            "needs_refocus": True,
        }

    return {
        # ... normal state updates ...
        "focus_score": focus_score,
        "needs_refocus": False,
    }
```

**Facilitator Integration:**

```python
# bo1/agents/facilitator.py (UPDATE decide_next_action)

async def decide_next_action(...):
    """..."""

    # Check if refocus needed
    if state.needs_refocus:
        logger.info("🎯 Refocusing discussion due to drift")

        return (
            FacilitatorDecision(
                action="continue",
                reasoning="Discussion has drifted off-topic. Refocusing on core problem.",
                next_speaker=select_on_topic_expert(state),
                speaker_prompt=(
                    "Bring the discussion back to the core problem. "
                    "What specific aspect of the decision needs resolution?"
                ),
            ),
            None
        )
```

**Integration Points:**

- **parallel_round_node**: Calculate focus score after each round
- **facilitator_decide_node**: Check `needs_refocus` flag and take corrective action
- **State**: Add `focus_score`, `needs_refocus` fields

**Success Metrics:**

- Average focus score: 0.75+
- Drift rate: <10% of rounds trigger refocus
- User feedback: "Meetings stay on track"

---

### Component 5: Expert Rotation & Dominance Prevention

**Rationale:**

With multi-expert-per-round, the rotation rules must change. Instead of "1 expert per round", we need "balanced participation across rounds with novelty enforcement".

**Implementation Approach:**

**Updated Rotation Rules:**

1. **Balance rule**: Over full meeting, each expert contributes 15-25% of total (for 5 experts)
2. **Consecutive limit**: No expert in >50% of consecutive rounds (e.g., not in 3 out of 4 rounds)
3. **Novelty enforcement**: Experts with low novelty (<0.4) are temporarily excluded
4. **Phase coverage**: Ensure all experts contribute at least once per phase (exploration, challenge, convergence)

```python
# bo1/agents/facilitator.py (REPLACE _check_rotation_limits)

def _check_rotation_limits_parallel(
    self,
    state: DeliberationGraphState
) -> dict[str, Any] | None:
    """Check rotation rules for parallel-round system.

    Returns:
        Override info if limits exceeded, None otherwise
    """

    contributions = state.get("contributions", [])
    personas = state.get("personas", [])
    round_number = state.get("round_number", 0)

    if not contributions or not personas:
        return None

    # Count contributions per expert
    contribution_counts = self._count_contributions(contributions)
    total_contributions = len(contributions)

    # Rule 1: Balance - no expert >25% of total (for 5 experts)
    max_allowed = total_contributions * 0.25

    for persona_code, count in contribution_counts.items():
        if count > max_allowed:
            # This expert is dominating
            other_experts = [
                p.code for p in personas
                if contribution_counts.get(p.code, 0) < count * 0.7
            ]

            if other_experts:
                logger.warning(
                    f"BALANCE VIOLATION: {persona_code} has {count}/{total_contributions} "
                    f"contributions ({count/total_contributions:.1%} > 25%). "
                    f"Excluding from next round."
                )

                return {
                    "exclude_experts": [persona_code],
                    "reason": f"Balance enforcement: {persona_code} exceeded 25% threshold"
                }

    # Rule 2: Consecutive limit - expert not in >50% of last 4 rounds
    # With multi-expert-per-round, track which experts participated in each round
    if round_number >= 4:
        round_participation = {}  # {round_number: [expert_codes]}

        for contrib in contributions:
            rn = contrib.round_number
            if rn not in round_participation:
                round_participation[rn] = set()
            round_participation[rn].add(contrib.persona_code)

        # Check last 4 rounds
        recent_rounds = sorted(round_participation.keys())[-4:]

        for persona_code in [p.code for p in personas]:
            participation_count = sum(
                1 for rn in recent_rounds
                if persona_code in round_participation.get(rn, set())
            )

            if participation_count > 2:  # Participated in >50% of last 4 rounds
                logger.warning(
                    f"CONSECUTIVE VIOLATION: {persona_code} participated in "
                    f"{participation_count}/4 recent rounds. Excluding."
                )

                return {
                    "exclude_experts": [persona_code],
                    "reason": f"Consecutive enforcement: {persona_code} too frequent"
                }

    # Rule 3: Novelty enforcement - exclude experts with low novelty
    expert_novelty_scores = state.get("expert_novelty_scores", {})
    low_novelty_experts = [
        code for code, novelty in expert_novelty_scores.items()
        if novelty < 0.4  # Threshold from research
    ]

    if low_novelty_experts:
        logger.warning(
            f"NOVELTY VIOLATION: {low_novelty_experts} have low novelty scores. "
            f"Excluding to force fresh perspectives."
        )

        return {
            "exclude_experts": low_novelty_experts,
            "reason": f"Novelty enforcement: experts repeating themselves"
        }

    return None  # No violations
```

**Integration with Expert Selection:**

```python
# bo1/graph/nodes.py (UPDATE select_experts_for_round)

async def select_experts_for_round(...):
    """..."""

    # Check rotation limits
    from bo1.agents.facilitator import FacilitatorAgent
    facilitator = FacilitatorAgent()

    rotation_override = facilitator._check_rotation_limits_parallel(state)

    exclude_experts = []
    if rotation_override:
        exclude_experts = rotation_override.get("exclude_experts", [])
        logger.info(f"Excluding experts: {exclude_experts} ({rotation_override['reason']})")

    # Filter candidates
    candidates = [p for p in personas if p.code not in exclude_experts]

    # ... rest of selection logic ...
```

**Integration Points:**

- **parallel_round_node**: Use updated rotation logic
- **select_experts_for_round**: Respect exclusions from rotation limits
- **State**: Add `expert_round_participation` tracking

**Success Metrics:**

- Balance: All experts contribute 15-25% (Gini coefficient <0.2)
- Consecutive participation: No expert in >50% of recent rounds
- Novelty maintained: No expert with score <0.4 continues contributing
- User feedback: "All perspectives were heard"

---

### Component 6: Integration with LangGraph

**Current Graph Flow:**

```
decompose → context_collection → select_personas → initial_round →
facilitator_decide → [persona_contribute | moderator | research] →
check_convergence → [loop OR vote] → synthesize → END
```

**New Graph Flow:**

```
decompose → context_collection → select_personas →
parallel_round(exploration) → quality_check →
parallel_round(challenge) → quality_check →
parallel_round(convergence) → quality_check →
vote → synthesize → END
```

**Key Changes:**

1. **Replace single-expert nodes** with `parallel_round` node
2. **Add quality_check node** between rounds (exploration score, focus score, novelty)
3. **Remove facilitator_decide** from the loop (decisions are phase-based, not per-round)

**New Nodes:**

```python
# bo1/graph/config.py (UPDATE)

workflow.add_node("parallel_round", parallel_round_node)
workflow.add_node("quality_check", quality_check_node)

# New edges
workflow.add_edge("select_personas", "parallel_round")  # Start first round
workflow.add_edge("parallel_round", "quality_check")

# Conditional: continue rounds OR vote
workflow.add_conditional_edges(
    "quality_check",
    route_quality_check,
    {
        "parallel_round": "parallel_round",  # Continue if exploration incomplete
        "vote": "vote",  # End if sufficient depth
    }
)
```

**Router Logic:**

```python
# bo1/graph/routers.py (NEW)

def route_quality_check(state: DeliberationGraphState) -> str:
    """Route based on quality metrics (exploration, focus, convergence).

    Rules:
    1. If round < 3: Continue (minimum rounds)
    2. If exploration_score < 0.60: Continue (insufficient depth)
    3. If focus_score < 0.50: Refocus (drift detected)
    4. If convergence_score >= 0.70 AND exploration_score >= 0.70: Vote
    5. If round >= 10: Force vote (hard cap)
    6. Otherwise: Continue
    """

    round_number = state.get("round_number", 0)
    exploration_score = state.get("exploration_score", 0.0)
    focus_score = state.get("focus_score", 1.0)
    convergence_score = state.get("convergence_score", 0.0)

    # Hard cap
    if round_number >= 10:
        logger.info("Hard cap reached (10 rounds). Moving to vote.")
        return "vote"

    # Minimum rounds
    if round_number < 3:
        logger.info(f"Minimum rounds not met ({round_number}/3). Continuing.")
        return "parallel_round"

    # Exploration requirement
    if exploration_score < 0.60:
        logger.info(
            f"Exploration incomplete ({exploration_score:.2f} < 0.60). Continuing."
        )
        return "parallel_round"

    # Focus requirement
    if focus_score < 0.50:
        logger.warning(
            f"Focus drift detected ({focus_score:.2f} < 0.50). Refocusing."
        )
        return "parallel_round"

    # Convergence + exploration both sufficient
    if convergence_score >= 0.70 and exploration_score >= 0.70:
        logger.info(
            f"Meeting complete: exploration={exploration_score:.2f}, "
            f"convergence={convergence_score:.2f}. Moving to vote."
        )
        return "vote"

    # Default: continue
    logger.info(
        f"Continuing: round={round_number}, exploration={exploration_score:.2f}, "
        f"convergence={convergence_score:.2f}"
    )
    return "parallel_round"
```

**State Changes:**

```python
# bo1/graph/state.py (UPDATE DeliberationGraphState)

class DeliberationGraphState(TypedDict, total=False):
    # ... existing fields ...

    # NEW: Quality scoring
    exploration_score: float  # 0-1, aspect coverage
    focus_score: float  # 0-1, on-topic ratio
    convergence_score: float  # 0-1, agreement level
    novelty_score: float  # 0-1, semantic uniqueness

    # NEW: Expert tracking
    expert_novelty_scores: dict[str, float]  # Per-expert novelty
    expert_round_participation: dict[int, list[str]]  # {round: [expert_codes]}

    # NEW: Aspect tracking
    missing_critical_aspects: list[str]  # Which aspects not yet discussed

    # NEW: Phase tracking
    current_phase: str  # "exploration" | "challenge" | "convergence"
```

---

### Implementation Plan

**Phase 1: Core Architecture (Weeks 1-2)**

1. **Week 1: Parallel Round Node**
   - Implement `parallel_round_node` with multi-expert selection
   - Implement `select_experts_for_round` with phase logic
   - Implement `generate_parallel_contributions` using asyncio.gather
   - Update graph config to use new node
   - **Testing**: Verify 3-5 experts contribute per round

2. **Week 2: Semantic Deduplication**
   - Implement `semantic_deduplication_filter` with Voyage AI
   - Add embedding caching to ContributionMessage
   - Integrate with parallel_round_node
   - **Testing**: Verify repetitive contributions filtered (80% similarity)

**Phase 2: Quality Scoring (Weeks 3-4)**

3. **Week 3: Exploration Scoring**
   - Implement `calculate_exploration_score` with LLM judge
   - Add aspect tracking to state
   - Implement hard rules in quality_check router
   - **Testing**: Verify meetings don't end with exploration <0.60

4. **Week 4: Focus & Novelty Scoring**
   - Implement `calculate_focus_score` for drift detection
   - Enhance `check_convergence_node` to track per-expert novelty
   - Update facilitator to handle refocus scenarios
   - **Testing**: Verify drift detected and corrected

**Phase 3: Rotation & Polish (Week 5)**

5. **Week 5: Rotation Rules & Integration**
   - Implement updated rotation limits for parallel system
   - Add expert exclusion logic to selection
   - Full integration testing across all components
   - **Testing**: End-to-end meeting with balanced participation

**Phase 4: Migration (Week 6)**

6. **Week 6: Production Migration**
   - Feature flag: `use_parallel_rounds` (default: false)
   - A/B testing: 20% traffic to new system
   - Monitor metrics: round count, participation balance, exploration scores
   - Gradual rollout: 50% → 80% → 100%

---

### Success Metrics

**Quantitative:**

- **Meeting efficiency**: Average rounds reduced from 8-12 to 3-5 (40-50% reduction)
- **Participation balance**: Gini coefficient <0.25 (equal distribution)
- **Exploration quality**: Average exploration_score at convergence >= 0.75
- **Novelty maintenance**: Average novelty_score throughout meeting >= 0.50
- **Focus maintenance**: Average focus_score >= 0.70
- **Deduplication rate**: 5-15% of contributions filtered as repetitive
- **User completion rate**: 95%+ meetings complete successfully

**Qualitative:**

- User feedback: "Meetings feel like real expert panels"
- User feedback: "All important aspects were explored"
- User feedback: "No repetition or wasted time"
- User feedback: "Natural flow with multiple voices"

---

### Migration Path

**Step 1: Backward Compatibility**

Keep existing single-expert flow available:

```python
# bo1/graph/config.py

def create_deliberation_graph(use_parallel_rounds: bool = False):
    """..."""

    if use_parallel_rounds:
        # New parallel system
        workflow.add_node("parallel_round", parallel_round_node)
        workflow.add_edge("select_personas", "parallel_round")
    else:
        # Legacy serial system
        workflow.add_node("initial_round", initial_round_node)
        workflow.add_edge("select_personas", "initial_round")
```

**Step 2: Feature Flag**

```python
# backend/api/sessions.py

async def create_session(...):
    """..."""

    # Feature flag from environment or user tier
    use_parallel_rounds = os.getenv("ENABLE_PARALLEL_ROUNDS", "false").lower() == "true"

    graph = create_deliberation_graph(use_parallel_rounds=use_parallel_rounds)
```

**Step 3: A/B Testing**

```python
# A/B test: 20% of users get new system
import random

use_parallel_rounds = random.random() < 0.2  # 20% chance
```

**Step 4: Gradual Rollout**

```
Week 1: 0% (dev testing only)
Week 2: 10% (early adopters)
Week 3: 25% (monitoring metrics)
Week 4: 50% (if metrics good)
Week 5: 80% (if metrics good)
Week 6: 100% (full rollout)
```

**Step 5: Deprecate Old System**

After 2 weeks at 100% with stable metrics, remove legacy code.

---

### Testing Approach

**Unit Tests:**

```python
# tests/graph/test_parallel_round.py

async def test_parallel_round_selects_multiple_experts():
    """Verify 2-5 experts selected per round based on phase."""

    state = create_test_state(phase="exploration", round_number=1)

    selected = await select_experts_for_round(
        state=state,
        phase="exploration",
        round_number=1
    )

    assert 3 <= len(selected) <= 5, "Exploration phase should select 3-5 experts"


async def test_semantic_deduplication_filters_repetitive():
    """Verify contributions >80% similar are filtered."""

    contrib1 = ContributionMessage(
        persona_code="expert_a",
        content="We should invest in EU markets due to strong demand."
    )

    contrib2 = ContributionMessage(
        persona_code="expert_b",
        content="We should invest in European markets because of high demand."
        # Very similar to contrib1
    )

    state = create_test_state(contributions=[contrib1])

    filtered = await semantic_deduplication_filter(
        contributions=[contrib2],
        state=state,
        similarity_threshold=0.80
    )

    assert len(filtered) == 0, "Repetitive contribution should be filtered"


async def test_exploration_score_requires_aspects():
    """Verify exploration score checks aspect coverage."""

    # Missing "risks_failure_modes" aspect
    state = create_test_state(
        contributions=[
            ContributionMessage(content="Market is good"),  # objectives
            ContributionMessage(content="We have options A, B, C"),  # options
        ]
    )

    score = await calculate_exploration_score(
        contributions=state["contributions"],
        state=state
    )

    assert score < 0.60, "Missing risks should yield low exploration score"
```

**Integration Tests:**

```python
# tests/integration/test_parallel_meeting_flow.py

async def test_full_parallel_meeting_completes():
    """End-to-end test of parallel-round meeting."""

    # Create session with 5 experts
    state = create_initial_state(
        session_id="test_123",
        problem=Problem(description="Should we expand to EU?"),
        personas=create_test_personas(count=5),
        use_parallel_rounds=True
    )

    # Run graph
    graph = create_deliberation_graph(use_parallel_rounds=True)
    result = await graph.ainvoke(state, config={"thread_id": "test_123"})

    # Verify completion
    assert result["phase"] == DeliberationPhase.COMPLETE

    # Verify efficiency
    assert result["round_number"] <= 5, "Should complete in 5 rounds or less"

    # Verify participation balance
    contribution_counts = count_contributions_per_expert(result["contributions"])
    gini = calculate_gini_coefficient(contribution_counts.values())
    assert gini < 0.25, "Participation should be balanced (Gini <0.25)"

    # Verify exploration quality
    assert result["exploration_score"] >= 0.70, "Should achieve high exploration score"
```

**Performance Tests:**

```python
async def test_parallel_contributions_faster_than_serial():
    """Verify parallel execution is faster."""

    # Serial execution (existing system)
    start_serial = time.time()
    await run_serial_round(experts=5)
    duration_serial = time.time() - start_serial

    # Parallel execution (new system)
    start_parallel = time.time()
    await run_parallel_round(experts=5)
    duration_parallel = time.time() - start_parallel

    # Parallel should be ~5x faster (5 experts in parallel vs serial)
    assert duration_parallel < duration_serial * 0.3, "Parallel should be significantly faster"
```

---

## Conclusion

The boardof.one system has **solid architectural foundations** (LangGraph state machine, Redis checkpointing, SSE streaming) but suffers from a **fundamental flaw in its meeting architecture**: the serial, 1-expert-per-round model creates mathematically impossible rotation rules, unrealistic meeting dynamics, and poor user experience.

**The New Architecture** addresses this by:

1. **Multi-expert-per-round**: 2-5 experts contribute in parallel, creating realistic meeting dynamics
2. **Semantic deduplication**: Voyage AI embeddings prevent repetition in real-time
3. **Exploration scoring**: LLM judge ensures depth before allowing convergence
4. **Focus scoring**: Track on-topic contributions and refocus when drift detected
5. **Updated rotation**: Balance, consecutive limits, and novelty enforcement prevent dominance
6. **Phase structure**: Exploration → Challenge → Convergence creates natural flow

**Benefits:**

- **Efficiency**: Meetings complete in 3-5 rounds (vs 8-12), 40-50% faster
- **Realism**: Multiple voices per round feels like actual expert deliberation
- **Quality**: Depth scoring ensures all critical aspects explored
- **Balance**: Hard limits prevent single expert domination
- **No repetition**: Semantic deduplication filters similar contributions

**Critical Path:**

1. Implement parallel round node with multi-expert selection (Weeks 1-2)
2. Add semantic deduplication and exploration scoring (Weeks 3-4)
3. Update rotation rules and integrate all components (Week 5)
4. A/B test and gradual rollout (Week 6)

**Estimated Total Effort:** 6 weeks with 1 engineer

**Next Steps:**

1. Review architectural redesign with team
2. Prioritize components based on impact
3. Begin Phase 1 implementation (parallel round node)
4. Set up A/B testing infrastructure
5. Monitor metrics during rollout

---

**Document Version:** 2.0
**Author:** Claude (Sonnet 4.5)
**Date:** November 25, 2025
**Status:** Ready for Review - Architectural Redesign Complete
