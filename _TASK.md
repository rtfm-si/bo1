# Task Backlog

_Last updated: 2026-01-03 (Task decomposition from _TODO.md)_

---

## Open Tasks

### Active Bugs

- [x] [AUTH][P0] Fix Google social login for existing email users
  - Root cause: SuperTokens AccountLinking recipe was not enabled
  - Users who signed up with email/password couldn't sign in with Google OAuth using same email
  - Added `accountlinking` and `emailverification` recipes to `supertokens_config.py`
  - Implemented `should_do_automatic_account_linking()` callback to auto-link verified emails
  - OAuth emails (Google, LinkedIn, GitHub) auto-link without extra verification
  - Email/password accounts require email verification before linking
  - Added logging for account linking events
  - Tests: 10 unit tests in `tests/api/test_account_linking.py`
- [x] [ADMIN][P0] Fix user impersonation: showing logged-in admin details instead of impersonated user data
  - Backend: `/api/v1/auth/me` now returns target user data with impersonation metadata
  - Added `is_impersonation`, `real_admin_id`, `impersonation_write_mode`, `impersonation_expires_at`, `impersonation_remaining_seconds` to response
  - Frontend: User type extended with impersonation fields; layout uses user store instead of admin API call
  - Tests: 4 new unit tests in `tests/api/test_admin_impersonation.py::TestAuthMeImpersonation`
- [x] [DATA][P0] Fix metrics not saving when user adds additional metrics
  - Root cause: `apply_metric_suggestion()` passed same dict for both `new_context` and `existing_context`
  - Fix: Shallow copy `existing_context` before modifying `context_data`
  - Tests: 6 new unit tests in `tests/api/context/test_apply_metric_suggestion.py`
- [x] [CONTEXT][P0] Fix competitor addition not working
  - Synced `ManagedCompetitorResponse` frontend type with backend (added `relevance_warning`, `relevance_score`)
  - Added 5 integration tests in `tests/api/context/test_managed_competitors.py::TestManagedCompetitorAPI`
  - Verified skeptic check failure doesn't block add (try/except in route handler lines 1778-1789)
  - Regenerated frontend types from OpenAPI spec

### P0 Features

- [x] [LLM][P0] Adapt language style to user's business context: use website analysis to tailor responses to product-based vs B2B SaaS models
  - Created `bo1/prompts/style_adapter.py` with StyleProfile enum (B2B_SAAS, B2C_PRODUCT, B2C_SERVICE, AGENCY, ENTERPRISE, NEUTRAL)
  - `detect_style_profile()` analyzes business_model, brand_tone, product_categories to select profile
  - `get_style_instruction()` generates `<communication_style>` XML block for prompt injection
  - Updated `format_business_context()` in mentor.py and data_analyst.py to include style block
  - Updated mentor system prompts to reference communication_style block
  - Updated `compose_persona_contribution_prompt()` to accept business_context parameter
  - Updated `compose_synthesis_prompt()` to accept business_context parameter
  - Wired business_context through PromptBuilder for persona contributions
  - Tests: 44 unit tests in `tests/prompts/test_style_adapter.py`
- [x] [UX][P0] Add default currency setting to user preferences for metric display (£/$/€)
  - Migration: `zza_add_preferred_currency.py` adds `preferred_currency` column to users table (GBP default)
  - Backend: Extended `PreferencesResponse`/`PreferencesUpdate` models with `preferred_currency` field (GBP|USD|EUR)
  - API: GET/PATCH `/api/v1/user/preferences` now includes `preferred_currency`
  - Frontend store: Created `preferences.ts` store with `loadPreferences()` and `preferredCurrency` derived store
  - Utility: Created `currency.ts` with `formatCurrency()`, `isMonetaryMetric()`, `parseCurrencyValue()`
  - Settings UI: Added currency selector to `/settings/account` with auto-save toggle buttons
  - Dashboard: Updated `ValueMetricsPanel.svelte` to format monetary metrics with user's preferred currency
  - Key Metrics: Updated `/context/key-metrics` page with currency-aware value formatting
  - Tests: 7 unit tests in `tests/api/test_currency_preferences.py`

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

### Backlog (from _TODO.md, 2026-01-02)

#### Auth & Security

- [x] [AUTH][P2] Enforce stronger password requirements (12+ chars, letters+numbers)
  - Implemented: `validate_password_strength()` in `backend/api/supertokens_config.py:87-111`
  - 17 unit tests in `tests/api/test_password_validation.py`
