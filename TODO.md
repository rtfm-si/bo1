# Board of One - Prioritized TODO

Last updated: 2025-12-05 (deep audit completed)
Status: **P0 CRITICAL ISSUE ACTIVE** (Data Persistence - partial mitigation in place)

**Audit Summary** (verified 2025-12-05):

- ✅ P0-002: COMPLETED (sub-problem validation before meta-synthesis)
- ✅ P1-001: COMPLETED (Gantt chart fully implemented with error handling)
- ✅ P1-004: COMPLETED (working_status events for all 10 major phases)
- ✅ P1-008: COMPLETED (admin counts backend working)
- ✅ Cleanup Tasks: ALL COMPLETED (Synthesis label, mobile layout)
- ✅ P1-006: COMPLETED (soft-delete cascade)
- ⚠️ P0-001, P0-003, P0-004: PARTIAL implementation
- ⚠️ P2-001, P2-002, P2-003: PARTIAL implementation (dashboard, kanban, skip questions)
- ✅ P1-007: COMPLETED (actions filtered by session status)
- ✅ P1-005: COMPLETED (soft delete backend, UI pending)
- ❌ P1-002, P1-003: NOT STARTED

---

## P0: Critical Bugs (Data Loss / Core Functionality Broken)

These issues cause data loss or break core meeting functionality. **Fix immediately.**

### 1. [P0-001] Data Persistence Failure - Records Not Saved

**Status**: PARTIAL (retry logic exists, critical gaps remain)
**Reported**: ntfy alert 2025-12-05 - "no records persisted"
**User Impact**: Completed meetings/actions/business context lost after deploy

**Symptoms**:

- Completed sessions have no contributions in PostgreSQL
- Business context disappears after deployment
- Actions from meetings are lost

**Currently Implemented** (verified 2025-12-05):

- Event persistence verification: `event_collector.py:943-989` - compares Redis vs PostgreSQL counts
- Event publisher retry logic: `event_publisher.py:112-169` - 3 immediate retries (no backoff, intentionally non-blocking)
- Session status update retries: `event_collector.py:865-941` - exponential backoff (0.1s, 0.2s)
- Pool health check: `health.py:296-378` and `database.py:73-114`
- CRITICAL logging on persistence failures

**Critical Gaps**:

- No persistent queue - failed events are logged but NOT queued for later retry
- No deployment safety - restarts can interrupt in-progress meetings
- No early detection - daily reports don't catch persistence failures

**To Implement**:

- [x] Persistence verification at meeting end → `event_collector.py:943-989`
- [ ] Add persistence monitoring to health checks - **PARTIAL** (pool only, not events)
- [ ] Add Redis queue for failed persistence retries - **NOT DONE**
- [ ] Add deployment drain period (stop new meetings before restart) - **NOT DONE** - should we stand up the new instance for new meetings, let old meetings complete on the old instance, then cut over?
- [ ] Enhance daily report to detect persistence failures earlier - **PARTIAL**
- [ ] Add PostgreSQL write-ahead logging for critical events - **NOT DONE**

**Files**: `backend/api/event_publisher.py`, `bo1/state/repositories/session_repository.py`, `backend/api/event_collector.py`

---

### 2. [P0-002] Sub-Problems Fail But Summary Still Generated

**Status**: ✅ COMPLETED (verified 2025-12-05)
**User Impact**: Users get incomplete/wrong meeting results

**Problem**: When sub-problems fail during deliberation, the meta-synthesis still runs and generates a summary based on incomplete data.

**Implemented**:

- [x] Add validation in `routers.py` before meta-synthesis → `bo1/graph/routers.py:181-224`
- [x] Emit `meeting_failed` event if any sub-problems fail → `bo1/graph/routers.py:196-221`
- [x] Show clear error state to user instead of partial results → `ErrorEvent.svelte`

**Files**: `bo1/graph/routers.py`, `backend/api/event_collector.py`

---

### 3. [P0-003] Deployment Succeeds But App Actually Fails

