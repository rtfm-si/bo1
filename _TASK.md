# Task Backlog

_Last updated: 2026-01-07 (test fixes for http_error response format)_

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

---

## Audit-derived tasks (2026-01-06)

### P1 - High

- [x] [PERF][P1] Add composite indexes for partitioned tables - z15_add_covering_indexes.py migration (2026-01-06)
- [x] [PERF][P1] Optimize action tag filtering query - CTE + JOIN pattern in action_repository.py:185-186 (2026-01-06)
- [x] [PERF][P1] Enable pg_stat_statements monitoring - z16_enable_pg_stat_statements.py migration (2026-01-06)
- [x] [OBS][P1] Add Redis connection pool metrics - metrics.py:311-332, health.py (2026-01-06)
- [x] [API][P1] Standardize error response format Phase 2 - migrated 10 high-priority files: mentor.py, business_metrics.py, admin/users.py, admin/ops.py, health.py, middleware/auth.py, middleware/workspace_auth.py, admin/experiments.py, billing.py, admin/blog.py (2026-01-06)
- [x] [API][P2] Standardize error response format Phase 3 - migrated 15 admin files: templates.py, billing.py, promotions.py, feature_flags.py, feedback.py, helpers.py, impersonation.py, email.py, runtime_config.py, terms.py, session_control.py, costs.py, partitions.py, beta_whitelist.py, research_cache.py (2026-01-06)
- [x] [API][P2] Standardize error response format Phase 4 - migrated 7 non-admin files: email.py, onboarding.py, integrations/calendar.py, tags.py, analysis.py, auth.py, templates.py; added EXT_WEBHOOK_ERROR, FEATURE_DISABLED, USER_NOT_FOUND error codes (2026-01-06)
- [x] [API][P1] Add max length validation to text fields - blocking_reason/cancellation_reason (2000 chars), what_and_how items (1000 chars, max 20), success/kill_criteria items (500 chars, max 20) (2026-01-06)

### P2 - Medium

- [x] [PERF][P2] Implement session metadata caching - redis_manager.py:740-827 with PostgreSQL fallback (2026-01-06)
- [x] [PERF][P2] Implement aggregation result caching - get_session_costs uses Redis (2026-01-06)
- [x] [PERF][P2] Add contribution pruning in graph state - prune_contributions_after_round() prunes contributions older than 2 rounds after summary generated; reduces memory 60-80% during deliberation (2026-01-06)
- [x] [DATA][P2] Fix Recommendation model missing fields - session_id, sub_problem_index, id, created_at, user_id in recommendations.py:22-27 (2026-01-06)
- [x] [DATA][P2] Fix ContributionMessage schema drift - user_id, status fields in bo1/models/state.py:166-169 (2026-01-07)
- [x] [DATA][P2] Fix Session nullable field consistency - phase, total_cost, round_number defaults in bo1/models/session.py:34-36 (2026-01-07)
- [x] [REL][P2] Add Redis metadata fallback to PostgreSQL - dual-write in redis_manager.py (2026-01-06)
- [x] [REL][P2] Add SSE reconnection backoff - burst protection with 429+Retry-After after >3 rapid reconnects, exponential backoff 5s-60s (2026-01-06)
- [x] [REL][P2] Add deadlock retry to @retry_db decorator - retry.py:33-68 handles 40P01 errors (2026-01-06)
- [x] [COST][P2] Compress persona protocol boilerplate - consolidated BEHAVIORAL_GUIDELINES + EVIDENCE_PROTOCOL into CORE_PROTOCOL (~180 tokens savings per contribution) (2026-01-06)
- [x] [COST][P2] Reduce persona context window from 5 to 3 contributions - bo1/prompts/persona.py:130-134 (2026-01-07)
- [x] [LLM][P2] Add unit tests for sanitization - 1184 lines across tests/test_sanitizer.py + tests/prompts/test_sanitizer.py (2026-01-06)

### P3 - Low

- [x] [ARCH][P3] Move event publishing out of routers - extracted meeting_failed from route_after_next_subproblem to EventCollector._check_and_publish_subproblem_failures(); added SubproblemFailure TypedDict; 6 new unit tests (2026-01-07)
- [x] [ARCH][P3] Create bo1/graph/routers/__init__.py with router registry - split into phase.py, facilitator.py, synthesis.py; added get_router()/list_routers() (2026-01-06)
- [x] [OBS][P3] Add query timeout to long-running database operations - statement_timeout in database.py:262,322-324 (2026-01-06)
- [x] [OBS][P3] Add error rate metrics by component - already in metrics.py (2026-01-06)

