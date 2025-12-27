# Task Backlog

_Last updated: 2025-12-27_

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

## Completed Summary

### December 2025

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
