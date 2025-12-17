"""Add cost tracking infrastructure.

Creates:
- daily_cost_summary: Aggregated daily costs by provider/category
- fixed_costs: Fixed infrastructure costs (DO, Redis, etc.)
- Composite index on api_costs(session_id, created_at) for meeting attribution

Revision ID: z7_add_cost_tracking
Revises: z6_add_north_star_goal
Create Date: 2025-12-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z7_add_cost_tracking"
down_revision: str | Sequence[str] | None = "z6_add_north_star_goal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add cost tracking tables and indexes."""
    # ==========================================================================
    # 1. daily_cost_summary: Pre-aggregated daily costs by provider
    # ==========================================================================
    op.create_table(
        "daily_cost_summary",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Provider: anthropic, voyage, brave, tavily, digitalocean, resend",
        ),
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            comment="Category: llm_inference, embeddings, search, email, storage, compute",
        ),
        sa.Column(
            "amount_usd",
            sa.Numeric(precision=12, scale=6),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "request_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "provider", "category", name="uq_daily_cost_summary"),
    )

    # Index for date range queries
    op.create_index(
        "idx_daily_cost_summary_date",
        "daily_cost_summary",
        ["date"],
        postgresql_using="btree",
    )

    # Index for provider filtering
    op.create_index(
        "idx_daily_cost_summary_provider",
        "daily_cost_summary",
        ["provider"],
    )

    # ==========================================================================
    # 2. fixed_costs: Fixed infrastructure costs
    # ==========================================================================
    op.create_table(
        "fixed_costs",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Provider: digitalocean, redis_labs, neon, resend, etc.",
        ),
        sa.Column(
            "description",
            sa.String(200),
            nullable=False,
            comment="Description: DO Droplet, DO Spaces, Managed Redis, etc.",
        ),
        sa.Column(
            "monthly_amount_usd",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            server_default="compute",
            comment="Category: compute, storage, database, email, monitoring",
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for active costs
    op.create_index(
        "idx_fixed_costs_active",
        "fixed_costs",
        ["active"],
        postgresql_where=sa.text("active = true"),
    )

    # ==========================================================================
    # 3. Composite index on api_costs for meeting cost attribution
    # ==========================================================================
    # This index optimizes queries that group costs by session and time range
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_api_costs_session_created
        ON api_costs (session_id, created_at DESC)
        WHERE session_id IS NOT NULL
    """)

    # ==========================================================================
    # 4. Add comments
    # ==========================================================================
    op.execute("""
        COMMENT ON TABLE daily_cost_summary IS
        'Pre-aggregated daily API costs by provider and category for analytics';
    """)
    op.execute("""
        COMMENT ON TABLE fixed_costs IS
        'Fixed infrastructure costs (compute, storage, etc.) for total cost calculation';
    """)


def downgrade() -> None:
    """Remove cost tracking tables and indexes."""
    # Drop index on api_costs
    op.execute("DROP INDEX IF EXISTS idx_api_costs_session_created")

    # Drop fixed_costs table
    op.drop_index("idx_fixed_costs_active", table_name="fixed_costs")
    op.drop_table("fixed_costs")

    # Drop daily_cost_summary table
    op.drop_index("idx_daily_cost_summary_provider", table_name="daily_cost_summary")
    op.drop_index("idx_daily_cost_summary_date", table_name="daily_cost_summary")
    op.drop_table("daily_cost_summary")
