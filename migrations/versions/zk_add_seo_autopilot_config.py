"""Add seo_autopilot_config JSONB column to user_context.

Revision ID: zk_add_seo_autopilot_config
Revises: zj_add_meeting_credits
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zk_add_seo_autopilot_config"
down_revision: str | Sequence[str] | None = "zj_add_meeting_credits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add seo_autopilot_config JSONB column.

    Structure: {
        "enabled": false,
        "frequency_per_week": 1,  # 1-7
        "auto_publish": false,
        "require_approval": true,
        "target_keywords": [],
        "purchase_intent_only": true
    }

    Stores user's SEO autopilot configuration for automated content generation.
    """
    op.add_column(
        "user_context",
        sa.Column(
            "seo_autopilot_config",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            comment="SEO autopilot configuration (enabled, frequency, keywords)",
        ),
    )


def downgrade() -> None:
    """Remove seo_autopilot_config column."""
    op.drop_column("user_context", "seo_autopilot_config")
