"""Add strategic_objectives_progress JSONB column to user_context.

Revision ID: zd_add_objective_progress
Revises: zc_add_seo_blog_articles
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zd_add_objective_progress"
down_revision: str | Sequence[str] | None = "zc_add_seo_blog_articles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add strategic_objectives_progress JSONB column.

    Structure: {
        "0": {"current": "5K", "target": "10K", "unit": "MRR", "updated_at": "2025-01-01T00:00:00Z"},
        "1": {"current": "50%", "target": "80%", "unit": "%", "updated_at": "2025-01-01T00:00:00Z"}
    }

    Uses objective index (string) as key to handle objective text changes.
    """
    op.add_column(
        "user_context",
        sa.Column(
            "strategic_objectives_progress",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            comment="Progress tracking per strategic objective (keyed by index)",
        ),
    )


def downgrade() -> None:
    """Remove strategic_objectives_progress column."""
    op.drop_column("user_context", "strategic_objectives_progress")
