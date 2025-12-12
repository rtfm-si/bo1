"""Add api_audit_log table for request tracking.

Revision ID: q1_add_api_audit_log
Revises: o1_add_user_cost_tracking
Create Date: 2025-12-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q1_add_api_audit_log"
down_revision: str | Sequence[str] | None = "o1_add_user_cost_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create api_audit_log table."""
    op.create_table(
        "api_audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("method", sa.Text, nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=True, index=True),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("ip_address", sa.Text, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column(
            "request_id",
            sa.Text,
            nullable=True,
            comment="Correlation ID from X-Request-ID header",
        ),
    )

    # Index for cleanup jobs (delete old logs)
    op.create_index(
        "idx_api_audit_log_timestamp",
        "api_audit_log",
        ["timestamp"],
    )

    # Index for user queries (GDPR, admin)
    op.create_index(
        "idx_api_audit_log_user_timestamp",
        "api_audit_log",
        ["user_id", "timestamp"],
    )


def downgrade() -> None:
    """Drop api_audit_log table."""
    op.drop_index("idx_api_audit_log_user_timestamp", table_name="api_audit_log")
    op.drop_index("idx_api_audit_log_timestamp", table_name="api_audit_log")
    op.drop_table("api_audit_log")
