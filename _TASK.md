## Product backlog (from \_TODO.md, 2025-12-09)

### P1  Data Analysis Platform [P1-DATA]

#### EPIC 1: Data Ingestion

- [x] [DATA][P1] Implement DO Spaces storage wrapper (boto3 S3-compatible client) ✅ backend/services/spaces.py
- [x] [DATA][P1] Add `DO_SPACES_*` env vars to config ✅ bo1/config.py
- [x] [DATA][P1] Add retry logic and error handling to Spaces client ✅ SpacesError + exponential backoff
- [x] [DATA][P1] Create datasets/dataset_profiles migration ✅ f1_create_datasets_tables.py
- [x] [DATA][P1] Implement CSV upload endpoint with size/header validation ✅ POST /api/v1/datasets/upload + csv_utils.py
- [x] [DATA][P1] Implement Google Sheets integration (OAuth flow + import) ✅ Public sheets via API key + Private sheets via OAuth (backend/services/sheets.py OAuthSheetsClient, POST /v1/auth/google/sheets/connect)
- [x] [DATA][P1] Implement dataset list/delete endpoints ✅ backend/api/datasets.py

#### EPIC 2: Profiling & Summary

- [x] [DATA][P1] Implement DataFrame loading (CSV from Spaces, Sheets via API) ✅ backend/services/dataframe_loader.py
- [x] [DATA][P1] Implement type inference (dates, currencies, percentages) ✅ backend/services/type_inference.py
- [x] [DATA][P1] Compute per-column statistics (null_count, unique_count, min/max/mean) ✅ backend/services/statistics.py + POST /api/v1/datasets/{id}/profile
- [x] [DATA][P1] Implement LLM summary generation for dataset profiles ✅ backend/services/summary_generator.py + Redis caching
- [x] [DATA][P1] Create dataset profile service with Redis caching ✅ bo1/tools/data_profile.py (NOTE: defined as Claude tool but not invoked - profiling triggered via REST endpoint)

#### EPIC 3: Query & Analysis

- [x] [DATA][P1] Implement QuerySpec model (aggregate/filter/trend/compare/correlate) ✅ backend/api/models.py (FilterSpec, AggregateSpec, GroupBySpec, TrendSpec, CompareSpec, CorrelateSpec, QuerySpec)
- [x] [DATA][P1] Implement QueryEngine filter/group/aggregate operations ✅ backend/services/query_engine.py + execute_query()
- [ ] [DATA][P2] Add DuckDB backend for large datasets (>100K rows) - defer until needed
- [x] [DATA][P1] Implement result pagination ✅ QuerySpec.limit/offset + QueryResult.has_more
- [x] [DATA][P1] Create query API endpoint ✅ POST /api/v1/datasets/{id}/query
- [x] [DATA][P1] Implement ChartGenerator service (line/bar/pie/scatter with plotly) ✅ backend/services/chart_generator.py
- [x] [DATA][P1] Create chart API endpoint ✅ POST /api/v1/datasets/{id}/chart
- [x] [DATA][P1] Upload charts to Spaces and store metadata ✅ g2_create_dataset_analyses.py + chart persistence in POST /chart

#### EPIC 4: Meeting Data Integration

- [x] [DATA][P1] Create DataAnalysisAgent (mirrors ResearcherAgent pattern) ✅ bo1/agents/data_analyst.py
- [x] [DATA][P1] Add Facilitator `analyze_data` action type ✅ FacilitatorAction Literal + VALID_FACILITATOR_ACTIONS
- [x] [DATA][P1] Implement DataAnalysisAgent.analyze_dataset() - calls query/chart endpoints ✅ Calls /api/v1/datasets/{id}/query and /chart
- [x] [DATA][P1] Implement DataAnalysisAgent.format_analysis_context() - formats results for LLM ✅ XML-formatted context
- [x] [DATA][P1] Inject dataset analysis into meeting context (like research results) ✅ data_analysis_node + graph routing

#### EPIC 5: Dataset Q&A (Standalone)

- [x] [DATA][P1] Create data analyst system prompt for Q&A flow ✅ bo1/prompts/data_analyst.py
- [x] [DATA][P1] Implement `/v1/datasets/{dataset_id}/ask` endpoint with SSE streaming ✅ backend/api/datasets.py
- [x] [DATA][P1] Implement multi-turn conversation state (Redis-backed) ✅ backend/services/conversation_repo.py
- [x] [DATA][P1] Test multi-step analysis flows ✅ tests/api/test_dataset_ask.py (18 tests)

#### EPIC 6: UI

- [x] [DATA][P1] Implement dataset list page with drag-drop CSV upload ✅ frontend/src/routes/(app)/datasets/+page.svelte
- [x] [DATA][P1] Implement Google Sheets URL input on dataset list page ✅ frontend/src/routes/(app)/datasets/+page.svelte
- [x] [DATA][P1] Implement dataset detail page with profile summary ✅ frontend/src/routes/(app)/datasets/[dataset_id]/+page.svelte
- [x] [DATA][P1] Implement "Ask a question" chat interface on dataset detail ✅ frontend/src/lib/components/dataset/DatasetChat.svelte
- [x] [DATA][P1] Show analysis history and chart gallery on dataset detail ✅ AnalysisGallery.svelte + GET /api/v1/datasets/{id}/analyses
- [x] [DATA][P1] Add dataset attachment selector to meeting creation ✅ g3_add_dataset_sessions.py + Svelte 5 selector + ownership validation

### P4 Stripe Integration [P4-STRIPE] ✅ PHASE 1 COMPLETE

