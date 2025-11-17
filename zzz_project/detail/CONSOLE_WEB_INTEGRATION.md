# Board of One - Console/Web Integration Strategy
**Dual-Mode Architecture: Console (Admin) + Web (Users)**

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Architecture Design
**Purpose**: Maintain console mode for admin/debug while building web mode for end users

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Console Mode (Admin/Debug)](#2-console-mode-admindebug)
3. [Web Mode (End Users)](#3-web-mode-end-users)
4. [Shared Backend](#4-shared-backend)
5. [Migration Path](#5-migration-path)
6. [What Can Be Built in Console Now?](#6-what-can-be-built-in-console-now)
7. [Console-to-Web Feature Parity](#7-console-to-web-feature-parity)

---

## 1. Architecture Overview

### 1.1 Dual-Mode Design

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                      │
├──────────────────────────────┬──────────────────────────────┤
│       Console/CLI Mode       │         Web Mode             │
│       (Admin/Debug)          │       (End Users)            │
│                              │                              │
│  - Rich/Textual (Python)     │  - SvelteKit 5 (Svelte 5)    │
│  - bo1/ui/console.py         │  - Browser-based             │
│  - Localhost/VPN only        │  - Public internet           │
│  - No auth required          │  - Supabase Auth required    │
│  - Full cost/token visibility│  - Cost metrics hidden       │
│  - Direct Redis/DB access    │  - API-mediated access       │
│  - Debugging tools visible   │  - User-friendly UX          │
│                              │                              │
└──────────────┬───────────────┴───────────────┬──────────────┘
               │                               │
               │                               │
        ┌──────┴────────┐             ┌────────┴───────┐
        │  FastAPI      │             │  SvelteKit     │
        │  Admin API    │             │  Public API    │
        │  /api/admin/* │             │  /api/v1/*     │
        └──────┬────────┘             └────────┬───────┘
               │                               │
               └───────────────┬───────────────┘
                               │
                ┌──────────────┴───────────────┐
                │     Bo1 Core (Python)        │
                │     - Deliberation logic     │
                │     - LLM orchestration      │
                │     - Agents (personas, etc.)│
                └──────────────┬───────────────┘
                               │
                ┌──────────────┴───────────────┐
                │       Data Layer             │
                │  - PostgreSQL (shared)       │
                │  - Redis (shared)            │
                │  - S3/Blob (shared)          │
                └──────────────────────────────┘
```

### 1.2 Key Principles

1. **Shared Backend**: Both modes use same Bo1 core, database, Redis
2. **Separate Entry Points**: Console = Python CLI, Web = SvelteKit SSR
3. **Different Access Levels**: Console = admin (full visibility), Web = user (scoped)
4. **Parallel Development**: Can build console features now, migrate to web later
5. **No Duplication**: Business logic in Bo1 core, UI layer is thin

---

## 2. Console Mode (Admin/Debug)

### 2.1 Current Implementation

**Stack**:
- **UI**: Rich/Textual (Python TUI framework)
- **API**: Direct Python imports (no HTTP, bo1/orchestration)
- **Auth**: None (localhost/VPN access only)
- **Deployment**: Makefile (`make run`, `make shell`)

**Features** (already built, v1):
- ✅ Problem input & clarification
- ✅ Sub-problem decomposition
- ✅ Persona selection
- ✅ Multi-round deliberation
- ✅ Voting & synthesis
- ✅ Markdown export
- ✅ Cost/token tracking (visible)
- ✅ Redis state inspection

**Console UI** (`bo1/ui/console.py`):
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()

# Display contribution
def display_contribution(contrib: ContributionMessage):
    panel = Panel(
        Markdown(contrib.content),
        title=f"{contrib.persona_name} ({contrib.contribution_type})",
        subtitle=f"Tokens: {contrib.token_count} | Cost: ${contrib.cost:.4f}",
        border_style=get_persona_color(contrib.persona_code)
    )
    console.print(panel)

# Display metrics (admin view)
def display_metrics(state: DeliberationState):
    table = Table(title="Session Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Cost", f"${state.total_cost:.4f}")
    table.add_row("Total Tokens", str(state.total_tokens))
    table.add_row("Cache Hit Rate", f"{state.cache_hits / (state.cache_hits + state.cache_misses) * 100:.1f}%")
    table.add_row("Convergence", f"{state.convergence_score:.2f}")

    console.print(table)
```

### 2.2 Admin-Only Features

**Cost Visibility**:
- Display cost per contribution (`$0.002`)
- Display total session cost (`$0.68`)
- Display cache savings (`Saved $0.15 via caching`)
- Display token breakdown (input: 12,000, output: 3,500)

**Debug Panel**:
- View raw LLM responses (thinking, XML tags)
- Inspect Redis state (`HGETALL session:12345`)
- View prompt construction
- Retry failed calls manually
- Force phase transitions

**Direct Database Access**:
```bash
# Console mode can query DB directly
make shell
>>> from bo1.state.redis_manager import RedisManager
>>> redis = RedisManager()
>>> redis.get_session("session-123")
```

### 2.3 When to Use Console Mode

**Use Console For**:
- ✅ Local development & testing
- ✅ Debugging deliberation logic
- ✅ Inspecting LLM responses
- ✅ Cost analysis (per-persona, per-round)
- ✅ Admin operations (manual session cleanup)
- ✅ Feature prototyping (faster than web)

**Don't Use Console For**:
- ❌ Production end-user sessions (use web)
- ❌ Multi-user scenarios (no auth)
- ❌ Mobile access (TUI not mobile-friendly)

---

## 3. Web Mode (End Users)

### 3.1 Planned Implementation

**Stack**:
- **Frontend**: SvelteKit 5 (Svelte 5 Runes)
- **Backend**: SvelteKit Server Endpoints + FastAPI (hybrid)
- **Auth**: Supabase Auth (social OAuth, email/password)
- **Deployment**: Railway/Render (MVP) → AWS ECS (production)

**Features** (to be built, v2):
- 🔄 Problem input (web form)
- 🔄 Sub-problem decomposition (visual cards)
- 🔄 Persona selection (grid view)
- 🔄 Live deliberation (WebSocket streaming)
- 🔄 Voting & synthesis (formatted report)
- 🔄 PDF export (styled)
- ❌ Cost/token tracking (hidden from users)
- ✅ Session management (dashboard)

**User-Facing UI** (No cost metrics):
- ✅ Session status (active, completed, archived)
- ✅ Progress indicators (Round 3/7, Phase: Deliberation)
- ✅ Convergence metrics (62% consensus)
- ❌ Token counts (hidden)
- ❌ Cost per contribution (hidden)
- ❌ Cache hit rates (hidden)

**Admin View in Web** (Special route: `/admin`):
- Requires admin role (not just any authenticated user)
- Shows cost metrics, token usage, cache rates
- Session inspection (full transcript + debug info)
- User management (view, anonymize, suspend)

### 3.2 User-Focused Features

**Simplified Metrics**:
- "High confidence recommendation" (instead of "0.85 confidence")
- "Strong consensus" (instead of "75% vote agreement")
- "Deliberation complete in 12 minutes" (instead of "12m 34s, 15,234 tokens")

**Social Sharing** (see next section):
- Share synthesis report on LinkedIn, Twitter
- Generate nicely formatted post with key insights
- Optional: Share public read-only link

**Landing Page** (see next section):
- Hero section with value prop
- How it works (3-step flow)
- Pricing tiers (Free, Pro, Enterprise)
- Testimonials (placeholder for MVP)
- CTA: "Start Free Deliberation"

---

## 4. Shared Backend

### 4.1 Bo1 Core (Python)

**Location**: `bo1/` module (unchanged from v1)

**Components**:
- `bo1/agents/` - Decomposer, FacilitatorAgent, PersonaSelectorAgent, etc.
- `bo1/orchestration/` - DeliberationOrchestrator
- `bo1/models/` - Pydantic models (DeliberationState, ContributionMessage, etc.)
- `bo1/prompts/` - Prompt composition functions
- `bo1/state/` - RedisManager, serialization

**Access Pattern**:
- **Console Mode**: Direct Python imports
  ```python
  from bo1.orchestration.deliberation import DeliberationOrchestrator
  orchestrator = DeliberationOrchestrator()
  await orchestrator.run_deliberation(session_id)
  ```

- **Web Mode**: Via API layer (FastAPI or SvelteKit endpoints)
  ```typescript
  // SvelteKit server endpoint
  import { spawnDeliberation } from '$lib/server/deliberation';
  export const POST = async ({ request }) => {
    const { session_id } = await request.json();
    await spawnDeliberation(session_id); // Spawns Python subprocess or calls FastAPI
    return json({ status: 'started' });
  };
  ```

### 4.2 Shared Database (PostgreSQL)

**Tables**:
- `users` - User accounts (Supabase auth linkage)
- `sessions` - Deliberation sessions (shared between modes)
- `contributions` - Expert contributions (shared)
- `votes` - Expert votes (shared)
- `synthesis_reports` - Final reports (shared)
- `personas` - 45 expert personas (shared)
- `embeddings` - pgvector embeddings (shared)
- `audit_log` - Access logs (shared)

**Access Control**:
- **Console Mode**: Direct SQL (psql, admin service role)
- **Web Mode**: Row-level security (RLS) policies (user can only see own sessions)

**Example**:
```sql
-- Console mode: See all sessions
SELECT * FROM sessions;

-- Web mode (RLS enforced): See only own sessions
SELECT * FROM sessions; -- Implicitly filtered by auth.uid()
```

### 4.3 Shared Redis

**Keys**:
- `session:{session_id}:state` - Session state (shared)
- `session:{session_id}:events` - Real-time events (web mode only)
- `ratelimit:{user_id}:sessions` - Rate limiting (web mode only)
- `cache:llm:{hash}` - LLM response cache (shared)

**Access**:
- **Console Mode**: Direct Redis commands (`redis.get()`, `redis.hgetall()`)
- **Web Mode**: Via RedisManager abstraction (same as console, but scoped by user_id)

---

## 5. Migration Path

### 5.1 Phase 1: Console Only (Current State)

**Status**: ✅ Complete (v1)

**Features**:
- Full deliberation pipeline (problem → synthesis)
- Cost tracking
- Markdown export
- Redis persistence

**Access**: Localhost only (`make run`)

### 5.2 Phase 2: Add Web UI (Parallel to Console)

**Status**: 🔄 In Design (this document)

**Steps**:
1. **Build SvelteKit frontend** (4-6 weeks)
   - Authentication (Supabase)
   - User dashboard
   - Session creation flow
   - Live deliberation view
   - Synthesis report display

2. **Add API layer** (2-3 weeks)
   - SvelteKit server endpoints (`/api/v1/*`)
   - WebSocket streaming
   - User-scoped access (RLS)
   - Rate limiting

3. **Deploy web app** (1 week)
   - Railway/Render deployment
   - SSL setup (Traefik)
   - Supabase Auth configuration
   - Stripe integration

**Coexistence**:
- Console mode continues to work (unchanged)
- Web mode uses same Bo1 core, database, Redis
- Both modes can be used simultaneously (admin uses console, users use web)

### 5.3 Phase 3: Web Becomes Primary

**Status**: 📅 Future (6-12 months)

**Transition**:
- 90%+ users use web mode
- Console reserved for admin/debugging
- Separate deployments (console on VPN, web public)

**Console Remains For**:
- Admin operations (user management, session cleanup)
- Debugging production issues
- Cost analysis & optimization
- Feature prototyping (faster than web iteration)

---

## 6. What Can Be Built in Console Now?

### 6.1 Realistic Console-Only Features (Near-Term)

**Week 4 Features** (Can build in console immediately):
1. ✅ **Hierarchical Context Management** (Days 16-17)
   - Background summarization (Haiku)
   - Old rounds = 100-token summaries, current round = full detail
   - Already has logging/metrics in console
   - **Console View**: Display summary vs full detail toggle

2. ✅ **Convergence Detection** (Days 22-23)
   - Semantic similarity, novelty tracking
   - Early stop triggers
   - **Console View**: Display convergence score, chart over rounds

3. ✅ **Problem Drift Detection** (Days 24-25)
   - Relevance scoring vs sub-problem goal
   - Facilitator redirects if drift detected
   - **Console View**: Display drift score, highlight off-topic contributions

4. ✅ **AI-First Quality Detection** (Day 26)
   - Haiku-based quality validator (enhancement over pattern-matching)
   - **Console View**: Display quality scores, moderator triggers

5. ✅ **External Research** (Day 27)
   - Web search integration (Brave/Tavily API)
   - Display research results in console
   - **Console View**: Display research snippets, sources

6. ✅ **Adaptive Round Limits** (Already partially built)
   - Complexity-based max rounds (simple=5, moderate=7, complex=10)
   - **Console View**: Display round progress bar, max rounds remaining

### 6.2 Features That Benefit from Web (Defer)

**Better in Web UI**:
1. ⏸ **Social Sharing** (LinkedIn, Twitter posts)
   - Requires web-based share buttons, OAuth
   - **Defer to web mode**

2. ⏸ **PDF Export with Styling**
   - Console can export markdown (already works)
   - Styled PDF requires web rendering (headless Chrome, Playwright)
   - **Defer to web mode**

3. ⏸ **Collaborative Sessions** (Read-only sharing)
   - Requires shareable URLs, auth
   - **Defer to web mode**

4. ⏸ **Visual Analytics** (Charts, graphs)
   - Console can show ASCII charts (Rich library)
   - Interactive charts better in web
   - **Defer to web mode** (but prototype in console with Rich)

5. ⏸ **Payment Integration** (Stripe)
   - No payments in console mode (admin-only)
   - **Defer to web mode**

### 6.3 Console-First Development Strategy

**Advantages**:
- ✅ **Faster iteration**: No frontend build time, no CSS tweaking
- ✅ **Focus on logic**: Core features without UI distractions
- ✅ **Easy debugging**: Print statements, breakpoints, direct DB access
- ✅ **Cost analysis**: See exact token/cost metrics during development

**Workflow**:
1. **Build feature in Bo1 core** (Python, business logic)
2. **Add console UI** (Rich/Textual, quick visualization)
3. **Test & validate** (local, with real LLM calls)
4. **Migrate to web** (SvelteKit UI, API endpoints)

**Example: Convergence Detection**
```
Week 1: Build convergence logic in bo1/orchestration/deliberation.py
Week 2: Add console UI to display convergence score, chart
Week 3: Test with 10+ real deliberations, tune thresholds
Week 4: Migrate to web UI (Svelte component, real-time chart)
```

---

## 7. Console-to-Web Feature Parity

### 7.1 Feature Matrix

| Feature | Console (v1) | Web (v2) | Notes |
|---------|--------------|----------|-------|
| **Problem Input** | ✅ Text prompt | 🔄 Web form | Console: immediate, Web: prettier |
| **Decomposition** | ✅ Table view | 🔄 Card view | Web adds visual editing |
| **Persona Selection** | ✅ List view | 🔄 Grid view | Web adds profile previews |
| **Deliberation** | ✅ Sequential display | 🔄 Real-time stream | Web adds WebSocket |
| **Voting** | ✅ Table view | 🔄 Card view | Web adds confidence bars |
| **Synthesis** | ✅ Markdown | 🔄 Styled HTML | Web adds PDF export |
| **Cost Metrics** | ✅ Full visibility | ❌ Hidden | Admin-only in web |
| **Token Tracking** | ✅ Per-contribution | ❌ Hidden | Admin-only in web |
| **Cache Metrics** | ✅ Hit rate % | ❌ Hidden | Admin-only in web |
| **Debug Panel** | ✅ Built-in | 🔄 `/admin` route | Web requires auth |
| **Session Management** | ✅ Redis CLI | 🔄 Dashboard | Web adds visual UI |
| **Export** | ✅ Markdown | 🔄 PDF, JSON | Web adds styling |
| **Social Sharing** | ❌ N/A | 🔄 LinkedIn, Twitter | Web-only |
| **Payments** | ❌ N/A | 🔄 Stripe | Web-only |
| **Multi-User** | ❌ Single user | ✅ Multi-tenant | Web adds RLS |

### 7.2 Console-Specific Advantages

**Keep in Console**:
1. **Direct DB Access**: `make shell` → query any table
2. **Redis Inspection**: `redis-cli` → inspect any key
3. **Manual Interventions**: Force phase transitions, retry LLM calls
4. **Cost Optimization**: See exact cost breakdown, tune prompts
5. **Debugging**: Breakpoints, print statements, stack traces
6. **Rapid Prototyping**: No frontend build, test logic instantly

**Don't Migrate**:
- Console mode is permanent admin tool
- Always faster for power users
- Better for debugging production issues

### 7.3 Web-Specific Advantages

**Web Only**:
1. **Social Sharing**: Share synthesis on LinkedIn, Twitter
2. **Collaborative Sessions**: Share read-only links
3. **Payment Integration**: Stripe subscriptions
4. **Mobile Access**: Responsive design, mobile-friendly
5. **Marketing**: Landing page, SEO, public demos
6. **User Onboarding**: Guided tours, tooltips
7. **Analytics**: Plausible/Fathom tracking (privacy-focused)

---

## 8. Implementation Recommendations

### 8.1 Near-Term (Next 4 weeks)

**Focus on Console**:
1. Complete Week 4 features in console mode
   - Hierarchical context (Days 16-17)
   - Convergence detection (Days 22-23)
   - Drift detection (Days 24-25)
   - AI-first quality detection (Day 26)
   - External research (Day 27)

2. Validate features with real use cases
   - Run 10+ deliberations per feature
   - Tune thresholds (convergence >0.85, drift <6, etc.)
   - Optimize prompts based on results

3. Document feature behavior
   - Update TASKS.md with learnings
   - Add feature flags if needed
   - Prepare migration notes for web

**Defer Web Development**:
- Focus on core Bo1 logic first
- Web UI can wait until features are validated
- Avoid building UI for half-baked features

### 8.2 Mid-Term (2-3 months)

**Start Web Development**:
1. Set up SvelteKit project (`web/` directory)
2. Integrate Supabase Auth
3. Build authentication flow (login, signup, OAuth)
4. Create dashboard (session list)
5. Implement session creation flow (problem input → decomposition)

**Parallel Console Use**:
- Admins continue using console for debugging
- Early adopters test web mode (beta)
- Both modes coexist, share backend

### 8.3 Long-Term (6-12 months)

**Web Becomes Primary**:
- 90%+ users on web mode
- Console reserved for admin/debug
- Separate deployments (console on VPN, web public)

**Feature Parity**:
- All console features available in web
- Admin panel in web (`/admin` route)
- Cost metrics visible to admins only

---

## 9. Deployment Architecture

### 9.1 Development (Now)

```
Developer Laptop
  ├── make run (console mode, localhost)
  ├── PostgreSQL (Docker Compose)
  ├── Redis (Docker Compose)
  └── Bo1 Core (Python, direct imports)
```

### 9.2 Staging (2-3 months)

```
Staging Server (Railway/Render)
  ├── Web App (SvelteKit, public URL)
  ├── Admin Console (FastAPI, VPN-only URL)
  ├── PostgreSQL (managed)
  ├── Redis (managed)
  └── Bo1 Core (shared Python module)
```

### 9.3 Production (6-12 months)

```
Production (AWS ECS/EKS)
  ├── Web App (SvelteKit, app.boardof.one)
  │   ├── Load Balancer (Traefik, 3 instances)
  │   └── Auto-scaling (CPU > 70%)
  ├── Admin Console (FastAPI, admin.boardof.one, VPN-only)
  │   └── Single instance (low traffic)
  ├── PostgreSQL (AWS RDS, Multi-AZ)
  ├── Redis (AWS ElastiCache, cluster mode)
  └── Bo1 Core (shared ECR image)
```

---

## 10. Summary & Recommendations

### 10.1 Key Takeaways

1. **Console mode is valuable long-term**: Don't deprecate, keep as admin tool
2. **Shared backend eliminates duplication**: Bo1 core used by both modes
3. **Build features in console first**: Faster iteration, easier debugging
4. **Migrate to web when validated**: Don't build UI for unproven features
5. **Different audiences**: Console for admins, web for end users

### 10.2 Realistic Console-Only Build (Next 4 Weeks)

**Can Build Now** (100% console):
- ✅ Hierarchical context management
- ✅ Convergence detection
- ✅ Problem drift detection
- ✅ AI-first quality detection
- ✅ External research integration
- ✅ Adaptive round limits (already partially built)

**Total**: 6 major features, all testable in console

**Defer to Web**:
- Social sharing (LinkedIn, Twitter)
- PDF export with styling
- Payment integration (Stripe)
- Landing page
- Public sessions

### 10.3 Development Priority

**Priority 1: Console Features** (4 weeks)
- Build all Week 4 features in console
- Validate with real deliberations
- Document learnings

**Priority 2: API Layer** (2 weeks)
- FastAPI admin endpoints
- SvelteKit server endpoints (basic)
- WebSocket streaming setup

**Priority 3: Web UI** (6-8 weeks)
- Authentication (Supabase)
- Dashboard & session management
- Deliberation view (real-time)
- Synthesis report

**Priority 4: Marketing & Payments** (4 weeks)
- Landing page
- Stripe integration
- Social sharing

**Total**: ~16-18 weeks to full web launch

---

**END OF CONSOLE/WEB INTEGRATION STRATEGY**

This document provides a clear path for maintaining console mode as an admin tool while building web mode for end users, with realistic timelines for what can be built in console now vs what requires web UI.
