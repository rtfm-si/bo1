"""Consolidated baseline schema.

This migration creates the complete database schema in a single operation.
Use this for NEW deployments only. Existing deployments should use the
incremental migration chain.

To use this baseline for fresh deployments:
    alembic stamp 0001_consolidated_baseline
    alembic upgrade head  # Apply any post-baseline migrations

Revision ID: 0001_consolidated_baseline
Revises:
Create Date: 2025-12-09
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_consolidated_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("consolidated",)
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create complete schema from consolidated baseline SQL."""
    # Load and execute the consolidated schema SQL
    schema_path = Path(__file__).parent.parent / "consolidated_baseline.sql"
    schema_sql = schema_path.read_text()

    # Execute the schema SQL
    op.execute(schema_sql)

    # Ensure partitions exist for current date range
    # The create_next_month_partitions function handles this
    op.execute("SELECT create_next_month_partitions()")


def downgrade() -> None:
    """Drop all application tables.

    WARNING: This will delete all data. Only use in development.
    """
    # Drop in reverse dependency order
    op.execute("""
        -- Drop RLS policies first
        DROP POLICY IF EXISTS waitlist_admin_only ON waitlist;
        DROP POLICY IF EXISTS users_system_insert ON users;
        DROP POLICY IF EXISTS users_self_update ON users;
        DROP POLICY IF EXISTS users_self_access ON users;
        DROP POLICY IF EXISTS user_onboarding_own_data ON user_onboarding;
        DROP POLICY IF EXISTS sessions_user_isolation ON sessions;
        DROP POLICY IF EXISTS session_tasks_user_isolation ON session_tasks;
        DROP POLICY IF EXISTS session_tasks_admin_access ON session_tasks;
        DROP POLICY IF EXISTS session_events_user_isolation ON session_events;
        DROP POLICY IF EXISTS session_events_admin_access ON session_events;
        DROP POLICY IF EXISTS industry_insights_write_system ON industry_insights;
        DROP POLICY IF EXISTS industry_insights_read_all ON industry_insights;
        DROP POLICY IF EXISTS facilitator_decisions_user_isolation ON facilitator_decisions;
        DROP POLICY IF EXISTS facilitator_decisions_admin_access ON facilitator_decisions;
        DROP POLICY IF EXISTS contributions_user_isolation ON contributions;
        DROP POLICY IF EXISTS contributions_admin_access ON contributions;
        DROP POLICY IF EXISTS competitor_profiles_own_data ON competitor_profiles;
        DROP POLICY IF EXISTS business_metrics_own_data ON business_metrics;
        DROP POLICY IF EXISTS audit_log_user_isolation ON audit_log;
        DROP POLICY IF EXISTS api_costs_user_isolation ON api_costs;
        DROP POLICY IF EXISTS api_costs_admin_access ON api_costs;

        -- Drop materialized views
        DROP MATERIALIZED VIEW IF EXISTS session_cost_summary CASCADE;
        DROP VIEW IF EXISTS user_metrics CASCADE;

        -- Drop tables (partitioned tables drop their partitions automatically)
        DROP TABLE IF EXISTS action_tags CASCADE;
        DROP TABLE IF EXISTS action_dependencies CASCADE;
        DROP TABLE IF EXISTS action_updates CASCADE;
        DROP TABLE IF EXISTS actions CASCADE;
        DROP TABLE IF EXISTS tags CASCADE;
        DROP TABLE IF EXISTS session_projects CASCADE;
        DROP TABLE IF EXISTS projects CASCADE;
        DROP TABLE IF EXISTS api_costs CASCADE;
        DROP TABLE IF EXISTS contributions CASCADE;
        DROP TABLE IF EXISTS session_events CASCADE;
        DROP TABLE IF EXISTS session_tasks CASCADE;
        DROP TABLE IF EXISTS sub_problem_results CASCADE;
        DROP TABLE IF EXISTS recommendations CASCADE;
        DROP TABLE IF EXISTS facilitator_decisions CASCADE;
        DROP TABLE IF EXISTS session_clarifications CASCADE;
        DROP TABLE IF EXISTS sessions CASCADE;
        DROP TABLE IF EXISTS personas CASCADE;
        DROP TABLE IF EXISTS research_metrics CASCADE;
        DROP TABLE IF EXISTS research_cache CASCADE;
        DROP TABLE IF EXISTS user_context CASCADE;
        DROP TABLE IF EXISTS user_onboarding CASCADE;
        DROP TABLE IF EXISTS business_metrics CASCADE;
        DROP TABLE IF EXISTS metric_templates CASCADE;
        DROP TABLE IF EXISTS industry_insights CASCADE;
        DROP TABLE IF EXISTS competitor_profiles CASCADE;
        DROP TABLE IF EXISTS beta_whitelist CASCADE;
        DROP TABLE IF EXISTS waitlist CASCADE;
        DROP TABLE IF EXISTS audit_log CASCADE;
        DROP TABLE IF EXISTS users CASCADE;

        -- Drop functions
        DROP FUNCTION IF EXISTS create_next_month_partitions() CASCADE;
        DROP FUNCTION IF EXISTS list_partitions(text) CASCADE;
        DROP FUNCTION IF EXISTS partition_sizes(text) CASCADE;
        DROP FUNCTION IF EXISTS refresh_session_cost_summary() CASCADE;
        DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

        -- Drop types
        DROP TYPE IF EXISTS aal_level CASCADE;
        DROP TYPE IF EXISTS code_challenge_method CASCADE;
        DROP TYPE IF EXISTS factor_status CASCADE;
        DROP TYPE IF EXISTS factor_type CASCADE;
        DROP TYPE IF EXISTS one_time_token_type CASCADE;

        -- Drop extension
        DROP EXTENSION IF EXISTS vector CASCADE;
    """)
