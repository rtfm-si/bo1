# Board of One - Prioritized TODO

Last updated: 2025-12-08
Status: **Core Features Stable** - Focus on monetization and data platform

---

## Priority Framework

| Priority | Definition | Focus |
|----------|------------|-------|
| **P1** | Revenue & core value - monetization, key differentiators | Active |
| **P2** | Polish & growth - UX improvements, engagement | Next |
| **P3** | Scale features - enterprise, teams, automation | Backlog |

---

## P1: High Priority - Revenue & Core Value

### 1. [P1-DATA] Data Analysis Platform

**Status**: NOT STARTED
**Value**: Transforms Bo1 from one-off decisions to ongoing business intelligence
**Effort**: 3-4 weeks

#### Overview

```
User Upload → Storage (DO Spaces) → Profile → Claude Tools → Analysis → Insights → Meeting Context
```

Users upload CSV/Google Sheets, ask questions, get AI analysis that feeds into meeting context.

---

#### EPIC 1: Data Ingestion (Week 1)

**Goal**: Store files, register datasets.

##### 1.1 Storage Layer
```python
# bo1/storage/spaces.py
class SpacesClient:
    def upload_file(file_bytes: bytes, key: str) -> str: ...
    def get_file(key: str) -> bytes: ...
    def delete_file(key: str) -> bool: ...
```
- [ ] Implement DO Spaces wrapper (boto3 S3-compatible)
- [ ] Add `DO_SPACES_*` env vars to config
- [ ] Add retry logic and error handling

##### 1.2 Database Schema
```sql
-- migrations/versions/d1_create_datasets_tables.py

CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id VARCHAR NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'csv_upload' | 'google_sheet'
    source_location TEXT NOT NULL,    -- Spaces key or sheet URL
    row_count INTEGER,
    column_count INTEGER,
    file_size_bytes BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE dataset_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    profile_json JSONB NOT NULL,      -- schema, stats, samples
    summary_text TEXT,                -- LLM-generated description
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE dataset_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    user_question TEXT NOT NULL,
    analysis_plan JSONB,              -- tools, params, steps
    results_json JSONB,               -- aggregates, stats
    charts_meta JSONB,                -- chart files in Spaces
    status VARCHAR(50) DEFAULT 'running', -- running|completed|failed
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE dataset_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_analysis_id UUID REFERENCES dataset_analyses(id) ON DELETE CASCADE,
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    insight_summary TEXT NOT NULL,
    business_tags TEXT[],             -- ['revenue', 'retention']
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_datasets_owner ON datasets(owner_user_id);
CREATE INDEX idx_dataset_analyses_dataset ON dataset_analyses(dataset_id);
CREATE INDEX idx_dataset_insights_dataset ON dataset_insights(dataset_id);
```
- [ ] Create migration file
- [ ] Add soft delete indexes

##### 1.3 Ingestion Endpoints
```python
# backend/api/datasets.py

@router.post("/v1/datasets/upload_csv")
async def upload_csv(file: UploadFile, name: str, user: dict = Depends(get_current_user)):
    """Upload CSV, store in Spaces, create dataset record."""
    # Validate: size < 50MB, valid CSV headers
    # Upload to Spaces: datasets/{user_id}/{uuid}.csv
    # Insert into datasets table
    # Return: { dataset_id, name, row_count, column_count }

@router.post("/v1/datasets/from_sheet")
async def from_google_sheet(sheet_url: str, name: str, user: dict = Depends(get_current_user)):
    """Import from Google Sheets URL."""
    # Validate URL format
    # Store URL as source_location
    # Trigger async profile job
    # Return: { dataset_id, name, status: 'profiling' }

@router.get("/v1/datasets")
async def list_datasets(user: dict = Depends(get_current_user)):
    """List user's datasets with profile summaries."""

@router.delete("/v1/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, user: dict = Depends(get_current_user)):
    """Soft delete dataset."""
```
- [ ] Implement CSV upload with validation
- [ ] Implement Google Sheets integration (OAuth flow)
- [ ] Add list/delete endpoints

