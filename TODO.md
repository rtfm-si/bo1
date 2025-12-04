# Feature Roadmap

Prioritized by: implementation speed, dependencies, and user value.

---

## Tier 1: Quick Wins (High Value, Low Effort)

_Ship in days, immediate user impact_

- [x] **Expert panel as columns** (not rows) - 1-2h ✅

  - Converted to responsive grid (2-5 columns)
  - Individual expert cards with centered info, order badge in corner
  - Updated: `frontend/src/lib/components/events/ExpertPanel.svelte`

- [x] **Meeting UI counters** - 4-6h ✅

  - Added 5 counters: Topics explored, Research performed, Risks mitigated, Challenges resolved, Options discussed
  - Each with icon, count, hover tooltip
  - Added to DecisionMetrics as "Deliberation Progress" section
  - Updated: `frontend/src/lib/components/ui/DecisionMetrics.svelte`

- [x] **Persona diversity in contributions** - 4-8h ✅

  - Added response_style visual indicators (technical/analytical/socratic/narrative)
  - Left border color + badge showing thinking style
  - Persona code → response style mapping
  - Updated: `frontend/src/lib/components/events/PersonaContribution.svelte`

- [x] **Landing page hero carousel** - 8-12h ✅
  - 3-slide auto-advancing carousel (6s interval)
  - Slide 1: Problem statement with typewriter effect
  - Slide 2: Expert discussion with 2 contribution previews
  - Slide 3: Report output preview with 3 sections
  - Navigation: arrows, dots, slide labels
  - Created: `frontend/src/lib/components/landing/HeroCarousel.svelte`
  - Updated: `frontend/src/lib/components/landing/HeroSection.svelte`

---

## Tier 2: Core UX Improvements (Medium Effort, High Value)

_1-2 week features that significantly improve retention_

- [x] **Action item tracking (simple kanban)** - 2-3d ✅

  - Added `task_statuses` JSONB column to `session_tasks` table
  - API endpoints: GET `/{session_id}/actions`, PATCH `/{session_id}/actions/{task_id}`
  - Kanban frontend: `TaskCard.svelte`, `KanbanBoard.svelte`, `ActionsPanel.svelte`
  - Three columns: Todo, Doing, Done with status transitions
  - Created: `migrations/versions/b1c2d3e4f5g6_add_task_status_tracking.py`
  - Updated: `bo1/state/repositories/session_repository.py`, `backend/api/sessions.py`

- [x] **Fix "Clarify" flow** - 1-2d ✅

  - Added "clarify" action to FacilitatorDecision type and response parser
  - Added Option E (Request Clarification) to facilitator prompt
  - Connected facilitator → clarification node in graph config
  - Added router case for "clarify" action
  - Clarification answers now stored with timestamps and round_number
  - Updated: `bo1/llm/response_parser.py`, `bo1/graph/routers.py`, `bo1/graph/config.py`, `bo1/prompts/facilitator.py`, `bo1/graph/nodes/context.py`

- [x] **More proactive research triggers** - 1-2d ✅

  - Created `ComparisonDetector` utility for "X vs Y" pattern detection
  - Integrated into `decompose_node` at problem intake stage
  - Detects: explicit vs, timing, build vs buy, market expansion, technology choices
  - Auto-generates research queries with HIGH/MEDIUM priority
  - Emits `comparison_detected` SSE event for frontend awareness
  - Created: `bo1/utils/comparison_detector.py`, `tests/utils/test_comparison_detector.py`
  - Updated: `bo1/graph/nodes/decomposition.py`, `bo1/graph/state.py`, `backend/api/event_collector.py`

- [x] **Admin: Delete user + Lock/Unlock account** - 4-6h ✅
  - Lock/Unlock user accounts with session revocation
  - Soft delete (preserves data) and hard delete (permanent) options
  - SuperTokens integration blocks locked users at sign-in
  - Audit logging for all admin actions
  - UI: Status column, modals for lock/delete with confirmations
  - Updated: `backend/api/admin/users.py`, `frontend/src/routes/(app)/admin/users/+page.svelte`

