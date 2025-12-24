"""Add strategic_objectives column to users table.

Revision ID: z23_add_strategic_objectives
Revises: z22_add_file_pending_scan
Create Date: 2025-12-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z23_add_strategic_objectives"
down_revision: str | Sequence[str] | None = "z22_add_file_pending_scan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add strategic_objectives column to user_context table."""
    # Note: Originally added to users table, but CONTEXT_FIELDS queries user_context
    op.add_column(
        "user_context",
        sa.Column(
            "strategic_objectives",
            sa.ARRAY(sa.Text()),
            nullable=True,
            comment="User's strategic objectives (max 5)",
        ),
    )


def downgrade() -> None:
    """Remove strategic_objectives column."""
    op.drop_column("user_context", "strategic_objectives")