- [ ] [BILLING][P4] Create Stripe account and configure products/prices (Free/Starter/Pro) - Manual setup required
- [x] [BILLING][P4] Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` to env ✅ bo1/config.py
- [x] [BILLING][P4] Install `stripe` package ✅ stripe==14.0.1
- [x] [BILLING][P4] Implement Stripe webhook handler endpoint ✅ POST /api/v1/billing/webhook
- [x] [BILLING][P4] Handle key webhook events (checkout.session.completed, subscription.updated/deleted, invoice.payment_failed) ✅ backend/api/billing.py
- [x] [BILLING][P4] Add idempotency checks to webhook handler ✅ stripe_events table + _is_event_processed()
- [x] [BILLING][P4] Implement checkout session creation endpoint ✅ POST /api/v1/billing/checkout
- [x] [BILLING][P4] Handle checkout success/cancel redirects ✅ /billing/success + /billing/cancel pages
- [x] [BILLING][P4] Implement billing portal session creation ✅ POST /api/v1/billing/portal
- [x] [BILLING][P4] Store stripe_customer_id in users table ✅ ao1_add_stripe_customer migration + user_repository methods
- [x] [BILLING][P4] Implement tier checking middleware ✅ Pre-existing in backend/api/middleware/tier_limits.py
- [x] [BILLING][P4] Add meeting limit checks to session creation ✅ Pre-existing in tier_limits.py check_meeting_limit()
- [x] [BILLING][P4] Add graceful upgrade prompts on limit reached ✅ Pre-existing tier_limits upgrade_url
- [x] [BILLING][P4] Add Checkout button integration to billing settings ✅ /settings/billing upgrade cards
- [x] [BILLING][P4] Fix Portal button stub in billing settings ✅ Stripe portal integration complete
- [ ] [BILLING][P4] Show upgrade prompts when near usage limit - Deferred (nice-to-have)

### P1  Critical UX Fixes [P1-UI]

#### Dashboard Overhaul

- [x] [UX][P1] Add "Actions needing attention" section (overdue, due today) ✅ Added to dashboard with overdue/due-today filtering
- [x] [UX][P1] Add progress visualization (completion trends) ✅ Added CompletionTrendsChart component with /api/v1/actions/stats endpoint
- [x] [UX][P1] Add quick actions panel (new meeting, view actions) ✅ Added 3-card quick actions grid to dashboard
- [x] [UX][P1] Add new user onboarding checklist ✅ OnboardingChecklist.svelte on dashboard with 3-step guide

#### Navigation Improvements

- [x] [UX][P1] Group related sidebar items (Decisions, Actions, Data) ✅ Header nav now uses NavDropdown with Work (Actions, Projects) and Data (Datasets) groups
- [x] [UX][P1] Improve UI for navigation items (Decisions, Actions, Data) - remove duplication and consolidate ✅ Removed breadcrumbs from top-level pages, grouped nav with dropdowns
- [x] [UX][P1] Add "Back to meeting" from action detail ✅ Added header link in action detail page
- [x] [UX][P1] Add loading skeletons for async content ✅ Extended ShimmerSkeleton with list-item/stat-card/chart variants, added to Dashboard/Actions pages

#### Actions Page Polish

- [x] [UX][P1] Add filter by status, due date, meeting to actions page ✅ Added status and due date dropdowns
- [x] [UX][P1] Add bulk actions (mark multiple complete) ✅ Added checkboxes, select all, bulk action bar with Mark Complete/Start/To Do
- [x] [UX][P1] Add due date warnings (overdue = red, due soon = amber) ✅ Added to dashboard, actions page, action detail

### P1 Email Notifications [P1-EMAIL] ✅ COMPLETE

- [x] [EMAIL][P1] Choose email provider and configure domain (SPF, DKIM) ✅ Resend configured
- [x] [EMAIL][P1] Add EMAIL env vars to config ✅ RESEND_API_KEY in config.py
- [x] [EMAIL][P1] Implement email sender service ✅ backend/services/email.py
- [x] [EMAIL][P1] Create welcome email template ✅ render_welcome_email() + supertokens hook
- [x] [EMAIL][P1] Create meeting completed email template ✅ render_meeting_completed_email()
- [x] [EMAIL][P1] Create action reminder template ✅ render_action_reminder_email()
- [x] [EMAIL][P1] Create weekly digest template ✅ render_weekly_digest_email()

### P2  Polish & Growth

#### Performance Phase 2 [P2-PERF]

- [x] [PERF][P2] Implement event batching (buffer 50ms windows, batch Postgres inserts) ✅ backend/services/event_batcher.py + integration
- [x] [PERF][P2] Implement priority queuing (critical events before status events) ✅ EventPriority enum + critical events flush immediately
- [x] [PERF][P2] Optimize stream writer for per-expert events during sub-problem rounds ✅ ExpertEventBuffer class + publish_event_buffered() method + event merging + profiling baseline tests

#### Clarification Toggle [P2-SKIP] ✅ COMPLETE

- [x] [UX][P2] Add user preference "Skip pre-meeting questions by default" ✅ GET/PATCH /api/v1/user/preferences
- [x] [UX][P2] Store skip preference in users table or preferences JSONB ✅ t1_add_skip_clarification.py migration
- [x] [UX][P2] Apply skip preference during meeting creation ✅ identify_gaps_node skips if preference set

#### Mentor Mode [P2-MENTOR] ✅ COMPLETE

- [x] [MENTOR][P2] Implement mentor chat endpoint with SSE streaming ✅ backend/api/mentor.py
- [x] [MENTOR][P2] Build context injection (business context, meetings, datasets, actions) ✅ backend/services/mentor_context.py
- [x] [MENTOR][P2] Store mentor chat history (Redis) ✅ backend/services/mentor_conversation_repo.py
- [x] [MENTOR][P2] Implement mentor persona selection ✅ backend/services/mentor_persona.py
- [x] [MENTOR][P2] Auto-select mentor persona based on question topic ✅ auto_select_persona() heuristic
- [x] [MENTOR][P2] Implement mentor chat UI page ✅ frontend/src/routes/(app)/mentor/+page.svelte
- [x] [MENTOR][P2] Add persona picker to mentor UI ✅ frontend/src/lib/components/mentor/PersonaPicker.svelte
- [x] [MENTOR][P2] Show context sources panel in mentor UI ✅ frontend/src/lib/components/mentor/ContextSourcesBadge.svelte

#### Action System Polish [P2-ACTIONS]

- [x] [ACTIONS][P2] Add "What went wrong?" prompt when marking action cancelled ✅ CancellationModal.svelte + cancellation_reason/cancelled_at columns + API validation
- [x] [ACTIONS][P2] Suggest replanning via new meeting on action failure ✅ x1_add_replanning_fields migration + failure_reason_category categorization + ReplanningSuggestionModal + action detail integration + replan context extraction + analytics logging
- [x] [ACTIONS][P2] Improve action dependency visualization ✅ DependencyGraph.svelte + API client methods + action detail integration

### P3  Enterprise & Scale

#### Workspaces & Teams [P3-TEAMS]

- [x] [TEAMS][P3] Create workspaces/workspace_members database schema ✅ aa1_create_workspaces migration + workspace_repository.py + Pydantic models
- [x] [TEAMS][P3] Add workspace FKs to meetings/datasets tables ✅ aa2_add_workspace_to_sessions + aa3_add_workspace_to_datasets migrations
- [x] [TEAMS][P3] Implement workspace authorization layer ✅ backend/services/workspace_auth.py (role-based permissions) + backend/api/middleware/workspace_auth.py (FastAPI dependencies) + backend/api/workspaces/routes.py (CRUD + member management) + 40 unit tests
- [x] [TEAMS][P3] Implement invitation system (email invite, accept/decline) ✅ ab1_create_workspace_invitations migration + invitation_repository.py + invitation_service.py + render_workspace_invitation_email() + API endpoints + frontend InvitationManager.svelte + /invite/[token] page + 18 tests
- [x] [TEAMS][P3] Implement workspace switching UI ✅ WorkspaceSwitcher.svelte + CreateWorkspaceModal.svelte + workspace store + Header integration + /settings/workspace page + API client methods
- [x] [TEAMS][P3] Implement per-workspace billing ✅ aq1_add_workspace_billing migration + workspace_repository billing methods + workspace_billing_service.py + API endpoints (billing info, checkout, portal) + webhook handlers for workspace customers + tier_limits workspace context + /settings/workspace/billing UI + 16 unit tests

#### Projects System [P3-PROJECTS]

- [x] [PROJECTS][P3] Implement projects CRUD ✅ backend/api/projects.py + project_repository.py (complete)
- [x] [PROJECTS][P3] Assign meetings/actions to projects ✅ POST/DELETE /api/v1/projects/{id}/actions/{action_id}
- [x] [PROJECTS][P3] Add filter views by project ✅ GET /api/v1/actions with ?project_id filter
- [x] [PROJECTS][P3] Add Gantt chart per project ✅ GET /api/v1/projects/{id}/gantt endpoint

#### Advanced Tier Features [P3-TIERS] ✅ PHASE 1 COMPLETE

- [x] [TIERS][P3] Implement feature flags per tier (datasets, mentor, API access) ✅ bo1/constants.py TierFeatureFlags + TierLimits
- [x] [TIERS][P3] Add usage tracking (meetings, analyses, API calls) ✅ backend/services/usage_tracking.py + Redis+Postgres hybrid + ag1_add_usage_tracking migration
- [x] [TIERS][P3] Add admin override capability ✅ tier_override JSONB column + GET/POST/DELETE /api/admin/users/{id}/tier-override
- [x] [TIERS][P3] Implement tier limit enforcement on endpoints ✅ backend/api/middleware/tier_limits.py + sessions/datasets/mentor integration
- [x] [TIERS][P3] Add usage API endpoints ✅ GET /api/v1/user/usage + GET /api/v1/user/tier-info
- [x] [TIERS][P3] Add frontend usage components ✅ UsageMeter.svelte + UsagePanel.svelte
- [x] [TIERS][P3] Create pricing page with comparison table ✅ /pricing page + PricingTable.svelte + pricing.ts data config + Header nav links + UsagePanel upgrade link + tier_limits upgrade_url

#### Admin Improvements [P3-ADMIN]

- [x] [ADMIN][P3] Implement admin impersonation ("view as user") ✅ ah1_add_admin_impersonation migration + backend/services/admin_impersonation.py + backend/api/admin/impersonation.py (POST/DELETE/GET) + ImpersonationMiddleware + auth dependency mod + ImpersonationBanner.svelte + admin users page modal + 18 tests
- [x] [ADMIN][P3] Add in-app feature request form ✅ FeedbackModal.svelte + POST /api/v1/feedback + admin review at /admin/feedback
- [x] [ADMIN][P3] Add in-app problem reporting (auto-attach context) ✅ FeedbackModal with context checkbox + tier/URL/browser auto-attach for problem reports

#### AI Content Engine [P3-SEO]

- [ ] [SEO][P3] Implement content generation pipeline (trending topics � Claude � blog)
- [ ] [SEO][P3] Implement social posting (LinkedIn, Twitter)
- [ ] [SEO][P3] Add performance tracking and iteration

#### AI Ops Self-Healing [P3-OPS] ✅ COMPLETE

- [x] [OPS][P3] Implement error pattern detection ✅ backend/services/error_detector.py + ErrorPattern dataclass + detect_patterns() + frequency tracking
- [x] [OPS][P3] Create known error → known fix mapping ✅ ar1_create_error_patterns + ar2_seed_error_patterns migrations + error_fixes table
- [x] [OPS][P3] Implement automated recovery procedures ✅ backend/services/auto_remediation.py (7 fix types: redis reconnect, db pool reset, circuit break, SSE reset, cache clear, session kill, alert only)
- [x] [OPS][P3] Create self-monitoring dashboard ✅ backend/api/admin/ops.py + frontend/src/routes/(app)/admin/ops/+page.svelte + 45 unit tests

---

## Task backlog (from \_TODO.md, 2025-12-09)

### GDPR User Rights [GDPR]

- [x] [GDPR][P1] Implement GET /api/v1/user/export endpoint (Art. 15 data export) ✅ backend/api/user.py
- [x] [GDPR][P1] Implement DELETE /api/v1/user/delete endpoint with anonymization (Art. 17) ✅ backend/api/user.py
- [x] [GDPR][P1] Create audit logging for data export/deletion requests ✅ backend/services/audit.py + l1_add_gdpr_audit_log.py
- [x] [GDPR][P2] Clarify data retention policy duration (365 days vs compliance needs) ✅ User-configurable 30-730 days
- [x] [GDPR][P2] Implement user-configurable retention period setting ✅ GET/PATCH /api/v1/user/retention + /settings/privacy UI + per-user cleanup
- [x] [GDPR][P1] Implement scheduled cleanup job for expired sessions ✅ backend/jobs/session_cleanup.py (now uses per-user retention)
- [x] [GDPR][P1] Add rate limiting to export endpoint (1 request per 24h) ✅ via audit.get_recent_export_request()

### Promotions System [PROMO]

- [x] [PROMO][P2] Create promotions and user_promotions database migration ✅ ai1_create_promotions.py
- [x] [PROMO][P2] Create Pydantic models for Promotion, UserPromotion, AddPromotionRequest ✅ backend/api/models.py
- [x] [PROMO][P2] Seed common promotion templates (goodwill, discounts) ✅ WELCOME10, GOODWILL5, LAUNCH2025
- [x] [PROMO][P2] Add promotion repository ✅ bo1/state/repositories/promotion_repository.py
- [x] [PROMO][P2] Implement check_deliberation_allowance() service ✅ backend/services/promotion_service.py
- [x] [PROMO][P2] Implement consume_promo_deliberation() service ✅ backend/services/promotion_service.py
- [x] [PROMO][P2] Implement apply_promotions_to_invoice() service ✅ backend/services/promotion_service.py
- [x] [PROMO][P2] Implement daily promo expiry background job ✅ backend/jobs/promotion_expiry.py
- [x] [PROMO][P2] Create admin promotions API endpoints (GET/POST/DELETE) ✅ backend/api/admin/promotions.py
- [x] [PROMO][P2] Create user promo code apply endpoint ✅ POST /api/v1/user/promo-code
- [x] [PROMO][P2] Integrate promotions with deliberation flow (start/complete) ✅ aj1_add_session_promo_tracking migration + MeetingLimitResult with promo fallback + session used_promo_credit flag + event_collector consume on completion + SessionResponse.promo_credits_remaining
- [x] [PROMO][P2] Integrate promotions with Stripe invoice creation ✅ ap1_add_promo_invoice_tracking migration + apply_promotions_to_stripe_invoice service + invoice.created webhook handler + create_invoice_item Stripe method + idempotency tracking + 18 unit tests
- [x] [PROMO][P2] Create admin promotions management page (Svelte) ✅ /admin/promotions page + admin API client methods
- [x] [PROMO][P2] Create AddPromotionModal component ✅ frontend/src/lib/components/admin/AddPromotionModal.svelte
- [x] [PROMO][P2] Create PromotionCard component ✅ frontend/src/lib/components/admin/PromotionCard.svelte
- [x] [PROMO][P2] Write promotions E2E tests ✅ frontend/e2e/admin-promotions.spec.ts (24 tests: list, filter tabs, create flow, delete flow, form validation, empty state, error handling)

### Stripe Integration (Checkout & Webhooks) [STRIPE-EXT] ✅ COMPLETE

- [x] [STRIPE][P4] Implement Stripe webhook signature validation ✅ stripe_service.construct_webhook_event()
- [x] [STRIPE][P4] Handle invoice.payment_failed webhook ✅ _handle_payment_failed() in billing.py
- [x] [STRIPE][P4] Implement replay attack prevention (reject old timestamps) ✅ _validate_webhook_timestamp() 5-minute tolerance
- [x] [STRIPE][P4] Implement webhook idempotency ✅ stripe_events table + _is_event_processed()/_record_event()
- [x] [STRIPE][P4] Create billing/success page ✅ /billing/success
- [x] [STRIPE][P4] Create billing/cancel page ✅ /billing/cancel
- [x] [STRIPE][P4] Implement Stripe Customer Portal endpoint ✅ POST /api/v1/billing/portal

### Email Integration (Resend) [EMAIL-EXT]

- [x] [EMAIL][P1] Create Resend account and configure domain (SPF, DKIM) ✅ Prod configured
- [x] [EMAIL][P1] Create backend/services/email.py service ✅ send_email(), send_email_async(), retries
- [x] [EMAIL][P1] Create backend/services/email_templates.py ✅ welcome, meeting_completed, action_reminder, weekly_digest
- [x] [EMAIL][P1] Implement welcome email trigger on signup ✅ supertokens_config.py hook
- [ ] [EMAIL][P4] Implement payment receipt email trigger on Stripe webhook - blocked on Stripe integration
- [x] [EMAIL][P1] Add unsubscribe link to all emails ✅ generate_unsubscribe_token() + /v1/email/unsubscribe endpoint
- [x] [EMAIL][P2] Create email preferences page (frontend) - API exists at GET/PATCH /v1/user/email-preferences ✅ /settings/privacy
- [x] [EMAIL][P2] Test email deliverability across clients ✅ backend/scripts/test_email_deliverability.py + Makefile targets (test-email-deliverability, test-email-template, list-email-templates) + 26 unit tests

### Production Monitoring [MONITORING]

- [x] [MONITORING][P1] Create backend/services/monitoring.py for runaway session detection ✅ detect_runaway_sessions() + RunawaySessionResult
- [x] [MONITORING][P1] Create admin session kill endpoint ✅ POST /api/admin/sessions/{id}/kill + POST /api/admin/sessions/kill-all (already existed)
- [x] [MONITORING][P1] Implement ntfy.sh alert integration ✅ backend/services/alerts.py with alert_runaway_session(), alert_session_killed()
- [x] [MONITORING][P1] Create session_kills audit table migration ✅ m1_add_session_kills.py
- [x] [MONITORING][P1] Create background monitoring job ✅ backend/jobs/session_monitoring.py (CLI + async)
- [x] [MONITORING][P1] Create backend/services/analytics.py for cost aggregation ✅ backend/services/analytics.py (CostSummary, UserCost, DailyCost, CostReport)
- [x] [MONITORING][P1] Create admin cost analytics endpoints ✅ GET /api/admin/analytics/costs, /costs/users, /costs/daily
- [x] [MONITORING][P1] Create admin CLI cost report script ✅ backend/scripts/cost_report.py (text/json/csv formats)
- [x] [MONITORING][P1] Implement per-tier rate limiting middleware ✅ backend/api/middleware/rate_limit.py (Redis-backed, per-tier limits via RateLimits constants)
- [x] [MONITORING][P1] Implement advanced health checks (readiness/liveness probes) ✅ /api/health (liveness), /api/ready (readiness with Postgres+Redis checks)
- [x] [MONITORING][P1] Implement graceful shutdown handler ✅ backend/api/main.py (SIGTERM/SIGINT handlers, in-flight request draining, 30s timeout)
- [ ] [MONITORING][P1] Create Kubernetes deployment manifest - are we using kubernetes?
- [x] [MONITORING][P1] Implement vendor outage detection and degraded mode ✅ vendor_health.py + service_monitor.py + ServiceStatusBanner.svelte + /api/v1/status + ntfy alerts
- [x] [MONITORING][P1] Implement per-user cost tracking and budget thresholds ✅ user_cost_tracking.py + admin endpoints + ntfy alerts + session block on exceed
- [x] [MONITORING][P1] Create feature flag service ✅ backend/services/feature_flags.py + admin API + require_feature() helper + Redis caching
- [x] [MONITORING][P1] Define SLIs/SLOs and create Grafana SLO dashboard ✅ docs/slo.md + infra/grafana/dashboards/slo.json + recording rules
- [x] [MONITORING][P1] Instrument FastAPI with Prometheus metrics ✅ middleware/metrics.py + custom business metrics (sessions, LLM costs, requests) + /metrics endpoint
- [x] [MONITORING][P1] Create Grafana dashboards (API, deliberation, cost, infrastructure) ✅ infra/grafana/dashboards/{api,deliberation,cost,infrastructure}.json
- [x] [MONITORING][P1] Configure Prometheus alerting rules ✅ infra/prometheus/alerts/slo.yml + infra/alertmanager/config.yml + docker-compose monitoring profile
- [x] [MONITORING][P1] Configure structured JSON logging with context fields ✅ bo1/utils/logging.py (JsonFormatter, log_format setting, correlation_id integration)
- [x] [MONITORING][P1] Setup Grafana Loki for log aggregation ✅ loki+promtail in docker-compose.infrastructure.yml, Loki datasource, logs dashboard
- [x] [MONITORING][P1] Implement audit logging middleware ✅ backend/api/middleware/audit_logging.py + backend/services/api_audit.py + backend/jobs/audit_cleanup.py + q1_add_api_audit_log.py migration
- [x] [MONITORING][P1] Add security headers middleware ✅ backend/api/middleware/security_headers.py (X-Frame-Options, HSTS, CSP, etc.)

### Admin Dashboard [ADMIN-UI]

- [x] [ADMIN][P2] Create admin route layout and auth middleware ✅ +layout.ts + +layout.svelte with client-side redirect
- [x] [ADMIN][P2] Create admin API client ✅ frontend/src/lib/api/admin.ts
- [x] [ADMIN][P2] Create active sessions page with live updates ✅ /admin/sessions with 10s polling
- [x] [ADMIN][P2] Create session details modal ✅ SessionDetailModal.svelte
- [x] [ADMIN][P2] Create cost analytics page with charts ✅ /admin/costs with daily bar chart
- [x] [ADMIN][P2] Implement CSV export for cost data ✅ Export button on costs page
- [x] [ADMIN][P2] Add kill session button with confirmation ✅ SessionDetailModal kill with reason
- [x] [ADMIN][P2] Add kill-all-sessions emergency button ✅ Sessions page kill-all with double confirm
- [x] [ADMIN][P2] Create kill history audit trail display ✅ /admin/kill-history + GET /api/admin/sessions/kill-history endpoint
- [x] [ADMIN][P2] Create alert settings page (ntfy.sh thresholds) ✅ /admin/alerts/settings + GET /api/admin/alerts/settings endpoint
- [x] [ADMIN][P2] Create alert history page ✅ /admin/alerts/history + GET /api/admin/alerts/history endpoint + v1_add_alert_history.py migration + log_alert() in alerts.py

### QA & Security [QA]

- [x] [QA][P1] Create load test scenarios (normal, peak, sustained) with Locust ✅ tests/load/ + Makefile targets (load-test-normal/peak/sustained/ui)
- [x] [QA][P1] Perform auth security audit (session, OAuth, rate limiting) ✅ audits/reports/auth-security.report.md (0 critical, 2 medium, 3 low)
- [x] [QA][P1] Perform auth penetration testing (session fixation, CSRF, brute force) ✅ audits/reports/auth-pentest.report.md (0 critical, 0 high, 1 low)
- [x] [QA][P1] Perform infrastructure security audit (network, secrets, logging) ✅ audits/reports/infra-security.report.md (0 critical, 1 high, 4 medium, 3 low)
- [x] [QA][P1] Scan Python and npm dependencies for vulnerabilities ✅ pip-audit + npm audit in CI + Makefile targets (audit-python, audit-npm, audit-deps)
- [x] [QA][P1] Perform GDPR compliance audit ✅ audits/reports/gdpr-compliance.report.md (0 critical, 1 high, 4 medium, 3 low)
- [x] [QA][P1] Create E2E tests for critical user flows (Playwright) ✅ frontend/e2e/ + auth.spec.ts, meeting-create.spec.ts, meeting-complete.spec.ts, actions.spec.ts, datasets.spec.ts + CI integration
- [x] [QA][P1] Perform OWASP Top 10 security testing ✅ audits/reports/owasp-top10.report.md (0 critical, 0 high, 2 medium, 4 low)

### Deployment & Infrastructure [DEPLOY]

- [x] [DEPLOY][P1] Draft privacy policy (GDPR Art. 13-14) ✅ frontend/src/routes/legal/privacy/+page.svelte
- [x] [DEPLOY][P1] Draft terms of service ✅ frontend/src/routes/legal/terms/+page.svelte (13 sections: acceptance, service description, accounts, acceptable use, IP, payments, privacy, liability, indemnification, disclaimer, changes, governing law, contact)
- [x] [DEPLOY][P1] Create privacy policy and terms of service pages ✅ /legal/privacy, /legal/terms, /legal/cookies exist
- [ ] [DEPLOY][P1] Sign DPAs with data processors (Supabase, Resend, Anthropic, DigitalOcean)
- [x] [DEPLOY][P1] Create GitHub Actions CI workflow (test.yml) ✅ .github/workflows/ci.yml (lint, typecheck, pytest, coverage)
- [x] [DEPLOY][P1] Create staging deployment workflow (deploy-staging.yml) ✅ .github/workflows/deploy-staging.yml (auto-deploy on main, ports 8002/3002)
- [x] [DEPLOY][P1] Create production deployment workflow (deploy-production.yml) ✅ .github/workflows/deploy-production.yml (blue-green, security scan, health checks)
- [ ] [DEPLOY][P1] Configure GitHub secrets
- [ ] [DEPLOY][P1] Purchase domain and configure DNS
- [ ] [DEPLOY][P1] Setup SSL/TLS with Let's Encrypt
- [x] [DEPLOY][P1] Enable PostgreSQL daily backups ✅ scripts/backup_postgres.sh + make backup-db/restore-db/verify-backup
- [x] [DEPLOY][P1] Configure Redis persistence (AOF + RDB) ✅ appendonly yes + save in docker-compose.infrastructure.yml
- [x] [DEPLOY][P1] Create disaster recovery runbook ✅ docs/DISASTER_RECOVERY.md (pre-existing)
- [ ] [DEPLOY][P1] Setup uptime monitoring (UptimeRobot)
- [x] [DEPLOY][P1] Create incident response playbook ✅ docs/INCIDENT_RESPONSE.md
- [ ] [DEPLOY][P1] Setup blue-green deployment environments
- [x] [DEPLOY][P1] Document production deployment procedure ✅ docs/PRODUCTION_DEPLOYMENT.md

### User Documentation & Launch [LAUNCH]

- [x] [LAUNCH][P1] Create help center page ✅ frontend/src/routes/(app)/help/+page.svelte
- [x] [LAUNCH][P1] Write user documentation (getting started, FAQs, tutorials) ✅ frontend/src/lib/data/help-content.ts (16 articles across 6 categories)
- [x] [LAUNCH][P1] Add search to help center ✅ Client-side fuzzy search in help page
- [ ] [LAUNCH][P1] Deploy Prometheus and Grafana to production
- [ ] [LAUNCH][P1] Configure production Alertmanager
- [ ] [LAUNCH][P1] Switch Stripe to live mode
- [x] [LAUNCH][P1] Create system shutdown procedure ✅ docs/SYSTEM_SHUTDOWN.md
- [ ] [LAUNCH][P1] Test emergency access procedures

---

## Task backlog (from \_TODO.md, 2025-12-09 update)

### Admin & Analytics [ADMIN-EXT]

- [x] [ADMIN][P1] Extend admin pages with cost tracking and reporting views ✅ /admin/costs already exists
- [x] [ADMIN][P1] Implement onboarding pipeline analytics (funnel metrics) ✅ backend/services/onboarding_analytics.py + /api/admin/metrics/onboarding
- [x] [ADMIN][P1] Implement app usage metrics dashboard (DAU, sessions, actions) ✅ /admin/metrics page with DAU/WAU/MAU, daily charts, funnel
- [x] [SECURITY][P1] Audit API to verify costs not exposed to non-admin users ✅ Fixed: GET /sessions/{id}/costs now admin-only, SessionResponse.cost stripped for non-admin, SSE cost events filtered

### Governance Audits [AUDIT]

- [x] [AUDIT][P1] Run governance audit: clean (code quality, lint, format) ✅ ruff check/format, mypy, svelte-check, pre-commit all pass
- [x] [AUDIT][P1] Run governance audit: secure (security scan) ✅ audits/reports/secure-governance.report.md (0 critical, 0 high, 1 medium, 2 low)
- [x] [AUDIT][P1] Run governance audit: full (comprehensive review) ✅ audits/reports/full-governance.report.md (synthesis of 17 audits, 0 critical, 0 high open, 1 medium accepted)

### Social Login [AUTH]

- [x] [AUTH][P2] Implement LinkedIn OAuth login ✅ bo1/config.py + supertokens_config.py + login/+page.svelte + tests/api/test_auth_linkedin.py
- [x] [AUTH][P2] Implement GitHub OAuth login ✅ bo1/feature_flags/features.py + supertokens_config.py + login/+page.svelte + tests/api/test_auth_github.py
- [x] [AUTH][P2] Implement Bluesky login ✅ bo1/config.py + bo1/feature_flags/features.py + supertokens_config.py + login/+page.svelte + af1_add_bluesky_auth.py + tests/api/test_auth_bluesky.py
- [x] [AUTH][P2] Implement Twitter/X OAuth login ✅ bo1/feature_flags/features.py + bo1/config.py + supertokens_config.py + login/+page.svelte + tests/api/test_auth_twitter.py

### Social Posting [SOCIAL]

- [ ] [SOCIAL][P3] Implement post-to-social feature (share meeting summaries)

### Mentor Chat Extensions [MENTOR-EXT] ✅ COMPLETE

- [x] [MENTOR][P2] Add mentor mode: general business advice ✅ "general" persona in mentor.py
- [x] [MENTOR][P2] Add mentor mode: action-focused guidance ✅ "action_coach" persona in mentor.py
- [x] [MENTOR][P2] Add mentor mode: metrics/data interpretation ✅ "data_analyst" persona in mentor.py

### Dataset Q&A [DATA-EXT]

- [x] [DATA][P1] Implement dataset Q&A flow ("which product range should I focus on given X,Y,Z?") ✅ Business context injection in /ask endpoint + format_business_context() + system prompt business_awareness section

### Onboarding Flow [ONBOARDING]

- [x] [ONBOARDING][P1] Implement new account → business context → first question flow ✅ backend/api/onboarding.py + frontend/src/routes/(app)/onboarding/+page.svelte (pre-existing) + welcome page redirect
- [x] [ONBOARDING][P1] Generate demo questions derived from business context ✅ backend/services/demo_questions.py + GET /api/v1/context/demo-questions + frontend/src/routes/(app)/welcome/+page.svelte

### Integrations [INTEGRATIONS]

- [x] [INTEGRATIONS][P2] Implement Google Calendar integration for actions (sync due dates) ✅ backend/services/google_calendar.py + action_calendar_sync.py + API endpoints + /settings/integrations UI + 27 unit tests
- [x] [LLM][P1] Implement OpenAI fallback when Anthropic unavailable ✅ Provider-agnostic tier system (core/fast) + circuit breaker fallback

### Backlog Review [META]

- [x] [META][P1] Review MVP doc and add any incomplete tasks to \_TASK.md ✅ Cross-referenced MVP_IMPLEMENTATION_ROADMAP.md, MVP_LAUNCH_READINESS.md, PRODUCT_REQUIREMENTS.md - existing backlog comprehensive, added session export and sharing tasks

---

## Bug fixes (from \_TODO.md, 2025-12-09)

### Working Status Timer [BUG-TIMER]

- [x] [BUG][P1] Fix working status timer estimates (shows "2-4 seconds" but takes 30s+) ✅ Removed misleading time estimates
- [x] [BUG][P1] Improve working status timer accuracy or remove time estimates ✅ Now shows elapsed time only

### Expert Contribution Quality [BUG-DELIB]

- [x] [BUG][P1] Reduce expert repetition across rounds (detect when topic fully explored) ✅ Novelty detection + semantic dedup working
- [x] [BUG][P1] Enforce max 1 contribution per expert per round ✅ Fixed round numbering mismatch + added guard
- [x] [BUG][P1] Add signal detection when nothing new to add (topic exhausted) ✅ Judge novelty_score + should_exit_early() implemented

### Productive Disagreement [BUG-DELIB]

- [x] [BUG-DELIB][P1] Add "stalled disagreement" detection (conflict > 0.7 AND novelty < 0.40 for 2+ rounds) ✅ detect_stalled_disagreement() + counter tracking
- [x] [BUG-DELIB][P1] Add Facilitator "Acknowledge Impasse" option to guide experts toward resolution ✅ \_handle_impasse_intervention() in facilitator.py
- [x] [BUG-DELIB][P1] Guide experts to: find common ground, disagree-and-commit, or propose conditional recommendations ✅ Resolution options in impasse guidance
- [x] [BUG-DELIB][P1] Trigger early synthesis when topic exhausted even without consensus (reduces cost, improves UX) ✅ force_synthesis after 3+ stalled rounds

### Meeting Output [BUG-OUTPUT]

- [x] [BUG][P1] Add actions to PDF report export ✅ Added actions section to PDF generator with status/priority badges

### Context Persistence [BUG-CONTEXT]

- [x] [BUG][P1] Persist clarifying question answers to settings > context > insights/metrics ✅ Added clarifications column + CONTEXT_FIELDS entry

### Gantt Chart API [BUG-GANTT]

- [x] [BUG][P1] Fix Gantt API validation error (GanttDependency missing from/to/type fields) ✅ Fixed field names
- [x] [BUG][P2] Gantt chart month view renders bars incorrectly (wrong positioning/sizing) ✅ Postinstall patch enables commented-out Month view fix in frappe-gantt

### Navigation & Routing [BUG-NAV]

- [x] [BUG][P1] /meeting breadcrumb link returns 404 (no meetings list page exists) ✅ Created /meeting/+page.svelte
- [x] [BUG][P1] Clicking action in dashboard navigates to meeting instead of action detail page ✅ Fixed href to /actions/{id}

---

## Task backlog (from \_TODO.md, 2025-12-11)

### Gantt Chart UX [GANTT-UX]

- [x] [UX][P1] Fix Gantt click-drag: only click-and-release should open action; click-drag should not trigger navigation ✅ Drag detection via mouse events, 5px threshold
- [x] [UX][P2] Confirm Gantt drag-to-reschedule saves to DB ✅ PATCH /api/v1/actions/{id}/dates endpoint exists; added updateActionDates() to API client; wired onDateChange in project Gantt; 12 unit tests
- [x] [UX][P2] Improve Gantt colour coding by project and/or status ✅ Implemented 4 strategies (BY_STATUS, BY_PROJECT, BY_PRIORITY, HYBRID) with user preferences + color service + API endpoints + 20 unit tests + help documentation

### Action Tracking Enhancements [ACTION-TRACK]

- [x] [UX][P2] Track action delays and early start/finish dates for variance analysis ✅ a2_add_action_progress migration + calculate_variance() method + ActionVariance model
- [x] [UX][P2] Add progress measurement to actions (percentage, points, or expanded status states) ✅ progress_type/progress_value/estimated_effort_points fields + PATCH /api/v1/actions/{id}/progress endpoint + ActionProgressUpdate model
- [x] [UX][P2] Show full action details in exported PDF/report (not just title) ✅ Extended ReportAction interface, enhanced renderActionItem with what_and_how/success_criteria/dependencies/progress, added overdue highlighting, CSS styling, 20 unit tests

### Projects System & Action Dependencies [PROJECTS-COMPLETE]

- [x] [PROJECTS][P2] Allow actions/meetings to be assigned to projects ✅ project_id field in actions table + PATCH /api/v1/actions/{id} support
- [x] [PROJECTS][P2] Implement action dependencies ✅ POST/GET/DELETE /api/v1/actions/{id}/dependencies + circular detection + auto-block/unblock
- [x] [PROJECTS][P2] Comprehensive test coverage (45 tests) ✅ tests/api/test_projects.py, test_action_dependencies_api.py, test_projects_integration.py

### Admin Observability [ADMIN-OBS]

- [x] [ADMIN][P1] Extend admin pages with user metrics (signup rate, active users) ✅ backend/services/user_analytics.py + /admin/metrics page
- [x] [ADMIN][P1] Extend admin pages with usage metrics (meeting count, action count, API calls) ✅ /api/admin/metrics/usage endpoint + frontend charts
- [x] [ADMIN][P2] Add admin access link to Grafana dashboard ✅ ObservabilityLinks component + GET /api/admin/observability-links + env config
- [x] [ADMIN][P2] Add admin access link to Prometheus dashboard ✅ ObservabilityLinks component + GET /api/admin/observability-links + env config
- [x] [ADMIN][P2] Add admin access link to Sentry error tracking ✅ ObservabilityLinks component + GET /api/admin/observability-links + env config
- [x] [ADMIN][P2] Add admin view of onboarding funnel analytics ✅ backend/services/onboarding_analytics.py + /api/admin/metrics/onboarding + funnel visualization

### Navigation & Header [NAV-HEADER]

- [x] [UX][P1] Highlight header nav link for current/active page ✅ Header.svelte isActive() with $page store

### Data Analysis Persistence [DATA-PERSIST]

- [x] [BUG][P1] Persist analysis clarifying questions/answers so they are available in future sessions ✅ Added clarifications JSONB column to datasets, auto-detect Q&A patterns, inject prior context into prompts

### Dashboard Redesign [DASH-REDESIGN] ✅ COMPLETE

- [x] [UX][P2] Replace dashboard completion trend bar chart with GitHub-style heatmap (meetings run, completed, tasks started, planned) ✅ ActivityHeatmap.svelte component with 52-week grid, color-coded activity intensity, date range toggle (1M/3M/1Y), tooltip breakdown

### Dev Workflow [DEV-FLOW]

- [ ] [DEV][P2] Clarify scope of: "update live MCP prompt (fix.md) - dev server is running via docker only, stop if inaccessible"
- [x] [UX][P2] Add observability for slow/failing/repeated operations (timing, error tracking) ✅ Frontend operation-tracker.ts + API client instrumentation + POST /api/v1/metrics/client + Redis storage + 15 tests
- [x] [DEV][P3] Automate plan→build flow loop using hooks ✅ .claude/settings.json Stop hook + plan.md approval step + workflow-state.json

### Deliberation Improvements [DELIB-IMPROVE]

- [x] [DELIB][P2] Evaluate adding pragmatist/realist expert persona to improve actionable recommendations ✅ Added Implementation Realist persona (Marcus Chen) to bo1/data/personas.json + ae1_impl_realist_persona migration

### Insights System [INSIGHTS] ✅ COMPLETE

- [x] [UX][P2] Add staleness tracking (updated_at timestamps) to insights ✅ y1_add_insight_timestamps migration
- [x] [UX][P2] Implement PATCH endpoint for editing individual insights ✅ PATCH /api/v1/context/insights/{question_hash}
- [x] [UX][P2] Add "Edit" button to insights with modal UI ✅ frontend/src/routes/(app)/settings/context/insights/+page.svelte
- [x] [UX][P2] Add insights to GDPR data export ✅ Structured insights extraction in backend/services/gdpr.py
- [x] [UX][P2] Add staleness prompt to meeting creation (>30 days old) ✅ backend/services/insight_staleness.py + SessionResponse.stale_insights + modal warning in meeting/new
- [x] [UX][P2] Display insights in meeting context summary ✅ bo1/graph/nodes/context.py injects insights with freshness indicators
- [x] [UX][P2] Note insight sources/freshness in expert prompts ✅ bo1/prompts/persona.py insight_awareness section

---

## Task backlog (from \_TODO.md, 2025-12-11)

### Sub-Problem Meeting UI [SUBPROBLEM-UI]

- [x] [BUG][P1] Fix meeting UI not auto-displaying meeting events (requires manual refresh) ✅ Added subproblem_waiting to SSE EVENT_TYPES + verified $state.raw reactivity
- [x] [BUG][P1] Fix sub-problem showing "meeting complete" twice but not showing experts selected or their contributions ✅ Fixed singleton event deduplication in sessionStore.svelte.ts
- [x] [UX][P1] Mask or replace "subproblem_waiting" technical event with user-friendly message ("Waiting for sub-problems 1, 2 to complete..."), these should disappear when the meeting starts and new content appears ✅ Created SubProblemWaiting.svelte component
- [x] [BUG][P1] Fix summary showing sub-problem 1 completed before all sub-problems finished (timing/sequencing issue) ✅ Fixed showConclusionTab logic to require meta_synthesis for multi-SP meetings

### Meeting Page UI Issues [MEETING-UI]

- [x] [BUG][P0] Parse and format synthesis JSON in Executive Summary (currently displays raw JSON with curly braces) ✅ Fixed frontend xml-parser.ts to handle JSON+footer format
- [x] [BUG][P1] Fix page header to show "Meeting Complete" instead of "Meeting in Progress" for completed meetings ✅ MeetingHeader.svelte now status-aware
- [x] [BUG][P1] Populate sidebar metrics (Rounds, Contributions, Risks) from session events instead of showing 0 ✅ DecisionMetrics already derives from events (verified)
- [x] [BUG][P1] Fix Focus Area tab switching (clicking tabs doesn't change displayed content) ✅ Added tab validation in viewState.svelte.ts
- [x] [UX][P2] Show descriptive sub-problem goals in Focus Area tab labels instead of "Focus Area 1" ✅ Truncated goal labels + tooltip on hover
- [x] [UX][P2] Hide or update "Connected" indicator for completed meetings ✅ Wrapped connection status in {#if session?.status !== 'completed'}
- [x] [UX][P2] Humanize meeting breadcrumb with problem statement excerpt instead of raw ID ✅ breadcrumbLabels store + truncateLabel() + layout getBreadcrumbsWithData()
- [x] [UX][P1] Auto-scroll to clarification input when user action required (not obvious input is needed) ✅ Added scrollIntoView effect + attention animation + auto-focus
- [x] [TEST][P2] Add E2E test for completed meeting view (header, synthesis, tabs, metrics) ✅ Enhanced meeting-complete.spec.ts with connection status, JSON rendering, tab labels, metrics values, breadcrumb, console error tests

### Early Meeting Termination [MEETING-TERMINATE] ✅ COMPLETE

- [x] [UX][P2] Add early meeting termination option when critical blocker identified in sub-problem ✅ POST /api/v1/sessions/{id}/terminate + TerminationModal.svelte + MeetingHeader "End Early" button
- [x] [UX][P2] Add user prompts for critical blockers: provide info, continue best-endeavours, or cancel ✅ Three termination types: blocker_identified, continue_best_effort, user_cancelled with reason input
- [x] [BILLING][P2] Implement partial meeting billing (only completed meetings count toward usage) ✅ billable_portion calculated from completed_sub_problems/total_sub_problems + z3_add_session_termination migration

---

## Task backlog (from \_TODO.md, 2025-12-11)

### Storage Organization [STORAGE-ORG]

- [x] [STORAGE][P2] Implement workspace/user folder hierarchy for DO Spaces uploads (organize user files under workspace_id/user_id paths) ✅ SpacesClient.put_file() + datasets/user_id/ prefix + storage_path column + 11 tests

---

## Task backlog (from MVP review, 2025-12-12)

### Session Export & Sharing [SESSION-EXPORT] ✅ COMPLETE

**Completed (2025-12-12):**

- [x] [EXPORT][P3] Create session export service (JSON/Markdown) ✅ backend/services/session_export.py
- [x] [EXPORT][P3] Create session_shares migration and schema ✅ migrations/versions/z2_create_session_shares.py (with merge resolution)
- [x] [EXPORT][P3] Create session share service (tokens, expiry, validation) ✅ backend/services/session_share.py

**Completed (2025-12-12, phase 2):**

- [x] [EXPORT][P3] Add export API endpoints (GET /sessions/{id}/export?format=json|markdown) ✅ backend/api/sessions.py + SessionExporter
- [x] [EXPORT][P3] Add share API endpoints (POST/GET/DELETE /sessions/{id}/share) ✅ backend/api/sessions.py
- [x] [EXPORT][P3] Add public share endpoint (GET /api/v1/share/{token}) ✅ backend/api/share.py
- [x] [EXPORT][P3] Add cleanup job for expired shares ✅ backend/jobs/session_share_cleanup.py + scheduler integration
- [x] [EXPORT][P3] Add session_repository sharing methods (create_share, list_shares, revoke_share, get_share_by_token) ✅ bo1/state/repositories/session_repository.py

**Completed (2025-12-12, phase 3 - frontend):**

- [x] [EXPORT][P3] Add API client methods for export/sharing ✅ frontend/src/lib/api/client.ts (exportSession, createShare, listShares, revokeShare, getPublicShare)
- [x] [EXPORT][P3] Implement session detail export UI (download buttons) ✅ MeetingHeader.svelte with Export dropdown (JSON/Markdown)
- [x] [EXPORT][P3] Implement public share UI and modal (TTL selector, copy URL) ✅ frontend/src/lib/components/meeting/ShareModal.svelte
- [x] [EXPORT][P3] Create public view page for shared sessions ✅ frontend/src/routes/share/[token]/+page.svelte + +layout.svelte + +error.svelte + +page.server.ts
- [x] [EXPORT][P3] Write API tests ✅ tests/api/test_session_export.py + test_session_sharing.py (28 tests)

---

## Task backlog (from auth security audit, 2025-12-12)

### Security Remediation [SECURITY-REMEDIATION]

- [x] [SECURITY][P2] Encrypt OAuth tokens at rest (use Fernet/cryptography for google_tokens column) ✅ backend/services/encryption.py + s1_encrypt_oauth_tokens migration
- [x] [SECURITY][P2] Implement account lockout after failed auth attempts (exponential backoff: 5 failures=30s, 10=5min, 15=1hr) ✅ backend/services/auth_lockout.py + bo1/constants.py AuthLockout + SuperTokens API override
- [x] [SECURITY][P3] Sanitize OAuth error messages to avoid revealing internal flow state ✅ backend/api/utils/oauth_errors.py + sanitized auth.py + supertokens_config.py + frontend error mapping
- [x] [SECURITY][P3] Add Redis availability monitoring for rate limiter fail-open risk ✅ RateLimiterHealthTracker in rate_limit.py + ntfy alerts + Prometheus metrics (bo1_rate_limiter_degraded gauge)

---

## Task backlog (from infra security audit, 2025-12-12)

### Infrastructure Security Remediation [INFRA-SEC]

- [x] [SECURITY][P1] Bind development ports to localhost in docker-compose.yml (Postgres, Redis, SuperTokens, API) ✅
- [x] [SECURITY][P2] Remove hardcoded SuperTokens API key fallback - fail startup if env var missing ✅
- [x] [SECURITY][P2] Add Redis authentication to development docker-compose.yml ✅
- [x] [SECURITY][P2] Add log scrubbing pipeline stages to Promtail config (password, token, secret patterns) ✅
- [x] [SECURITY][P2] Encrypt database backups with GPG/age before storage ✅ scripts/backup_postgres.sh + restore + verify + Makefile targets + docs/DISASTER_RECOVERY.md
- [x] [DEPLOY][P2] Create disaster recovery runbook (docs/DISASTER_RECOVERY.md) (2-4 hours) ✅ docs/DISASTER_RECOVERY.md
- [x] [SECURITY][P3] Reduce Promtail Docker socket exposure - use file-based scraping instead ✅ Removed docker.sock mount, added /var/lib/docker/containers:ro, updated promtail-config.yml for file-based log scraping
- [x] [DEPLOY][P3] Extend backup retention (weekly for 30 days, monthly for 90 days) ✅ scripts/backup_postgres.sh tiered retention (daily 7d, weekly 30d, monthly 90d) + remote cleanup

---

## Task backlog (from GDPR compliance audit, 2025-12-12)

### GDPR Remediation [GDPR-REMEDIATION]

- [x] [GDPR][P1] Implement GDPR consent capture during signup (checkbox + timestamp in gdpr_consent_at column) ✅ Login page checkbox, callback stores consent, POST /api/v1/user/gdpr-consent endpoint
- [x] [GDPR][P2] Add dataset clarifications to data export (backend/services/gdpr.py collect_user_data) ✅
- [x] [GDPR][P2] Add dataset Q&A conversation history to data export ✅
- [x] [GDPR][P2] Clear Redis conversation history on account deletion (backend/services/gdpr.py delete_user_data) ✅
- [x] [GDPR][P3] Fix privacy policy links to /settings/privacy (create page or update links) - Created /settings/privacy page with email prefs, data export, account deletion
- [x] [GDPR][P3] Add explicit LLM processing notice during onboarding flow ✅ Info callout on /onboarding before progress indicator
- [x] [GDPR][P3] Add user-configurable data retention period setting ✅ r1_add_user_retention_setting.py + GET/PATCH /api/v1/user/retention + /settings/privacy UI

---

## Task backlog (from supply-chain + web security investigation, 2025-12-12)

### Supply-Chain Security [SEC][SUPPLY]

- [x] [SEC][SUPPLY][P1] Pin npm dependency versions (remove `^` ranges from package.json) ✅ All deps pinned in frontend/package.json

- [x] [SEC][SUPPLY][P1] Add automated malware/typosquatting scanning to CI ✅ OSV-Scanner in .github/workflows/ci.yml + .osv-scanner.toml + make osv-scan

- [x] [SEC][SUPPLY][P2] Review high-risk transitive dependencies for single-maintainer packages ✅ audits/reports/supply-chain-review.report.md (70 npm + 16 Python packages analyzed; no critical risks; dompurify/Cure53 accepted)

---

### CI & Dependency Policy [SEC][CI]

- [x] [SEC][CI][P1] Make `npm audit` failures blocking (currently runs but may not fail build on moderate) ✅ Changed to --audit-level=moderate in ci.yml

- [x] [SEC][CI][P1] Add PR dependency review gate (flag new deps for manual review) ✅ Added dependency-review-action job to ci.yml

- [x] [SEC][CI][P2] Integrate OSV-Scanner or Trivy for broader vulnerability coverage ✅ OSV-Scanner added to CI

---

### Web Security [SEC][WEB]

- [x] [SEC][WEB][P1] Tighten CSP: replace `'unsafe-inline' 'unsafe-eval'` with nonce-based script loading ✅ SvelteKit CSP mode:'auto' + nginx CSP removed (SvelteKit handles)

- [x] [SEC][WEB][P2] Add CSP report-uri endpoint for violation monitoring ✅ POST /api/v1/csp-report + svelte.config.js report-uri directive

- [x] [SEC][WEB][P2] Submit domain to HSTS preload list ✅ nginx configs updated with preload directive + /api/health/hsts endpoint + nginx/README.md docs
  - Manual submission required at https://hstspreload.org after verifying production deployment

---

### Authentication & Sessions [SEC][AUTH]

- [x] [SEC][AUTH][P1] Verify COOKIE_SECURE=true in production deployment ✅ Startup validation + CI check + docs

  - Startup fails if ENV=production and COOKIE_SECURE!=true
  - deploy-production.yml pre-deployment check added
  - docs/DISASTER_RECOVERY.md security checklist added

- [x] [SEC][AUTH][P2] Add explicit CSRF token validation for non-SuperTokens routes ✅ backend/api/middleware/csrf.py + frontend X-CSRF-Token header
  - SuperTokens routes protected via anti-csrf; custom endpoints now use double-submit cookie pattern

---

### Rate Limiting & Abuse [SEC][ABUSE]

- [x] [SEC][ABUSE][P1] Add rate limiting to SSE streaming endpoint ✅ @limiter.limit(STREAMING_RATE_LIMIT) applied to stream_deliberation()

- [x] [SEC][ABUSE][P1] Add rate limiting to dataset upload endpoint ✅ @limiter.limit(UPLOAD_RATE_LIMIT) applied to upload_dataset() with 10/hour limit

- [x] [SEC][ABUSE][P2] Add WAF rules for common attack patterns (SQLi, XSS probes) ✅ nginx/waf-rules.conf + waf-allowlist.conf + Promtail scraping

---

### Logging & Monitoring [SEC][LOG]

- [x] [SEC][LOG][P2] Audit logs for PII/secret leakage ✅ bo1/utils/log_sanitizer.py + JsonFormatter integration + Promtail scrubbing + 33 tests

  - Centralized sanitizer: password/secret/token/api_key redaction
  - Email partial masking (j\*\*\*@example.com)
  - Bearer token truncation (8 chars + ...)
  - Nested dict recursive sanitization
  - Defense-in-depth: app-level + Promtail pipeline

- [x] [SEC][LOG][P2] Add security event alerting (failed auth spikes, rate limit hits) ✅ backend/services/security_alerts.py + bo1/constants.py SecurityAlerts + integration with auth_lockout.py and rate_limit.py

- [x] [SEC][LOG][P2] Extend security event alerting (failed auth spikes, rate limit hits) with ntfy alerts ✅ security_alerts.py calls alerts.py (alert_auth_failure_spike, alert_rate_limit_spike, alert_lockout_spike) - ntfy integration complete

---

## Task backlog (from \_TODO.md, 2025-12-12)

### Privacy Settings Fix [BUG-PRIVACY]

- [x] [BUG][P1] Fix 500 error on GET /api/v1/user/retention endpoint (settings > privacy page broken) ✅ Added NULL fallback handling in get_retention_setting() + integration tests

### Mentor Enhancements [MENTOR-ENH]

- [x] [MENTOR][P2] Allow user to select any expert persona for mentor coaching session (not just auto-selected) ✅ GET /api/v1/mentor/personas endpoint + PersonaPicker fetches from API + Auto option + persona override in chat
- [x] [MENTOR][P2] Add ability to @ mention meetings, actions, and datasets in mentor chat for context injection ✅ @meeting/@action/@dataset:UUID parsing + MentionResolver + MentionAutocomplete.svelte + message chips + prompt injection + 30 tests

### Data Retention Policy [RETENTION-POLICY]

- [x] [UX][P2] Extend data retention minimum to 1 year (current options too short for monthly plan users) ✅ Range now 365-3650 days (1-10 years); ac1_extend_retention_range migration
- [x] [UX][P3] Evaluate removing user-facing retention config (data available until account closure) ✅ Evaluation complete in \_PLAN.md; **DECISION REQUIRED**: Option A (remove config, infinite retention) vs Option B (keep); implementation blocked pending user decision

### Insights Enhancement [INSIGHTS-ENH] ✅ COMPLETE

- [x] [INSIGHTS][P2] Use Haiku to categorize and structure user-provided insights (extract metrics, map to business context) ✅ backend/services/insight_parser.py
- [x] [INSIGHTS][P2] Auto-parse raw insight text into structured metric/category format ✅ InsightCategory enum + InsightMetric dataclass + category badges in UI

### Context Auto-Update [CONTEXT-AUTO] ✅ COMPLETE

- [x] [CONTEXT][P2] Detect business context updates from user input across all flows (clarifications, problem statements, action updates) ✅ backend/services/context_extractor.py + integration in control.py, sessions.py, actions.py
- [x] [CONTEXT][P2] Auto-update context with >80% confidence; prompt user confirmation if <80% confident ✅ filter_high_confidence_updates() + pending_updates JSONB + GET/POST/DELETE /api/v1/context/pending-updates endpoints + PendingUpdates.svelte
- [x] [CONTEXT][P2] Maintain history of metric changes to show trend direction (improving/worsening) ✅ context_metric_history JSONB + ad1_add_context_metric_history migration + backend/services/trend_calculator.py + GET /api/v1/context/with-trends endpoint

### Industry Benchmarking [INDUSTRY-BENCH] ✅ COMPLETE

- [x] [INDUSTRY][P3] Extend competitor watch to industry/market benchmarking (churn, ARPU, etc.) ✅ backend/api/industry_insights.py expanded with 4 benchmark categories (growth, retention, efficiency, engagement), 15+ metrics across 4 industry segments (SaaS, E-commerce, Fintech, Marketplace)
- [x] [INDUSTRY][P3] Implement tiered industry comparison limits (Free=3, Starter=5, Pro=all) ✅ bo1/constants.py IndustryBenchmarkLimits + tier filtering in get_stub_insights() + locked field on IndustryInsight + upgrade_prompt in response
- [x] [INDUSTRY][P3] Add user benchmark comparison endpoint ✅ GET /api/v1/industry-insights/compare with percentile calculation + performance status
- [x] [INDUSTRY][P3] Create frontend benchmarks UI page ✅ frontend/src/routes/(app)/settings/intelligence/benchmarks/+page.svelte with category filtering, percentile visualization, tier awareness
- [x] [INDUSTRY][P3] Write unit tests for benchmark tier filtering ✅ tests/api/test_industry_benchmarks.py (41 tests)

---

## Task backlog (from \_TODO.md, 2025-12-13)

### Dashboard Completion Trends Bug [BUG-TRENDS] ✅ COMPLETE

- [x] [BUG][P1] Fix dashboard completion trends timeframe toggles (1m, 3m, 1y) - buttons don't update displayed data ✅ Fixed date filtering by actual date range instead of array slice
- [x] [BUG][P1] Fix dashboard completion trends chart box positioning - boxes not aligned to correct month on x-axis ✅ Fixed grid generation to use relative week offsets from range start
- [x] [BUG][P1] Investigate and fix root cause of dashboard completion trends display issues ✅ Root causes: 1) slice by index instead of date filter, 2) grid relative to year start instead of range start, 3) hardcoded month positions

### Privacy Retention Settings [RETENTION-UX] ✅ COMPLETE

- [x] [UX][P2] Change default privacy retention setting to 2 years ✅ af2_change_retention_default migration + backend fallback updated
- [x] [UX][P2] Replace 5-year and 10-year retention options with single 'forever' option ✅ Frontend RETENTION_OPTIONS updated, backend validation accepts -1, cleanup job skips -1 users

---

## Task backlog (from \_TODO.md, 2025-12-13)

### Feedback Analysis System [FEEDBACK-AI] ✅ COMPLETE

- [x] [FEEDBACK][P2] Run submitted feedback through Haiku to extract sentiment (positive/negative/neutral) ✅ backend/services/feedback_analyzer.py + FeedbackAnalysis dataclass + Sentiment enum
- [x] [FEEDBACK][P2] Extract top themes and topics from feedback via LLM analysis ✅ 15 standard themes + Haiku extraction + fallback keyword detection
- [x] [FEEDBACK][P2] Track users who requested specific features (link feedback to user for follow-up) ✅ GET /api/admin/feedback/by-theme/{theme} + theme filtering in list endpoint
- [x] [FEEDBACK][P2] Display feedback themes and sentiment summary in admin page ✅ FeedbackAnalysisSummary + sentiment badges + theme tags + filtering UI

### Dashboard Activity Heatmap [HEATMAP-ENH] ✅ COMPLETE

- [x] [UX][P2] Change activity heatmap to rolling 12-month view (6 months back, 6 months forward) ✅ ActivityHeatmap.svelte - fixed 12-month window (dateRange calculation)
- [x] [UX][P2] Add colour coding per activity type (meetings run, actions completed, actions started, mentor sessions) ✅ ACTIVITY_COLORS constant + getDominantType() + getColor() with type-based colours (brand/success/warning/info)
- [x] [UX][P2] Add toggle buttons to show/hide individual activity types on heatmap ✅ enabledTypes state + toggleType() + clickable legend items + toggle buttons above heatmap

### Mentor @ Feature Bug [BUG-MENTOR]

- [x] [BUG][P1] Fix mentor @ feature: content list doesn't update when tabbing between meetings/actions/data ✅ Fixed $effect dependency tracking by reading activeTab synchronously

### Meeting Context Selection [MEETING-CONTEXT] ✅ COMPLETE

- [x] [UX][P2] Add context selector to meeting setup for attaching specific data, past meetings, and actions ✅ MeetingContextSelector.svelte + context_ids in CreateSessionRequest + backend validation + context_collection_node injection + an1_add_session_context migration + 8 unit tests

### Context Auto-Detection [CONTEXT-ENH]

- [x] [UX][P2] Improve competitor auto-detect to identify specific competitors (not generic industry groups) ✅ Enhanced LLM prompt + fallback regex + merge_competitors() + format_competitors_for_display() + PendingUpdates chip UI

---

## E2E Test Failures (from CI, 2025-12-12) ✅ FIXED

### Actions E2E Tests [E2E-ACTIONS] ✅

- [x] [E2E][P2] Fix actions.spec.ts - Updated mock data to match AllActionsResponse structure (sessions array with nested tasks)
- [x] [E2E][P2] Fix actions.spec.ts - Added ActionDetailResponse mock for detail page tests

### Datasets E2E Tests [E2E-DATASETS] ✅

- [x] [E2E][P2] Fix datasets.spec.ts - Updated mock data to match DatasetListResponse structure (source_type, file_size_bytes, etc.)
- [x] [E2E][P2] Fix datasets.spec.ts - Updated mockDatasetProfile to match DatasetDetailResponse with profiles array (column_name field)

### Meeting E2E Tests [E2E-MEETING] ✅

- [x] [E2E][P2] Fix meeting-complete.spec.ts - Updated mockCompletedSession to match SessionResponse structure (phase, last_activity_at, etc.)
- [x] [E2E][P2] Fix meeting-complete.spec.ts - Fixed in_progress session mock to use 'active' status (valid enum value)

---
