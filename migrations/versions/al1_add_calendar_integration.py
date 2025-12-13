"""Add Google Calendar integration columns.

Adds calendar_tokens JSONB to users and calendar_event_id to actions.

Revision ID: al1_calendar_integration
Revises: ak1_create_feedback
Create Date: 2025-12-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "al1_calendar_integration"
down_revision: str | Sequence[str] | None = "ak1_create_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add calendar integration columns."""
    # Add calendar tokens to users (separate from sheets tokens)
    op.add_column(
        "users",
        sa.Column("google_calendar_tokens", JSONB, nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "google_calendar_connected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Add calendar event reference to actions
    op.add_column(
        "actions",
        sa.Column("calendar_event_id", sa.Text, nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("calendar_event_link", sa.Text, nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("calendar_sync_enabled", sa.Boolean, default=True, nullable=True),
    )


def downgrade() -> None:
    """Remove calendar integration columns."""
    op.drop_column("actions", "calendar_sync_enabled")
    op.drop_column("actions", "calendar_event_link")
    op.drop_column("actions", "calendar_event_id")
    op.drop_column("users", "google_calendar_connected_at")
    op.drop_column("users", "google_calendar_tokens")
