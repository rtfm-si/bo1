# Board of One - Prioritized TODO

Last updated: 2025-12-06
Status: **Core Features Stable** - Focus shifting to growth features

---

## Completed Work (Reference)

The following major work is complete and should not be revisited:

| Area | Items Completed |
|------|-----------------|
| **P0 Critical** | Data persistence (Redis retry queue), sub-problem validation, deployment health checks, ntfy monitoring |
| **P1 UX** | Gantt chart, mobile navigation, breadcrumbs, working_status messages, soft delete (actions + cascade), session filtering, admin counts |
| **P2 Features** | Kanban drag-drop, expert summaries UI, research results UI, sample reports (6), SSE/LLM performance Phase 1 |
| **Cleanup** | Synthesis labels, mobile layout, duplicate headers |

---

## Priority Framework

| Priority | Definition | Timeline |
|----------|------------|----------|
| **P1** | High user value - drives adoption/conversion | Next 2-4 weeks |
| **P2** | Medium value - polish & engagement | Next 1-2 months |
| **P3** | Future - enterprise/scale features | Backlog |

---

## P1: High Priority - User Value Features

### 1. [P1-DATA] Data Analysis Platform

**Status**: NOT STARTED
**User Impact**: Transforms Bo1 from one-off decisions to ongoing business intelligence
**Effort**: 3-4 weeks

This feature allows users to upload data (CSV/Google Sheets), ask questions, and get AI-powered analysis that feeds into meeting context.

#### Architecture Overview

```
User Upload → Storage (Spaces) → Profile → Claude Tools → Analysis → Insights → Meeting Context
```

**Storage:**
- DigitalOcean Spaces: Raw CSVs, exports, charts
- PostgreSQL: datasets, profiles, analyses, insights
- Redis: Session state, cached profiles

---

#### EPIC 1: Backend Data Ingestion & Storage

**Goal:** Store raw files, register datasets, load them.

##### Task 1.1: Set up Spaces client
- [ ] Implement Python wrapper for DigitalOcean Spaces (boto3/S3-compatible)
- [ ] Functions: `upload_file(file_bytes, key) -> key`, `get_file(key) -> file_bytes`
- [ ] Add `DO_SPACES_*` env vars to config

**Files:** `bo1/storage/spaces.py`

##### Task 1.2: Implement CSV ingestion endpoint
- [ ] New route: `POST /api/v1/datasets/upload_csv`
- [ ] Accept multipart upload
- [ ] Store file in Spaces
- [ ] Create `datasets` row
- [ ] Return `{ dataset_id }`

**Files:** `backend/api/datasets.py`

##### Task 1.3: Implement Google Sheets ingestion endpoint
- [ ] New route: `POST /api/v1/datasets/from_sheet`
- [ ] Validate sheet URL, handle OAuth
- [ ] Store sheet URL in `source_location`
- [ ] Return `{ dataset_id }`

**Files:** `backend/api/datasets.py`

##### Task 1.4: Create Postgres migrations
- [ ] `datasets` table:
  ```sql
  id UUID PRIMARY KEY,
  owner_user_id VARCHAR NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  name VARCHAR(255) NOT NULL,
  source_type VARCHAR(50), -- 'csv_upload' | 'google_sheet'
  source_location TEXT,
  row_count INTEGER,
  column_count INTEGER,
  is_active BOOLEAN DEFAULT TRUE,
  deleted_at TIMESTAMPTZ
  ```
- [ ] `dataset_profiles` table:
  ```sql
  id UUID PRIMARY KEY,
  dataset_id UUID REFERENCES datasets(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  profile_json JSONB, -- col names, types, stats, missingness
  summary_text TEXT   -- LLM-generated description
  ```
- [ ] `dataset_analyses` table:
  ```sql
  id UUID PRIMARY KEY,
  dataset_id UUID REFERENCES datasets(id),
  user_id VARCHAR NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  user_question TEXT,
  analysis_plan JSONB,  -- tools run, parameters, steps
  results_json JSONB,   -- structured stats, aggregates
  charts_meta JSONB,    -- chart files in Spaces
  status VARCHAR(50),   -- 'running' | 'completed' | 'failed'
  error_message TEXT
  ```
- [ ] `dataset_insights` table:
  ```sql
  id UUID PRIMARY KEY,
  dataset_analysis_id UUID REFERENCES dataset_analyses(id),
  dataset_id UUID REFERENCES datasets(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  insight_summary TEXT,
  business_tags TEXT[]  -- e.g. ['revenue', 'retention']
  ```
