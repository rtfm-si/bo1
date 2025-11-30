"""add_rls_policies_api_costs

Add Row Level Security (RLS) policies to api_costs table to prevent
cross-user data leakage. Critical security fix.

Policy Design:
1. User Isolation: Users can only see their own API costs
2. Admin Access: Admins can see all API costs for analytics

Revision ID: 9a51aef9277a
Revises: c7d8e9f0a1b2
Create Date: 2025-11-30 21:27:48.788078

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a51aef9277a"
down_revision: str | Sequence[str] | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable RLS on api_costs table
    op.execute("ALTER TABLE api_costs ENABLE ROW LEVEL SECURITY")

    # Policy 1: User isolation - users can only access their own API costs
    # Uses app.current_user_id session variable set by application code
    op.execute("""
        CREATE POLICY api_costs_user_isolation ON api_costs
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    # Policy 2: Admin access - admins can view all API costs for analytics
    # Admins identified by is_admin flag in users table
    op.execute("""
        CREATE POLICY api_costs_admin_access ON api_costs
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
    """Downgrade schema."""
    # Drop policies (must drop before disabling RLS)
    op.execute("DROP POLICY IF EXISTS api_costs_admin_access ON api_costs")
    op.execute("DROP POLICY IF EXISTS api_costs_user_isolation ON api_costs")

    # Disable RLS
    op.execute("ALTER TABLE api_costs DISABLE ROW LEVEL SECURITY")
