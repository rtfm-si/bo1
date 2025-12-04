"""Add industry_insights table for cross-user intelligence.

Phase 4 of ACCOUNT_CONTEXT_PLAN - Cross-User Intelligence.

This table stores aggregated, anonymized industry insights that can benefit
all users. Includes:
- Market trends by industry
- Benchmark metrics (aggregated from user data)
- Competitor intelligence (shared with consent)
- Best practices

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2025-12-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "e4f5g6h7i8j9"
down_revision: str | Sequence[str] | None = "d3e4f5g6h7i8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create industry_insights table for cross-user intelligence."""
    # ==========================================================================
    # Create industry_insights table
    # ==========================================================================
    op.create_table(
        "industry_insights",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("industry", sa.String(100), nullable=False, index=True),
        sa.Column(
            "insight_type",
            sa.String(50),
            nullable=False,
            comment="trend, benchmark, competitor, best_practice",
        ),
        sa.Column(
            "content",
            JSONB,
            nullable=False,
            comment="Structured insight data varies by type",
        ),
        # Embedding for semantic search (optional, for future use)
        # Using pgvector VECTOR type - ensure pgvector extension is enabled
        # sa.Column("embedding", sa.ARRAY(sa.Float), nullable=True),
        sa.Column(
            "source_count",
            sa.Integer,
            server_default="1",
            nullable=False,
            comment="Number of users contributing to this insight",
        ),
        sa.Column(
            "confidence",
            sa.Numeric(3, 2),
            server_default="0.50",
            nullable=False,
            comment="Aggregated confidence score 0.00-1.00",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When this insight expires (trends expire, benchmarks refresh quarterly)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Add check constraint for insight_type
    op.create_check_constraint(
        "industry_insights_type_check",
        "industry_insights",
        "insight_type IN ('trend', 'benchmark', 'competitor', 'best_practice')",
    )

    # Add index for type + industry queries
    op.create_index(
        "idx_industry_insights_type_industry",
        "industry_insights",
        ["insight_type", "industry"],
    )

    # Add index for finding insights (with optional expiration filter in queries)
    op.create_index(
        "idx_industry_insights_active",
        "industry_insights",
        ["industry", "insight_type", "expires_at"],
    )

    # Enable RLS (public read, admin write)
    op.execute("ALTER TABLE industry_insights ENABLE ROW LEVEL SECURITY")

    # RLS policy - all authenticated users can read
    op.execute("""
        CREATE POLICY industry_insights_read_all ON industry_insights
        FOR SELECT
        USING (true);
    """)

    # RLS policy - only system/admin can write (via service role)
    # This ensures insights are only created through aggregation jobs
    op.execute("""
        CREATE POLICY industry_insights_write_system ON industry_insights
        FOR ALL
        USING (current_setting('app.current_user_role', true) = 'admin')
        WITH CHECK (current_setting('app.current_user_role', true) = 'admin');
    """)


def downgrade() -> None:
    """Drop industry_insights table."""
    op.execute("DROP POLICY IF EXISTS industry_insights_write_system ON industry_insights")
    op.execute("DROP POLICY IF EXISTS industry_insights_read_all ON industry_insights")
    op.drop_index("idx_industry_insights_active", table_name="industry_insights")
    op.drop_index("idx_industry_insights_type_industry", table_name="industry_insights")
    op.drop_constraint("industry_insights_type_check", "industry_insights", type_="check")
    op.drop_table("industry_insights")
