"""Add research_metrics table.

Revision ID: 001_research_metrics
Revises: f23423398b2a
Create Date: 2025-11-25 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_research_metrics"
down_revision: str | None = "f23423398b2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add research_metrics table for tracking research success rate."""
    op.create_table(
        "research_metrics",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("research_depth", sa.String(10), nullable=False),
        sa.Column("keywords_matched", sa.Text(), nullable=True),  # JSON array as text
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sources_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("response_time_ms", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add indexes for common queries
    op.create_index(
        "idx_research_metrics_timestamp",
        "research_metrics",
        ["timestamp"],
        postgresql_using="btree",
    )
    op.create_index(
        "idx_research_metrics_depth",
        "research_metrics",
        ["research_depth"],
        postgresql_using="btree",
    )
    op.create_index(
        "idx_research_metrics_success", "research_metrics", ["success"], postgresql_using="btree"
    )


def downgrade() -> None:
    """Remove research_metrics table."""
    op.drop_index("idx_research_metrics_success", table_name="research_metrics")
    op.drop_index("idx_research_metrics_depth", table_name="research_metrics")
    op.drop_index("idx_research_metrics_timestamp", table_name="research_metrics")
    op.drop_table("research_metrics")
