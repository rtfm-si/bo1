"""Create RLS policies.

Revision ID: 396e8f26d0a5
Revises: ced8f3f148bb
Create Date: 2025-11-14 17:04:59.082869
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "396e8f26d0a5"
down_revision: str | Sequence[str] | None = "ced8f3f148bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Row Level Security (RLS) policies for multi-tenancy."""
    # Sessions table - users can only access their own sessions
    op.execute("""
        CREATE POLICY sessions_user_isolation ON sessions
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    # Contributions table - users can only see contributions from their own sessions
    op.execute("""
        CREATE POLICY contributions_user_isolation ON contributions
        FOR ALL
        USING (
            session_id IN (
                SELECT id FROM sessions
                WHERE user_id = current_setting('app.current_user_id', TRUE)::text
            )
        )
    """)

    # Votes table - users can only see votes from their own sessions
    op.execute("""
        CREATE POLICY votes_user_isolation ON votes
        FOR ALL
        USING (
            session_id IN (
                SELECT id FROM sessions
                WHERE user_id = current_setting('app.current_user_id', TRUE)::text
            )
        )
    """)

    # Audit log table - users can only see their own audit logs
    # Note: Admin users will bypass RLS using service role
    op.execute("""
        CREATE POLICY audit_log_user_isolation ON audit_log
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)


def downgrade() -> None:
    """Drop RLS policies."""
    op.execute("DROP POLICY IF EXISTS sessions_user_isolation ON sessions")
    op.execute("DROP POLICY IF EXISTS contributions_user_isolation ON contributions")
    op.execute("DROP POLICY IF EXISTS votes_user_isolation ON votes")
    op.execute("DROP POLICY IF EXISTS audit_log_user_isolation ON audit_log")
