# Task Backlog

_Last updated: 2025-12-22 (Supply-chain & web security scan)_

---

## Blocked / Deferred / Manual

### External/Manual Setup (User action required)

- [x] [DEPLOY][P1] Sign DPAs with data processors (Supabase, Resend, Anthropic, DigitalOcean)
- [ ] [LAUNCH][P1] Switch Stripe to live mode
- [ ] [LAUNCH][P1] Test emergency access procedures
- [ ] [BILLING][P4] Configure Stripe products/prices (Free/Starter/Pro)

### Blocked on Dependencies

- [ ] [EMAIL][P4] Payment receipt email trigger - blocked on Stripe integration
- [ ] [SOCIAL][P3] Direct posting to social accounts - blocked on user decision (see \_PLAN.md)

### Deferred by Design

- [ ] [DATA][P2] DuckDB backend for large datasets (>100K rows) - defer until needed
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have

### Needs Clarification

- [ ] [MONITORING][P1] Kubernetes deployment manifest - are we using kubernetes?
- [x] [SEO][P3] Clarify scope of "auto seo" feature - implemented as blog system with AI generation
- [ ] [MONITORING] Clarify "grafana logs: value A" (ambiguous)

### User-Owned

- [ ] [DOCS][P3] Help pages content review and polish (Si's todo)

---

## Incomplete Tasks

### Security [SECURITY]

- [x] [SEC][WEB][P1] Sanitize blog page HTML rendering with DOMPurify (XSS via `{@html renderContent()}` in `/blog/[slug]`)
  - Added `DOMPurify.sanitize()` wrapper around `renderContent()` output in `frontend/src/routes/blog/[slug]/+page.svelte`
  - 20 unit tests in `frontend/src/lib/utils/sanitize-blog.test.ts`
- [x] [SEC][SUPPLY][P2] Pin npm dependency versions (replace `^` ranges with exact versions for 8 packages)
  - Pinned: @lucide/svelte, clsx, openapi-typescript, tailwind-merge, tailwind-variants, tw-animate-css, driver.js, html2canvas
- [x] [SEC][SUPPLY][P2] Update `cookie` package to >=0.7.0 (GHSA-pxg6-pf52-xh8x in @sveltejs/kit dependency)
  - Added `overrides.cookie: "^1.0.0"` to package.json; cookie now at v1.1.1
- [x] [SEC][WEB][P3] Add CSP header in SvelteKit hooks.server.ts for dev mode consistency
  - Added `transformPageChunk` to extract nonce from SvelteKit's generated HTML
  - Inject CSP header with nonce-based script-src for HTML responses
  - Matches production nginx CSP policy directives
- [x] [SECURITY][P1] Fix Redis healthcheck to avoid password exposure (use REDISCLI_AUTH env var instead of `-a` flag)
- [x] [SECURITY][P2] Add rate limiting to CSRF-exempt `/api/v1/waitlist` endpoint
- [x] [SECURITY][P2] CSRF token rotation on auth state change (regenerate in SuperTokens sign-in callback)
- [x] [SECURITY][P3] Honeypot detection for prompt injection (hidden fields for automated attack detection)
- [x] [SECURITY][P3] Audit log alerting for admin impersonation usage

### QA Automation [QA]

- [x] [QA][P1] Playwright sweep: test ALL admin page links and buttons, write findings report
- [x] [QA][P1] Playwright sweep: test meeting creation and completion flow, write findings report

### Admin Features [ADMIN]

- [x] [ADMIN][P2] Add user impersonation access point to admin UI (link/button to initiate impersonation from user list or user detail page)
  - Impersonate button with Eye icon in `/admin/users` page (line 416-421)
  - Full impersonation modal with confirmation workflow (line 598-690)
  - Backend API: `backend/api/admin/impersonation.py`
  - Tests: `tests/api/test_admin_impersonation.py`, `tests/api/admin/test_impersonation.py`
- [x] [ADMIN][P2] Admin UI toggle for `PROMPT_INJECTION_BLOCK_SUSPICIOUS` (emergency disable - LLM shutdown)
- [x] [ADMIN][P3] Send branded email (from template) to end user from within admin
- [x] [ADMIN][P3] Expose other emergency-disable config toggles in admin UI

### LLM Alignment [LLM]

- [x] [LLM][P2] Output format validation with re-prompt on XML parsing failure (standardize across nodes)
- [x] [LLM][P3] Document sanitization requirements per prompt template; add injection vector tests
  - Created `bo1/prompts/SANITIZATION.md` documenting all sanitization functions, prompt builders, and API entry points
  - Added 68 injection vector tests in `tests/prompts/test_injection_vectors.py`
  - Added 31 integration tests in `tests/security/test_template_injection.py`

### API Contract [API]

- [x] [API][P2] Define and enforce structured error response schema (replace ad-hoc HTTPException)
- [x] [API][P2] Document SSE event schemas - created `frontend/src/lib/api/sse-events.ts` with 40+ typed event definitions
- [x] [API][P3] Add `response_model` to endpoints returning raw dicts
- [x] [API][P3] Define API versioning strategy for breaking changes (ADR, middleware, deprecation decorator)

### Data Model [DATA]

- [x] [DATA][P2] Automated schema validation tests (Pydantic models vs migration schema)
- [x] [DATA][P2] Remove `[key: string]: any` escape hatch from `SessionDetailResponse.state` in frontend types
- [x] [DATA][P3] Update CLAUDE.md to replace `state_to_v1/v1_to_state` references with actual function names
- [x] [DATA][P3] Auto-generate frontend TypeScript types from Pydantic models via openapi-typescript
  - Added `openapi-typescript` package and `npm run generate:types` script
  - Created `make openapi-export` to export OpenAPI spec from backend
  - Generated types in `frontend/src/lib/api/generated-types.ts`
  - Added freshness check (`npm run check:types-fresh`) with pre-commit hook and CI integration
  - Re-exported key types in `types.ts` with `Generated*` prefix for gradual migration
- [x] [DATA][P3] Fix SSE event type narrowing in meeting components (69 strict type errors exposed by new SSEEventMap)

### Observability [OBS]

- [x] [OBS][P2] Standardize error logging format with error codes for easier aggregation
- [x] [OBS][P3] Log level tuning per environment (reduce noise in production)

### Reliability [REL]

- [x] [REL][P2] Extend circuit breaker pattern to database and Redis calls (currently LLM-only)
- [x] [REL][P2] Ensure all retry callsites use `total_timeout` parameter consistently
- [x] [REL][P3] Wire chaos tests (`tests/chaos/`) into CI for automated resilience verification
- [x] [REL][P3] SSE event sequence detection for reconnection gaps

### Cost Optimization [COST]

- [x] [COST][P2] Centralize model selection config for easier A/B testing of cheaper models
- [x] [COST][P2] Add `cache_control` markers to prompt builds that don't currently use them
- [x] [COST][P3] Expose research cache hit rate metrics to admin dashboard
- [x] [COST][P3] Use full SHA-256 hash for LLM cache keys (currently first 16 chars)

### Infrastructure [INFRA]

- [x] [INFRA][P3] Evaluate WAF (Web Application Firewall) for additional protection
  - Recommendation: No additional WAF needed - existing nginx WAF + rate limiting is comprehensive
  - Report: `docs/infra/waf-evaluation.md`
- [x] [INFRA][P3] SIEM integration for centralized threat detection
  - Grafana security dashboard: `monitoring/grafana/dashboards/security.json`
  - Loki alerting rules: `monitoring/loki/loki-alerting-rules.yml`
  - Promtail security event labels in `monitoring/promtail/promtail-config.yml`
  - Grafana contact point routing to ntfy: `monitoring/grafana/provisioning/alerting/security-alerts.yml`
  - Structured security event logging: `log_security_event()` in `bo1/logging/errors.py`
- [x] [INFRA][P3] Automated dependency vulnerability scanning in CI (beyond pip-audit)
  - Added `.github/dependabot.yml` for Python, npm, and GitHub Actions
  - Added Trivy container scanning job to CI (fails on CRITICAL/HIGH)
  - Existing: pip-audit, npm audit, OSV Scanner, dependency-review-action
- [x] [DEPLOY][P1] Setup uptime monitoring (UptimeRobot) - create monitors for boardof.one, /health
- [x] [LAUNCH][P1] Verify Alertmanager running in prod, set NTFY_TOPIC env var

### Context & Goals [CONTEXT]

- [x] [CONTEXT][P2] Capture company goals/objectives as meeting context (allow users to define strategic objectives)
  - Added `strategic_objectives` field to `BusinessContext` model (list of up to 5 strings)
  - Added to `CONTEXT_FIELDS` and JSONB serialization in `user_repository.py`
  - Context injection in `context_collection_node.py` adds "## Strategic Objectives" section
  - UI section added to `/context/overview` page with add/remove functionality
  - Frontend types updated in `types.ts`
  - 11 tests added in `tests/api/context/test_strategic_objectives.py`

### Branding & SEO [BRAND/SEO]

- [x] [BRAND][P2] Update company attribution to "Sico Software Ltd" (footer, legal pages, about)
- [x] [SEO][P2] Configure robots.txt and meta tags for AI tool discovery (ChatGPT, Claude, etc.)
- [x] [SEO][P3] Auto-SEO content pages: AI-generated topic pages with admin approval workflow
  - Backend: `/api/v1/blog/posts` public API, blog_repository CRUD, AI content generation
  - Admin UI: `/admin/blog` with generate/edit/publish/schedule workflow
  - Frontend: `/blog` list page, `/blog/[slug]` detail page with SEO meta tags
  - Tests: `tests/api/test_public_blog.py` (8 tests passing)

### Landing Page [LANDING]

- [x] [LANDING][P3] Remove or verify social links (bottom right of landing page)

### Auth [AUTH]

- [x] [AUTH][P3] Setup additional social login providers (LinkedIn, Bluesky, Twitter/X)
  - Backend: SuperTokens config in `backend/api/supertokens_config.py` supports all providers
  - Feature flags: `TWITTER_OAUTH_ENABLED`, `BLUESKY_OAUTH_ENABLED` (default false until creds added)
  - Frontend: Login/signup pages have buttons for all providers
  - Tests: 23 auth tests passing (`test_auth_twitter.py`, `test_auth_bluesky.py`, `test_auth_linkedin.py`)

### Production Bugs [BUG]

- [x] [BUG][P1] Fix admin blog API 429 rate limiting (all `/api/admin/blog/posts*` endpoints returning 429)
  - Removed per-endpoint `@limiter.limit(ADMIN_RATE_LIMIT)` from all 9 blog endpoints
  - Blog admin endpoints now use global IP limit only (500/min), matching other high-traffic admin pages
  - Authentication still required via API key
- [x] [BUG][P2] Fix blog post generation returning "Invalid input: Blog generation returned invalid JSON format"
  - Added robust JSON parser (`extract_json_from_response`) to handle markdown wrapping and trailing text
  - Added retry logic (1 retry) with explicit re-prompt on parse failure
  - Added 7 unit tests in `tests/services/test_content_generator.py`
- [x] [BUG][P1] Fix status.boardof.one returning 502 Bad Gateway
  - Added `uptime-kuma` service to `docker-compose.infrastructure.yml`
  - Port: 127.0.0.1:3003:3001, Volume: uptime-kuma-data, Network: bo1-network
  - Resource limits: 0.25 CPU, 256M memory
  - Requires prod deployment to apply; may need first-run admin setup via web UI
- [x] [BUG][P2] Fix action delete button not working (no response on click)
  - Added `e.stopPropagation()` to all action buttons in TaskCard.svelte (Start, Complete, Move back, Reopen, Delete, expand)
  - Added stopPropagation to delete confirmation overlay to prevent parent button click
- [x] [BUG][P2] Fix action reminder-settings 404 (`/api/v1/actions/{id}/reminder-settings` returns "Action not found")
  - Root cause: `db_session()` calls missing `user_id` parameter for RLS context
  - Fixed: Added `user_id` to `get_reminder_settings`, `update_reminder_settings`, `snooze_reminder`, `get_pending_reminders`
  - Fixed: Removed forward reference quotes from `ReminderSettingsUpdate` type annotation in API endpoint
  - Added 7 HTTP API integration tests in `tests/api/test_action_reminders.py`
- [x] [UX][P3] Add admin/blog page link from main admin page
  - Added Blog Management card to admin dashboard with FileText icon
  - Links to `/admin/blog`
- [x] [BUG][P1] Fix drag-and-drop action status update: "Invalid task ID format. Expected 'task_N' format" error
  - Fixed `/actions` page to use `updateActionStatus` (UUID-based) instead of `updateTaskStatus` (task_N format)
  - Fixed `handleKanbanStatusChange` and `handleBulkStatusChange` in `/actions/+page.svelte`
- [x] [BUG][P2] Meeting clarification questions don't appear on mobile (meeting appears paused)
  - Added floating mobile action button (lg:hidden) that prompts users to scroll up when questions need answers
  - Improved auto-scroll behavior with multiple attempts and window.scrollTo for mobile Safari compatibility
- [x] [BUG][P2] Submit/skip question buttons still visible after questions have been answered (desktop)
  - Fixed `handleClarificationSubmitted` to immediately update session status/phase, hiding the form before SSE reconnects
- [x] [BUG][P2] Fix UptimeRobot 404 when clicking through from admin system status
- [x] [BUG][P1] Fix `/api/v1/sessions/recent-failures` 404 on dashboard
- [x] [BUG][P1] Fix action status PATCH 422 errors (drag-drop and "start" button)
- [x] [BUG][P2] Fix `/api/v1/projects/unassigned-count` 500 error on projects tab
- [x] [BUG][P2] Fix admin API rate limiting (429s hitting most admin endpoints)
- [x] [BUG][P2] Fix admin sessions page 404 (`/admin/sessions`)
- [x] [BUG][P3] Fix admin error reporting POST 403 (`/api/errors`)

### UX Improvements [UX]

- [x] [UX][P2] Add "raise hand" feature for users to interject during meetings with context or questions
  - Backend: POST `/sessions/{id}/raise-hand` endpoint with rate limiting and injection checks
  - State: Added `user_interjection`, `interjection_responses`, `needs_interjection_response` to graph state
  - SSE: Three new events - `user_interjection_raised`, `interjection_response`, `interjection_complete`
  - Frontend: Floating `RaiseHandButton.svelte` component with modal, integrated in meeting page
  - API client: `raiseHand()` method added
  - Tests: 13 tests in `tests/api/test_raise_hand.py`
- [x] [UX][P2] Add links to monitoring, analytics, and status pages from admin system status
- [x] [UX][P2] Add "ask mentor" button to actions tab (link to mentor with context)
- [x] [UX][P2] Include actions in mentor @ mention popup (currently only shows meetings)
  - Actions tab in `MentionAutocomplete.svelte:127-131`
  - Backend search handles `type == "action"` in `mentor.py:555-572`
- [x] [UX][P2] Add failed meeting acknowledgment UI (mask failures after user acknowledges)
- [x] [UX][P2] Hide actions from unacknowledged failed meetings (prevent orphan/unprogressable actions)

### Integrations [INTEG]

- [x] [INTEG][P3] Add user-level "Sync actions to Google Calendar" toggle in settings (only show if user has Google auth provider; controls whether actions with due dates create calendar events)

---

## Completed Summary (900+ tasks)

### Core Platform

- **Data Analysis Platform**: Ingestion (DO Spaces, CSV, Google Sheets), Profiling, Query Engine, Meeting Integration, Dataset Q&A, UI
- **Meetings & Sessions**: Multi-agent deliberation, SSE streaming, export/sharing, error handling, cap enforcement
- **Actions System**: Kanban, Gantt, reminders, bidirectional status, close/replan, calendar sync
- **Projects**: CRUD, Gantt, auto-generation from actions/context, versioning, workspace constraints
- **Mentor Mode**: Expert personas, proactive patterns, improvement plans, @ mentions

### Business Features

- **Billing**: Stripe integration, tier middleware, beta caps, cost tracking (variable + fixed), per-user metrics
- **Workspaces**: Schema, authorization, invitations, auto-creation, switching
- **Promotions**: Schema, services, admin UI, Stripe integration
- **Context System**: Insights, staleness tracking, benchmarks, north star goal, competitor detection

### Admin & Ops

- **Admin Dashboard**: Sessions, costs, KPIs, kill history, alerts, users, waitlist, promotions, impersonation
- **AI Ops**: Error detection, auto-remediation, self-monitoring
- **Observability**: Prometheus metrics, Grafana dashboards, Loki logging, graph node instrumentation
- **Monitoring**: Health checks (Redis, Postgres, Anthropic, Voyage, Brave), pool exhaustion alerts

### Security & Compliance

- **Security**: Rate limiting (global IP, SSE, dataset, admin), prompt injection detection, SQL validation, metrics auth
- **GDPR**: Data export, deletion/anonymization, audit logging, retention, consent capture
- **Supply Chain**: Pinned versions, OSV-Scanner, pip-audit blocking
- **Web Security**: Nonce-based CSP, CSRF protection, HSTS, WAF rules

### Quality & Testing

- **E2E Tests**: Dashboard, settings, meeting-create, meeting-complete, actions, datasets, admin promotions (all passing)
- **Security Tests**: Auth, authz, input validation, prompt injection, rate limiting, SQL injection
- **Architecture Audit**: State refactor, router consolidation, serialization cleanup, NODE_HANDLERS typing

### UX & Frontend

- **Navigation**: Grouped sidebar, dropdowns, loading skeletons
- **Toast System**: Success/error/info/warning with auto-dismiss
- **Accessibility**: Skip links, ARIA labels, focus traps, landmarks
- **Onboarding**: driver.js tour (dashboard, actions, projects), relationship diagram
- **shadcn Migration**: Button, Input, Badge, Alert, Card

### Performance

- **API Startup**: UMAP lazy-loading (12.6s → 6.8s, 46% faster)
- **Caching**: Redis user context cache, prompt caching, embedding dedup
- **Database**: Composite indexes, partition pruning, N+1 fixes, batch cost inserts

### Infrastructure

- **Deployment**: GitHub Actions CI, PostgreSQL backups, Redis persistence, blue-green deployment
- **Email**: Resend integration, templates (welcome, meeting, action reminder, weekly digest, failure notification)
- **Analytics**: Umami self-hosted integration
- **Integrations**: Google Calendar OAuth + action sync

### Documentation

- Help center (16 articles, 6 categories), privacy policy, terms of service, runbooks

---

## Audit-Derived Tasks (2025-12-22)

### Architecture [ARCH]

- [x] [ARCH][P1] Parallelize initial_round_node by applying pattern from parallel_round_node (60-70% latency reduction)
  - Refactored `initial_round_node` in `bo1/graph/nodes/rounds.py` to use `_generate_parallel_contributions()` pattern
  - Added double-contribution guard (mirrors `parallel_round_node` lines 719-745)
  - Added semantic deduplication via `_apply_semantic_deduplication()`
  - Added quality check via `_check_contribution_quality()` with facilitator guidance
  - Added round summarization via `_summarize_round()`
  - Extended `_generate_parallel_contributions()` with `contribution_type` and `expert_memories` params
  - Added `_build_cross_subproblem_memories()` helper for expert context continuity
  - 15 unit tests in `tests/graph/test_initial_round.py`
- [x] [ARCH][P2] Add `state_transition` SSE events with from/to node names for client-side progress visualization
  - Added `StateTransitionPayload` interface to `frontend/src/lib/api/sse-events.ts` with `from_node`, `to_node`, `sub_problem_index`
  - Added `state_transition` to `SSEEventType` union and `SSEEventMap`
  - Added typed event alias `StateTransitionEvent` and type guard `isStateTransitionEvent()`
  - Added `_previous_node` instance variable to `EventCollector` for tracking transitions
  - Added `_emit_state_transition()` helper method to emit events and update previous node
  - Emit transition events in both `_collect_with_custom_events()` and `_collect_with_astream_events()`
  - Reset `_previous_node` to `None` at start of `collect_and_publish()` for each new session
  - 7 unit tests in `tests/api/test_event_collector.py`
- [x] [ARCH][P1] Implement configurable wall-clock timeout in `collect_and_publish()` (default 10 min) to prevent runaway sessions
  - Added `GRAPH_EXECUTION_TIMEOUT_SECONDS` env var in `backend/api/constants.py` (default: 600s)
  - Wrapped both `_collect_with_custom_events()` and `_collect_with_astream_events()` with `asyncio.timeout()`
  - Added `session_timeout` SSE event with elapsed time and threshold
  - Updated `_mark_session_failed()` to accept `timeout_exceeded` flag with metadata
  - Added `graph_execution_timeout_total{session_type}` counter and `graph_execution_duration_seconds` histogram in metrics.py
  - 6 unit tests in `tests/api/test_event_collector.py`
- [x] [ARCH][P2] Extract shared router validation helpers like `validate_state_has_field()` to reduce duplication
  - Added `_validate_state_field(state, field_name, router_name)` helper to `bo1/graph/routers.py`
  - Migrated `route_facilitator_decision` and `route_after_synthesis` to use helper
  - 8 unit tests in `tests/graph/test_routers.py::TestValidationHelpers` and `TestRouteFacilitatorDecisionWithHelper`
- [x] [ARCH][P1] Add circuit breaker with PostgreSQL-based polling fallback for SSE when Redis PubSub drops
  - Created `SSEPollingFallback` class in `backend/api/event_poller.py`
  - Added `poll_events_from_postgres()` for reusable PostgreSQL event polling
  - Added `is_redis_sse_available()` helper combining circuit breaker check + Redis ping
  - Updated `stream_session_events()` to check Redis availability upfront
  - Added mid-stream Redis failure handling with automatic switch to polling
  - Emits `sse_fallback_activated` event to clients when switching modes
  - Added Prometheus metrics: `sse_fallback_activations_total`, `sse_polling_duration_seconds`, `sse_polling_events_per_batch`, `sse_fallback_active`
  - Added env vars: `SSE_POLLING_INTERVAL_MS`, `SSE_POLLING_BATCH_SIZE`, `SSE_CIRCUIT_CHECK_INTERVAL_MS`
  - 20 unit tests in `tests/api/test_sse_fallback.py`

### Performance [PERF]

- [x] [PERF][P0] Denormalize task_count into sessions table with DB trigger (session listing perf)
  - Added `task_count INTEGER DEFAULT 0 NOT NULL` column to sessions table
  - Backfilled from existing session_tasks.total_tasks
  - Created trigger function `update_session_task_count()` with INSERT/UPDATE/DELETE triggers
  - Updated `list_by_user()` to read directly from sessions.task_count (no JOIN)
  - Removed `include_task_count` parameter from method signature and callers
- [x] [PERF][P1] Increase POOL_MAX_CONNECTIONS to 75 and adjust load shedding threshold to 95%
  - Updated `bo1/constants.py:374` from 20 → 75
  - Updated `backend/api/constants.py:36` from 20 → 75
  - Updated `backend/api/event_publisher.py:38` PERSIST_SEMAPHORE_LIMIT from 15 → 50 (proportional)
  - Load shedding already at 95% - no change needed
  - All 15 pool_degradation tests pass (thresholds use percentages)
- [x] [PERF][P1] Database covering indexes for index-only scans
  - Migration: `z15_add_covering_indexes`
  - `idx_sessions_user_created_covering` with INCLUDE(id, status, phase, total_cost, round_number, expert_count, contribution_count, focus_area_count, task_count, workspace_id)
  - `idx_session_events_session_created_covering` with INCLUDE(event_type, sequence)
  - Note: `idx_api_costs_session_created` already sufficient (aggregation needs table access anyway)
- [x] [PERF][P1] Rewrite get_by_user() action tag filter using CTE + JOIN pattern
  - Refactored `action_repository.py:get_by_user()` to use CTE + JOIN when `tag_ids` present
  - CTE materializes tag matches once, avoiding correlated subquery per row
  - 7 unit tests added in `tests/state/test_action_visibility.py::TestTagFilteringWithCTE`
- [x] [PERF][P1] Enable pg_stat_statements extension in production database
  - Migration: `z16_enable_pg_stat_statements` creates extension
  - Docker: Added `shared_preload_libraries=pg_stat_statements` to docker-compose.yml
  - Admin endpoint: GET `/api/admin/queries/slow` returns top N slowest queries
  - Admin endpoint: POST `/api/admin/queries/slow/reset` clears query stats
  - 8 unit tests in `tests/api/admin/test_queries.py`
- [x] [PERF][P2] Implement SessionMetadataCache with Redis (5min TTL) for SSE requests
  - Created `SessionMetadataCache` class in `backend/api/session_cache.py`
  - Thread-safe LRU cache with TTL using stdlib (no cachetools dependency)
  - Prometheus metrics: `session_metadata_cache_hits_total`, `session_metadata_cache_misses_total`
  - Integrated into `get_verified_session()` dependency
  - Invalidation hooks in `event_collector.py`, `sessions.py`, `control.py`
  - Env vars: `SESSION_METADATA_CACHE_TTL_SECONDS` (default 300), `SESSION_METADATA_CACHE_MAX_SIZE` (default 1000)
  - 19 unit tests in `tests/api/test_session_cache.py`
- [x] [PERF][P2] Increase EmbeddingsConfig.BATCH_SIZE from 5 to 20 (4x fewer Voyage API calls)
- [x] [PERF][P2] Implement aggregation result caching decorator with 60s TTL for get_session_costs()
  - Created `AggregationCache` class in `bo1/llm/cost_tracker.py` (thread-safe LRU with TTL)
  - Added Prometheus metrics: `aggregation_cache_hits_total`, `aggregation_cache_misses_total`
  - Wrapped `get_session_costs()` with cache logic (60s TTL, 500 entry max)
  - Cache invalidation in `_flush_batch()` when new costs are flushed
  - 7 unit tests in `tests/llm/test_cost_tracker.py::TestAggregationCache`
- [x] [PERF][P2] Implement contribution pruning after convergence in DeliberationGraphState
  - Added `ContributionPruning` config class in `bo1/constants.py` (RETENTION_COUNT=6, PRUNE_AFTER_PHASE="convergence")
  - Created `prune_contributions_for_phase()` in `bo1/graph/state.py` with safety guards
  - Integrated pruning at synthesis node entry (reduces Redis checkpoint payload)
  - Preserves current round contributions + last N from previous rounds
  - Logs pruned count for observability
  - 10 unit tests in `tests/graph/test_contribution_pruning.py`
- [ ] [PERF][P3] Add py-spy profiling + Prometheus psutil metrics to /health endpoint
- [ ] [PERF][P3] Analyze graph topology for independent sub-problem parallelization opportunities
- [ ] [PERF][P3] Build Grafana dashboard for cache hit rates and cost savings by phase

### LLM Alignment [LLM]

- [x] [LLM][P1] Default to SYNTHESIS_LEAN_TEMPLATE in legacy code paths (30-60% synthesis cost reduction)
  - Updated `bo1/graph/deliberation/engine.py` `_generate_synthesis()` to use `SYNTHESIS_LEAN_TEMPLATE`
  - Updated `bo1/graph/deliberation/subgraph/nodes.py` `synthesize_sp_node()` to use `SYNTHESIS_LEAN_TEMPLATE`
  - Both now use hierarchical summarization: round summaries + final round detail
  - Prefill changed from `<thinking>` to `## The Bottom Line` (McKinsey-style answer-first)
  - max_tokens reduced from 4000 to 1500 (lean output ~800-1000 tokens)
  - Main path (`bo1/graph/nodes/synthesis.py`) already used lean template
- [x] [LLM][P1] Consolidate facilitator challenge section and trim metrics context (20% prompt reduction)
  - Removed INTERPRETATION and IMPASSE RESOLUTION sections from metrics context (~150 tokens saved)
  - Challenge section kept inline in `<phase_awareness>` (no duplication to remove)
- [x] [LLM][P1] Reduce persona context from last 5 to last 3 contributions (21% reduction)
  - Updated `compose_persona_contribution_prompt()` in `bo1/prompts/persona.py:129`
  - Updated synthesis fallback in `bo1/graph/nodes/synthesis.py:187-188`
- [x] [LLM][P0] Sanitize LLM outputs before re-injection: add sanitize_user_input() after strip_prompt_artifacts() in persona_executor.py:142
- [x] [LLM][P0] Sanitize round summaries before re-injection in rounds.py:492
- [x] [LLM][P0] Sanitize recommendations/votes before synthesis prompt interpolation
  - Added sanitize_user_input() in bo1/graph/deliberation/context.py:104-106 for synthesis recommendations
- [x] [LLM][P0] Sanitize Brave/Tavily search results before AND after LLM summarization in researcher.py
  - Added `sanitize_user_input()` to raw Brave search snippets/titles before LLM summarization
  - Added `sanitize_user_input()` to LLM-generated summaries after processing (both Brave and Tavily)
  - Sanitized source titles in returned results
  - 12 new unit tests in `tests/prompts/test_sanitizer.py`
- [x] [LLM][P1] Sanitize user interjection in control.py:1917 before storing in state
- [x] [LLM][P1] Sanitize clarification answers in control.py:994-1007 before context injection
- [x] [LLM][P1] Sanitize business context fields in context.py:70-88 (user-provided data)
  - Sanitized business_model, target_market, revenue, customers, growth_rate fields
  - Added 4 unit tests in `tests/prompts/test_sanitizer.py::TestBusinessContextSanitization`
- [x] [LLM][P1] Sanitize strategic objectives in context.py:86 before prompt injection
  - Each strategic objective now wrapped with `sanitize_user_input()`
  - Added 2 unit tests in `tests/prompts/test_sanitizer.py::TestStrategicObjectiveSanitization`
- [x] [LLM][P1] Sanitize saved clarifications in context.py:187 before re-use
  - Sanitized both question and answer from saved clarifications
  - Added 3 unit tests in `tests/prompts/test_sanitizer.py::TestSavedClarificationSanitization`
- [x] [LLM][P1] Add challenge phase validation: reject generic agreement in rounds 3-4
  - Added `GENERIC_AGREEMENT_PATTERNS` and `CHALLENGE_INDICATOR_PATTERNS` to `bo1/llm/response_parser.py`
  - Added `validate_challenge_phase_contribution()` method to `ResponseParser`
  - Added `ChallengePhaseConfig` to `bo1/constants.py` with `ROUNDS = [3, 4]`
  - Integrated validation in `PersonaExecutor.execute_persona_call()` with retry on failure
  - Added `_retry_with_challenge_directive()` method for explicit challenge re-prompt
  - 16 unit tests in `tests/llm/test_response_parser.py`
- [x] [LLM][P1] Remove keyword fallback for facilitator decision parsing, require strict XML tags with retry
  - Removed keyword fallback block from `parse_facilitator_decision()` in `bo1/llm/response_parser.py`
  - Now raises `XMLValidationError` if `<action>` tag missing or value invalid
  - Set `strict=True` in ValidationConfig for facilitator in `bo1/agents/facilitator.py`
  - Updated 10 tests in `tests/llm/test_response_parser.py` to expect exceptions
- [x] [LLM][P2] Add output length validation: warn if response uses <50% of max_tokens (verbosity check) or >90% (truncation risk)
  - Added `OutputLengthConfig` class in `bo1/constants.py` with VERBOSE_THRESHOLD=0.5, TRUNCATION_THRESHOLD=0.9
  - Added `llm_output_length_warnings_total{type, model}` Prometheus counter in `backend/api/middleware/metrics.py`
  - Added `_validate_output_length()` helper to `PromptBroker` in `bo1/llm/broker.py`
  - Integrated validation in `PromptBroker.call()` after response creation (non-blocking)
  - Added `output_ratio` and `max_tokens` fields to `log_llm_call()` structured output
  - Env toggle: `OUTPUT_LENGTH_VALIDATION_ENABLED` (default true)
  - 19 unit tests in `tests/llm/test_output_length_validation.py`
- [x] [LLM][P2] Add RateLimiter to PromptBroker (max 10 rounds/session, 6 calls/minute)
  - Added `LLMRateLimiterConfig` to `bo1/constants.py` with env toggle
  - Created `SessionRateLimiter` class in `bo1/llm/rate_limiter.py` (thread-safe, sliding window)
  - Integrated into `PromptBroker.call()` with graceful degradation (log + metric, don't block)
  - Added `llm_rate_limit_exceeded_total{type, session_id}` Prometheus counter
  - 22 unit tests in `tests/llm/test_rate_limiter.py`, 11 integration tests in `tests/llm/test_broker_rate_limit.py`
- [ ] [LLM][P2] Add tests/test_sanitizer.py with injection attack vectors
- [ ] [LLM][P2] Add prompt_type to CostRecord metadata for per-prompt-type cache analysis
- [ ] [LLM][P3] Add post-generation trait validation in agents/base.py
- [ ] [LLM][P3] Apply prefill="<thinking>" to all \_create_and_call_prompt() calls
- [ ] [LLM][P3] Consolidate `<critical_thinking_protocol>` and `<forbidden_patterns>` in persona.py

### Data Model [DATA]

- [x] [DATA][P0] Create migration to add user_id column with FK to recommendations table for RLS
  - Migration: `z14_recommendations_rls` adds user_id column, backfills from sessions, creates RLS policies
  - Index: `idx_recommendations_user_id` for efficient user queries
  - Policies: `recommendations_user_isolation` (user access), `recommendations_admin_access` (admin read)
- [x] [DATA][P0] Add missing DB-mapped fields to Recommendation Pydantic model (session_id, sub_problem_index, id, created_at)
  - Added: `id`, `session_id`, `sub_problem_index`, `user_id`, `created_at` as optional fields
  - Updated `save_recommendation()` to accept and auto-fetch `user_id`
  - Added `get_recommendations_by_session()` for retrieval with full DB fields
  - 17 unit tests in `tests/models/test_recommendations.py` and `tests/state/test_contribution_repository.py`
- [x] [DATA][P1] Add workspace_id: str | None to Session model
  - Added `workspace_id: str | None = Field(None)` to `Session` model in `bo1/models/session.py`
  - Updated `from_db_row()` to map `workspace_id` from DB column
  - 3 unit tests in `tests/models/test_session.py`
- [x] [DATA][P1] Update Session model nullable fields + add missing DB fields
  - Added `contribution_count: int = Field(0)` and `task_count: int = Field(0)` to Session model
  - Updated `phase: str = Field("problem_decomposition")` (was nullable)
  - Updated `total_cost: float = Field(0.0)` (was nullable)
  - Updated `round_number: int = Field(0)` (was nullable)
  - Updated `from_db_row()` with all new field mappings and defaults
  - 4 new tests in `tests/models/test_session.py`
- [x] [DATA][P1] Add user_id and status fields to ContributionMessage model
  - Added `ContributionStatus` enum with `in_flight`, `committed`, `rolled_back` values
  - Added `user_id: str | None` and `status: ContributionStatus` fields to `ContributionMessage`
  - Updated `from_db_row()` to map both fields with safe defaults
  - 19 unit tests in `tests/models/test_contribution_message.py`
- [ ] [DATA][P1] Create test_state_roundtrip() to validate serialize/deserialize functions
- [x] [DATA][P1] Add GitHub Action to check frontend types match backend OpenAPI spec
  - Created `scripts/check_openapi_fresh.py` - compares backend OpenAPI with committed spec
  - Added CI step to `lint-and-typecheck` job after mypy, before frontend steps
  - Fixed `SnoozeReminderRequest` forward reference in `backend/api/actions.py`
  - Regenerated `openapi.json` and frontend types
- [ ] [DATA][P2] Create migration audit script to detect model-migration field gaps
- [ ] [DATA][P2] Document which DeliberationGraphState fields are persisted vs ephemeral
- [ ] [DATA][P2] Create bo1/models/{action,project,workspace}.py with domain models
- [ ] [DATA][P2] Add JSON serialization for recommendations.conditions field
- [ ] [DATA][P3] Add CHECK constraints to enum columns (status, phase, priority)
- [ ] [DATA][P3] Add COMMENT ON TABLE/COLUMN for all tables
- [ ] [DATA][P3] Consolidate frontend types to single source of truth (prefer generated types)
- [ ] [DATA][P3] Review merge migrations for schema inconsistencies

### Observability [OBS]

- [x] [OBS][P0] Add `request_id` field to DeliberationGraphState and propagate through all graph nodes
  - Added `request_id: str | None` to `DeliberationGraphState` TypedDict
  - Updated `create_initial_state()` to accept `request_id` parameter
  - Updated `control.py` to pass `request_id` from HTTP request to initial state
  - Updated `log_with_session()` to include `request_id` in log format
  - Updated key error paths in `moderation.py`, `rounds.py`, `context.py` to include request_id
  - 4 unit tests in `tests/graph/test_state_serialization.py::TestRequestIdField`
- [x] [OBS][P0] Add `circuit_breaker_state{provider, state}` Prometheus gauge and configure alerts
  - Added `circuit_breaker_state{provider, state}` gauge in `backend/api/middleware/metrics.py`
  - Updated `record_circuit_breaker_state()` to set labeled gauge per provider/state
  - Added Prometheus alerting rules in `monitoring/prometheus/alert_rules.yml`:
    - `CircuitBreakerOpen`: Critical alert when circuit opens for >1 minute
    - `CircuitBreakerHalfOpen`: Warning when half-open for >5 minutes
    - `CircuitBreakerTripsHigh`: Warning for frequent trips
    - `AllLLMProvidersDown`: Critical when both Anthropic and OpenAI are down
  - 7 unit tests in `tests/utils/test_circuit_breaker_metrics.py`
- [ ] [OBS][P1] Add event persistence metrics: batch_size, duration_seconds, retry_queue_depth
- [x] [OBS][P1] Add Redis pool metrics: active connections, utilization %, acquisition latency
  - Added Prometheus gauges: `bo1_redis_pool_used_connections`, `bo1_redis_pool_free_connections`, `bo1_redis_pool_utilization_percent`
  - Added histogram: `bo1_redis_connection_acquire_seconds` (acquisition latency)
  - Added `get_pool_health()` method to `RedisManager` (bo1/state/redis_manager.py)
  - Added `/health/redis/pool` endpoint with `RedisPoolHealthResponse` model
  - 14 unit tests in `tests/state/test_redis_pool_metrics.py`
- [x] [OBS][P1] Audit backend/api/_.py and replace plain logger.error() with log_error(ErrorCode._)
  - Migrated 185 `logger.error()` calls across 40 files to `log_error(logger, ErrorCode.*, msg, **ctx)`
  - Added 7 new ErrorCodes: EXT_NTFY_ERROR, EXT_OAUTH_ERROR, API_SSE_ERROR, API_WORKSPACE_ERROR, SERVICE_ANALYSIS_ERROR, SERVICE_BILLING_ERROR, SERVICE_ONBOARDING_ERROR
  - 0 remaining `logger.error()` calls in backend/api (verified via grep)
- [ ] [OBS][P1] Add cost tracking metrics: flush_duration_seconds, retry_queue_depth, anomaly_total
- [ ] [OBS][P1] Add background LLM provider health probe with cached results
- [ ] [OBS][P1] Add unified degraded mode check to /ready including LLM circuit state and pool utilization
- [ ] [OBS][P1] Configure Prometheus alerts for event persistence backlog, circuit breaker opens, cost tracking failures
- [ ] [OBS][P2] Add session_id, sub_problem_index, round_number to all graph node exception logs
- [ ] [OBS][P2] Add event stream metrics: publish latency, event type distribution, batch priority queue depth
- [ ] [OBS][P2] Add graph_node_errors_total{node_name} and api_endpoint_errors_total{endpoint, status} counters
- [ ] [OBS][P2] Implement health check history storage (last 5 results with timestamps)
- [ ] [OBS][P2] Send cost anomaly alerts to ntfy topic

### API Contract [API]

- [x] [API][P1] Standardize HTTPException format across all endpoints to use dict detail with error_code field
  - Created `http_error(ErrorCode, message, status, **context)` helper in `backend/api/utils/errors.py`
  - Created `ErrorDetailDict` TypedDict for structured error response format
  - Exported from `backend/api/utils/__init__.py` for easy imports
  - Migrated `control.py` (26 HTTPException calls) as pattern demonstration
  - Added 8 new ErrorCodes: API_NOT_FOUND, API_FORBIDDEN, API_UNAUTHORIZED, API_CONFLICT, API_RATE_LIMIT, API_BAD_REQUEST, API_SESSION_ERROR, API_ACTION_ERROR
  - Updated frontend `ApiError` interface with `error_code`, `message`, and rate limit fields
  - 16 unit tests in `tests/api/utils/test_errors.py`
  - Note: Remaining 490 HTTPException calls can be migrated incrementally using this pattern
- [x] [API][P1] Centralize COST_FIELDS and COST_EVENT_TYPES constants in backend/api/constants.py
  - Moved from `streaming.py` to `backend/api/constants.py` with type annotations and docstrings
  - Updated imports in `streaming.py` and `tests/api/test_session_costs.py`
- [ ] [API][P1] Add SSE event schema versioning and document schema evolution path
- [ ] [API][P2] Document ExpertEventBuffer merging behavior in SSE_EVENTS.md
- [ ] [API][P2] Add sessionAuth security scheme to OpenAPI spec components
- [ ] [API][P2] Add rate limit info to OpenAPI responses (429) for all @limiter.limit decorated endpoints
- [ ] [API][P2] Add Field(max_length=10000) to CreateSessionRequest and other text fields
- [ ] [API][P2] Update OpenAPI error examples to include error_code field
- [ ] [API][P3] Add pagination helper fields (has_more, next_offset) to SessionListResponse and other list responses
- [ ] [API][P3] Refactor VerifiedSession into granular dependencies (VerifiedSession, VerifiedSessionAdmin, SessionMetadata)
- [ ] [API][P3] Create filtered public OpenAPI spec for non-admin endpoints
- [ ] [API][P3] Enforce Pydantic models for all datetime responses via linter rule

### Reliability [REL]

- [x] [REL][P0] Implement resume_session_from_checkpoint() in bo1/graph/execution.py + add "Retry Session" UI button
  - Added `resume_session_from_checkpoint()` function to `bo1/graph/execution.py` (loads checkpoint, resets stop flags)
  - Added POST `/api/v1/sessions/{id}/retry` endpoint in `backend/api/control.py` for failed sessions
  - Added `retrySession()` method to frontend API client
  - Updated `MeetingError.svelte` usage to call retry API for failed sessions
  - Updated `FailedMeetingAlert.svelte` with per-meeting retry buttons
  - 15 unit tests in `tests/api/test_retry_session.py`
- [x] [REL][P0] Add rollback logic to replanning_service.py to delete session on link/update failures
  - Added `session_repository.delete()` method for hard deletes during rollback
  - Added `_rollback_session()` helper to delete from PostgreSQL and Redis
  - Step 4 (project link): On failure, rollback entire session and raise RuntimeError
  - Step 5 (action update): On failure, unlink from project (if linked), rollback session, raise RuntimeError
  - Double-failure safe: rollback logs errors but doesn't re-raise
  - 5 unit tests in `tests/services/test_replanning_service.py`
- [x] [REL][P1] Add chaos test test_anthropic_circuit_open_triggers_openai_fallback + modify PromptBroker retry to switch providers
  - Modified `PromptBroker.call()` to attempt fallback provider when primary circuit breaker is open
  - Added `_call_with_provider()` helper method for fallback execution
  - Added `llm_provider_fallback_total{from_provider, to_provider, reason}` Prometheus counter
  - Added structured logging for fallback events
  - Added `_used_fallback` flag to prevent infinite fallback loops
  - 6 chaos tests in `tests/chaos/test_provider_fallback.py`
- [x] [REL][P1] Add session_repository.save_metadata() for dual-write to PostgreSQL when Redis unavailable
  - Added `save_metadata()` method to `SessionRepository` with type-safe field mapping
  - Added `extract_session_metadata()` helper to extract persistable fields from graph state
  - Integrated fallback in `event_collector.py` to call save_metadata when Redis circuit breaker is open
  - Updated `_reconstruct_state_from_postgres()` to use denormalized metadata for better recovery
  - Emits `redis_fallback_activated` SSE event when switching to fallback mode
  - 18 unit tests in `tests/state/test_session_repository.py` (TestSaveMetadata, TestExtractSessionMetadata)
- [ ] [REL][P2] Track SSE reconnect attempts in session metadata + return Retry-After header in streaming.py
- [ ] [REL][P2] Add 40P01 error code to RETRYABLE_EXCEPTIONS in bo1/utils/retry.py
- [ ] [REL][P2] Set statement_timeout in db_session() for batch operations
- [ ] [REL][P2] Add chaos test test_redis_down_sse_uses_postgres_events to validate event fallback

### Cost Optimisation [COST]

- [ ] [COST][P2] Add prompt_cache_hit_rate metric to CostTracker.get_session_costs()
- [ ] [COST][P2] Test extending Haiku to Round 3 in get_model_for_phase() (5-8% cost reduction)
- [ ] [COST][P3] Run A/B test comparing 3 vs 5 personas for user satisfaction (potential 20-30% reduction)
- [ ] [COST][P3] Monitor cache hit rate and adjust similarity threshold based on data
- [ ] [COST][P3] Remove verbose examples from facilitator.py after model training stabilizes

---

## E2E Findings (2024-12-22)

### Critical

- [x] [BUG][P0] Fix SubProblemResult validation: sub_problem_id receives list `['bo1', 'models', 'problem', 'SubProblem']` instead of string ID (blocks multi-sub-problem meetings)
  - Added `get_sub_problem_id_safe()` / `get_sub_problem_goal_safe()` helpers in `bo1/utils/checkpoint_helpers.py`
  - Updated `result_from_subgraph_state()`, `next_subproblem_node()`, and `engine.py` to use safe accessors
  - Added corruption detection + repair logic in `deserialize_state_from_checkpoint()`
  - Added `@field_validator` on `SubProblem.id` / `.goal` to reject list values at model level
  - 20 unit tests in `tests/utils/test_checkpoint_helpers.py`
  - 4 corruption tests in `tests/graph/test_state_serialization.py::TestCorruptedSubProblemId`

### Major

- [x] [BUG][P1] Fix context API 500 errors on dashboard load (`/api/v1/context/refresh-check`, `/api/v1/user/value-metrics`, `/api/v1/context`)
  - Root cause: `user_context` table had RLS enabled but no policies
  - Migration: `z17_add_user_context_rls_policy.py` adds `user_context_user_isolation` and `user_context_admin_access` policies
  - Updated `execute_query()` in `db_helpers.py` with optional `user_id` param for RLS context
  - Updated `/v1/context/refresh-check` and `/v1/context/dismiss-refresh` endpoints to pass `user_id`
- [x] [UX][P2] Add partial success UX for multi-sub-problem meetings (show which sub-problems succeeded vs failed instead of binary failure)
  - Extended `MeetingError.svelte` with optional `subProblemResults`, `totalSubProblems` props
  - Created `PartialResultsPanel.svelte` - collapsible accordion showing completed sub-problems with synthesis text
  - Created `SubProblemStatusBadge.svelte` - status pill (complete/in_progress/failed/pending)
  - Added `subProblemResultsForPartialSuccess` and `totalSubProblemsCount` to `eventDerivedState.svelte.ts`
  - Warm yellow styling for partial success (vs red for complete failure)
  - Copy button on each synthesis for user to extract value from partial results

### Minor

- [ ] [UX][P3] Add tooltip to warning indicator on actions from incomplete meetings (explain what ⚠ means)

---

_For detailed implementation notes on completed tasks, see git history._
