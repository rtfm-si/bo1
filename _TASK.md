# Task Backlog

## Incomplete / Blocked / Deferred

### External/Manual Setup (User action required)

- [ ] [BILLING][P4] Configure Stripe products/prices (Free/Starter/Pro)
- [ ] [DEPLOY][P1] Sign DPAs with data processors (Supabase, Resend, Anthropic, DigitalOcean)
- [ ] [DEPLOY][P1] Setup SSL/TLS with Let's Encrypt
- [ ] [DEPLOY][P1] Setup uptime monitoring (UptimeRobot)
- [ ] [LAUNCH][P1] Configure production Alertmanager
- [ ] [LAUNCH][P1] Switch Stripe to live mode
- [ ] [LAUNCH][P1] Test emergency access procedures

### Blocked on Dependencies

- [ ] [EMAIL][P4] Payment receipt email trigger - blocked on Stripe integration
- [ ] [SOCIAL][P3] Direct posting to social accounts (Option A) - blocked on user decision (see _PLAN.md)

### Deferred by Design

- [ ] [DATA][P2] DuckDB backend for large datasets (>100K rows) - defer until needed
- [ ] [BILLING][P4] Upgrade prompts near usage limit - nice-to-have

### Needs Clarification

- [ ] [MONITORING][P1] Kubernetes deployment manifest - are we using kubernetes?

---

## Task backlog (from Security Audit, 2025-12-15)

### Security Testing [SECURITY]

- [ ] [SECURITY][P2] Add security integration tests per audit checklist (auth, authz, input validation)
- [ ] [SECURITY][P2] Add LLM security tests (prompt injection, jailbreak, data exfiltration patterns)
- [ ] [SECURITY][P2] Add rate limiting tests (session creation, global flood protection)

### Security Hardening [SECURITY]

- [ ] [SECURITY][P2] Add global IP-based rate limit alongside user limits (M6)
- [ ] [SECURITY][P2] Strengthen SQL validation regex patterns (EXEC, xp_cmdshell) (M4)
- [ ] [SECURITY][P3] Add network policy or auth to /metrics endpoint (L2)
- [ ] [SECURITY][P3] Change pip-audit continue-on-error to false in CI (L3)
- [ ] [SECURITY][P3] Audit all @html usages for proper DOMPurify sanitization (L1)

### Production Config [DEPLOY]

- [ ] [DEPLOY][P1] Document TRUSTED_PROXY_IPS configuration for production reverse proxy

---

## Task backlog (from \_TODO.md, 2025-12-14)

### API Performance [PERF]

- [ ] [PERF][P1] Investigate API container 30s startup time - profile and optimize

### Header Navigation UX [NAV]

- [ ] [UX][P2] Improve header nav spacing for laptop screens (currently squashed)
- [ ] [UX][P2] Remove 'New Meeting' button from header (redundant)
- [ ] [UX][P2] Remove workspace switcher from header (use settings instead)
- [ ] [UX][P2] Add Meetings link to Reports dropdown on dashboard

### Projects System [PROJECTS]

- [ ] [PROJECTS][P2] Auto-generate projects from actions (dedupe existing projects)
- [ ] [PROJECTS][P2] Prevent reopening closed projects - support project versioning (v2, v3, etc.)

### Context Insights Data Quality [CONTEXT]

- [ ] [DATA][P1] Filter null/empty insight responses before storing (allow "none"/"n/a" as valid)
- [ ] [DATA][P1] Parse meaningful context from responses instead of storing raw input
- [ ] [CONTEXT][P2] Implement periodic context refresh prompts for stale metrics
- [ ] [CONTEXT][P2] Refresh volatile/action-affected metrics more frequently than stable metrics

### App Stability [QA]

- [ ] [QA][P0] Audit broken buttons/actions across app (identify fragile operations)
- [ ] [QA][P1] Fix 51 E2E tests marked as fixme - see [frontend/e2e/FIXME_TESTS.md](frontend/e2e/FIXME_TESTS.md)
- [ ] [QA][P1] Increase overall app stability - remove fragile operations

