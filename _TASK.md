# Task Backlog

_Last updated: 2025-12-27 (rolling week view)_

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

### User-Owned

- [ ] [DOCS][P3] Help pages content review (Si's todo)

---

## UX/UI Audit Issues (2025-12-27)

### Critical

- [x] [UX][P0] Fix Context API 500 errors - 4 endpoints returning 500: `/api/v1/context`, `/api/v1/context/refresh-check`, `/api/v1/context/goal-staleness`, `/api/v1/context/objectives/progress` ✅ Fixed: added missing `strategic_objectives_progress` column to prod DB
- [x] [UX][P0] Context page renders empty due to API failures - users see blank main content area ✅ Fixed: same root cause as above

### Minor

- [x] [UX][P2] Fix 404 for `/context/logo.png` - missing asset reference ✅ Fixed: changed `%sveltekit.assets%/logo.png` to absolute `/logo.png` in app.html

---

## Audit-derived tasks (2025-12-27)

### Security (from LLM Alignment Audit) - CRITICAL

- [x] [LLM][P0] Sanitize LLM outputs before re-injection into prompts (contributions, summaries, recommendations) ✅ Done: sanitization in persona_executor.py
- [x] [LLM][P0] Sanitize third-party API results (Brave, Tavily) before AND after LLM summarization ✅ Done: researcher agent sanitization
- [x] [LLM][P1] Sanitize user interjection and clarification answers before prompt interpolation ✅ Done
- [x] [LLM][P1] Sanitize database-stored user content (business context, strategic objectives, saved clarifications) ✅ Done

### Reliability (from Reliability Audit) - CRITICAL

- [x] [REL][P0] Implement LangGraph checkpoint recovery - failed sessions cannot resume ✅ Done: resume_session_from_checkpoint + "Retry Session" UI (FailedMeetingAlert.svelte)
- [x] [REL][P0] Fix replanning service rollback - partial failure creates orphaned sessions ✅ Done: cleanup on link/update failures + tests
- [x] [REL][P0] Validate LLM provider fallback with chaos test (Anthropic outage → OpenAI fallback) ✅ Done: tests/chaos/test_llm_chaos.py

### Performance (from Performance Audit)

- [x] [PERF][P0] Increase database connection pool from 20 → 75 (POOL_MAX_CONNECTIONS) ✅ Done: constants.py
- [x] [PERF][P1] Add composite indexes: idx_session_events_session_created, idx_api_costs_session_created, idx_sessions_user_created_desc ✅ Already present: covering indexes with additional INCLUDE columns
- [x] [PERF][P1] Optimize action tag filtering query (rewrite subquery to CTE + JOIN in action_repository.py) ✅ Done: CTE + JOIN pattern at action_repository.py:192-221
- [x] [PERF][P1] Enable pg_stat_statements monitoring in production ✅ Done: migration z16 + admin/queries.py API

### Data Model (from Data Model Audit)

- [x] [DATA][P0] Add user_id FK to recommendations table (required for RLS) ✅ Done: migration z14
- [x] [DATA][P1] Add workspace_id field to Session Pydantic model ✅ Done: bo1/models/session.py:54
- [x] [DATA][P1] Add session_id, sub_problem_index, id, created_at to Recommendation model ✅ Done: bo1/models/recommendations.py:23-27
- [x] [DATA][P1] Fix Session nullable field consistency ✅ Done: fields have proper defaults in model
- [x] [DATA][P2] Add CI check for TypeScript type sync ✅ Done: .github/workflows/ci.yml:92-93 npm run check:types-fresh

### Observability (from Observability Audit)

- [x] [OBS][P1] Add request_id (correlation ID) to DeliberationGraphState and propagate through node logs ✅ Done: state.py + node logs
- [x] [OBS][P1] Expose circuit breaker state as Prometheus metrics (circuit_breaker_state{provider, state}) ✅ Done: metrics.py bo1_circuit_breaker_state_labeled
- [x] [OBS][P1] Add event persistence metrics: batch_size, duration_seconds, retry_queue_depth ✅ Done
- [x] [OBS][P1] Add Redis connection pool metrics ✅ Done: redis_manager.py:get_pool_health(), metrics.py gauges, /health/redis/pool endpoint, 16 tests
- [x] [OBS][P2] Standardize error code usage in backend/api/*.py (replace plain logger.error with log_error + ErrorCode) ✅ Done: migrated 8 occurrences across seo/routes.py, email.py, e2e_auth.py, context/routes.py, admin/blog.py, middleware/tier_limits.py
- [x] [OBS][P2] Configure missing Prometheus alerts ✅ Done: alert_rules.yml:98-170 (event persistence + circuit breaker alerts)

### API Contract (from API Contract Audit)

- [x] [API][P1] Standardize error response format (migrate from string detail to structured {error_code, message}) ✅ Done: migrated projects.py, sessions.py, actions.py, competitors.py to http_error()
- [x] [API][P1] Centralize cost field definitions for SSE filtering ✅ Done: constants.py:94 COST_FIELDS, streaming.py:24,63-67, tests
- [x] [API][P2] Add OpenAPI security scheme for SuperTokens session auth ✅ Done: sessionAuth + csrfToken in openapi.json
- [x] [API][P2] Document rate limits in OpenAPI responses for all @limiter.limit decorated endpoints ✅ Added RATE_LIMIT_RESPONSE to 24 endpoints across 6 files

### Cost Optimization (from Cost Audit)

- [x] [COST][P1] Default to SYNTHESIS_LEAN_TEMPLATE ✅ Done: synthesis.py:162,232 + engine.py:25,200 + subgraph/nodes.py:31,640
- [x] [COST][P2] Extend Haiku model to Round 3 (currently rounds 1-2 only) ✅ Done: HAIKU_ROUND_LIMIT=3, AB_TEST_LIMIT=4
- [x] [COST][P2] Add cache hit rate metrics (prompt cache, research cache, LLM cache) to cost_tracker ✅ Done: CostTracker.get_cache_metrics(), Prometheus gauges, admin API endpoint, admin UI card
- [x] [COST][P3] Reduce persona context window from last 6 → last 3 contributions (~3-5% cost reduction) ✅ Done: PersonaContextConfig.CONTRIBUTION_LIMIT=3 in constants.py, updated subgraph/nodes.py:227, 7 unit tests

### Architecture (from Architecture Audit)

- [x] [ARCH][P2] Migrate high-traffic read paths to use nested state accessors (get_problem_state, get_phase_state, etc.) ✅ Done: refactored experts.py and nodes/rounds.py to use get_*_state() accessors

---

## Backlog (from _TODO.md, 2025-12-27)

### Auth & Login

- [x] [AUTH][P1] Fix local development login issue (authentication not working locally)
- [x] [AUTH][P2] Fix GDPR consent API returning 403 during OAuth callback flow

### SEO Tools

- [x] [SEO][P1] Fix 'Discover' button in blog generate modal (topic discovery)
- [x] [SEO][P2] Define SEO autopilot strategy: focus on high-intent-to-purchase traffic generation
- [x] [SEO][P2] Create marketing collateral bank (images, animations, concepts) for AI content generation
- [x] [SEO][P2] Fix SEO assets route order (/assets/suggest 404) - moved route before parameterized /{asset_id}

### Admin Dashboard

- [x] [ADMIN][P2] Make dashboard cards drillable to relevant metrics (currently only waitlist is drillable)
- [x] [ADMIN][P2] Fix rate limiting on admin endpoints causing 429 cascade during callback (email-stats, observability-links, research-cache, costs, runtime-config, extended-kpis, blog/topics)
- [x] [ANALYTICS][P2] Investigate signup page conversion (48 unique visitors, 0 waitlist signups) - Fixed: slowapi param naming bug
- [x] [ADMIN][P2] Fix ratings admin 401 (wrong auth dependency) + add rate limiting

### UX Improvements

- [x] [DASHBOARD][P3] Change 'this week' view from calendar-based (Mon-Sun) to rolling ±3 days view

### Billing & Pricing

- [x] [BILLING][P3] Add non-profit/charity discount tier (free or 80% off)
- [x] [BILLING][P3] Create granular meeting tiers in Stripe (1-9 meetings @ £10 each, targeting 90% gross margin)
- [x] [BILLING][P2] Non-fixed costs fair usage caps - implemented per-feature daily cost limits with p90 heavy user detection

### Competitors

- [x] [COMPETITORS][P3] Add skeptic checks for competitor relevance (similar product? ICP? market?)

### Peer Benchmarks

- [x] [BENCHMARKS][P3] Review peer benchmark opt-in UX: show one teaser metric OR default opt-in with privacy explanation

### Metrics & Context

- [x] [CONTEXT][P2] Add 'Metrics You Need to Know' feature: user metrics, competitor metrics, industry benchmarks, importance ranking (now vs later), pendulum indicator

---

## Completed Summary

### December 2025

- **Admin API Bug Fixes (2025-12-27)**: Fixed multiple admin endpoint issues:
  - Ratings admin 401: Changed `require_admin` → `require_admin_any` (correct admin middleware)
  - Ratings admin rate limiting: Added `@limiter.limit(ADMIN_RATE_LIMIT)` to `/metrics`, `/trend`, `/negative` endpoints
  - SEO assets route order: Moved `/assets/suggest` before `/assets/{asset_id}` to fix 404
  - Sessions.py: Fixed duplicate 429 response key in OpenAPI spec

- **Fair Usage Caps for Variable-Cost Features (2025-12-27)**: Implemented per-feature daily cost limits with p90 heavy user detection:
  - Data model: Added `feature` column to `api_costs`, created `daily_user_feature_costs` aggregation table
  - PlanConfig: Added `FairUsageLimits` dataclass with per-tier limits for `mentor_chat`, `dataset_qa`, `competitor_analysis`, `meeting`
  - Service: `backend/services/fair_usage.py` with usage checking, soft/hard cap logic, p90 calculation
  - Middleware: `backend/api/middleware/fair_usage.py` with `require_fair_usage()` dependency
  - Admin API: `/admin/costs/fair-usage/heavy-users` and `/admin/costs/fair-usage/by-feature` endpoints
  - User API: `GET /api/v1/user/fair-usage` endpoint for usage meter
  - Tests: 8 PlanConfig tests + 10 FairUsageService tests

- **Persona Context Window Optimization (2025-12-27)**: Reduced persona context window from 6 to 3 contributions for ~3-5% token cost savings:
  - Config: `PersonaContextConfig.CONTRIBUTION_LIMIT = 3` in `bo1/constants.py`
  - Implementation: Updated `bo1/graph/deliberation/subgraph/nodes.py:227` to use config constant
  - Logging: Added debug log for contribution context size (chars/tokens) for cost tracking
  - Tests: 7 unit tests in `tests/llm/test_persona_context.py` covering limit value, slicing, edge cases
  - Quality preserved: Round summaries provide broader context, most recent round most relevant

- **Unified Cache Metrics (2025-12-27)**: Implemented cache hit rate monitoring across all cache systems:
  - Backend: `CostTracker.get_cache_metrics()` aggregates metrics from prompt (Anthropic), research (PostgreSQL), LLM (Redis) caches
  - Backend: `_emit_cache_rate_gauges()` updates Prometheus gauges on each call
  - Prometheus: `bo1_cache_hit_rate{cache_type}`, `bo1_cache_hits_total{cache_type}`, `bo1_cache_misses_total{cache_type}` gauges
  - API: `GET /api/admin/costs/cache-metrics` endpoint returning `UnifiedCacheMetricsResponse`
  - Admin UI: Cache Performance card on Costs page with 4-column layout (Prompt/Research/LLM/Aggregate)
  - Tests: 4 unit tests for `TestGetCacheMetrics` class covering structure, error handling, aggregation, zero-state
  - Models: `CacheTypeMetrics`, `AggregatedCacheMetrics`, `UnifiedCacheMetricsResponse` Pydantic models

- **Marketing Collateral Bank (2025-12-27)**: Implemented marketing asset storage for AI content generation:
  - Database: `marketing_assets` table (migration zl) with file metadata, CDN URL, tags, type
  - Backend: `backend/services/marketing_assets.py` with CRUD, DO Spaces upload, tag-based search
  - Backend: Asset suggestion algorithm using tag overlap for article relevance scoring
  - API: POST/GET/PATCH/DELETE `/api/v1/seo/assets`, GET `/api/v1/seo/assets/suggest`
  - Billing: `marketing_assets_total` limit (free=10, starter=50, pro=500, enterprise=unlimited)
  - Frontend: Admin collateral bank page `/admin/collateral` with drag-drop upload, grid view, edit/delete
  - Frontend: Type filtering, tag-based search, CDN URL copy
  - Tests: 16 unit tests for validation, service, tier limits
  - Asset types: image, animation, concept, template (PNG, JPG, GIF, WebP, SVG, MP4, WebM)

- **SEO Autopilot (2025-12-27)**: Implemented automated SEO content generation with purchase intent prioritization:
  - Database: `seo_autopilot_config` JSONB column on user_context (migration zk)
  - Backend: `SEOAutopilotConfig` Pydantic model (enabled, frequency_per_week, auto_publish, require_approval, target_keywords, purchase_intent_only)
  - Backend: `SEOAutopilotService` class with topic discovery, article generation, tier limit enforcement
  - Backend: Purchase intent scoring - transactional (+0.4), problem-solution (+0.3), comparison (+0.25), decision-stage (+0.2) keywords
  - Backend: Scheduled job (`seo_autopilot_job.py`) runs daily, respects frequency settings
  - API: GET/PUT `/api/v1/seo/autopilot/config`, GET `/api/v1/seo/autopilot/pending`, POST `.../approve`, POST `.../reject`
  - Frontend: Autopilot settings card in SEO page sidebar (toggle, frequency selector, stats)
  - Frontend: Pending review queue with approve/reject actions
  - Tests: 2 unit tests for purchase intent scoring logic
  - High-intent targeting: Prioritizes keywords with transactional, comparison, and decision-stage signals

- **Peer Benchmark Preview UX (2025-12-27)**: Improved opt-in UX for peer benchmarking:
  - Backend: `GET /api/v1/peer-benchmarks/preview` endpoint returns one sample metric (industry median) without consent
  - Backend: `get_preview_metric()` service function finds first metric with sufficient sample count (>=5 peers)
  - Frontend: Teaser card with industry preview metric, blurred locked metrics, clear "Opt In to Compare" CTA
  - Frontend: Enhanced consent card with privacy checkmarks (k-anonymity, no PII, industry-level only)
  - API client: `getPeerBenchmarkPreview()` method added
  - Tests: 7 new tests for PreviewMetricResponse model validation
  - Privacy-first: Preview shows only industry p50, never user data

- **Competitor Skeptic Relevance (2025-12-27)**: Added AI-powered relevance checks for detected competitors:
  - Backend: `backend/api/context/skeptic.py` with `evaluate_competitor_relevance()` and batch evaluation
  - Model: Extended `DetectedCompetitor` with `relevance_score` (0.0-1.0), `relevance_flags` (similar_product/same_icp/same_market), `relevance_warning`
  - Integration: Skeptic check runs during auto-detect and for manually added competitors
  - API: `ManagedCompetitorResponse` now includes `relevance_warning` and `relevance_score`
  - Frontend: Color-coded relevance indicators (✓ green = high, ~ yellow = partial, ? red = low) in strategic context
  - Tooltip shows which checks passed/failed on hover
  - Tests: 27 unit tests for skeptic evaluation and model validation

- **Meeting Bundle Purchases (2025-12-27)**: Implemented one-time meeting bundle purchases:
  - Database: `meeting_credits` column on users (migration zj)
  - Backend: `MeetingBundleConfig` in PlanConfig, bundles of 1/3/5/9 meetings @ £10 each
  - Backend: `POST /api/v1/billing/purchase-bundle`, `GET /api/v1/billing/credits` endpoints
  - Webhook: `checkout.session.completed` handler credits user account for bundle purchases
  - Usage: Meeting credits consumed before tier limits when creating sessions
  - Frontend: `MeetingBundles.svelte` component on pricing page
  - Frontend: Billing settings shows remaining credits with purchase buttons
  - Script: `create_meeting_tier_prices.py` for Stripe product/price creation
  - Tests: 10 unit tests for bundle config and credit management

- **Nonprofit Discount Tier (2025-12-27)**: Added nonprofit/charity discount feature:
  - Database: `is_nonprofit`, `nonprofit_verified_at`, `nonprofit_org_name` columns on users (migration zi)
  - Promo codes: NONPROFIT80 (80% off), NONPROFIT100 (free) via `create_nonprofit_promos.py` script
  - Admin API: POST/DELETE `/api/admin/users/{id}/nonprofit` endpoints for status management
  - Auto-applies promo code when setting nonprofit status
  - Admin UI: Nonprofit badge (pink heart) in Users table Badges column
  - Runbook: `docs/runbooks/nonprofit-verification.md` with verification process

- **Rolling 7-Day View (2025-12-27)**: Changed dashboard week view from calendar-based (Mon-Sun) to rolling ±3 days:
  - Updated `getWeekDays()` in `WeeklyPlanView.svelte` to center on today
  - Renamed header from "This Week" to "7-Day View"
  - Added 9 unit tests for date logic (month/year boundary handling)

- **Key Metrics Feature (2025-12-27)**: Implemented "Metrics You Need to Know" for prioritized metric tracking:
  - Database: `key_metrics_config` JSONB column on `user_context` (migration zh)
  - Backend: Pydantic models (KeyMetricConfig, KeyMetricDisplay, KeyMetricsResponse), trend calculation from benchmark_history
  - API: GET `/api/v1/context/key-metrics`, PUT `/api/v1/context/key-metrics/config`
  - Service: `get_key_metrics_for_user()` aggregates user metrics, calculates trends (up/down/stable), industry comparisons
  - Frontend: `/context/key-metrics` page with 3 sections (Focus Now, Track Later, Monitor), trend arrows, benchmark bars
  - Navigation: Added to Context dropdown in header
  - Tests: 31 unit tests for model validation
  - Displays user's prioritized metrics with pendulum trend indicators

- **Waitlist Form 500 Error Fix (2025-12-27)**: Fixed production waitlist form returning 500 error:
  - Root cause: slowapi rate limiter requires first parameter to be named `request` (starlette.requests.Request)
  - Waitlist endpoints used `http_request` causing slowapi to throw exception
  - Renamed `http_request` → `request` and `request` → `body` in both endpoints
  - Updated corresponding tests
  - This was why 48 unique visitors → 0 signups on the waitlist page

- **Admin Blog Rate Limiting (2025-12-27)**: Added missing rate limiting to all 9 admin blog endpoints:
  - Added `@limiter.limit(ADMIN_RATE_LIMIT)` to: list_posts, create_post, get_post, update_post, delete_post, generate_post, discover_blog_topics, publish_post, schedule_post
  - Consistent with other admin endpoints (1200/minute)
  - Prevents 429 cascade during admin dashboard load

- **Admin Dashboard Drillable Cards (2025-12-27)**: Made all admin dashboard stat cards navigable:
  - Total Users → `/admin/users`
  - Total Meetings → `/admin/sessions`
  - Total Cost → `/admin/costs`
  - Whitelist Count → `/admin/whitelist`
  - Added hover effects (shadow, border color change) matching existing Waitlist card style
  - Proper `<a>` tags for accessibility (keyboard nav, right-click context menu)

- **GDPR Consent OAuth Fix (2025-12-27)**: Fixed 403 error when recording GDPR consent during OAuth callback:
  - Root cause: callback page used raw `fetch()` without CSRF token header
  - Added `recordGdprConsent()` method to apiClient with proper CSRF handling
  - Updated callback page to call `apiClient.recordGdprConsent()` after `initAuth()` (ensures CSRF cookie set)
  - Removed unused imports (`env`, `ApiClientError`)

- **SEO Topic Discovery Fix (2025-12-27)**: Fixed 'Discover' button in BlogGenerateModal:
  - Added `TopicDiscoveryError` exception class for specific error handling
  - Improved LLM prompt for reliable JSON output (explicit schema, lower temperature 0.6)
  - Added retry logic (max 2 attempts) on JSON parse failures
  - Added debug logging for raw LLM responses
  - API returns 429/500 with descriptive error messages
  - Frontend shows specific error messages with retry button
  - Added loading state with "5-10 seconds" timing hint
  - Added `USE_MOCK_TOPIC_DISCOVERY=true` env flag for local dev
  - Tests: 8 new tests (4 API endpoint, 4 service unit tests)

- **Local Development Auth Fix (2025-12-27)**: Fixed authentication not working in local development:
  - Created `.env.local.example` with documented local dev auth variables
  - Updated `docker-compose.yml` to explicitly pass SuperTokens env vars to API container
  - Added `backend/api/startup_validation.py` with auth config validation at startup
  - Created `docs/runbooks/local-dev-auth.md` with setup guide and troubleshooting
  - Added `make auth-check` Makefile target for diagnostics
  - Validates SuperTokens Core reachability, OAuth provider credentials, cookie settings

- **Cross-User Research Sharing (2025-12-27)**: Implemented opt-in research sharing between users:
  - Database: `research_sharing_consent` table + `user_id`/`is_shareable` columns on `research_cache` (migration zg)
  - Backend: Consent service (give/revoke/check), cache filtering with shared research lookup
  - API: GET/POST/DELETE `/api/v1/research-sharing/consent` endpoints
  - ResearcherAgent: Pass `user_id` and `sharing_consented` for cache save/lookup
  - Graph: `research_sharing_consented` state field, `shared` flag in research results
  - Frontend: Toggle in Settings > Privacy with privacy explanation
  - Tests: 5 unit tests for consent service, 8 unit tests for cache filtering
  - Privacy-first: Only research findings shared, never PII; explicit consent required

- **Peer Benchmarking (2025-12-27)**: Implemented anonymous peer comparison feature:
  - Database: `peer_benchmark_consent` + `peer_benchmark_aggregates` tables (migration zf)
  - Backend: Consent service (give/revoke/check), aggregation with k-anonymity (min 5 peers)
  - API: GET/POST/DELETE `/api/v1/peer-benchmarks/consent`, GET `/api/v1/peer-benchmarks`, GET `/api/v1/peer-benchmarks/compare`
  - Billing: `peer_benchmarks_visible` (free=3, starter=5, pro=unlimited) via PlanConfig
  - Frontend: `/context/peer-benchmarks` page with consent toggle, percentile cards, tier-gated metrics
  - Navigation: Added to Context dropdown
  - Tests: 23 unit tests for service and model validation

- **Project Management Blog Post (2025-12-27)**: Created SEO-optimized blog article "Bo1 for Light-Touch Project Management: Ditch the Complexity":
  - ~1000 words covering: lightweight PM without Jira/Asana, meeting mode for scoping, Kanban actions, Gantt timeline, mentor for risks, calendar sync
  - Script: `backend/scripts/create_project_management_article.py` for article creation
  - Article stored as draft in seo_blog_articles (id=6), ready for review and publishing

- **Analytics Blog Post (2025-12-27)**: Created SEO-optimized blog article "Bo1 for Analytics: Make Sense of Your Data with AI Deliberation":
  - ~1000 words covering: data import (CSV/Sheets), Dataset Q&A, meeting mode for analytics interpretation, mentor mode for KPI setup
  - Real examples: churn analysis, revenue trends, marketing attribution, user behavior patterns
  - Script: `backend/scripts/create_analytics_article.py` for article creation
  - Article stored as draft in seo_blog_articles (id=5), ready for review and publishing

- **Stripe Configuration Runbook (2025-12-27)**: Created `docs/runbooks/stripe-config.md`:
  - Documents test/live mode price ID tables
  - Step-by-step setup: products, webhook, customer portal
  - Environment variable reference (PUBLIC_STRIPE_PRICE_STARTER, PUBLIC_STRIPE_PRICE_PRO)
  - Verification checklist and go-live instructions

- **Solo Founders Blog Post (2025-12-26)**: Created SEO-optimized blog article "Bo1 for Solo Founders: Your Board in a Box":
  - ~1000 words covering: solo decision-making (board in a box), meeting prep, SMB team alignment
  - Script: `backend/scripts/create_solo_founders_article.py` for article creation
  - Article stored as draft in seo_blog_articles (id=3), ready for review and publishing

- **Dogfooding Blog Post (2025-12-26)**: Created SEO-optimized blog article "How We Built Bo1 Using Bo1: A Dogfooding Story":
  - ~1200 words covering prioritization with meeting mode, mentor mode for pricing, actions system for launch management
  - Script: `backend/scripts/create_dogfooding_article.py` for article creation
  - Article stored as draft in seo_blog_articles (id=2), ready for review and publishing

- **Emergency Access Procedures (2025-12-26)**: Created E2E tests and runbook for emergency admin procedures:
  - E2E tests: `tests/e2e/test_admin_impersonation.py` (12 tests) for full impersonation lifecycle
  - E2E tests: `tests/e2e/test_emergency_toggles.py` (14 tests) for runtime config toggle flow
  - Runbook: `docs/runbooks/emergency-access.md` documenting impersonation, runtime toggles, session kill, database access
  - All tests pass with memory-based rate limiter for test isolation

- **SEO Content Analytics (2025-12-26)**: Implemented article view/click/signup tracking and admin dashboard:
  - Database: `seo_article_events` table (migration ze) with event_type, UTM params, session tracking
  - Backend: `POST /api/v1/seo/articles/{id}/events` (public, rate-limited 30/min), `GET /api/v1/seo/articles/{id}/analytics`, `GET /api/v1/seo/analytics`
  - Admin: `GET /api/admin/seo/analytics` with summary stats, top articles by views/conversion
  - Frontend: `seoTracking.ts` utility with `trackArticleView()`, `trackArticleClick()`, `trackArticleSignup()`, de-duplicated view tracking
  - Admin UI: `/admin/seo` page with summary cards, time-based metrics, top articles tables
  - Tests: 20 unit tests for ArticleEventCreate, ArticleAnalytics, ArticleAnalyticsListResponse models

- **Strategic Objective Progress (2025-12-26)**: Implemented per-objective progress tracking on dashboard:
  - Backend: GET/PUT/DELETE `/api/v1/context/objectives/{index}/progress` endpoints
  - Database: `strategic_objectives_progress` JSONB column on user_context (migration zd)
  - Pydantic models: ObjectiveProgress, ObjectiveProgressUpdate, ObjectiveProgressResponse, ObjectiveProgressListResponse
  - Frontend: GoalBanner shows "current → target" pills next to each objective, clickable to edit
  - Modal: ObjectiveProgressModal with current/target inputs and unit presets (%, $, MRR, customers)
  - Dashboard integration: fetches progress on mount, modal save updates state
  - Tests: 15 unit tests for Pydantic model validation

- **SEO Blog Generator (2025-12-26)**: Implemented SEO article generation from topics:
  - Backend: `POST /topics/{id}/generate` and CRUD endpoints for `/api/v1/seo/articles`
  - Database: `seo_blog_articles` table (migration zc) with title, excerpt, content, meta fields, status
  - Billing: `seo_articles_monthly` limit (free=1, starter=5, pro=unlimited) via PlanConfig
  - Rate limiting: 2 requests/minute via SEO_GENERATE_RATE_LIMIT
  - Frontend: "Generate Article" button on topics table, Generated Articles card with copy-to-clipboard
  - Tests: 17 unit tests for article Pydantic model validation

- **SEO Topics Table (2025-12-26)**: Implemented SEO topics tracking for blog generation workflow:
  - Backend: CRUD endpoints `/api/v1/seo/topics` (list/create/update/delete)
  - Database: `seo_topics` table with keyword, status (researched/writing/published), source_analysis FK, notes
  - Frontend: Topics table in /seo page with "Add to Topics" on opportunities, status badges, delete action
  - Tests: 17 unit tests for Pydantic model validation

- **SEO Trend Analyzer (2025-12-26)**: Implemented `/seo` route with ResearcherAgent-powered analysis:
  - Backend: `/api/v1/seo/analyze-trends` and `/api/v1/seo/history` endpoints
  - Database: `seo_trend_analyses` table with user/workspace/keywords/results
  - Billing: Tier limits (free=1/month, starter=5, pro=unlimited) via PlanConfig
  - Rate limiting: 5 requests/minute via SEO_ANALYZE_RATE_LIMIT
  - Frontend: Full UI with keyword input, industry context, history sidebar
  - Navigation: Added "SEO Tools" to Board dropdown

- **Onboarding first-login flow (2025-12-26)**: After onboarding tour completes, redirect to `/context/overview` with dismissible welcome banner:
  - Updated `completeTour()` to set localStorage flag and return boolean for redirect handling
  - Dashboard redirects to context overview after tour completion
  - Context overview shows one-time welcome banner explaining context setup benefits
  - Added 3 unit tests for completeTour localStorage behavior

- **Plan limits audit (2025-12-26)**: Migrated `backend/api/user.py` from deprecated `TierLimits`/`TierFeatureFlags` to `PlanConfig`:
  - Updated `/api/v1/user/usage` and `/api/v1/user/tier-info` endpoints
  - All tier-enforced endpoints now use centralized `PlanConfig`
  - Added docstring notes for deprecated class tests

- **Centralized plan configuration (2025-12-26)**: Created `bo1/billing/config.py` with unified `PlanConfig`:
  - Single source of truth for all tier limits, features, and pricing
  - Updated billing.py, usage_tracking.py, industry_insights.py to use new config
  - Deprecated TierLimits, TierFeatureFlags, IndustryBenchmarkLimits (backward compat maintained)
  - Added 33 unit tests for PlanConfig

- **Rate limits audit (2025-12-26)**: Extended rate limiting coverage:
  - Added 10 new rate limit constants (CONTEXT, USER, PROJECTS, MENTOR, BUSINESS_METRICS, etc.)
  - Raised STREAMING limit from 20/min to 30/min for reconnection resilience
  - Applied rate limits to LLM-heavy endpoints: mentor/chat, mentor/improvement-plan, context/enrich, context/competitors/detect, context/trends/refresh

- **UX audit fixes (2025-12-26)**: 4 issues from UX/UI comprehensive audit:
  - Context API 500 errors: Root cause was missing `action_metric_triggers` column in production (migration fb2)
  - Navigation dropdowns: Increased z-index for proper stacking context
  - Status page traffic API: Graceful "coming soon" state for unimplemented endpoint

- **Batch run (2025-12-26)**: 17 tasks completed including:
  - GDPR consent extension & multi-policy enforcement
  - User feedback system (meeting & action ratings)
  - Benchmark metrics expanded (12→22 metrics)
  - Market trends content extraction & refresh logic
  - Insights staleness detection (90/180 days) & action-triggered staleness (28 days)
  - Onboarding tour fixes (step 2 buttons, exit flow, popup persistence)
  - Dashboard strategic objectives tick fix
  - Competitors 503 error fix, duplicate buttons UX, enrich database error fix
  - Market trends tier gating & default "Now" view
  - Projects unassigned-count 500 error fix
  - Analytics.boardof.one 502 nginx error fix

### Core Platform

- **Data Analysis Platform**: Ingestion (DO Spaces, CSV, Google Sheets), Profiling, Query Engine, Meeting Integration, Dataset Q&A, UI
- **Meetings & Sessions**: Multi-agent deliberation, SSE streaming, export/sharing, error handling, cap enforcement, wall-clock timeout, retry/resume from checkpoint
- **Actions System**: Kanban, Gantt, reminders, bidirectional status, close/replan, calendar sync, post-mortems, blocker analyzer, blocker escalation
- **Projects**: CRUD, Gantt, auto-generation, versioning, workspace constraints, meeting templates
- **Mentor Mode**: Expert personas, proactive patterns, @ mentions, chat persistence, auto-labeling, post-mortem insights

### Business Features

- **Billing**: Stripe integration, tier middleware, beta caps, cost tracking, per-user metrics
- **Workspaces**: Schema, authorization, invitations, auto-creation, switching
- **Promotions**: Schema, services, admin UI, Stripe integration
- **Context System**: Insights, staleness tracking, benchmarks (22 metrics), north star goal with history, competitor detection (manual + auto), managed competitors, trend analysis, market trend forecasts (3m/12m/24m with tier-gating)
- **Legal & Consent**: T&C versioning, GDPR consent, multi-policy enforcement, consent audit logs

### Admin & Ops

- **Admin Dashboard**: Sessions, costs, KPIs, kill history, alerts, users, waitlist, promotions, impersonation, blog management, template management, email metrics, research cache metrics, A/B experiments, feedback tracking
- **AI Ops**: Error detection, auto-remediation, self-monitoring
- **Observability**: Prometheus metrics, Grafana dashboards, Loki logging, graph node instrumentation
- **Monitoring**: Health checks (Redis, Postgres, Anthropic, Voyage, Brave, ClamAV), pool exhaustion alerts

### Security & Compliance

- **Security**: Rate limiting, prompt injection detection, SQL validation, metrics auth, input sanitization
- **GDPR**: Data export, deletion/anonymization, audit logging, retention, consent capture
- **Supply Chain**: Pinned versions, OSV-Scanner, pip-audit, Trivy, Dependabot
- **Web Security**: Nonce-based CSP, CSRF, HSTS, WAF rules, ClamAV scanning

### Architecture & Performance

- **Architecture**: Parallel initial round (60-70% latency reduction), SSE state transitions, PostgreSQL polling fallback, circuit breaker fallback
- **Performance**: Session metadata cache, aggregation caching, contribution pruning, covering indexes, pool size tuning
- **Data Model**: Pydantic models, OpenAPI type generation, schema audit scripts

### Quality & Testing

- **E2E Tests**: Dashboard, settings, meeting-create, meeting-complete, actions, datasets, admin
- **Security Tests**: Auth, authz, input validation, prompt injection (132 cases), rate limiting, SQL injection
- **Chaos Tests**: Provider fallback, SSE Redis fallback, circuit breaker behavior

### UX & Frontend

- **Navigation**: Grouped sidebar, dropdowns, loading skeletons
- **Toast System**: Success/error/info/warning with auto-dismiss
- **Accessibility**: Skip links, ARIA labels, focus traps, landmarks
- **Onboarding**: driver.js tour with exit flow
- **shadcn Migration**: Button, Input, Badge, Alert, Card
- **Dashboard**: Goal banner, weekly plan, daily activities

### LLM Alignment

- **Cost Reduction**: Lean synthesis (30-60% reduction), Haiku extended to round 3, A/B persona count experiment
- **Output Validation**: Challenge phase validation, XML parsing, output length warnings
- **Sanitization**: All LLM call sites sanitized

### Infrastructure

- **Deployment**: GitHub Actions CI, PostgreSQL backups, Redis persistence, blue-green deployment
- **Email**: Resend integration with templates
- **Analytics**: Umami self-hosted, UptimeRobot monitoring
- **Integrations**: Google Calendar OAuth + action sync

### Documentation

- Help center (16 articles), privacy policy, terms of service, runbooks, SSE events docs

---

_For detailed implementation notes, see git history._
