"""Add meta_title to published_decisions table.

Revision ID: zzzc_decision_meta_title
Revises: zzzb_gsc_integration
Create Date: 2025-02-04

Adds:
- meta_title: SEO-optimized title (50-60 chars) separate from display title
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "zzzc_decision_meta_title"
down_revision: str | Sequence[str] | None = "zzzb_gsc_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add meta_title column to published_decisions."""
    op.add_column(
        "published_decisions",
        sa.Column("meta_title", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Remove meta_title column from published_decisions."""
    op.drop_column("published_decisions", "meta_title")
