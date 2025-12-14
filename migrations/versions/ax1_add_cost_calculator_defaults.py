"""Add cost calculator defaults column to users table.

Stores user preferences for the meeting cost calculator widget:
avg_hourly_rate, typical_participants, typical_duration_mins, typical_prep_mins.

Revision ID: ax1_add_cost_calculator_defaults
Revises: aw1_add_action_reminders
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ax1_add_cost_calculator_defaults"
down_revision: str | Sequence[str] | None = "aw1_add_action_reminders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add cost_calculator_defaults JSONB column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "cost_calculator_defaults",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="User defaults for meeting cost calculator: avg_hourly_rate, typical_participants, typical_duration_mins, typical_prep_mins",
        ),
    )


def downgrade() -> None:
    """Remove cost_calculator_defaults column from users table."""
    op.drop_column("users", "cost_calculator_defaults")