- [ ] Add indexes on `dataset_id`, `user_id`, `created_at`

**Files:** `migrations/versions/d1_create_datasets_tables.py`

---

#### EPIC 2: Dataset Profiling & Summary

**Goal:** Compute schema, stats, human-readable summary for each dataset.

##### Task 2.1: Low-level profiling function
- [ ] Load CSV/Sheet into Pandas given `dataset_id`
- [ ] Infer types (int/float/date/string/categorical)
- [ ] Per column: `type`, `null_count`, `unique_count`, `min`, `max`, `mean`, `std`, sample values
- [ ] Return `profile_json` dict

**Files:** `bo1/data/profiler.py`

##### Task 2.2: Save profile to Postgres
- [ ] Repository: `create_dataset_profile(dataset_id, profile_json, summary_text)`
- [ ] Update `datasets.row_count` and `datasets.column_count`

**Files:** `bo1/state/repositories/dataset_repository.py`

##### Task 2.3: LLM-generated dataset summary
- [ ] Helper that calls LLM with `profile_json` (stats only, not raw rows)
- [ ] Prompt: "Summarise this dataset in 3-5 sentences for a business user."
- [ ] Store as `dataset_profiles.summary_text`

**Files:** `bo1/data/profiler.py`

##### Task 2.4: Expose `data_profile_dataset` as Claude tool
- [ ] Tool schema: Input `{ dataset_id }`, Output `{ profile_id, profile_json, summary_text }`
- [ ] Cache profile in Redis for quick reuse

**Files:** `bo1/tools/data_tools.py`

---

#### EPIC 3: Analysis Tools (Core Computation)

**Goal:** Let Claude describe analysis, execute in Python, get results + charts.

##### Task 3.1: Define `query_spec` format
- [ ] JSON schema for operations:
  ```json
  {
    "operation": "aggregate | filter | trend | compare | correlate",
    "group_by": ["column_name"],
    "metrics": [{"column": "revenue", "agg": "sum"}],
    "filters": [{"column": "status", "op": "eq", "value": "active"}]
  }
  ```
- [ ] Document examples in comments

**Files:** `bo1/data/query_spec.py`

##### Task 3.2: Implement `data_run_query` tool
- [ ] Input: `{ dataset_id, query_spec }`
- [ ] Load data (cache small datasets, DuckDB for large)
- [ ] Apply filters, group-bys, aggregations
- [ ] Return: `{ columns: [...], rows: [[...], [...]] }`

**Files:** `bo1/tools/data_tools.py`, `bo1/data/query_engine.py`

##### Task 3.3: Implement `data_generate_chart` tool
- [ ] Input: `{ dataset_id, chart_spec, result_table }`
- [ ] `chart_spec`: `{ type: "line|bar|pie", x: "column", y: "column" }`
- [ ] Generate PNG via matplotlib/plotly
- [ ] Upload to Spaces
- [ ] Return: `{ chart_url, chart_meta }`

**Files:** `bo1/tools/data_tools.py`, `bo1/data/chart_generator.py`

---

#### EPIC 4: Analysis Runs & Insight Storage

**Goal:** Store every analysis and summarise for future context.

##### Task 4.1: Implement `analysis_store_run` tool
- [ ] Input: `{ dataset_id, user_id, user_question, analysis_plan, results_json, charts_meta }`
- [ ] Create `dataset_analyses` row, set `status='completed'`
- [ ] Return: `{ analysis_id }`

##### Task 4.2: Implement `analysis_store_insight` tool
- [ ] Input: `{ analysis_id, insight_summary, business_tags }`
- [ ] Insert row in `dataset_insights`
- [ ] Return: `{ insight_id }`

##### Task 4.3: Implement `analysis_get_recent_context` tool
- [ ] Input: `{ dataset_id, limit }`
- [ ] Fetch last N insights
- [ ] Return: `{ insights: [{ created_at, insight_summary, business_tags }] }`

##### Task 4.4: Add Redis session helpers
- [ ] Tools: `session_state_set` / `session_state_get`
- [ ] Keys: `current_dataset_id`, `last_analysis_id`

**Files:** `bo1/tools/data_tools.py`, `bo1/state/repositories/dataset_repository.py`

---

#### EPIC 5: Orchestration & Smart Analyst Behavior

**Goal:** Teach Claude to chain tools and persist context.