---

## New Tasks (from _TODO.md, 2026-01-04)

### P1 - High

- [x] [UI][P1] Fix currency display: metrics show $ despite user selecting GBP £ in settings (2026-01-04)
- [x] [DATA][P1] Extract existing insights to metrics - implemented CATEGORY_TO_METRIC_KEY mapping, migration script, auto-sync hooks (2026-01-04)

### P2 - Medium

- [x] [UI][P2] Add app version number display in settings (major.minor.patch format, currently 0.8.0) (2026-01-04)

### Deferred by Design

- [ ] [DATA][P2] DuckDB backend for large datasets - defer until >100K rows
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have

---

## Feature Explorer Issues (2026-01-04 Session 2 - FIXED)

### P0 - Critical

- [x] [API][P0] ISS-004: Session sharing 500 errors - removed stale `SessionLocal` imports from sessions.py; repository methods already use `db_session()` context manager (2026-01-04)

### P1 - Major

- [x] [API][P1] ISS-001: 2FA setup 403 error - SuperTokens TOTP requires paid license; added `available` + `unavailable_reason` fields to status endpoint, UI now shows "Coming Soon" when unavailable (2026-01-04)

### P2 - Minor

- [x] [API][P2] ISS-002: Dataset insights 422 - expected behavior for unprofiled datasets (2026-01-04)
- [x] [API][P2] ISS-003: Managed competitors 503 - transient connection pool exhaustion (2026-01-04)
- [x] [API][P2] ISS-005: @mention context not injected - added `mentions_not_found` to mentor response for UI feedback; improved logging when mentions fail to resolve (2026-01-04)

---

## Feature Explorer Issues (2026-01-04 Session 1 - FIXED)

### P0 - Critical

- [x] [API][P0] ISS-001: Session sharing 500 errors - PostgreSQL fallback already exists in `verify_session_ownership()`; added integration tests for share endpoints + PostgreSQL fallback (2026-01-04)
- [x] [API][P0] ISS-002: Project detail 500 errors - fixed gantt SQL (removed non-existent progress_percent), fixed sessions column alias mismatch (2026-01-04)

### P1 - Major

- [x] [API][P1] ISS-003: 2FA setup 500 error - added `user_repository.ensure_exists()` call before backup code storage, RETURNING id check for UPDATE (2026-01-04)
- [x] [API][P1] ISS-004: SEO module 404 errors - verified working: all endpoints return 401 (auth required) not 404; tables+migrations deployed (2026-01-04)

### P2 - Minor

- [x] [API][P2] ISS-005: Dataset insights 422 error - frontend now gracefully handles 422 (expected for unprofiled data) (2026-01-04)
- [x] [ROUTE][P2] ISS-006: Direct `/projects/new` navigation 500 - added client-side redirect to `/projects?create=true` (2026-01-04)

---

## Feature Audit Tasks (2026-01-03)

### P0 - Critical

- [x] [API][P0] Fix `/api/v1/user/preferences` 500 error - missing `preferred_currency` column; migrations applied to prod (2026-01-03)
- [x] [ROUTE][P0] Deploy `/settings/security` route - 2FA code verified, migration applied, tests pass (22/22)
- [x] [API][P0] Fix session sharing 500 errors - added `created_by` to INSERT query in session_repository.py (2026-01-03)
- [x] [API][P0] Fix 2FA setup 500 error - added UnknownUserIdError handling in two_factor.py (2026-01-03)

### P1 - High

- [x] [API][P1] Investigate `/context/strategic` 503 - transient pool exhaustion during audit; 503+Retry-After handling already present (2026-01-03)
- [x] [UI][P1] Fix metric save .trim() error - ensured editValue is string before calling trim() (2026-01-03)

### P2 - Medium

- [x] [API][P2] Fix `/context/peer-benchmarks` 404 errors - added API_CONTEXT_MISSING and API_INDUSTRY_NOT_SET error codes with context-specific frontend guidance (2026-01-03)
- [x] [ROUTE][P2] Add /context/competitors redirect - 301 redirect to /reports/competitors (2026-01-03)
- [x] [UI][P2] Fix Mentor clear button - added onConversationChange callback to clear conversation (2026-01-03)
- [x] [UI][P2] Fix dataset insights 422 logging - check for status code before logging as error (2026-01-03)

