# Progressive Disclosure UX: Technical Specification

**Purpose**: Solve the "blank screen problem" during 5-15 minute deliberations
**Implementation**: Week 6-7 (Web API + UI)
**Priority**: CRITICAL (40% user churn without this)

---

## Problem Statement

**Current UX Failure**:
- Deliberations take 5-15 minutes to complete
- Users see: Blank screen or static spinner
- Users think: "Is it broken? Should I refresh?"
- Result: 40% abandon on first session

**Root Cause**: No feedback loop during long-running graph execution

---

## Solution: Three-Part Progressive Disclosure

1. **Micro-stages**: User-friendly narrative (NOT graph nodes)
2. **Staggered reveals**: Advisors appear one-by-one (NOT bulk dump)
3. **Background mode**: Optional "ping me when done"

**Principle**: People don't mind waiting if they feel progress.

---

## 1. Micro-Stage System

### Stage Mapping (Graph → User-Friendly)

| Graph Node(s) | Visible Stage | Duration | Message |
|---------------|---------------|----------|---------|
| `decompose` | `framing_problem` | 30s | "Breaking your question into focus areas..." |
| `select_personas` | `gathering_perspectives` | 20s | "Assembling expert advisory panel..." |
| `initial_round` | `gathering_perspectives` | 60s | "Experts reviewing your question..." |
| `facilitator_decide` | `analyzing_tensions` | 15s | "Identifying key tensions..." |
| `persona_contribute` | `analyzing_tensions` | 45s | "Advisors refining positions..." |
| `check_convergence` | `aligning_insights` | 10s | "Checking for consensus..." |
| `vote` | `aligning_insights` | 20s | "Finalizing recommendations..." |
| `synthesize` | `preparing_recommendations` | 45s | "Drafting final report..." |

### Backend Implementation

```python
# backend/api/events.py

def map_node_to_visible_stage(node_name: str) -> dict:
    """Map graph node to user-friendly stage (HIDE IMPLEMENTATION DETAILS)."""
    stage_map = {
        "decompose": {
            "stage": "framing_problem",
            "duration_est": 30,
            "message": "Breaking your question into focus areas...",
        },
        "select_personas": {
            "stage": "gathering_perspectives",
            "duration_est": 20,
            "message": "Assembling expert advisory panel...",
        },
        # ... (full mapping above)
    }
    return stage_map.get(node_name, {
        "stage": "processing",
        "duration_est": 30,
        "message": "Processing...",
    })

def emit_stage_transition_event(node_name: str):
    """Emit user-facing stage transition event."""
    stage_data = map_node_to_visible_stage(node_name)
    return {
        "type": "stage_transition",
        "data": {
            "stage": stage_data["stage"],
            "message": stage_data["message"],
            "duration_est": stage_data["duration_est"],
            "timestamp": datetime.now().isoformat(),
        }
    }
```

### Frontend Implementation

```svelte
<!-- frontend/src/lib/components/StageProgress.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';

  export let stage: string;
  export let message: string;
  export let durationEst: number;

  let progress = 0;
  let interval: number;

  onMount(() => {
    // Animate progress bar over estimated duration
    const increment = 100 / (durationEst * 10); // Update every 100ms
    interval = setInterval(() => {
      if (progress < 95) { // Never reach 100% until actual completion
        progress += increment;
      }
    }, 100);

    return () => clearInterval(interval);
  });

  $: if (stage) {
    progress = 0; // Reset on stage change
  }
</script>

<div class="stage-progress">
  <h3>{message}</h3>
  <div class="progress-bar">
    <div class="progress-fill" style="width: {progress}%"></div>
  </div>
  <p class="stage-label">{stage.replace('_', ' ')}</p>
</div>
```

---

## 2. Staggered Advisor Reveals

### Problem: Bulk Dump

**Bad UX**: 5 advisors execute in parallel → all complete at once → bulk dump of contributions

### Solution: Staggered Typing Indicators

**Good UX**: Advisors appear one-by-one every 45-90 seconds

### Backend Implementation (Natural Pacing)

**Strategy**: Execute in parallel, stream as they complete, pace reveals to maintain activity.

```python
# bo1/graph/nodes.py - initial_round_node()

async def initial_round_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """
    Initial round with natural pacing.

    Experts called in parallel (fastest execution), but contributions
    revealed with minimum spacing to avoid bulk dumps.

    Expected timing:
    - Haiku calls: ~5s each
    - 5 experts in parallel: ~5s total (not 25s sequential)
    - Natural variance creates staggered arrival
    - Minimum 3-5s spacing between reveals (if multiple arrive simultaneously)
    """
    personas = state["personas"]

    # Execute all personas in parallel
    tasks = [call_persona(p, state) for p in personas]

    # Process contributions as they complete (natural ordering)
    last_reveal_time = time.time()
    min_spacing = 3  # Minimum seconds between reveals (configurable)

    for task in asyncio.as_completed(tasks):
        contribution = await task

        # Emit typing indicator when we start processing
        yield {
            "type": "advisor_typing",
            "data": {
                "persona_code": contribution.persona_code,
                "persona_name": contribution.persona_name,
            }
        }

        # If previous reveal was recent, add small delay to pace reveals
        time_since_last = time.time() - last_reveal_time
        if time_since_last < min_spacing:
            await asyncio.sleep(min_spacing - time_since_last)

        # Emit contribution (ready to display)
        yield {
            "type": "advisor_complete",
            "data": contribution.dict(),
        }

        last_reveal_time = time.time()

    return {"contributions": contributions}
```

