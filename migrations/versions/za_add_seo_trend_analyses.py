"""Add seo_trend_analyses table for SEO trend analyzer feature.

Stores user's SEO trend analysis results with industry/keywords context.

Revision ID: za_add_seo_trend_analyses
Revises: z9_add_email_log
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "za_add_seo_trend_analyses"
down_revision: str | Sequence[str] | None = "fb2_add_action_metric_triggers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create seo_trend_analyses table."""
    op.create_table(
        "seo_trend_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", UUID(), nullable=True),
        sa.Column("keywords", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("results_json", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )

    # Index for efficient history queries by user and time
    op.create_index(
        "idx_seo_trend_analyses_user_created",
        "seo_trend_analyses",
        ["user_id", "created_at"],
    )

    # Index for workspace-based queries
    op.create_index(
        "idx_seo_trend_analyses_workspace",
        "seo_trend_analyses",
        ["workspace_id"],
    )


def downgrade() -> None:
    """Drop seo_trend_analyses table."""
    op.drop_index("idx_seo_trend_analyses_workspace", table_name="seo_trend_analyses")
    op.drop_index("idx_seo_trend_analyses_user_created", table_name="seo_trend_analyses")
    op.drop_table("seo_trend_analyses")