**Status**: PARTIAL (API smoke tests exist, missing frontend/SSE)
**User Impact**: Users get errors after "successful" deployment

**Problem**: CI/CD reports success but pages don't load or API fails. Tests don't cover page load/interactivity.

**Current State** (verified 2025-12-05):

- API health checks implemented: `/api/health`, `/api/health/db`, `/api/health/redis`
- Deployment fails if API health checks fail (15 retries with 3s delay)
- Post-deploy validation hits production URL after nginx cutover

**To Implement**:

- [x] Add post-deploy smoke tests (hit key endpoints, verify response) → `.github/workflows/deploy-production.yml:679-695`
- [ ] Add frontend health check (can pages render?) - **NOT DONE**
- [ ] Add SSE connection test in deployment verification - **NOT DONE**
- [x] Fail deployment if smoke tests fail → exits with code 1 on failure

**Files**: `scripts/verify_deployment.py`, `.github/workflows/deploy-production.yml`

---

### 4. [P0-004] ntfy Daily Report Not Triggering Reliably

**Status**: PARTIAL (cron configured, missing heartbeat)
**User Impact**: Admin doesn't know when systems fail

**Problem**: Report didn't trigger this morning

**Current State** (verified 2025-12-05):

- Cron job configured: `0 9 * * *` (9:00 AM UTC daily) via `setup-db-monitoring-cron.sh`
- Docker container auto-detection (blue-green aware) in `db-report.sh`
- Weekly report also configured: `0 10 * * 1` (Monday 10:00 AM UTC)
- Logs to `/var/log/db-monitoring.log`

**To Implement**:

- [x] Check cron job configuration → `scripts/setup-db-monitoring-cron.sh:22-46`
- [ ] Add heartbeat check (alert if no report in 25 hours) - **NOT DONE**
- [ ] Add redundant alerting channel (email/Slack fallback) - **NOT DONE**

**Files**: `scripts/send_database_report.py`, `scripts/db-report.sh`, `scripts/setup-db-monitoring-cron.sh`

---

## P1: UX Blockers (Direct User Experience Impact)

These issues frustrate users and hurt retention. **Fix this week.**

### 1. [P1-001] Gantt Chart Fails to Load

**Status**: ✅ COMPLETED (verified 2025-12-05)
**User Impact**: Actions timeline view broken

**Implemented**:

- [x] frappe-gantt initialization in `GlobalGanttChart.svelte:224-273` - dynamic import, proper error handlers
- [x] Empty/invalid date data handled gracefully - `lines 217, 227, 314-318` default to today + 7 days
- [x] Empty state UI with helpful message - `lines 298-323`

**Files**: `frontend/src/lib/components/actions/GlobalGanttChart.svelte`

---

### 2. [P1-002] Mobile Navigation Broken - Text Too Big

**Status**: TODO
**User Impact**: App unusable on mobile

**To Implement**:

- [ ] Audit responsive breakpoints
- [ ] Fix font scaling on mobile
- [ ] Test navigation on common mobile viewport sizes

---

### 3. [P1-003] App Navigation Confusing

**Status**: TODO
**User Impact**: Users don't know where to go

**Problem**: Hierarchy unclear: meetings → projects → actions

**To Implement**:

- [ ] Add breadcrumbs
- [ ] Improve sidebar organization
- [ ] Add "back to meeting" from actions
- [ ] Dashboard as central hub (see P2-001)

---

### 4. [P1-004] "Still Working" Messages Inconsistent

**Status**: ✅ COMPLETED (verified 2025-12-05)
**User Impact**: Users think app is broken during long operations

**Implemented** (all 10 major phases now have working_status events):

- WorkingStatus.svelte component: ✅ Implemented with sticky positioning, elapsed time
- WorkingStatusBanner.svelte: ✅ Integrated with staleness fallback (8s timeout)
- SSE handler for working_status events: ✅ Implemented
- Timing state management: ✅ Consolidated in timingState.svelte.ts

**All Phases WITH working_status events** (user-friendly messages):

