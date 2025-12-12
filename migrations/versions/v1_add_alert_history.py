"""Add alert_history table for tracking ntfy alerts.

Revision ID: v1_add_alert_history
Revises: u1_add_cancellation_fields
Create Date: 2025-12-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "v1_add_alert_history"
down_revision: str | Sequence[str] | None = "u1_add_cancellation_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create alert_history table for tracking sent alerts."""
    op.create_table(
        "alert_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "alert_type",
            sa.Text,
            nullable=False,
            index=True,
            comment="Alert type (runaway_session, session_killed, service_degraded, cost_threshold, auth_failure_spike, rate_limit_spike, lockout_spike, etc.)",
        ),
        sa.Column(
            "severity",
            sa.Text,
            nullable=False,
            comment="Alert severity (info, warning, high, urgent, critical)",
        ),
        sa.Column(
            "title",
            sa.Text,
            nullable=False,
            comment="Alert title/headline",
        ),
        sa.Column(
            "message",
            sa.Text,
            nullable=False,
            comment="Alert message body",
        ),
        sa.Column(
            "metadata",
            JSONB,
            nullable=True,
            comment="Additional context (session_id, user_id, cost, IP, etc.)",
        ),
        sa.Column(
            "delivered",
            sa.Boolean,
            nullable=False,
            default=True,
            comment="Whether ntfy delivery succeeded",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for querying alerts by type and time (admin dashboard)
    op.create_index(
        "idx_alert_history_type_created",
        "alert_history",
        ["alert_type", "created_at"],
    )

    # Index for time-based queries (recent alerts)
    op.create_index(
        "idx_alert_history_created",
        "alert_history",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop alert_history table."""
    op.drop_index("idx_alert_history_created", table_name="alert_history")
    op.drop_index("idx_alert_history_type_created", table_name="alert_history")
    op.drop_table("alert_history")
