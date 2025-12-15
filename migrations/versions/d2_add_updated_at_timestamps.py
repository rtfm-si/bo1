"""Add updated_at columns to audit tables.

Add updated_at timestamps to session_events, session_shares, alert_history,
and session_kills tables for consistent audit trails.

Revision ID: d2_updated_at
Revises: d1_soft_delete
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2_updated_at"
down_revision: str | None = "d1_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add updated_at columns and triggers to audit tables."""
    # --- session_events ---
    op.add_column(
        "session_events",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.execute(
        """
        CREATE TRIGGER update_session_events_updated_at
        BEFORE UPDATE ON session_events
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # --- session_shares ---
    op.add_column(
        "session_shares",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.execute(
        """
        CREATE TRIGGER update_session_shares_updated_at
        BEFORE UPDATE ON session_shares
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # --- alert_history ---
    op.add_column(
        "alert_history",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.execute(
        """
        CREATE TRIGGER update_alert_history_updated_at
        BEFORE UPDATE ON alert_history
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # --- session_kills ---
    op.add_column(
        "session_kills",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.execute(
        """
        CREATE TRIGGER update_session_kills_updated_at
        BEFORE UPDATE ON session_kills
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Remove updated_at columns and triggers."""
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_session_kills_updated_at ON session_kills")
    op.execute("DROP TRIGGER IF EXISTS update_alert_history_updated_at ON alert_history")
    op.execute("DROP TRIGGER IF EXISTS update_session_shares_updated_at ON session_shares")
    op.execute("DROP TRIGGER IF EXISTS update_session_events_updated_at ON session_events")

    # Drop columns
    op.drop_column("session_kills", "updated_at")
    op.drop_column("alert_history", "updated_at")
    op.drop_column("session_shares", "updated_at")
    op.drop_column("session_events", "updated_at")
