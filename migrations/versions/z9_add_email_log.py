"""Add email_log table for tracking sent emails.

Tracks all transactional emails sent via Resend for admin analytics.

Revision ID: z9_add_email_log
Revises: z8_add_benchmark_history
Create Date: 2025-12-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z9_add_email_log"
down_revision: str | Sequence[str] | None = "z8_add_benchmark_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create email_log table."""
    op.create_table(
        "email_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email_type", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="sent"),
        sa.Column("resend_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for efficient count queries by type and time
    op.create_index(
        "idx_email_log_type_created",
        "email_log",
        ["email_type", "created_at"],
    )


def downgrade() -> None:
    """Drop email_log table."""
    op.drop_index("idx_email_log_type_created", table_name="email_log")
    op.drop_table("email_log")
