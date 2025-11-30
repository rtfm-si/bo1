"""add_user_id_and_rls_session_events_tasks

Add user_id column to session_events and session_tasks tables with RLS policies.
Critical security fix to prevent cross-user data leakage.

Changes:
1. Add user_id column to session_events
2. Add user_id column to session_tasks
3. Backfill user_id from sessions table
4. Add NOT NULL constraint and foreign key
5. Create indexes on user_id
6. Enable RLS and create policies

Revision ID: 6ed4a804bd2b
Revises: 9a51aef9277a
Create Date: 2025-11-30 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ed4a804bd2b"
down_revision: str | Sequence[str] | None = "9a51aef9277a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ========== session_events ==========

    # Add user_id column (nullable initially for backfill)
    op.add_column("session_events", sa.Column("user_id", sa.String(length=255), nullable=True))

    # Backfill user_id from sessions table
    op.execute("""
        UPDATE session_events se
        SET user_id = s.user_id
        FROM sessions s
        WHERE se.session_id = s.id
    """)

    # Add NOT NULL constraint after backfill
    op.alter_column("session_events", "user_id", nullable=False)

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_session_events_user_id",
        "session_events",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create index for efficient user queries
    op.create_index("idx_session_events_user_id", "session_events", ["user_id"])

    # Enable RLS and create policies
    op.execute("ALTER TABLE session_events ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY session_events_user_isolation ON session_events
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    op.execute("""
        CREATE POLICY session_events_admin_access ON session_events
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE id = current_setting('app.current_user_id', TRUE)::text
                AND is_admin = true
            )
        )
    """)

    # ========== session_tasks ==========

    # Add user_id column (nullable initially for backfill)
    op.add_column("session_tasks", sa.Column("user_id", sa.String(length=255), nullable=True))

    # Backfill user_id from sessions table
    op.execute("""
        UPDATE session_tasks st
        SET user_id = s.user_id
        FROM sessions s
        WHERE st.session_id = s.id
    """)

    # Add NOT NULL constraint after backfill
    op.alter_column("session_tasks", "user_id", nullable=False)

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_session_tasks_user_id",
        "session_tasks",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Create index for efficient user queries
    op.create_index("idx_session_tasks_user_id", "session_tasks", ["user_id"])

    # Enable RLS and create policies
    op.execute("ALTER TABLE session_tasks ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY session_tasks_user_isolation ON session_tasks
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    op.execute("""
        CREATE POLICY session_tasks_admin_access ON session_tasks
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
    # ========== session_tasks ==========

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS session_tasks_admin_access ON session_tasks")
    op.execute("DROP POLICY IF EXISTS session_tasks_user_isolation ON session_tasks")
    op.execute("ALTER TABLE session_tasks DISABLE ROW LEVEL SECURITY")

    # Drop index
    op.drop_index("idx_session_tasks_user_id", table_name="session_tasks")

    # Drop foreign key
    op.drop_constraint("fk_session_tasks_user_id", "session_tasks", type_="foreignkey")

    # Drop column
    op.drop_column("session_tasks", "user_id")

    # ========== session_events ==========

    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS session_events_admin_access ON session_events")
    op.execute("DROP POLICY IF EXISTS session_events_user_isolation ON session_events")
    op.execute("ALTER TABLE session_events DISABLE ROW LEVEL SECURITY")

    # Drop index
    op.drop_index("idx_session_events_user_id", table_name="session_events")

    # Drop foreign key
    op.drop_constraint("fk_session_events_user_id", "session_events", type_="foreignkey")

    # Drop column
    op.drop_column("session_events", "user_id")