---

#### EPIC 2: Profiling & Summary (Week 1-2)

**Goal**: Auto-analyze uploaded data, generate human-readable summary.

##### 2.1 Profiler Engine
```python
# bo1/data/profiler.py

class DataProfiler:
    def profile(self, dataset_id: str) -> DatasetProfile:
        """Load data, compute stats, return profile."""
        df = self._load_dataframe(dataset_id)
        return DatasetProfile(
            columns=[self._profile_column(col, df[col]) for col in df.columns],
            row_count=len(df),
            column_count=len(df.columns),
            sample_rows=df.head(5).to_dict('records'),
        )

    def _profile_column(self, name: str, series: pd.Series) -> ColumnProfile:
        """Infer type, compute stats."""
        return ColumnProfile(
            name=name,
            inferred_type=self._infer_type(series),  # int|float|date|string|categorical
            null_count=series.isna().sum(),
            unique_count=series.nunique(),
            min=series.min() if series.dtype in ['int64', 'float64'] else None,
            max=series.max() if series.dtype in ['int64', 'float64'] else None,
            mean=series.mean() if series.dtype in ['int64', 'float64'] else None,
            sample_values=series.dropna().head(5).tolist(),
        )
```
- [ ] Implement DataFrame loading (CSV from Spaces, Sheets via API)
- [ ] Implement type inference (handle dates, currencies, percentages)
- [ ] Compute per-column statistics

##### 2.2 LLM Summary Generation
```python
# bo1/data/profiler.py

async def generate_summary(self, profile: DatasetProfile) -> str:
    """Generate 3-5 sentence business summary."""
    prompt = f"""
    Analyze this dataset profile and write a 3-5 sentence summary for a business user.
    Focus on: what data this represents, key metrics available, potential insights.

    Columns: {[c.name for c in profile.columns]}
    Row count: {profile.row_count}
    Column stats: {profile.columns}
    """
    return await llm.generate(prompt, max_tokens=200)
```
- [ ] Implement summary generation prompt
- [ ] Store in dataset_profiles.summary_text

##### 2.3 Claude Tool: `data_profile_dataset`
```python
# bo1/tools/data_tools.py

@tool
async def data_profile_dataset(dataset_id: str) -> dict:
    """Profile a dataset and return schema/stats."""
    # Check cache in Redis
    # If not cached, run profiler
    # Store profile in Postgres
    # Cache in Redis (1 hour TTL)
    return {"profile_id": ..., "profile_json": ..., "summary_text": ...}
```
- [ ] Implement as Claude tool
- [ ] Add Redis caching

---

#### EPIC 3: Query & Analysis (Week 2)

**Goal**: Let Claude query data and generate visualizations.

##### 3.1 Query Specification
```python
# bo1/data/query_spec.py

class QuerySpec(BaseModel):
    operation: Literal["aggregate", "filter", "trend", "compare", "correlate"]
    group_by: list[str] = []
    metrics: list[MetricSpec] = []  # [{column, agg: sum|avg|count|min|max}]
    filters: list[FilterSpec] = []  # [{column, op: eq|gt|lt|contains, value}]
    order_by: str | None = None
    limit: int = 100
```

##### 3.2 Query Engine
```python
# bo1/data/query_engine.py

class QueryEngine:
    def execute(self, dataset_id: str, query: QuerySpec) -> QueryResult:
        """Execute query against dataset."""
        df = self._load_data(dataset_id)

        # Apply filters
        for f in query.filters:
            df = self._apply_filter(df, f)

        # Apply aggregations
        if query.group_by:
            df = df.groupby(query.group_by).agg(...)

        return QueryResult(columns=..., rows=df.values.tolist())
```
- [ ] Implement filter/group/aggregate operations
- [ ] Add DuckDB backend for large datasets (>100K rows)
- [ ] Implement result pagination

