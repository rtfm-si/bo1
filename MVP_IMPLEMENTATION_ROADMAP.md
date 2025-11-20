# Board of One - MVP Implementation Roadmap

**Timeline**: 15.5 weeks (110 days) - **Updated: 2025-11-20**
**Current Status**: Week 7 Complete ✅ - Production landing page live with design system, waitlist, and legal pages
**Next Phase**: Week 7-8 - Google OAuth + Action Tracking Lite (authenticate real users + action extraction)
**Target Launch**: Week 15 Day 110 (Public Beta / MVP) - **On track for closed beta with waitlist system**

---

## Executive Summary

This roadmap covers the complete path from Week 3 completion to **10/10 production-grade MVP launch**, integrating:

- **Week 3.5**: Database & infrastructure setup (PostgreSQL, Alembic, environment config) ✅
- **Weeks 4-5**: Console → LangGraph migration (unified architecture) + developer onboarding tools ✅
- **Week 6**: Web API adapter (FastAPI + SSE streaming) + Self-hosted Supabase Auth + Multi-sub-problem iteration ✅
- **Week 7**: Production landing page + design system + waitlist + legal pages + deployment infrastructure ✅
- **Week 7-8**: Google OAuth integration + Action Tracking Lite (NEW - 9 days)
- **Week 8-9**: Stripe payments + rate limiting + GDPR user rights
- **Week 9**: Production hardening + vendor outage contingency + cost anomaly detection + feature flags
- **Weeks 10-11**: Admin dashboard (monitoring, analytics, kill switches, ntfy.sh alerts)
- **Week 12**: Resend integration + email templates
- **Week 14**: Final QA, security audit, load testing (blue-green deployment already complete ✅)
- **Week 15**: Launch preparation + user documentation + business continuity planning

**Key Decisions**:

- ✅ **Unified LangGraph architecture** (console + web, NOT dual systems)
- ✅ **DigitalOcean deployment** (NOT Render, Railway, or Fly.io)
- ✅ **Self-hosted Supabase** (auth only, full control, no vendor lock-in)
- ✅ **Resend for emails** (transactional, developer-friendly)
- ✅ **ntfy.sh for admin alerts** (runaway sessions, cost reports)
- ✅ **100% confidence infinite loop prevention** (5-layer safety system)
- ✅ **10/10 Production Excellence** (vendor resilience, cost controls, zero-downtime deploys, business continuity)
- ✅ **NEVER trust user input** (validate, sanitize, test malicious inputs)
- ✅ **AI-generated content disclaimers** (all outputs labeled as learning/knowledge only)
- ✅ **Two-Layer UX Architecture** (visible: polished outputs, hidden: orchestration mechanics)
- ✅ **Outcome-Focused Positioning** (sell clarity/confidence/better decisions, NOT mechanisms)
- ✅ **Action Tracking Lite in MVP** (extract actions, set dates, simple dashboard - NOT full tracking)
- ✅ **Google OAuth in MVP** (real authentication, defer LinkedIn/GitHub to v2.0)
- ✅ **Design System First** (Week 7: comprehensive token system, 20+ components, light/dark themes)
- ✅ **Legal Pages Early** (GDPR-ready privacy/terms/cookies - brought forward from Week 14)
- ✅ **Closed Beta Launch Strategy** (waitlist + whitelist system for controlled beta access)

**Full Details**: See `zzz_project/FULL_ROADMAP_ARCHIVE.md` for complete task breakdowns, code examples, and validation checklists.

---

## 🔒 Security & Integration Testing Policy

**See**: `docs/TESTING.md` and `zzz_project/INTEGRATION_TEST_TEMPLATE.md` for comprehensive security testing requirements.

**Core Principles**:

- Input validation with Pydantic models (all user inputs)
- Malicious input handling (XSS, SQL injection, path traversal)
- Row-level security (RLS) enforced
- Rate limiting per tier
- Audit logging for security events

---

## Progress Tracking

| Week         | Phase                              | Status         | Tasks Complete     |
| ------------ | ---------------------------------- | -------------- | ------------------ |
| 1-3          | Console v1 Foundation              | ✅ Complete    | 228/228 (100%)     |
| 3.5          | Database & Infrastructure Setup    | ✅ Complete    | 35/35 (100%)       |
| 4-5          | LangGraph Migration                | ✅ Complete    | 215/215 (100%)     |
| 5 (Day 35)   | Week 5 Retrospective + Pre-commit  | ✅ Complete    | 17/17 (100%)       |
| 5 (Day 36.5) | Multi-Sub-Problem Iteration (Core) | ✅ Complete    | 83/83 (100%)       |
| 6 (Day 36)   | FastAPI Setup + Context Tables     | ✅ Complete    | 68/68 (100%)       |
| 6 (Day 42.5) | Backend Security & Code Quality    | ✅ Complete    | 31/31 (100%)       |
| 6            | Web API Adapter - FastAPI + SSE    | ✅ Complete    | 192/192 (100%)     |
| 7 (Days 43-49) | Web UI Foundation + Landing Page | ✅ Complete    | 89/42 (212%)       |
| 14 (Partial) | Legal Pages + Blue-Green Deployment | ✅ Complete   | 43/167 (26%)       |
| 7-8 (NEW)    | Google OAuth + Action Tracking Lite| 📅 Planned     | 0/62 (0%)          |
| 8-9          | Payments + Promotions + Rate Limiting + GDPR | 📅 Planned | 0/126 (0%)    |
| 9-10         | Production Hardening               | 🔄 In Progress | 22/210 (10%)       |
| 11-12        | Admin Dashboard                    | 📅 Planned     | 0/98 (0%)          |
| 13           | Resend Integration                 | 📅 Planned     | 0/42 (0%)          |
| 14           | QA + Security Audit + Deployment   | 🔄 In Progress | 43/167 (26%)       |
| 15           | Launch + Documentation             | 📅 Planned     | 0/112 (0%)         |
| **Total**    |                                    |                | **968/1699 (57%)** |

---

## Week 3.5 (Day 21): Database & Infrastructure Setup

**Status**: ✅ Complete - 35/35 tasks
**Goal**: Establish database schema, migrations, and environment configuration

**Summary**: PostgreSQL with pgvector, Alembic migrations, 15-table schema, RLS policies, persona seeding, environment configuration, Redis key patterns documented.

**Deliverables**:

- migrations/versions/001_initial_schema.py
- .env.example (25+ variables)
- docs/DATABASE_SCHEMA.md
- docs/REDIS_KEY_PATTERNS.md

---

## Week 4 (Days 22-28): LangGraph Console Migration - Part 1

**Status**: ✅ Complete - 56/56 tasks
**Goal**: Begin migrating console to LangGraph architecture with safety guarantees

**Completed**:

- Day 22: LangGraph setup, training, pre-commit hooks, one-command dev setup, code review guidelines
- Day 23: Graph state schema (DeliberationGraphState), v1↔v2 conversion functions, troubleshooting guide
- Day 24: Infinite loop prevention layers 1-3 (recursion limit, cycle detection, round counter)
- Day 25: Loop prevention layers 4-5 (timeout watchdog, cost kill switch), 5-layer documentation
- Day 26: Kill switches (user + admin), session manager, graceful shutdown
- Day 27: Basic graph implementation (decompose, select_personas, initial_round nodes)
- Day 28: Console adapter with pause/resume, benchmarking (v1 vs v2)

**Key Achievements**:

- ✅ 100% confidence loop prevention (5 layers)
- ✅ Pause/resume support with Redis checkpointing (7-day TTL)
- ✅ Console UX identical to v1 (hidden migration)
- ✅ Benchmark: <10% latency increase vs v1

**Deliverables**:

- bo1/graph/ module (state.py, nodes.py, routers.py, config.py, execution.py)
- bo1/graph/safety/ (loop_prevention.py, kill_switches.py)
- docs/CODE_REVIEW_GUIDELINES.md, docs/TROUBLESHOOTING.md

---

## Week 5 (Days 29-35): LangGraph Console Migration - Part 2

**Status**: ✅ Complete - 78/78 tasks
**Goal**: Complete console migration with full deliberation loop

**Completed**:

