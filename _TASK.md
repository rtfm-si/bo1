# Task Backlog

_Last updated: 2026-02-03 (Full Audit Suite - DRY focus)_

---

## Open Tasks

### DRY Violation Fixes (from Full Audit 2026-02-03)

**DATA MODEL DRY (80+ instances)**
- [x] [DATA][P1] Create `bo1/models/util.py` with `normalize_uuid()` and `coerce_enum()` helpers - consolidates 15+ UUID and 8+ enum coercion patterns ✅ DONE
- [x] [DATA][P1] Create `from_db_row` base mixin for model instantiation - standardizes 15 model methods ✅ DONE
- [x] [DATA][P2] Merge `WorkspaceRole` + `MemberRole` enums - single source in bo1/models/workspace.py ✅ DONE
- [x] [DATA][P2] Create `BaseAuditModel` with `created_at`, `updated_at` - reduces duplication in 4 models ✅ DONE
- [x] [DATA][P3] Document domain→response model mapping rationale - clarify Session/SessionResponse duplication ✅ DONE

**LLM/PROMPT DRY (Already addressed)**
- [x] [LLM] protocols.py consolidation - CORE_PROTOCOL eliminates ~180 tokens/contribution duplication ✅ DONE

**PERFORMANCE/DB DRY (Already addressed)**
- [x] [PERF] BaseRepository pattern - all 22 repositories extend BaseRepository ✅ DONE
- [x] [PERF] _execute_query(), _execute_one() helpers standardized ✅ DONE

### Audit Findings (Non-DRY)

**Architecture (Minor)**
- [x] [ARCH][P3] Use router registry in graph config - replace direct imports with `get_router("name")` ✅ DONE
- [x] [ARCH][P4] Document parallel subproblems flag impact - add ADR for two topologies ✅ DONE (docs/adr/005-parallel-subproblems-graph-topology.md)

**Observability (Gaps)**
- [x] [OBS][P3] Evaluate OpenTelemetry adoption - add span tracing for LLM calls ✅ DONE (bo1/observability/tracing.py, OTEL_ENABLED=true to enable)
- [x] [OBS][P3] Activate Sentry SDK - if error aggregation desired beyond logging ✅ DONE (bo1/observability/sentry.py, SENTRY_DSN to enable)

**Reliability (Minor)**
- [x] [REL][P3] Add thread-safe circuit breaker option - current uses asyncio.Lock (not thread-safe for sync) ✅ DONE (threading.Lock for call_sync)
- [x] [REL][P4] Make pool polling interval configurable - DatabaseConfig.POOL_POLLING_INTERVAL_MS ✅ DONE

**Cost Optimization (Opportunities)**
- [x] [COST][P2] Cache sub-problem context across personas - estimated $0.10-0.30/session savings ✅ DONE
- [x] [COST][P3] Batch research queries - combine multiple Brave/Tavily calls ✅ DONE (parallel asyncio.gather in benchmark researcher + competitor bulk enrich)
- [x] [COST][P3] Profile cache hit rate per prompt type - enable data-driven optimization ✅ DONE (bo1_prompt_type_cache_total Prometheus metric + /api/admin/costs/prompt-cache-by-type endpoint)

**LLM Alignment (Minor)**
- [x] [LLM][P2] Add challenge phase contribution validation - reject rounds 3-4 without disagreement markers ✅ DONE (bo1/prompts/validation.py)
- [x] [LLM][P3] Track prompt cache hit rate per prompt type - add metrics ✅ DONE

**Performance (Minor)**
- [x] [PERF][P2] Add contribution pruning after round summary - reduce memory during long deliberations ✅ DONE (bo1/graph/state.py)
- [x] [PERF][P3] Add session metadata cache hit metrics - track cache effectiveness ✅ DONE


### Blocked on User Action (NOT AUTOMATABLE)

- [ ] [LAUNCH][P1] Switch Stripe to live mode - see `docs/runbooks/stripe-config.md` ⛔ MANUAL
- [ ] [EMAIL][P4] Payment receipt email trigger - blocked on Stripe live mode ⛔ BLOCKED
- [ ] [SOCIAL][P3] Direct posting to social accounts - user to decide approach ⛔ MANUAL
- [ ] [SEC][P1] Verify DO Spaces encryption-at-rest configuration ⛔ MANUAL (check DO dashboard)

### Needs Clarification (NOT AUTOMATABLE)