##### 3.3 Chart Generator
```python
# bo1/data/chart_generator.py

class ChartGenerator:
    def generate(self, data: QueryResult, spec: ChartSpec) -> ChartResult:
        """Generate chart image, upload to Spaces."""
        fig = self._create_figure(data, spec)

        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150)

        # Upload to Spaces
        key = f"charts/{uuid4()}.png"
        url = spaces.upload_file(buf.getvalue(), key)

        return ChartResult(url=url, chart_type=spec.type)
```
- [ ] Implement line/bar/pie charts (matplotlib or plotly)
- [ ] Upload to Spaces, return URL
- [ ] Add chart metadata storage

##### 3.4 Claude Tools
```python
# bo1/tools/data_tools.py

@tool
async def data_run_query(dataset_id: str, query_spec: dict) -> dict:
    """Execute query against dataset."""
    return {"columns": [...], "rows": [[...], ...]}

@tool
async def data_generate_chart(dataset_id: str, chart_spec: dict, result_table: dict) -> dict:
    """Generate visualization from query results."""
    return {"chart_url": "...", "chart_type": "..."}
```
- [ ] Implement query tool
- [ ] Implement chart tool
- [ ] Add input validation and error handling

---

#### EPIC 4: Insight Storage (Week 2-3)

**Goal**: Persist analysis runs, extract reusable insights.

##### 4.1 Analysis Persistence
```python
# bo1/tools/data_tools.py

@tool
async def analysis_store_run(
    dataset_id: str,
    user_id: str,
    user_question: str,
    analysis_plan: dict,
    results_json: dict,
    charts_meta: dict | None = None
) -> dict:
    """Store completed analysis."""
    # Insert into dataset_analyses
    return {"analysis_id": ...}

@tool
async def analysis_store_insight(
    analysis_id: str,
    insight_summary: str,
    business_tags: list[str]
) -> dict:
    """Extract and store insight from analysis."""
    # Insert into dataset_insights
    return {"insight_id": ...}

@tool
async def analysis_get_recent_context(
    dataset_id: str,
    limit: int = 5
) -> dict:
    """Get recent insights for context."""
    # Fetch last N insights
    return {"insights": [...]}
```
- [ ] Implement storage tools
- [ ] Add context retrieval for follow-up questions

##### 4.2 Session State Helpers
```python
# bo1/tools/data_tools.py

@tool
async def session_state_set(key: str, value: str) -> dict:
    """Set session state (current_dataset_id, last_analysis_id)."""

@tool
async def session_state_get(key: str) -> dict:
    """Get session state value."""
```
- [ ] Implement Redis-backed session state

---

#### EPIC 5: Orchestration (Week 3)

**Goal**: Claude chains tools intelligently.

##### 5.1 Data Analyst System Prompt
```python
# bo1/prompts/data_analyst.py

DATA_ANALYST_PROMPT = """
You are a data analyst assistant. When the user asks about their data:

1. Check if dataset is profiled: call data_profile_dataset if no profile exists
2. Get context: call analysis_get_recent_context for past insights
3. Plan analysis: determine what queries will answer the question
4. Execute queries: call data_run_query with appropriate query_spec
5. Visualize if helpful: call data_generate_chart for trends/comparisons
6. Summarize: explain results in plain language
7. Store: call analysis_store_run and analysis_store_insight

RULES:
- Never infer precise numbers without querying
- Never load raw data into context (use profiles and queries)
- Always reference specific columns from the profile
- Generate charts for time series and comparisons
"""
```
- [ ] Create orchestrator prompt
- [ ] Test multi-step analysis flows

##### 5.2 Top-Level API
```python
# backend/api/datasets.py

@router.post("/v1/datasets/{dataset_id}/ask")
async def ask_question(
    dataset_id: str,
    question: str,
    user: dict = Depends(get_current_user)
):
    """Ask a question about a dataset."""
    # Invoke Claude with data analyst prompt + tools
    # Stream response via SSE
    return StreamingResponse(...)
```
- [ ] Implement question endpoint
- [ ] Add SSE streaming

##### 5.3 Meeting Context Integration
- [ ] When meeting starts, inject attached dataset insights into context
- [ ] Personas can reference "recent data analysis" in deliberation

