"""Add replanning fields to actions table.

Revision ID: a8_add_replanning_fields
Revises: a7_add_project_id_to_actions
Create Date: 2025-12-04

Adds fields to track replanning sessions for blocked actions:
- replan_session_id: References the session created to replan this action
- replan_requested_at: When replanning was requested
- replanning_reason: User-provided context for why replanning is needed
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a8_add_replanning_fields"
down_revision = "a7_add_project_id_to_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add replanning fields to actions table."""
    # Add replanning fields to actions table
    op.add_column("actions", sa.Column("replan_session_id", sa.String(255), nullable=True))
    op.add_column(
        "actions", sa.Column("replan_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("actions", sa.Column("replanning_reason", sa.Text(), nullable=True))

    # Add index for finding actions by replan session
    op.create_index("idx_actions_replan_session", "actions", ["replan_session_id"])

    # Add foreign key constraint (sessions table uses VARCHAR id)
    op.create_foreign_key(
        "fk_actions_replan_session",
        "actions",
        "sessions",
        ["replan_session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove replanning fields from actions table."""
    # Remove foreign key constraint
    op.drop_constraint("fk_actions_replan_session", "actions", type_="foreignkey")

    # Remove index
    op.drop_index("idx_actions_replan_session", table_name="actions")

    # Remove columns
    op.drop_column("actions", "replanning_reason")
    op.drop_column("actions", "replan_requested_at")
    op.drop_column("actions", "replan_session_id")
