"""Add user-level calendar_sync_enabled preference column.

Allows users to pause calendar sync without disconnecting entirely.
When disabled, no new calendar events are created for actions.

Revision ID: z12_calendar_sync_preference
Revises: z11_add_failure_acknowledged
Create Date: 2025-12-18
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z12_calendar_sync_preference"
down_revision: str | Sequence[str] | None = "z11_add_failure_acknowledged"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add calendar_sync_enabled column to users table."""
    # Default to true so existing connected users continue syncing
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS calendar_sync_enabled BOOLEAN DEFAULT true;
    """)


def downgrade() -> None:
    """Remove calendar_sync_enabled column from users table."""
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS calendar_sync_enabled;")