**Why This Works**:
1. **Natural variance**: Haiku calls have ~5s avg, but range 3-8s → natural stagger
2. **Minimum spacing**: If 2+ complete simultaneously, space them 3-5s apart
3. **No fake delays**: Contributions arrive as fast as possible, just not dumped in bulk
4. **Configurable pacing**: `min_spacing` can be tuned based on user feedback

**Example Timeline** (5 experts, Haiku ~5s avg):
```
0s: All 5 calls start in parallel
4s: Maria completes (fast) → emit immediately
5s: Zara completes → emit immediately (1s after Maria, natural)
7s: Tariq completes → emit immediately (2s after Zara)
8s: Chen + Aria both complete → emit Chen immediately, Aria after 3s delay
11s: Aria emitted (3s spacing from Chen)
```

**Result**: User sees activity every 1-3 seconds (no bulk dump, no long gaps)

**Configuration Options** (for different scenarios):

```python
# bo1/graph/config.py

# Initial round: Tight spacing (maintain activity feel)
INITIAL_ROUND_MIN_SPACING = 3  # seconds

# Later rounds: Looser spacing (fewer experts, can space more)
LATER_ROUND_MIN_SPACING = 5  # seconds

# Can also vary by model speed:
# - Haiku: 3s spacing (fast responses)
# - Sonnet: 5s spacing (slower, more thoughtful)
```

**Multi-Round Handling**:
- Round 1 (5 experts in parallel): Natural stagger + 3s minimum spacing
- Round 2 (1 expert sequential): Emit immediately (no spacing needed)
- Round 3 (1 expert sequential): Emit immediately
- This maintains consistent activity throughout deliberation

### Frontend Implementation

```svelte
<!-- frontend/src/lib/components/ContributionFeed.svelte -->
<script lang="ts">
  import { sseStore } from '$lib/stores/sse';
  import AdvisorTypingIndicator from './AdvisorTypingIndicator.svelte';
  import ContributionCard from './ContributionCard.svelte';

  $: advisors = $sseStore.advisors;
  // Array of {code, name, status: "typing" | "complete", contribution}
</script>

<div class="contribution-feed">
  {#each advisors as advisor}
    {#if advisor.status === "typing"}
      <AdvisorTypingIndicator name={advisor.name} />
    {:else if advisor.status === "complete"}
      <ContributionCard contribution={advisor.contribution} />
    {/if}
  {/each}
</div>
```

---

## 3. Early Partial Outputs

