"""Add termination fields to sessions table.

This migration adds fields to support early meeting termination:
- terminated_at: When the session was terminated
- termination_reason: User-provided reason for termination
- termination_type: Type of termination (blocker_identified, user_cancelled, continue_best_effort)
- billable_portion: Fraction (0.0-1.0) of session to bill based on completed sub-problems

Revision ID: z3_add_session_termination
Revises: z2_create_session_shares
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z3_add_session_termination"
down_revision: str | Sequence[str] | None = "z2_create_session_shares"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add termination fields to sessions table."""
    # Add terminated_at timestamp
    op.add_column(
        "sessions",
        sa.Column(
            "terminated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the session was terminated early (NULL if not terminated)",
        ),
    )

    # Add termination_reason (user-provided reason)
    op.add_column(
        "sessions",
        sa.Column(
            "termination_reason",
            sa.Text(),
            nullable=True,
            comment="User-provided reason for early termination",
        ),
    )

    # Add termination_type enum-like field
    op.add_column(
        "sessions",
        sa.Column(
            "termination_type",
            sa.String(32),
            nullable=True,
            comment="Type of termination: blocker_identified, user_cancelled, continue_best_effort",
        ),
    )

    # Add billable_portion (0.0-1.0 fraction)
    op.add_column(
        "sessions",
        sa.Column(
            "billable_portion",
            sa.Float(),
            nullable=True,
            default=1.0,
            comment="Fraction of session to bill (0.0-1.0), based on completed sub-problems",
        ),
    )

    # Add index on terminated_at for analytics queries
    op.create_index(
        "sessions_terminated_at_idx",
        "sessions",
        ["terminated_at"],
        postgresql_where=sa.text("terminated_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove termination fields from sessions table."""
    op.drop_index("sessions_terminated_at_idx", table_name="sessions")
    op.drop_column("sessions", "billable_portion")
    op.drop_column("sessions", "termination_type")
    op.drop_column("sessions", "termination_reason")
    op.drop_column("sessions", "terminated_at")