### Admin Observability [ADMIN]

- [ ] [ADMIN][P3] Add embeddings visualization page (graphical embedding explorer)
- [ ] [ADMIN][P2] Add extended KPIs: mentor sessions, data analyses, projects, actions by status

### Proactive Mentoring [MENTOR]

- [ ] [MENTOR][P3] Detect repeated help requests on similar topics
- [ ] [MENTOR][P3] Detect persistent action failure patterns
- [ ] [MENTOR][P3] Proactively generate improvement plans for struggling users

### Accessibility & UI Modernization [UX]

- [ ] [UX][P3] Improve accessibility compliance
- [ ] [UX][P3] Modernize UI components using shadcn

### Onboarding Experience [ONBOARDING]

- [ ] [ONBOARDING][P2] Implement guided onboarding using driver.js
- [ ] [ONBOARDING][P2] Tour step: Business context setup
- [ ] [ONBOARDING][P2] Tour step: First meeting creation
- [ ] [ONBOARDING][P2] Tour step: Post-meeting kanban & gantt views
- [ ] [ONBOARDING][P2] Tour step: Projects overview

---

## Completed Summary (900+ tasks)

### P1 Data Analysis Platform ✅
- 6 epics complete: Ingestion (DO Spaces, CSV, Google Sheets), Profiling (type inference, statistics), Query Engine (filters, aggregates, charts), Meeting Integration (DataAnalysisAgent), Dataset Q&A (SSE streaming, multi-turn), UI (list, detail, chat, gallery)

### P4 Stripe Integration ✅
- Checkout flow, webhook handling (checkout.completed, subscription.*, invoice.payment_failed), idempotency, billing portal, tier middleware

### P1 Critical UX ✅
- Dashboard (actions needing attention, progress viz, quick actions, onboarding checklist)
- Navigation (grouped sidebar, dropdowns, loading skeletons)
- Actions page (filters, bulk actions, due warnings)

### P1 Email Notifications ✅
- Resend integration, welcome/meeting-completed/action-reminder/weekly-digest templates, unsubscribe handling

### P2 Polish & Growth ✅
- Event batching + priority queuing, clarification toggle preference, mentor mode (personas, context injection, UI), action cancellation/replanning/dependencies

### P3 Enterprise & Scale ✅
- Workspaces (schema, authorization, invitations, switching, per-workspace billing)
- Projects (CRUD, Gantt, meeting/action assignment)
- Tier features (flags, usage tracking, admin override, enforcement, UI)
- Admin (impersonation, feedback forms, problem reporting)
- AI Content Engine (blog generation, social sharing, performance tracking)
- AI Ops (error detection, auto-remediation, self-monitoring dashboard)

### GDPR ✅
- Data export (Art. 15), deletion/anonymization (Art. 17), audit logging, configurable retention (30-730 days), scheduled cleanup

### Promotions ✅
- Promo schema, repository, services (allowance/consume/apply), expiry job, admin UI, Stripe invoice integration

### Monitoring ✅
- Runaway session detection, admin kill endpoints, ntfy alerts, cost analytics, rate limiting, health probes, graceful shutdown, vendor outage detection, per-user cost tracking, feature flags, SLIs/SLOs, Prometheus metrics, Grafana dashboards, alerting rules, structured logging, Loki log aggregation, audit middleware, security headers

### Admin Dashboard ✅
- Sessions (live updates, detail modal, kill controls), cost analytics (charts, CSV export), kill history, alert settings/history, user metrics, onboarding funnel

### QA & Security ✅
- Load tests (Locust), auth audit, penetration testing, infra audit, dependency scanning, GDPR audit, E2E tests (Playwright), OWASP Top 10

### Deployment ✅
- Privacy policy, terms of service, GitHub Actions CI (test, staging, production), PostgreSQL backups, Redis persistence, disaster recovery runbook, incident response playbook, blue-green deployment, production deployment docs

