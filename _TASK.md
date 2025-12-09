## Product backlog (from \_TODO.md, 2025-12-09)

### P1  Data Analysis Platform [P1-DATA]

#### EPIC 1: Data Ingestion

- [ ] [DATA][P1] Implement DO Spaces storage wrapper (boto3 S3-compatible client)
- [ ] [DATA][P1] Add `DO_SPACES_*` env vars to config
- [ ] [DATA][P1] Add retry logic and error handling to Spaces client
- [ ] [DATA][P1] Create datasets/dataset_profiles/dataset_analyses/dataset_insights migration
- [ ] [DATA][P1] Implement CSV upload endpoint with size/header validation
- [ ] [DATA][P1] Implement Google Sheets integration (OAuth flow + import)
- [ ] [DATA][P1] Implement dataset list/delete endpoints

#### EPIC 2: Profiling & Summary

- [ ] [DATA][P1] Implement DataFrame loading (CSV from Spaces, Sheets via API)
- [ ] [DATA][P1] Implement type inference (dates, currencies, percentages)
- [ ] [DATA][P1] Compute per-column statistics (null_count, unique_count, min/max/mean)
- [ ] [DATA][P1] Implement LLM summary generation for dataset profiles
- [ ] [DATA][P1] Create `data_profile_dataset` Claude tool with Redis caching

#### EPIC 3: Query & Analysis

- [ ] [DATA][P1] Implement QuerySpec model (aggregate/filter/trend/compare/correlate)
- [ ] [DATA][P1] Implement QueryEngine filter/group/aggregate operations
- [ ] [DATA][P1] Add DuckDB backend for large datasets (>100K rows - do we need duckdb? we already have postgres, would sqllite be better?)
- [ ] [DATA][P1] Implement result pagination
- [ ] [DATA][P1] Implement ChartGenerator (line/bar/pie/scatter/heat with matplotlib/plotly)
- [ ] [DATA][P1] Upload charts to Spaces and store metadata
- [ ] [DATA][P1] Create `data_run_query` Claude tool
- [ ] [DATA][P1] Create `data_generate_chart` Claude tool

#### EPIC 4: Insight Storage

- [ ] [DATA][P1] Create `analysis_store_run` tool (persist analysis runs)
- [ ] [DATA][P1] Create `analysis_store_insight` tool (extract reusable insights)
- [ ] [DATA][P1] Create `analysis_get_recent_context` tool (context retrieval)
- [ ] [DATA][P1] Implement Redis-backed session state helpers

#### EPIC 5: Orchestration

- [ ] [DATA][P1] Create data analyst system prompt (orchestrator prompt)
- [ ] [DATA][P1] Test multi-step analysis flows
- [ ] [DATA][P1] Implement `/v1/datasets/{dataset_id}/ask` endpoint with SSE streaming
- [ ] [DATA][P1] Inject attached dataset insights into meeting context

#### EPIC 6: UI

- [ ] [DATA][P1] Implement dataset list page with drag-drop CSV upload
- [ ] [DATA][P1] Implement Google Sheets URL input on dataset list page
- [ ] [DATA][P1] Implement dataset detail page with profile summary
- [ ] [DATA][P1] Implement "Ask a question" chat interface on dataset detail
- [ ] [DATA][P1] Show analysis history and chart gallery on dataset detail
- [ ] [DATA][P1] Add dataset attachment selector to meeting creation

### P1  Stripe Integration [P1-STRIPE]

