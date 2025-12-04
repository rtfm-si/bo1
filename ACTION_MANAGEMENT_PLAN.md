# Action Management Enhancement Plan

## Implementation Progress

### ✅ Phase 1: Foundation (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Database Migrations** (`migrations/versions/a1_*` through `a4_*`):
   - `a1_create_actions_table.py` - Created comprehensive actions table with 28 columns
   - `a2_create_action_dependencies.py` - Created action_dependencies table for dependency tracking
   - `a3_create_action_updates.py` - Created action_updates table for activity feed
   - `a4_migrate_session_tasks_data.py` - Migrated 43 tasks from session_tasks JSONB to actions table

2. **Backend Components**:
   - `bo1/state/repositories/action_repository.py` - Full CRUD operations for actions
   - `bo1/utils/timeline_parser.py` - Parses "2 weeks" → 10 business days
   - `backend/api/actions.py` - Updated API endpoints for new actions table
   - `backend/api/models.py` - Updated ActionStatus enum (6 states)

3. **Frontend Updates**:
   - Updated all components to use `in_progress` instead of `doing`
   - Updated `ActionStatus` type to include all 6 states
   - Updated statusConfig in action detail page for all statuses
   - Updated dashboard, actions page, kanban board, and task cards

**Key Design Decisions**:
- Used VARCHAR with CHECK constraints instead of PostgreSQL ENUMs (simpler migrations)
- Breaking changes accepted (no live customers)
- Status mapping: `doing` → `in_progress` throughout the codebase

**Database Schema**:
```
actions (28 columns)
├── id (UUID PK)
├── user_id → users.id
├── source_session_id → sessions.id
├── title, description, what_and_how[], success_criteria[], kill_criteria[]
├── status: todo | in_progress | blocked | in_review | done | cancelled
├── priority, category, timeline, estimated_duration_days
├── target_start_date, target_end_date, estimated_start_date, estimated_end_date
├── actual_start_date, actual_end_date
├── blocking_reason, blocked_at, auto_unblock
├── confidence, source_section, sub_problem_index, sort_order
└── created_at, updated_at

action_dependencies
├── action_id → actions.id
├── depends_on_action_id → actions.id
├── dependency_type: finish_to_start | start_to_start | finish_to_finish
├── lag_days
└── created_at

action_updates (activity feed)
├── id (BigInt PK)
├── action_id → actions.id
├── user_id → users.id
├── update_type: progress | blocker | note | status_change | date_change | completion
├── content, old_status, new_status, old_date, new_date, date_field, progress_percent
└── created_at
```

### ✅ Phase 2: Status Workflow (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Status Transition Validation** (`bo1/state/repositories/action_repository.py`):
   - `VALID_TRANSITIONS` dict defining allowed status flows
   - `validate_status_transition()` - Returns (is_valid, error_message)
   - Terminal states: `done` and `cancelled` cannot transition to other states

   Valid transitions:
   ```
   todo → in_progress, blocked, cancelled
   blocked → todo, in_progress, cancelled
   in_progress → blocked, in_review, done, cancelled
   in_review → in_progress, done, cancelled
   done → (terminal)
   cancelled → (terminal)
   ```

2. **Dependency CRUD Operations** (`bo1/state/repositories/action_repository.py`):
   - `add_dependency()` - Add dependency with circular check, auto-blocks if needed
   - `remove_dependency()` - Remove dependency, auto-unblocks if all deps complete
   - `get_dependencies()` - Get all dependencies (what this action depends on)
   - `get_dependents()` - Get all actions that depend on this action
   - `has_incomplete_dependencies()` - Check if action has incomplete dependencies

3. **Circular Dependency Detection**:
   - `_would_create_cycle()` - BFS traversal to detect cycles before adding dependency
   - Prevents self-dependencies and transitive cycles (A→B→C→A)

4. **Auto-Blocking Logic**:
   - `_check_and_auto_block()` - Auto-block action when dependency added to incomplete action
   - Only auto-blocks actions in `todo` status
   - Sets `blocking_reason` to "Waiting for: {dependency_title}"
   - Sets `auto_unblock = true` for automatic unblocking later

5. **Auto-Unblocking Logic**:
   - `_check_and_auto_unblock()` - Unblock when dependency removed and no more incomplete deps
   - `auto_unblock_dependents()` - Unblock all dependent actions when action completes
   - Called automatically when action marked as `done` or `cancelled`
   - Creates audit trail in `action_updates` table

6. **Convenience Methods**:
   - `block_action()` - Block with reason, validates transition
   - `unblock_action()` - Unblock to target status (default: 'todo')

7. **API Endpoints** (`backend/api/actions.py`):

   **Dependency Endpoints:**
   - `GET /api/v1/actions/{id}/dependencies` - List dependencies with completion status
   - `POST /api/v1/actions/{id}/dependencies` - Add dependency (auto-blocks if incomplete)
   - `DELETE /api/v1/actions/{id}/dependencies/{dep_id}` - Remove dependency (may auto-unblock)

   **Block/Unblock Endpoints:**
   - `POST /api/v1/actions/{id}/block` - Block with reason and optional auto_unblock
   - `POST /api/v1/actions/{id}/unblock` - Unblock to target status (warns about incomplete deps)

   **Updated Endpoints:**
   - `PATCH /api/v1/actions/{id}/status` - Now validates transitions, auto-unblocks on done/cancelled
   - `POST /api/v1/actions/{id}/complete` - Now returns list of auto-unblocked dependents

8. **Pydantic Models** (`backend/api/models.py`):
   - `DependencyCreate` - Request for adding dependency
   - `DependencyResponse` - Dependency with action details
   - `DependencyListResponse` - List with has_incomplete flag
   - `BlockActionRequest` - Block with reason and auto_unblock
   - `UnblockActionRequest` - Unblock with target status