- [x] Decomposition: `event_collector.py:450` - "Breaking down your decision into key areas..."
- [x] Persona selection: `event_collector.py:533` - "Assembling the right experts for your question..."
- [x] Initial round: `event_collector.py:606` - "Experts are sharing their initial perspectives..." (15-30s)
- [x] Facilitator decisions: `event_collector.py:637` - "Guiding the discussion deeper..."
- [x] Parallel rounds: `event_collector.py:674` - "Experts are discussing (round N)..."
- [x] Moderator interventions: `event_collector.py:711` - "Ensuring balanced perspectives..."
- [x] Convergence checks: `event_collector.py:722` - "Checking for emerging agreement..."
- [x] Voting phase: `event_collector.py:742` - "Experts are finalizing their recommendations..."
- [x] Synthesis phase: `event_collector.py:756` - "Bringing together the key insights..."
- [x] Meta-synthesis: `event_collector.py:791` - "Crafting your final recommendation..."

**Files**: `frontend/src/lib/components/ui/WorkingStatus.svelte`, `backend/api/event_collector.py`

---

### 5. [P1-005] Delete Actions (Soft Delete)

**Status**: ✅ COMPLETED (backend) / PARTIAL (UI pending)
**User Impact**: Can't remove unwanted actions

**Implemented**:

- [x] Add `deleted_at` column to actions table → `migrations/versions/b2_add_actions_soft_delete.py`
- [x] Add soft delete endpoint → `DELETE /api/v1/actions/{action_id}` in `actions.py:645-688`
- [x] Repository methods: `delete()`, `restore()`, `hard_delete()` → `action_repository.py:517-566`
- [x] Exclude deleted actions from user queries → `action_repository.py:203-205`
- [x] Admins can see deleted items via `is_admin` parameter
- [ ] UI: Add delete button with confirmation (frontend pending)

**Files**: `bo1/state/repositories/action_repository.py`, `backend/api/actions.py`, `migrations/versions/b2_add_actions_soft_delete.py`

---

### 6. [P1-006] Deleted Meetings Should Delete Actions

**Status**: ✅ COMPLETED (2025-12-05)
**User Impact**: Orphaned actions from deleted meetings clutter UI

**Implemented**:

- [x] CASCADE constraint exists: `a1_create_actions_table.py:141` - `ondelete="CASCADE"`
  - Hard deletes cascade correctly at database level
- [x] Soft-delete actions when meeting soft-deleted → `sessions.py:668-677`
- [x] Repository methods: `soft_delete_by_session()`, `restore_by_session()` → `action_repository.py:572-602`

**Files**: `backend/api/sessions.py`, `bo1/state/repositories/action_repository.py`

---

### 7. [P1-007] Only Completed Meetings Should Show Actions

**Status**: ✅ COMPLETED (2025-12-05)
**User Impact**: Users see incomplete/failed meeting actions

**Problem**: In-progress and failed meetings showing actions

**Implemented**:

- [x] Filter actions API by session status = 'completed' → `action_repository.py:194-201`
- [x] Admin override to see all → `is_admin` parameter in `get_by_user()`
- [x] Failed meetings masked from end users (admin can see) → `actions.py:430-432`
- [x] Auth middleware fetches is_admin from database → `auth.py:118-130`

**Files**: `backend/api/actions.py`, `bo1/state/repositories/action_repository.py`, `backend/api/middleware/auth.py`

---

### 8. [P1-008] Admin Counts Not Working

**Status**: ✅ COMPLETED (verified 2025-12-05)
**User Impact**: Admin can't see usage metrics

**Investigation Result**:
Backend admin dashboard queries are fully implemented and working:

- `GET /api/admin/stats` → `AdminQueryService.get_stats()` in `backend/api/admin/helpers.py:115-153`
- `GET /api/admin/users` → `AdminQueryService.list_users()` with proper JOIN and GROUP BY
- `GET /api/admin/metrics` → API performance metrics via `MetricsCollector`

**Implemented**:

