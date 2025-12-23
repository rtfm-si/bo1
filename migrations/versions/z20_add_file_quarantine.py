"""Add file_quarantine table for malware tracking.

Creates table to log files that failed antivirus scanning.
Supports admin review and audit trail for security compliance.

Revision ID: z20_add_file_quarantine
Revises: z19_add_table_comments
Create Date: 2025-12-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z20_add_file_quarantine"
down_revision: str | Sequence[str] | None = "z19_add_table_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create file_quarantine table."""
    op.create_table(
        "file_quarantine",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "file_hash", sa.String(64), nullable=False, comment="SHA-256 hash of file content"
        ),
        sa.Column(
            "threat_name", sa.String(255), nullable=False, comment="ClamAV threat identifier"
        ),
        sa.Column(
            "original_filename", sa.String(512), nullable=True, comment="User-provided filename"
        ),
        sa.Column(
            "file_size_bytes", sa.BigInteger(), nullable=True, comment="Size of file in bytes"
        ),
        sa.Column("content_type", sa.String(128), nullable=True, comment="MIME type of file"),
        sa.Column(
            "scan_duration_ms", sa.Float(), nullable=True, comment="Time taken to scan in ms"
        ),
        sa.Column("source_ip", sa.String(45), nullable=True, comment="Client IP address"),
        sa.Column("user_agent", sa.String(512), nullable=True, comment="Client user agent"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Index for user lookup
    op.create_index("idx_file_quarantine_user_id", "file_quarantine", ["user_id"])
    # Index for threat type analysis
    op.create_index("idx_file_quarantine_threat_name", "file_quarantine", ["threat_name"])
    # Index for time-based queries
    op.create_index("idx_file_quarantine_created_at", "file_quarantine", ["created_at"])

    # Table comment
    op.execute(
        "COMMENT ON TABLE file_quarantine IS "
        "'Files blocked by ClamAV antivirus scanner. Records for admin review and security audit.'"
    )

    # Enable RLS
    op.execute("ALTER TABLE file_quarantine ENABLE ROW LEVEL SECURITY")

    # RLS policy: admins can read all, users cannot see quarantine entries (security sensitive)
    op.execute("""
        CREATE POLICY file_quarantine_admin_access ON file_quarantine
        FOR SELECT
        TO PUBLIC
        USING (
            current_setting('bo1.is_admin', true)::boolean = true
        )
    """)


def downgrade() -> None:
    """Drop file_quarantine table."""
    op.execute("DROP POLICY IF EXISTS file_quarantine_admin_access ON file_quarantine")
    op.drop_index("idx_file_quarantine_created_at", table_name="file_quarantine")
    op.drop_index("idx_file_quarantine_threat_name", table_name="file_quarantine")
    op.drop_index("idx_file_quarantine_user_id", table_name="file_quarantine")
    op.drop_table("file_quarantine")
