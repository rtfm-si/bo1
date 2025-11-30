"""add_composite_indexes_performance

Add comprehensive composite indexes to optimize common query patterns.
Significant performance improvement for user-scoped and time-based queries.

Indexes created:
- api_costs: user+created_at, session+node (for cost analytics)
- contributions: persona_code, session+persona, created_at (for contribution analysis)
- recommendations: persona_code, session+persona (for voting analysis)
- research_cache: category+date (for research hit rate)
- research_metrics: depth+success (for research analytics)
- sub_problem_results: session+created_at (for timeline views)

Revision ID: b233c4ff7a14
Revises: 074cc4d875b0
Create Date: 2025-11-30 21:28:38.565771

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b233c4ff7a14"
down_revision: str | Sequence[str] | None = "074cc4d875b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # All indexes are created with idempotent SQL (IF NOT EXISTS)
    # This allows migrations to run even if tables don't exist yet

    # api_costs indexes - optimized for user analytics and cost tracking
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_costs_user_created
        ON api_costs (user_id, created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_costs_session_node
        ON api_costs (session_id, node_name)
    """)

    # contributions indexes - optimized for persona analytics
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contributions_persona_code
        ON contributions (persona_code)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contributions_session_persona
        ON contributions (session_id, persona_code)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contributions_created_at
        ON contributions (created_at DESC)
    """)

    # recommendations indexes - optimized for voting analysis
    # Only create if table exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'recommendations') THEN
                CREATE INDEX IF NOT EXISTS idx_recommendations_persona_code
                ON recommendations (persona_code);

                CREATE INDEX IF NOT EXISTS idx_recommendations_session_persona
                ON recommendations (session_id, persona_code);
            END IF;
        END $$;
    """)

    # research_cache indexes - optimized for cache hit analysis
    # Only create if table exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'research_cache') THEN
                CREATE INDEX IF NOT EXISTS idx_research_cache_category_date
                ON research_cache (category, research_date DESC);
            END IF;
        END $$;
    """)

    # research_metrics indexes - optimized for research analytics
    # Only create if table exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'research_metrics') THEN
                CREATE INDEX IF NOT EXISTS idx_research_metrics_depth_success
                ON research_metrics (research_depth, success);
            END IF;
        END $$;
    """)

    # sub_problem_results indexes - optimized for timeline views
    # Only create if table exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sub_problem_results') THEN
                CREATE INDEX IF NOT EXISTS idx_sub_problem_results_created_at
                ON sub_problem_results (session_id, created_at DESC);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes in reverse order
    op.drop_index("idx_sub_problem_results_created_at", table_name="sub_problem_results")

    # Drop research_metrics index if it exists
    op.execute("DROP INDEX IF EXISTS idx_research_metrics_depth_success")

    op.drop_index("idx_research_cache_category_date", table_name="research_cache")
    op.drop_index("idx_recommendations_session_persona", table_name="recommendations")
    op.drop_index("idx_recommendations_persona_code", table_name="recommendations")
    op.drop_index("idx_contributions_created_at", table_name="contributions")
    op.drop_index("idx_contributions_session_persona", table_name="contributions")
    op.drop_index("idx_contributions_persona_code", table_name="contributions")
    op.drop_index("idx_api_costs_session_node", table_name="api_costs")
    op.drop_index("idx_api_costs_user_created", table_name="api_costs")
