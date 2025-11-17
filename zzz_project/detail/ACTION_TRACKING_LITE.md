# Board of One - Action Tracking Lite (Linear.app-style)

**Version**: 1.0 (Lite)
**Date**: 2025-01-17
**Status**: Design Ready for Implementation
**Scope**: Minimal viable action tracking with timeline view

---

## Design Philosophy

**Linear.app-lite**: Simple, fast, beautiful action tracking - no bloat.

**Core Principle**: "Show what needs to be done, when it's due, and what's blocking progress."

**What We're NOT Building** (v1):
- ❌ Complex dependencies (e.g., "Action B blocks Action C")
- ❌ Team collaboration (multi-user assignment)
- ❌ Custom statuses/workflows
- ❌ Time tracking (hours spent)
- ❌ Sprint planning / iterations
- ❌ Advanced filtering (labels, custom fields)

**What We ARE Building** (v1):
- ✅ Action extraction from synthesis (AI-powered)
- ✅ Clean list view (Linear-style)
- ✅ Simple Gantt timeline (horizontal bars, date axis)
- ✅ 3 statuses: Todo → In Progress → Done
- ✅ Due dates with visual urgency (overdue = red)
- ✅ Quick status updates (keyboard shortcuts)
- ✅ Progress indicators (3/7 actions complete)

---

## 1. UI Layout

### 1.1 Main View: `/actions`

**Layout** (Desktop):
```
┌─────────────────────────────────────────────────────────────────┐
│ [☰] Actions                                         [+ New]  👤 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┬──────────────────────────────────────┐   │
│  │ List (7)         │ Timeline                             │   │
│  ├──────────────────┼──────────────────────────────────────┤   │
│  │                  │  Jan 15    Jan 22    Jan 29    Feb 5 │   │
│  │ ┌──────────────┐ │  ──────────────────────────────────  │   │
│  │ │ ○ Customer   │ │  ████████░░░░░░░░░░░░░░░░░░░░░░░░   │ (60%)
│  │ │   interviews │ │                                      │   │
│  │ │   Due: Jan 20│ │                                      │   │
│  │ └──────────────┘ │                                      │   │
│  │                  │                                      │   │
│  │ ┌──────────────┐ │                                      │   │
│  │ │ ◐ Landing    │ │          ████████████░░░░░░░░░░░░   │ (50%)
│  │ │   page       │ │                                      │   │
│  │ │   Due: Jan 27│ │                                      │   │
│  │ └──────────────┘ │                                      │   │
│  │                  │                                      │   │
│  │ ┌──────────────┐ │                                      │   │
│  │ │ ● Beta launch│ │                  ░░░░░░░░░░░░░░░░░  │ (0%)
│  │ │   Due: Feb 3 │ │                                      │   │
│  │ └──────────────┘ │                                      │   │
│  │                  │                                      │   │
│  │ Progress: 3/7    │  Today ↓                             │   │
│  └──────────────────┴──────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Elements**:
- **Split view**: List (left) + Timeline (right)
- **Status icons**: ○ (Todo), ◐ (In Progress), ● (Done)
- **Timeline bars**: Horizontal bars showing date range
- **Progress shading**: Filled portion shows % complete
- **"Today" marker**: Vertical line on timeline
- **Toggle views**: Switch between List-only, Timeline-only, or Split

---

## 2. Data Model

### 2.1 Action Schema

```typescript
interface Action {
  id: string;
  deliberation_id: string;  // Link to parent deliberation

  // Core fields
  title: string;             // "Conduct customer interviews"
  description?: string;      // Optional details
  status: 'todo' | 'in_progress' | 'done';

  // Dates
  created_at: Date;
  start_date?: Date;         // When to start (optional, defaults to today)
  due_date: Date;            // Deadline
  completed_at?: Date;       // When marked done

  // Progress
  progress_percent?: number; // 0-100 (optional, user updates manually)