---

## Tier 3: Business Context System (Foundation for Future Features)

_Enables personalization, better advice quality_

- [x] **Lightweight onboarding flow** - 3-5d ✅

  - Company name + website URL input with multi-step form
  - Auto-crawl + enrich via EnrichmentService (Brave Search + Claude Haiku)
  - Detects: industry, product categories, pricing, positioning, tone, brand maturity, SEO structure, tech stack
  - Business model detection (SaaS, marketplace, agency, etc.)
  - Competitor and ICP identification
  - Keyword extraction for market category
  - Driver.js guided tour for new users
  - Umami analytics integration (self-hosted)
  - Created: `bo1/services/enrichment.py`, `frontend/src/routes/(app)/onboarding/+page.svelte`
  - Created: `frontend/src/lib/tours/index.ts`, `frontend/src/lib/utils/analytics.ts`
  - Updated: `backend/api/context.py`, `backend/api/onboarding.py`

- [x] **Business stage dropdown** - 2-4h ✅

  - Stage: idea → early → growing → scaling
  - Primary objective: acquire customers / improve retention / raise capital / launch product / reduce costs
  - Integrated into onboarding flow and context settings page

- [x] **Business context page** - 2-3d ✅

  - Full view/edit of enriched business data
  - Auto-enrichment from website URL
  - Context auto-injected into meeting creation
  - Created: `frontend/src/routes/(app)/settings/context/+page.svelte`
  - Updated: `backend/api/sessions.py` (context injection)

- [x] **Periodic context refresh prompt** - 4-6h ✅
  - ContextRefreshBanner on dashboard when context >30 days old
  - Checks for missing fields, days since update
  - Dismissable with API tracking
  - Created: `frontend/src/lib/components/ui/ContextRefreshBanner.svelte`
  - Updated: `backend/api/context.py` (refresh-check, dismiss-refresh endpoints)

### Additional Context Fields (Implemented) ✅

- Target customer profile & geography
- Traffic range, MAU buckets, revenue stage
- Main product/service, value proposition
- Team size (solo founder / small team / contractors)
- Budget, time, regulatory constraints
- All stored in extended `user_context` table (30+ fields)
- Migration: `migrations/versions/c2d3e4f5g6h7_add_extended_business_context.py`

---

## Tier 4: Security & Stability (Important, Less Visible)

_Must-do before scaling_

- [x] **Rate limiting on "Start Meeting"** - 4-6h ✅

  - Redis-backed rate limiter for multi-instance support
  - User-based throttling after auth (tier-aware: free/pro/enterprise)
  - IP-based fallback before auth
  - Updated: `backend/api/middleware/rate_limit.py`, `bo1/constants.py`, `backend/api/sessions.py`

- [x] **Prompt injection audit** - 1-2d ✅

  - LLM-based prompt injection auditor using Claude Haiku
  - 8 risk categories with confidence levels
  - Integrated into session creation and clarification endpoints
  - Created: `bo1/security/prompt_injection.py`
  - Updated: `bo1/security/__init__.py`, `backend/api/sessions.py`, `backend/api/control.py`

- [x] **SQL injection audit** - 4-6h ✅

  - Comprehensive audit: 95%+ queries use safe parameterized queries
  - Added defense-in-depth validation for dynamic SQL field names
  - Added `_validate_sql_identifiers()` to user_repository.py
  - Added SQL safety documentation to repository files
  - No production vulnerabilities found

- [x] **Redis → Postgres cleanup** - 1-2d ✅
  - Redis TTLs aligned (7 days for all: metadata, events, checkpoints)
  - Added `cleanup_session()` and `schedule_cleanup()` to RedisManager
  - Terminal sessions (completed/failed/killed) schedule cleanup after 1h grace period
  - Completed meetings automatically fall back to Postgres after cleanup
  - Updated: `bo1/constants.py`, `bo1/state/redis_manager.py`, `bo1/graph/execution.py`

