"""Add seo_article_events table for SEO content analytics.

Tracks article views, clicks, and signups for content performance analytics.

Revision ID: ze_add_seo_article_events
Revises: zd_add_strategic_objectives_progress
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ze_add_seo_article_events"
down_revision: str | Sequence[str] | None = "zd_add_objective_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create seo_article_events table."""
    op.create_table(
        "seo_article_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column("referrer", sa.String(length=1000), nullable=True),
        sa.Column("utm_source", sa.String(length=255), nullable=True),
        sa.Column("utm_medium", sa.String(length=255), nullable=True),
        sa.Column("utm_campaign", sa.String(length=255), nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["seo_blog_articles.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "event_type IN ('view', 'click', 'signup')",
            name="ck_seo_article_events_event_type",
        ),
    )

    # Index for efficient aggregation queries
    op.create_index(
        "idx_seo_article_events_aggregation",
        "seo_article_events",
        ["article_id", "event_type", "created_at"],
    )

    # Index for time-range queries
    op.create_index(
        "idx_seo_article_events_created",
        "seo_article_events",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop seo_article_events table."""
    op.drop_index("idx_seo_article_events_created", table_name="seo_article_events")
    op.drop_index("idx_seo_article_events_aggregation", table_name="seo_article_events")
    op.drop_table("seo_article_events")
