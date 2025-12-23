"""Add file_pending_scan table for deferred antivirus scanning.

Files uploaded when ClamAV is unavailable are queued here for later scanning.

Revision ID: z22_add_file_pending_scan
Revises: z21_add_meeting_templates
Create Date: 2025-12-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z22_add_file_pending_scan"
down_revision: str | Sequence[str] | None = "z21_add_meeting_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create file_pending_scan table."""
    op.create_table(
        "file_pending_scan",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "file_key",
            sa.String(512),
            nullable=False,
            comment="Storage path/key for file retrieval",
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "file_hash", sa.String(64), nullable=False, comment="SHA-256 hash of file content"
        ),
        sa.Column(
            "original_filename", sa.String(512), nullable=True, comment="User-provided filename"
        ),
        sa.Column(
            "file_size_bytes", sa.BigInteger(), nullable=True, comment="Size of file in bytes"
        ),
        sa.Column("content_type", sa.String(128), nullable=True, comment="MIME type of file"),
        sa.Column("source_ip", sa.String(45), nullable=True, comment="Client IP address"),
        sa.Column("user_agent", sa.String(512), nullable=True, comment="Client user agent"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When scan was completed",
        ),
        sa.Column(
            "scan_result",
            sa.String(32),
            nullable=True,
            comment="Result: clean, infected, file_not_found",
        ),
        sa.Column(
            "threat_name",
            sa.String(255),
            nullable=True,
            comment="ClamAV threat identifier if infected",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Index for finding unscanned files (ordered by creation time)
    op.create_index(
        "idx_file_pending_scan_unscanned",
        "file_pending_scan",
        ["created_at"],
        postgresql_where=sa.text("scanned_at IS NULL"),
    )
    # Index for user lookup
    op.create_index("idx_file_pending_scan_user_id", "file_pending_scan", ["user_id"])
    # Index for file key lookup (in case we need to check if a file is pending)
    op.create_index("idx_file_pending_scan_file_key", "file_pending_scan", ["file_key"])

    # Table comment
    op.execute(
        "COMMENT ON TABLE file_pending_scan IS "
        "'Files awaiting antivirus scan. Queued when ClamAV was unavailable at upload time.'"
    )

    # Enable RLS
    op.execute("ALTER TABLE file_pending_scan ENABLE ROW LEVEL SECURITY")

    # RLS policy: admins can read all
    op.execute("""
        CREATE POLICY file_pending_scan_admin_access ON file_pending_scan
        FOR ALL
        TO PUBLIC
        USING (
            current_setting('bo1.is_admin', true)::boolean = true
        )
    """)


def downgrade() -> None:
    """Drop file_pending_scan table."""
    op.execute("DROP POLICY IF EXISTS file_pending_scan_admin_access ON file_pending_scan")
    op.drop_index("idx_file_pending_scan_file_key", table_name="file_pending_scan")
    op.drop_index("idx_file_pending_scan_user_id", table_name="file_pending_scan")
    op.drop_index("idx_file_pending_scan_unscanned", table_name="file_pending_scan")
    op.drop_table("file_pending_scan")