##### Task 5.1: Create "Data Analyst Orchestrator" system prompt
- [ ] Instructions:
  - When dataset uploaded: call `data_profile_dataset` if no profile exists
  - When question asked:
    1. Call `analysis_get_recent_context` for past insights
    2. Decide on `data_run_query` calls using `query_spec`
    3. Call `data_generate_chart` if visual would help
    4. Summarise results in plain language
    5. Construct `analysis_plan` JSON
    6. Call `analysis_store_run` to persist
    7. Write insight summary + tags, call `analysis_store_insight`
  - Never: infer precise numbers without `data_run_query`; load full CSV into prompt

**Files:** `bo1/prompts/data_analyst.py`

##### Task 5.2: Define `answer_dataset_question` top-level tool
- [ ] Input: `{ dataset_id, user_id, question }`
- [ ] Forwards to Claude with orchestrator prompt + all tools
- [ ] Returns: `{ answer, chart_urls, analysis_id }`

**Files:** `backend/api/datasets.py`, `bo1/tools/data_tools.py`

##### Task 5.3: Connect to Bo1 meeting context
- [ ] After `answer_dataset_question`: push `insight_summary` into meeting context store
- [ ] Meetings can reference "latest data insight" from attached datasets

**Files:** `backend/api/datasets.py`, `bo1/graph/nodes/research.py`

---

#### EPIC 6: UI Integration

**Goal:** Simple but effective UI for beta users.

##### Task 6.1: Dataset management UI
- [ ] New page: `/data` or `/datasets`
- [ ] Features:
  - Upload CSV (drag-drop)
  - Add Google Sheet URL
  - List datasets with profile summary (rows, columns, date range)
  - Delete dataset

**Files:** `frontend/src/routes/(app)/data/+page.svelte`

##### Task 6.2: "Ask a question" panel
- [ ] Per dataset detail page:
  - Text area: "Ask a question about this data"
  - Show last few insights for context
  - On submit: call `answer_dataset_question`
  - Render: narrative answer, table snippet, chart images

**Files:** `frontend/src/routes/(app)/data/[id]/+page.svelte`, `frontend/src/lib/components/data/QuestionPanel.svelte`

##### Task 6.3: Link datasets into meetings
- [ ] Allow attaching datasets to a Bo1 meeting
- [ ] Meeting context includes: `dataset_profiles.summary_text`, recent `dataset_insights`
- [ ] Personas can reference dataset context

**Files:** `frontend/src/routes/(app)/meeting/new/+page.svelte`, `bo1/graph/state.py`

---

### 2. [P1-UI] UI/Layout Improvements

**Status**: NOT STARTED
**User Impact**: Poor UX drives users away; good UX builds trust and engagement
**Effort**: 1-2 weeks

#### Task 2.1: Design system audit
- [ ] Review current component consistency (buttons, cards, spacing)
- [ ] Create/document design tokens (colors, typography, spacing scale)
- [ ] Identify and fix inconsistent patterns

**Files:** `frontend/src/lib/styles/`, `frontend/src/lib/components/ui/`

#### Task 2.2: Navigation & information architecture
- [ ] Improve sidebar organization (group related items)
- [ ] Add "back to meeting" from actions detail
- [ ] Review and improve empty states across all pages
- [ ] Add loading skeletons for async content

**Files:** `frontend/src/lib/components/Sidebar.svelte`, `frontend/src/routes/(app)/+layout.svelte`

#### Task 2.3: Dashboard overhaul
- [ ] "Active actions needing attention" section with urgency indicators
- [ ] Progress overview visualization (completion rates, trends)
- [ ] Quick actions panel (start meeting, view actions, recent datasets)
- [ ] Onboarding checklist for new users

**Files:** `frontend/src/routes/(app)/dashboard/+page.svelte`

#### Task 2.4: Meeting page improvements
- [ ] Clearer phase progression indicator
- [ ] Better expert contribution layout (cards vs list)
- [ ] Improved synthesis/recommendation display
- [ ] Mobile-optimized meeting view

**Files:** `frontend/src/routes/(app)/meeting/[id]/+page.svelte`

#### Task 2.5: Actions page polish
- [ ] Filter/sort controls (by status, due date, meeting)
- [ ] Bulk actions (mark multiple complete)
- [ ] Better visual hierarchy in task cards
- [ ] Due date warnings (overdue, due soon)

**Files:** `frontend/src/routes/(app)/actions/+page.svelte`, `frontend/src/lib/components/actions/`