- [x] Debug admin dashboard queries → queries work correctly
- [x] Verify metrics aggregation → proper SQL aggregation with COUNT, SUM, MAX

**Note**: If admin counts appear incorrect, issue is likely frontend display or null values in sessions table.

---

## P2: User Value Features (Adoption/Conversion Drivers)

Drive user adoption and conversion. **Next 2-4 weeks.**

### 1. [P2-001] Dashboard as Control Centre

**Status**: PARTIAL (CTA added, remaining items optional)
**User Impact**: No single view of everything important

**Implemented** (`frontend/src/routes/(app)/dashboard/+page.svelte`):

- [x] Recent meetings summary (sessions list)
- [x] Outstanding actions panel (top 5 todo + in_progress)
- [x] Quick navigation to actions
- [x] Start new meeting CTA on dashboard → `+page.svelte:269-283`

**To Implement** (lower priority):

- [ ] "Active actions needing attention" section with urgency indicators
- [ ] Progress overview visualization

---

### 2. [P2-002] Kanban Board for Actions

**Status**: PARTIAL
**User Impact**: Better task management UX

**Implemented** (`frontend/src/lib/components/actions/KanbanBoard.svelte`):

- [x] 3-column layout: To Do, In Progress, Done
- [x] Task cards with status display
- [x] Status change callback (`onStatusChange`)
- [x] Responsive grid (single column on mobile)

**To Implement**:

- [ ] Drag-and-drop functionality (no drag library integrated)
- [ ] Persist sort order within columns

---

### 3. [P2-003] Clarify Questions Toggle/Skip

**Status**: PARTIAL
**User Impact**: Forced to answer questions even when unnecessary

**Implemented** (`frontend/src/lib/components/meeting/ClarificationForm.svelte:60-94`):

- [x] "Skip Questions" button implemented
- [x] `handleSkip()` function posts with `skip: true`

**To Implement**:

- [ ] User preference/setting to disable pre-deliberation questions entirely

---

### 4. [P2-004] Improve Summarization Quality

**Status**: TODO
**User Impact**: Summaries sometimes miss key points

**To Implement**:

- [ ] Use hierarchical summarization (round summaries in synthesis)
- [ ] Display expert summaries in UI
- [ ] Cap max sub-problems to reduce noise (simplify graph)

---

### 5. [P2-005] Performance Bottleneck Investigation

**Status**: TODO
**User Impact**: 30s gaps between events instead of expected 5s

**To Implement**:

- [ ] Add timing metrics to each graph node
- [ ] Profile LLM call latency
- [ ] Check for blocking I/O
- [ ] Investigate retry logic delays

---

### 6. [P2-006] Business Context & Competitor Research

**Status**: TODO
**User Impact**: Context not being used effectively

**To Implement**:

- [ ] Store research results locally (embeddings for deduplication)
- [ ] Retrieve from cache before expensive API calls
- [ ] Display research in meeting context

---

### 7. [P2-007] Email Waitlist Notification

**Status**: TODO
**User Impact**: Waitlist users not being engaged

**To Implement**:

- [ ] "X people joined waitlist" display
- [ ] Trigger email when spot opens
- [ ] Weekly engagement emails

---

### 8. [P2-008] Multiple Sample Reports

**Status**: TODO
**User Impact**: Landing page only shows one example

**To Implement**:

- [ ] Create sample reports for different business sizes/depths
- [ ] Add selector on landing page

---

### 9. [P2-009] Stripe Integration

**Status**: BLOCKED (on fixing P0/P1 first)

**To Implement**:

- [ ] Payment flow
- [ ] Tier management
- [ ] Trial period logic

---

### 10. [P2-010] Settings/Account Improvements

**Status**: TODO

**To Implement**:

- [ ] Remove 'delete context' from settings context > overview
- [ ] Account management page
- [ ] Subscription management

---

## P3: Nice-to-Haves (Polish & Growth)

Lower priority. **Backlog.**

### 1. [P3-001] Auto-Update Dependent Actions on Close

When actions closed (completed/killed), dependent actions should auto-update.
Note: `action_repository.py:auto_unblock_dependents()` may already exist - verify and add UI refresh.

