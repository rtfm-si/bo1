"""Add seo_topics table for SEO topic tracking with blog generation workflow.

Stores user's researched SEO topics with status tracking (researched/writing/published).

Revision ID: zb_add_seo_topics
Revises: za_add_seo_trend_analyses
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "zb_add_seo_topics"
down_revision: str | Sequence[str] | None = "za_add_seo_trend_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create seo_topics table."""
    op.create_table(
        "seo_topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", UUID(), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="researched",
            nullable=False,
        ),
        sa.Column("source_analysis_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_analysis_id"],
            ["seo_trend_analyses.id"],
            ondelete="SET NULL",
        ),
    )

    # Index for efficient queries by user and time
    op.create_index(
        "idx_seo_topics_user_created",
        "seo_topics",
        ["user_id", "created_at"],
    )

    # Index for workspace-based queries
    op.create_index(
        "idx_seo_topics_workspace",
        "seo_topics",
        ["workspace_id"],
    )


def downgrade() -> None:
    """Drop seo_topics table."""
    op.drop_index("idx_seo_topics_workspace", table_name="seo_topics")
    op.drop_index("idx_seo_topics_user_created", table_name="seo_topics")
    op.drop_table("seo_topics")