#### Task 2.6: Responsive design audit
- [ ] Test all pages on mobile, tablet, desktop
- [ ] Fix any layout issues found
- [ ] Ensure touch targets are adequate (44px minimum)
- [ ] Test with screen readers (basic accessibility)

---

### 3. [P1-STRIPE] Stripe Integration

**Status**: NOT STARTED
**User Impact**: Required for monetization; blocks tier-based features
**Effort**: 1-2 weeks

#### Task 3.1: Stripe account setup
- [ ] Create Stripe account, get API keys
- [ ] Define pricing tiers (Free, Pro, Enterprise?)
- [ ] Create Products and Prices in Stripe dashboard
- [ ] Add `STRIPE_*` env vars

#### Task 3.2: Backend integration
- [ ] Install `stripe` Python package
- [ ] Webhook endpoint: `POST /api/webhooks/stripe`
- [ ] Handle events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
- [ ] Store subscription status in `users` table

**Files:** `backend/api/billing.py`, `migrations/versions/s1_add_subscription_fields.py`

#### Task 3.3: Checkout flow
- [ ] Endpoint: `POST /api/v1/billing/create-checkout-session`
- [ ] Redirect user to Stripe Checkout
- [ ] Handle success/cancel redirects

**Files:** `backend/api/billing.py`

#### Task 3.4: Customer portal
- [ ] Endpoint: `POST /api/v1/billing/create-portal-session`
- [ ] Allow users to manage subscription (upgrade, downgrade, cancel)

#### Task 3.5: Frontend billing page
- [ ] Current plan display
- [ ] Upgrade/downgrade buttons
- [ ] Invoice history (from Stripe)
- [ ] Cancel subscription flow with confirmation

**Files:** `frontend/src/routes/(app)/settings/billing/+page.svelte`

#### Task 3.6: Tier enforcement
- [ ] Middleware to check user tier on protected routes
- [ ] Feature flags per tier (meeting limits, dataset limits, etc.)
- [ ] Graceful handling when limit reached

**Files:** `backend/api/middleware/tier.py`

---

### 4. [P1-EMAIL] Email Notifications & Waitlist

**Status**: NOT STARTED
**User Impact**: Re-engagement is critical for SaaS retention
**Effort**: 1 week

#### Task 4.1: Email service setup
- [ ] Choose provider (SendGrid, Postmark, Resend)
- [ ] Configure domain verification (SPF, DKIM)
- [ ] Add `EMAIL_*` env vars

#### Task 4.2: Transactional emails
- [ ] Welcome email on signup
- [ ] Meeting completed notification
- [ ] Action due reminder (24h before, on due date)
- [ ] Weekly digest (actions summary, meeting count)

**Files:** `bo1/email/templates/`, `bo1/email/sender.py`

#### Task 4.3: Waitlist management
- [ ] "X people joined waitlist" display on landing
- [ ] Trigger email when spot opens
- [ ] Admin UI to manage waitlist

**Files:** `backend/api/waitlist.py`, `frontend/src/routes/(marketing)/+page.svelte`

---

## P2: Medium Priority - Polish & Growth

### 1. [P2-PERF] Performance Phase 2

**Status**: PENDING (Phase 1 complete)
**Current**: 30s gaps reduced to 5-10s gaps

#### Task 1.1: Event batching
- [ ] Buffer events in 50ms windows during high-throughput
- [ ] Batch PostgreSQL inserts in single transaction
- [ ] Expected: 70% reduction in per-event DB roundtrips

**Files:** `backend/api/event_publisher.py`

#### Task 1.2: Priority-based event queuing
- [ ] Critical events (contribution, error) = priority 1
- [ ] Status events (working_status) = priority 10
- [ ] Process in priority order

#### Task 1.3: Subgraph stream writer
- [ ] Use LangGraph's `get_stream_writer()` for real-time emission
- [ ] Emit per-expert events during each sub-problem round
- [ ] Expected: Eliminates 3-5 min UI blackouts

**Files:** `bo1/graph/nodes/subproblems.py`

---

### 2. [P2-DASH] Dashboard Enhancements

**Status**: PARTIAL

#### Outstanding:
- [ ] "Active actions needing attention" section with urgency indicators
- [ ] Progress overview visualization (completion trends)

---

### 3. [P2-SKIP] Clarification Questions Toggle

**Status**: PARTIAL (skip button exists)

