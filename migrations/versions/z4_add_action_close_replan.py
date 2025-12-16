"""Add close/replan fields to actions table.

This migration adds fields to support action closure (failed/abandoned) and replanning:
- closure_reason: Reason for closing action as failed/abandoned
- replanned_from_id: FK to original action when this action was created via replan

Also updates the action_status_enum to include new statuses:
- failed, abandoned, replanned

Revision ID: z4_add_action_close_replan
Revises: z3_add_session_termination
Create Date: 2025-12-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z4_add_action_close_replan"
down_revision: str | Sequence[str] | None = "ay1_add_project_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add closure and replan fields to actions table."""
    # Add closure_reason for failed/abandoned actions
    op.add_column(
        "actions",
        sa.Column(
            "closure_reason",
            sa.Text(),
            nullable=True,
            comment="Reason for closing action as failed or abandoned",
        ),
    )

    # Add replanned_from_id FK to link replanned actions to originals
    op.add_column(
        "actions",
        sa.Column(
            "replanned_from_id",
            sa.UUID(),
            nullable=True,
            comment="Original action ID when this action was created via replan",
        ),
    )

    # Create FK constraint
    op.create_foreign_key(
        "actions_replanned_from_id_fkey",
        "actions",
        "actions",
        ["replanned_from_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index on replanned_from_id for lookup
    op.create_index(
        "actions_replanned_from_id_idx",
        "actions",
        ["replanned_from_id"],
        postgresql_where=sa.text("replanned_from_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove closure and replan fields from actions table."""
    op.drop_index("actions_replanned_from_id_idx", table_name="actions")
    op.drop_constraint("actions_replanned_from_id_fkey", "actions", type_="foreignkey")
    op.drop_column("actions", "replanned_from_id")
    op.drop_column("actions", "closure_reason")
