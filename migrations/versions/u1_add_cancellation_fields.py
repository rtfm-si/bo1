"""Add cancellation_reason and cancelled_at columns to actions table.

Allows capturing why an action was cancelled (mirrors blocking_reason pattern).

Revision ID: u1_add_cancellation_fields
Revises: t1_add_skip_clarification
Create Date: 2025-12-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "u1_add_cancellation_fields"
down_revision: str | Sequence[str] | None = "t1_add_skip_clarification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add cancellation_reason and cancelled_at columns."""
    op.add_column(
        "actions",
        sa.Column(
            "cancellation_reason",
            sa.Text,
            nullable=True,
            comment="Reason for cancellation (what went wrong)",
        ),
    )
    op.add_column(
        "actions",
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When action was cancelled",
        ),
    )


def downgrade() -> None:
    """Remove cancellation fields."""
    op.drop_column("actions", "cancelled_at")
    op.drop_column("actions", "cancellation_reason")