9. **Frontend Types** (`frontend/src/lib/api/types.ts`):
   - `DependencyType` - finish_to_start | start_to_start | finish_to_finish
   - `DependencyCreateRequest`, `DependencyResponse`, `DependencyListResponse`
   - `BlockActionRequest`, `UnblockActionRequest`
   - `DependencyMutationResponse`, `BlockUnblockResponse`

**Key Design Decisions**:
- Auto-block only triggers for `todo` status (not for in-progress actions)
- Auto-unblock uses `auto_unblock` flag (can be disabled per-action)
- Users can manually unblock even with incomplete dependencies (with warning)
- All status changes create audit records in `action_updates`

### ✅ Phase 3: Date Calculations (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Timeline Parsing Utility** (`bo1/utils/timeline_parser.py` - already existed):
   - `parse_timeline()` - Converts "2 weeks" → 10 business days
   - `add_business_days()` - Adds business days skipping weekends
   - `format_timeline()` - Converts days back to human-readable format

2. **Date Calculation Methods** (`bo1/state/repositories/action_repository.py`):
   - `calculate_estimated_start_date()` - Calculates start based on dependencies:
     - Returns maximum of: today, target_start_date, and dependency end dates + lag_days
     - Handles finish_to_start and start_to_start dependency types
     - Uses actual_end_date for completed dependencies, estimated_end_date for others
   - `calculate_estimated_end_date()` - Calculates end based on start + duration:
     - Uses target_end_date if set
     - Otherwise: estimated_start + estimated_duration_days (business days)
   - `recalculate_action_dates()` - Recalculates and updates dates for single action
   - `recalculate_dates_cascade()` - BFS cascade through dependency chain:
     - Starts from changed action, visits all dependents
     - Updates estimated dates for each affected action
     - Returns list of updated action IDs
   - `recalculate_all_user_dates()` - Bulk recalculation for all user's active actions

3. **Integration with Dependency Management**:
   - `add_dependency()` now triggers date cascade after adding dependency
   - `complete_action()` now triggers date cascade after completion
   - Dates propagate through the dependency chain automatically

4. **API Endpoints** (`backend/api/actions.py`):
   - `PATCH /api/v1/actions/{id}/dates` - Update target dates and/or timeline
     - Validates date formats (YYYY-MM-DD)
     - Validates target_end >= target_start
     - Updates timeline and estimated_duration_days if timeline provided
     - Triggers cascade recalculation
     - Returns updated dates and cascade count
   - `POST /api/v1/actions/{id}/recalculate-dates` - Force recalculation
     - Useful for manual refresh or debugging
     - Returns current dates after recalculation

5. **Pydantic Models** (`backend/api/models.py`):
   - `ActionDatesUpdate` - Request for updating dates (all fields optional)
   - `ActionDatesResponse` - Response with all date fields and cascade count

6. **Frontend Dates Display** (`frontend/src/routes/(app)/actions/[session_id]/[task_id]/+page.svelte`):
   - Added "Schedule & Dates" card to action detail page
   - Displays:
     - Duration (timeline or estimated_duration_days)
     - Target start/end dates (user-set, amber styling)
     - Estimated start/end dates (calculated, brand styling)
     - Actual start/end dates (when action started/completed, success styling)
     - Blocking info when status is blocked
   - Helper functions:
     - `formatDate()` - Formats dates as "Dec 4, 2025"
     - `hasAnyDates()` - Shows card only if action has date info

**Key Design Decisions**:
- Dates cascade automatically on dependency add/complete
- Business days only (weekends skipped)
- Target dates (user-set) take precedence over calculated estimates
- Cascade uses BFS to ensure proper dependency order
- All date changes create audit records in action_updates

### ✅ Phase 4: Projects (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Database Migrations** (`migrations/versions/a5_*` through `a7_*`):
   - `a5_create_projects_table.py` - Projects table with status, dates, progress tracking
   - `a6_create_session_projects_table.py` - Session-project linking (discusses, created_from, replanning)
   - `a7_add_project_id_to_actions.py` - Added project_id FK to actions table

2. **Backend Components**:
   - `bo1/state/repositories/project_repository.py` - Full CRUD operations:
     - `create()`, `get()`, `get_by_user()`, `update()`, `delete()`
     - `update_status()` - Status workflow validation (active→paused→completed→archived)
     - `recalculate_progress()` - Calculate progress from completed actions
     - `get_actions()` - Get project's actions with filtering
     - `assign_action()`, `unassign_action()` - Action-project assignment
     - `link_session()`, `unlink_session()`, `get_sessions()` - Session linking
     - `get_gantt_data()` - Timeline data for Gantt visualization
   - `backend/api/projects.py` - API router with endpoints:
     - `GET/POST /api/v1/projects` - List/create projects
     - `GET/PATCH/DELETE /api/v1/projects/{id}` - CRUD operations
     - `PATCH /api/v1/projects/{id}/status` - Status updates
     - `GET/POST/DELETE /api/v1/projects/{id}/actions/{action_id}` - Action management
     - `GET /api/v1/projects/{id}/gantt` - Gantt chart data
     - `POST/DELETE/GET /api/v1/projects/{id}/sessions` - Session linking
   - `backend/api/models.py` - Pydantic models:
     - `ProjectCreate`, `ProjectUpdate`, `ProjectStatusUpdate`
     - `ProjectDetailResponse`, `ProjectListResponse`
     - `ProjectActionSummary`, `ProjectActionsResponse`
     - `ProjectSessionLink`, `GanttResponse`