- [ ] [BILLING][P1] Create Stripe account and configure products/prices (Free/Starter/Pro)
- [ ] [BILLING][P1] Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` to env
- [ ] [BILLING][P1] Install `stripe` package
- [ ] [BILLING][P1] Implement Stripe webhook handler endpoint
- [ ] [BILLING][P1] Handle key webhook events (checkout.session.completed, subscription.updated/deleted, invoice.payment_failed)
- [ ] [BILLING][P1] Add idempotency checks to webhook handler
- [ ] [BILLING][P1] Implement checkout session creation endpoint
- [ ] [BILLING][P1] Handle checkout success/cancel redirects
- [ ] [BILLING][P1] Implement billing portal session creation
- [ ] [BILLING][P1] Store stripe_customer_id in users table
- [ ] [BILLING][P1] Implement tier checking middleware
- [ ] [BILLING][P1] Add meeting limit checks to session creation
- [ ] [BILLING][P1] Add graceful upgrade prompts on limit reached
- [ ] [BILLING][P1] Add Checkout button integration to billing settings
- [ ] [BILLING][P1] Fix Portal button stub in billing settings
- [ ] [BILLING][P1] Show upgrade prompts when near usage limit

### P1  Critical UX Fixes [P1-UI]

#### Dashboard Overhaul

- [ ] [UX][P1] Add "Actions needing attention" section (overdue, due today)
- [ ] [UX][P1] Add progress visualization (completion trends)
- [ ] [UX][P1] Add quick actions panel (new meeting, view actions)
- [ ] [UX][P1] Add new user onboarding checklist

#### Navigation Improvements

- [ ] [UX][P1] Group related sidebar items (Decisions, Actions, Data)
- [ ] [UX][P1] Add "� Back to meeting" from action detail
- [ ] [UX][P1] Add loading skeletons for async content

#### Actions Page Polish

- [ ] [UX][P1] Add filter by status, due date, meeting to actions page
- [ ] [UX][P1] Add bulk actions (mark multiple complete)
- [ ] [UX][P1] Add due date warnings (overdue = red, due soon = amber)

### P1  Email Notifications [P1-EMAIL]

- [ ] [EMAIL][P1] Choose email provider and configure domain (SPF, DKIM)
- [ ] [EMAIL][P1] Add `EMAIL_*` env vars to config
- [ ] [EMAIL][P1] Implement email sender service (Resend or similar)
- [ ] [EMAIL][P1] Create welcome email template (on signup)
- [ ] [EMAIL][P1] Create meeting completed email template (summary + actions)
- [ ] [EMAIL][P1] Create action due reminder template (24h before)
- [ ] [EMAIL][P1] Create weekly digest template (actions summary)

### P2  Polish & Growth

#### Performance Phase 2 [P2-PERF]

- [ ] [PERF][P2] Implement event batching (buffer 50ms windows, batch Postgres inserts)
- [ ] [PERF][P2] Implement priority queuing (critical events before status events)
- [ ] [PERF][P2] Optimize stream writer for per-expert events during sub-problem rounds

#### Clarification Toggle [P2-SKIP]

- [ ] [UX][P2] Add user preference "Skip pre-meeting questions by default"
- [ ] [UX][P2] Store skip preference in users table or preferences JSONB
- [ ] [UX][P2] Apply skip preference during meeting creation

#### Mentor Mode [P2-MENTOR]

- [ ] [MENTOR][P2] Implement mentor chat endpoint with SSE streaming
- [ ] [MENTOR][P2] Build context injection (business context, meetings, datasets, actions)
- [ ] [MENTOR][P2] Store mentor chat history (Redis � Postgres)
- [ ] [MENTOR][P2] Implement mentor persona selection
- [ ] [MENTOR][P2] Auto-select mentor persona based on question topic
- [ ] [MENTOR][P2] Implement mentor chat UI page
- [ ] [MENTOR][P2] Add persona picker to mentor UI
- [ ] [MENTOR][P2] Show context sources panel in mentor UI

#### Action System Polish [P2-ACTIONS]

- [ ] [ACTIONS][P2] Add "What went wrong?" prompt when marking action failed
- [ ] [ACTIONS][P2] Suggest replanning via new meeting on action failure
- [ ] [ACTIONS][P2] Improve action dependency visualization

### P3  Enterprise & Scale

#### Workspaces & Teams [P3-TEAMS]

- [ ] [TEAMS][P3] Create workspaces/workspace_members database schema
- [ ] [TEAMS][P3] Add workspace FKs to meetings/datasets tables
- [ ] [TEAMS][P3] Implement workspace authorization layer
- [ ] [TEAMS][P3] Implement invitation system (email invite, accept/decline)
- [ ] [TEAMS][P3] Implement workspace switching UI
- [ ] [TEAMS][P3] Implement per-workspace billing

#### Projects System [P3-PROJECTS]

- [ ] [PROJECTS][P3] Implement projects CRUD
- [ ] [PROJECTS][P3] Assign meetings/actions to projects
- [ ] [PROJECTS][P3] Add filter views by project
- [ ] [PROJECTS][P3] Add Gantt chart per project

#### Advanced Tier Features [P3-TIERS]

- [ ] [TIERS][P3] Implement feature flags per tier (datasets, mentor, API access)
- [ ] [TIERS][P3] Add usage tracking (meetings, analyses, API calls)
- [ ] [TIERS][P3] Add admin override capability
- [ ] [TIERS][P3] Create pricing page with comparison table

#### Admin Improvements [P3-ADMIN]

- [ ] [ADMIN][P3] Implement admin impersonation ("view as user")
- [ ] [ADMIN][P3] Add in-app feature request form
- [ ] [ADMIN][P3] Add in-app problem reporting (auto-attach context)

#### AI Content Engine [P3-SEO]

- [ ] [SEO][P3] Implement content generation pipeline (trending topics � Claude � blog)
- [ ] [SEO][P3] Implement social posting (LinkedIn, Twitter)
- [ ] [SEO][P3] Add performance tracking and iteration

#### AI Ops Self-Healing [P3-OPS]

- [ ] [OPS][P3] Implement error pattern detection
- [ ] [OPS][P3] Create known error → known fix mapping
- [ ] [OPS][P3] Implement automated recovery procedures
- [ ] [OPS][P3] Create self-monitoring dashboard

---

## Task backlog (from \_TODO.md, 2025-12-09)

### GDPR User Rights [GDPR]

- [ ] [GDPR][P1] Implement GET /api/v1/user/export endpoint (Art. 15 data export)
- [ ] [GDPR][P1] Implement DELETE /api/v1/user/delete endpoint with anonymization (Art. 17)
- [ ] [GDPR][P1] Create audit logging for data export/deletion requests
- [ ] [GDPR][P1] Clarify data retention policy duration (365 days vs compliance needs)
- [ ] [GDPR][P1] Implement user-configurable retention period setting
- [ ] [GDPR][P1] Implement scheduled cleanup job for expired sessions
- [ ] [GDPR][P1] Add rate limiting to export endpoint (1 request per 24h)

### Promotions System [PROMO]

- [ ] [PROMO][P2] Create promotions and user_promotions database migration
- [ ] [PROMO][P2] Create Pydantic models for Promotion, UserPromotion, AddPromotionRequest
- [ ] [PROMO][P2] Seed common promotion templates (goodwill, discounts)
- [ ] [PROMO][P2] Implement check_deliberation_allowance() service
- [ ] [PROMO][P2] Implement consume_promo_deliberation() service
- [ ] [PROMO][P2] Implement apply_promotions_to_invoice() service
- [ ] [PROMO][P2] Implement daily promo expiry background job
- [ ] [PROMO][P2] Create admin promotions API endpoints (GET/POST/DELETE)
- [ ] [PROMO][P2] Create user promo code apply endpoint
- [ ] [PROMO][P2] Integrate promotions with deliberation flow (start/complete)
- [ ] [PROMO][P2] Integrate promotions with Stripe invoice creation
- [ ] [PROMO][P2] Create admin promotions management page (Svelte)
- [ ] [PROMO][P2] Create AddPromotionModal component
- [ ] [PROMO][P2] Create PromotionCard component
- [ ] [PROMO][P2] Write promotions E2E tests

### Stripe Integration (Checkout & Webhooks) [STRIPE-EXT]

- [ ] [STRIPE][P1] Implement Stripe webhook signature validation
- [ ] [STRIPE][P1] Handle invoice.payment_failed webhook
- [ ] [STRIPE][P1] Implement replay attack prevention (reject old timestamps)
- [ ] [STRIPE][P1] Implement webhook idempotency
- [ ] [STRIPE][P1] Create billing/success page
- [ ] [STRIPE][P1] Create billing/cancel page
- [ ] [STRIPE][P1] Implement Stripe Customer Portal endpoint

### Email Integration (Resend) [EMAIL-EXT]

- [ ] [EMAIL][P1] Create Resend account and configure domain (SPF, DKIM)
- [ ] [EMAIL][P1] Create backend/services/email.py service
- [ ] [EMAIL][P1] Create backend/services/email_templates.py
- [ ] [EMAIL][P1] Implement welcome email trigger on signup
- [ ] [EMAIL][P1] Implement payment receipt email trigger on Stripe webhook
- [ ] [EMAIL][P1] Add unsubscribe link to all emails
- [ ] [EMAIL][P1] Create email preferences page
- [ ] [EMAIL][P1] Test email deliverability across clients

### Production Monitoring [MONITORING]

- [ ] [MONITORING][P1] Create backend/services/monitoring.py for runaway session detection
- [ ] [MONITORING][P1] Create admin session kill endpoint
- [ ] [MONITORING][P1] Implement ntfy.sh alert integration
- [ ] [MONITORING][P1] Create backend/services/analytics.py for cost aggregation
- [ ] [MONITORING][P1] Create admin cost analytics endpoints
- [ ] [MONITORING][P1] Create admin CLI cost report script
- [ ] [MONITORING][P1] Implement per-tier rate limiting middleware
- [ ] [MONITORING][P1] Implement advanced health checks (readiness/liveness probes)
- [ ] [MONITORING][P1] Implement graceful shutdown handler
- [ ] [MONITORING][P1] Create Kubernetes deployment manifest
- [ ] [MONITORING][P1] Implement vendor outage detection and degraded mode
- [ ] [MONITORING][P1] Implement per-user cost tracking and budget thresholds
- [ ] [MONITORING][P1] Create feature flag service
- [ ] [MONITORING][P1] Define SLIs/SLOs and create Grafana SLO dashboard
- [ ] [MONITORING][P1] Instrument FastAPI with Prometheus metrics
- [ ] [MONITORING][P1] Create Grafana dashboards (API, deliberation, cost, infrastructure)
- [ ] [MONITORING][P1] Configure Prometheus alerting rules
- [ ] [MONITORING][P1] Configure structured JSON logging with context fields
- [ ] [MONITORING][P1] Setup Grafana Loki for log aggregation
- [ ] [MONITORING][P1] Implement audit logging middleware
- [ ] [MONITORING][P1] Add security headers middleware

### Admin Dashboard [ADMIN-UI]

- [ ] [ADMIN][P2] Create admin route layout and auth middleware
- [ ] [ADMIN][P2] Create admin API client
- [ ] [ADMIN][P2] Create active sessions page with live updates
- [ ] [ADMIN][P2] Create session details modal
- [ ] [ADMIN][P2] Create cost analytics page with charts
- [ ] [ADMIN][P2] Implement CSV export for cost data
- [ ] [ADMIN][P2] Add kill session button with confirmation
- [ ] [ADMIN][P2] Add kill-all-sessions emergency button
- [ ] [ADMIN][P2] Create kill history audit trail display
- [ ] [ADMIN][P2] Create alert settings page (ntfy.sh thresholds)
- [ ] [ADMIN][P2] Create alert history page

### QA & Security [QA]

- [ ] [QA][P1] Create load test scenarios (normal, peak, sustained) with Locust
- [ ] [QA][P1] Perform auth security audit (session, OAuth, rate limiting)
- [ ] [QA][P1] Perform auth penetration testing (session fixation, CSRF, brute force)
- [ ] [QA][P1] Perform infrastructure security audit (network, secrets, logging)
- [ ] [QA][P1] Scan Python and npm dependencies for vulnerabilities
- [ ] [QA][P1] Perform GDPR compliance audit
- [ ] [QA][P1] Create E2E tests for critical user flows (Playwright)
- [ ] [QA][P1] Perform OWASP Top 10 security testing

### Deployment & Infrastructure [DEPLOY]

- [ ] [DEPLOY][P1] Draft privacy policy (GDPR Art. 13-14)
- [ ] [DEPLOY][P1] Draft terms of service
- [ ] [DEPLOY][P1] Create privacy policy and terms of service pages
- [ ] [DEPLOY][P1] Sign DPAs with data processors (Supabase, Resend, Sentry)
- [ ] [DEPLOY][P1] Create GitHub Actions CI workflow (test.yml)
- [ ] [DEPLOY][P1] Create staging deployment workflow (deploy-staging.yml)
- [ ] [DEPLOY][P1] Create production deployment workflow (deploy-production.yml)
- [ ] [DEPLOY][P1] Configure GitHub secrets
- [ ] [DEPLOY][P1] Purchase domain and configure DNS
- [ ] [DEPLOY][P1] Setup SSL/TLS with Let's Encrypt
- [ ] [DEPLOY][P1] Enable PostgreSQL daily backups
- [ ] [DEPLOY][P1] Configure Redis persistence (AOF + RDB)
- [ ] [DEPLOY][P1] Create disaster recovery runbook
- [ ] [DEPLOY][P1] Setup uptime monitoring (UptimeRobot)
- [ ] [DEPLOY][P1] Create incident response playbook
- [ ] [DEPLOY][P1] Setup blue-green deployment environments
- [ ] [DEPLOY][P1] Document production deployment procedure

### User Documentation & Launch [LAUNCH]

- [ ] [LAUNCH][P1] Create help center page
- [ ] [LAUNCH][P1] Write user documentation (getting started, FAQs, tutorials)
- [ ] [LAUNCH][P1] Add search to help center
- [ ] [LAUNCH][P1] Deploy Prometheus and Grafana to production
- [ ] [LAUNCH][P1] Configure production Alertmanager
- [ ] [LAUNCH][P1] Switch Stripe to live mode
- [ ] [LAUNCH][P1] Create system shutdown procedure
- [ ] [LAUNCH][P1] Test emergency access procedures

---

## Task backlog (from \_TODO.md, 2025-12-09 update)

### Admin & Analytics [ADMIN-EXT]

- [ ] [ADMIN][P1] Extend admin pages with cost tracking and reporting views
- [ ] [ADMIN][P1] Implement onboarding pipeline analytics (funnel metrics)
- [ ] [ADMIN][P1] Implement app usage metrics dashboard (DAU, sessions, actions)
- [ ] [SECURITY][P1] Audit API to verify costs not exposed to non-admin users

### Governance Audits [AUDIT]

- [ ] [AUDIT][P1] Run governance audit: clean (code quality, lint, format)
- [ ] [AUDIT][P1] Run governance audit: secure (security scan)
- [ ] [AUDIT][P1] Run governance audit: full (comprehensive review)

### Social Login [AUTH]

- [ ] [AUTH][P2] Implement LinkedIn OAuth login
- [ ] [AUTH][P2] Implement GitHub OAuth login
- [ ] [AUTH][P2] Implement Bluesky login
- [ ] [AUTH][P2] Implement Twitter/X OAuth login

### Social Posting [SOCIAL]

- [ ] [SOCIAL][P3] Implement post-to-social feature (share meeting summaries)

### Mentor Chat Extensions [MENTOR-EXT]

- [ ] [MENTOR][P2] Add mentor mode: general business advice
- [ ] [MENTOR][P2] Add mentor mode: action-focused guidance
- [ ] [MENTOR][P2] Add mentor mode: metrics/data interpretation

### Dataset Q&A [DATA-EXT]

- [ ] [DATA][P1] Implement dataset Q&A flow ("which product range should I focus on given X,Y,Z?")

### Onboarding Flow [ONBOARDING]

- [ ] [ONBOARDING][P1] Implement new account → business context → first question flow
- [ ] [ONBOARDING][P1] Generate demo questions derived from business context

### Integrations [INTEGRATIONS]

- [ ] [INTEGRATIONS][P2] Implement Google Calendar integration for actions (sync due dates)
- [ ] [LLM][P1] Implement OpenAI fallback when Anthropic unavailable

### Backlog Review [META]

- [ ] [META][P1] Review MVP doc and add any incomplete tasks to \_TASK.md

---

## Bug fixes (from \_TODO.md, 2025-12-09)

### Working Status Timer [BUG-TIMER]

- [x] [BUG][P1] Fix working status timer estimates (shows "2-4 seconds" but takes 30s+) ✅ Removed misleading time estimates
- [x] [BUG][P1] Improve working status timer accuracy or remove time estimates ✅ Now shows elapsed time only

### Expert Contribution Quality [BUG-DELIB]

- [x] [BUG][P1] Reduce expert repetition across rounds (detect when topic fully explored) ✅ Novelty detection + semantic dedup working
- [ ] [BUG][P1] Enforce max 1 contribution per expert per round - STILL BROKEN (experts contribute 2x in round 1)
- [x] [BUG][P1] Add signal detection when nothing new to add (topic exhausted) ✅ Judge novelty_score + should_exit_early() implemented

### Productive Disagreement [BUG-DELIB]

- [ ] [BUG-DELIB][P1] Add "stalled disagreement" detection (conflict > 0.7 AND novelty < 0.40 for 2+ rounds)
- [ ] [BUG-DELIB][P1] Add Facilitator "Acknowledge Impasse" option to guide experts toward resolution
- [ ] [BUG-DELIB][P1] Guide experts to: find common ground, disagree-and-commit, or propose conditional recommendations
- [ ] [BUG-DELIB][P1] Trigger early synthesis when topic exhausted even without consensus (reduces cost, improves UX)

### Meeting Output [BUG-OUTPUT]

- [x] [BUG][P1] Add actions to PDF report export ✅ Added actions section to PDF generator with status/priority badges

### Context Persistence [BUG-CONTEXT]

- [x] [BUG][P1] Persist clarifying question answers to settings > context > insights/metrics ✅ Added clarifications column + CONTEXT_FIELDS entry

### Gantt Chart API [BUG-GANTT]

- [x] [BUG][P1] Fix Gantt API validation error (GanttDependency missing from/to/type fields) ✅ Fixed field names
- [ ] [BUG][P2] Gantt chart month view renders bars incorrectly (wrong positioning/sizing)

### Navigation & Routing [BUG-NAV]

- [ ] [BUG][P1] /meeting breadcrumb link returns 404 (no meetings list page exists)
- [ ] [BUG][P1] Clicking action in dashboard navigates to meeting instead of action detail page
