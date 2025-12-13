"""Add context_ids column to sessions table.

Revision ID: an1_add_session_context
Revises: am1_add_feedback_analysis
Create Date: 2025-12-13

Stores user-selected context for meeting creation:
- meeting_ids: past meetings to reference
- action_ids: actions to consider
- dataset_ids: datasets to analyze
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "an1_add_session_context"
down_revision = "am1_add_feedback_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add context_ids JSONB column to sessions table."""
    op.add_column(
        "sessions",
        sa.Column(
            "context_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="User-selected context: {meetings: [...], actions: [...], datasets: [...]}",
        ),
    )


def downgrade() -> None:
    """Remove context_ids column."""
    op.drop_column("sessions", "context_ids")
