"""Add email-related fields to users and actions tables.

Adds:
- users.email_preferences (JSONB) - user email preferences
- actions.reminder_sent_at (TIMESTAMPTZ) - when reminder was sent

Revision ID: k1_add_email_fields
Revises: j1_add_dataset_clarifications
Create Date: 2025-12-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "k1_add_email_fields"
down_revision: str | Sequence[str] | None = "j1_dataset_clarifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add email_preferences to users and reminder_sent_at to actions."""
    # Add email_preferences JSONB column to users
    op.add_column(
        "users",
        sa.Column(
            "email_preferences",
            JSONB,
            nullable=True,
            comment="User email notification preferences (e.g., meeting_emails, reminder_emails, digest_emails)",
        ),
    )

    # Add reminder_sent_at column to actions
    op.add_column(
        "actions",
        sa.Column(
            "reminder_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when reminder email was sent",
        ),
    )

    # Add index for finding actions that need reminders
    op.create_index(
        "idx_actions_reminder_due",
        "actions",
        ["reminder_sent_at", "target_end_date"],
        postgresql_where=sa.text("status NOT IN ('done', 'cancelled')"),
    )


def downgrade() -> None:
    """Remove email fields."""
    op.drop_index("idx_actions_reminder_due", table_name="actions")
    op.drop_column("actions", "reminder_sent_at")
    op.drop_column("users", "email_preferences")
