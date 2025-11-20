"""Enable RLS on users table.

Revision ID: 012a6abb33ac
Revises: 4c18ea4c164f
Create Date: 2025-11-20 19:29:48.911158

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012a6abb33ac"
down_revision: str | Sequence[str] | None = "4c18ea4c164f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable Row Level Security on users table with proper policies."""
    # Enable RLS on users table
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;")

    # Policy: Users can view their own profile
    op.execute("""
        CREATE POLICY users_self_access ON public.users
            FOR SELECT
            USING (id::text = current_setting('app.current_user_id', TRUE)::text);
    """)

    # Policy: System can insert new users during OAuth registration
    op.execute("""
        CREATE POLICY users_system_insert ON public.users
            FOR INSERT
            WITH CHECK (true);
    """)

    # Policy: Users can update their own profile
    op.execute("""
        CREATE POLICY users_self_update ON public.users
            FOR UPDATE
            USING (id::text = current_setting('app.current_user_id', TRUE)::text)
            WITH CHECK (id::text = current_setting('app.current_user_id', TRUE)::text);
    """)


def downgrade() -> None:
    """Disable Row Level Security on users table."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS users_self_update ON public.users;")
    op.execute("DROP POLICY IF EXISTS users_system_insert ON public.users;")
    op.execute("DROP POLICY IF EXISTS users_self_access ON public.users;")

    # Disable RLS
    op.execute("ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;")