---

#### EPIC 6: UI (Week 3-4)

**Goal**: User-friendly data management interface.

##### 6.1 Dataset List Page
```svelte
<!-- frontend/src/routes/(app)/data/+page.svelte -->
- Drag-drop CSV upload
- Google Sheets URL input
- Dataset cards: name, rows, columns, last analyzed
- Delete button (soft delete)
```
- [ ] Implement upload UI
- [ ] Implement list with cards

##### 6.2 Dataset Detail Page
```svelte
<!-- frontend/src/routes/(app)/data/[id]/+page.svelte -->
- Profile summary card
- Column schema table
- "Ask a question" chat interface
- Recent insights list
- Chart gallery
```
- [ ] Implement profile display
- [ ] Implement question chat
- [ ] Show analysis history

##### 6.3 Meeting Integration
```svelte
<!-- frontend/src/routes/(app)/meeting/new/+page.svelte -->
- "Attach datasets" selector
- Shows dataset summary in context preview
```
- [ ] Add dataset attachment to meeting creation

---

### 2. [P1-STRIPE] Stripe Integration

**Status**: STUBS EXIST (billing.py)
**Value**: Required for monetization
**Effort**: 1-2 weeks

Current state: Billing API exists with plan/usage endpoints, but no Stripe connection.

#### 2.1 Stripe Setup
- [ ] Create Stripe account, configure products/prices:
  - Free: $0/mo, 3 meetings
  - Starter: $29/mo, 20 meetings
  - Pro: $99/mo, unlimited
- [ ] Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` to env
- [ ] Install `stripe` package

#### 2.2 Webhook Handler
```python
# backend/api/billing.py

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)

    match event.type:
        case "checkout.session.completed":
            # Create/update subscription
        case "customer.subscription.updated":
            # Update user tier
        case "customer.subscription.deleted":
            # Downgrade to free
        case "invoice.payment_failed":
            # Send notification
```
- [ ] Implement webhook endpoint
- [ ] Handle key event types
- [ ] Add idempotency checks

#### 2.3 Checkout Flow
```python
@router.post("/v1/billing/create-checkout-session")
async def create_checkout(tier: str, user: dict = Depends(get_current_user)):
    """Create Stripe Checkout session."""
    session = stripe.checkout.Session.create(
        customer_email=user["email"],
        line_items=[{"price": PRICE_IDS[tier], "quantity": 1}],
        mode="subscription",
        success_url=f"{BASE_URL}/settings/billing?success=true",
        cancel_url=f"{BASE_URL}/settings/billing?canceled=true",
        metadata={"user_id": user["id"]},
    )
    return {"checkout_url": session.url}
```
- [ ] Implement checkout session creation
- [ ] Handle success/cancel redirects

#### 2.4 Customer Portal
```python
@router.post("/v1/billing/create-portal-session")
async def create_portal(user: dict = Depends(get_current_user)):
    """Create Stripe billing portal session."""
    # Get or create Stripe customer
    customer_id = await get_or_create_customer(user)
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{BASE_URL}/settings/billing",
    )
    return {"url": session.url, "available": True}
```
- [ ] Implement portal session creation
- [ ] Store stripe_customer_id in users table

#### 2.5 Tier Enforcement
```python
# backend/api/middleware/tier.py

async def check_meeting_limit(user_id: str) -> bool:
    """Check if user can create a meeting."""
    tier = get_user_tier(user_id)
    limit = TIER_LIMITS.get(tier)
    if limit is None:  # Unlimited
        return True
    count = get_monthly_meeting_count(user_id)
    return count < limit

# Apply in session creation
@router.post("/v1/sessions")
async def create_session(...):
    if not await check_meeting_limit(user_id):
        raise HTTPException(402, "Meeting limit reached. Upgrade your plan.")
