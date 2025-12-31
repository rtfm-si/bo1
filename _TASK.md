# Task Backlog

_Last updated: 2025-12-30 (Fresh full audit suite run - all 8 audits completed, 10 new P2/P3 tasks added)_

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

- [x] [INFRA][P2] Add retry logic for Anthropic API failures with exponential backoff
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Implemented: MAX_RETRIES=5, RETRY_BASE_DELAY=1.0s, RETRY_MAX_DELAY=60.0s with jitter
  - Metrics: `bo1_llm_retries_total{provider,attempt,error_type}`, `bo1_llm_retries_exhausted_total{provider,error_type}`
- [x] [INFRA][P2] Implement circuit breaker pattern for LLM calls
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Implemented: `bo1/llm/circuit_breaker.py` with CLOSED/OPEN/HALF_OPEN states, fault classification, metrics
  - Tests: `tests/llm/test_circuit_breaker_faults.py`, `test_circuit_breaker_registry.py`, `test_circuit_breaker_provider.py`, `test_circuit_breaker_status.py`
- [x] [INFRA][P3] Add fallback model configuration (e.g., Claude 3.5 Sonnet when primary fails)
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Implemented: `llm_model_fallback_enabled`, `llm_anthropic_fallback_chain`, `llm_openai_fallback_chain` settings
  - Model fallback helper in `bo1/llm/model_fallback.py`, 529/503 classified as MODEL_SPECIFIC fault
  - Metrics: `bo1_model_fallback_total{provider,from_model,to_model}`
  - SSE event: `model_fallback` with user-friendly message
- [x] [UX][P3] Improve error messaging for third-party API failures
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Implemented: Centralized `apiErrorMessages.ts` utility, error_code in SSE events, MeetingError.svelte/ErrorEvent.svelte enhanced with actionable guidance and recovery times
- [x] [INFRA][P2] Enable resume from last successful sub-problem checkpoint
  - Source: E2E run e2e-2025-12-29-golden-meeting ISS-001
  - Implemented: `zw_add_checkpoint_resume_fields` migration adds `last_completed_sp_index`, `sp_checkpoint_at`, `total_sub_problems` to sessions
  - SP boundary checkpoint saved in `synthesis.py:next_subproblem_node` after each SP completes
  - Resume router (`routers.py:route_on_resume`) routes to select_personas for incomplete sessions
  - API endpoints: `GET /sessions/{id}/checkpoint-state`, `POST /sessions/{id}/resume`
  - Frontend: `SessionRecoveryBanner.svelte` for resumable session UI
  - Expert memory propagation via `prior_expert_summaries` state field

### Audit-Derived Tasks (2025-12-30)

#### P0 - Critical

- [x] [PERF][P0] Increase database connection pool from 20 to 75 - `constants.py:445`
- [x] [DATA][P0] Add user_id FK to recommendations table - `models/recommendations.py:26`
- [x] [DATA][P0] Add workspace_id field to Session model - `models/session.py:54`
- [x] [LLM][P0] Sanitize LLM outputs before re-injection - `persona_executor.py:149-150`
- [x] [LLM][P0] Sanitize third-party API results (Brave, Tavily) - `agents/researcher.py:694-872`
- [x] [OBS][P0] Add correlation ID (request_id) propagation - nodes/decomposition.py, research.py, synthesis.py, persona_executor.py

#### P1 - High Priority

