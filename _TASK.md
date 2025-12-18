# Task Backlog

_Last updated: 2025-12-18 (Task backlog complete - remaining items require user action)_

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

- [x] [SECURITY][P1] Fix Redis healthcheck to avoid password exposure (use REDISCLI_AUTH env var instead of `-a` flag)
- [x] [SECURITY][P2] Add rate limiting to CSRF-exempt `/api/v1/waitlist` endpoint
- [x] [SECURITY][P2] CSRF token rotation on auth state change (regenerate in SuperTokens sign-in callback)
- [x] [SECURITY][P3] Honeypot detection for prompt injection (hidden fields for automated attack detection)
- [x] [SECURITY][P3] Audit log alerting for admin impersonation usage

### QA Automation [QA]

- [x] [QA][P1] Playwright sweep: test ALL admin page links and buttons, write findings report
- [x] [QA][P1] Playwright sweep: test meeting creation and completion flow, write findings report

### Admin Features [ADMIN]

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

- [x] [BUG][P2] Fix UptimeRobot 404 when clicking through from admin system status
- [x] [BUG][P1] Fix `/api/v1/sessions/recent-failures` 404 on dashboard
- [x] [BUG][P1] Fix action status PATCH 422 errors (drag-drop and "start" button)
- [x] [BUG][P2] Fix `/api/v1/projects/unassigned-count` 500 error on projects tab
- [x] [BUG][P2] Fix admin API rate limiting (429s hitting most admin endpoints)
- [x] [BUG][P2] Fix admin sessions page 404 (`/admin/sessions`)
- [x] [BUG][P3] Fix admin error reporting POST 403 (`/api/errors`)

### UX Improvements [UX]

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

_For detailed implementation notes on completed tasks, see git history._
