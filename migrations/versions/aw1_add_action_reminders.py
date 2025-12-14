"""Add action reminders columns and user reminder preferences.

Adds reminder tracking columns to actions table and default_reminder_frequency_days
to users table for configurable action reminder notifications.

Revision ID: aw1_add_action_reminders
Revises: av1_add_workspace_to_projects
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aw1_add_action_reminders"
down_revision: str | Sequence[str] | None = "av1_add_workspace_to_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add reminder columns to actions and users tables."""
    # Add reminder columns to actions table
    op.add_column(
        "actions",
        sa.Column(
            "start_reminder_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When to send start reminder (anticipated_start passed + not started)",
        ),
    )

    op.add_column(
        "actions",
        sa.Column(
            "deadline_reminder_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When to send deadline reminder (approaching due date)",
        ),
    )

    op.add_column(
        "actions",
        sa.Column(
            "reminder_frequency_days",
            sa.Integer(),
            nullable=True,
            server_default="3",
            comment="Days between reminder emails (default 3)",
        ),
    )

    op.add_column(
        "actions",
        sa.Column(
            "last_reminder_sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When last reminder email was sent",
        ),
    )

    op.add_column(
        "actions",
        sa.Column(
            "reminders_enabled",
            sa.Boolean(),
            nullable=True,
            server_default="true",
            comment="Whether reminders are enabled for this action",
        ),
    )

    op.add_column(
        "actions",
        sa.Column(
            "snoozed_until",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Reminder snoozed until this time",
        ),
    )

    # Add default reminder frequency to users table
    op.add_column(
        "users",
        sa.Column(
            "default_reminder_frequency_days",
            sa.Integer(),
            nullable=True,
            server_default="3",
            comment="Default reminder frequency for new actions (1-14 days)",
        ),
    )

    # Create index for efficient reminder queries (snoozed_until check done at query time)
    op.create_index(
        "ix_actions_reminders_pending",
        "actions",
        ["user_id", "status", "reminders_enabled"],
        postgresql_where=sa.text("status NOT IN ('done', 'cancelled') AND deleted_at IS NULL"),
    )

    # Index for looking up actions by snoozed_until
    op.create_index(
        "ix_actions_snoozed_until",
        "actions",
        ["snoozed_until"],
        postgresql_where=sa.text("snoozed_until IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove reminder columns."""
    op.drop_index("ix_actions_snoozed_until", table_name="actions")
    op.drop_index("ix_actions_reminders_pending", table_name="actions")

    op.drop_column("users", "default_reminder_frequency_days")
    op.drop_column("actions", "snoozed_until")
    op.drop_column("actions", "reminders_enabled")
    op.drop_column("actions", "last_reminder_sent_at")
    op.drop_column("actions", "reminder_frequency_days")
    op.drop_column("actions", "deadline_reminder_at")
    op.drop_column("actions", "start_reminder_at")