3. **Frontend Components**:
   - `frontend/src/lib/api/types.ts` - TypeScript types for all project-related data
   - `frontend/src/lib/api/client.ts` - API client methods for all project endpoints
   - `frontend/src/routes/(app)/projects/+page.svelte` - Project listing page:
     - Grid view with progress bars and status badges
     - Create project modal
     - Archive/delete functionality
   - `frontend/src/routes/(app)/projects/[id]/+page.svelte` - Project detail page:
     - Project status and progress display
     - Description and dates sections
     - Actions list with status indicators
     - Remove actions from project
     - Linked sessions management

**Key Design Decisions**:
- Status workflow: active → paused → completed → archived (with validation)
- Progress auto-calculated from completed_actions / total_actions
- Actions can be assigned to at most one project
- Session linking supports multiple relationship types
- Gantt data endpoint ready for Phase 6 visualization

### ✅ Phase 5: Action Updates (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Backend Pydantic Models** (`backend/api/models.py`):
   - `ActionUpdateCreate` - Request model for creating updates (progress, blocker, note)
   - `ActionUpdateResponse` - Response model with all update fields
   - `ActionUpdatesResponse` - List response with total count

2. **API Endpoints** (`backend/api/actions.py`):
   - `GET /api/v1/actions/{action_id}/updates` - Get activity timeline for an action
   - `POST /api/v1/actions/{action_id}/updates` - Add progress update, blocker, or note

3. **Frontend TypeScript Types** (`frontend/src/lib/api/types.ts`):
   - `ActionUpdateType` - Union type for all update types
   - `ActionUpdateCreateRequest`, `ActionUpdateResponse`, `ActionUpdatesResponse`

4. **Frontend API Client** (`frontend/src/lib/api/client.ts`):
   - `getActionUpdates(actionId, limit?)` - Fetch activity timeline
   - `addActionUpdate(actionId, update)` - Add new update

5. **Frontend Components**:
   - `ActivityTimeline.svelte` - Displays activity feed chronologically with:
     - Relative timestamps ("2h ago", "Dec 4, 2025")
     - Color-coded update types (progress, blocker, note, status_change, etc.)
     - Progress bars for progress updates
     - Empty state handling
   - `UpdateInput.svelte` - Form to add updates with:
     - Type selector (Note, Progress, Blocker)
     - Content textarea
     - Progress slider (0-100%) for progress updates
     - Cmd+Enter keyboard shortcut
     - Disabled state for completed/cancelled actions

6. **Page Integration** (`frontend/src/routes/(app)/actions/[session_id]/[task_id]/+page.svelte`):
   - Activity section with UpdateInput and ActivityTimeline
   - Auto-loads updates on mount
   - Updates list on successful submission

**Note**: Auto-create on status/date changes was already implemented in Phase 2/3. The repository methods (`add_update`, `get_updates`) call these automatically when status or dates change.

### ✅ Phase 6: Gantt Visualization (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Gantt Library Selection**:
   - Evaluated frappe-gantt (MIT, lightweight) vs SVAR Gantt (GPLv3, requires commercial license)
   - Selected frappe-gantt for MIT license compatibility with commercial use
   - Created TypeScript declarations at `frontend/src/lib/types/frappe-gantt.d.ts`

