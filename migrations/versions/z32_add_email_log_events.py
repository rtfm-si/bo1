"""Add event tracking columns to email_log table.

Enables Resend webhook integration to track email delivery events:
delivered, opened, clicked, bounced, failed.

Revision ID: z32_add_email_log_events
Revises: z31_add_projects_soft_delete
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z32_add_email_log_events"
down_revision: str | Sequence[str] | None = "z31_add_projects_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add event timestamp columns to email_log table."""
    # Add event tracking columns
    op.add_column(
        "email_log",
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "email_log",
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "email_log",
        sa.Column("clicked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "email_log",
        sa.Column("bounced_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "email_log",
        sa.Column("failed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Index on status for efficient rate calculations
    op.create_index(
        "idx_email_log_status",
        "email_log",
        ["status"],
    )

    # Index on resend_id for webhook lookups
    op.create_index(
        "idx_email_log_resend_id",
        "email_log",
        ["resend_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove event tracking columns from email_log table."""
    op.drop_index("idx_email_log_resend_id", table_name="email_log")
    op.drop_index("idx_email_log_status", table_name="email_log")
    op.drop_column("email_log", "failed_at")
    op.drop_column("email_log", "bounced_at")
    op.drop_column("email_log", "clicked_at")
    op.drop_column("email_log", "opened_at")
    op.drop_column("email_log", "delivered_at")