**Strategy**: Show safe outputs IMMEDIATELY (don't wait for full deliberation)

### Examples

**1. Problem Decomposition** (after `decompose_node`):
```python
# bo1/graph/nodes.py
def decompose_node(state: DeliberationGraphState) -> DeliberationGraphState:
    sub_problems = decompose_problem(state["problem"])

    # Emit early partial output
    yield {
        "type": "decomposition_ready",
        "data": {
            "sub_problems": [sp.dict() for sp in sub_problems],
            "message": f"We've broken this into {len(sub_problems)} focus areas",
        }
    }

    return {"sub_problems": sub_problems}
```

**2. Advisory Panel** (after `select_personas`):
```svelte
<!-- Show immediately -->
{#if advisorPanel}
  <div class="advisor-panel">
    <h3>Your Advisory Board:</h3>
    <div class="avatars">
      {#each advisorPanel as advisor}
        <Avatar name={advisor.name} expertise={advisor.expertise} />
      {/each}
    </div>
  </div>
{/if}
```

**3. Facilitator Reflections** (after each round):
```svelte
{#if facilitatorSummary}
  <InsightCard type="facilitator">
    <p>{facilitatorSummary}</p>
  </InsightCard>
{/if}
```

---

## 4. Background Mode (Optional)

### User Flow

1. User submits problem → deliberation starts
2. Micro-stages begin showing progress
3. User clicks "Continue in Background"
4. SSE disconnects, user can close tab
5. 8 minutes later: Browser notification fires
6. User returns, sees full results

### Frontend Implementation

```svelte
<!-- frontend/src/routes/(app)/sessions/[id]/+page.svelte -->
<script lang="ts">
  import { sseStore } from '$lib/stores/sse';

  let backgroundMode = false;

  function enableBackgroundMode() {
    backgroundMode = true;
    sseStore.disconnect(); // Save server resources

    // Register service worker for notifications
    if ('Notification' in window && Notification.permission === 'granted') {
      navigator.serviceWorker.ready.then(registration => {
        registration.active.postMessage({
          type: 'watch_session',
          session_id: sessionId,
        });
      });
    }
  }
</script>

{#if !backgroundMode}
  <button on:click={enableBackgroundMode} class="background-btn">
    <Icon name="bell" />
    We'll ping you when ready (5-10 min)
  </button>
{:else}
  <div class="background-notice">
    <Icon name="clock" />
    <p>Deliberation running in background. We'll notify you when complete.</p>
  </div>
{/if}
```

### Service Worker Implementation

```typescript
// frontend/src/service-worker.ts

self.addEventListener('message', (event) => {
  if (event.data.type === 'watch_session') {
    const sessionId = event.data.session_id;

    // Poll API every 30s for session status
    const interval = setInterval(async () => {
      const response = await fetch(`/api/v1/sessions/${sessionId}`);
      const session = await response.json();

      if (session.status === 'completed') {
        clearInterval(interval);

        // Send browser notification
        self.registration.showNotification('Deliberation Complete', {
          body: 'Your Board of One session is ready to review.',
          icon: '/icon-192.png',
          badge: '/badge-72.png',
          tag: `session-${sessionId}`,
          requireInteraction: true,
          actions: [
            { action: 'view', title: 'View Results' },
            { action: 'dismiss', title: 'Dismiss' },
          ],
        });
      }
    }, 30000); // Poll every 30s
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view') {
    const sessionId = event.notification.tag.replace('session-', '');
    event.waitUntil(
      clients.openWindow(`/sessions/${sessionId}`)
    );
  }
});
```

---

## 5. Testing Requirements

### Unit Tests

```python
# tests/ui/test_progressive_disclosure.py

def test_map_node_to_visible_stage():
    """Graph nodes map to user-friendly stages (NOT raw node names)."""
    result = map_node_to_visible_stage("decompose")
    assert result["stage"] == "framing_problem"
    assert "decompose" not in result["message"].lower()

def test_staggered_delays():
    """Advisors revealed with 45-90s stagger."""
    delays = []
    for i in range(5):
        if i > 0:
            delay = calculate_stagger_delay(i)
            assert 45 <= delay <= 90
            delays.append(delay)

    # Verify total spread
    assert sum(delays) >= 180  # At least 3 minutes total
```

### Integration Tests

```python
# tests/integration/test_progressive_ux_flow.py

async def test_user_sees_updates_every_30_seconds():
    """User should see UI update at least every 30 seconds."""
    events = []

    async for event in stream_deliberation(session_id):
        events.append(event)

    # Check max time between events
    timestamps = [e["timestamp"] for e in events]
    max_gap = max([t2 - t1 for t1, t2 in zip(timestamps, timestamps[1:])])

    assert max_gap < 30, f"User saw gap of {max_gap}s without updates"
```

### E2E Tests

```typescript
// tests/e2e/test_blank_screen.spec.ts

test('user never sees blank screen during 10-min deliberation', async ({ page }) => {
  await page.goto('/sessions/new');
  await page.fill('textarea', 'Should I invest $50K in SEO or paid ads?');
  await page.click('button[type="submit"]');

  // Monitor UI updates for 10 minutes
  const updates: number[] = [];
  const startTime = Date.now();

  while (Date.now() - startTime < 600000) { // 10 min
    await page.waitForSelector('.stage-progress', { timeout: 30000 });
    updates.push(Date.now() - startTime);
  }

  // Verify: UI updated at least every 30 seconds
  const gaps = updates.map((t, i) => i > 0 ? t - updates[i-1] : 0);
  expect(Math.max(...gaps)).toBeLessThan(30000);
});
```

---

## 6. Success Criteria

- [ ] User sees UI update at least every 30 seconds
- [ ] No static spinners visible >2 minutes
- [ ] Stage transitions smooth (animated)
- [ ] Advisor typing indicators appear before contributions
- [ ] Background mode notification fires correctly
- [ ] Session completion rate >85% (vs. <60% without progressive disclosure)

---

**Implementation Timeline**: Week 6, Day 46.5 (new day inserted into roadmap)

**Dependencies**:
- SSE streaming (Day 45-46)
- Event filtering (hide internal events)
- Service worker setup (for background notifications)

**Deliverables**:
- `backend/api/events.py` - Stage mapping + event filtering
- `frontend/src/lib/components/StageProgress.svelte`
- `frontend/src/lib/components/AdvisorTypingIndicator.svelte`
- `frontend/src/service-worker.ts` - Background notifications

---

**END OF SPECIFICATION**