```
- [ ] Implement tier checking middleware
- [ ] Add limit checks to session creation
- [ ] Add graceful upgrade prompts

#### 2.6 Frontend Updates
```svelte
<!-- frontend/src/routes/(app)/settings/billing/+page.svelte -->
- Show current plan prominently
- Upgrade/downgrade buttons → Checkout
- "Manage subscription" → Portal
- Usage bar (meetings used / limit)
```
- [ ] Add Checkout button integration
- [ ] Add Portal button (fix stub)
- [ ] Show upgrade prompts when near limit

---

### 3. [P1-UI] Critical UX Fixes

**Status**: PARTIAL
**Value**: Poor UX drives users away
**Effort**: 1 week

#### 3.1 Dashboard Overhaul
```svelte
<!-- frontend/src/routes/(app)/dashboard/+page.svelte -->
Current: Basic meeting list
Target: Action-oriented dashboard
```
- [ ] "Actions needing attention" section (overdue, due today)
- [ ] Progress visualization (completion trends)
- [ ] Quick actions panel (new meeting, view actions)
- [ ] New user onboarding checklist

#### 3.2 Navigation Improvements
- [ ] Sidebar: group related items (Decisions, Actions, Data)
- [ ] Add "← Back to meeting" from action detail
- [ ] Loading skeletons for async content

#### 3.3 Actions Page Polish
- [ ] Filter by status, due date, meeting
- [ ] Bulk actions (mark multiple complete)
- [ ] Due date warnings (overdue = red, due soon = amber)

---

### 4. [P1-EMAIL] Email Notifications

**Status**: NOT STARTED
**Value**: Re-engagement critical for retention
**Effort**: 1 week

#### 4.1 Setup
- [ ] Choose provider (Resend recommended - simple API)
- [ ] Configure domain (SPF, DKIM)
- [ ] Add `EMAIL_*` env vars

#### 4.2 Transactional Emails
```python
# bo1/email/sender.py

async def send_email(to: str, template: str, context: dict):
    """Send transactional email."""
    html = render_template(template, context)
    await resend.send(to=to, subject=..., html=html)
```
Templates needed:
- [ ] Welcome email (on signup)
- [ ] Meeting completed (summary + actions)
- [ ] Action due reminder (24h before)
- [ ] Weekly digest (actions summary)

---

## P2: Medium Priority - Polish & Growth

### 1. [P2-PERF] Performance Phase 2

**Status**: Phase 1 complete (30s gaps → 5-10s)
**Value**: Better real-time experience

Remaining work:
- [ ] Event batching: Buffer 50ms windows, batch Postgres inserts
- [ ] Priority queuing: Critical events (contribution) before status events
- [ ] Stream writer optimization: Per-expert events during sub-problem rounds

Files: `backend/api/event_publisher.py`, `bo1/graph/nodes/subproblems.py`

---

### 2. [P2-SKIP] Clarification Toggle

**Status**: Skip button exists
**Value**: Power users want to skip questions

- [ ] Add user preference: "Skip pre-meeting questions by default"
- [ ] Store in users table or preferences JSONB
- [ ] Apply during meeting creation

---

### 3. [P2-MENTOR] Mentor Mode

**Status**: PLANNED
**Value**: Ongoing AI guidance beyond meetings
**Effort**: 2 weeks

#### Overview
Chat directly with an AI expert mentor, using business context and past insights.

#### 3.1 Backend
```python
# backend/api/mentor.py

@router.post("/v1/mentor/chat")
async def mentor_chat(
    message: str,
    session_id: str | None = None,
    dataset_id: str | None = None,
    user: dict = Depends(get_current_user)
):
    """Chat with AI mentor."""
    # Build context from:
    # - Business context
    # - Recent meeting summaries
    # - Dataset insights (if attached)
    # - Action statuses
    # Stream response via SSE
