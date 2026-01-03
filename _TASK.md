# Task Backlog

_Last updated: 2026-01-03_

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

---

## Feature Audit Tasks (2026-01-03)

### P0 - Critical

- [x] [API][P0] Fix `/api/v1/user/preferences` 500 error - missing `preferred_currency` column; migrations applied to prod (2026-01-03)
- [x] [ROUTE][P0] Deploy `/settings/security` route - 2FA code verified, migration applied, tests pass (22/22)

### P1 - High

- [x] [API][P1] Investigate `/context/strategic` 503 - transient pool exhaustion during audit; 503+Retry-After handling already present (2026-01-03)

### P2 - Medium

- [x] [API][P2] Fix `/context/peer-benchmarks` 404 errors - added API_CONTEXT_MISSING and API_INDUSTRY_NOT_SET error codes with context-specific frontend guidance (2026-01-03)

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

### January 2026 (Week of 01/02)

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

_For detailed implementation notes, see git history._