- [x] [AUTH][P3] Detect insecure passwords and prompt users to update on login
  - Backend: Password check in `sign_in` override sets `password_upgrade_needed` flag in users table
  - Migration: `zx_add_password_upgrade_needed.py` adds column
  - API: `POST /api/v1/user/upgrade-password` endpoint with old/new password validation
  - Frontend: `PasswordUpgradePrompt.svelte` modal with 7-day snooze, integrated in app layout
  - Auth store: `passwordUpgradeNeeded` derived store and `clearPasswordUpgradeFlag()` helper
  - Tests: 7 unit tests in `tests/api/test_password_upgrade.py`
- [ ] [AUTH][P4] Implement magic link passwordless login option
- [ ] [AUTH][P4] Add 2FA login support

#### Projects API Fixes

- [x] [API][P2] Fix `/api/v1/projects/autogenerate-suggestions` returning 500 - route ordering fix
- [x] [API][P2] Fix `/api/v1/projects/context-suggestions` returning 500 - route ordering fix

#### SEO API Fixes

- [x] [API][P2] Fix `/api/v1/seo/history` returning 404 - route exists, tested
- [x] [API][P2] Fix `/api/v1/seo/autopilot/config` returning 500 - fixed db_session usage
- [x] [API][P2] Fix `/api/v1/seo/articles` returning 404 - route exists, tested
- [x] [API][P2] Fix `/api/v1/seo/topics` returning 404 - route exists, tested

#### Analysis Features

- [x] [UX][P2] Show question history in "Ask a question" (not just latest answer)
  - Added `DatasetChatHistory.svelte` sidebar component
  - Updated `DatasetChat.svelte` with `selectedConversationId` prop and conversation loading
  - Updated dataset page layout with history sidebar next to chat
  - API client methods already exist: `getConversations`, `getConversation`, `deleteConversation`
- [x] [UX][P3] Improve question UX guidance to help users find right answers
  - Added `ColumnReferenceSidebar.svelte`: Collapsible sidebar showing available columns with click-to-copy, semantic type badges, and business meaning
  - Added `QueryTemplates.svelte`: Expandable quick query chips (Ranking, Trends, Comparison, Distribution, Correlation, Segments) with auto-filled column names
  - Enhanced `DatasetChat.svelte` empty state: Shows available column names and contextual example based on data types
  - Improved error handling: Parses error types (no_results, invalid_column, timeout, syntax) with specific remediation guidance and "Show columns" link
  - Wired components in dataset page with column sidebar toggle and query template selection
- [x] [FEATURE][P2] Add chart analysis rendering with detail/simple dual-view modes
  - Added `plotly.js-basic-dist` npm package (~1MB minimal bundle)
  - Created `ChartRenderer.svelte` with detail/simple dual-view modes
    - Detail mode: Full interactive Plotly chart with hover, zoom, pan
    - Simple mode: Static SVG sparkline with key stats (min/max/mean/latest/trend)
    - Mode toggle button, expand button for fullscreen
  - Created `ChartModal.svelte` for fullscreen chart viewing
  - Created Plotly TypeScript declarations in `types/plotly.d.ts`
  - Updated `DataInsightsPanel.svelte`:
    - Added chart preview on suggested chart click via `previewChart()` API
    - Renders chart in simple mode with expand option to modal
  - Updated `ChatMessage.svelte`:
    - Added "Preview" button for messages with `chart_spec`
    - Loads chart on demand via `previewChart()` API
    - Renders chart with expand to fullscreen modal

#### Datasets Features

- [x] [API][P2] Fix `/api/v1/datasets/{id}/insights` returning 422 error
  - Added `response_model=DatasetInsightsResponse` to endpoint
  - Added `cached: bool` field to `DatasetInsightsResponse` model
  - Regenerated OpenAPI spec and frontend types
  - Note: 422 is intentional when dataset not profiled (handled gracefully by frontend)
- [x] [DATA][P2] Persist analysis history across sessions
  - Backend: `_stream_ask_response()` in `datasets.py` saves chart_spec to `dataset_analyses` via `create_analysis()`
  - Done event includes `analysis_id` when chart saved
  - Frontend: `DatasetChat.svelte` accepts `onAnalysisCreated` callback, triggers on analysis_id in done event
  - Dataset page passes `fetchAnalyses` as callback to refresh gallery
  - `AnalysisGallery.svelte` updated to render Plotly charts via `previewChart` API when `chart_url` is null but `chart_spec` exists