```
- [ ] Implement chat endpoint with SSE
- [ ] Build context injection
- [ ] Store chat history (Redis → Postgres)

#### 3.2 Persona Selection
- [ ] Allow selecting mentor persona (CFO, CTO, etc.)
- [ ] Auto-select based on question topic

#### 3.3 UI
```svelte
<!-- frontend/src/routes/(app)/mentor/+page.svelte -->
- Chat interface (messages list + input)
- Persona selector
- Context panel (attached datasets, recent meetings)
```
- [ ] Implement chat UI
- [ ] Add persona picker
- [ ] Show context sources

---

### 4. [P2-ACTIONS] Action System Polish

**Status**: Core complete, polish needed

- [ ] "What went wrong?" prompt when marking action failed
- [ ] Suggest replanning via new meeting
- [ ] Better dependency visualization

---

## P3: Future - Enterprise & Scale

### 1. [P3-TEAMS] Workspaces & Teams

**Value**: Collaboration, enterprise sales
**Effort**: 3-4 weeks

Architecture:
```
Workspace
  ├── Members (users with roles: owner, admin, member, viewer)
  ├── Shared Meetings
  ├── Shared Datasets
  ├── Team Context
  └── Billing (per workspace)
```

Key tasks:
- [ ] Database schema (workspaces, workspace_members, FK on meetings/datasets)
- [ ] Authorization layer (workspace membership checks)
- [ ] Invitation system (email invite, accept/decline)
- [ ] Workspace switching UI
- [ ] Per-workspace billing

---

### 2. [P3-PROJECTS] Projects System

**Value**: Organize related work
**Effort**: 2 weeks

```
Project
  ├── Meetings (many)
  ├── Actions (many)
  └── Sub-projects (hierarchy)
```

- [ ] Projects CRUD
- [ ] Assign meetings/actions to projects
- [ ] Filter views by project
- [ ] Gantt chart per project

---

### 3. [P3-TIERS] Advanced Tier Features

**Depends on**: Stripe integration

- [ ] Feature flags per tier (datasets, mentor, API access)
- [ ] Usage tracking (meetings, analyses, API calls)
- [ ] Admin override capability
- [ ] Pricing page with comparison table

---

### 4. [P3-ADMIN] Admin Improvements

- [ ] Admin impersonation ("view as user")
- [ ] In-app feature request form
- [ ] In-app problem reporting (auto-attach context)

---

### 5. [P3-SEO] AI Content Engine

**Value**: Organic growth
**Effort**: 2-3 weeks

- [ ] Content generation pipeline (trending topics → Claude → blog)
- [ ] Social posting (LinkedIn, Twitter)
- [ ] Performance tracking and iteration

---

### 6. [P3-OPS] AI Ops Self-Healing

**Value**: Reliability
**Effort**: 2-3 weeks

- [ ] Error pattern detection
- [ ] Known error → known fix mapping
- [ ] Automated recovery procedures
- [ ] Self-monitoring dashboard

---

## Completed Work (Reference)

| Area | Completed Items |
|------|-----------------|
| **P0 Critical** | Data persistence (Redis retry), sub-problem validation, deployment health, ntfy monitoring |
| **P1 UX** | Gantt chart, mobile nav, breadcrumbs, working_status, soft delete, session filtering, admin counts |
| **P2 Features** | Kanban drag-drop, expert summaries UI, research UI, sample reports, SSE Phase 1 |
| **Meeting System** | Clarification flow, cost tracking, state recovery, context sufficiency detection |
| **Cleanup** | Synthesis labels, mobile layout, duplicate headers |
| **Actions** | Auto-unblock dependents, blocking/unblocking flow |
| **Billing** | Stub endpoints (plan, usage, portal) |
| **Sub-problems** | Capped at 4 max (was averaging 4.2) |

---

## Key Files Reference

| Area | File |
|------|------|
| Event persistence | `backend/api/event_publisher.py` |
| Session/event saving | `bo1/state/repositories/session_repository.py` |
| Actions CRUD | `bo1/state/repositories/action_repository.py` |
| Meeting flow | `backend/api/event_collector.py` |
| Graph config | `bo1/graph/config.py` |
| Billing | `backend/api/billing.py` |
| Stream writer | `bo1/graph/deliberation/subgraph/nodes.py` |

---

## Commands Reference

```bash
make up / shell / test / pre-commit
uv run alembic upgrade head
uv run alembic revision -m "desc"
python scripts/send_database_report.py daily
```
