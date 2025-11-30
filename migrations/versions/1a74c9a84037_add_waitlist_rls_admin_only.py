"""add_waitlist_rls_admin_only

Add Row Level Security to waitlist table (admin-only access).
Waitlist contains PII (emails) and should only be accessible by admins.

Revision ID: 1a74c9a84037
Revises: 6ed4a804bd2b
Create Date: 2025-11-30 21:28:38.088187

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a74c9a84037"
down_revision: str | Sequence[str] | None = "6ed4a804bd2b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable RLS on waitlist table
    op.execute("ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY")

    # Admin-only policy - only admins can access waitlist data
    # Regular users have no access (waitlist is for admin management only)
    op.execute("""
        CREATE POLICY waitlist_admin_only ON waitlist
        FOR ALL
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE id = current_setting('app.current_user_id', TRUE)::text
                AND is_admin = true
            )
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop policy
    op.execute("DROP POLICY IF EXISTS waitlist_admin_only ON waitlist")

    # Disable RLS
    op.execute("ALTER TABLE waitlist DISABLE ROW LEVEL SECURITY")
