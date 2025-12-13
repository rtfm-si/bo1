"""Add usage tracking tables and tier override field.

This migration adds:
- user_usage table for persistent usage tracking
- tier_override JSONB column on users for admin overrides

Revision ID: ag1_add_usage_tracking
Revises: z3_add_session_termination
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ag1_add_usage_tracking"
down_revision: str | Sequence[str] | None = "z3_add_session_termination"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add usage tracking infrastructure."""
    # Create user_usage table for persistent monthly rollups
    op.create_table(
        "user_usage",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("period", sa.String(length=10), nullable=False),  # YYYY-MM or YYYY-MM-DD
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
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

    # Unique constraint for upsert operations
    op.create_unique_constraint(
        "uq_user_usage_user_metric_period",
        "user_usage",
        ["user_id", "metric", "period"],
    )

    # Index for fast user lookups
    op.create_index("ix_user_usage_user_id", "user_usage", ["user_id"])

    # Index for period-based queries (cleanup, reporting)
    op.create_index("ix_user_usage_period", "user_usage", ["period"])

    # Add tier_override JSONB column to users table
    # Structure: {"tier": "pro", "expires_at": "2025-01-01T00:00:00Z", "reason": "beta tester"}
    op.add_column(
        "users",
        sa.Column("tier_override", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    """Remove usage tracking infrastructure."""
    # Remove tier_override from users
    op.drop_column("users", "tier_override")

    # Drop user_usage table
    op.drop_index("ix_user_usage_period", table_name="user_usage")
    op.drop_index("ix_user_usage_user_id", table_name="user_usage")
    op.drop_constraint("uq_user_usage_user_metric_period", "user_usage", type_="unique")
    op.drop_table("user_usage")
