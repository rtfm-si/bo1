"""Add post-mortem fields to actions table.

Captures lessons learned and what went well when completing actions.
Both fields are optional text fields for user reflection.

Revision ID: z28_add_action_postmortem
Revises: z27_add_managed_competitors
Create Date: 2025-12-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z28_add_action_postmortem"
down_revision: str | Sequence[str] | None = "z27_add_managed_competitors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add lessons_learned and went_well columns to actions table."""
    # Add lessons_learned column
    op.add_column(
        "actions",
        sa.Column(
            "lessons_learned",
            sa.Text(),
            nullable=True,
            comment="User reflection on lessons learned from this action",
        ),
    )

    # Add went_well column
    op.add_column(
        "actions",
        sa.Column(
            "went_well",
            sa.Text(),
            nullable=True,
            comment="User reflection on what went well during this action",
        ),
    )


def downgrade() -> None:
    """Remove post-mortem columns from actions table."""
    op.drop_column("actions", "went_well")
    op.drop_column("actions", "lessons_learned")
