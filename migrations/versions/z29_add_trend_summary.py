"""Add trend_summary JSONB column to user_context table.

Stores AI-generated market trend summaries for user's industry.
Includes summary, key trends, opportunities, threats, and metadata.
Refreshes every 7 days or on industry change.

Revision ID: z29_add_trend_summary
Revises: z28_add_action_postmortem
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z29_add_trend_summary"
down_revision: str | Sequence[str] | None = "z28_add_action_postmortem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add trend_summary JSONB column to user_context table."""
    op.add_column(
        "user_context",
        sa.Column(
            "trend_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="AI-generated market trend summary (summary, key_trends, opportunities, threats, generated_at, industry)",
        ),
    )
    # Note: No index needed - staleness checks done in application code


def downgrade() -> None:
    """Remove trend_summary column from user_context table."""
    op.drop_column("user_context", "trend_summary")
