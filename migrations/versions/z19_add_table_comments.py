r"""Add COMMENT ON TABLE/COLUMN for schema discoverability.

Adds PostgreSQL COMMENT statements to all tables and key columns.
Visible via \dt+ and \d+ table_name in psql.

Revision ID: z19_add_table_comments
Revises: z18_enum_check_constraints
Create Date: 2025-12-23
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z19_add_table_comments"
down_revision: str | Sequence[str] | None = "z18_enum_check_constraints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add COMMENT ON TABLE/COLUMN for schema discoverability."""
    # =====================
    # CORE TABLES
    # =====================

    # Users
    op.execute(
        "COMMENT ON TABLE users IS 'User accounts. Primary identity table linked to SuperTokens auth.'"
    )
    op.execute("COMMENT ON COLUMN users.id IS 'SuperTokens user ID (primary key).'")
    op.execute(
        "COMMENT ON COLUMN users.auth_provider IS 'OAuth provider: google, linkedin, github, twitter, bluesky.'"
    )
    op.execute("COMMENT ON COLUMN users.subscription_tier IS 'Billing tier: free, starter, pro.'")
    op.execute("COMMENT ON COLUMN users.is_admin IS 'Admin flag for elevated permissions.'")
    op.execute("COMMENT ON COLUMN users.gdpr_consent_at IS 'Timestamp of GDPR consent acceptance.'")
    op.execute(
        "COMMENT ON COLUMN users.data_retention_days IS 'User-selected data retention period in days.'"
    )

    # Sessions (meetings)
    op.execute(
        "COMMENT ON TABLE sessions IS 'Deliberation sessions (meetings). Core entity for multi-agent decision-making.'"
    )
    op.execute("COMMENT ON COLUMN sessions.id IS 'UUID session identifier.'")
    op.execute("COMMENT ON COLUMN sessions.user_id IS 'FK to users.id. Owner of the session.'")
    op.execute(
        "COMMENT ON COLUMN sessions.problem_statement IS 'User-provided problem/question to deliberate.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.problem_context IS 'JSONB: sub_problems, personas, clarifications.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.status IS 'Lifecycle: created, running, completed, failed, killed.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.phase IS 'Deliberation phase: intake, decomposition, selection, initial_round, discussion, voting, synthesis, complete.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.total_cost IS 'Accumulated LLM cost for this session (USD).'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.round_number IS 'Current deliberation round (0-indexed).'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.expert_count IS 'Denormalized: number of personas selected.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.contribution_count IS 'Denormalized: total contributions across all rounds.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.task_count IS 'Denormalized: number of extracted tasks.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.focus_area_count IS 'Denormalized: number of focus areas/sub-problems.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.workspace_id IS 'FK to workspaces.id. Workspace isolation.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.dataset_id IS 'FK to datasets.id. Attached data for analysis.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.killed_at IS 'Timestamp when session was manually killed.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.killed_by IS 'User ID or \"admin\" who killed the session.'"
    )
    op.execute(
        "COMMENT ON COLUMN sessions.kill_reason IS 'User-provided reason for killing session.'"
    )

    # Contributions
    op.execute(
        "COMMENT ON TABLE contributions IS 'Persona contributions during deliberation rounds.'"
    )
    op.execute("COMMENT ON COLUMN contributions.session_id IS 'FK to sessions.id.'")
    op.execute(
        "COMMENT ON COLUMN contributions.persona_code IS 'FK to personas.code. Which expert contributed.'"
    )
    op.execute("COMMENT ON COLUMN contributions.content IS 'LLM-generated contribution text.'")
    op.execute("COMMENT ON COLUMN contributions.round_number IS 'Deliberation round (0-indexed).'")
    op.execute(
        "COMMENT ON COLUMN contributions.phase IS 'Contribution type: initial_round, deliberation, moderator_intervention.'"
    )
    op.execute("COMMENT ON COLUMN contributions.cost IS 'LLM cost for this contribution (USD).'")
    op.execute(
        "COMMENT ON COLUMN contributions.model IS 'LLM model used: claude-sonnet-4-20250514, etc.'"
    )
    op.execute(
        "COMMENT ON COLUMN contributions.embedding IS 'vector(1536): Voyage embedding for semantic search.'"
    )
    op.execute(
        "COMMENT ON COLUMN contributions.user_id IS 'FK to users.id (denormalized for RLS).'"
    )
    op.execute(
        "COMMENT ON COLUMN contributions.status IS 'Lifecycle: in_flight, committed, rolled_back.'"
    )

    # Recommendations
    op.execute(
        "COMMENT ON TABLE recommendations IS 'Final recommendations from personas before synthesis.'"
    )
    op.execute("COMMENT ON COLUMN recommendations.session_id IS 'FK to sessions.id.'")
    op.execute("COMMENT ON COLUMN recommendations.persona_code IS 'FK to personas.code.'")
    op.execute(
        "COMMENT ON COLUMN recommendations.recommendation IS 'The persona''s recommended course of action.'"
    )
    op.execute(
        "COMMENT ON COLUMN recommendations.reasoning IS 'Rationale behind the recommendation.'"
    )
    op.execute("COMMENT ON COLUMN recommendations.confidence IS 'Confidence score 0.0-1.0.'")
    op.execute(
        "COMMENT ON COLUMN recommendations.conditions IS 'JSONB: conditions/caveats for the recommendation.'"
    )
    op.execute(
        "COMMENT ON COLUMN recommendations.sub_problem_index IS 'Which sub-problem (0-indexed).'"
    )
    op.execute(
        "COMMENT ON COLUMN recommendations.user_id IS 'FK to users.id (denormalized for RLS).'"
    )

    # Personas
    op.execute(
        "COMMENT ON TABLE personas IS 'Expert persona definitions. Seeded from personas.json.'"
    )
    op.execute(
        "COMMENT ON COLUMN personas.code IS 'Unique identifier: strategic_analyst, domain_expert, etc.'"
    )
    op.execute("COMMENT ON COLUMN personas.name IS 'Display name for the persona.'")
    op.execute("COMMENT ON COLUMN personas.expertise IS 'Area of expertise description.'")
    op.execute(
        "COMMENT ON COLUMN personas.system_prompt IS 'LLM system prompt defining persona behavior.'"
    )

    # Facilitator Decisions
    op.execute(
        "COMMENT ON TABLE facilitator_decisions IS 'Facilitator agent decisions during deliberation.'"
    )
    op.execute("COMMENT ON COLUMN facilitator_decisions.session_id IS 'FK to sessions.id.'")
    op.execute(
        "COMMENT ON COLUMN facilitator_decisions.action IS 'Decision type: continue, conclude, extend, moderate.'"
    )
    op.execute(
        "COMMENT ON COLUMN facilitator_decisions.reasoning IS 'LLM reasoning for the decision.'"
    )
    op.execute(
        "COMMENT ON COLUMN facilitator_decisions.round_number IS 'Round when decision was made.'"
    )
    op.execute(
        "COMMENT ON COLUMN facilitator_decisions.user_id IS 'FK to users.id (denormalized for RLS).'"
    )

    # Sub-problem Results
    op.execute("COMMENT ON TABLE sub_problem_results IS 'Synthesis results per sub-problem.'")
    op.execute("COMMENT ON COLUMN sub_problem_results.session_id IS 'FK to sessions.id.'")
    op.execute(
        "COMMENT ON COLUMN sub_problem_results.sub_problem_index IS 'Sub-problem index (0-indexed).'"
    )
    op.execute("COMMENT ON COLUMN sub_problem_results.goal IS 'Sub-problem goal statement.'")
    op.execute(
        "COMMENT ON COLUMN sub_problem_results.synthesis IS 'Synthesized answer for this sub-problem.'"
    )
    op.execute(
        "COMMENT ON COLUMN sub_problem_results.expert_summaries IS 'JSONB: per-expert summary contributions.'"
    )
    op.execute(
        "COMMENT ON COLUMN sub_problem_results.cost IS 'LLM cost for this sub-problem (USD).'"
    )
    op.execute(
        "COMMENT ON COLUMN sub_problem_results.user_id IS 'FK to users.id (denormalized for RLS).'"
    )

    # =====================
    # SESSION LIFECYCLE
    # =====================

    # Session Events
    op.execute(
        "COMMENT ON TABLE session_events IS 'SSE event log for session streaming. Partitioned by created_at.'"
    )
    op.execute("COMMENT ON COLUMN session_events.session_id IS 'FK to sessions.id.'")
    op.execute(
        "COMMENT ON COLUMN session_events.event_type IS 'Event type: contribution, synthesis, error, etc.'"
    )
    op.execute("COMMENT ON COLUMN session_events.data IS 'JSONB payload for the event.'")
    op.execute(
        "COMMENT ON COLUMN session_events.sequence IS 'Monotonic sequence number for ordering.'"
    )
    op.execute(
        "COMMENT ON COLUMN session_events.user_id IS 'FK to users.id (denormalized for RLS).'"
    )

    # Session Tasks
    op.execute("COMMENT ON TABLE session_tasks IS 'Extracted tasks from session synthesis.'")
    op.execute("COMMENT ON COLUMN session_tasks.session_id IS 'FK to sessions.id.'")
    op.execute("COMMENT ON COLUMN session_tasks.tasks IS 'JSONB: array of extracted task objects.'")
    op.execute("COMMENT ON COLUMN session_tasks.total_tasks IS 'Number of tasks extracted.'")
    op.execute(
        "COMMENT ON COLUMN session_tasks.extraction_confidence IS 'Confidence in task extraction quality.'"
    )
    op.execute(
        "COMMENT ON COLUMN session_tasks.sub_problem_index IS 'Which sub-problem generated these tasks.'"
    )
    op.execute(
        "COMMENT ON COLUMN session_tasks.task_statuses IS 'JSONB: status tracking per task.'"
    )

    # Session Kills
    op.execute("COMMENT ON TABLE session_kills IS 'Audit log for manually killed sessions.'")
    op.execute("COMMENT ON COLUMN session_kills.session_id IS 'FK to sessions.id.'")
    op.execute("COMMENT ON COLUMN session_kills.killed_by IS 'User ID or \"admin\".'")
    op.execute("COMMENT ON COLUMN session_kills.reason IS 'Kill reason provided by user/admin.'")
    op.execute("COMMENT ON COLUMN session_kills.cost_at_kill IS 'Cost at time of kill (USD).'")

    # Session Shares
    op.execute("COMMENT ON TABLE session_shares IS 'Public sharing links for sessions.'")
    op.execute("COMMENT ON COLUMN session_shares.session_id IS 'FK to sessions.id.'")
    op.execute("COMMENT ON COLUMN session_shares.token IS 'Unique token for public access.'")
    op.execute("COMMENT ON COLUMN session_shares.expires_at IS 'Link expiration timestamp.'")
    op.execute(
        "COMMENT ON COLUMN session_shares.created_by IS 'FK to users.id. Who created the share.'"
    )

    # Session Clarifications
    op.execute(
        "COMMENT ON TABLE session_clarifications IS 'User-provided clarifications during intake phase.'"
    )
    op.execute("COMMENT ON COLUMN session_clarifications.session_id IS 'FK to sessions.id.'")
    op.execute(
        "COMMENT ON COLUMN session_clarifications.question IS 'Clarification question asked by system.'"
    )
    op.execute("COMMENT ON COLUMN session_clarifications.answer IS 'User-provided answer.'")
    op.execute(
        "COMMENT ON COLUMN session_clarifications.asked_by_persona IS 'Persona that asked the question.'"
    )
    op.execute("COMMENT ON COLUMN session_clarifications.priority IS 'Question priority level.'")

    # =====================
    # ACTIONS & PROJECTS
    # =====================

    # Actions
    op.execute(
        "COMMENT ON TABLE actions IS 'User-actionable tasks derived from sessions or created manually.'"
    )
    op.execute("COMMENT ON COLUMN actions.id IS 'UUID action identifier.'")
    op.execute("COMMENT ON COLUMN actions.user_id IS 'FK to users.id. Owner of the action.'")
    op.execute(
        "COMMENT ON COLUMN actions.source_session_id IS 'FK to sessions.id. Source session (nullable).'"
    )
    op.execute(
        "COMMENT ON COLUMN actions.project_id IS 'FK to projects.id. Parent project (nullable).'"
    )
    op.execute("COMMENT ON COLUMN actions.title IS 'Action title.'")
    op.execute("COMMENT ON COLUMN actions.description IS 'Detailed description.'")
    op.execute(
        "COMMENT ON COLUMN actions.status IS 'Lifecycle: todo, in_progress, blocked, in_review, done, cancelled.'"
    )
    op.execute("COMMENT ON COLUMN actions.priority IS 'Priority: high, medium, low.'")
    op.execute(
        "COMMENT ON COLUMN actions.category IS 'Category: strategic, operational, research, communication.'"
    )
    op.execute("COMMENT ON COLUMN actions.target_end_date IS 'Target completion date.'")
    op.execute("COMMENT ON COLUMN actions.estimated_duration_days IS 'Estimated effort in days.'")
    op.execute("COMMENT ON COLUMN actions.progress_value IS 'Completion percentage 0-100.'")
    op.execute("COMMENT ON COLUMN actions.deleted_at IS 'Soft delete timestamp.'")

    # Action Dependencies
    op.execute(
        "COMMENT ON TABLE action_dependencies IS 'DAG edges between actions for dependency tracking.'"
    )
    op.execute(
        "COMMENT ON COLUMN action_dependencies.action_id IS 'FK to actions.id. The dependent action.'"
    )
    op.execute(
        "COMMENT ON COLUMN action_dependencies.depends_on_action_id IS 'FK to actions.id. The prerequisite action.'"
    )

    # Action Updates
    op.execute("COMMENT ON TABLE action_updates IS 'Progress updates/notes on actions.'")
    op.execute("COMMENT ON COLUMN action_updates.action_id IS 'FK to actions.id.'")
    op.execute("COMMENT ON COLUMN action_updates.content IS 'Update text.'")
    op.execute(
        "COMMENT ON COLUMN action_updates.update_type IS 'Type: progress, note, status_change, blocker.'"
    )
    op.execute("COMMENT ON COLUMN action_updates.user_id IS 'FK to users.id. Who made the update.'")

    # Tags & Action Tags
    op.execute("COMMENT ON TABLE tags IS 'User-defined tags for categorizing actions.'")
    op.execute("COMMENT ON COLUMN tags.user_id IS 'FK to users.id. Owner of the tag.'")
    op.execute("COMMENT ON COLUMN tags.name IS 'Tag name.'")
    op.execute("COMMENT ON COLUMN tags.color IS 'Hex color for display.'")

    op.execute("COMMENT ON TABLE action_tags IS 'Many-to-many join: actions <-> tags.'")
    op.execute("COMMENT ON COLUMN action_tags.action_id IS 'FK to actions.id.'")
    op.execute("COMMENT ON COLUMN action_tags.tag_id IS 'FK to tags.id.'")

    # Projects
    op.execute("COMMENT ON TABLE projects IS 'Project containers for grouping related actions.'")
    op.execute("COMMENT ON COLUMN projects.id IS 'UUID project identifier.'")
    op.execute("COMMENT ON COLUMN projects.user_id IS 'FK to users.id. Owner of the project.'")
    op.execute("COMMENT ON COLUMN projects.name IS 'Project name.'")
    op.execute("COMMENT ON COLUMN projects.description IS 'Project description.'")
    op.execute(
        "COMMENT ON COLUMN projects.status IS 'Lifecycle: active, paused, completed, archived.'"
    )

    # Session Projects
    op.execute("COMMENT ON TABLE session_projects IS 'Many-to-many join: sessions <-> projects.'")
    op.execute("COMMENT ON COLUMN session_projects.session_id IS 'FK to sessions.id.'")
    op.execute("COMMENT ON COLUMN session_projects.project_id IS 'FK to projects.id.'")

    # =====================
    # WORKSPACES
    # =====================

    # Workspaces
    op.execute("COMMENT ON TABLE workspaces IS 'Team workspaces for multi-user collaboration.'")
    op.execute("COMMENT ON COLUMN workspaces.id IS 'UUID workspace identifier.'")
    op.execute("COMMENT ON COLUMN workspaces.name IS 'Workspace name.'")
    op.execute("COMMENT ON COLUMN workspaces.owner_id IS 'FK to users.id. Workspace owner.'")

    # Workspace Members
    op.execute("COMMENT ON TABLE workspace_members IS 'Workspace membership with roles.'")
    op.execute("COMMENT ON COLUMN workspace_members.workspace_id IS 'FK to workspaces.id.'")
    op.execute("COMMENT ON COLUMN workspace_members.user_id IS 'FK to users.id.'")
    op.execute("COMMENT ON COLUMN workspace_members.role IS 'Role: owner, admin, member, viewer.'")
    op.execute(
        "COMMENT ON COLUMN workspace_members.invited_by IS 'FK to users.id. Who invited this member.'"
    )

    # Workspace Invitations
    op.execute(
        "COMMENT ON TABLE workspace_invitations IS 'Pending invitations to join workspaces.'"
    )
    op.execute("COMMENT ON COLUMN workspace_invitations.workspace_id IS 'FK to workspaces.id.'")
    op.execute("COMMENT ON COLUMN workspace_invitations.email IS 'Invitee email address.'")
    op.execute("COMMENT ON COLUMN workspace_invitations.role IS 'Role to assign on acceptance.'")
    op.execute("COMMENT ON COLUMN workspace_invitations.token IS 'Unique invitation token.'")
    op.execute(
        "COMMENT ON COLUMN workspace_invitations.expires_at IS 'Invitation expiration timestamp.'"
    )

    # Workspace Join Requests
    op.execute("COMMENT ON TABLE workspace_join_requests IS 'User requests to join workspaces.'")
    op.execute("COMMENT ON COLUMN workspace_join_requests.workspace_id IS 'FK to workspaces.id.'")
    op.execute("COMMENT ON COLUMN workspace_join_requests.user_id IS 'FK to users.id. Requestor.'")
    op.execute(
        "COMMENT ON COLUMN workspace_join_requests.status IS 'Status: pending, approved, rejected.'"
    )
    op.execute("COMMENT ON COLUMN workspace_join_requests.message IS 'Request message from user.'")

    # Workspace Role Changes
    op.execute("COMMENT ON TABLE workspace_role_changes IS 'Audit log for workspace role changes.'")
    op.execute("COMMENT ON COLUMN workspace_role_changes.workspace_id IS 'FK to workspaces.id.'")
    op.execute(
        "COMMENT ON COLUMN workspace_role_changes.user_id IS 'FK to users.id. Affected user.'"
    )
    op.execute(
        "COMMENT ON COLUMN workspace_role_changes.changed_by IS 'FK to users.id. Who made the change.'"
    )
    op.execute("COMMENT ON COLUMN workspace_role_changes.old_role IS 'Previous role.'")
    op.execute("COMMENT ON COLUMN workspace_role_changes.new_role IS 'New role.'")

    # =====================
    # USER CONTEXT & BUSINESS
    # =====================

    # User Context
    op.execute(
        "COMMENT ON TABLE user_context IS 'Business context for personalized deliberations.'"
    )
    op.execute("COMMENT ON COLUMN user_context.user_id IS 'FK to users.id.'")
    op.execute("COMMENT ON COLUMN user_context.company_name IS 'Company/organization name.'")
    op.execute("COMMENT ON COLUMN user_context.industry IS 'Industry sector.'")
    op.execute("COMMENT ON COLUMN user_context.team_size IS 'Team size.'")
    op.execute("COMMENT ON COLUMN user_context.north_star_goal IS 'Primary strategic objective.'")

    # Business Metrics
    op.execute("COMMENT ON TABLE business_metrics IS 'User-tracked business KPIs.'")
    op.execute("COMMENT ON COLUMN business_metrics.user_id IS 'FK to users.id.'")

    # Metric Templates
    op.execute("COMMENT ON TABLE metric_templates IS 'Predefined metric templates for onboarding.'")
    op.execute("COMMENT ON COLUMN metric_templates.metric_key IS 'Unique metric identifier.'")
    op.execute("COMMENT ON COLUMN metric_templates.name IS 'Metric display name.'")
    op.execute(
        "COMMENT ON COLUMN metric_templates.applies_to IS 'Which contexts this metric applies to.'"
    )

    # Industry Insights
    op.execute("COMMENT ON TABLE industry_insights IS 'AI-generated industry insights.'")
    op.execute("COMMENT ON COLUMN industry_insights.industry IS 'Industry sector.'")
    op.execute(
        "COMMENT ON COLUMN industry_insights.insight_type IS 'Type: trend, benchmark, opportunity, risk.'"
    )
    op.execute("COMMENT ON COLUMN industry_insights.content IS 'Insight text.'")

    # Competitor Profiles
    op.execute("COMMENT ON TABLE competitor_profiles IS 'User-defined competitor information.'")
    op.execute("COMMENT ON COLUMN competitor_profiles.user_id IS 'FK to users.id.'")
    op.execute("COMMENT ON COLUMN competitor_profiles.name IS 'Competitor company name.'")

    # =====================
    # DATASETS & ANALYSIS
    # =====================

    # Datasets
    op.execute("COMMENT ON TABLE datasets IS 'User-uploaded datasets for analysis.'")
    op.execute("COMMENT ON COLUMN datasets.id IS 'UUID dataset identifier.'")
    op.execute("COMMENT ON COLUMN datasets.user_id IS 'FK to users.id. Owner.'")
    op.execute("COMMENT ON COLUMN datasets.name IS 'Dataset name.'")
    op.execute("COMMENT ON COLUMN datasets.source_type IS 'Source: upload, google_sheets, api.'")
    op.execute("COMMENT ON COLUMN datasets.source_uri IS 'External source URL (Google Sheets).'")
    op.execute("COMMENT ON COLUMN datasets.file_key IS 'DO Spaces file key for uploaded files.'")
    op.execute("COMMENT ON COLUMN datasets.storage_path IS 'Full storage path.'")
    op.execute("COMMENT ON COLUMN datasets.row_count IS 'Number of rows in dataset.'")
    op.execute("COMMENT ON COLUMN datasets.column_count IS 'Number of columns.'")
    op.execute("COMMENT ON COLUMN datasets.file_size_bytes IS 'File size in bytes.'")
    op.execute("COMMENT ON COLUMN datasets.summary IS 'AI-generated dataset summary.'")
    op.execute(
        "COMMENT ON COLUMN datasets.workspace_id IS 'FK to workspaces.id. Workspace isolation.'"
    )
    op.execute("COMMENT ON COLUMN datasets.deleted_at IS 'Soft delete timestamp.'")

    # Dataset Profiles
    op.execute(
        "COMMENT ON TABLE dataset_profiles IS 'Column-level profiling results for datasets.'"
    )
    op.execute("COMMENT ON COLUMN dataset_profiles.dataset_id IS 'FK to datasets.id.'")
    op.execute("COMMENT ON COLUMN dataset_profiles.column_name IS 'Column name.'")

    # Dataset Analyses
    op.execute("COMMENT ON TABLE dataset_analyses IS 'AI analysis results for datasets.'")
    op.execute("COMMENT ON COLUMN dataset_analyses.dataset_id IS 'FK to datasets.id.'")

    # =====================
    # RESEARCH & CACHE
    # =====================

    # Research Cache
    op.execute("COMMENT ON TABLE research_cache IS 'Cached web research results.'")
    op.execute("COMMENT ON COLUMN research_cache.question IS 'Research question.'")
    op.execute(
        "COMMENT ON COLUMN research_cache.question_embedding IS 'vector(1536): Voyage embedding for similarity search.'"
    )
    op.execute("COMMENT ON COLUMN research_cache.answer_summary IS 'Summarized answer.'")
    op.execute("COMMENT ON COLUMN research_cache.sources IS 'JSONB: source URLs and metadata.'")

    # Research Metrics
    op.execute("COMMENT ON TABLE research_metrics IS 'Metrics for research operations.'")
    op.execute("COMMENT ON COLUMN research_metrics.query IS 'Search query.'")
    op.execute("COMMENT ON COLUMN research_metrics.cached IS 'Whether result was from cache.'")

    # =====================
    # COST TRACKING
    # =====================

    # API Costs
    op.execute("COMMENT ON TABLE api_costs IS 'LLM API cost records. Partitioned by created_at.'")
    op.execute(
        "COMMENT ON COLUMN api_costs.session_id IS 'FK to sessions.id (nullable for non-session calls).'"
    )
    op.execute("COMMENT ON COLUMN api_costs.user_id IS 'FK to users.id.'")
    op.execute(
        "COMMENT ON COLUMN api_costs.model_name IS 'LLM model: claude-sonnet-4-20250514, etc.'"
    )
    op.execute("COMMENT ON COLUMN api_costs.provider IS 'Provider: anthropic, openai, voyage.'")
    op.execute("COMMENT ON COLUMN api_costs.input_tokens IS 'Input token count.'")
    op.execute("COMMENT ON COLUMN api_costs.output_tokens IS 'Output token count.'")
    op.execute("COMMENT ON COLUMN api_costs.total_cost IS 'Calculated total cost in USD.'")
    op.execute(
        "COMMENT ON COLUMN api_costs.operation_type IS 'Operation category: persona, synthesis, research, etc.'"
    )
    op.execute(
        "COMMENT ON COLUMN api_costs.cache_creation_tokens IS 'Anthropic cache creation tokens.'"
    )
    op.execute(
        "COMMENT ON COLUMN api_costs.cache_read_tokens IS 'Anthropic cache read tokens (5% cost).'"
    )
    op.execute("COMMENT ON COLUMN api_costs.sub_problem_index IS 'Which sub-problem (0-indexed).'")
    op.execute("COMMENT ON COLUMN api_costs.metadata IS 'JSONB: additional cost metadata.'")

    # Daily Cost Summary
    op.execute("COMMENT ON TABLE daily_cost_summary IS 'Aggregated daily costs.'")
    op.execute("COMMENT ON COLUMN daily_cost_summary.date IS 'Summary date.'")
    op.execute("COMMENT ON COLUMN daily_cost_summary.provider IS 'Cost provider.'")
    op.execute("COMMENT ON COLUMN daily_cost_summary.category IS 'Cost category.'")
    op.execute("COMMENT ON COLUMN daily_cost_summary.amount_usd IS 'Total cost for the day (USD).'")

    # Fixed Costs
    op.execute("COMMENT ON TABLE fixed_costs IS 'Monthly fixed infrastructure costs.'")
    op.execute("COMMENT ON COLUMN fixed_costs.provider IS 'Provider name.'")
    op.execute("COMMENT ON COLUMN fixed_costs.monthly_amount_usd IS 'Monthly cost amount (USD).'")
    op.execute("COMMENT ON COLUMN fixed_costs.category IS 'Category: hosting, storage, services.'")

    # User Usage
    op.execute("COMMENT ON TABLE user_usage IS 'Daily usage tracking per user for billing caps.'")
    op.execute("COMMENT ON COLUMN user_usage.user_id IS 'FK to users.id.'")

    # =====================
    # BILLING & PROMOTIONS
    # =====================

    # Promotions
    op.execute("COMMENT ON TABLE promotions IS 'Promotional codes and discounts.'")
    op.execute("COMMENT ON COLUMN promotions.code IS 'Promo code (unique).'")
    op.execute("COMMENT ON COLUMN promotions.type IS 'Type: percent, fixed, sessions.'")
    op.execute("COMMENT ON COLUMN promotions.value IS 'Discount amount.'")
    op.execute("COMMENT ON COLUMN promotions.max_uses IS 'Maximum total redemptions.'")
    op.execute("COMMENT ON COLUMN promotions.uses_count IS 'Current redemption count.'")
    op.execute("COMMENT ON COLUMN promotions.expires_at IS 'Promo end date.'")

    # User Promotions
    op.execute("COMMENT ON TABLE user_promotions IS 'Promo redemptions per user.'")
    op.execute("COMMENT ON COLUMN user_promotions.user_id IS 'FK to users.id.'")
    op.execute("COMMENT ON COLUMN user_promotions.promotion_id IS 'FK to promotions.id.'")

    # Promo Invoice Applications
    op.execute("COMMENT ON TABLE promo_invoice_applications IS 'Promo applied to Stripe invoices.'")
    op.execute(
        "COMMENT ON COLUMN promo_invoice_applications.user_promotion_id IS 'FK to user_promotions.id.'"
    )
    op.execute(
        "COMMENT ON COLUMN promo_invoice_applications.stripe_invoice_id IS 'Stripe invoice ID.'"
    )

    # Stripe Events
    op.execute("COMMENT ON TABLE stripe_events IS 'Processed Stripe webhook events (idempotency).'")
    op.execute("COMMENT ON COLUMN stripe_events.event_id IS 'Stripe event ID (unique).'")
    op.execute("COMMENT ON COLUMN stripe_events.event_type IS 'Stripe event type.'")

    # Conversion Events
    op.execute("COMMENT ON TABLE conversion_events IS 'User conversion funnel events.'")
    op.execute(
        "COMMENT ON COLUMN conversion_events.event_type IS 'Event: signup, first_session, subscription, etc.'"
    )
    op.execute("COMMENT ON COLUMN conversion_events.session_id IS 'Analytics session ID.'")
    op.execute("COMMENT ON COLUMN conversion_events.metadata IS 'JSONB: event metadata.'")

    # =====================
    # ADMIN & AUDIT
    # =====================

    # Admin Impersonation Sessions
    op.execute(
        "COMMENT ON TABLE admin_impersonation_sessions IS 'Admin user impersonation audit log.'"
    )
    op.execute(
        "COMMENT ON COLUMN admin_impersonation_sessions.admin_user_id IS 'FK to users.id. Admin who impersonated.'"
    )
    op.execute(
        "COMMENT ON COLUMN admin_impersonation_sessions.target_user_id IS 'FK to users.id. User being impersonated.'"
    )
    op.execute(
        "COMMENT ON COLUMN admin_impersonation_sessions.reason IS 'Reason for impersonation.'"
    )

    # Audit Log
    op.execute("COMMENT ON TABLE audit_log IS 'General audit log for security and compliance.'")
    op.execute(
        "COMMENT ON COLUMN audit_log.user_id IS 'FK to users.id (nullable for system events).'"
    )
    op.execute("COMMENT ON COLUMN audit_log.action IS 'Action: session_created, user_login, etc.'")
    op.execute(
        "COMMENT ON COLUMN audit_log.resource_type IS 'Resource type: session, user, action.'"
    )
    op.execute("COMMENT ON COLUMN audit_log.resource_id IS 'Resource identifier.'")
    op.execute("COMMENT ON COLUMN audit_log.details IS 'JSONB: action details.'")

    # API Audit Log
    op.execute("COMMENT ON TABLE api_audit_log IS 'API request audit log for debugging.'")
    op.execute("COMMENT ON COLUMN api_audit_log.user_id IS 'FK to users.id.'")
    op.execute("COMMENT ON COLUMN api_audit_log.method IS 'HTTP method: GET, POST, etc.'")
    op.execute("COMMENT ON COLUMN api_audit_log.path IS 'Request path.'")

    # GDPR Audit Log
    op.execute("COMMENT ON TABLE gdpr_audit_log IS 'GDPR compliance audit log.'")
    op.execute("COMMENT ON COLUMN gdpr_audit_log.user_id IS 'FK to users.id.'")
    op.execute(
        "COMMENT ON COLUMN gdpr_audit_log.action IS 'Action: export_requested, deletion_requested, etc.'"
    )

    # Alert History
    op.execute("COMMENT ON TABLE alert_history IS 'Sent alert history (ntfy, email).'")
    op.execute(
        "COMMENT ON COLUMN alert_history.alert_type IS 'Alert type: session_failed, cost_anomaly, etc.'"
    )
    op.execute(
        "COMMENT ON COLUMN alert_history.severity IS 'Severity: info, warning, error, critical.'"
    )
    op.execute("COMMENT ON COLUMN alert_history.message IS 'Alert message.'")
    op.execute("COMMENT ON COLUMN alert_history.metadata IS 'JSONB: alert metadata.'")

    # =====================
    # ERROR HANDLING & AUTO-REMEDIATION
    # =====================

    # Error Patterns
    op.execute("COMMENT ON TABLE error_patterns IS 'Detected error patterns for auto-remediation.'")
    op.execute("COMMENT ON COLUMN error_patterns.pattern_name IS 'Pattern name.'")
    op.execute("COMMENT ON COLUMN error_patterns.pattern_regex IS 'Regex to match error messages.'")
    op.execute(
        "COMMENT ON COLUMN error_patterns.severity IS 'Severity: low, medium, high, critical.'"
    )

    # Error Fixes
    op.execute("COMMENT ON TABLE error_fixes IS 'Applied error fixes.'")
    op.execute("COMMENT ON COLUMN error_fixes.error_pattern_id IS 'FK to error_patterns.id.'")
    op.execute("COMMENT ON COLUMN error_fixes.fix_type IS 'Type of fix applied.'")

    # Auto-remediation Log
    op.execute("COMMENT ON TABLE auto_remediation_log IS 'Log of automatic remediation actions.'")
    op.execute(
        "COMMENT ON COLUMN auto_remediation_log.error_pattern_id IS 'FK to error_patterns.id.'"
    )
    op.execute(
        "COMMENT ON COLUMN auto_remediation_log.outcome IS 'Outcome: success, failed, partial.'"
    )

    # =====================
    # EMAIL & COMMUNICATIONS
    # =====================

    # Email Log
    op.execute("COMMENT ON TABLE email_log IS 'Sent email audit log (Resend).'")
    op.execute(
        "COMMENT ON COLUMN email_log.email_type IS 'Type: welcome, meeting_complete, weekly_digest, etc.'"
    )
    op.execute("COMMENT ON COLUMN email_log.recipient IS 'Email recipient address.'")
    op.execute("COMMENT ON COLUMN email_log.resend_id IS 'Resend message ID.'")
    op.execute("COMMENT ON COLUMN email_log.status IS 'Status: sent, delivered, bounced, failed.'")

    # =====================
    # USER ONBOARDING & FEEDBACK
    # =====================

    # User Onboarding
    op.execute("COMMENT ON TABLE user_onboarding IS 'User onboarding progress tracking.'")
    op.execute("COMMENT ON COLUMN user_onboarding.user_id IS 'FK to users.id.'")
    op.execute(
        "COMMENT ON COLUMN user_onboarding.tour_completed IS 'Whether onboarding tour was completed.'"
    )
    op.execute(
        "COMMENT ON COLUMN user_onboarding.steps_completed IS 'JSONB: list of completed steps.'"
    )

    # Feedback
    op.execute("COMMENT ON TABLE feedback IS 'User feedback submissions.'")
    op.execute("COMMENT ON COLUMN feedback.user_id IS 'FK to users.id.'")
    op.execute("COMMENT ON COLUMN feedback.type IS 'Type: bug, feature, general.'")
    op.execute("COMMENT ON COLUMN feedback.description IS 'Feedback text.'")
    op.execute("COMMENT ON COLUMN feedback.analysis IS 'JSONB: AI analysis of feedback.'")

    # =====================
    # CONTENT & ANALYTICS
    # =====================

    # Blog Posts
    op.execute("COMMENT ON TABLE blog_posts IS 'AI-generated SEO blog posts.'")
    op.execute("COMMENT ON COLUMN blog_posts.slug IS 'URL slug (unique).'")
    op.execute("COMMENT ON COLUMN blog_posts.title IS 'Post title.'")
    op.execute("COMMENT ON COLUMN blog_posts.content IS 'Post HTML content.'")
    op.execute("COMMENT ON COLUMN blog_posts.meta_description IS 'SEO meta description.'")
    op.execute("COMMENT ON COLUMN blog_posts.status IS 'Status: draft, scheduled, published.'")
    op.execute("COMMENT ON COLUMN blog_posts.published_at IS 'Publish timestamp.'")
    op.execute("COMMENT ON COLUMN blog_posts.seo_keywords IS 'JSONB: SEO keywords.'")

    # Page Views
    op.execute("COMMENT ON TABLE page_views IS 'Page view analytics. Partitioned by created_at.'")
    op.execute("COMMENT ON COLUMN page_views.path IS 'Page path.'")
    op.execute("COMMENT ON COLUMN page_views.referrer IS 'Referrer URL.'")
    op.execute("COMMENT ON COLUMN page_views.session_id IS 'Analytics session ID.'")

    # =====================
    # ACCESS CONTROL
    # =====================

    # Waitlist
    op.execute("COMMENT ON TABLE waitlist IS 'Beta waitlist signups.'")
    op.execute("COMMENT ON COLUMN waitlist.email IS 'Signup email address.'")
    op.execute("COMMENT ON COLUMN waitlist.status IS 'Status: pending, approved, rejected.'")
    op.execute("COMMENT ON COLUMN waitlist.source IS 'How user found Bo1.'")

    # Beta Whitelist
    op.execute("COMMENT ON TABLE beta_whitelist IS 'Approved beta access emails.'")
    op.execute("COMMENT ON COLUMN beta_whitelist.email IS 'Whitelisted email address.'")