---

## Tier 5: Premium Features (High Effort, High Value)

_Differentiated value, potential monetization_

- [ ] **Mentor Mode** - 1-2w

  - Chat directly with an expert (like ChatGPT)
  - Has business context, problem history, actions
  - Natural extension of meeting system
  - mentors can be grouped under categories as well:
    Leadership
    Product
    Marketing
    Founder Psychology
    Productivity
    Career
    etc...
    chat to all in category as an 'addon' package?
    can be 'called' from within an action, with the convo linked to action, and summary added to action as an 'update'

- [ ] **Gated features system** - 2-3d

  - User A sees page X, User B doesn't
  - Enables tier-based access control

- [ ] **Tier plans infrastructure** - 3-5d

  - Depends on gated features
  - Pricing page, feature limits per tier
  - different levels of market insight and competitor watch are unlocked at different plans

- [ ] **Action replanning** - 1w
  - Track action outcomes - user inputs progress updates
  - "What went wrong" flow
  - Replan based on results
  - Actions have deadlines - basic capability chase user for update, and mentors can follow up 'need any help with...?' if plan tier allows

---

## Tier 6: Team & Scale Features (Later Stage)

_Build after core product is solid_

- [ ] **Workspaces** - 1-2w

  - Team containers
  - Shared meetings, business context

- [ ] **Projects** - 1w

  - Group related meetings
  - Depends on workspaces

- [ ] **Informal expert tier** - 1w

  - Sole trader / small business level personas
  - Depends on business context system

- [ ] **Competition research** - 1w
  - Auto-identify and research competitors (basic capability on sign up (plan tier specific)
  - Depends on business context onboarding
  - Use Brave and Tavily
  - Can request market updates every month maybe (plan tier)?
  - embeddings are used to ensure we dont make repeated expensive searches for the same businesses / markets etc - just reuse existing if recent

---

Admin should be able to 'impersonate' a user and see their dashboard, meetings, actions etc but with the additional admin views (like costs, failed meetings etc etc)

NB - only completed meetings should have actions showing up. failed meetings should probably be masked from end users dashboard (except admin). in progress should only show actions when the meeting has completed.

when actions are closed (completed / killed etc) the dependant actions should 'auto update'?

projects should be able to be tagged with ai generated categories and filterable

gantt chart should be filterable by project

gantt chart should be accessible from actions tab

what do top level page links look like?
meetings -< projects -< actions

ntfy report didnt trigger this am

## Tier 7: Marketing & Growth (Ongoing)

- [ ] **Landing page SEO** - 2-3d

  - Meta tags, structured data, content optimization

- [ ] **Footer pages audit** - 1d

  - Terms, privacy, about pages need updating & checking

- [ ] **Suggested questions from business context** - 2-3d
  - CTA to add business context when starting new meeting
  - Depends on business context system

---

## Cleanup Tasks

- [ ] Verify "Sub-Problem Complete" taxonomy change (may already be done)
- [ ] Remove "Synthesis" label if no longer in use
- [ ] Fix "The Bottom Line" duplicate in UI

---

## Recommended Sprint Plan

**Sprint 1 (Week 1-2):** Tier 1 quick wins + admin basics

**Sprint 2 (Week 3-4):** Tier 2 core UX (action tracking, clarify fix, research triggers)

**Sprint 3 (Week 5-6):** Tier 3 business context foundation

**Sprint 4 (Week 7-8):** Tier 4 security hardening

**Sprint 5+:** Tier 5-7 based on user feedback and growth metrics

new thoughts:
how to add 'actions' and kanban to carousel?
should we show competitor analysis in carousel?

remove 'delete context' from settings context > overview
