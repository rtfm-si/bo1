"""Add CTR metrics columns to blog_posts table.

Tracks view counts, click-through counts, and last viewed timestamp
for SEO performance analytics.

Revision ID: zt_blog_post_ctr_metrics
Revises: zs_experiments_table
Create Date: 2025-12-29
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "zt_blog_post_ctr_metrics"
down_revision: str = "zs_experiments_table"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add CTR tracking columns to blog_posts."""
    op.execute("""
        ALTER TABLE blog_posts
        ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS click_through_count INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS last_viewed_at TIMESTAMPTZ
    """)

    # Index for performance queries (most viewed, recently viewed)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_blog_posts_view_count
        ON blog_posts (view_count DESC)
        WHERE status = 'published'
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_blog_posts_last_viewed
        ON blog_posts (last_viewed_at DESC NULLS LAST)
        WHERE status = 'published'
    """)


def downgrade() -> None:
    """Remove CTR tracking columns."""
    op.execute("DROP INDEX IF EXISTS idx_blog_posts_last_viewed")
    op.execute("DROP INDEX IF EXISTS idx_blog_posts_view_count")
    op.execute("""
        ALTER TABLE blog_posts
        DROP COLUMN IF EXISTS view_count,
        DROP COLUMN IF EXISTS click_through_count,
        DROP COLUMN IF EXISTS last_viewed_at
    """)
