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

- [ ] **Lightweight onboarding flow** - 3-5d

  - Company name + website URL input
  - Auto-crawl + enrich: industry, product categories, pricing, positioning, tone, brand maturity, SEO structure, tech stack
  - Detect business model (SaaS, marketplace, agency, etc.)
  - Identify competitors and ICP
  - Extract keywords for market category

- [ ] **Business stage dropdown** - 2-4h

  - Stage: idea → early → growing → scaling
  - Primary objective: acquire customers / improve retention / raise capital / launch product / reduce costs

- [ ] **Business context page** - 2-3d

  - View/edit enriched business data
  - Inject into meeting context for better advice

- [ ] **Periodic context refresh prompt** - 4-6h
  - "Are these details still correct?" every N months
  - Prompt after first meeting completion

### Additional Context Fields (Optional, High Value)

- Target customer profile & geography
- Traffic range, MAU buckets, revenue stage
- Main product/service, value proposition
- Team size (solo founder / small team / contractors)
- Budget, time, regulatory constraints

---

## Tier 4: Security & Stability (Important, Less Visible)

_Must-do before scaling_

- [ ] **Rate limiting on "Start Meeting"** - 4-6h

  - Prevent free account spam
  - IP + user-based throttling

- [ ] **Prompt injection audit** - 1-2d

  - Review all LLM inputs for injection vectors

- [ ] **SQL injection audit** - 4-6h

  - Verify parameterized queries everywhere

- [ ] **Redis → Postgres cleanup** - 1-2d
  - Redis for live memory only
  - Completed meetings read from Postgres
  - Clear Redis cache post-meeting completion

---

## Tier 5: Premium Features (High Effort, High Value)

_Differentiated value, potential monetization_

- [ ] **Mentor Mode** - 1-2w

  - Chat directly with an expert (like ChatGPT)
  - Has business context, problem history, actions
  - Natural extension of meeting system

- [ ] **Gated features system** - 2-3d

  - User A sees page X, User B doesn't
  - Enables tier-based access control

- [ ] **Tier plans infrastructure** - 3-5d

  - Depends on gated features
  - Pricing page, feature limits per tier

- [ ] **Action replanning** - 1w
  - Track action outcomes
  - "What went wrong" flow
  - Replan based on results

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
  - Auto-identify and research competitors
  - Depends on business context onboarding

---

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
