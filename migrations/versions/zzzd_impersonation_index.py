"""Add composite index to admin_impersonation_sessions for faster lookups.

Revision ID: zzzd_impersonation_index
Revises: zzzc_decision_meta_title
Create Date: 2025-02-05
"""

from alembic import op

revision = "zzzd_impersonation_index"
down_revision = "zzzc_decision_meta_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add composite index for faster active impersonation lookups."""
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS
        ix_admin_impersonation_sessions_active_lookup
        ON admin_impersonation_sessions (admin_user_id, ended_at, expires_at)
        WHERE ended_at IS NULL
    """)


def downgrade() -> None:
    """Remove composite index."""
    op.execute("DROP INDEX IF EXISTS ix_admin_impersonation_sessions_active_lookup")