### 2. [P3-002] Projects with AI-Generated Tags

Projects taggable with AI-generated categories, filterable.

### 3. [P3-003] Gantt Filterable by Project

Add project filter to Gantt chart. Also: Gantt accessible from actions tab.

### 4. [P3-004] Admin Impersonation

Admin can impersonate user to see their dashboard/meetings/actions with admin overlay (costs, failures, etc).

### 5. [P3-005] Feature Request Form

In-app feature request submission.

### 6. [P3-006] Report a Problem Flow

In-app problem reporting.

### 7. [P3-007] Help/Documentation

Help pages, onboarding guidance.

### 8. [P3-008] Landing Page SEO

Meta tags, structured data, content optimization. (2-3d)

### 9. [P3-009] Footer Pages Audit

Terms, privacy, about pages need updating. (1d)

---

## Cleanup Tasks (Low Effort)

- [x] Verify "Sub-Problem Complete" taxonomy change → ✅ VERIFIED in `SynthesisComplete.svelte:59`
- [x] Rename "Synthesis" to "Executive Summary" in fallback section → ✅ FIXED in `SynthesisComplete.svelte:259`
- [x] "The Bottom Line" duplicate in UI - FIXED in `xml-parser.ts`:
  - Added "The Bottom Line" to markdown section mappings (maps to `executive_summary`)
  - Added `stripDuplicateHeader()` function to remove LLM-repeated header text from content
  - Added lean template mappings: "What To Do Next", "Why This Matters", "Board Confidence", "Key Risks"
- [x] On mobile, 'connected' should flow under 'active' → ✅ FIXED in `meeting/[id]/+page.svelte:461-462`
  - Changed to `flex flex-col sm:flex-row sm:items-center` for responsive stacking

---

## Deferred: Not Now

These are complex systems premature for current stage. **Revisit after core product solid.**

### AI SEO Growth Engine

Automated content generation, social posting, comment learning.
**Status**: DEFERRED - Focus on core product first

### AI Ops Self-Healing System

Auto-recovery from failures, self-monitoring, Claude Code integration.
**Status**: DEFERRED - Need dedicated DevOps capacity

### Mentor Mode

Chat directly with AI expert, business context aware.
**Status**: DEFERRED - 1-2 week impl, needs solid action system first

### Workspaces & Teams

Team containers, shared meetings/context.
**Status**: DEFERRED - Later stage feature

### Projects System

Group related meetings, sub-projects.
**Status**: DEFERRED - Depends on workspaces

### Competition Research System

Auto-identify competitors, Brave/Tavily integration.
**Status**: DEFERRED - Depends on business context

### Gated Features / Tier Plans

Feature flags per user tier, pricing page.
**Status**: DEFERRED - After Stripe integration

### Action Replanning

Track outcomes, "what went wrong" flow, deadline chasing.
**Status**: DEFERRED - After core actions work

---

## Data Model Notes (Reference)

```
Projects
  ├── Actions (many)
  └── Sub-projects (many)

Meetings (sessions)
  ├── Projects (many)
  └── Actions (many)

Actions
  ├── Project (one, optional)
  ├── Sub-actions (many)
  └── Mentor assistance (future)

Expert Panels
  └── Mentors/Personas (many)
```

---

## Key Files Reference

| Area                 | File                                           |
| -------------------- | ---------------------------------------------- |
| Event persistence    | `backend/api/event_publisher.py`               |
| Session/event saving | `bo1/state/repositories/session_repository.py` |
| Monitoring           | `scripts/send_database_report.py`              |
| Actions CRUD         | `bo1/state/repositories/action_repository.py`  |
| Meeting flow         | `backend/api/event_collector.py`               |
| Graph config         | `bo1/graph/config.py`                          |

---

## Commands Reference

```bash
make pre-commit                    # Before any PR
make test                          # Run tests
uv run alembic upgrade head        # Apply migrations
python scripts/send_database_report.py daily  # Manual report
```
