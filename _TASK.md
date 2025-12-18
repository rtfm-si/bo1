# Task Backlog

_Last updated: 2025-12-18_

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
- [ ] [SEO][P3] Clarify scope of "auto seo" feature (ambiguous)
- [ ] [MONITORING] Clarify "grafana logs: value A" (ambiguous)

---

## Incomplete Tasks

### Security [SECURITY]

- [x] [SECURITY][P1] Fix Redis healthcheck to avoid password exposure (use REDISCLI_AUTH env var instead of `-a` flag)
- [x] [SECURITY][P2] Add rate limiting to CSRF-exempt `/api/v1/waitlist` endpoint
- [x] [SECURITY][P2] CSRF token rotation on auth state change (regenerate in SuperTokens sign-in callback)
- [ ] [SECURITY][P3] Honeypot detection for prompt injection (hidden fields for automated attack detection)
- [ ] [SECURITY][P3] Audit log alerting for admin impersonation usage

### QA Automation [QA]

- [x] [QA][P1] Playwright sweep: test ALL admin page links and buttons, write findings report
- [x] [QA][P1] Playwright sweep: test meeting creation and completion flow, write findings report

### Admin Features [ADMIN]

- [x] [ADMIN][P2] Admin UI toggle for `PROMPT_INJECTION_BLOCK_SUSPICIOUS` (emergency disable - LLM shutdown)
- [ ] [ADMIN][P3] Send branded email (from template) to end user from within admin
- [ ] [ADMIN][P3] Expose other emergency-disable config toggles in admin UI

### LLM Alignment [LLM]

- [x] [LLM][P2] Output format validation with re-prompt on XML parsing failure (standardize across nodes)
- [ ] [LLM][P3] Document sanitization requirements per prompt template; add injection vector tests

### API Contract [API]

- [x] [API][P2] Define and enforce structured error response schema (replace ad-hoc HTTPException)
- [x] [API][P2] Document SSE event schemas - created `frontend/src/lib/api/sse-events.ts` with 40+ typed event definitions
- [ ] [API][P3] Add `response_model` to endpoints returning raw dicts
- [ ] [API][P3] Define API versioning strategy for breaking changes

### Data Model [DATA]

- [x] [DATA][P2] Automated schema validation tests (Pydantic models vs migration schema)
- [x] [DATA][P2] Remove `[key: string]: any` escape hatch from `SessionDetailResponse.state` in frontend types
- [x] [DATA][P3] Update CLAUDE.md to replace `state_to_v1/v1_to_state` references with actual function names
- [ ] [DATA][P3] Consider auto-generating frontend TypeScript types from Pydantic models
- [x] [DATA][P3] Fix SSE event type narrowing in meeting components (69 strict type errors exposed by new SSEEventMap)

### Observability [OBS]

- [x] [OBS][P2] Standardize error logging format with error codes for easier aggregation
- [ ] [OBS][P3] Log level tuning per environment (reduce noise in production)

### Reliability [REL]

- [x] [REL][P2] Extend circuit breaker pattern to database and Redis calls (currently LLM-only)
- [x] [REL][P2] Ensure all retry callsites use `total_timeout` parameter consistently
- [ ] [REL][P3] Wire chaos tests (`tests/chaos/`) into CI for automated resilience verification
- [ ] [REL][P3] SSE event sequence detection for reconnection gaps

### Cost Optimization [COST]

- [x] [COST][P2] Centralize model selection config for easier A/B testing of cheaper models
- [x] [COST][P2] Add `cache_control` markers to prompt builds that don't currently use them
- [ ] [COST][P3] Expose research cache hit rate metrics to admin dashboard
- [ ] [COST][P3] Use full SHA-256 hash for LLM cache keys (currently first 16 chars)

### Infrastructure [INFRA]

- [ ] [INFRA][P3] Evaluate WAF (Web Application Firewall) for additional protection
- [ ] [INFRA][P3] SIEM integration for centralized threat detection
- [ ] [INFRA][P3] Automated dependency vulnerability scanning in CI (beyond pip-audit)
- [x] [DEPLOY][P1] Setup uptime monitoring (UptimeRobot) - create monitors for boardof.one, /health
- [x] [LAUNCH][P1] Verify Alertmanager running in prod, set NTFY_TOPIC env var

### Branding & SEO [BRAND/SEO]

- [x] [BRAND][P2] Update company attribution to "Sico Software Ltd" (footer, legal pages, about)
- [x] [SEO][P2] Configure robots.txt and meta tags for AI tool discovery (ChatGPT, Claude, etc.)
- [ ] [SEO][P3] Auto-SEO content pages: AI-generated topic pages with admin approval workflow

### Landing Page [LANDING]

- [ ] [LANDING][P3] Remove or verify social links (bottom right of landing page)

### Auth [AUTH]

- [ ] [AUTH][P3] Setup additional social login providers (LinkedIn, Bluesky, Twitter/X)

### Documentation [DOCS]

- [ ] [DOCS][P3] Help pages need content review and polish (Si's todo)

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

_For detailed implementation notes on completed tasks, see git history._
