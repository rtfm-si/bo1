"""Create blog_posts table for SEO content generation pipeline.

Tracks:
- Blog post content (title, slug, content, excerpt)
- Publishing workflow (draft/scheduled/published status)
- SEO metadata (keywords, generated_by_topic)
- Timestamps

Revision ID: ba2_create_blog_posts
Revises: ba1_create_page_analytics
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ba2_create_blog_posts"
down_revision: str | Sequence[str] | None = "ba1_create_page_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create blog_posts table."""
    op.create_table(
        "blog_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=False,
            comment="Blog post title",
        ),
        sa.Column(
            "slug",
            sa.String(500),
            nullable=False,
            unique=True,
            index=True,
            comment="URL-friendly slug (unique)",
        ),
        sa.Column(
            "content",
            sa.Text,
            nullable=False,
            comment="Full blog post content in Markdown",
        ),
        sa.Column(
            "excerpt",
            sa.String(500),
            nullable=True,
            comment="Short excerpt for previews/meta description",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
            index=True,
            comment="Publication status: draft, scheduled, published",
        ),
        sa.Column(
            "published_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            index=True,
            comment="Actual or scheduled publication datetime",
        ),
        sa.Column(
            "seo_keywords",
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
            comment="SEO target keywords",
        ),
        sa.Column(
            "generated_by_topic",
            sa.String(500),
            nullable=True,
            comment="Topic that triggered AI generation (if auto-generated)",
        ),
        sa.Column(
            "meta_title",
            sa.String(100),
            nullable=True,
            comment="Custom meta title for SEO",
        ),
        sa.Column(
            "meta_description",
            sa.String(300),
            nullable=True,
            comment="Custom meta description for SEO",
        ),
        sa.Column(
            "author_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who created/edited the post",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'scheduled', 'published')",
            name="blog_posts_status_check",
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_blog_posts_status_published_at",
        "blog_posts",
        ["status", "published_at"],
        postgresql_where=sa.text("status = 'scheduled'"),
    )


def downgrade() -> None:
    """Drop blog_posts table."""
    op.drop_index("ix_blog_posts_status_published_at", table_name="blog_posts")
    op.drop_table("blog_posts")