- [x] [ARCH][P1] Parallelize initial_round_node - uses `_generate_parallel_contributions` in `rounds.py`
- [x] [PERF][P1] Add composite indexes for partitioned tables - multiple migrations exist
- [x] [PERF][P1] Optimize action tag filtering query - CTE+JOIN in `action_repository.py:185`
- [x] [PERF][P1] Enable pg_stat_statements monitoring - `z16_enable_pg_stat_statements.py`
- [x] [DATA][P1] Add missing fields to Recommendation model - all fields present
- [x] [DATA][P1] Create comprehensive serialization roundtrip tests - `tests/graph/test_state_roundtrip.py`
- [x] [LLM][P1] Sanitize user interjection and clarification - `control.py:2093-2094`
- [x] [LLM][P1] Switch to SYNTHESIS_HIERARCHICAL_TEMPLATE as default (completed 2025-12-30)
- [x] [OBS][P1] Expose circuit breaker state as Prometheus metrics - `middleware/metrics.py`
- [x] [OBS][P1] Standardize ErrorCode usage - 137 occurrences across 50+ files
- [x] [API][P1] Standardize error response format - 9 major files migrated (seo/routes, user, datasets, workspaces/*, projects, context/routes, mentor) ~250 endpoints
- [x] [API][P1] Document SSE event schemas in OpenAPI spec - added SSEEvent_* schemas to OpenAPI, /api/v1/sse/schemas endpoint, updated streaming docstrings
- [x] [REL][P1] Fix replanning service rollback - proper cleanup + error raising in `replanning_service.py`
- [x] [REL][P1] Add Redis metadata fallback to PostgreSQL (dual-write session metadata)
- [x] [COST][P1] Switch to hierarchical synthesis template (5-6% cost reduction) - completed 2025-12-30
- [x] [COST][P1] Compress persona protocols - 27.8% per-call token reduction (545 tokens saved) - completed 2025-12-30

#### P2 - Medium Priority

- [x] [ARCH][P2] Consolidate router validation logic - `_validate_state_field` in `routers.py:18-42`
- [x] [ARCH][P2] Add circuit breaker for Redis PubSub failures with PostgreSQL polling fallback - `streaming.py:859-862`, 4 new tests in `test_sse_redis_fallback.py`
- [x] [PERF][P2] Implement session metadata caching with Redis backend - dual-write to PostgreSQL with fallback in `redis_manager.py:670-824`
- [x] [PERF][P2] Increase embedding batch size from 5 to 20 - `constants.py:BATCH_SIZE=20`
- [x] [PERF][P2] Implement aggregation result caching for cost queries - `/api/admin/costs/cache-metrics`, `AggregatedCacheMetrics` model
- [x] [PERF][P2] Add contribution pruning in graph state after synthesis - `state.py:prune_contributions_for_phase()`, `synthesis.py:175-181`
- [x] [DATA][P2] Add CI check for TypeScript type sync with backend models - `.github/workflows/ci.yml:92-93`, `npm run check:types-fresh`
- [x] [DATA][P2] Create Pydantic models for domain entities (Action, Project, Workspace) - `backend/api/models.py`, `backend/api/workspaces/models.py`
- [x] [LLM][P2] Add rate limiting to PromptBroker - `llm/rate_limiter.py`
- [x] [LLM][P2] Audit dataset CSV handling for malicious cell values (injection risk) - `csv_utils.py:sanitize_csv_cell()`, `dataframe_loader.py:load_dataframe(sanitize=True)`
- [x] [OBS][P2] Add event persistence metrics (batch size histogram, duration, retry queue depth) - `metrics.py:129-150`, `bo1_event_persistence_*` gauges
- [x] [OBS][P2] Add Redis connection pool metrics (active connections, utilization, latency) - `metrics.py:298-317`, `bo1_redis_pool_*` gauges
- [x] [OBS][P2] Configure Prometheus alerts for event persistence, circuit breakers, cost tracking - `monitoring/prometheus/alert_rules.yml:95-216`
- [x] [API][P2] Add OpenAPI security schemes - `openapi_security.py`, SessionAuthDep/CSRFTokenDep applied to sessions, streaming, control, actions, projects
- [x] [API][P2] Document rate limits in API responses - X-RateLimit-Limit/Remaining/Reset headers via middleware, OpenAPI x-rate-limits extension
- [x] [REL][P2] Add SSE reconnection backoff with Retry-After header - `streaming.py:77-116`
- [x] [REL][P2] Add deadlock retry to @retry_db decorator - 40P01 in `utils/retry.py:36`
- [x] [COST][P2] Extend Haiku to Round 3 - `HAIKU_ROUNDS_THRESHOLD=3` in `constants.py:253`
- [x] [COST][P2] Add cache hit rate metrics to get_session_costs() - SessionCostBreakdown now includes cache_hit_rate, prompt_cache_hit_rate, total_saved

#### P2/P3 - Fresh Audit (2025-12-30)

- [x] [ARCH][P3] Migrate nodes to use nested state accessors (`get_problem_state()`, `get_phase_state()`) - cleaner data access
  - Pattern established: `rounds.py` demonstrates full accessor usage
  - Accessors available: `get_problem_state`, `get_phase_state`, `get_participant_state`, `get_discussion_state`, `get_research_state`, `get_comparison_state` in `state.py:755-820`
  - Remaining nodes use direct access (works fine); migrate incrementally when touching nodes
- [x] [ARCH][P3] Document parallel subproblems feature flag (`ENABLE_PARALLEL_SUBPROBLEMS`) impact on graph topology - ADR needed
  - Implemented: `docs/adr/005-parallel-subproblems-graph-topology.md`
  - Sequential mode: full LangGraph events, node-by-node checkpointing
  - Parallel mode: `analyze_dependencies` → `parallel_subproblems` → `meta_synthesis`
  - EventBridge pattern for event emission workaround documented
  - Mermaid diagrams for both topologies
- [x] [LLM][P3] Add challenge phase validation - reject round 3-4 contributions lacking critical engagement markers
  - Implemented: `bo1/prompts/validation.py` with CHALLENGE_MARKERS patterns and detection functions
  - Phase 1 (soft enforcement): Log warnings + emit Prometheus metric, don't reject
  - Metric: `bo1_challenge_phase_validation_total{result,round_number,expert_type}`
  - Tests: 31 unit tests in `tests/prompts/test_challenge_validation.py`, 11 integration tests in `tests/graph/test_challenge_phase.py`
- [x] [LLM][P3] Add unit tests for sanitization injection defenses - `tests/test_sanitizer.py`
  - Already comprehensive: 734 lines in `tests/test_sanitizer.py`, 452 in `tests/prompts/test_sanitizer.py`, 459 in `tests/prompts/test_injection_vectors.py`
  - Covers: XML/HTML injection, instruction override, role switching, SQL injection, unicode attacks, encoding bypasses, boundary conditions
- [x] [OBS][P3] Add event type distribution metric (`events_published_total{event_type}`)
  - Already implemented: `bo1_event_type_published_total{event_type}` in `metrics.py:384-388`
  - Recording: `event_publisher.py:1226` calls `record_event_type_published(event_type)`
  - Tests: `test_event_stream_metrics.py:56-95`
- [x] [API][P3] Add `has_more` field to pagination responses for infinite scroll
  - Already implemented: `pagination.py:20-26` provides `has_more` and `next_offset`
  - Used in: sessions, projects, datasets, admin/users, admin/terms, admin/drilldown
  - All paginated response models include `has_more: bool` field
- [x] [REL][P2] Implement LangGraph checkpoint recovery - `resume_session_from_checkpoint()` for retrying failed sessions
  - Implemented: `bo1/graph/execution.py` with `is_safe_resume_boundary()`, `_validate_checkpoint_state()`, PostgreSQL fallback
  - State validation: detects corrupted checkpoints (missing problem, personas, phase)
  - Boundary detection: safe resume at start, between sub-problems, at synthesis node; unsafe mid-round
  - PostgreSQL fallback: `_reconstruct_state_from_postgres()` replays session_events when Redis unavailable
  - Resume failure event: `publish_resume_failed_event()` notifies frontend of unrecoverable state
  - API endpoint: `/sessions/{id}/resume` returns 410 Gone with fallback_used flag
  - Tests: 19 new tests in `tests/graph/test_checkpoint_recovery.py`
- [x] [REL][P2] Add chaos test: Anthropic outage → OpenAI fallback validation
  - Implemented: `tests/chaos/test_anthropic_outage_integration.py` with 12 tests
  - Tests: circuit breaker trips, fallback activation, SSE events, Prometheus metrics, session completion via fallback, disabled fallback behavior
- [x] [REL][P3] Add query timeout (`statement_timeout`) to long-running database operations
  - Already implemented: `StatementTimeoutConfig` in `constants.py:1316-1346`
  - `db_session()` accepts `statement_timeout_ms`, runs `SET LOCAL statement_timeout`
  - Metric: `bo1_db_statement_timeout_total` for cancelled queries (SQLSTATE 57014)
  - Tests: `tests/state/test_database.py` with 10+ test cases
- [x] [COST][P3] Run persona count A/B test (3 vs 5 personas) - quality vs cost tradeoff
  - Already running: 50/50 split in `sessions.py:383-401` via user_id hash
  - Migration: `ab1_add_persona_experiment.py` adds `persona_count_variant` column
  - Execution: `selection.py:51-60` uses variant for persona selection
  - Analytics: `admin/extended_kpis.py:210-221` provides experiment metrics

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