- Day 29: Facilitator node + routing (continue/vote/moderator/research)
- Day 30: Persona contribution + moderator nodes, multi-round loop
- Day 31: Vote + synthesis nodes, background summarizer (hierarchical context)
- Day 32: Checkpoint recovery + resume (pause at any node)
- Day 33: Cost tracking per phase (analytics module, CSV/JSON export)
- Day 34: Final validation + migration (v1 feature parity, documentation updates)
- Day 35: Retrospective + pre-commit (code quality, 59% test coverage)

**Key Achievements**:

- ✅ Full deliberation loop (decompose → personas → debate → vote → synthesis)
- ✅ Pause/resume from any checkpoint
- ✅ Phase-based cost tracking + analytics
- ✅ 95% integration test pass rate (243/255)

**Deliverables**:

- Complete graph implementation (all nodes, routers, analytics)
- zzz_project/WEEK5_RETROSPECTIVE.md
- zzz_project/LANGGRAPH_MIGRATION_COMPLETE.md

---

## Week 6 (Days 36-42): Web API Adapter - FastAPI + SSE

**Status**: Day 36 + 36.5 Complete ✅ | Days 37-42 In Progress 🔄
**Goal**: Web API serves LangGraph backend with real-time streaming + Multi-sub-problem iteration

### Day 36: FastAPI Setup + Health Checks + Context Tables

**Status**: ✅ Complete - 68/68 tasks

**Completed**:

- FastAPI application (backend/api/main.py, health.py, deliberation.py, context.py)
- Health check endpoints (/api/health, /api/health/db, /api/health/redis, /api/health/anthropic)
- Database schema: user_context, session_clarifications, research_cache (with pgvector embeddings)
- Self-hosted Supabase Auth setup (documented, disabled for MVP - ENABLE_SUPABASE_AUTH=false)
- Docker configuration (api service, hot reload)

**Key Tables**:

- `user_context` - Persistent business context (business_model, target_market, revenue, etc.)
- `session_clarifications` - Mid-deliberation Q&A logging
- `research_cache` - Semantic-cached external research (Voyage AI embeddings, 70-90% cost reduction)

**Deliverables**:

- backend/ directory structure
- migrations for context tables
- bo1/state/postgres_manager.py (context CRUD)
- bo1/llm/embeddings.py (Voyage AI voyage-3)
- supabase/README.md (OAuth setup guide)

### Day 36.5: Multi-Sub-Problem Iteration (CRITICAL GAP)

**Status**: ✅ Complete - 83/83 tasks
**Value**: Enable deliberation of ALL sub-problems (not just the first)

**Completed**:

- SubProblemResult model with expert_summaries field
- DeliberationGraphState extended (sub_problem_results, sub_problem_index)
- next_subproblem_node() - saves results, generates expert summaries, resets state, loops to next SP
- meta_synthesize_node() - integrates all sub-problem syntheses into unified recommendation
- META_SYNTHESIS_PROMPT_TEMPLATE - comprehensive integration prompt
- route_after_synthesis() - atomic optimization (1 SP skips meta-synthesis)
- Expert memory across sub-problems (experts "remember" earlier contributions)
- Console UI updates (sub-problem progress headers, meta-synthesis formatting)

**Graph Flow**:

```
decompose → select_personas → initial_round → facilitator → (persona|moderator|vote)
                                   ↓
                          check_convergence → (loop|vote)
                                   ↓
                               synthesize
                                   ↓
                    (next_subproblem → select_personas) OR meta_synthesis → END
```

**Expert Memory**:

- SummarizerAgent.summarize_expert_contributions() - 50-100 token per-expert summaries
- Injected into compose_persona_prompt() via expert_memory parameter
- Continuity across sub-problems (Maria in SP1 + SP2 builds on SP1 position)
- Cost: ~$0.0008 per expert summary (Haiku 4.5)

**Key Achievement**: System now deliberates ALL sub-problems (not just first), with proper iteration and meta-synthesis.

**Deliverables**:

- bo1/models/state.py (SubProblemResult)
- bo1/graph/nodes.py (next_subproblem_node, meta_synthesize_node)
- bo1/prompts/reusable_prompts.py (META_SYNTHESIS_PROMPT_TEMPLATE)
- bo1/agents/summarizer.py (expert memory functions)
- zzz_project/detail/DAY_36_5_IMPLEMENTATION_SUMMARY.md

### Days 37-42: Web API Streaming + Admin Endpoints (In Progress)

**Tasks** (see archived roadmap for details):

- Day 37: SSE streaming endpoints (/api/stream/deliberation/{session_id})
- Day 38: Session control endpoints (start, pause, resume, kill)
- Day 39: Context collection endpoints (user_context CRUD, info gaps)
- Day 40: Admin endpoints (session monitoring, metrics, kill switches)
- Day 41: API testing + documentation (OpenAPI, admin-only /admin/docs)
- Day 42: Week 6 retrospective + security review

---

## Week 7 (Days 43-49): Web UI Foundation + Landing Page + Design System

**Goal**: Production-ready landing page with design system and closed beta waitlist

**Status**: ✅ Complete - 89/42 tasks (212% - exceeded scope with design system, legal pages, and waitlist)

**Key Achievement**: Built comprehensive design system, landing page, and waitlist infrastructure - far beyond original "basic web UI" scope.

### Days 43-44: SvelteKit Setup + Design System (COMPLETE ✅)

**Value**: Frontend foundation with production-grade design system

#### SvelteKit Initialization
- [x] Create SvelteKit project with TypeScript
- [x] Install dependencies (@sveltejs/kit, svelte, vite, tailwindcss)
- [x] Configure for SSR + CSR (adapter-node)
- [x] Hot reload working in Docker