### User Documentation ✅
- Help center (16 articles, 6 categories), search, system shutdown procedure

### Security Remediation ✅
- OAuth token encryption, account lockout, sanitized error messages, Redis rate limiter monitoring, localhost port binding, Redis auth, log scrubbing, encrypted backups, Promtail hardening, backup retention tiers

### GDPR Remediation ✅
- Consent capture, data export completeness, Redis cleanup on deletion, LLM processing notice, retention settings

### Supply-Chain Security ✅
- Pinned npm versions, OSV-Scanner in CI, transitive dependency review

### Web Security ✅
- Nonce-based CSP, CSP violation reporting, HSTS preload prep, CSRF protection, WAF rules

### Rate Limiting ✅
- SSE streaming limits, dataset upload limits, admin rate limits (300/min)

### Logging ✅
- PII sanitization, security event alerting, ntfy integration

### Bug Fixes (100+ items) ✅
- Timer estimates, expert repetition, disagreement detection, PDF exports, context persistence, Gantt API, navigation, meeting UI, sub-problem display, early termination, heatmap alignment, feedback modal, 429/500 errors, CORS/CSRF issues

### Session Export & Sharing ✅
- Export service (JSON/Markdown), share tokens/expiry, public view page, API + frontend complete

### Mentor Enhancements ✅
- All expert personas available, @ mentions for meetings/actions/datasets

### Insights System ✅
- Staleness tracking, PATCH endpoint, edit UI, GDPR export, staleness prompts, context display

### Context Features ✅
- Metric volatility classification, stale metric detection, action-metric correlation, auto-update with confidence thresholds, trend history

### Industry Benchmarking ✅
- 4 categories, 15+ metrics, tier-based limits, comparison endpoint, frontend UI

### Dashboard ✅
- Activity heatmap (12-month rolling, color by type, toggles), completion trends (meetings/mentor/tasks), value metrics panel

### Projects ✅
- Workspace constraints, M:N session-project links, auto-suggestions from meetings, autogeneration from actions/context, project meetings

### Social Sharing ✅
- Share buttons for heatmap/meeting summaries/action achievements, canvas export, intent-based sharing

### Action System ✅
- Reminders (start/deadline), configurable frequency, dashboard highlights, email notifications, progress tracking, variance analysis

### Architecture Audit ✅
- State mutation patterns verified, transactional contribution persistence, event versioning, idempotent cost tracking, clarification cleanup

### Performance ✅
- Composite indexes (session_events, action_tags, session_shares), cost insert batching, session capacity limits, N+1 query fixes, Redis user_id caching, adaptive embedding timeouts

### LLM Alignment ✅
- Input sanitization, XML validation with re-response, citation requirements, facilitator action whitelist, uncertainty fallbacks, adaptive temperature, confidence level enforcement

### Data Model ✅
- Schema-model drift fixed, deprecated columns removed, soft-delete standardized, updated_at timestamps added, JSONB validation

### Observability ✅
- Correlation ID propagation, mandatory context fields in logs, LLM latency histograms, metric cardinality controls, SLO alert thresholds, health checks for event queue/circuit breaker

### API Contract ✅
- Proper Pydantic models for all responses, error response documentation, public endpoint markers, auth pattern standardization, workspace access validation

### Reliability ✅
- Session state recovery, cost tracking retry queue, Redis reconnection + PostgreSQL fallback, SSE gap detection, cost limit kill switch, fault classification in circuit breaker, total timeout for retries, pool exhaustion degradation

### Cost Optimization ✅
- Prompt caching enabled, Haiku for synthesis/selector, early exit on convergence, embedding dedup, similarity threshold alignment, research cache TTL cleanup

### E2E Tests ✅
- Dashboard (15 tests), settings (17 tests), actions, datasets, meeting-complete - all blocking in CI

### Data Quality ✅
- Insight response validation, null/empty filtering, storage layer validation

### API Performance ✅
- Startup timing instrumentation, phase metrics (module init ~2.5s, lifespan <50ms)

---

*Last updated: 2025-12-14*