- [x] [DATA][P2] Persist "Ask a question" history and show conversation thread
  - Migration: `zy_add_dataset_conversations.py` creates `dataset_conversations` + `dataset_messages` tables
  - PostgreSQL repository: `backend/services/dataset_conversation_pg_repo.py` with full CRUD
  - ConversationRepository dual-write: PostgreSQL source of truth, Redis 24h cache
  - GDPR integration: export/delete via `_collect_dataset_conversations` / `_delete_dataset_conversations`
  - Tests: 15 unit tests in `tests/services/test_dataset_conversation_pg_repo.py`
- [x] [FEATURE][P2] Run exploratory analytics on dataset load with auto-generated charts and next-step suggestions
  - Added `SuggestedChart` model in `backend/api/models.py` with `chart_spec`, `title`, `rationale`
  - Added `suggested_charts` field to `DatasetInsights` model (defaults to empty list)
  - Added `_generate_chart_suggestions()` in `backend/services/insight_generator.py` with heuristics:
    - Date + numeric → line chart (time series)
    - Categorical + numeric → bar chart
    - Numeric only → histogram/distribution
    - Two numeric → scatter plot
    - Categorical only → pie chart
  - Limits to 3 suggestions, scans first 20 columns for wide datasets
  - Added `POST /datasets/{id}/preview-chart` lightweight preview endpoint (no persistence)
  - Frontend: Extended `DataInsightsPanel.svelte` with Suggested Charts section
  - API client: Added `previewChart()` method
  - Tests: 15 unit tests in `tests/services/test_chart_suggestions.py`, 4 model tests in `tests/api/test_datasets.py`

#### Context System Fixes

- [x] [FEATURE][P2] Use context/insights data to auto-populate context/metrics and context/key-metrics
  - Added `get_metrics_from_insights()` service function in `backend/api/context/services.py`
  - Maps clarification categories (revenue, customers, growth, team) to context fields
  - Filters by confidence >= 0.6, recency <= 90 days, deduplicates by field
  - API: `GET /context/metric-suggestions` - returns suggestions from insights
  - API: `POST /context/apply-metric-suggestion` - applies suggestion and updates context
  - Frontend: `MetricSuggestions.svelte` component with apply/dismiss per suggestion
  - Integrated into `/context/key-metrics` page above metrics grid
  - Tests: 27 unit tests in `tests/api/test_context_services.py`
- [x] [API][P2] Fix `/api/v1/context/trends/summary/refresh` returning 403 (auth or permission issue)
  - Added CSRF token header to frontend fetch call in `frontend/src/routes/(app)/context/strategic/+page.svelte`
  - Added tests in `tests/api/test_peer_benchmarks.py`
- [x] [API][P2] Fix `/api/v1/peer-benchmarks` and `/preview` returning 500
  - Added try/catch error handling in `get_preview_metric()` and `get_peer_comparison()` service functions
  - Service functions now gracefully return None on database errors instead of raising exceptions
  - Routes already had `@handle_api_errors` decorator which converts None to 404 response
  - Added 24 unit tests in `tests/api/test_peer_benchmarks.py`

#### Competitors Features

- [x] [DATA][P2] Persist competitor enrichment data across sessions
  - Extended `ManagedCompetitor` model with `relevance_score`, `relevance_flags`, `relevance_warning` fields
  - Updated `auto_save_competitors()` to persist enrichment data including serialized `RelevanceFlags`
  - Updated list endpoint to return enrichment data with proper deserialization
  - Added relevance badges to `CompetitorManager.svelte` (green >0.66, amber >0.33, red ≤0.33)
  - Added warning tooltip when `relevance_warning` is present
  - Tests: 5 unit tests in `tests/api/test_context_services.py::TestAutoSaveCompetitorsEnrichment`
- [x] [LLM][P3] Improve competitor enrichment extraction quality
  - Enhanced LLM prompt to extract descriptions, categories (direct/indirect/adjacent), and confidence
  - Added URL normalization: extracts company domains from G2/Capterra links, guesses domain from name
  - Added competitor name normalization and deduplication (removes Inc/LLC/domain suffixes, merges data)
  - Improved skeptic prompt with confidence-weighted scoring (high=1.0x, medium=0.7x, low=0.4x)
  - Added Redis caching for skeptic evaluations (24h TTL, context-hash aware)
  - Tests: 102 passing in test_competitor_skeptic.py and test_competitor_detection.py

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