#### Directory Structure
- [x] Create route structure (/, /legal/*, /design-system)
- [x] Component organization (ui/, Header, Footer, CookieConsent, ThemeSwitcher)
- [x] Design system directory (lib/design/)

#### Tailwind CSS Setup
- [x] Install and configure Tailwind CSS
- [x] Configure `tailwind.config.js` with extended theme
- [x] Create `src/app.css` with custom utilities
- [x] Typography and spacing system

#### Design System (NEW - NOT in original roadmap)
- [x] **Design tokens** (`lib/design/tokens.ts`):
  - [x] Color system (9 brand colors + semantic colors)
  - [x] Typography scale (6 sizes, line heights)
  - [x] Spacing scale (12 levels, 0.25rem base)
  - [x] Shadow system (4 levels)
  - [x] Border radius (4 levels)
  - [x] Animation durations and easings
- [x] **Theme system** (`lib/design/themes.ts`):
  - [x] Light and dark themes
  - [x] CSS variable mapping
  - [x] Theme switcher component
  - [x] localStorage persistence

#### UI Component Library (NEW - 20+ components)
- [x] Layout: Card, Modal
- [x] Forms: Button, Input, Dropdown, Tabs
- [x] Feedback: Alert, Badge, Spinner, ProgressBar, Toast, Tooltip
- [x] Content: Avatar, InsightFlag, ContributionCard
- [x] Utilities: ColorSwatch, ShadowDemo, BorderRadiusDemo

#### Cookie Consent Banner
- [x] Install js-cookie + @types/js-cookie
- [x] Create CookieConsent.svelte component
- [x] Essential, Analytics, Marketing categories
- [x] Show banner on first visit
- [x] Respect user choice (analytics blocked if declined)
- [x] Store preference in cookie (365 day expiry)
- [x] Test: Analytics not loaded if user declines

#### Testing
- [x] SvelteKit dev server starts (port 5173)
- [x] Tailwind CSS working
- [x] TypeScript compilation working
- [x] Docker hot reload working
- [x] Design system demo page functional

**Deliverables**:
- frontend/ (SvelteKit + Vite + TypeScript)
- frontend/src/lib/design/ (tokens, themes)
- frontend/src/lib/components/ui/ (20+ components)
- frontend/src/routes/design-system/+page.svelte (demo)

---

### Days 45-47: Landing Page + Waitlist (COMPLETE ✅)

**Value**: Production landing page for closed beta launch

#### Landing Page (Hormozi Framework)
- [x] **Hero section**: "Better decisions, faster" value prop
- [x] **Metrics section**: 2x2 grid (6 persona perspectives, 3 rounds, 90% confidence, $0.10/decision)
- [x] **Why This Matters**: Pain point addressing
- [x] **Use Cases**: 4 decision types (fundraising, pricing, scaling, resources)
- [x] **How It Works**: 3-step process (Ask → Analysis → Action)
- [x] **Value Blocks**: 3 outcomes with hover examples
- [x] **Demo Screenshot**: "See It In Action" with real meeting view
- [x] **Before/After**: Decision quality comparison
- [x] **Social Proof**: 3 testimonials (placeholder)
- [x] **Beta Invite**: Waitlist signup form
- [x] **FAQ**: 5 questions with accordion
- [x] **Final CTA**: Bottom signup

#### Waitlist System (Backend + Frontend)
- [x] Database migration: `beta_whitelist` table
- [x] Pydantic models: WaitlistRequest, WaitlistResponse
- [x] API endpoint: POST /waitlist (backend/api/waitlist.py)
- [x] Email validation (EmailStr)
- [x] Duplicate prevention
- [x] Beta whitelist checking (BETA_WHITELIST env var)
- [x] Frontend form with validation
- [x] Success/error states
- [x] Integration with landing page

#### Header & Footer Components
- [x] Header.svelte (logo, nav, theme switcher)
- [x] Footer.svelte (links, legal, social)
- [x] Responsive design
- [x] Brand consistency

#### Legal Pages (BROUGHT FORWARD from Week 14)
- [x] Privacy Policy (/legal/privacy) - GDPR compliant
- [x] Terms of Service (/legal/terms) - User agreement
- [x] Cookie Policy (/legal/cookies) - Consent details
- [x] Footer links to all legal pages

#### Testing
- [x] Landing page loads and renders
- [x] Waitlist form submits successfully
- [x] Duplicate email handling works
- [x] Beta whitelist checking works
- [x] Legal pages accessible
- [x] Responsive design (mobile, tablet, desktop)
- [x] Theme switcher works (light/dark)
- [x] Cookie consent banner works

**Deliverables**:
- frontend/src/routes/+page.svelte (landing page)
- backend/api/waitlist.py (waitlist API)
- migrations/versions/8a5d2f9e1b3c_add_beta_whitelist.py
- frontend/src/routes/legal/ (privacy, terms, cookies)
- frontend/src/lib/components/ (Header, Footer, ThemeSwitcher)
- frontend/static/demo_meeting.jpg (demo screenshot)

---

### Days 48-49: Polishing + Documentation (COMPLETE ✅)

**Value**: Production-ready frontend

#### Copy & Content
- [x] Hormozi framework implementation (value-first)
- [x] Direct, operator-focused copy
- [x] Pain point addressing
- [x] Social proof integration
- [x] Clear CTAs throughout

#### Visual Polish
- [x] Border-y section separators
- [x] Gradient fade edges
- [x] Hover states and animations
- [x] Intersection observer for staggered reveals
- [x] Professional color palette
- [x] Consistent spacing and typography

#### Security (BROUGHT FORWARD from Week 14)
- [x] Comprehensive security audit (21/26 fixes)
- [x] XSS prevention (Pydantic validation)
- [x] SQL injection prevention (parameterized queries)
- [x] CSRF protection (SameSite cookies)
- [x] Rate limiting infrastructure
- [x] Input sanitization
- [x] Security headers

#### Production Infrastructure (BROUGHT FORWARD from Week 14)
- [x] Blue-green deployment scripts
- [x] Let's Encrypt SSL automation
- [x] Production docker-compose.prod.yml
- [x] Docker network configuration (postgres/redis hostnames)
- [x] Health checks (frontend, API, DB, Redis)
- [x] Deployment documentation

#### Documentation
- [x] Design system demo page
- [x] Component examples
- [x] README updates
- [x] Deployment guides

**Deliverables**:
- Polished landing page (0ce8391 commit)
- Security audit report
- Blue-green deployment system
- SSL automation
- Production-ready infrastructure

**Summary**: Week 7 delivered 212% of planned scope by including design system, waitlist, legal pages, security audit, and deployment infrastructure - positioning project for immediate closed beta launch.

---

## Week 7-8 (Days 45-54): Google OAuth + Action Tracking Lite

**Goal**: Real user authentication + Post-deliberation action tracking

**Status**: 0/62 tasks complete

**Timeline**: 9 days total (4 days OAuth + 5 days Actions)

**Value**: Enables production launch with real users + differentiates from "advice-only" AI tools

---

### Days 45-48: Google OAuth Integration (4 days)

**Value**: Replace `test_user_1` with real authentication

#### Day 45-46: Backend Auth Flow

**Tasks**:
- [ ] Verify Supabase GoTrue running (`docker-compose up -d`)
- [ ] Test Google OAuth credentials in `.env`
- [ ] Create OAuth callback endpoint: `backend/api/auth.py`
- [ ] Implement JWT verification middleware (already exists in `backend/api/middleware/auth.py`)
- [ ] Create user on first sign-in (link to trial tier)
- [ ] Update `get_current_user()` to use JWT instead of hardcoded user

**Deliverables**:
- `backend/api/auth.py` - OAuth callback handling
- Updated `backend/api/middleware/auth.py` - JWT verification
- Test suite: `tests/test_auth_oauth.py`

**Validation**:
- [ ] Test: Google OAuth flow completes
- [ ] Test: JWT verification works
- [ ] Test: User created on first sign-in
- [ ] Test: User linked to trial tier
- [ ] Test: Invalid JWT rejected (401)
- [ ] Test: Expired JWT rejected (401)

#### Day 47-48: Frontend Auth UI

**Tasks**:
- [ ] Create sign-in page: `frontend/src/routes/(auth)/login/+page.svelte`
- [ ] "Sign in with Google" button (OAuth redirect)
- [ ] OAuth callback handler: `frontend/src/routes/(auth)/callback/+page.svelte`
- [ ] Store JWT in httpOnly cookies
- [ ] Add auth check to protected routes
- [ ] Create auth store: `frontend/src/lib/stores/auth.ts`
- [ ] Add sign-out functionality

**Deliverables**:
- Sign-in page with Google OAuth button
- Callback handler (exchange code for JWT)
- Auth middleware for protected routes
- Sign-out flow

**Validation**:
- [ ] Test: Sign-in redirects to Google
- [ ] Test: Callback stores JWT in cookie
- [ ] Test: Protected routes redirect to /login if not authenticated
- [ ] Test: Sign-out clears cookie and redirects
- [ ] Test: JWT refresh works (before expiry)

**Notes**:
- LinkedIn and GitHub OAuth deferred to v2.0
- Email/password auth disabled for MVP (OAuth only)

---

### Days 50-54: Action Tracking Lite (5 days)

**Value**: Extract actions from synthesis, user commits with target dates, simple tracking dashboard

**Full Implementation**: See `zzz_project/detail/ACTION_TRACKING_LITE_IMPLEMENTATION.md`

#### Day 50-51: Backend + Database (2 days)

**Tasks**:
- [ ] Create migration: `migrations/versions/XXX_add_actions_lite.py`
- [ ] Create Pydantic models: `bo1/models/actions.py`
- [ ] Create API endpoints: `backend/api/actions.py`
  - [ ] POST `/api/actions/extract` - AI extraction (Haiku 4.5)
  - [ ] POST `/api/actions` - Save actions
  - [ ] GET `/api/actions` - List user actions
  - [ ] DELETE `/api/actions/{id}` - Delete action
  - [ ] PUT `/api/actions/{id}` - Update action
- [ ] Register router in `backend/api/main.py`
- [ ] Write unit tests: `tests/test_actions_api.py`

**Database Schema**:
```sql
CREATE TABLE actions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  description TEXT NOT NULL,
  target_date DATE NOT NULL,
  priority INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

**Validation**:
- [ ] Run migration: `alembic upgrade head`
- [ ] Test: Extract actions from synthesis
- [ ] Test: Save actions (user owns session)
- [ ] Test: List actions (sorted by target date)
- [ ] Test: Delete action (ownership check)
- [ ] Test: Update action (edit description, change date)
- [ ] Test: Authorization (user cannot access other user's actions)

#### Day 52-53: Frontend (2 days)

**Tasks**:
- [ ] Create component: `frontend/src/lib/components/ActionExtractor.svelte`
  - [ ] Display AI-extracted actions
  - [ ] Allow edit descriptions
  - [ ] Set target dates (date picker)
  - [ ] Add/remove actions
  - [ ] Save or skip flow
- [ ] Create dashboard: `frontend/src/routes/(app)/actions/+page.svelte`
  - [ ] List all actions (sorted by target date)
  - [ ] Filter: All, Upcoming, Overdue
  - [ ] Show overdue count/warning
  - [ ] Link to deliberation
  - [ ] Delete action
- [ ] Add TypeScript types: `frontend/src/lib/types.ts`
- [ ] Integrate into session page (show after synthesis)

**Validation**:
- [ ] Test: Action extractor appears after synthesis
- [ ] Test: Add/remove/edit actions
- [ ] Test: Save actions (API call)
- [ ] Test: Dashboard loads all actions
- [ ] Test: Filters work (upcoming, overdue)
- [ ] Test: Delete action from dashboard
- [ ] Test: Mobile responsive

#### Day 54: Integration + Testing (1 day)

**Tasks**:
- [ ] E2E test: `tests/e2e/test_actions_lite.py`
  - [ ] Extract → edit → save → list → delete flow
  - [ ] Authorization checks
  - [ ] Edge cases (no synthesis, empty actions)
- [ ] Manual testing (real LLM calls)
- [ ] Performance test (100+ actions)
- [ ] Documentation: `docs/ACTIONS_LITE.md`
- [ ] Update roadmap progress

**Validation**:
- [ ] E2E tests pass
- [ ] Action extraction cost: ~$0.002 per deliberation
- [ ] No N+1 query issues (dashboard loads fast)
- [ ] All edge cases handled gracefully

**NOT Included** (defer to v2.0):
- Status tracking (in_progress, blocked, completed)
- Reminders & notifications
- Replanning deliberations
- Progress reports
- Dependencies & templates

---

## Week 8-9 (Days 55-63): Payments + Rate Limiting + GDPR + Promotions

**Goal**: Stripe subscriptions, promotions system, rate limiting, and GDPR compliance working

**Status**: 0/126 tasks complete (98 original + 28 promotions)

### Day 50-51: GDPR User Rights Implementation

**Goal**: Implement data export, account deletion, and data retention policies

#### Data Export Endpoint (GDPR Art. 15)

- [ ] Create endpoint: GET /api/v1/user/export
- [ ] Export user data as JSON:
- [ ] Test: Verify complete data export

#### Account Deletion Endpoint (GDPR Art. 17)

- [ ] Create endpoint: DELETE /api/v1/user/delete
- [ ] Implement anonymization (NOT hard delete):
- [ ] Keep aggregate analytics (anonymized)
- [ ] Log deletion request (audit trail)
- [ ] Send confirmation email (optional, if user still has access)
- [ ] Test: Verify GDPR compliance

#### Data Retention Policy

- check data retention policy for financial and fraud compliance etc. 365 days seems too short

* [ ] Default retention: 365 days (configurable by user)
* [ ] User setting: Configure retention period (365d, 730d, indefinite)
* [ ] Cleanup job: Archive sessions >365 days old
* [ ] Document retention policy in privacy policy

**Validation**:

- [See TESTING.md for test requirements]

- [ ] **Data export completeness**: Verify ALL user data included (sessions, contributions, votes, audit logs)
- [ ] **Anonymization verification**: After deletion, verify PII truly unrecoverable (not just flagged)
- [ ] **Export format validation**: JSON schema valid, no binary data, max 100MB
- [ ] **Authorization**: User A cannot export User B's data
- [ ] **Rate limiting**: Max 1 export request per 24 hour (prevent abuse)
- [ ] **Deletion cascade**: Verify related data anonymized (sessions, contributions)
- [ ] **Audit logging**: Data export/deletion logged with IP, timestamp, user agent
- [ ] **Malicious input**: Test with email containing SQL injection, script tags

**Deliverables**:

---

### Day 55-56: Promotions System (Backend + Database)

**Goal**: Flexible promotion system for goodwill gestures, discounts, and bonus deliberations

**Value**: Critical for early-stage customer success and "oops" scenarios

**Full Spec**: See `zzz_project/detail/PROMOTIONS_SYSTEM_DESIGN.md`

#### Day 55: Database + Models (1 day)

**Database Schema**:
- [ ] Create migration: `migrations/versions/XXX_add_promotions.py`
  - [ ] `promotions` table (reusable templates)
  - [ ] `user_promotions` table (applied to users)
  - [ ] Indexes for performance
  - [ ] RLS policies
  - [ ] Constraints (promo_type, application_type, status)

**Tables**:
```sql
-- promotions: Reusable templates (e.g., "50% off for 6 months")
-- user_promotions: Applied promotions per user (tracks usage, expiry)
```

**Pydantic Models**:
- [ ] Create `bo1/models/promotions.py`
  - [ ] `Promotion` - Template model
  - [ ] `UserPromotion` - Applied promotion model
  - [ ] `AddPromotionRequest` - Admin request
  - [ ] `PromotionUsage` - Usage tracking

**Seed Data**:
- [ ] Common promotion templates:
  - [ ] "Goodwill +5 deliberations" (one-time)
  - [ ] "Goodwill +10 deliberation bank" (total_additional)
  - [ ] "50% off for 6 months" (recurring_periods)
  - [ ] "20% off forever" (recurring_forever)
  - [ ] "£10 off this month" (one_time)

**Validation**:
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify tables created
- [ ] Test model validation (promo_type, value, application_type)
- [ ] Seed data inserted successfully

---

#### Day 56: Backend Logic + API Endpoints (1 day)

**Core Logic**:
- [ ] Create `backend/services/promotions.py`
  - [ ] `check_deliberation_allowance()` - Check base + promo limits
  - [ ] `consume_promo_deliberation()` - Decrement credits after use
  - [ ] `apply_promotions_to_invoice()` - Calculate discounted amount
  - [ ] `get_active_promotions()` - Get user's active promos
  - [ ] `expire_promotions()` - Background job (daily cron)

**Discount Application Order** (Important!):
```python
# 1. £ off first (fixed amount)
final = base_amount - amount_off
final = max(final, 0)  # Floor at £0

# 2. % off second (on remaining amount)
percent = min(total_percent_off, 100)  # Cap at 100%
final = final - (final * percent / 100)
```

**Admin API Endpoints**:
- [ ] Create `backend/api/admin/promotions.py`
  - [ ] `GET /admin/users/{email}/promotions` - View user's promos
  - [ ] `POST /admin/users/{email}/promotions` - Add promo to user
  - [ ] `DELETE /admin/users/{email}/promotions/{id}` - Remove promo
  - [ ] `GET /admin/promotions/templates` - List all templates

**User API Endpoints**:
- [ ] `GET /api/promotions/available` - User can see available codes
- [ ] `POST /api/promotions/apply` - User applies promo code

**Integration with Deliberation Flow**:
- [ ] Update `start_deliberation()` to check promo allowance
- [ ] Update `complete_deliberation()` to consume promo credits
- [ ] Update tier limit checks to include promo bonuses

**Integration with Stripe Billing**:
- [ ] Update invoice creation to apply promo discounts
- [ ] Add promo details to invoice metadata
- [ ] Decrement promo periods on billing cycle

**Testing**:
- [ ] Unit tests: `tests/test_promotions.py`
  - [ ] Test deliberation limit calculation
  - [ ] Test discount application (£ then %)
  - [ ] Test promo expiry logic
  - [ ] Test credit consumption (FIFO)
- [ ] Integration tests:
  - [ ] Test deliberation with promo bonus
  - [ ] Test invoice with multiple discounts
  - [ ] Test promo expiry on billing cycle

**Validation**:
- [ ] Test: User with base limit 10 + promo +5 = 15 effective limit
- [ ] Test: Base £25, promo £5 off + 50% off = £10 final
- [ ] Test: Promo expires after N periods
- [ ] Test: Draw-down bank decrements correctly
- [ ] Test: Negative invoice prevented (floor at £0)
- [ ] Test: % discount capped at 100%
- [ ] Test: Admin cannot apply same promo twice (if max_uses_per_user=1)

**Deliverables**:
- `migrations/versions/XXX_add_promotions.py`
- `bo1/models/promotions.py`
- `backend/services/promotions.py`
- `backend/api/admin/promotions.py`
- `tests/test_promotions.py`

---

### Day 57: Promotions Admin UI (Frontend)

**Goal**: Admin can lookup users and manage promotions via UI

**Admin Dashboard Page**:
- [ ] Create `frontend/src/routes/(admin)/admin/users/[email]/promotions/+page.svelte`
  - [ ] User lookup (by email)
  - [ ] Display: Current tier, renewal date, usage stats
  - [ ] List active promotions
  - [ ] List promotion history (expired, cancelled)
  - [ ] "Add Promotion" button → modal
  - [ ] "Remove Promotion" button (per promo)

**Add Promotion Modal**:
- [ ] Create `frontend/src/lib/components/admin/AddPromotionModal.svelte`
  - [ ] Select from template dropdown (common promos)
  - [ ] OR create custom (type, value, duration)
  - [ ] Enter reason (required, for audit trail)
  - [ ] Preview impact (e.g., "Limit increases from 10 to 15")
  - [ ] Confirm and apply

**Promotion Card Component**:
- [ ] Create `frontend/src/lib/components/admin/PromotionCard.svelte`
  - [ ] Display: Type, value, application type
  - [ ] Show: Remaining credits/periods, expiry date
  - [ ] Applied by/date, reason
  - [ ] Remove button (with confirmation)

**TypeScript Types**:
- [ ] Add to `frontend/src/lib/types.ts`
  - [ ] `Promotion`
  - [ ] `UserPromotion`
  - [ ] `PromotionTemplate`

**User Lookup**:
- [ ] Search bar: Enter email → fetch user details
- [ ] Display: User summary card
- [ ] Navigate to promotions tab

**Testing**:
- [ ] Test: Search user by email
- [ ] Test: View active promotions
- [ ] Test: Add promotion (select template)
- [ ] Test: Add promotion (create custom)
- [ ] Test: Remove promotion (with confirmation)
- [ ] Test: View promotion history
- [ ] Test: Mobile responsive

**Validation**:
- [ ] Admin can lookup any user by email
- [ ] Active promotions display correctly
- [ ] Add promotion updates user limits immediately
- [ ] Remove promotion reverts limits
- [ ] Audit trail shows who/when/why

**Deliverables**:
- `frontend/src/routes/(admin)/admin/users/[email]/promotions/+page.svelte`
- `frontend/src/lib/components/admin/AddPromotionModal.svelte`
- `frontend/src/lib/components/admin/PromotionCard.svelte`

---

### Day 58: Promotions Integration Testing

**Goal**: End-to-end testing of promotions system

**E2E Tests**:
- [ ] Create `tests/e2e/test_promotions_flow.py`
  - [ ] Test: Admin adds +5 deliberations promo
  - [ ] Test: User starts deliberation (uses promo credit)
  - [ ] Test: Promo credits decrement correctly
  - [ ] Test: User exceeds limit after promo exhausted
  - [ ] Test: Admin adds 50% discount
  - [ ] Test: Invoice applies discount correctly
  - [ ] Test: Promo expires after N periods
  - [ ] Test: Multiple promos stack (£ then %)

**Manual Testing Scenarios**:
- [ ] Scenario 1: "Oops" goodwill gesture
  - [ ] Admin gives user +5 deliberations
  - [ ] User immediately sees increased limit
  - [ ] User completes deliberation, credits decrement
- [ ] Scenario 2: Beta discount
  - [ ] User applies code "BETA50"
  - [ ] 50% discount applied for 6 months
  - [ ] Invoice shows reduced amount
  - [ ] After 6 months, discount expires
- [ ] Scenario 3: Deliberation bank
  - [ ] Admin gives 50 deliberations (total_additional)
  - [ ] User uses 10 deliberations over 3 months
  - [ ] Bank shows 40 remaining
  - [ ] No expiry date

**Background Jobs Testing**:
- [ ] Test: Daily cron expires promotions
- [ ] Test: Monthly billing decrements periods_remaining
- [ ] Test: Exhausted promos marked as status='exhausted'

**Performance Testing**:
- [ ] Load test: 1000 users with active promos
- [ ] Query performance: Get active promotions (<50ms)
- [ ] Invoice calculation: Apply 5 promos (<100ms)

**Documentation**:
- [ ] Update `docs/ADMIN_GUIDE.md` - Promotions section
- [ ] Update `docs/API.md` - Admin endpoints
- [ ] Create `docs/PROMOTIONS_EXAMPLES.md` - Common scenarios

**Validation**:
- [ ] All E2E tests pass
- [ ] No N+1 query issues
- [ ] Admin UI workflow smooth (<3 clicks to add promo)
- [ ] Audit trail complete (who, when, why)

**Deliverables**:
- `tests/e2e/test_promotions_flow.py`
- `docs/ADMIN_GUIDE.md` (updated)
- `docs/PROMOTIONS_EXAMPLES.md`

---

### Day 59: Stripe Integration Setup

**Value**: Accept payments for subscriptions

#### Stripe Account Setup

- [ ] Create Stripe account at stripe.com
- [ ] Create products

#### Environment Configuration

- [ ] Add Stripe keys to `.env`
- [ ] Add to frontend `.env`

#### Stripe Client (Backend)

- [ ] Install Stripe SDK
- [ ] Create `backend/integrations/stripe.py`

#### Database Update

- [ ] Add Stripe fields to `users` table

#### Testing

- [ ] Test: Stripe client works
- [ ] Test: Can create checkout session

**Validation**:

- [See TESTING.md for test requirements]

#### Rate Limiting Implementation

- [ ] Install rate limiting library: `uv add slowapi redis`
- [ ] Create rate limiter service (backend/services/rate_limiter.py)
- [ ] Add middleware to check user tier and apply limits
- [ ] Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
- [ ] Redis backend for distributed rate limiting
- [ ] Create rate limit exceeded endpoint (429 response)
- [ ] Add rate limiting to all API endpoints:

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 53: Checkout Flow Implementation

**Value**: Users can upgrade to Pro

#### Pricing Page

- [ ] Create `src/routes/(app)/pricing/+page.svelte`

#### Checkout Endpoint

- [ ] Create `backend/api/checkout.py`
- [ ] Frontend: Redirect to Stripe Checkout

#### Success/Cancel Handlers

- [ ] Create `src/routes/(app)/billing/success/+page.svelte`
- [ ] Create `src/routes/(app)/billing/cancel/+page.svelte`

#### Testing

- [ ] Test: Pricing page displays
- [ ] Test: Checkout flow works
- [ ] Test: Cancel flow works

**Validation**:

- [See TESTING.md for test requirements]

#### Stripe Customer Portal

- [ ] Add `POST /api/v1/billing/portal` endpoint
- [ ] Add "Manage Billing" button to dashboard

#### Testing

- [ ] Test: Webhook signature validation
- [ ] Test: Subscription created webhook
- [ ] Test: Subscription deleted webhook
- [ ] Test: Customer portal works

**Validation**:

- [See TESTING.md for test requirements]

- [ ] **Signature validation**: Reject webhook with invalid signature (CRITICAL)
- [ ] **Replay attack prevention**: Reject webhook with old timestamp (>5 min)
- [ ] **Unknown event types**: Gracefully handle future Stripe events
- [ ] **Malicious payload**: Test with crafted JSON (SQL injection, script tags)
- [ ] **Idempotency**: Process same webhook twice, verify idempotent
- [ ] **Race conditions**: Two webhooks for same subscription arrive simultaneously
- [ ] **Database consistency**: Verify subscription status matches Stripe after webhook
- [ ] **Audit logging**: All webhooks logged with event type, status, timestamp

---

### Day 55: Resend Email Integration

**Value**: Send transactional emails (welcome, receipts)

#### Resend Account Setup

- [ ] Create Resend account at resend.com

#### Environment Configuration

- [ ] Add Resend variables to `.env`

#### Email Service

- [ ] Install Resend SDK
- [ ] Create `backend/services/email.py`

#### Email Templates

- [ ] Create `backend/services/email_templates.py`

#### Testing

- [ ] Test: Resend API works
- [ ] Test: Welcome email sends
- [ ] Test: Payment receipt sends

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 56: Email Triggers + Pre-commit

**Value**: Emails sent automatically on key events

#### Self-Hosted Supabase Auth Webhook (Welcome Email)

- [ ] Create database trigger for new user signups
- [ ] Create `backend/api/webhooks/auth.py`
- [ ] Alternative: Use HTTP webhook endpoint directly

#### Payment Receipt Email (Stripe Webhook)

- [ ] Update `backend/api/webhooks/stripe.py`

#### Code Quality

- [ ] Run pre-commit checks
- [ ] Fix all issues
- [ ] Ensure test coverage >90%

#### Documentation

- [ ] Update `README.md`
- [ ] Create `zzz_project/WEEK8_PAYMENTS_EMAIL_SUMMARY.md`

**Validation**:

- [See TESTING.md for test requirements]

- [ ] ✅ Stripe integration works (test mode)
- [ ] ✅ Resend emails deliver successfully
- [ ] ✅ Webhooks handle all events correctly
- [ ] ✅ All tests pass

---

---

## Week 9 (Days 57-63): Production Hardening + Monitoring

**Goal**: System is production-ready with monitoring, alerts, and guardrails

**Status**: 0/70 tasks complete

### Day 57: Runaway Session Detection

**Value**: Detect and alert on sessions consuming too many resources

#### Detection Metrics

- [ ] Create `backend/services/monitoring.py`

#### Alert Triggers

- [ ] Create alert thresholds

#### Admin Resume/Restart Capability

- [ ] Create `backend/api/admin/sessions.py`

#### Background Monitoring Task

- [ ] Create `backend/services/background_tasks.py`

#### Testing

- [ ] Test: Runaway detection works
- [ ] Test: Auto-kill works
- [ ] Test: False positives rare

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 58: ntfy.sh Alert Integration

**Value**: Admin receives real-time alerts for critical events

#### ntfy.sh Setup

- [ ] Create ntfy.sh topic
- [ ] Add to `.env`

#### Alert Service

- [ ] Create `backend/services/alerts.py`

#### Alert Templates

- [ ] Define alert formats

#### Integration

- [ ] Update `RunawayDetector`
- [ ] Update error handlers

#### Testing

- [ ] Test: ntfy.sh receives alerts
- [ ] Test: Priority levels work
- [ ] Test: Alert rate limiting

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 59: Cost Analytics Dashboard (Admin)

**Value**: Admin visibility into spending patterns

#### Cost Aggregation

- [ ] Create `backend/services/analytics.py`

#### Admin Endpoint

- [ ] Add `GET /api/admin/analytics/cost`
- [ ] Add `GET /api/admin/analytics/cost/trend`
- [ ] Add `GET /api/admin/analytics/sessions/expensive`

#### Console Display (Admin CLI)

- [ ] Create `scripts/admin_cost_report.py`

#### Testing

- [ ] Test: Cost summary correct
- [ ] Test: Cost trend works
- [ ] Test: Top sessions accurate

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 60: Rate Limiting (Per-Tier)

**Value**: Prevent abuse, enforce subscription limits

#### Rate Limit Configuration

- [ ] Define tier limits in `backend/config.py`

#### Rate Limiter

- [ ] Create `backend/middleware/rate_limit.py`

#### Apply to Endpoints

- [ ] Add middleware to session creation
- [ ] Add to deliberation start

#### User-Facing Errors

- [ ] Return helpful error messages

#### Testing

- [ ] Test: Free tier enforced (5 sessions/month)
- [ ] Test: Pro tier enforced (50 sessions/month)
- [ ] Test: Concurrent sessions enforced
- [ ] Test: Rate limit reset works

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 61: Health Checks + Graceful Shutdown

**Value**: Production reliability (readiness probes, zero-downtime deploys)

#### Advanced Health Checks

- [ ] Update `backend/api/health.py`

#### Graceful Shutdown

- [ ] Update `backend/api/main.py`

#### Deployment Configuration

- [ ] Create `k8s/deployment.yaml` (for DigitalOcean Kubernetes)

#### Testing

- [ ] Test: Readiness probe fails when Redis down
- [ ] Test: Liveness probe always succeeds
- [ ] Test: Graceful shutdown works

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

#### Vendor Outage Contingency Plans

**Value**: System resilience when third-party services fail

- [ ] Document degraded mode operation (what works when vendors down?)
- [ ] Create vendor status monitoring
- [ ] Integrate status page APIs (for external vendors only)
- [ ] Create fallback strategies
- [ ] Test degraded mode (disable each vendor, verify UX)

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

#### Cost Anomaly Detection & Budget Controls

**Value**: Prevent unexpected cost spikes

- [ ] Implement per-user cost tracking (real-time)
- [ ] Set budget thresholds per tier
- [ ] Create cost anomaly detection
- [ ] Implement auto-pause on budget exceeded
- [ ] Admin dashboard: Cost per user (sortable, filterable)
- [ ] Test: Exceed budget, verify auto-pause

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

#### Feature Flags for Gradual Rollout

**Value**: Deploy risky features safely with instant rollback

- [ ] Install feature flag library: `uv add launchdarkly-server-sdk` (or use simple Redis-based)
- [ ] Create simple feature flag service (backend/services/feature_flags.py)
- [ ] Implement feature flags for risky features:
- [ ] Admin UI: Toggle feature flags (on/off/percentage rollout)
- [ ] Wrap risky code paths with flags
- [ ] Test: Verify flags work (on/off/percentage)

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

#### Service Level Indicators & Objectives

**Value**: Define and measure service quality promises

- [ ] Define SLIs (what to measure)
- [ ] Set SLOs (targets)
- [ ] Document SLAs (user promises)
- [ ] Create SLO monitoring dashboard (Grafana)
- [ ] Alerting rules for SLO breaches
- [ ] Create error budget tracking

**Validation**:

- [See TESTING.md for test requirements]

#### Request Logging Middleware

- [ ] Create `backend/middleware/logging.py`

#### Error Logging

- [ ] Update error handlers
- [ ] Add to all `except` blocks

#### Log Aggregation (Future)

- [ ] Document log aggregation setup (for production)

#### Testing

- [ ] Test: Structured logs output JSON
- [ ] Test: Context propagates correctly
- [ ] Test: Errors logged with stack traces

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 63-64: Production Monitoring & Observability

**Goal**: Implement comprehensive monitoring with Prometheus, Grafana, and structured logging

#### Prometheus Metrics Instrumentation

- [ ] Install: `uv add prometheus-fastapi-instrumentator`
- [ ] Instrument FastAPI app (backend/api/main.py)
- [ ] Add custom metrics:
- [ ] Test: Verify metrics at http://localhost:8000/metrics

#### Grafana Dashboards

- [ ] Setup Grafana (Docker or cloud)
- [ ] Add Prometheus data source
- [ ] Create 4 dashboards:

#### Alerting Rules

- [ ] Configure Prometheus alerting rules:
- [ ] Test: Trigger test alert

#### Structured Logging

- [ ] Configure structured JSON logging (backend/utils/logging.py)
- [ ] Add context fields: session_id, user_id, trace_id, request_id
- [ ] Log all API requests (middleware)
- [ ] Log all LLM calls (with cost)

#### Log Aggregation

- [ ] Setup Grafana Loki (or CloudWatch Logs if AWS)
- [ ] Configure log shipping (promtail or Docker log driver)
- [ ] Retention: 30 days
- [ ] Test: Query logs by session_id in Grafana

#### Audit Logging

- [ ] Middleware: Log all API requests
- [ ] Log authentication events (login, logout, token refresh)
- [ ] Log admin actions (kill session, view user data)
- [ ] Log GDPR requests (export, delete)
- [ ] Retention: 7 years (compliance requirement)

#### Security Headers Implementation

- [ ] Add security headers middleware (backend/api/middleware/security.py)
- [ ] Apply middleware to FastAPI app
- [ ] Test: Verify headers present

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

- [ ] ✅ Infinite loop prevention tested (100% confidence)
- [ ] ✅ Runaway detection works (alerts sent)
- [ ] ✅ Rate limiting enforced (per-tier)
- [ ] ✅ Health checks work (Kubernetes probes)
- [ ] ✅ Logging structured (ready for aggregation)
- [ ] ✅ Prometheus metrics exposed
- [ ] ✅ Grafana dashboards working
- [ ] ✅ Security headers implemented

---

## Week 10-11 (Days 64-77): Admin Dashboard

**Goal**: Web-based admin dashboard for monitoring and control

**Status**: 0/98 tasks complete

### Day 64: Admin Dashboard Setup (SvelteKit)

**Value**: Foundation for admin monitoring UI

#### Route Structure

- [ ] Create admin routes in frontend
- [ ] Route layout: `src/routes/(admin)/+layout.svelte`

#### Admin Auth Middleware

- [ ] Create `src/lib/auth/admin.ts`

#### Admin API Client

- [ ] Create `src/lib/api/admin.ts`

#### Testing

- [ ] Test: Admin routes require admin role
- [ ] Test: Admin API client works

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Highlight new sessions (since last poll)
- [ ] Fade out completed sessions

#### Session Details Modal

- [ ] Create `SessionDetailsModal.svelte`

#### Testing

- [ ] Test: Active sessions page loads
- [ ] Test: Live updates work
- [ ] Test: Session details modal works

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Create charts:

#### Export Functionality

- [ ] Add "Export CSV" button

#### Testing

- [ ] Test: Cost analytics page loads
- [ ] Test: Charts render
- [ ] Test: CSV export works

**Validation**:

- [See TESTING.md for test requirements]
- [ ] **Admin auth required**: Non-admin cannot access user management (403)
- [ ] **Search injection**: Test search with SQL injection, XSS attempts
- [ ] **Tier change authorization**: Only admin can change user tiers
- [ ] **Ban cascade**: Verify banning user prevents login, kills active sessions
- [ ] **Delete triggers GDPR**: Verify delete calls anonymization function
- [ ] **Audit trail**: Tier changes, bans, deletes logged with admin_id
- [ ] **Impersonation security**: Verify impersonation requires second confirmation
- [ ] **Stripe link validation**: Verify customer_id link goes to correct Stripe account

---

### Day 68: Kill Switches (Admin UI)

**Value**: Admin can terminate runaway sessions from UI

#### Kill Session Action

- [ ] Add "Kill" button to active sessions table

#### Kill All Sessions (Emergency)

- [ ] Add "Kill All Sessions" button (top-right, admin only)

#### Audit Trail

- [ ] Display kill history

#### Testing

- [ ] Test: Kill session works
- [ ] Test: Kill all works
- [ ] Test: Audit trail works

**Validation**:

- [See TESTING.md for test requirements]
- [ ] **Admin auth required**: Non-admin cannot access kill endpoints (403)
- [ ] **API key validation**: Invalid X-Admin-Key rejected (403)
- [ ] **Kill reason required**: Cannot kill without providing reason (422)
- [ ] **Audit trail**: All kills logged with admin_id, session_id, reason, timestamp
- [ ] **Double confirmation**: Kill all requires "KILL ALL" typed exactly
- [ ] **Idempotency**: Killing already-killed session returns 200 (not 404)
- [ ] **Checkpoint preservation**: Verify checkpoint saved before kill
- [ ] **User notification**: User receives email/notification when session killed by admin

---

### Day 69: Alert Configuration (ntfy.sh UI)

**Value**: Admin can configure alert thresholds from UI

#### Alert Settings Page

- [ ] Create `src/routes/(admin)/admin/settings/alerts/+page.svelte`

#### Alert History

- [ ] Create `src/routes/(admin)/admin/alerts/history/+page.svelte`

#### Test Alert

- [ ] Add "Send Test Alert" button

#### Testing

- [ ] Test: Alert settings page loads
- [ ] Test: Can edit thresholds
- [ ] Test: Test alert works

**Validation**:

- [See TESTING.md for test requirements]

## Week 12 (Days 78-84): Email Templates + Final Integrations

**Goal**: Complete Resend integration with all email templates

**Status**: 0/42 tasks complete

### Day 78: Welcome Email Template

**Value**: Onboard new users with helpful email

#### Template Design

- [ ] Create HTML email template
- [ ] Create plain text version (fallback)
- [ ] Test rendering in email clients (Gmail, Outlook, Apple Mail)

#### Implementation

- [ ] Update `backend/services/email_templates.py`
- [ ] Test email sending

**Validation**:

- [See TESTING.md for test requirements]

#### Unsubscribe Link

- [ ] Add unsubscribe link to all emails

#### Testing

- [ ] Test: Preferences page works
- [ ] Test: Unsubscribe link works
- [ ] Test: Emails respect preferences

**Validation**:

- [See TESTING.md for test requirements]
- [ ] **Token validation**: Reject unsubscribe with invalid/expired JWT token
- [ ] **Token tampering**: Reject modified token (e.g., changed user_id)
- [ ] **Authorization**: User A cannot unsubscribe User B via token manipulation
- [ ] **Replay attacks**: Reject reused unsubscribe token (one-time use)
- [ ] **Preferences persistence**: Verify unsubscribe persists after server restart
- [ ] **Email respect**: After unsubscribe, verify no emails sent (integration test)
- [ ] **GDPR compliance**: Unsubscribe link in ALL email templates
- [ ] **Malicious input**: Test with XSS in preferences JSON

---

### Day 84: Week 12 Polish + Pre-commit

**Value**: Email system complete and tested

#### Email Testing

- [ ] Test all email templates
- [ ] Test in multiple email clients
- [ ] Verify deliverability

#### Code Quality

- [ ] Run pre-commit checks
- [ ] Fix all issues
- [ ] Ensure test coverage >90%

#### Documentation

- [ ] Update `README.md`
- [ ] Create `zzz_project/WEEK12_EMAIL_COMPLETE.md`

**Validation**:

- [See TESTING.md for test requirements]

## Week 13 (Days 85-91): QA + Security Audit

**Goal**: Production-ready system, security audited, load tested

**Status**: 0/56 tasks complete

### Day 85: Load Testing

**Value**: Verify system handles production load

#### Load Test Scenarios

- [ ] Scenario 1: Normal load
- [ ] Scenario 2: Peak load
- [ ] Scenario 3: Sustained load

#### Load Testing Tool

- [ ] Install Locust
- [ ] Create `tests/load/locustfile.py`

#### Results Analysis

- [ ] Collect metrics:
- [ ] Identify bottlenecks
- [ ] Optimize hot paths

#### Testing

- [ ] Test: Normal load passes
- [ ] Test: Peak load passes
- [ ] Test: Sustained load passes

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 86: Security Audit - Authentication

**Value**: Verify auth system secure

#### Auth Security Checklist

- [ ] Session security
- [ ] OAuth security
- [ ] Password security (if email/password enabled)
- [ ] Rate limiting

#### Penetration Testing

- [ ] Test: Session fixation attack
- [ ] Test: CSRF attack
- [ ] Test: Session hijacking
- [ ] Test: Brute force login

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 88: Security Audit - Infrastructure

**Value**: Verify infrastructure secure

#### Infrastructure Security Checklist

- [ ] Network security
- [ ] Secrets management
- [ ] Logging
- [ ] Monitoring

#### Dependency Scanning

- [ ] Scan Python dependencies
- [ ] Scan npm dependencies
- [ ] Fix critical vulnerabilities (upgrade packages)

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 89: GDPR Compliance Audit

**Value**: Verify legal compliance

#### GDPR Checklist

- [ ] Data minimization
- [ ] User rights
- [ ] Data retention
- [ ] Data processing agreements (DPAs)
- [ ] Privacy policy

#### Testing

- [ ] Test: User can export data
- [ ] Test: User can delete account
- [ ] Test: User can opt-out of emails

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Create test file: `tests/e2e/user_flows.spec.ts`

#### Critical Flows

- [ ] Test: User signup and login
- [ ] Test: Create deliberation
- [ ] Test: Pause and resume
- [ ] Test: Upgrade to Pro
- [ ] Test: Admin dashboard

#### Run Tests

- [ ] Run E2E tests
- [ ] Generate HTML report

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 91: Privacy Policy, Terms, CI/CD & Deployment Setup

**Goal**: Create legal documents, automation pipeline, and deployment infrastructure

#### Privacy Policy & Terms of Service (GDPR Art. 13-14)

- [ ] Draft privacy policy covering:
- [ ] Legal review (lawyer or use template service like Termly)
- [ ] Create page: src/routes/privacy-policy/+page.svelte
- [ ] Link in footer
- [ ] Draft terms of service covering:
- [ ] Create page: src/routes/terms-of-service/+page.svelte
- [ ] Link in footer

#### Data Processing Agreements (DPAs)

- [ ] Sign DPA with Supabase (https://supabase.com/dpa)
- [ ] Verify Anthropic data policy (they don't retain data)
- [ ] Verify Stripe GDPR compliance (already compliant)
- [ ] Sign DPA with Resend (https://resend.com/dpa)
- [ ] Sign DPA with Sentry (if using)
- [ ] Document all processors in privacy policy

#### CI/CD Pipeline Setup

- [ ] Create .github/workflows/test.yml
- [ ] Create .github/workflows/deploy-staging.yml (on merge to main)
- [ ] Create .github/workflows/deploy-production.yml (on tag v\*)
- [ ] Configure secrets in GitHub (API keys, credentials)
- [ ] Test: Push to branch, verify CI runs
- [ ] Test: Merge to main, verify staging deployment
- [ ] Test: Create tag v0.1.0, verify production deployment

#### DNS & SSL Setup

- [ ] Purchase boardof.one (Namecheap or Cloudflare Registrar)
- [ ] Configure DNS records:
- [ ] Verify DNS propagation: `dig boardof.one`
- [ ] Setup Let's Encrypt (auto-provisioned by DigitalOcean App Platform)
- [ ] Test HTTPS redirect

#### Backup & Disaster Recovery

- [ ] PostgreSQL: Enable daily automated backups (Supabase Pro)
- [ ] Redis: AOF + RDB snapshots
- [ ] Test backup restore procedure:
- [ ] Document disaster recovery plan (RTO: 4 hours, RPO: 1 hour)
- [ ] Create runbook: docs/DISASTER_RECOVERY.md

#### Uptime Monitoring

- [ ] Setup UptimeRobot (free tier) or Better Uptime
- [ ] Monitor /health endpoint (5-minute interval)
- [ ] Monitor /api/health/db (database health)
- [ ] Monitor /api/health/redis (Redis health)
- [ ] Configure alerts:
- [ ] Target: 99.9% uptime (8.7 hours/year downtime allowed)

#### Incident Response Playbook

- [ ] Create docs/INCIDENT_RESPONSE_PLAYBOOK.md
- [ ] Document procedures for common incidents:

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Test: Cross-service integration (FastAPI + SvelteKit + Redis + PostgreSQL)
- [ ] Test: WebSocket/SSE streaming works
- [ ] Test: Checkpoint recovery works

#### Load Testing

- [ ] Install Locust: `uv add locust`
- [ ] Create load test script (tests/load/deliberation_load.py)
- [ ] Run load test: 100 concurrent users
- [ ] Target metrics:
- [ ] Identify bottlenecks, optimize if needed

#### Security Testing (OWASP Top 10)

- [ ] SQL Injection tests
- [ ] XSS tests
- [ ] CSRF tests (verify SameSite cookies)
- [ ] Auth bypass tests
- [ ] Rate limit tests (verify 429 returned)

#### Deployment Documentation

- [ ] Document production deployment steps (docs/DEPLOYMENT.md):
- [ ] Create deployment checklist
- [ ] Document rollback procedure

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

#### Blue-Green Deployment (Zero-Downtime)

**Value**: Deploy new versions without user-facing downtime

- [ ] Setup blue and green environments (DigitalOcean App Platform)
- [ ] Deploy new version to green (inactive)
- [ ] Run smoke tests against green environment
- [ ] Database migrations (run before traffic switch)
- [ ] Switch traffic from blue to green (DNS or load balancer)
- [ ] Monitor green environment (5 minutes)
- [ ] Rollback procedure if green fails
- [ ] Decommission blue environment after 24h (if green stable)

**Validation**:

- [See TESTING.md for test requirements]

**Deliverables**:

- [ ] ✅ Load testing passes (all scenarios)
- [ ] ✅ Security audits pass (no critical vulnerabilities)
- [ ] ✅ GDPR compliance verified
- [ ] ✅ E2E tests pass (all critical flows)
- [ ] ✅ Documentation complete
- [ ] ✅ Deployment procedure tested
- [ ] ✅ Blue-green deployment working

---

## Week 14 (Days 93-101): Launch Preparation + User Documentation

**Goal**: Deploy to production, create user docs, announce launch, monitor closely

**Status**: 0/77 tasks complete

### Day 93-94: User Documentation & Help Center

**Goal**: Create comprehensive user-facing documentation

- [ ] Create help center page (src/routes/help/+page.svelte)
- [ ] Write documentation:
- [ ] Add search functionality (simple keyword search)
- [ ] Link from navigation and footer

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Test: PostgreSQL accessible
- [ ] Test: Redis accessible
- [ ] Test: DNS resolves

**Validation**:

- [See TESTING.md for test requirements]

---

### Day 97: Production Monitoring Setup

**Value**: Real-time production observability

#### Metrics (Prometheus + Grafana)

- [ ] Deploy Prometheus to Kubernetes
- [ ] Deploy Grafana to Kubernetes

#### Alerts (Alertmanager)

- [ ] Configure Alertmanager

#### Logs (Loki or CloudWatch)

- [ ] Deploy Loki to Kubernetes (optional for MVP)
- [ ] OR: Use DigitalOcean Monitoring (managed logs)

#### Testing

- [ ] Test: Prometheus scraping metrics
- [ ] Test: Grafana dashboards render
- [ ] Test: Alerts trigger

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Review exported data
- [ ] Import to production
- [ ] Verify migration

#### Stripe Migration (Test → Live)

- [ ] Switch Stripe keys
- [ ] Migrate test subscriptions (if any)

#### Testing

- [ ] Test: Production database accessible
- [ ] Test: Stripe live mode works

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Test: Rate limiting works (production)

**Validation**:

- [See TESTING.md for test requirements]
- [ ] Create system shutdown procedure (worst case)
- [ ] Document system operation knowledge base
- [ ] Test emergency vault access (have trusted person access and report)

**Validation**:

- [See TESTING.md for test requirements]

## Post-Launch Roadmap (Week 16+)

**v1.1 Features** (4-6 weeks post-launch):
- Background summarizer node (async, zero latency impact) - design ready, needs integration
- LinkedIn & GitHub OAuth (infrastructure exists, just add providers)
- Advanced research caching (cross-user cache sharing, industry-specific caches)

**v2.0 Features** (Q1 2026 - Major Release):
- **Full Action Tracking** (8-12 weeks) - see zzz_project/detail/ACTION_TRACKING_FEATURE.md
  - Status tracking (in_progress, blocked, completed)
  - Email + in-app reminders
  - Monthly progress reports
  - Replanning deliberations (when blocked)
  - Dependencies (Pro tier)
  - Templates (Pro tier)
- Multi-language support (i18n for personas + synthesis)
- Slack/Discord integrations (deliberation results in team channels)

**Completed in MVP** (brought forward from v2.0):
- ✅ Google OAuth (Days 45-48)
- ✅ Action Tracking Lite (Days 50-54) - extract, review, save, track

---

## Full Archive

**Detailed task breakdowns, code examples, validation checklists**: See `zzz_project/FULL_ROADMAP_ARCHIVE.md`

**Retrospectives**:

- zzz_project/WEEK5_RETROSPECTIVE.md
- zzz_project/LANGGRAPH_MIGRATION_COMPLETE.md
- zzz_project/detail/DAY_36_5_IMPLEMENTATION_SUMMARY.md

**Feature Specifications**:

- zzz_project/detail/CONTEXT_COLLECTION_FEATURE.md
- zzz_project/detail/RESEARCH_CACHE_SPECIFICATION.md
- zzz_project/detail/MULTI_SUBPROBLEM_DELIBERATION.md
- zzz_project/detail/CROSS_SUBPROBLEM_EXPERT_MEMORY.md
- zzz_project/detail/ACTION_TRACKING_FEATURE.md (post-MVP)
- zzz_project/detail/UX_DESIGN_PRINCIPLES.md