2. **Gantt Chart Component** (`frontend/src/lib/components/projects/GanttChart.svelte`):
   - Uses Svelte action pattern for frappe-gantt initialization (avoids SSR issues)
   - Dynamic import to prevent server-side rendering errors
   - Status-based color coding for all 6 action statuses:
     - `todo`: neutral-400 (#9CA3AF)
     - `in_progress`: brand-500 (#6366F1)
     - `blocked`: error-500 (#EF4444)
     - `in_review`: purple-500 (#A855F7)
     - `done`: success-500 (#22C55E)
     - `cancelled`: neutral-500 (#6B7280)
   - Dependency arrows between actions (finish-to-start visualization)
   - Progress bars reflecting action completion
   - Custom popup with status badge, dates, and blocking reason
   - Click-to-navigate to action detail page
   - Drag-to-reschedule capability (when readOnly=false)
   - Empty state when no actions have dates

3. **Project Detail Page Integration** (`frontend/src/routes/(app)/projects/[id]/+page.svelte`):
   - Added Gantt section with view mode selector (Day/Week/Month/Quarter)
   - Loads Gantt data via existing `/api/v1/projects/{id}/gantt` endpoint
   - Task click navigates to action detail page
   - Styled to match application design system

4. **View Mode Controls**:
   - Day: Daily granularity for short-term planning
   - Week: Default view for typical project timelines
   - Month: Monthly view for longer projects
   - Quarter: Quarterly view for strategic planning

**Key Design Decisions**:
- Used frappe-gantt (MIT) over SVAR Gantt (GPLv3) for commercial licensing compatibility
- Svelte action pattern for clean library integration and proper cleanup
- Dynamic import prevents SSR issues with DOM-dependent library
- Status colors match existing design system tokens
- Read-only mode by default (editing via action detail page preferred)

### ✅ Phase 7: AI Integration (COMPLETED - December 4, 2025)

**What was implemented:**

1. **Database Migration** (`migrations/versions/a8_add_replanning_fields.py`):
   - Added `replan_session_id` FK to actions table (references sessions)
   - Added `replan_requested_at` timestamp
   - Added `replanning_reason` text field
   - Created index and foreign key constraint

2. **Replanning Context Builder** (`bo1/services/replanning_context.py`):
   - `build_replan_problem_statement()` - Creates structured problem statement:
     - Original action details (title, description, steps, success/kill criteria)
     - Current blocking reason and duration
     - User-provided additional context
   - `gather_related_context()` - Collects comprehensive context:
     - Action dependencies and their statuses
     - Project information (if action is in a project)
     - Original session problem statement and synthesis
   - `build_problem_context()` - Creates `problem_context` dict for session

3. **Replanning Service** (`bo1/services/replanning_service.py`):
   - `create_replan_session()` - Main orchestration method:
     - Validates action exists and is blocked
     - Returns existing replan session if one already exists
     - Builds problem context using replanning_context module
     - Creates new session via session_repository
     - Links session to project (if action has project) with 'replanning' relationship
     - Updates action with replan_session_id and replan_requested_at
     - Returns session_id for redirect

4. **Backend API** (`backend/api/actions.py`):
   - `POST /api/v1/actions/{action_id}/replan` - New endpoint:
     - Accepts optional `additional_context` in request body
     - Validates action ownership and blocked status
     - Returns `ReplanResponse` with session_id, redirect_url, and is_existing flag

5. **Pydantic Models** (`backend/api/models.py`):
   - `ReplanRequest` - Optional additional_context field
   - `ReplanResponse` - session_id, action_id, message, redirect_url, is_existing
   - Added replanning fields to `ActionDetailResponse`:
     - `replan_session_id`, `replan_requested_at`, `replanning_reason`
     - `can_replan` - Computed field (true when status is 'blocked')

6. **Frontend Types** (`frontend/src/lib/api/types.ts`):
   - `ReplanRequest`, `ReplanResponse` interfaces
   - Updated `ActionDetailResponse` with replanning fields

7. **Frontend API Client** (`frontend/src/lib/api/client.ts`):
   - `requestReplan(actionId, additionalContext?)` - New method

8. **Action Detail Page UI** (`frontend/src/routes/(app)/actions/[session_id]/[task_id]/+page.svelte`):
   - Replanning state management (showReplanModal, replanContext, isRequestingReplan)
   - "Request AI Replanning" button in blocked section (when can_replan is true)
   - "View Meeting" link (when replan_session_id exists)
   - Replan modal with:
     - Action summary and blocking reason
     - Optional additional context textarea
     - Cancel/Submit buttons with loading state
     - Error handling
   - Auto-redirect to replanning meeting on submit

**Key Design Decisions**:
- Reuses existing session/deliberation infrastructure
- One replan session per action (returns existing if already created)
- Links replan session to project with 'replanning' relationship type
- Full context provided to AI: action details, dependencies, project, original synthesis
- Clean modal UX with progressive disclosure (optional context)

**Database Schema Addition**:
```sql
-- Added to actions table
ALTER TABLE actions ADD COLUMN replan_session_id VARCHAR(255) REFERENCES sessions(id) ON DELETE SET NULL;
ALTER TABLE actions ADD COLUMN replan_requested_at TIMESTAMPTZ;
ALTER TABLE actions ADD COLUMN replanning_reason TEXT;
CREATE INDEX idx_actions_replan_session ON actions(replan_session_id);
```

---

## All Phases Complete!

The Action Management system is now fully implemented with:
- **Phase 1**: Foundation - Actions table, migrations, data migration
- **Phase 2**: Status Workflow - 6-status system, auto-blocking/unblocking
- **Phase 3**: Date Calculations - Timeline parsing, cascade recalculation
- **Phase 4**: Projects - Project CRUD, session linking, action assignment
- **Phase 5**: Action Updates - Activity timeline, progress tracking
- **Phase 6**: Gantt Visualization - frappe-gantt integration, dependency arrows
- **Phase 7**: AI Integration - Replanning for blocked actions

---

## Overview

Transform Board of One's task management from simple todo/doing/done tracking into a comprehensive project-based action management system with dependency tracking, date estimation, and Gantt visualization.

---

## Core Concepts

### Entity Hierarchy

```
User
  └── Projects (value-delivery containers)
        └── Actions (individual tasks)
              └── Updates (progress notes, blockers, etc.)

Sessions (deliberation meetings)
  └── Discusses 1+ Projects
  └── Creates Actions (assigned to Projects)
```

### Key Relationships

| Entity | Relationship | Entity |
|--------|--------------|--------|
| Project | has many | Actions |
| Action | belongs to | Project |
| Action | depends on | Actions (0..n) |
| Action | blocks | Actions (0..n) |
| Session | discusses | Projects (1..n) |
| Session | creates | Actions (via deliberation) |
| Action | has many | Updates |
| User | owns | Projects |

---

## Data Model

### Projects Table (NEW)

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),

    -- Core fields
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, completed, archived

    -- Dates
    target_start_date DATE,
    target_end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,

    -- Calculated (updated by triggers/app)
    estimated_start_date DATE,  -- min(actions.estimated_start_date)
    estimated_end_date DATE,    -- max(actions.estimated_end_date)

    -- Progress
    progress_percent INTEGER DEFAULT 0,  -- calculated from completed actions

    -- Metadata
    color VARCHAR(7),  -- hex color for Gantt
    icon VARCHAR(50),  -- emoji or icon name

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
```

### Actions Table (REPLACES session_tasks JSONB)

```sql
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    project_id UUID REFERENCES projects(id),
    source_session_id UUID REFERENCES sessions(id),

    -- Core fields (from existing task model)
    title VARCHAR(500) NOT NULL,
    description TEXT,
    what_and_how TEXT[],
    success_criteria TEXT[],
    kill_criteria TEXT[],

    -- Status workflow
    status VARCHAR(50) DEFAULT 'todo',
    -- todo, in_progress, blocked, in_review, done, cancelled

    -- Priority & Category
    priority VARCHAR(20) DEFAULT 'medium',  -- high, medium, low
    category VARCHAR(50) DEFAULT 'implementation',
    -- implementation, research, decision, communication, ongoing

    -- Duration & Dates
    timeline VARCHAR(100),              -- original text: "2-3 weeks"
    estimated_duration_days INTEGER,    -- parsed: 17

    target_start_date DATE,             -- user-set goal
    target_end_date DATE,               -- user-set deadline

    estimated_start_date DATE,          -- calculated from dependencies
    estimated_end_date DATE,            -- estimated_start + duration

    actual_start_date TIMESTAMPTZ,      -- when "Start" clicked
    actual_end_date TIMESTAMPTZ,        -- when marked "Done"

    -- Blocking & Dependencies
    blocking_reason TEXT,
    blocked_at TIMESTAMPTZ,
    auto_unblock BOOLEAN DEFAULT true,  -- auto-unblock when deps complete

    -- Recurring
    is_recurring BOOLEAN DEFAULT false,
    recurrence_rule VARCHAR(500),       -- RFC 5545 RRULE
    parent_action_id UUID REFERENCES actions(id),

    -- AI metadata
    confidence FLOAT DEFAULT 0.0,
    source_section VARCHAR(100),
    sub_problem_index INTEGER,

    -- Ordering
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_actions_user ON actions(user_id);
CREATE INDEX idx_actions_project ON actions(project_id);
CREATE INDEX idx_actions_status ON actions(status);
CREATE INDEX idx_actions_estimated_dates ON actions(estimated_start_date, estimated_end_date);
```

### Action Dependencies Table (NEW)

```sql
CREATE TABLE action_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    depends_on_action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,

    dependency_type VARCHAR(50) DEFAULT 'finish_to_start',
    -- finish_to_start: B cannot start until A finishes
    -- start_to_start: B cannot start until A starts
    -- finish_to_finish: B cannot finish until A finishes

    lag_days INTEGER DEFAULT 0,  -- buffer between dependency completion and this start

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(action_id, depends_on_action_id)
);

CREATE INDEX idx_deps_action ON action_dependencies(action_id);
CREATE INDEX idx_deps_depends_on ON action_dependencies(depends_on_action_id);
```

### Action Updates Table (NEW)

```sql
CREATE TABLE action_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),

    update_type VARCHAR(50) NOT NULL,
    -- progress, blocker, note, status_change, date_change, completion

    content TEXT,

    -- For status changes
    old_status VARCHAR(50),
    new_status VARCHAR(50),

    -- For date changes
    old_date DATE,
    new_date DATE,
    date_field VARCHAR(50),  -- which date changed

    -- For progress
    progress_percent INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_updates_action ON action_updates(action_id);
CREATE INDEX idx_updates_created ON action_updates(created_at DESC);
```

### Session-Project Link Table (NEW)

```sql
CREATE TABLE session_projects (
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    relationship VARCHAR(50) DEFAULT 'discusses',
    -- discusses, created_from, replanning

    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY(session_id, project_id)
);
```

---

## Status Workflow

### Status States

| Status | Description | Can Transition To |
|--------|-------------|-------------------|
| `todo` | Not started, ready to begin | in_progress, blocked, cancelled |
| `blocked` | Cannot proceed (dependency or external) | todo, in_progress, cancelled |
| `in_progress` | Actively being worked on | blocked, in_review, done, cancelled |
| `in_review` | Waiting for feedback/approval | in_progress, done, cancelled |
| `done` | Successfully completed | (terminal) |
| `cancelled` | Abandoned, no longer relevant | (terminal) |

### Automatic Status Transitions

```python
# When a dependency is added to an action
if any(dep.status not in ['done', 'cancelled'] for dep in action.dependencies):
    action.status = 'blocked'
    action.blocking_reason = f"Waiting for: {incomplete_deps[0].title}"

# When a dependency completes
for dependent_action in action.blocked_by_this:
    if all(dep.status in ['done', 'cancelled'] for dep in dependent_action.dependencies):
        if dependent_action.auto_unblock:
            dependent_action.status = 'todo'
            dependent_action.blocking_reason = None
```

---

## Date Calculation Logic

### Estimated Start Date

```python
def calculate_estimated_start_date(action):
    """
    Estimated start = latest of:
    1. Today (can't start in the past)
    2. Target start date (if set)
    3. Max dependency estimated_end_date + lag_days
    """
    candidates = [date.today()]

    if action.target_start_date:
        candidates.append(action.target_start_date)

    for dep in action.dependencies:
        dep_end = dep.action.estimated_end_date
        if dep_end:
            # Add lag days from dependency relationship
            start_after = dep_end + timedelta(days=dep.lag_days)
            candidates.append(start_after)

    return max(candidates)
```

### Estimated End Date

```python
def calculate_estimated_end_date(action):
    """
    Estimated end = estimated_start + duration (in business days)
    """
    if not action.estimated_start_date:
        return None

    duration = action.estimated_duration_days or parse_timeline(action.timeline)
    if not duration:
        return None

    # Add business days (skip weekends)
    return add_business_days(action.estimated_start_date, duration)
```

### Cascade Recalculation

```python
def recalculate_dates_cascade(changed_action):
    """
    When an action's dates change, recalculate all dependents.
    Uses topological sort to ensure correct order.
    """
    # Get all actions that depend on this one (directly or indirectly)
    affected = get_dependent_actions_recursive(changed_action)

    # Sort by dependency depth (shallow first)
    sorted_actions = topological_sort(affected)

    for action in sorted_actions:
        old_start = action.estimated_start_date
        old_end = action.estimated_end_date

        action.estimated_start_date = calculate_estimated_start_date(action)
        action.estimated_end_date = calculate_estimated_end_date(action)

        # Log if dates changed significantly
        if old_end != action.estimated_end_date:
            create_update(action, 'date_change',
                         old_date=old_end,
                         new_date=action.estimated_end_date,
                         date_field='estimated_end_date')
```

### Timeline Parsing

```python
import re

def parse_timeline(timeline: str) -> int | None:
    """Parse timeline string to days."""
    if not timeline:
        return None

    timeline = timeline.lower().strip()

    patterns = [
        # "2 days", "1 day"
        (r'(\d+)\s*(?:day|d)s?', lambda m: int(m.group(1))),
        # "2 weeks", "1 week"
        (r'(\d+)\s*(?:week|w)s?', lambda m: int(m.group(1)) * 5),  # 5 business days
        # "2-3 weeks" (take average)
        (r'(\d+)\s*-\s*(\d+)\s*(?:week|w)s?',
         lambda m: ((int(m.group(1)) + int(m.group(2))) // 2) * 5),
        # "1 month", "2 months"
        (r'(\d+)\s*(?:month|m)s?', lambda m: int(m.group(1)) * 22),  # ~22 business days
        # "ongoing" - no end date
        (r'ongoing|continuous|recurring', lambda m: None),
    ]

    for pattern, converter in patterns:
        match = re.search(pattern, timeline)
        if match:
            return converter(match)

    return None  # Unknown format
```

---

## API Endpoints

### Projects

```
GET    /api/v1/projects                    # List user's projects
POST   /api/v1/projects                    # Create project
GET    /api/v1/projects/{id}               # Get project details
PATCH  /api/v1/projects/{id}               # Update project
DELETE /api/v1/projects/{id}               # Archive project

GET    /api/v1/projects/{id}/actions       # Get project's actions
GET    /api/v1/projects/{id}/gantt         # Get Gantt chart data
GET    /api/v1/projects/{id}/timeline      # Get timeline data
```

### Actions

```
GET    /api/v1/actions                     # List all actions (with filters)
POST   /api/v1/actions                     # Create action
GET    /api/v1/actions/{id}                # Get action details
PATCH  /api/v1/actions/{id}                # Update action
DELETE /api/v1/actions/{id}                # Delete/cancel action

POST   /api/v1/actions/{id}/start          # Start action (sets actual_start_date)
POST   /api/v1/actions/{id}/complete       # Complete action
POST   /api/v1/actions/{id}/block          # Block action with reason
POST   /api/v1/actions/{id}/unblock        # Unblock action

GET    /api/v1/actions/{id}/dependencies   # Get dependencies
POST   /api/v1/actions/{id}/dependencies   # Add dependency
DELETE /api/v1/actions/{id}/dependencies/{dep_id}  # Remove dependency

GET    /api/v1/actions/{id}/updates        # Get action updates
POST   /api/v1/actions/{id}/updates        # Add update/note
```

### Gantt Data

```
GET /api/v1/projects/{id}/gantt

Response:
{
  "project": {
    "id": "...",
    "name": "Launch MVP",
    "estimated_start_date": "2025-01-06",
    "estimated_end_date": "2025-02-28"
  },
  "actions": [
    {
      "id": "action_1",
      "title": "Design mockups",
      "estimated_start_date": "2025-01-06",
      "estimated_end_date": "2025-01-10",
      "actual_start_date": "2025-01-06",
      "actual_end_date": null,
      "status": "in_progress",
      "progress_percent": 60,
      "dependencies": [],
      "color": "#3B82F6"
    },
    {
      "id": "action_2",
      "title": "Implement UI",
      "estimated_start_date": "2025-01-13",
      "estimated_end_date": "2025-01-24",
      "actual_start_date": null,
      "actual_end_date": null,
      "status": "blocked",
      "progress_percent": 0,
      "dependencies": ["action_1"],
      "blocking_reason": "Waiting for: Design mockups",
      "color": "#9CA3AF"
    }
  ],
  "dependencies": [
    {
      "from": "action_1",
      "to": "action_2",
      "type": "finish_to_start"
    }
  ]
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Migrate from JSONB tasks to proper actions table with date fields

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 1.1 Create migration for `actions` table | 2 days | - | Day 1 | Day 2 |
| 1.2 Create migration for `action_dependencies` | 1 day | 1.1 | Day 3 | Day 3 |
| 1.3 Create migration for `action_updates` | 1 day | 1.1 | Day 3 | Day 3 |
| 1.4 Migrate existing session_tasks to actions | 2 days | 1.1-1.3 | Day 4 | Day 5 |
| 1.5 Update backend models (Pydantic) | 2 days | 1.4 | Day 6 | Day 7 |
| 1.6 Update session_repository for new schema | 2 days | 1.5 | Day 8 | Day 9 |
| 1.7 Parse existing `timeline` → `estimated_duration_days` | 1 day | 1.4 | Day 10 | Day 10 |

### Phase 2: Status Workflow (Week 2-3)

**Goal**: Implement 6-status workflow with automatic blocking

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 2.1 Expand status enum in backend | 1 day | 1.5 | Day 11 | Day 11 |
| 2.2 Implement status transition validation | 2 days | 2.1 | Day 12 | Day 13 |
| 2.3 Add blocking/unblocking endpoints | 2 days | 2.2 | Day 14 | Day 15 |
| 2.4 Implement auto-block on dependency add | 2 days | 2.3 | Day 16 | Day 17 |
| 2.5 Implement auto-unblock on dependency complete | 2 days | 2.4 | Day 18 | Day 19 |
| 2.6 Update frontend action detail page | 3 days | 2.5 | Day 20 | Day 22 |

### Phase 3: Date Calculations (Week 3-4)

**Goal**: Automatic date estimation and cascade recalculation

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 3.1 Implement timeline parsing function | 1 day | 1.7 | Day 23 | Day 23 |
| 3.2 Implement estimated_start_date calculation | 2 days | 3.1, 2.5 | Day 24 | Day 25 |
| 3.3 Implement estimated_end_date calculation | 1 day | 3.2 | Day 26 | Day 26 |
| 3.4 Implement cascade recalculation | 3 days | 3.3 | Day 27 | Day 29 |
| 3.5 Add "Start" button that sets actual_start_date | 1 day | 3.4 | Day 30 | Day 30 |
| 3.6 Frontend: Show dates in action detail | 2 days | 3.5 | Day 31 | Day 32 |

### Phase 4: Projects (Week 4-5)

**Goal**: Introduce projects as containers for related actions

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 4.1 Create migration for `projects` table | 1 day | 1.1 | Day 33 | Day 33 |
| 4.2 Create migration for `session_projects` | 1 day | 4.1 | Day 34 | Day 34 |
| 4.3 Project CRUD endpoints | 2 days | 4.2 | Day 35 | Day 36 |
| 4.4 Link actions to projects | 2 days | 4.3 | Day 37 | Day 38 |
| 4.5 Project listing page (frontend) | 2 days | 4.4 | Day 39 | Day 40 |
| 4.6 Project detail page with actions | 3 days | 4.5 | Day 41 | Day 43 |
| 4.7 Assign actions to projects from deliberation | 2 days | 4.6 | Day 44 | Day 45 |

### Phase 5: Action Updates (Week 5-6)

**Goal**: Progress tracking with notes and status history

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 5.1 Action updates endpoints | 2 days | 1.3 | Day 46 | Day 47 |
| 5.2 Auto-create updates on status change | 1 day | 5.1 | Day 48 | Day 48 |
| 5.3 Auto-create updates on date change | 1 day | 5.2 | Day 49 | Day 49 |
| 5.4 Frontend: Update input on action detail | 2 days | 5.3 | Day 50 | Day 51 |
| 5.5 Frontend: Activity timeline on action detail | 2 days | 5.4 | Day 52 | Day 53 |

### Phase 6: Gantt Visualization (Week 6-7)

**Goal**: Visual timeline of project actions with dependencies

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 6.1 Research Gantt libraries (frappe-gantt, etc.) | 1 day | - | Day 54 | Day 54 |
| 6.2 Gantt data endpoint | 2 days | 4.6, 3.4 | Day 55 | Day 56 |
| 6.3 Integrate Gantt component | 3 days | 6.2 | Day 57 | Day 59 |
| 6.4 Dependency arrows on Gantt | 2 days | 6.3 | Day 60 | Day 61 |
| 6.5 Drag-to-reschedule on Gantt | 3 days | 6.4 | Day 62 | Day 64 |
| 6.6 Status colors and progress bars | 2 days | 6.5 | Day 65 | Day 66 |

### Phase 7: AI Integration (Week 7-8)

**Goal**: AI-assisted replanning when actions are blocked

| Task | Duration | Dependencies | Start | End |
|------|----------|--------------|-------|-----|
| 7.1 "Request Replanning" button on blocked actions | 1 day | 2.6 | Day 67 | Day 67 |
| 7.2 Replanning context builder | 2 days | 7.1 | Day 68 | Day 69 |
| 7.3 Trigger new deliberation with context | 2 days | 7.2 | Day 70 | Day 71 |
| 7.4 Link replan session to original project | 1 day | 7.3 | Day 72 | Day 72 |
| 7.5 Merge replan actions into project | 2 days | 7.4 | Day 73 | Day 74 |

---

## UI Components

### Action Status Badge (Quick Update)

```svelte
<!-- Single-click status dropdown -->
<StatusBadge
  status={action.status}
  onStatusChange={(newStatus) => updateStatus(action.id, newStatus)}
  allowedTransitions={getAllowedTransitions(action.status)}
/>

<!-- Shows colored badge, click → dropdown with valid next states -->
<!-- Optimistic update, toast on error -->
```

### Block Modal (Lightweight)

```svelte
<BlockModal action={action} onBlock={handleBlock}>
  <!-- Shows when user clicks "Block" -->
  <!-- Pre-fills blocking_reason from dependencies -->
  <!-- Auto-suggest: "Waiting for: [first incomplete dependency]" -->
  <!-- Optional custom reason text -->
  <!-- Toggle: "Auto-unblock when dependencies complete" -->
</BlockModal>
```

### Action Timeline (Activity Feed)

```svelte
<ActionTimeline actionId={action.id}>
  <!-- Shows all updates in reverse chronological order -->
  <!-- Status changes, date changes, notes, blockers -->
  <!-- "Add update" input at top -->
</ActionTimeline>
```

### Project Gantt Chart

```svelte
<ProjectGantt projectId={project.id}>
  <!-- Horizontal timeline with actions as bars -->
  <!-- Dependency arrows between bars -->
  <!-- Color by status: blue=progress, gray=blocked, green=done -->
  <!-- Click bar → open action detail -->
  <!-- Drag bar ends → reschedule -->
  <!-- Today line indicator -->
</ProjectGantt>
```

### Dependency Selector

```svelte
<DependencySelector
  actionId={action.id}
  projectActions={project.actions}
  onAddDependency={addDep}
  onRemoveDependency={removeDep}
>
  <!-- Shows current dependencies with remove button -->
  <!-- Dropdown to add new dependency from project actions -->
  <!-- Prevents circular dependencies -->
  <!-- Shows warning if would cause date conflicts -->
</DependencySelector>
```

---

## Migration Strategy

### Data Migration (session_tasks → actions)

```python
def migrate_session_tasks_to_actions():
    """
    Migrate existing JSONB tasks to new actions table.
    Preserves all data and relationships.
    """
    # 1. Get all session_tasks records
    session_tasks = db.query("SELECT * FROM session_tasks")

    for record in session_tasks:
        session_id = record['session_id']
        tasks = record['tasks']  # JSONB array
        statuses = record['task_statuses'] or {}

        # Get session for user_id
        session = db.query("SELECT user_id FROM sessions WHERE id = %s", session_id)

        for task in tasks:
            # 2. Create action record
            action = {
                'id': task['id'],
                'user_id': session['user_id'],
                'source_session_id': session_id,
                'project_id': None,  # Will be assigned later

                'title': task.get('title', ''),
                'description': task.get('description', ''),
                'what_and_how': task.get('what_and_how', []),
                'success_criteria': task.get('success_criteria', []),
                'kill_criteria': task.get('kill_criteria', []),

                'status': statuses.get(task['id'], 'todo'),
                'priority': task.get('priority', 'medium'),
                'category': task.get('category', 'implementation'),

                'timeline': task.get('timeline', ''),
                'estimated_duration_days': parse_timeline(task.get('timeline')),

                'confidence': task.get('confidence', 0.0),
                'source_section': task.get('source_section'),
                'sub_problem_index': task.get('sub_problem_index'),
            }

            db.insert('actions', action)

            # 3. Create dependency records
            for dep in task.get('dependencies', []):
                # Dependencies are currently strings, need to match to action IDs
                # This is a best-effort match
                dep_action = find_action_by_title_or_id(dep)
                if dep_action:
                    db.insert('action_dependencies', {
                        'action_id': task['id'],
                        'depends_on_action_id': dep_action['id'],
                        'dependency_type': 'finish_to_start',
                    })

    # 4. Calculate initial dates for all actions
    recalculate_all_action_dates()
```

---

## Testing Plan

### Unit Tests

```python
# test_date_calculations.py
def test_parse_timeline():
    assert parse_timeline("2 days") == 2
    assert parse_timeline("1 week") == 5
    assert parse_timeline("2-3 weeks") == 12  # average
    assert parse_timeline("1 month") == 22
    assert parse_timeline("ongoing") is None

def test_estimated_start_no_deps():
    action = Action(target_start_date=date(2025, 1, 15))
    # Today is 2025-01-10
    assert calculate_estimated_start_date(action) == date(2025, 1, 15)

def test_estimated_start_with_deps():
    dep_action = Action(estimated_end_date=date(2025, 1, 20))
    action = Action(dependencies=[dep_action])
    assert calculate_estimated_start_date(action) == date(2025, 1, 21)

def test_cascade_recalculation():
    # A → B → C chain
    a = Action(estimated_duration_days=5)  # ends Jan 10
    b = Action(estimated_duration_days=3, dependencies=[a])  # ends Jan 15
    c = Action(estimated_duration_days=2, dependencies=[b])  # ends Jan 17

    # Change A to take 10 days
    a.estimated_duration_days = 10
    recalculate_dates_cascade(a)

    assert a.estimated_end_date == date(2025, 1, 15)
    assert b.estimated_end_date == date(2025, 1, 20)
    assert c.estimated_end_date == date(2025, 1, 22)
```

### Integration Tests

```python
# test_status_workflow.py
def test_auto_block_on_dependency_add():
    action_a = create_action(status='in_progress')
    action_b = create_action(status='todo')

    add_dependency(action_b, depends_on=action_a)

    action_b.refresh()
    assert action_b.status == 'blocked'
    assert 'Waiting for' in action_b.blocking_reason

def test_auto_unblock_on_dependency_complete():
    action_a = create_action(status='in_progress')
    action_b = create_action(status='blocked', is_blocked_by=[action_a])

    complete_action(action_a)

    action_b.refresh()
    assert action_b.status == 'todo'
    assert action_b.blocking_reason is None
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Actions with due dates | >80% | % of actions with estimated_end_date |
| On-time completion | >70% | % completed before estimated_end_date |
| Average time blocked | <3 days | Mean(unblocked_at - blocked_at) |
| Update frequency | >2/week | Mean updates per active action per week |
| Project completion | >60% | % of projects reaching 100% progress |

---

## Future Enhancements (Post-MVP)

1. **Resource allocation**: Assign team members to actions
2. **Capacity planning**: Prevent over-allocation based on duration
3. **Critical path analysis**: Highlight actions that affect project end date
4. **Slack time visualization**: Show buffer between actions
5. **Scenario planning**: "What if" analysis for date changes
6. **Calendar integration**: Sync with Google Calendar / Outlook
7. **Notifications**: Email/push for upcoming due dates, blockers
8. **AI suggestions**: "Action X is blocking 3 others, prioritize?"

---

## Appendix: Gantt Library Options

| Library | Pros | Cons | License |
|---------|------|------|---------|
| frappe-gantt | Simple, lightweight | Limited features | MIT |
| dhtmlx-gantt | Full-featured, enterprise | Complex, paid for commercial | GPL/Commercial |
| bryntum-gantt | Modern, React support | Expensive | Commercial |
| gantt-task-react | React-native, customizable | Newer, less mature | MIT |

**Recommendation**: Start with `frappe-gantt` for MVP, evaluate `dhtmlx-gantt` for advanced features.

---

## Summary

This plan transforms Board of One's action management from simple status tracking to a comprehensive project management system with:

- **6-status workflow** with automatic blocking
- **Dependency tracking** with auto-unblock on completion
- **Date estimation** from timeline parsing and dependency chains
- **Projects** as containers for related value-delivering actions
- **Gantt visualization** for timeline planning
- **AI replanning** when actions are blocked

Total estimated duration: **8-10 weeks** for full implementation, with usable MVP at **4 weeks**.
