"""Add action_metric_triggers JSONB column to user_context table.

Stores action-triggered metric staleness entries that delay staleness
warnings by 28 days after an action affects a business metric.

Structure: [{"metric_name": "...", "triggered_at": "...", "delay_until": "...", "action_id": "..."}]

Revision ID: fb2_add_action_metric_triggers
Revises: fb1_create_user_ratings
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "fb2_add_action_metric_triggers"
down_revision: str | Sequence[str] | None = "fb1_create_user_ratings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add action_metric_triggers JSONB column to user_context table."""
    op.add_column(
        "user_context",
        sa.Column(
            "action_metric_triggers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="Action-triggered metric staleness delays (28-day grace period)",
        ),
    )

    op.execute(
        "COMMENT ON COLUMN user_context.action_metric_triggers IS "
        "'Action-triggered metric staleness delays. Structure: "
        '[{"metric_name": "revenue", "triggered_at": "2025-01-01T00:00:00Z", '
        '"delay_until": "2025-01-29T00:00:00Z", "action_id": "uuid"}]\''
    )


def downgrade() -> None:
    """Remove action_metric_triggers column from user_context table."""
    op.drop_column("user_context", "action_metric_triggers")