- [ ] [MONITORING][P1] Kubernetes deployment manifest - are we using k8s? (current: SSH to droplet) ⛔ UNCLEAR
- [ ] [MONITORING] Clarify "grafana logs: value A" requirement ⛔ UNCLEAR
- [ ] [DATA][P2] Clarify data retention soft-delete behavior ⛔ UNCLEAR
- [ ] [ARCH] Clarify scope of: "deduplication, redundancy, obsolescence check, DRY, code simplification plan" ⛔ UNCLEAR
- [ ] [AUTH] Clarify scope of: "get google auth thing working properly" - identify failure cases ⛔ UNCLEAR
- [ ] [AUTH] Clarify scope of: "get account sync working properly" - identify sync issues ⛔ UNCLEAR
- [ ] [SEO] Clarify scope of: "still needs work" - define specific improvements ⛔ UNCLEAR
- [ ] [BILLING] Clarify pricing model: advisor chats, SEO, data analysis ⛔ UNCLEAR
- [ ] [BILLING] Clarify pricing model: reports - 1 free then paywall, or all free? ⛔ UNCLEAR
- [x] [UI][P2] Remove 'recent analyses' section - moved to dropdown in form header

### Deferred by Design

- [ ] [COST][P2] Run persona count A/B test - need ≥100 sessions per variant ⛔ DEFERRED
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have ⛔ DEFERRED

### User-Owned