---

## Previous Audit Tasks (2026-01-03)

### P0 - Critical

- [x] [REL][P0] Implement LangGraph checkpoint recovery - resume failed sessions from last checkpoint, add "Retry Session" UI (2026-01-03)
- [x] [REL][P0] Fix replanning service rollback - `_rollback_session()` in replanning_service.py (2026-01-03)
- [x] [REL][P0] Validate LLM provider fallback - `tests/chaos/test_anthropic_outage_integration.py` covers full outage flow (2026-01-03)

### P1 - High

- [x] [OBS][P1] Add correlation ID to graph state and node logs - propagate request_id through LLM broker calls (2026-01-03)
- [x] [OBS][P1] Expose circuit breaker state as Prometheus metrics - `circuit_breaker_state{provider, state}` gauge in metrics.py (2026-01-03)
- [x] [OBS][P1] Add event persistence metrics - in event_publisher.py and event_collector.py (2026-01-03)
- [x] [DATA][P1] Add missing fields to Session Pydantic model - dataset_id added (2026-01-03)
- [x] [API][P1] Standardize error response format Phase 1 - migrated peer_benchmarks & context routes to http_error() (2026-01-03)
- [x] [LLM][P1] Add challenge phase validation - Phase 2 rejection implemented: hard mode rejects + re-prompts (2026-01-03)
- [x] [ARCH][P1] Split DeliberationGraphState by domain - added CoreState TypedDict + get_core_state() accessor; migrated 9 node files to use nested state accessors (2026-01-03)

### P2 - Medium

- [x] [ARCH][P2] Consolidate router validation - created router_utils.py with shared helpers, added @log_routing_decision decorator (2026-01-03)
- [x] [ARCH][P2] Remove ENABLE_PARALLEL_SUBPROBLEMS feature flag - always use dependency analysis path (2026-01-03)
- [x] [PERF][P2] Add cache hit rate monitoring - `prompt_cache_hit_rate` in `get_session_costs()` (2026-01-03)
- [x] [DATA][P2] Add CI check for TypeScript type sync - `check:types-fresh` in CI workflow (2026-01-03)
- [x] [API][P2] Document SSE event schema versions - Version History in SSE_EVENTS.md (2026-01-03)
- [x] [API][P2] Document rate limits in OpenAPI spec - 59 endpoints with 429 + `x-rate-limits` (2026-01-03)
- [ ] [COST][P2] Run persona count A/B test - **DEFERRED**: only 32 sessions from 3 users (all hash to variant 5). Need ≥100 sessions per variant with users in both cohorts. Re-check when user base grows.

### User-Owned