#### Outstanding:
- [ ] User preference/setting to disable pre-deliberation questions entirely
- [ ] Store in user preferences table
- [ ] Apply during meeting creation

---

### 4. [P2-SUMMARIZE] Summarization Improvements

**Status**: MOSTLY COMPLETE

#### Outstanding:
- [ ] Cap max sub-problems to reduce noise (limit to 3-4)

---

### 5. [P2-MENTOR] Mentor Mode

**Status**: DEFERRED → PLANNED
**User Impact**: Chat directly with AI expert, ongoing guidance
**Effort**: 1-2 weeks

#### Task 5.1: Mentor chat backend
- [ ] New endpoint: `POST /api/v1/mentor/chat`
- [ ] Input: `{ message, session_id?, dataset_id? }`
- [ ] Uses business context + recent insights as system prompt
- [ ] Streaming response via SSE

**Files:** `backend/api/mentor.py`

#### Task 5.2: Mentor persona selection
- [ ] User can choose from available personas
- [ ] Or "auto" mode that picks based on question
- [ ] Persona context injected into prompt

#### Task 5.3: Mentor chat UI
- [ ] Chat interface (similar to ChatGPT)
- [ ] Message history (stored in Redis, persisted to Postgres)
- [ ] Ability to reference meetings/actions/datasets

**Files:** `frontend/src/routes/(app)/mentor/+page.svelte`

#### Task 5.4: Context-aware responses
- [ ] Mentor has access to:
  - Business context
  - Recent meeting summaries
  - Dataset insights
  - Action statuses
- [ ] Can suggest creating meetings for complex decisions

---

### 6. [P2-ACTIONS] Action System Improvements

**Status**: PARTIAL

#### Task 6.1: Auto-update dependent actions
- [ ] When action closed (completed/killed), dependent actions auto-unblock
- [ ] Verify `action_repository.py:auto_unblock_dependents()` works
- [ ] Add UI refresh after status change

#### Task 6.2: Action replanning flow
- [ ] "What went wrong?" prompt when action marked failed
- [ ] Store outcome notes
- [ ] Suggest replanning via new meeting

---

## P3: Future - Enterprise & Scale Features

### 1. [P3-TEAMS] Workspaces & Teams

**User Impact**: Collaboration, enterprise sales
**Effort**: 3-4 weeks

#### Architecture:
```
Workspace
  ├── Members (users with roles)
  ├── Shared Meetings
  ├── Shared Datasets
  ├── Team Context (shared business info)
  └── Billing (per workspace)
```

#### Task 1.1: Database schema
- [ ] `workspaces` table (id, name, created_at, owner_user_id)
- [ ] `workspace_members` table (workspace_id, user_id, role)
- [ ] Add `workspace_id` FK to: meetings, datasets, actions, business_context
- [ ] Migration to add default personal workspace for existing users

#### Task 1.2: Authorization layer
- [ ] Middleware to check workspace membership
- [ ] Role-based permissions (owner, admin, member, viewer)
- [ ] Workspace switching in UI

#### Task 1.3: Invitation system
- [ ] Invite by email
- [ ] Accept/decline flow
- [ ] Pending invitations UI

#### Task 1.4: Workspace settings UI
- [ ] Members management
- [ ] Workspace billing (upgrade workspace plan)
- [ ] Workspace context (shared business info)

---

### 2. [P3-PROJECTS] Projects System

**User Impact**: Organize related meetings and actions
**Effort**: 2 weeks
**Depends on**: Workspaces (optional, can do without)

#### Architecture:
```
Project
  ├── Meetings (many)
  ├── Actions (many, or via meetings)
  ├── Sub-projects (many)
  └── AI-generated tags
```

#### Task 2.1: Database schema
- [ ] `projects` table (id, workspace_id, name, description, parent_project_id, ai_tags)
- [ ] Add `project_id` FK to meetings and actions
- [ ] Migration

#### Task 2.2: Project CRUD
- [ ] Create/read/update/delete endpoints
- [ ] AI tag generation on create/update
- [ ] Soft delete with cascade

#### Task 2.3: Project UI
- [ ] Projects list page
- [ ] Project detail (meetings, actions, sub-projects)
- [ ] Assign meeting to project during creation
- [ ] Filter actions/meetings by project

#### Task 2.4: Gantt filterable by project
- [ ] Add project filter to GlobalGanttChart
- [ ] Make Gantt accessible from actions tab

---

### 3. [P3-SEO] AI SEO Growth Engine

