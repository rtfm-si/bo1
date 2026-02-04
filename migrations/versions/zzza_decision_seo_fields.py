"""Add SEO fields to published_decisions table.

Revision ID: zzza_decision_seo_fields
Revises: zzz_featured_decisions
Create Date: 2025-02-04

Adds:
- featured_image_url: For og:image and Article schema image
- seo_keywords: Array of keywords for meta keywords tag
- reading_time_minutes: Calculated reading time for UX
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "zzza_decision_seo_fields"
down_revision: str | Sequence[str] | None = "zzz_featured_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add SEO fields to published_decisions."""
    op.add_column(
        "published_decisions",
        sa.Column("featured_image_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "published_decisions",
        sa.Column(
            "seo_keywords",
            sa.dialects.postgresql.ARRAY(sa.String(100)),
            nullable=True,
        ),
    )
    op.add_column(
        "published_decisions",
        sa.Column("reading_time_minutes", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    """Remove SEO fields from published_decisions."""
    op.drop_column("published_decisions", "reading_time_minutes")
    op.drop_column("published_decisions", "seo_keywords")
    op.drop_column("published_decisions", "featured_image_url")