- [ ] [DOCS][P3] Help pages content review (Si's todo)

---

## Completed Summary

### January 2026 (Week of 01/06)

**Audit Task Verification**: Verified and marked 12 audit-derived tasks as complete:
- P1: Composite indexes (z15_add_covering_indexes.py), action tag CTE+JOIN optimization, pg_stat_statements (z16 migration), Redis pool metrics
- P2: Session metadata caching, aggregation caching, Recommendation model fields, Redis PostgreSQL fallback, deadlock retry, sanitization tests (1184 lines)
- P3: Statement timeout, error rate metrics

### January 2026 (Week of 01/02)

**Navigation Consolidation - Board Menu**: Unified `/mentor` page with tabs (Chat, Analysis, Data Sources). Consolidated datasets upload, Google Sheets import, analysis chat, and mentor chat into single tabbed interface. Updated Header.svelte navigation. Added redirects from old `/datasets` and `/analysis` routes.

**Navigation Consolidation - Context Menu**: Merged strategic content into context/overview (GoalHistory component + quick links). Created `/reports/trends` page for trend data (TrendSummaryCard, Market Trends, Trend Insights). Simplified context/metrics (removed inline benchmarks, added link to reports/benchmarks). Converted `/context/strategic` to redirect. Updated Header navigation (removed strategic/key-metrics from Context, added Trends to Reports).

**Navigation Consolidation - Dashboard**: Converted `/context/key-metrics` to redirect to `/context/metrics`. Updated ValueMetricsPanel links. Created ResearchHeadlinesWidget with newspaper-style layout (headlines, taglines, category badges, links to source meetings). Replaced scatter plot visualization with actionable research insights.

**Insight-to-Metrics Migration**: Auto-sync clarification insights to business_metrics table. Migration script for historical data. `CATEGORY_TO_METRIC_KEY` mapping. Hooks in routes.py and control.py for ongoing sync.

**2FA Authentication**: Full TOTP 2FA with backup codes, rate limiting (5 attempts → 15min lockout), `/settings/security` UI, QR setup flow.

**Magic Link Fixes**: Fixed stray `raise` blocking emails, added 60s rate limiting via `last_magic_link_at`.

**Account Linking**: Enabled SuperTokens AccountLinking recipe for OAuth/email user linking.

**Password Security**: 12+ char requirement, upgrade prompts for weak passwords via `PasswordUpgradePrompt.svelte`.

### December 2025 (Week of 12/29)

**Bug Fixes**: `/api/v1/user/preferences` 500 error (impersonation middleware), currency display (GBP/EUR not applied), Google OAuth linking, admin impersonation showing wrong user, metrics not saving, competitor addition.

**Language Adaptation**: `StyleProfile` enum (B2B_SAAS, B2C_PRODUCT, etc.) with `detect_style_profile()` for tailored responses.

**Currency Preferences**: User-selectable currency (GBP/USD/EUR), `formatCurrency()` utility, settings UI.

**E2E Reliability**: Retry logic (5 retries, exponential backoff), circuit breaker pattern, model fallback chains, checkpoint recovery, SSE error improvements.

**Audit Tasks Completed**: 45+ P0-P3 audit items including connection pool increase (20→75), user_id FK on recommendations, workspace_id on sessions, LLM output sanitization, correlation ID propagation, parallel rounds, composite indexes, rate limiting, Redis fallback, Haiku round extension, and more.

**Dashboard Redesign**: Week Planner, SmartFocusBanner, GoalBanner, RecentMeetingsWidget, ValueMetricsPanel, ResearchInsightsWidget, ActivityHeatmap with sparklines.

**Admin Improvements**: Emergency toggles page, A/B experiment management, cost drill-downs (cache effectiveness, model impact, tuning recommendations), internal cost tracking, blog CTR tracking.

**API Fixes**: Projects autogenerate/suggestions 500s, SEO endpoints (history, autopilot, articles, topics), datasets insights 422, context trends 403, peer benchmarks 500s.

**Analysis Features**: Question history sidebar, column reference sidebar, query templates, chart rendering with detail/simple modes, chart suggestions on dataset load.

**Competitor Enrichment**: Relevance scoring persistence, URL normalization, deduplication, skeptic caching.

### December 2025 (Week of 12/27)

**Fair Usage & Billing**: Per-feature cost limits, meeting bundles, nonprofit tier.

**SEO Platform**: Autopilot, trend analyzer, article generator, content analytics.

**Peer Features**: Benchmark opt-in, research sharing, competitor skeptic.

**Context System**: Key metrics, strategic objectives, heatmap history.

### Earlier

**Core Platform**: Multi-agent deliberation, SSE streaming, checkpoint recovery, actions (Kanban/Gantt), projects, mentor mode.

**Business**: Stripe billing, workspaces, promotions, context system, competitor detection.

**Security**: Rate limiting, prompt injection (132 tests), SQL validation, GDPR.

**Infrastructure**: Blue-green deploy, PostgreSQL backups, Prometheus/Grafana/Loki.

**LLM Optimization**: Lean synthesis (30-60% cost reduction), Haiku to round 3, persona context 6→3.

---

## Navigation Consolidation (from _TODO.md, 2026-01-04)

### P1 - Board Menu Consolidation (COMPLETED 2026-01-04)

- [x] [UI][P1] Consolidate datasets, analysis, mentor pages into single "Mentor" page under Board menu - unified page with Chat/Analysis/Data Sources tabs (2026-01-04)
- [x] [UI][P1] Ensure data loading capability works in consolidated Mentor page - CSV upload + Google Sheets import in Data Sources tab (2026-01-04)
- [x] [UI][P1] Ensure data analysis capability works in consolidated Mentor page - AnalysisChat component in Analysis tab (2026-01-04)
- [x] [UI][P1] Audit and remove duplicate features across datasets/analysis/mentor during consolidation - all features consolidated, old routes redirect (2026-01-04)

### P1 - Context Menu Consolidation (COMPLETED 2026-01-04)

- [x] [UI][P1] Merge context/strategic page content into context/overview page - added GoalHistory component + quick links, converted strategic to redirect (2026-01-04)
- [x] [UI][P1] Create new reports/trends page for trend-type data from strategic page - created trends page with TrendSummaryCard, Market Trends, Trend Insights (2026-01-04)
- [x] [UI][P1] Move competitor-type data from strategic to existing reports/competitors page - competitors already in reports, quick link added to overview (2026-01-04)
- [x] [UI][P1] Move industry benchmarks from context/metrics to reports/benchmarks - removed inline display, kept simple link to reports/benchmarks (2026-01-04)

### P1 - Dashboard Consolidation (COMPLETED 2026-01-04)

- [x] [UI][P1] Remove key-metrics from context menu and integrate into dashboard key metrics section - converted /context/key-metrics to redirect, updated ValueMetricsPanel links to /context/metrics (2026-01-04)
- [x] [UI][P1] Populate dashboard research section with insights from meetings/mentor/data analysis - created ResearchHeadlinesWidget using existing getInsights() API (2026-01-04)
- [x] [UI][P1] Display research insights as newspaper-style headlines with concise taglines and links - newspaper-style layout with category badges, clickable links to source meetings (2026-01-04)

---

## New Tasks (from _TODO.md, 2026-01-04 - Batch 2)

### P1 - High

- [x] [DATA][P1] Fix data analysis column detection: ensure loaded dataset column names are available when asking questions in analysis tab (2026-01-04)
- [x] [DATA][P1] Auto-run exploratory analysis on dataset load: show top-level insights (summary stats, distributions, notable patterns) as part of load flow (2026-01-04)
- [x] [UI][P1] Generated articles: add click-through to review full article content (2026-01-04)
- [x] [UI][P1] Generated articles: add "regenerate with changes" feature (up to 3 user-specified changes + tone selector) (2026-01-04)
- [x] [UI][P1] Generated articles: use website/brand tone from context for initial tone of voice (2026-01-04)

### P2 - Medium

- [x] [UI][P2] Fix duplicate breadcrumbs on mentor page - removed page-level Breadcrumb, layout handles it (2026-01-04)
- [x] [UI][P2] Fix duplicate breadcrumbs on SEO page - removed page-level Breadcrumb, layout handles it (2026-01-04)
- [x] [SEO][P2] Remove industry box from SEO page; add CTA linking to context/overview if industry/product info not populated (2026-01-04)
- [x] [SEO][P2] Allow users to manually add their own SEO topics - added form with keyword + notes fields above topics table (2026-01-04)
- [x] [SEO][P2] Add "autogenerate topics" button using AI analysis - uses discover_topics() service, filters duplicates (2026-01-04)
- [x] [UI][P2] Fix analysis output formatting: render markdown/HTML properly instead of raw text - updated InsightsPreview.svelte to use MarkdownContent for narrative_summary and insight.detail (2026-01-04)
- [x] [NAV][P2] Move peer benchmarks from context to reports/benchmarks as a tab (industry tab + peer tab) - created IndustryBenchmarksTab/PeerBenchmarksTab components, added URL-synced tabbed interface, updated Header navigation (2026-01-04)
- [x] [CONTEXT][P2] Metrics: allow users to remove metrics marked "not relevant to me" - added is_relevant column, PATCH /api/v1/business-metrics/{key}/relevance endpoint, dismiss UI with confirmation (2026-01-04)
- [x] [CONTEXT][P2] Metrics: add ability to restore removed metrics from hidden section - added include_irrelevant query param, collapsible Hidden Metrics section with restore button (2026-01-04)
- [x] [CONTEXT][P2] Metrics: add "need a new metric?" CTA linking to feature request - added mailto:feedback@boardofone.com CTA below benchmarks link (2026-01-05)
- [x] [DATA][P2] Extend metrics with D2C/product-specific metrics - added InsightCategory values (INVENTORY, MARGIN, CONVERSION, AOV, COGS, RETURNS), CATEGORY_TO_METRIC_KEY mappings, METRIC_BUSINESS_TYPES for filtering, metric templates migration (2026-01-05)
- [x] [CONTEXT][P2] Metrics: smart selection - show top 5 relevant metrics based on business context, others optional/progressive (2026-01-05)

---

_For detailed implementation notes, see git history._
