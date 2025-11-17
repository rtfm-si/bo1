# Board of One - Action Tracking & Accountability Feature
**Post-Deliberation Success System**

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Feature Design (Major Feature)
**Priority**: Phase 2-3 (Post-MVP Core Feature)

---

## Table of Contents

1. [Feature Overview](#1-feature-overview)
2. [User Journey](#2-user-journey)
3. [Tier-Specific Features](#3-tier-specific-features)
4. [Action Model & States](#4-action-model--states)
5. [UI Components](#5-ui-components)
6. [Reminders & Notifications](#6-reminders--notifications)
7. [Progress Reporting](#7-progress-reporting)
8. [Replanning & Adaptation](#8-replanning--adaptation)
9. [Database Schema](#9-database-schema)
10. [Implementation Phases](#10-implementation-phases)

---

## 1. Feature Overview

### 1.1 Vision

**Problem**: Traditional advisory tools give recommendations, then disappear. Users are left alone to execute, often failing due to:
- No accountability ("I'll do it later" → never happens)
- No progress tracking (forgotten commitments)
- No adaptation (context changes, plan becomes stale)

**Solution**: Board of One doesn't just deliberate—it helps users **achieve success**.

**Core Principle**: "We don't just tell you what to do, we help you do it."

### 1.2 Key Features

**Action Extraction** (Post-Deliberation):
- AI extracts actionable next steps from synthesis report
- User reviews, edits, and confirms actions
- Each action has: Description, deadline, success criteria

**Progress Tracking**:
- Mark actions as: Not Started, In Progress, Completed, Blocked
- Track completion dates vs deadlines (on-time vs overdue)
- Visualize progress (5 actions: 2 completed, 2 in progress, 1 blocked)

**Reminders & Nudges**:
- Email reminders for upcoming deadlines (3 days, 1 day, overdue)
- In-app notifications for Pro users
- Weekly digest: "You have 3 overdue actions from your pricing strategy deliberation"

**Replanning** (When Things Change):
- User marks action as "Blocked" → Trigger replanning deliberation
- "Situation has changed, need to adjust plan" → New deliberation with context
- Update existing actions or create new deliberation

**Progress Reports**:
- Monthly summary: "You completed 12/15 actions this month (80%)"
- Insights: "Your avg completion time: 7 days (target: 5 days)"
- Accountability: "You're falling behind on pricing strategy actions"

### 1.3 Differentiation

**vs Notion/Todoist** (Task managers):
- Bo1 actions are tied to deliberations (context-aware)
- Replanning triggers new deliberation (adaptive, not static)
- Success criteria are expert-validated (not just user-defined)

**vs Generic AI Advice** (ChatGPT, etc.):
- ChatGPT gives advice, Bo1 ensures execution
- Deliberation → Actions → Tracking → Replanning (full loop)
- Accountability built-in (can't ignore overdue actions)

**Value Prop**: "The only AI decision tool that helps you achieve your goals, not just advise you."

---

## 2. User Journey

### 2.1 End of Deliberation (Action Extraction)

**After synthesis report is generated**:

1. **AI Extracts Actions** (Automatic):
   - Parse synthesis report's "Next Steps" section
   - Extract 3-10 actionable items
   - Suggest deadlines based on urgency/dependencies
   - Add success criteria (how to know it's done)

2. **User Reviews Actions** (Interactive):
   - See proposed actions in editable list
   - Edit descriptions, deadlines, success criteria
   - Add new actions manually
   - Remove irrelevant actions
   - Reorder by priority

3. **User Confirms Actions**:
   - Click "Track These Actions" → Actions saved to database
   - Reminder preferences set (email daily/weekly, in-app for Pro)

**UI Flow**:
```svelte
<!-- After synthesis report -->
<section class="action-extraction">
  <h2>📋 Proposed Actions</h2>
  <p>Based on the synthesis, here are the key actions to take:</p>

  {#each proposedActions as action, i}
    <div class="action-card editable">
      <input type="checkbox" bind:checked={action.selected} />

      <div class="action-content">
        <textarea bind:value={action.description} rows="2">
          {action.description}
        </textarea>

        <div class="action-meta">
          <label>
            Deadline:
            <input type="date" bind:value={action.deadline} />
          </label>

          <label>
            Success Criteria:
            <input type="text" bind:value={action.success_criteria} placeholder="How will you know it's done?" />
          </label>
        </div>
      </div>

      <button class="btn-icon" on:click={() => removeAction(i)}>🗑️</button>
    </div>
  {/each}

  <button class="btn-secondary" on:click={addAction}>+ Add Action</button>

  <div class="action-footer">
    <button class="btn-primary" on:click={confirmActions}>
      Track {selectedActions.length} Actions
    </button>

    <button class="btn-link" on:click={skipActions}>
      Skip (No tracking)
    </button>
  </div>
</section>
```

**AI Action Extraction** (Example):

**Synthesis Report (Input)**:
```markdown
## Next Steps

1. Week 1-2: Conduct 20 customer interviews to validate pricing hypotheses
2. Week 3-4: Build landing page with pricing tiers, collect 100 email signups
3. Week 5-8: Launch beta pricing ($29/month), monitor conversion rate
4. Week 9: Analyze results, adjust pricing if conversion <5%
```

**Extracted Actions** (Output):
```json
[
  {
    "description": "Conduct 20 customer interviews to validate pricing hypotheses",
    "deadline": "2025-12-01", // 2 weeks from now
    "success_criteria": "Completed 20 interviews, documented key insights",
    "priority": 1
  },
  {
    "description": "Build landing page with pricing tiers",
    "deadline": "2025-12-15", // 4 weeks from now
    "success_criteria": "Landing page live, 100 email signups collected",
    "priority": 2,
    "depends_on": [1] // Depends on action #1
  },
  {
    "description": "Launch beta pricing at $29/month",
    "deadline": "2026-01-12", // 8 weeks from now
    "success_criteria": "Beta launched, 10+ paying customers",
    "priority": 3,
    "depends_on": [2]
  },
  {
    "description": "Analyze pricing results and adjust if needed",
    "deadline": "2026-01-19", // 9 weeks from now
    "success_criteria": "Conversion rate measured, decision made on adjustments",
    "priority": 4,
    "depends_on": [3]
  }
]
```

### 2.2 In-Progress Tracking

**User accesses action dashboard** (`/actions`):

1. **View All Actions**:
   - Grouped by deliberation (e.g., "Pricing Strategy", "Product Roadmap")
   - Filtered by status (All, Not Started, In Progress, Completed, Blocked, Overdue)
   - Sorted by deadline (soonest first)

2. **Update Action Status**:
   - Click action → Mark as "In Progress" or "Completed"
   - Add notes (progress updates, blockers encountered)
   - Extend deadline if needed (with reason)

3. **Mark as Blocked**:
   - Select blocker reason (e.g., "Dependency not met", "Unexpected obstacle")
   - Optionally trigger replanning deliberation

**UI**:
```svelte
<!-- src/routes/actions/+page.svelte -->
<section class="action-dashboard">
  <h1>Your Actions</h1>

  <!-- Filters -->
  <div class="filters">
    <select bind:value={filterStatus}>
      <option value="all">All</option>
      <option value="not_started">Not Started</option>
      <option value="in_progress">In Progress</option>
      <option value="completed">Completed</option>
      <option value="blocked">Blocked</option>
      <option value="overdue">Overdue</option>
    </select>

    <select bind:value={filterDeliberation}>
      <option value="all">All Deliberations</option>
      {#each deliberations as delib}
        <option value={delib.id}>{delib.title}</option>
      {/each}
    </select>
  </div>

  <!-- Actions List -->
  <div class="actions-list">
    {#each filteredActions as action}
      <div class="action-item" class:overdue={action.is_overdue}>
        <div class="action-header">
          <h3>{action.description}</h3>
          <StatusBadge status={action.status} />
        </div>

        <div class="action-meta">
          <span>Deadline: {formatDate(action.deadline)}</span>
          {#if action.is_overdue}
            <span class="overdue-label">⚠️ {daysOverdue(action.deadline)} days overdue</span>
          {/if}
        </div>

        <p class="success-criteria">✅ Success: {action.success_criteria}</p>

        <div class="action-actions">
          <button on:click={() => updateStatus(action.id, 'in_progress')}>Start</button>
          <button on:click={() => updateStatus(action.id, 'completed')}>Complete</button>
          <button on:click={() => markBlocked(action.id)}>Mark Blocked</button>
          <button on:click={() => editAction(action.id)}>Edit</button>
        </div>

        {#if action.notes}
          <details class="action-notes">
            <summary>Notes ({action.notes.length})</summary>
            <ul>
              {#each action.notes as note}
                <li>{formatDate(note.created_at)}: {note.content}</li>
              {/each}
            </ul>
          </details>
        {/if}
      </div>
    {/each}
  </div>
</section>
```

### 2.3 Replanning (When Blocked or Context Changes)

**User marks action as blocked**:

1. **Blocker Reason** (Modal):
   - Select reason: "Dependency not met", "Resource unavailable", "Unexpected obstacle", "Context changed"
   - Add details (optional): "Customer interviews revealed pricing is too high"

2. **Trigger Replanning** (Optional):
   - "Would you like to replan this action with expert input?"
   - If yes → Start new deliberation with context:
     - Original deliberation summary
     - Current action status
     - Blocker details

3. **New Deliberation**:
   - Problem statement: "How to adjust pricing strategy given customer feedback?"
   - Experts discuss, provide revised recommendations
   - New actions extracted

**UI**:
```svelte
<!-- Modal: Mark Action as Blocked -->
<Modal bind:open={blockModalOpen}>
  <h2>Mark Action as Blocked</h2>

  <label>
    Why is this action blocked?
    <select bind:value={blockerReason}>
      <option value="dependency">Dependency not met</option>
      <option value="resource">Resource unavailable</option>
      <option value="obstacle">Unexpected obstacle</option>
      <option value="context_change">Context changed</option>
    </select>
  </label>

  <label>
    Details (optional):
    <textarea bind:value={blockerDetails} placeholder="What happened?"></textarea>
  </label>

  <div class="replan-option">
    <label>
      <input type="checkbox" bind:checked={triggerReplanning} />
      Trigger replanning deliberation (get expert help adjusting plan)
    </label>
  </div>

  <div class="modal-actions">
    <button class="btn-secondary" on:click={closeModal}>Cancel</button>
    <button class="btn-primary" on:click={confirmBlocked}>Confirm</button>
  </div>
</Modal>
```

**Replanning Deliberation** (Auto-generated problem statement):
```
Original Deliberation: "Pricing Strategy for SaaS Product"

Original Action: "Launch beta pricing at $29/month, achieve 10+ paying customers"

Blocker: Unexpected obstacle - Customer interviews revealed $29/month is too high for target market (solo founders). Willingness to pay is closer to $15-20/month.

New Problem: How should we adjust our pricing strategy given this feedback? Should we:
- Lower price to $15-20/month and validate demand?
- Add more value to justify $29/month?
- Pivot to a different customer segment (e.g., agencies vs solo founders)?

Context:
- Current state: 5 customer interviews completed, 0 paying customers yet
- Resources: $10K budget remaining, 8 months runway
- Constraints: Need to hit $5K MRR by month 6
```

---

## 3. Tier-Specific Features

### 3.1 Trial Tier (Free)

**Action Tracking**: ❌ **Locked** (visible but disabled)

**UX**:
- After synthesis report → Show action extraction UI (grayed out)
- "Upgrade to Core to track your actions and stay accountable" CTA
- No access to action dashboard

**Rationale**: Action tracking is a sticky feature (high retention), so paywall it to drive conversions.

### 3.2 Core Tier (£25/month)

**Action Tracking**: ✅ **Basic**

**Features**:
- **Max 5 actions per deliberation** (sufficient for most use cases)
- **Email reminders**: Daily or weekly digest for overdue actions
- **Progress tracking**: Mark actions as not started, in progress, completed, blocked
- **Notes**: Add progress updates to actions
- **Monthly progress report**: Email summary at end of month

**Limitations**:
- No in-app notifications (email only)
- No action templates (manual entry only)
- No advanced analytics (just basic completion rate)

### 3.3 Pro Tier (£50/month)

**Action Tracking**: ✅ **Advanced**

**Features**:
- **Unlimited actions per deliberation**
- **In-app notifications**: Real-time reminders for overdue actions, milestones
- **Weekly + monthly reports**: Detailed progress tracking with insights
- **Action templates**: Pre-built templates for common workflows (product launch, fundraising, hiring)
- **Dependency tracking**: Link actions with dependencies (can't start Action B until Action A complete)
- **Advanced analytics**: Completion rate over time, avg time to complete, bottleneck detection
- **Replanning priority**: Replanning deliberations get higher priority (faster LLM responses)

**Pro-Only Features**:
```svelte
<!-- Action templates -->
<div class="action-templates">
  <h3>Use a Template</h3>
  <select bind:value={selectedTemplate}>
    <option value="">Select a template</option>
    <option value="product_launch">Product Launch (10 actions)</option>
    <option value="fundraising">Fundraising Round (8 actions)</option>
    <option value="hiring">First Hire (6 actions)</option>
  </select>
  <button on:click={applyTemplate}>Apply Template</button>
</div>

<!-- Dependency tracking -->
<div class="action-dependencies">
  <label>
    Depends on:
    <select multiple bind:value={action.depends_on}>
      {#each previousActions as prevAction}
        <option value={prevAction.id}>{prevAction.description}</option>
      {/each}
    </select>
  </label>
</div>
```

---

## 4. Action Model & States

### 4.1 Action States

```
Not Started → In Progress → Completed
     ↓              ↓
   Blocked ← ← ← ← ←
```

**State Definitions**:
- **Not Started**: Action created but not yet begun
- **In Progress**: User actively working on it
- **Completed**: Action finished, success criteria met
- **Blocked**: Cannot proceed due to blocker (dependency, resource, obstacle)

**State Transitions**:
- Not Started → In Progress (user starts working)
- In Progress → Completed (user marks complete)
- In Progress → Blocked (user encounters blocker)
- Blocked → In Progress (blocker resolved)
- Any state → Blocked (can block at any time)

### 4.2 Action Properties

```typescript
interface Action {
  id: string; // UUID
  deliberation_id: string; // References session
  user_id: string;

  // Content
  description: string; // "Conduct 20 customer interviews"
  success_criteria: string; // "Completed 20 interviews, documented insights"

  // Scheduling
  deadline: Date; // Target completion date
  estimated_duration_hours?: number; // Optional: "This will take ~10 hours"

  // Status
  status: 'not_started' | 'in_progress' | 'completed' | 'blocked';
  priority: number; // 1 (highest) to 10 (lowest)

  // Dependencies (Pro tier)
  depends_on: string[]; // Array of action IDs

  // Progress
  started_at?: Date; // When user marked "in progress"
  completed_at?: Date; // When user marked "completed"
  blocked_at?: Date; // When user marked "blocked"
  blocker_reason?: string; // "dependency", "resource", "obstacle", "context_change"
  blocker_details?: string; // Free text

  // Metadata
  created_at: Date;
  updated_at: Date;
}

interface ActionNote {
  id: string;
  action_id: string;
  content: string; // Progress update, blocker details, etc.
  created_at: Date;
}
```

---

## 5. UI Components

### 5.1 Action Extraction (Post-Deliberation)

**Location**: Immediately after synthesis report

**Component**: `ActionExtractor.svelte`

**Features**:
- AI-proposed actions (editable)
- Drag-to-reorder (priority)
- Add/remove actions
- Set deadlines (date picker, or quick options: "1 week", "2 weeks", "1 month")
- Success criteria (pre-filled, editable)

**Tier Gates**:
- Trial: Locked (show UI but disable, upgrade CTA)
- Core: Max 5 actions
- Pro: Unlimited actions

### 5.2 Action Dashboard

**Location**: `/actions` (dedicated page)

**Component**: `ActionDashboard.svelte`

**Sections**:
1. **Overview** (Top):
   - Total actions: 15
   - Completed: 8 (53%)
   - In Progress: 5 (33%)
   - Blocked: 2 (13%)
   - Overdue: 3 (20%)

2. **Filters** (Left sidebar or top bar):
   - Status (all, not started, in progress, completed, blocked, overdue)
   - Deliberation (filter by which deliberation)
   - Date range (this week, this month, all time)

3. **Actions List** (Main area):
   - Grouped by deliberation (collapsible)
   - Each action: Description, deadline, status badge, quick actions (start, complete, block, edit)

4. **Quick Actions** (Right sidebar, Pro only):
   - "Mark all overdue as blocked"
   - "Extend all deadlines by 1 week"
   - "Archive completed actions"

**Keyboard Shortcuts**:
- `S` - Mark selected action as "Started" (In Progress)
- `C` - Mark selected action as "Completed"
- `B` - Mark selected action as "Blocked"
- `E` - Edit selected action
- `J/K` - Navigate up/down actions (Vim-style)

### 5.3 Action Detail Modal

**Triggered by**: Clicking action in dashboard

**Component**: `ActionDetailModal.svelte`

**Sections**:
- **Description** (editable)
- **Success Criteria** (editable)
- **Deadline** (editable with date picker)
- **Status** (dropdown: not started, in progress, completed, blocked)
- **Priority** (slider: 1-10)
- **Dependencies** (multi-select, Pro only)
- **Notes** (timeline of progress updates)
- **Quick Actions**: Start, Complete, Block, Delete

### 5.4 Progress Reports

**Location**: Sent via email (monthly), viewable at `/actions/reports`

**Component**: `ProgressReport.svelte`

**Content**:
```
📊 Monthly Progress Report (November 2025)

Actions Completed: 12 / 15 (80%)
On-Time Completion Rate: 75% (9 completed on time, 3 late)
Avg Completion Time: 7 days (target: 5 days)
Blocked Actions: 2 (1 resolved, 1 still blocked)

Deliberations with Actions:
1. Pricing Strategy: 5/5 completed ✅
2. Product Roadmap: 4/6 completed (2 in progress)
3. Hiring Plan: 3/4 completed (1 blocked)

Insights:
- You're consistently completing actions, great job! 🎉
- Consider reducing deadline estimates by 2 days (you're finishing early on average)
- "Hiring Plan" has 1 blocked action for 3 weeks - consider replanning?

Next Month's Actions (5 upcoming):
- "Launch beta pricing" (Due: Dec 5)
- "Hire first engineer" (Due: Dec 12)
- "Ship v1 feature set" (Due: Dec 20)

[View Full Report] →
```

---

## 6. Reminders & Notifications

### 6.1 Email Reminders (Core + Pro)

**Frequency Options**:
- Daily digest (all overdue + due today)
- Weekly digest (all overdue + due this week)
- Per-action reminders (3 days before, 1 day before, overdue)

**Email Template** (Daily Digest):
```
Subject: 🔔 You have 3 overdue actions

Hi [User],

You have 3 overdue actions from your Board of One deliberations:

1. "Conduct 20 customer interviews" (Pricing Strategy)
   - Deadline: Nov 1, 2025 (13 days overdue)
   - Success: Completed 20 interviews, documented insights
   [Mark Complete] [Mark Blocked] [View Details]

2. "Build landing page with pricing tiers" (Pricing Strategy)
   - Deadline: Nov 10, 2025 (4 days overdue)
   - Success: Landing page live, 100 signups
   [Mark Complete] [Mark Blocked] [View Details]

3. "Hire first engineer" (Hiring Plan)
   - Deadline: Nov 12, 2025 (2 days overdue)
   - Success: Offer accepted, start date set
   [Mark Complete] [Mark Blocked] [View Details]

Don't let these slip! Stay on track to achieve your goals.

[View All Actions] → https://app.boardof.one/actions

---
Board of One
[Unsubscribe from action reminders]
```

### 6.2 In-App Notifications (Pro Only)

**Notification Types**:
- Action overdue (1 day, 3 days, 7 days overdue)
- Action due soon (3 days, 1 day, today)
- Dependency completed (if action has dependency, notify when unblocked)
- Weekly summary (every Monday: "You have 5 actions this week")

**Notification UI** (Top-right bell icon):
```svelte
<div class="notifications">
  <button class="notification-bell" on:click={toggleNotifications}>
    🔔
    {#if unreadCount > 0}
      <span class="badge">{unreadCount}</span>
    {/if}
  </button>

  {#if notificationsOpen}
    <div class="notification-dropdown">
      <h3>Notifications</h3>

      {#each notifications as notif}
        <div class="notification-item" class:unread={!notif.read}>
          <p>{notif.message}</p>
          <span class="timestamp">{formatRelativeTime(notif.created_at)}</span>
          <button on:click={() => markRead(notif.id)}>Dismiss</button>
        </div>
      {/each}

      {#if notifications.length === 0}
        <p class="empty">No new notifications</p>
      {/if}

      <a href="/settings/notifications" class="link">Notification Settings</a>
    </div>
  {/if}
</div>
```

---

## 7. Progress Reporting

### 7.1 Metrics Tracked

**Action-Level Metrics**:
- Completion rate (completed / total)
- On-time completion rate (completed on-time / total completed)
- Avg time to complete (actual completion time vs estimated)
- Blocked rate (blocked / total)
- Time to resolve blocker (blocked_at → in_progress)

**Deliberation-Level Metrics**:
- Actions per deliberation (avg: 5, max: 10)
- Deliberations with all actions completed (success rate)
- Most blocked deliberation (needs replanning?)

**User-Level Metrics**:
- Monthly action completion count
- Completion streak (days with at least 1 action completed)
- Avg deadline adherence (on-time %)

### 7.2 Report Types

**Monthly Progress Email**:
- Sent on 1st of each month
- Summary of last month's actions
- Insights and recommendations
- Preview of next month's actions

**Weekly Digest Email** (Pro only):
- Sent every Monday
- Actions due this week
- Overdue actions
- Completion progress (week-over-week)

**In-App Report** (`/actions/reports`):
- Interactive charts (completion rate over time, on-time %)
- Drill down by deliberation
- Export to PDF

---

## 8. Replanning & Adaptation

### 8.1 Replanning Triggers

**User-Initiated**:
- Marks action as blocked → "Trigger replanning?" prompt
- Clicks "Replan" on action detail modal
- "Situation has changed" button on deliberation page

**System-Initiated** (Suggestions):
- Action blocked for >2 weeks → "Consider replanning?"
- 50%+ actions overdue on same deliberation → "Time to replan?"

### 8.2 Replanning Deliberation Flow

**Auto-Generated Problem Statement**:
```
Context: You previously deliberated on "[Original Problem]" and decided to "[Original Recommendation]".

You created the following action: "[Action Description]"
Deadline: [Original Deadline]
Success Criteria: "[Success Criteria]"

Current Status: Blocked
Blocker: [Blocker Reason] - [Blocker Details]

New Problem: How should you adjust your plan given this blocker?

Additional Context:
- Time elapsed since original deliberation: [X days]
- Other actions from same deliberation: [Y completed, Z blocked]
- Resources available: [Budget, time, team]
```

**Expert Deliberation**:
- Same personas as original (or request different perspectives)
- Focus: Adaptation, not starting from scratch
- Output: Revised recommendation, updated actions

**Action Updates**:
- User can update existing actions (extend deadlines, revise descriptions)
- Or create new actions (if plan changes significantly)

---

## 9. Database Schema

### 9.1 Actions Table

```sql
CREATE TABLE actions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  deliberation_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

  -- Content
  description TEXT NOT NULL,
  success_criteria TEXT NOT NULL,

  -- Scheduling
  deadline DATE NOT NULL,
  estimated_duration_hours INTEGER,

  -- Status
  status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'blocked')),
  priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),

  -- Dependencies (Pro tier)
  depends_on UUID[], -- Array of action IDs

  -- Progress timestamps
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  blocked_at TIMESTAMPTZ,

  -- Blocker info
  blocker_reason TEXT CHECK (blocker_reason IN ('dependency', 'resource', 'obstacle', 'context_change')),
  blocker_details TEXT,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_actions_user_id ON actions(user_id);
CREATE INDEX idx_actions_deliberation_id ON actions(deliberation_id);
CREATE INDEX idx_actions_status ON actions(status);
CREATE INDEX idx_actions_deadline ON actions(deadline);

-- RLS Policy
CREATE POLICY "users_own_actions" ON actions
  FOR ALL
  USING (auth.uid() = (SELECT supabase_user_id FROM users WHERE id = actions.user_id));
```

### 9.2 Action Notes Table

```sql
CREATE TABLE action_notes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_action_notes_action_id ON action_notes(action_id);

-- RLS Policy
CREATE POLICY "users_own_action_notes" ON action_notes
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM actions
      WHERE actions.id = action_notes.action_id
        AND actions.user_id = (SELECT id FROM users WHERE supabase_user_id = auth.uid())
    )
  );
```

### 9.3 Action Templates Table (Pro Tier)

```sql
CREATE TABLE action_templates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL, -- "Product Launch", "Fundraising", etc.
  description TEXT,
  actions JSONB NOT NULL, -- Array of template actions

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example template
INSERT INTO action_templates (name, description, actions) VALUES (
  'Product Launch',
  'Standard actions for launching a new product',
  '[
    {"description": "Finalize product roadmap and features", "deadline_offset_days": 0, "success_criteria": "Roadmap approved by stakeholders"},
    {"description": "Build MVP (minimum viable product)", "deadline_offset_days": 30, "success_criteria": "MVP shipped to beta testers"},
    {"description": "Conduct user testing with 10 beta users", "deadline_offset_days": 45, "success_criteria": "10 beta users tested, feedback documented"},
    {"description": "Launch marketing campaign (landing page, email, social)", "deadline_offset_days": 55, "success_criteria": "Landing page live, 100 signups"},
    {"description": "Public launch on Product Hunt", "deadline_offset_days": 60, "success_criteria": "Product Hunt launch, 500 upvotes"},
    {"description": "Gather post-launch feedback and iterate", "deadline_offset_days": 75, "success_criteria": "Feedback collected, 3 top bugs fixed"}
  ]'
);
```

---

## 10. Implementation Phases

### Phase 1: MVP (2-3 weeks)
**Goal**: Basic action tracking (Core tier)

**Features**:
- [ ] Action extraction (AI-powered, editable)
- [ ] Action dashboard (list view, status updates)
- [ ] Mark actions: not started, in progress, completed, blocked
- [ ] Email reminders (daily or weekly digest)
- [ ] Basic progress report (monthly email)

**Deliverables**:
- Actions table + RLS policies
- Action extraction UI (post-deliberation)
- Action dashboard page (`/actions`)
- Email reminder cron job

---

### Phase 2: Pro Features (2-3 weeks)
**Goal**: Advanced tracking for Pro tier

**Features**:
- [ ] Unlimited actions (Core limited to 5)
- [ ] In-app notifications (real-time)
- [ ] Dependency tracking (link actions)
- [ ] Action templates (pre-built workflows)
- [ ] Weekly + monthly reports (detailed insights)
- [ ] Advanced analytics (completion rate over time, bottleneck detection)

**Deliverables**:
- Action templates table
- Dependency tracking logic
- In-app notification system (WebSocket or polling)
- Advanced analytics dashboard (`/actions/analytics`)

---

### Phase 3: Replanning (3-4 weeks)
**Goal**: Adaptive deliberation when things change

**Features**:
- [ ] Mark action as blocked → Trigger replanning prompt
- [ ] Auto-generate replanning problem statement (with context)
- [ ] Replanning deliberation (same flow as original)
- [ ] Update existing actions or create new ones
- [ ] Track replanning history (deliberation → replanning → replanning v2)

**Deliverables**:
- Replanning deliberation logic
- Replanning UI flow (blocker modal → problem generation → deliberation)
- Action update/merge logic (update existing vs create new)

---

### Phase 4: Polish & Optimization (1-2 weeks)
**Goal**: UX polish, performance, and scalability

**Features**:
- [ ] Keyboard shortcuts (S, C, B, E, J/K)
- [ ] Bulk actions (mark all overdue as blocked, extend all deadlines)
- [ ] Action search (find actions by keyword)
- [ ] Export actions (CSV, JSON)
- [ ] Performance optimization (cache action counts, lazy load action notes)

**Deliverables**:
- Keyboard shortcut system
- Bulk action operations
- Search/filter performance optimization

---

**Total Timeline**: 8-12 weeks for full action tracking feature (MVP → Pro → Replanning → Polish)

**Priority**: Phase 1 (MVP) is critical for Core tier stickiness. Phase 2 (Pro) drives Pro tier upsells. Phase 3 (Replanning) is unique differentiator.

---

**END OF ACTION TRACKING FEATURE**

This document provides a complete design for the post-deliberation accountability system, including tier-specific features, replanning logic, database schema, and implementation phases. This is the "big feature" that drives user success and retention.