def downgrade() -> None:
    """Remove COMMENT statements from tables and columns."""
    # Note: PostgreSQL doesn't have a clean way to remove comments.
    # Setting to NULL effectively removes them.

    # Core tables
    op.execute("COMMENT ON TABLE users IS NULL")
    op.execute("COMMENT ON TABLE sessions IS NULL")
    op.execute("COMMENT ON TABLE contributions IS NULL")
    op.execute("COMMENT ON TABLE recommendations IS NULL")
    op.execute("COMMENT ON TABLE personas IS NULL")
    op.execute("COMMENT ON TABLE facilitator_decisions IS NULL")
    op.execute("COMMENT ON TABLE sub_problem_results IS NULL")

    # Session lifecycle
    op.execute("COMMENT ON TABLE session_events IS NULL")
    op.execute("COMMENT ON TABLE session_tasks IS NULL")
    op.execute("COMMENT ON TABLE session_kills IS NULL")
    op.execute("COMMENT ON TABLE session_shares IS NULL")
    op.execute("COMMENT ON TABLE session_clarifications IS NULL")

    # Actions & Projects
    op.execute("COMMENT ON TABLE actions IS NULL")
    op.execute("COMMENT ON TABLE action_dependencies IS NULL")
    op.execute("COMMENT ON TABLE action_updates IS NULL")
    op.execute("COMMENT ON TABLE tags IS NULL")
    op.execute("COMMENT ON TABLE action_tags IS NULL")
    op.execute("COMMENT ON TABLE projects IS NULL")
    op.execute("COMMENT ON TABLE session_projects IS NULL")

    # Workspaces
    op.execute("COMMENT ON TABLE workspaces IS NULL")
    op.execute("COMMENT ON TABLE workspace_members IS NULL")
    op.execute("COMMENT ON TABLE workspace_invitations IS NULL")
    op.execute("COMMENT ON TABLE workspace_join_requests IS NULL")
    op.execute("COMMENT ON TABLE workspace_role_changes IS NULL")

    # User context & business
    op.execute("COMMENT ON TABLE user_context IS NULL")
    op.execute("COMMENT ON TABLE business_metrics IS NULL")
    op.execute("COMMENT ON TABLE metric_templates IS NULL")
    op.execute("COMMENT ON TABLE industry_insights IS NULL")
    op.execute("COMMENT ON TABLE competitor_profiles IS NULL")

    # Datasets & analysis
    op.execute("COMMENT ON TABLE datasets IS NULL")
    op.execute("COMMENT ON TABLE dataset_profiles IS NULL")
    op.execute("COMMENT ON TABLE dataset_analyses IS NULL")

    # Research & cache
    op.execute("COMMENT ON TABLE research_cache IS NULL")
    op.execute("COMMENT ON TABLE research_metrics IS NULL")

    # Cost tracking
    op.execute("COMMENT ON TABLE api_costs IS NULL")
    op.execute("COMMENT ON TABLE daily_cost_summary IS NULL")
    op.execute("COMMENT ON TABLE fixed_costs IS NULL")
    op.execute("COMMENT ON TABLE user_usage IS NULL")

    # Billing & promotions
    op.execute("COMMENT ON TABLE promotions IS NULL")
    op.execute("COMMENT ON TABLE user_promotions IS NULL")
    op.execute("COMMENT ON TABLE promo_invoice_applications IS NULL")
    op.execute("COMMENT ON TABLE stripe_events IS NULL")
    op.execute("COMMENT ON TABLE conversion_events IS NULL")

    # Admin & audit
    op.execute("COMMENT ON TABLE admin_impersonation_sessions IS NULL")
    op.execute("COMMENT ON TABLE audit_log IS NULL")
    op.execute("COMMENT ON TABLE api_audit_log IS NULL")
    op.execute("COMMENT ON TABLE gdpr_audit_log IS NULL")
    op.execute("COMMENT ON TABLE alert_history IS NULL")

    # Error handling
    op.execute("COMMENT ON TABLE error_patterns IS NULL")
    op.execute("COMMENT ON TABLE error_fixes IS NULL")
    op.execute("COMMENT ON TABLE auto_remediation_log IS NULL")

    # Email
    op.execute("COMMENT ON TABLE email_log IS NULL")

    # User onboarding & feedback
    op.execute("COMMENT ON TABLE user_onboarding IS NULL")
    op.execute("COMMENT ON TABLE feedback IS NULL")

    # Content & analytics
    op.execute("COMMENT ON TABLE blog_posts IS NULL")
    op.execute("COMMENT ON TABLE page_views IS NULL")

    # Access control
    op.execute("COMMENT ON TABLE waitlist IS NULL")
    op.execute("COMMENT ON TABLE beta_whitelist IS NULL")
