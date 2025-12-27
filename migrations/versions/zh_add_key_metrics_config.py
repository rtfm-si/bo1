"""Add key_metrics_config JSONB column to user_context.

Revision ID: zh_add_key_metrics_config
Revises: zg_add_research_sharing
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zh_add_key_metrics_config"
down_revision: str | Sequence[str] | None = "zg_add_research_sharing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add key_metrics_config JSONB column.

    Structure: [
        {
            "metric_key": "revenue",
            "importance": "now",  # now, later, monitor
            "category": "user",   # user, competitor, industry
            "display_order": 0,
            "notes": "Track MRR growth"
        }
    ]

    Stores user's prioritization of which metrics to track.
    """
    op.add_column(
        "user_context",
        sa.Column(
            "key_metrics_config",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            comment="User's key metrics configuration (importance rankings)",
        ),
    )


def downgrade() -> None:
    """Remove key_metrics_config column."""
    op.drop_column("user_context", "key_metrics_config")
