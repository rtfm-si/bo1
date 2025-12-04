"""Create action_updates table for activity feed.

Tracks all updates to actions including progress, status changes, blockers, and notes.
Provides audit trail and activity feed for action management.

Revision ID: a3_create_action_updates
Revises: a2_create_action_dependencies
Create Date: 2025-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3_create_action_updates"
down_revision: str | Sequence[str] | None = "a2_create_action_dependencies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create action_updates table for activity feed."""
    # Create action_updates table (using VARCHAR with CHECK instead of ENUM)
    op.create_table(
        "action_updates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("action_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "update_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False, comment="Update content/note"),
        # Type-specific fields
        sa.Column(
            "old_status", sa.String(length=20), nullable=True, comment="For status_change updates"
        ),
        sa.Column(
            "new_status", sa.String(length=20), nullable=True, comment="For status_change updates"
        ),
        sa.Column("old_date", sa.Date(), nullable=True, comment="For date_change updates"),
        sa.Column("new_date", sa.Date(), nullable=True, comment="For date_change updates"),
        sa.Column(
            "date_field",
            sa.String(length=50),
            nullable=True,
            comment="Which date field changed (target_start_date, etc.)",
        ),
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=True,
            comment="Progress percentage (0-100) for progress updates",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        # Constraints
        sa.CheckConstraint(
            "update_type IN ('progress', 'blocker', 'note', 'status_change', 'date_change', 'completion')",
            name="check_valid_update_type",
        ),
        sa.CheckConstraint(
            "progress_percent IS NULL OR (progress_percent >= 0 AND progress_percent <= 100)",
            name="check_progress_percent_range",
        ),
        sa.CheckConstraint(
            "(update_type = 'status_change' AND old_status IS NOT NULL AND new_status IS NOT NULL) OR (update_type != 'status_change')",
            name="check_status_change_fields",
        ),
        sa.CheckConstraint(
            "(update_type = 'date_change' AND date_field IS NOT NULL) OR (update_type != 'date_change')",
            name="check_date_change_field",
        ),
    )

    # Indexes for efficient queries
    op.create_index("idx_action_updates_action_id", "action_updates", ["action_id"])
    op.create_index("idx_action_updates_user_id", "action_updates", ["user_id"])
    op.create_index("idx_action_updates_type", "action_updates", ["update_type"])
    op.create_index(
        "idx_action_updates_created_at", "action_updates", ["created_at"], postgresql_using="btree"
    )
    op.create_index(
        "idx_action_updates_action_created",
        "action_updates",
        ["action_id", "created_at"],
    )

    # Comments
    op.execute("""
        COMMENT ON TABLE action_updates IS 'Activity feed and audit trail for action updates';
        COMMENT ON COLUMN action_updates.update_type IS 'Type of update: progress (milestone reached), blocker (blocked), note (general comment), status_change (status changed), date_change (date updated), completion (completed)';
        COMMENT ON COLUMN action_updates.content IS 'Human-readable update content or note';
    """)


def downgrade() -> None:
    """Remove action_updates table."""
    op.drop_index("idx_action_updates_action_created", table_name="action_updates")
    op.drop_index("idx_action_updates_created_at", table_name="action_updates")
    op.drop_index("idx_action_updates_type", table_name="action_updates")
    op.drop_index("idx_action_updates_user_id", table_name="action_updates")
    op.drop_index("idx_action_updates_action_id", table_name="action_updates")
    op.drop_table("action_updates")
