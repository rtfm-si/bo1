# Task Backlog

_Last updated: 2025-12-26_

---

## Incomplete Tasks

### Launch-Critical [P1]

- [ ] [LAUNCH][P3] Test emergency access procedures

### Billing & Configuration [P2]

- [ ] [BILLING][P1] Centralize plan configuration: consolidate all tier limits/allowances into single source of truth
- [ ] [BILLING][P1] Plan limits audit: ensure all features check centralized config for free/starter/pro access
- [ ] [BILLING][P4] Configure Stripe products/prices (Free/Starter/Pro)

### Security [P2]

- [ ] [SECURITY][P0] Rate limits audit: review all rate limits for sensibility and user impact

### Features [P2-P3]

- [ ] [UX][P2] Onboarding first-login flow: after onboarding cards, redirect to context overview with explanation
- [ ] [FEAT][P2] Strategic objective progress tracking: allow user to enter current state vs target with flexible input
- [ ] [FEAT][P1] SEO trend analyzer: button to analyze recent trends using Google Trends, Brave, Tavily
- [ ] [FEAT][P1] SEO topics table: store researched topics with "Research & Write Blog Post" action per row
- [ ] [FEAT][P1] SEO blog generator: generate SEO-optimized articles linking Bo1 to user problems
- [ ] [ADMIN][P2] SEO content analytics: track view rate, CTR, and signup rate for blog content

### Future Enhancements [P3-P4]

- [ ] [FUTURE][P3] Peer benchmarking: compare user metrics against similar businesses anonymously
- [ ] [RESEARCH][P4] Cross-user research sharing: leverage research from similar business contexts

### Content [P4]

- [ ] [DOCS][P2] Blog post: using Bo1 for Bo1 (dogfooding success story)
- [ ] [DOCS][P2] Blog post: Bo1 for solo founders, meeting prep, and SMBs
- [ ] [DOCS][P2] Blog post: Bo1 for product launches
- [ ] [DOCS][P2] Blog post: Bo1 for analytics use cases
- [ ] [DOCS][P2] Blog post: Bo1 for light-touch project management

### Blocked on Dependencies

- [ ] [EMAIL][P4] Payment receipt email trigger - blocked on Stripe integration
- [ ] [SOCIAL][P3] Direct posting to social accounts - blocked on user decision (see \_PLAN.md)
- [ ] [LAUNCH][P1] Switch Stripe to live mode (not yet live)

### Deferred by Design

- [ ] [DATA][P2] DuckDB backend for large datasets (>100K rows) - defer until needed
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have

### Needs Clarification

- [ ] [MONITORING][P1] Kubernetes deployment manifest - are we using kubernetes?
- [ ] [MONITORING] Clarify "grafana logs: value A" (ambiguous)
- [ ] [DATA][P2] Clarify data retention soft-delete behavior

### User-Owned

- [ ] [DOCS][P3] Help pages content review and polish (Si's todo)

---

## Completed Summary

### December 2025

- **UX audit fixes (2025-12-26)**: 4 issues from UX/UI comprehensive audit:
  - Context API 500 errors: Added defensive error handling for auto-detect and stale metrics
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
