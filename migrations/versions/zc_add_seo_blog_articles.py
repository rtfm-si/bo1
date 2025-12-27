"""Add seo_blog_articles table for SEO blog content generation.

Stores generated blog articles with status tracking (draft/published).

Revision ID: zc_add_seo_blog_articles
Revises: zb_add_seo_topics
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "zc_add_seo_blog_articles"
down_revision: str | Sequence[str] | None = "zb_add_seo_topics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create seo_blog_articles table."""
    op.create_table(
        "seo_blog_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", UUID(), nullable=True),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="draft",
            nullable=False,
        ),
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
            ["topic_id"],
            ["seo_topics.id"],
            ondelete="SET NULL",
        ),
    )

    # Index for efficient queries by user and time
    op.create_index(
        "idx_seo_blog_articles_user_created",
        "seo_blog_articles",
        ["user_id", "created_at"],
    )

    # Index for topic-based queries
    op.create_index(
        "idx_seo_blog_articles_topic",
        "seo_blog_articles",
        ["topic_id"],
    )


def downgrade() -> None:
    """Drop seo_blog_articles table."""
    op.drop_index("idx_seo_blog_articles_topic", table_name="seo_blog_articles")
    op.drop_index("idx_seo_blog_articles_user_created", table_name="seo_blog_articles")
    op.drop_table("seo_blog_articles")