**User Impact**: Organic growth, content marketing
**Effort**: 2-3 weeks

#### Task 3.1: Content generation pipeline
- [ ] Topic research (trending business decisions)
- [ ] Article generation (Claude)
- [ ] SEO optimization (meta, structure)
- [ ] Auto-publish to blog

#### Task 3.2: Social posting
- [ ] LinkedIn integration
- [ ] Twitter/X integration
- [ ] Scheduled posting

#### Task 3.3: Performance tracking
- [ ] Track article views, engagement
- [ ] Learn from successful content
- [ ] Iterate on topics

---

### 4. [P3-OPS] AI Ops Self-Healing

**User Impact**: Reliability, reduced downtime
**Effort**: 2-3 weeks

#### Task 4.1: Error detection
- [ ] Monitor logs for patterns
- [ ] Anomaly detection in metrics
- [ ] Automated alerts

#### Task 4.2: Auto-recovery
- [ ] Known error → known fix mapping
- [ ] Automated restart procedures
- [ ] Escalation to human when needed

#### Task 4.3: Self-monitoring dashboard
- [ ] System health overview
- [ ] Recent incidents and resolutions
- [ ] Capacity planning

---

### 5. [P3-TIERS] Gated Features / Tier Plans

**User Impact**: Monetization, enterprise features
**Effort**: 1 week (after Stripe)
**Depends on**: Stripe integration

#### Task 5.1: Feature flags per tier
- [ ] Define tier → features mapping
- [ ] Free: 3 meetings/month, 1 dataset, basic actions
- [ ] Pro: unlimited meetings, 10 datasets, mentor mode
- [ ] Enterprise: workspaces, API access, priority support

#### Task 5.2: Usage tracking
- [ ] Track meetings created per month
- [ ] Track datasets uploaded
- [ ] Track API calls (if applicable)

#### Task 5.3: Limit enforcement
- [ ] Check limits before creating meeting/dataset
- [ ] Graceful upgrade prompts
- [ ] Admin override capability

#### Task 5.4: Pricing page
- [ ] Feature comparison table
- [ ] Clear CTAs for each tier
- [ ] FAQ section

---

### 6. [P3-ADMIN] Admin Improvements

#### Task 6.1: Admin impersonation
- [ ] Admin can "view as user" to see their dashboard/meetings/actions
- [ ] Admin overlay shows: costs, failures, debug info
- [ ] Audit log of impersonation sessions

#### Task 6.2: Feature request form
- [ ] In-app submission
- [ ] Admin dashboard to review/prioritize

#### Task 6.3: Report a problem flow
- [ ] In-app error reporting
- [ ] Auto-attach context (user, session, recent errors)
- [ ] Integration with issue tracker

---

## Remaining Cleanup (Low Effort)

- [ ] Add SSE connection test in deployment verification (complex, WebSocket client needed)
- [ ] Deployment drain period (stop new meetings before restart) - architectural change
- [ ] Improve sidebar organization
- [ ] Add "back to meeting" from actions detail
- [ ] Help/documentation pages
- [ ] Landing page SEO (meta tags, structured data)
- [ ] Footer pages audit (terms, privacy, about)

---

## Data Model Reference

```
Workspace (future)
  ├── Users (members)
  ├── Projects (many)
  ├── Meetings (many)
  ├── Datasets (many)
  └── Business Context

Projects
  ├── Meetings (many)
  ├── Actions (many)
  └── Sub-projects (many)

Meetings (sessions)
  ├── Projects (many)
  ├── Actions (many)
  └── Datasets (attached context)

Actions
  ├── Project (one, optional)
  ├── Sub-actions (many)
  └── Mentor assistance (future)

Datasets
  ├── Profiles (one)
  ├── Analyses (many)
  └── Insights (many)
```

---

## Key Files Reference

| Area | File |
|------|------|
| Event persistence | `backend/api/event_publisher.py` |
| Session/event saving | `bo1/state/repositories/session_repository.py` |
| Actions CRUD | `bo1/state/repositories/action_repository.py` |
| Meeting flow | `backend/api/event_collector.py` |
| Graph config | `bo1/graph/config.py` |
| Monitoring | `scripts/send_database_report.py` |

---

## Commands Reference

```bash
make pre-commit                    # Before any PR
make test                          # Run tests
uv run alembic upgrade head        # Apply migrations
uv run alembic revision -m "desc"  # Create migration
python scripts/send_database_report.py daily  # Manual report
```