- [ ] [DOCS][P3] Help pages content review (Si's todo)

### Backlog (from _TODO.md, 2026-01-10)

- [x] [REFACTOR] Rename mentor routes to 'advisor' (URL paths, API endpoints, component names)
- [x] [UI] Advisor/Analyze: Reduce data load section prominence, increase datasets section space
- [x] [FEATURE] Add dataset folders with names, tags, and organization support
- [x] [BUG] Fix data requirements endpoint 401/500 errors (GET /api/v1/objectives/data-requirements)
- [x] [UI] Advisor/Grow: Streamline 4 cards layout (too cramped)
- [x] [FEATURE] Advisor/Grow: Analyze user-submitted words or auto-suggest best topics
- [x] [UX] Advisor/Grow: Go straight to generated article with revision options
- [x] [UI] Context: Remove "explore more context" element
- [x] [FEATURE] Auto-map context insights to context metrics where possible
- [x] [BUG] Competitors: Enrichment now functional with per-row + bulk refresh, improved query building
- [x] [FEATURE] Align industry benchmarks to chosen focus metrics for business, industry, and objectives
- [x] [BUG] Fix market trends refresh endpoint 500 error (POST /api/v1/context/trends/summary/refresh)
- [x] [FEATURE] Market trends: Extract and summarize articles instead of showing raw news stories
- [x] [TECH-DEBT] Audit codebase for direct LLM model references and centralize to config only
- [x] [FEATURE] Context/Metrics: Add "help me calculate" dialog for building metrics from Q&A
- [x] [FEATURE] Store metric calculation Q&A answers as insights
- [x] [RESEARCH] Identify UX opportunities for embeddings or web research (Brave/Tavily) integration

### Feature Opportunities (from Embeddings/Web Research Audit, 2026-01-11)

See `docs/research/embeddings-web-research.md` for full analysis.

- [x] [FEATURE][P2] Advisor conversation search - semantic search over past Q&A (uses existing TopicDetector)
- [x] [FEATURE][P3] Dataset similarity discovery - find similar datasets/analyses using embeddings
- [x] [FEATURE][P3] SEO topic validation - web research to verify topic suggestions with competitor data
- [x] [FEATURE][P4] Context insight enrichment - auto-add market context to user-submitted metrics
- [x] [FEATURE][P4] Competitor intelligence - deeper web research on added competitors (news, funding)

---

## Completed Summary

### 2026-01-11

**Competitor Intelligence (Deep Research)**: Added multi-query Tavily-based intelligence gathering for Pro tier competitors. Backend: `CompetitorIntelligenceService` in `backend/services/competitor_intelligence.py` with 3 parallel Tavily searches (funding from Crunchbase/TechCrunch, product updates from ProductHunt, general news), LLM parsing via Haiku into structured data (FundingRound, ProductUpdate dataclasses). New `CompetitorIntel` dataclass with funding_rounds, product_updates, recent_news, key_signals fields. `intel_to_dict()` helper for JSON serialization. Database: Migration `zzu_competitor_intel_columns` adding 4 JSONB columns (product_updates, key_signals, funding_rounds, intel_gathered_at) to competitor_profiles. Updated `CompetitorProfile` model and `row_to_profile()`. Modified `enrich_competitor` endpoint to call intelligence service for deep tier, storing results in new columns. Frontend: Extended `ManagedCompetitor` TypeScript interface with intel fields, updated `CompetitorManager.svelte` with "Deep Intelligence" expandable section showing key signals as badges, funding rounds with amounts/dates/investors, product updates with descriptions and source links. 13 unit tests.

**Context Insight Enrichment**: Added market benchmark context to metric insights. Backend: Created `InsightEnrichmentService` in `backend/services/insight_enrichment.py` with `enrich_insight()` method that fetches industry benchmarks via `IndustryBenchmarkResearcher`, calculates percentile position (handling "lower is better" metrics like CAC/churn), generates human-readable comparison text. Extended `ClarificationStorageEntry` with `market_context` field (`MarketContext` model: benchmark_value, percentile_position 0-100, comparison_text, source_url, enriched_at, confidence). Added auto-enrichment trigger in `calculate_metric` endpoint (async background task). New manual enrichment endpoint `POST /api/v1/context/insights/{question_key}/enrich` with `InsightEnrichResponse` model. Frontend: Added `InsightMarketContext` and `InsightEnrichResponse` types, `enrichInsight()` API client method, market context badge display on insights page (percentile position, comparison text, source link), "Enrich" button for insights with metrics but no market context. 29 unit tests covering models, serialization, service methods, percentile calculations, and endpoint responses.

**SEO Topic Validation**: Added web research validation for topic suggestions. Backend: Extended `TopicSuggestion` model with `validation_status`, `competitor_presence`, `search_volume_indicator`, `validation_sources` fields. Added `skip_validation` parameter to `AnalyzeTopicsRequest`. New `_validate_topic_with_web_research()` helper using ResearcherAgent to check competitor presence and search volume via web searches. Updated `analyze_topics` endpoint to fetch user's competitors and validate top 5 suggestions (unless skip_validation=True). Added `seo_validation` cache category (30-day freshness). Frontend: Extended TypeScript `TopicSuggestion` interface with validation fields, updated `analyzeSeoTopics()` API client method to support skipValidation parameter. Updated `SeoTools.svelte` with: skip validation checkbox, validation status checkmark icon, competitor presence badge (high=error, medium=warning, low=success), search volume badge, collapsible validation sources with links. 22 unit tests covering model validation fields, skip_validation request parameter, and validation status values.

**Dataset Similarity Discovery**: Added semantic dataset matching using embeddings. Backend: `DatasetSimilarityService` with `SimilarDataset` dataclass, `find_similar_datasets()` using Voyage AI embeddings to compare dataset metadata (name, description, columns, summaries), Redis caching with 7-day TTL, shared column detection, new `GET /api/v1/datasets/{id}/similar` endpoint with threshold (0.4-0.9) and limit (1-10) parameters. Pydantic models: `SimilarDatasetItem`, `SimilarDatasetsResponse`. Frontend: TypeScript types (`SimilarDataset`, `SimilarDatasetsResponse`), `getSimilarDatasets()` API client method, `SimilarDatasetsPanel.svelte` component with collapsible "Find Similar" button, similarity percentages, shared column chips, insight preview, click-to-navigate. 35 unit tests covering service methods, caching, API endpoint validation, and response serialization.

**Advisor Conversation Search**: Added semantic search over past advisor conversations. Backend: `SimilarMessage` dataclass in TopicDetector, `find_similar_messages()` method using cached embeddings for zero additional API cost, new `/api/v1/advisor/search` endpoint with Pydantic models (`ConversationSearchResult`, `ConversationSearchResponse`), query parameters for threshold (0.5-0.95), limit (1-20), days (7-365). Frontend: TypeScript types, `searchAdvisorConversations()` API client method, search UI in MentorChat header with search icon toggle, debounced input, results dropdown showing preview + similarity percentage, click-to-load conversation. 12 unit tests covering endpoint validation, threshold filtering, user ownership, empty states, and TopicDetector method behavior.

**Embeddings & Web Research UX Audit**: Research pass identifying 5 UX integration opportunities. Created `docs/research/embeddings-web-research.md` documenting: (1) mature embedding infrastructure (Voyage AI, pgvector, semantic dedup, topic detection, admin visualization), (2) web research providers (Brave Search, Tavily AI), (3) prioritized opportunities with value/complexity matrix. Recommended first feature: Advisor conversation search using existing TopicDetector. Added 5 feature tasks to backlog.

**Benchmark Alignment to Objectives**: Added objective-aware benchmark prioritization. Backend: `benchmark_alignment.py` with `OBJECTIVE_METRICS` mapping 5 objectives (acquire_customers, improve_retention, raise_capital, launch_product, reduce_costs) to their 4 most relevant metrics each. `STAGE_WEIGHTS` modifies relevance by business stage (idea, early, growing, scaling). `score_benchmark_relevance()` returns (score, reason, is_aligned) tuple. Extended `BenchmarkComparison` model with `relevance_score`, `relevance_reason`, `is_objective_aligned` fields. Updated compare endpoint to sort benchmarks by relevance (highest first) before applying tier limits. Frontend: Added `AlignedBenchmarkComparison` interface extending `BenchmarkComparison`, updated `IndustryBenchmarksTab.svelte` with "Most Relevant for Your Goals" section showing objective-aligned metrics with star badges and relevance reasons, added "Set Your Objective" CTA when no objective is set. 17 unit tests.

**Insight-to-Metric Auto-Mapping**: Added keyword-based insight-to-business-metric mapping. Backend: `metric_mapping.py` with `METRIC_KEYWORDS` covering 13 metrics (MRR, ARR, burn_rate, runway, gross_margin, churn, NPS, CAC, LTV, ltv_cac_ratio, AOV, conversion_rate, return_rate), each with keywords, category, and value extraction patterns. `match_insight_to_metrics()` uses multi-factor scoring (category +0.3, keywords +0.4, value pattern +0.3). `get_insight_metric_suggestions()` aggregates best match per metric. Added 3 API endpoints (`GET /metrics/suggestions`, `POST /metrics/suggestions/apply`, `POST /metrics/suggestions/dismiss`). New Pydantic models (`BusinessMetricSuggestion`, `BusinessMetricSuggestionsResponse`, apply/dismiss request/response models). Frontend: Added types, API client methods, `BusinessMetricSuggestions.svelte` component on metrics page showing suggestions with Apply/Dismiss actions. Dismissals stored in user context. 25 unit tests.

**Metric Calculation Q&A Dialog**: Added Q&A-guided metric calculation feature. Backend: `metric_questions.py` with question bank for 13 metrics (MRR, ARR, burn rate, runway, gross margin, churn, NPS, CAC, LTV, LTV:CAC ratio, AOV, conversion rate, return rate). Extended `ClarificationStorageEntry` with `source="calculation"` and `metric_key` fields. Added 3 API endpoints (`GET /metrics/calculable`, `GET /metrics/{key}/questions`, `POST /metrics/{key}/calculate`). Frontend: New types (`MetricQuestionDef`, `MetricFormulaResponse`, `MetricCalculationRequest/Response`), API client methods, `MetricCalculatorModal.svelte` component with 3-step wizard (select metric → answer questions → view result), "Help me calculate" CTA on metrics page. Calculation results are saved as insights with source_type="calculation". 32 unit tests.

**Article Revision UX for Advisor/Grow**: Auto-open ArticleDetailModal immediately after article generation. Made revision/regenerate panel visible by default (not collapsed). Added inline edit mode with textarea for direct markdown content editing, Save/Cancel buttons using PATCH endpoint via updateSeoArticle(). Unsaved changes warning on close. 3 new unit tests for partial update validation.

### 2026-01-10

**Topic Analysis for Advisor/Grow**: Added `/api/v1/seo/topics/analyze` endpoint with TopicSuggestion model (keyword, seo_potential, trend_status, related_keywords, description). Frontend: AnalyzeTopicsResponse type, analyzeSeoTopics() client method, "Analyze" button in SeoTools.svelte Content tab. Suggestions panel shows SEO potential badges, trend status, related keywords with one-click "Add to Topics". 14 unit tests.

**LLM Model References Centralization**: Removed hardcoded model references from llm_health_probe.py and cost_tracker.py. Added HEALTH_PROBE_MODEL constant to config.py, replaced duplicate ANTHROPIC_PRICING/VOYAGE_PRICING in cost_tracker.py with imports from config, updated fallback pricing lookup to use resolve_model_alias("sonnet"). All model IDs now flow through config.py.

**Dataset Folders API**: Added hierarchical folder organization for datasets with zzt migration (dataset_folders, dataset_folder_tags, dataset_folder_memberships tables), Pydantic models (bo1/models/dataset_folder.py), repository layer (dataset_folder_repository), full CRUD API endpoints (/api/v1/datasets/folders), tree view endpoint, tag management, dataset membership operations, frontend types and API client methods, 19 unit tests.

**Competitor Enrichment & Detection**: Added managed competitor enrichment endpoints (single + bulk), enrichment UI in CompetitorManager.svelte with per-row enrich button and "Refresh All", expandable enrichment details (tagline, description, funding, employees, news), improved _build_competitor_search_query() to use target_market and business_model context, 12 new tests.

### 2026-01-08

**DuckDB Large Dataset Support**: Added duckdb>=1.0.0 dep, duckdb_engine.py with query functions (filter/aggregate/trend/compare/correlate), auto-backend selection at 100K threshold, updated profiler/chart_generator, 39 new tests.

**Multi-Dataset Analysis**: MultiDatasetAnalyzer service detecting schema drift, type mismatches, metric outliers; zzq migration; API endpoints POST/GET/DELETE /api/v1/datasets/multi-analysis; Compare Datasets UI; 16 unit tests.

**PII Detection**: Warning system for potential PII columns before upload, user acknowledgment requirement, zzo migration for pii_acknowledged_at column.

**Data Reports Persistence**: FK SET NULL migration, LEFT JOIN queries, standalone report route /reports/data/{id}, "Dataset Deleted" indicator.

**Navigation Restructure**: Renamed Assistant→Advisor, moved to top-level, converted tabs to pages (Discuss/Analyze/Grow).

**CSV Robustness**: skip_leading_empty_rows() in csv_utils.py, 14 new tests.

**Admin SEO Access**: Added seo_access promo type, check_seo_access_promo() service, has_seo_access() helper, SEO toggle in admin users page, 14 unit tests.

**Stripe Billing Fix**: validate_stripe_key() in BillingSyncService, GET /stripe/status endpoint, UI warning banner when unconfigured.

**Onboarding Audit**: Fixed missing tour selectors, corrected link routes, improved settings completion detection.

**Build Fixes**: Svelte 5 `<title>` content, missing imports, invalid tag syntax, Badge variants, TypeScript errors.

### 2026-01-07

- ContributionMessage schema drift fix (user_id, status fields)
- Session nullable field consistency fix (phase, total_cost, round_number defaults)
- Reduced persona context window from 5 to 3 contributions
- Moved event publishing out of routers (6 new unit tests)

### 2026-01-06

**Audit Tasks (12 completed)**:
- P1: Composite indexes, action tag CTE+JOIN optimization, pg_stat_statements, Redis pool metrics, error response standardization (32 files migrated), text field validation
- P2: Session metadata caching, aggregation caching, contribution pruning, Recommendation model fields, Redis PostgreSQL fallback, SSE reconnection backoff, deadlock retry, persona protocol compression, sanitization tests (1184 lines)
- P3: Statement timeout, error rate metrics, router registry

### 2026-01-05

- Metrics smart selection (top 5 relevant based on business context)
- D2C/product-specific metrics (INVENTORY, MARGIN, CONVERSION, AOV, COGS, RETURNS)
- "Need a new metric?" CTA

### 2026-01-04

**Navigation Consolidation**:
- Board Menu: Consolidated datasets/analysis/mentor into single Mentor page with tabs
- Context Menu: Merged strategic into overview, created reports/trends, moved benchmarks to reports
- Dashboard: Key-metrics redirect, ResearchHeadlinesWidget with newspaper-style layout

**Feature Explorer Issues (2 sessions, 11 fixes)**:
- Session sharing 500s, 2FA setup 403/500, dataset insights 422, managed competitors 503, @mention context, project detail 500, SEO module 404

**Data Analysis**:
- Column detection fix, auto-run exploratory analysis on load
- Generated articles: click-through, regenerate with changes, brand tone

**SEO**:
- Manual topic addition, autogenerate topics button, removed industry box

**UI Fixes**:
- Currency display, version number, duplicate breadcrumbs, analysis output markdown rendering
- Peer benchmarks moved to reports/benchmarks with tabs, metrics relevance dismiss/restore

### Earlier (December 2025 - January 2026)

See git history for detailed implementation notes on:
- 2FA authentication with backup codes
- Magic link fixes and rate limiting
- Account linking (SuperTokens AccountLinking recipe)
- Password security (12+ char requirement)
- Language adaptation (StyleProfile enum)
- E2E reliability (retry logic, circuit breaker, model fallback, checkpoint recovery)
- Dashboard redesign (Week Planner, SmartFocusBanner, etc.)
- Admin improvements (emergency toggles, A/B experiments, cost drill-downs)
- Analysis features (question history, column reference, chart suggestions)
- Fair usage & billing (per-feature limits, bundles, nonprofit tier)
- SEO platform (trend analyzer, article generator, content analytics)
- Core platform (multi-agent deliberation, SSE streaming, actions, projects)
- Security (rate limiting, prompt injection 132 tests, SQL validation, GDPR)
- Infrastructure (blue-green deploy, PostgreSQL backups, Prometheus/Grafana/Loki)
- LLM optimization (lean synthesis 30-60% cost reduction, Haiku to round 3)

---

_For detailed implementation notes, see git history._