  // Context
  success_criteria?: string; // "20 interviews completed"
  order_index: number;       // For manual reordering
}
```

### 2.2 Database Table

```sql
CREATE TABLE actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deliberation_id UUID REFERENCES sessions(id) ON DELETE CASCADE,

  title TEXT NOT NULL,
  description TEXT,
  status TEXT CHECK (status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',

  created_at TIMESTAMP DEFAULT NOW(),
  start_date DATE,
  due_date DATE NOT NULL,
  completed_at TIMESTAMP,

  progress_percent INT CHECK (progress_percent BETWEEN 0 AND 100),
  success_criteria TEXT,
  order_index INT DEFAULT 0,

  user_id UUID REFERENCES users(id),

  CONSTRAINT actions_deliberation_fkey FOREIGN KEY (deliberation_id)
    REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_actions_deliberation ON actions(deliberation_id);
CREATE INDEX idx_actions_user ON actions(user_id);
CREATE INDEX idx_actions_status ON actions(status);
CREATE INDEX idx_actions_due_date ON actions(due_date);
```

---

## 3. UI Components

### 3.1 Action List Item

**Anatomy**:
```
┌────────────────────────────────────────┐
│ ○  Customer interviews                 │
│    Due: Jan 20 (5 days) · Todo         │
│    ✓ 20 interviews completed           │ (success criteria)
│    ────────────────────────────────    │
│    60% ████████████░░░░░░░░░░          │ (progress bar)
└────────────────────────────────────────┘
```

**Props** (Svelte component):
```typescript
// src/lib/components/ActionItem.svelte
export let action: Action;
export let onStatusChange: (id: string, status: Status) => void;
export let onProgressUpdate: (id: string, percent: number) => void;
```

**Interactions**:
- Click status icon → Cycle through: ○ → ◐ → ●
- Click anywhere else → Open detail view (drawer)
- Keyboard: `Space` to toggle status, `Enter` to open details

**Visual States**:
```css
/* Status colors */
.status-todo { color: #9ca3af; }        /* Gray */
.status-in-progress { color: #3b82f6; } /* Blue */
.status-done { color: #10b981; }        /* Green */

/* Urgency colors (due date) */
.due-normal { color: #6b7280; }         /* Gray (>3 days) */
.due-soon { color: #f59e0b; }           /* Amber (1-3 days) */
.due-overdue { color: #ef4444; }        /* Red (past due) */
```

---

### 3.2 Gantt Timeline

**Anatomy**:
```
┌────────────────────────────────────────────────────────────┐
│  Jan 15    Jan 22    Jan 29    Feb 5    Feb 12    Feb 19  │
│  ───────────────────────────────────────────────────────   │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░        │ (Action 1)
│            ████████████████░░░░░░░░░░░░░░░░░░░░░░          │ (Action 2)
│                        ░░░░░░░░░░░░░░░░░░░░░░              │ (Action 3)
│                                                            │
│  Today ↓                                                   │
└────────────────────────────────────────────────────────────┘
```

**Implementation** (Canvas-based or SVG):

**Option 1: Pure CSS** (Simpler, less flexible):
```svelte
<div class="gantt-timeline">
  <div class="gantt-header">
    {#each weeks as week}
      <div class="week-label">{formatWeek(week)}</div>
    {/each}
  </div>

  <div class="gantt-rows">
    {#each actions as action}
      <div class="gantt-bar" style="
        left: {calculateLeftPercent(action.start_date)}%;
        width: {calculateWidthPercent(action.start_date, action.due_date)}%;
        background: linear-gradient(to right,
          #3b82f6 0%,
          #3b82f6 {action.progress_percent}%,
          #e5e7eb {action.progress_percent}%,
          #e5e7eb 100%);
      ">
        <span class="gantt-label">{action.title}</span>
      </div>
    {/each}

    <!-- Today marker -->
    <div class="today-line" style="left: {todayPercent}%"></div>
  </div>
</div>
```

**Option 2: SvelteKit + D3.js** (More powerful, interactive):
```svelte
<script>
  import * as d3 from 'd3';
  import { onMount } from 'svelte';

  export let actions: Action[];

  let svgElement: SVGSVGElement;

  onMount(() => {
    const svg = d3.select(svgElement);
    const width = svgElement.clientWidth;
    const height = actions.length * 40;

    // Time scale
    const xScale = d3.scaleTime()
      .domain([minDate, maxDate])
      .range([0, width]);

    // Draw bars
    svg.selectAll('rect')
      .data(actions)
      .join('rect')
      .attr('x', d => xScale(d.start_date || d.created_at))
      .attr('y', (d, i) => i * 40)
      .attr('width', d => xScale(d.due_date) - xScale(d.start_date || d.created_at))
      .attr('height', 30)
      .attr('fill', d => statusColor(d.status))
      .attr('opacity', d => d.progress_percent / 100);
  });
</script>

<svg bind:this={svgElement} width="100%" height={actions.length * 40}></svg>
```

**Recommendation**: Start with **CSS-based** (faster to implement), migrate to D3.js if needed for interactivity (drag-to-reschedule, zoom, etc.).

---

### 3.3 Action Extraction (After Synthesis)

**UI Flow**:
```svelte
<!-- src/routes/sessions/[id]/synthesis/+page.svelte -->

<section class="synthesis-report">
  <!-- Synthesis markdown content -->
  <div class="synthesis-content">
    {@html synthesisHtml}
  </div>

  <!-- Action extraction (NEW) -->
  <section class="action-extraction">
    <h2>📋 Next Steps → Actions</h2>
    <p>We've extracted actionable items from the synthesis. Review and adjust:</p>

    <div class="proposed-actions">
      {#each proposedActions as action, i}
        <div class="action-draft">
          <input
            type="checkbox"
            bind:checked={action.include}
            id="action-{i}"
          />
          <label for="action-{i}">
            <input
              type="text"
              bind:value={action.title}
              placeholder="Action title"
              class="action-title-input"
            />

            <div class="action-meta">
              <label>
                Due:
                <input type="date" bind:value={action.due_date} />
              </label>

              <label>
                Success:
                <input
                  type="text"
                  bind:value={action.success_criteria}
                  placeholder="How will you know it's done?"
                />
              </label>
            </div>
          </label>

          <button class="btn-icon" on:click={() => removeAction(i)}>×</button>
        </div>
      {/each}
    </div>

    <div class="action-footer">
      <button class="btn-secondary" on:click={addAction}>
        + Add Action
      </button>

      <button
        class="btn-primary"
        on:click={saveActions}
        disabled={!hasSelectedActions}
      >
        Save {selectedCount} Actions →
      </button>
    </div>
  </section>
</section>
```

**AI Extraction Prompt** (Backend):
```python
# bo1/agents/action_extractor.py

ACTION_EXTRACTION_SYSTEM_PROMPT = """
You are an expert at extracting actionable next steps from strategic recommendations.

Given a synthesis report, extract 3-10 concrete actions the user should take.

For each action:
- Title: Clear, specific, action-oriented (start with verb)
- Due date: Suggest realistic deadline (relative to today)
- Success criteria: Observable outcome (how to know it's done)

Output as JSON array:
[
  {
    "title": "Conduct 20 customer interviews",
    "due_date_offset_days": 14,  // 2 weeks from now
    "success_criteria": "20 interviews completed, insights documented"
  },
  ...
]

RULES:
- Each action must be specific (not vague like "research more")
- Deadlines should be realistic (don't suggest 1 day for complex tasks)
- Success criteria must be measurable/observable
- Max 10 actions (focus on high-impact items)
"""

async def extract_actions(synthesis_report: str) -> list[Action]:
    """Extract actions from synthesis using Claude."""
    response = await anthropic_client.messages.create(
        model="claude-sonnet-4.5",
        max_tokens=2000,
        temperature=0.3,
        system=ACTION_EXTRACTION_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"<synthesis_report>\n{synthesis_report}\n</synthesis_report>"
        }]
    )

    # Parse JSON response
    actions_json = json.loads(response.content[0].text)

    # Convert to Action objects
    return [
        Action(
            title=a["title"],
            due_date=datetime.now() + timedelta(days=a["due_date_offset_days"]),
            success_criteria=a["success_criteria"],
            status="todo"
        )
        for a in actions_json
    ]
```

---

## 4. API Endpoints

### 4.1 Action CRUD

```python
# backend/api/actions.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])

class ActionCreate(BaseModel):
    deliberation_id: str
    title: str
    description: str | None = None
    start_date: date | None = None
    due_date: date
    success_criteria: str | None = None

class ActionUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    progress_percent: int | None = None
    due_date: date | None = None
    success_criteria: str | None = None

@router.post("/")
async def create_action(action: ActionCreate, user_id: str = Depends(get_current_user)):
    """Create a new action."""
    # Insert into database
    action_id = await db.insert_action(action, user_id)
    return {"id": action_id, "status": "created"}

@router.get("/")
async def list_actions(
    deliberation_id: str | None = None,
    status: str | None = None,
    user_id: str = Depends(get_current_user)
):
    """List all actions for current user."""
    actions = await db.list_actions(
        user_id=user_id,
        deliberation_id=deliberation_id,
        status=status
    )
    return {"actions": actions}

@router.patch("/{action_id}")
async def update_action(
    action_id: str,
    update: ActionUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update action (status, progress, etc.)."""
    # Verify ownership
    action = await db.get_action(action_id)
    if action.user_id != user_id:
        raise HTTPException(403, "Not authorized")

    # Update
    await db.update_action(action_id, update)

    # If status changed to 'done', set completed_at
    if update.status == 'done':
        await db.mark_action_completed(action_id)

    return {"status": "updated"}

@router.delete("/{action_id}")
async def delete_action(action_id: str, user_id: str = Depends(get_current_user)):
    """Delete action."""
    action = await db.get_action(action_id)
    if action.user_id != user_id:
        raise HTTPException(403, "Not authorized")

    await db.delete_action(action_id)
    return {"status": "deleted"}
```

### 4.2 Action Extraction (AI)

```python
@router.post("/extract")
async def extract_actions_from_synthesis(
    deliberation_id: str,
    user_id: str = Depends(get_current_user)
):
    """Extract actions from synthesis report using AI."""
    # Get synthesis report
    session = await db.get_session(deliberation_id)
    if not session.synthesis:
        raise HTTPException(400, "Synthesis not yet generated")

    # Extract actions
    from bo1.agents.action_extractor import extract_actions
    actions = await extract_actions(session.synthesis)

    return {"actions": [a.dict() for a in actions]}
```

---

## 5. Keyboard Shortcuts (Linear-style)

```typescript
// src/lib/shortcuts.ts

const SHORTCUTS = {
  // Status updates
  't': () => setStatus('todo'),
  'i': () => setStatus('in_progress'),
  'd': () => setStatus('done'),

  // Navigation
  'j': () => selectNext(),
  'k': () => selectPrevious(),
  'Enter': () => openDetails(),
  'Escape': () => closeDetails(),

  // Quick actions
  'c': () => openCreateAction(),
  'e': () => editSelected(),
  '/': () => focusSearch(),
};
```

**Usage**:
- Select action with `j/k` (Vim-style)
- Press `i` to mark "In Progress"
- Press `d` to mark "Done"
- Press `Enter` to open details

---

## 6. Implementation Checklist

### Phase 1: Basic Actions (Week 1-2)
- [ ] Database schema (actions table)
- [ ] API endpoints (CRUD)
- [ ] Action list view (simple table)
- [ ] Status toggle (Todo/In Progress/Done)
- [ ] Due date with urgency colors

### Phase 2: Timeline View (Week 2-3)
- [ ] CSS-based Gantt chart
- [ ] Date axis (weeks/months)
- [ ] Horizontal bars for actions
- [ ] "Today" marker line
- [ ] Progress shading (0-100%)

### Phase 3: AI Extraction (Week 3-4)
- [ ] Action extraction prompt
- [ ] Integration after synthesis
- [ ] Review/edit UI for proposed actions
- [ ] Bulk save to database

### Phase 4: Polish (Week 4)
- [ ] Keyboard shortcuts
- [ ] Quick status updates
- [ ] Drag-to-reorder (list view)
- [ ] Mobile responsive

---

## 7. Visual Design

### 7.1 Color Palette

```css
:root {
  /* Status colors */
  --status-todo: #9ca3af;        /* Gray */
  --status-in-progress: #3b82f6; /* Blue */
  --status-done: #10b981;        /* Green */

  /* Urgency colors */
  --due-normal: #6b7280;         /* Gray */
  --due-soon: #f59e0b;           /* Amber */
  --due-overdue: #ef4444;        /* Red */

  /* Timeline */
  --gantt-bar-fill: #3b82f6;     /* Blue */
  --gantt-bar-empty: #e5e7eb;    /* Light gray */
  --gantt-today-line: #ef4444;   /* Red */
}
```

### 7.2 Typography

```css
.action-title {
  font-size: 0.875rem;     /* 14px */
  font-weight: 500;        /* Medium */
  color: #111827;          /* Almost black */
}

.action-meta {
  font-size: 0.75rem;      /* 12px */
  color: #6b7280;          /* Gray */
}

.gantt-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: white;
}
```

---

## 8. Example Usage

### After Deliberation:
1. User completes synthesis review
2. System extracts 5 actions from "Next Steps" section
3. User reviews, edits deadlines, adds 2 more manual actions
4. Clicks "Save 7 Actions"
5. Redirected to `/actions` view

### Daily Usage:
1. User opens `/actions`
2. Sees 3 overdue actions (red), 2 due soon (amber)
3. Marks "Customer interviews" as In Progress (click icon or press `i`)
4. Updates progress to 60% (slider)
5. Timeline view shows visual progress

### Weekly Review:
1. Filter by "this week" due dates
2. See 5/7 actions completed (progress indicator)
3. Identify blocker on landing page action
4. Update due date to next week

---

## 9. Future Enhancements (v2+)

**Not for MVP, but nice to have later:**
- [ ] Dependencies (Action B requires Action A)
- [ ] Recurring actions ("Weekly standup")
- [ ] Subtasks (break action into smaller steps)
- [ ] Attachments (link files, screenshots)
- [ ] Comments/notes (log progress updates)
- [ ] Email reminders (3 days, 1 day, overdue)
- [ ] Slack integration (notifications)
- [ ] Drag-to-reschedule on Gantt chart
- [ ] Zoom timeline (day/week/month/quarter view)
- [ ] Templates ("Product launch checklist")

---

## 10. Success Metrics

**Engagement**:
- **Action creation rate**: >80% of deliberations create actions
- **Action completion rate**: >60% of actions marked done within deadline
- **Weekly active usage**: >30% of users check actions weekly

**Quality**:
- **AI extraction accuracy**: >90% of extracted actions require no edits
- **Due date accuracy**: >70% of actions completed on or before due date

**Retention**:
- **30-day retention**: Users with actions are 2x more likely to return vs. those without

---

**END OF DOCUMENT**

This is a **Linear.app-lite** design - simple, fast, and focused on core action tracking with a clean timeline view. No bloat, just what you need to track what matters.
