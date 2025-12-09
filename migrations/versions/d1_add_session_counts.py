"""add session count columns for denormalized counts

Revision ID: d1_add_session_counts
Revises: 26fce129eb71
Create Date: 2025-12-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1_add_session_counts"
down_revision: str | Sequence[str] | None = "26fce129eb71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add denormalized count columns to sessions table."""
    # Add count columns with defaults
    op.add_column(
        "sessions", sa.Column("expert_count", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "sessions",
        sa.Column("contribution_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "sessions", sa.Column("focus_area_count", sa.Integer(), server_default="0", nullable=False)
    )

    # Backfill existing sessions from session_events
    op.execute("""
        UPDATE sessions s
        SET
            expert_count = COALESCE((
                SELECT COUNT(*) FROM session_events se
                WHERE se.session_id = s.id AND se.event_type = 'persona_selected'
            ), 0),
            contribution_count = COALESCE((
                SELECT COUNT(*) FROM session_events se
                WHERE se.session_id = s.id AND se.event_type = 'contribution'
            ), 0),
            focus_area_count = COALESCE((
                SELECT COUNT(*) FROM session_events se
                WHERE se.session_id = s.id AND se.event_type = 'subproblem_started'
            ), 0)
    """)


def downgrade() -> None:
    """Remove denormalized count columns from sessions table."""
    op.drop_column("sessions", "focus_area_count")
    op.drop_column("sessions", "contribution_count")
    op.drop_column("sessions", "expert_count")
