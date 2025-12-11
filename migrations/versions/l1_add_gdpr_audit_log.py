"""Add GDPR audit log table for tracking data export and deletion requests.

Revision ID: l1_add_gdpr_audit_log
Revises: k1_add_email_fields
Create Date: 2025-12-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "l1_add_gdpr_audit_log"
down_revision: str | Sequence[str] | None = "k1_add_email_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create gdpr_audit_log table."""
    op.create_table(
        "gdpr_audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text, nullable=False, index=True),
        sa.Column(
            "action",
            sa.Text,
            nullable=False,
            comment="GDPR action: export_requested, deletion_requested, deletion_completed",
        ),
        sa.Column(
            "details",
            JSONB,
            nullable=True,
            comment="Additional details about the action",
        ),
        sa.Column("ip_address", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for querying by user and time
    op.create_index(
        "idx_gdpr_audit_log_user_created",
        "gdpr_audit_log",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    """Drop gdpr_audit_log table."""
    op.drop_index("idx_gdpr_audit_log_user_created", table_name="gdpr_audit_log")
    op.drop_table("gdpr_audit_log")
