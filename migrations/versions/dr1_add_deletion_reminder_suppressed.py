"""Add deletion_reminder_suppressed and last_deletion_reminder_sent_at columns.

Revision ID: dr1_del_remind
Revises: z32_add_email_log_events
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "dr1_del_remind"
down_revision: str | Sequence[str] | None = "z32_add_email_log_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add columns for tracking deletion reminder preferences."""
    # Add boolean flag for suppressing reminders
    op.add_column(
        "users",
        sa.Column(
            "deletion_reminder_suppressed",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )

    # Add timestamp for tracking when last reminder was sent
    op.add_column(
        "users",
        sa.Column(
            "last_deletion_reminder_sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # Add comment for documentation
    op.execute(
        "COMMENT ON COLUMN users.deletion_reminder_suppressed IS "
        "'If true, user has opted out of data deletion reminder emails.'"
    )
    op.execute(
        "COMMENT ON COLUMN users.last_deletion_reminder_sent_at IS "
        "'Timestamp of last deletion reminder email sent (for rate limiting).'"
    )


def downgrade() -> None:
    """Remove deletion reminder columns."""
    op.drop_column("users", "last_deletion_reminder_sent_at")
    op.drop_column("users", "deletion_reminder_suppressed")
