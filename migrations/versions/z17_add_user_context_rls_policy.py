"""Add RLS policies to user_context table.

The user_context table has RLS enabled but no policies, causing 500 errors
when users try to access their context. This migration adds user isolation
and admin access policies matching the pattern from recommendations table.

Revision ID: z17_add_user_context_rls_policy
Revises: z16_enable_pg_stat_statements
Create Date: 2025-12-23
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z17_user_context_rls"
down_revision: str | Sequence[str] | None = "z16_enable_pg_stat_statements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add RLS policies to user_context table."""
    # Create user isolation policy (idempotent - drop if exists first)
    op.execute("DROP POLICY IF EXISTS user_context_user_isolation ON user_context")
    op.execute("""
        CREATE POLICY user_context_user_isolation ON user_context
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    # Create admin access policy for read operations
    op.execute("DROP POLICY IF EXISTS user_context_admin_access ON user_context")
    op.execute("""
        CREATE POLICY user_context_admin_access ON user_context
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE id = current_setting('app.current_user_id', TRUE)::text
                AND is_admin = true
            )
        )
    """)


def downgrade() -> None:
    """Remove RLS policies from user_context table."""
    op.execute("DROP POLICY IF EXISTS user_context_admin_access ON user_context")
    op.execute("DROP POLICY IF EXISTS user_context_user_isolation ON user_context")
