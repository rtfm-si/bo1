"""Add heatmap_history_months column to user_context.

Stores user's preferred activity heatmap history depth (1, 3, or 6 months).
Default: null → 3 months (applied in API layer).

Revision ID: zq_add_heatmap_history_months
Revises: zp_add_working_pattern
Create Date: 2025-12-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "zq_add_heatmap_history_months"
down_revision: str = "zp_add_working_pattern"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add heatmap_history_months column to user_context."""
    op.add_column(
        "user_context",
        sa.Column(
            "heatmap_history_months",
            sa.Integer(),
            nullable=True,
            comment="Heatmap history depth in months: 1, 3, or 6. Default: null → 3",
        ),
    )


def downgrade() -> None:
    """Remove heatmap_history_months column."""
    op.drop_column("user_context", "heatmap_history_months")
