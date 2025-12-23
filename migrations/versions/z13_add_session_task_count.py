"""Denormalize task_count into sessions table.

Adds task_count column to sessions table with PostgreSQL trigger to auto-update
on session_tasks INSERT/UPDATE/DELETE. Eliminates LEFT JOIN in list_by_user()
for O(1) read performance.

Revision ID: z13_add_session_task_count
Revises: z12_calendar_sync_preference
Create Date: 2025-12-22
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z13_add_session_task_count"
down_revision: str | Sequence[str] | None = "z12_calendar_sync_preference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add task_count column to sessions and create update trigger."""
    # 1. Add task_count column with default 0
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS task_count INTEGER DEFAULT 0 NOT NULL;
    """)

    # 2. Backfill from existing session_tasks
    op.execute("""
        UPDATE sessions s
        SET task_count = COALESCE(st.total_tasks, 0)
        FROM session_tasks st
        WHERE st.session_id = s.id;
    """)

    # 3. Create trigger function to update session task_count
    op.execute("""
        CREATE OR REPLACE FUNCTION update_session_task_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE sessions
                SET task_count = NEW.total_tasks
                WHERE id = NEW.session_id;
                RETURN NEW;
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.total_tasks IS DISTINCT FROM NEW.total_tasks THEN
                    UPDATE sessions
                    SET task_count = NEW.total_tasks
                    WHERE id = NEW.session_id;
                END IF;
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE sessions
                SET task_count = 0
                WHERE id = OLD.session_id;
                RETURN OLD;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 4. Create triggers for INSERT, UPDATE, DELETE on session_tasks
    op.execute("""
        DROP TRIGGER IF EXISTS trg_session_tasks_insert ON session_tasks;
        CREATE TRIGGER trg_session_tasks_insert
        AFTER INSERT ON session_tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_session_task_count();
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_session_tasks_update ON session_tasks;
        CREATE TRIGGER trg_session_tasks_update
        AFTER UPDATE OF total_tasks ON session_tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_session_task_count();
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_session_tasks_delete ON session_tasks;
        CREATE TRIGGER trg_session_tasks_delete
        AFTER DELETE ON session_tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_session_task_count();
    """)


def downgrade() -> None:
    """Remove task_count column and triggers."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_session_tasks_insert ON session_tasks;")
    op.execute("DROP TRIGGER IF EXISTS trg_session_tasks_update ON session_tasks;")
    op.execute("DROP TRIGGER IF EXISTS trg_session_tasks_delete ON session_tasks;")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_session_task_count();")

    # Drop column
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS task_count;")
