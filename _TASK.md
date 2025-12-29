# Task Backlog

_Last updated: 2025-12-29_

---

## Open Tasks

### Blocked on User Action

- [ ] [LAUNCH][P1] Switch Stripe to live mode - see `docs/runbooks/stripe-config.md`
- [ ] [EMAIL][P4] Payment receipt email trigger - blocked on Stripe live mode
- [ ] [SOCIAL][P3] Direct posting to social accounts - user to decide approach

### Needs Clarification

- [ ] [MONITORING][P1] Kubernetes deployment manifest - are we using k8s? (current: SSH to droplet)
- [ ] [MONITORING] Clarify "grafana logs: value A" requirement
- [ ] [DATA][P2] Clarify data retention soft-delete behavior

### Deferred by Design

- [ ] [DATA][P2] DuckDB backend for large datasets - defer until >100K rows
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have

### E2E Findings (2025-12-29)

- [ ] [INFRA][P2] Add retry logic for Anthropic API failures with exponential backoff
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Deferred: Third-party dependency (Anthropic API "overflow" error)
  - Lead: Meeting failed on sub-problem 4 of 4; 3 sub-problems completed successfully before failure
- [ ] [INFRA][P2] Implement circuit breaker pattern for LLM calls
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Deferred: Third-party dependency - requires infrastructure resilience work
- [ ] [INFRA][P3] Add fallback model configuration (e.g., Claude 3.5 Sonnet when primary fails)
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Deferred: Third-party dependency
- [ ] [UX][P3] Improve error messaging for third-party API failures
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Deferred: Current message is generic; could be more helpful
- [ ] [INFRA][P2] Enable resume from last successful sub-problem checkpoint
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Deferred: Complex feature requiring checkpoint management

### User-Owned

