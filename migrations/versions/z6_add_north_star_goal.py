"""Add north_star_goal to user_context.

User's primary objective for the next 3-6 months (e.g., "10K MRR by Q2").
Included in meeting context for more focused deliberations.

Revision ID: z6_add_north_star_goal
Revises: 9219aa1cf819
Create Date: 2025-12-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z6_add_north_star_goal"
down_revision: str | Sequence[str] | None = "9219aa1cf819"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add north_star_goal column to user_context."""
    op.add_column(
        "user_context",
        sa.Column(
            "north_star_goal",
            sa.String(200),
            nullable=True,
            comment="Primary objective for next 3-6 months (e.g., '10K MRR by Q2')",
        ),
    )


def downgrade() -> None:
    """Remove north_star_goal column."""
    op.drop_column("user_context", "north_star_goal")
