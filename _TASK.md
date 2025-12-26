# Task Backlog

_Last updated: 2025-12-26 (A/B persona count experiment: 3 vs 5 personas with admin metrics dashboard)_

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
- [ ] [MONITORING] Clarify "grafana logs: value A" (ambiguous)
- [ ] [DATA][P2] Clarify data retention soft-delete behavior: confirm soft-delete for retention vs hard-delete only on account deletion (RTBF compliance)

### User-Owned

- [ ] [DOCS][P3] Help pages content review and polish (Si's todo)

---

## Incomplete Tasks

### Cost Optimization [COST]

- [x] [COST][P4] Run A/B test comparing 3 vs 5 personas for user satisfaction (potential 20-30% reduction)
- [x] [COST][P3] Monitor cache hit rate and adjust similarity threshold based on data (admin metrics dashboard with recommendations)
- [x] [COST][P3] Remove verbose examples from facilitator.py after model training stabilizes

### Features [FEAT]

- [x] [FEAT][P3] Blocker buster: escalate blocked items to new meeting with prior context
- [x] [FEAT][P2] Action update LLM summarizer: pass all action updates through LLM for improved formatting
- [x] [FEAT][P2] Action post-mortems: capture what went well and lessons learned on action completion
- [x] [FEAT][P3] Action post-mortems: feed insights into "ask mentor" for future improvement suggestions
- [x] [FEAT][P2] Data retention email notifications: send reminder emails at 28 days and 1 day before scheduled deletion
- [x] [FEAT][P2] Data retention acknowledgement UI: allow users to acknowledge and suppress future deletion reminders
- [x] [FEAT][P2] Default data retention period: set 2-year default retention for new user accounts
- [x] [LEGAL][P1] T&C document versioning: schema to store T&C versions with content, version number, published_at timestamp, and active status
- [x] [LEGAL][P1] T&C consent capture: store agreement timestamp, T&C version, and IP address on user signup/re-acceptance
- [x] [LEGAL][P2] T&C admin management UI: create, edit, preview, and publish new T&C versions with version history
- [x] [LEGAL][P2] T&C version tracking: prompt users to re-accept when T&C version changes, block access until accepted
- [x] [LEGAL][P2] T&C consent audit log: admin view showing user consent history with timestamps, versions, and IPs
- [x] [LEGAL][P2] Privacy settings consent history: display Legal Agreements card with T&C version, consent date, and privacy policy link

### Context Strategic Enhancements [CONTEXT]

- [x] [CONTEXT][P2] Market trends: display current market insights summary for user's industry (TrendSummaryCard, Brave Search + Haiku)
- [x] [CONTEXT][P3] Market trends: add 3m/12m/24m forecast views with tier-gated access (GET/POST /v1/context/trends/forecast, TrendSummaryCard timeframe selector)
- [x] [CONTEXT][P2] Competitors: auto-detect competitors from user's business context (background task, rate-limited 24h, tier-aware limits)
- [x] [CONTEXT][P2] North star goal tracking: track updates/changes to goals, show progress over time, prompt user on goal changes

### Research Infrastructure [RESEARCH]

- [x] [RESEARCH][P2] Tier research providers: use Brave for starter tier, Tavily for pro tier (competitor analysis, market trends)
- [x] [RESEARCH][P1] Audit all research call sites: verify using Brave/Tavily instead of Anthropic/OpenAI for web research (see `audits/reports/research-providers.report.md`)
- [x] [RESEARCH][P2] Track Brave and Tavily API costs in admin dashboard
- [x] [RESEARCH][P2] Research caching with embeddings: timestamp research, generate Voyage embeddings, search existing before new API calls
- [ ] [RESEARCH][P4] Cross-user research sharing: leverage research from similar business contexts (same industry) - requires privacy review

### Admin Dashboard [ADMIN]

- [x] [ADMIN][P2] Drill-down views for top-level counts (users, costs, waitlist, whitelist) with time period filters (1h, 1d, 1w, 1m, all)
- [x] [ADMIN][P2] Email activity metrics: show open rate, click rate, failed rate by email type over period
- [x] [ADMIN][P2] Extended KPIs: add meeting tracking (created, completed, failed, deleted)
- [x] [ADMIN][P2] Extended KPIs: add deleted count to action stats
- [x] [ADMIN][P2] Extended KPIs: track deleted count for projects
- [x] [ADMIN][P3] Embeddings graph improvements: make filterable by category, add clustering analysis with cluster labels

### Production Bugs [BUG]

- [x] [BUG][P1] Fix admin rate limiting: 429 errors on costs, metrics, ops, landing page analytics, email-stats, research-cache endpoints
- [x] [BUG][P1] Fix admin analytics page 502 bad gateway error
- [x] [BUG][P2] Verify admin impersonation feature is accessible and working (reported as unavailable)

### Test Stability [TEST]

- [x] [TEST][P3] Fix flaky test_trend_analyzer.py::test_invalid_url_returns_error - event loop cleanup race condition (passes individually, fails in suite)

### Deferred / Future [FUTURE]

- [ ] [FUTURE][P4] Peer benchmarking: compare user metrics against similar businesses without exposing specific business data

---

## Completed Summary (1000+ tasks)

### Core Platform

- **Data Analysis Platform**: Ingestion (DO Spaces, CSV, Google Sheets), Profiling, Query Engine, Meeting Integration, Dataset Q&A, UI
- **Meetings & Sessions**: Multi-agent deliberation, SSE streaming, export/sharing, error handling, cap enforcement, wall-clock timeout, retry/resume from checkpoint
- **Actions System**: Kanban, Gantt, reminders, bidirectional status, close/replan, calendar sync, post-mortems (lessons learned capture), blocker analyzer, blocker escalation to meeting
- **Projects**: CRUD, Gantt, auto-generation from actions/context, versioning, workspace constraints, meeting templates
- **Mentor Mode**: Expert personas, proactive patterns, improvement plans, @ mentions (meetings, actions, projects, chats), chat persistence, auto-labeling, post-mortem insights context

### Business Features

- **Billing**: Stripe integration, tier middleware, beta caps, cost tracking (variable + fixed), per-user metrics
- **Workspaces**: Schema, authorization, invitations, auto-creation, switching
- **Promotions**: Schema, services, admin UI, Stripe integration
- **Context System**: Insights, staleness tracking, benchmarks, north star goal (with history tracking, staleness prompts, goal evolution timeline), competitor detection (manual + auto-detect with rate limiting), managed competitors, competitor insight cards, trend analysis, market trend forecasts (AI-generated 3m/12m/24m industry insights with tier-gating)

### Admin & Ops

- **Admin Dashboard**: Sessions, costs, KPIs, kill history, alerts, users, waitlist, promotions, impersonation, blog management, template management, email activity metrics (open/click/failed rates via Resend webhooks), research cache metrics with threshold recommendations, A/B experiments dashboard (persona count experiment)
- **AI Ops**: Error detection, auto-remediation, self-monitoring
- **Observability**: Prometheus metrics (circuit breakers, Redis pool, event persistence, cost tracking, health history), Grafana dashboards (overview, cache performance), Loki logging, graph node instrumentation
- **Monitoring**: Health checks (Redis, Postgres, Anthropic, Voyage, Brave, ClamAV), pool exhaustion alerts, LLM provider health probes

### Security & Compliance

- **Security**: Rate limiting (global IP, SSE, dataset, admin), prompt injection detection, SQL validation, metrics auth, input sanitization (LLM outputs, user interjections, business context)
- **GDPR**: Data export, deletion/anonymization, audit logging, retention, consent capture, T&C versioning (terms_versions/terms_consents tables, consent modal, callback flow integration)
- **Supply Chain**: Pinned versions, OSV-Scanner, pip-audit blocking, Trivy container scanning, Dependabot
- **Web Security**: Nonce-based CSP, CSRF protection, HSTS, WAF rules, ClamAV file scanning

### Architecture & Performance

- **Architecture**: Parallel initial round (60-70% latency reduction), SSE state transitions, PostgreSQL polling fallback, circuit breaker fallback between LLM providers
- **Performance**: Session metadata cache, aggregation caching, contribution pruning, covering indexes, pg_stat_statements, pool size tuning (75 connections), embedding batch size increase
- **Data Model**: Pydantic models for Action/Project/Workspace, OpenAPI type generation, schema audit scripts, enum CHECK constraints

### Quality & Testing

- **E2E Tests**: Dashboard, settings, meeting-create, meeting-complete, actions, datasets, admin (all passing)
- **Security Tests**: Auth, authz, input validation, prompt injection (132 test cases), rate limiting, SQL injection
- **Architecture Audit**: State refactor, router consolidation, serialization cleanup, roundtrip validation
- **Chaos Tests**: Provider fallback, SSE Redis fallback, circuit breaker behavior

### UX & Frontend

- **Navigation**: Grouped sidebar, dropdowns, loading skeletons
- **Toast System**: Success/error/info/warning with auto-dismiss
- **Accessibility**: Skip links, ARIA labels, focus traps, landmarks
- **Onboarding**: driver.js tour (dashboard, actions, projects), relationship diagram
- **shadcn Migration**: Button, Input, Badge, Alert, Card
- **Dashboard**: Goal banner, weekly plan view, daily activities, goal progress API
- **Meeting UX**: Raise hand feature, partial success display, mobile clarification scroll

### LLM Alignment

- **Cost Reduction**: Lean synthesis template (30-60% reduction), Haiku extended to round 3 (A/B tested), reduced persona context
- **Output Validation**: Challenge phase validation, strict XML parsing, output length warnings, rate limiting
- **Sanitization**: All LLM call sites sanitized (user input, research results, business context, interjections)

### API Contract

- **Standardization**: Structured error responses with error codes, SSE schema versioning, pagination helpers
- **Documentation**: OpenAPI security schemes, rate limit responses, max_length constraints, filtered public spec
- **Dependencies**: Granular session verification (admin, metadata-only variants)

### Reliability

- **Resilience**: Session retry from checkpoint, replanning rollback, statement timeouts, deadlock retry
- **Observability**: Request ID propagation, reconnect tracking, Retry-After headers
- **Alerts**: Circuit breaker, event persistence backlog, cost anomalies (ntfy integration)

### Infrastructure

- **Deployment**: GitHub Actions CI, PostgreSQL backups, Redis persistence, blue-green deployment
- **Email**: Resend integration, templates (welcome, meeting, action reminder, weekly digest, failure notification)
- **Analytics**: Umami self-hosted integration, UptimeRobot monitoring
- **Integrations**: Google Calendar OAuth + action sync

### Documentation

- Help center (16 articles, 6 categories), privacy policy, terms of service, runbooks, SSE events documentation, datetime handling guide

---

_For detailed implementation notes on completed tasks, see git history._