- [ ] [DOCS][P3] Help pages content review (Si's todo)

---

## Outstanding Work

### Dashboard & UX

- [x] [DASHBOARD][P3] Review/improve completion trends visual design
- [x] [DASHBOARD][P3] Add embeddings research visualization with click-through to source
- [x] [HEATMAP][P3] Review and improve heatmap color scheme

### Admin & Ops

- [x] [ADMIN][P2] Add deeper insight drill-downs for each admin metric - `/admin/costs` Insights tab
- [x] [ADMIN][P2] Improve research costs/cache insight for quality vs cost optimization - cache effectiveness buckets, quality indicators
- [x] [ADMIN][P2] Add guidance for configuring cache hit rate vs user quality tradeoffs - tuning recommendations endpoint
- [x] [ADMIN][P2] Clarify SSE streaming toggle default (why off? when to use?) - documented in /admin/toggles
- [x] [ADMIN][P2] Move emergency toggles to dedicated sub-page (reduce page depth) - /admin/toggles
- [x] [ADMIN][P2] Document how to manage A/B test experiments - in-page help panel on /admin/experiments
- [x] [ADMIN][P2] Add UI/workflow for starting new experiments - /admin/experiments with full CRUD
- [x] [ADMIN][P3] Move promotions, collateral, and blog out of user management into separate block

### SEO & Analytics

- [x] [SEO][P2] Track SEO admin page as internal cost - cost_category column in api_costs, /admin/costs/internal endpoint
- [x] [SEO][P2] Track click-through rates and benefits of SEO pages for ranking - view/click endpoints, frontend tracking, admin ROI UI

---

## Completed Summary

### December 2025 (Week of 12/29)

**ActivityHeatmap Visual Redesign**: Sparkline trend summary with 7-day rolling average, grouped toggle chips (Actual vs Planned), improved color accessibility (WCAG AA 4.5:1 contrast with 600 shades), consolidated legend into help tooltip, mobile responsive layout (12px cells, single-letter day labels, horizontal scroll indicator). Added 12 unit tests for sparkline calculations.

**AI Ops Research**: Researched proactive failure prediction packages. Recommended ADTK (rule-based time-series anomaly detection) + ruptures (change-point detection). See `docs/research/failure-prediction.md`.

**Dashboard Redesign**: Week Planner (-2/+4 days), SmartFocusBanner with priority CTAs, GoalBanner visual hierarchy, RecentMeetingsWidget (last 5 meetings), ValueMetricsPanel with KeyMetrics API, ResearchInsightsWidget (PCA-reduced scatter plot of research embeddings).

**Activity Heatmap**: Working pattern setting (Mon-Fri default), history depth user preference (1/3/6 months), non-working days greyed out, future limited to planned actions.

**Performance Monitoring**: PerformanceMonitor service with Redis time-series, ThresholdService with runtime-adjustable thresholds, FastAPI middleware for request tracking, degradation alerts via ntfy.

**Admin Fixes**: Fixed 13 broken admin endpoints (column names, auth patterns, SQL syntax). Created `tests/api/test_admin_routes_health.py` with 50 passing tests.

**Infrastructure**: Extended prod-cleanup.sh (static assets, Docker images, disk alerts), new user redirect to context setup, SuperTokens Core upgrade (9.3.0 → 10.1.4).

**SEO & Legal**: JSON-LD structured data for blog, cookie/privacy policy updates (SuperTokens/Umami instead of Supabase/PostHog), minimal tracking stance documentation.

**AI Ops**: Error pattern tracking with match counts, catch-all unclassified_error pattern, Redis buffer population from API 500s.

**Admin UX**: Dedicated `/admin/toggles` page for emergency toggles with full-width layout, grouped by Security/LLM/Features, expandable documentation tooltips for each toggle explaining when to enable/disable.

**Internal Cost Tracking**: New `cost_category` column in api_costs (user/internal_seo/internal_system), content_generator costs tagged as internal_seo, `/admin/costs/internal` endpoint for querying internal costs, new "Internal Costs" tab on admin costs page.

**A/B Experiment Management**: Database-backed experiment management (`experiments` table), lifecycle support (draft→running→paused→concluded), deterministic user-to-variant assignment, full CRUD API endpoints, enhanced `/admin/experiments` UI with create modal, status badges, action buttons, and in-page documentation panel.

**Blog CTR Tracking**: Added `view_count`, `click_through_count`, `last_viewed_at` columns to blog_posts, public tracking endpoints (`/view`, `/click`) with rate limiting, frontend session-based tracking integration, `/admin/seo/performance` endpoint with ROI metrics (cost per click), enhanced admin SEO page with sortable performance table.

**Cost Insight Drill-Downs**: 5 new admin drill-down endpoints (`/api/admin/drilldown/cache-effectiveness`, `/model-impact`, `/feature-efficiency`, `/tuning-recommendations`, `/quality-indicators`). Frontend Insights tab on `/admin/costs` with: cache effectiveness buckets (0-25%, 25-50%, 50-75%, 75-100% hit rate), model impact with what-if scenarios (all-Opus vs all-Haiku), feature efficiency by cost/session, AI-generated tuning recommendations with confidence levels, quality correlation indicators (cached vs uncached continuation rates).

### December 2025 (Week of 12/27)

**Fair Usage & Billing**: Per-feature daily cost limits with p90 detection, meeting bundle purchases (1/3/5/9 @ £10), nonprofit discount tier (80%/100% off).

**SEO Platform**: Autopilot with purchase intent scoring, trend analyzer, topics table, article generator, content analytics tracking.

**Peer Features**: Benchmark opt-in with k-anonymity, cross-user research sharing, competitor skeptic relevance checks.

**Context System**: Key metrics tracking, strategic objective progress, heatmap history depth.

**Admin Improvements**: Dashboard drillable cards, cache metrics UI, costs aggregations, fixed costs editing.

### Earlier (Pre-12/27)

**Core Platform**: Multi-agent deliberation, SSE streaming, checkpoint recovery, actions system (Kanban/Gantt/reminders), projects with Gantt, mentor mode with expert personas.

**Business Features**: Stripe billing, workspaces, promotions, context system with 22 benchmark metrics, competitor detection, market trends.

**Security**: Rate limiting, prompt injection detection (132 test cases), SQL validation, GDPR compliance, supply chain scanning.

**Infrastructure**: Blue-green deployment, PostgreSQL backups, Prometheus/Grafana/Loki observability, email via Resend.

**LLM Optimization**: Lean synthesis (30-60% cost reduction), Haiku extended to round 3, persona context window 6→3 contributions.

---

_For detailed implementation notes, see git history._
