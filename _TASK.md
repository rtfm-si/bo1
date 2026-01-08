# Task Backlog

_Last updated: 2026-01-08 (Build pass - backlog verified complete)_

---

## Open Tasks

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
- [ ] [UI][P2] Remove 'recent analyses' section (clarify location first) ⛔ UNCLEAR

### Deferred by Design

- [ ] [COST][P2] Run persona count A/B test - need ≥100 sessions per variant ⛔ DEFERRED
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have ⛔ DEFERRED

### User-Owned

- [ ] [DOCS][P3] Help pages content review (Si's todo)

---

## Completed Summary

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
