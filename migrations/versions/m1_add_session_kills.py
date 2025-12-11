"""Add session_kills audit table for tracking admin/automated session kills.

Revision ID: m1_add_session_kills
Revises: l1_add_gdpr_audit_log
Create Date: 2025-12-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m1_add_session_kills"
down_revision: str | Sequence[str] | None = "l1_add_gdpr_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create session_kills audit table."""
    op.create_table(
        "session_kills",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Text,
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Session that was killed (nullable if session deleted)",
        ),
        sa.Column(
            "killed_by",
            sa.Text,
            nullable=False,
            comment="User ID who killed, or 'system' for automated kills",
        ),
        sa.Column(
            "reason",
            sa.Text,
            nullable=False,
            comment="Reason for kill (e.g., 'cost_exceeded', 'duration_exceeded', 'admin_terminated')",
        ),
        sa.Column(
            "cost_at_kill",
            sa.Numeric(10, 4),
            nullable=True,
            comment="Session cost at time of kill in USD",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for querying by killer and time (admin audit trail)
    op.create_index(
        "idx_session_kills_killed_by_created",
        "session_kills",
        ["killed_by", "created_at"],
    )


def downgrade() -> None:
    """Drop session_kills table."""
    op.drop_index("idx_session_kills_killed_by_created", table_name="session_kills")
    op.drop_table("session_kills")
