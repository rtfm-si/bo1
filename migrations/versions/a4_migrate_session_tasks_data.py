"""Migrate existing session_tasks JSONB data to actions table.

One-time data migration that copies all existing tasks from session_tasks.tasks JSONB
to the new actions table. Maps old status values and parses timeline fields.

Revision ID: a4_migrate_session_tasks_data
Revises: a3_create_action_updates
Create Date: 2025-12-04

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4_migrate_session_tasks_data"
down_revision: str | Sequence[str] | None = "a3_create_action_updates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate data from session_tasks JSONB to actions table."""
    # Migration SQL (raw string for regex patterns)
    op.execute(r"""
        -- Migrate tasks from session_tasks to actions table
        INSERT INTO actions (
            user_id,
            source_session_id,
            title,
            description,
            what_and_how,
            success_criteria,
            kill_criteria,
            status,
            priority,
            category,
            timeline,
            estimated_duration_days,
            confidence,
            source_section,
            sub_problem_index,
            sort_order,
            created_at,
            updated_at
        )
        SELECT
            st.user_id,
            st.session_id,
            task->>'title' AS title,
            task->>'description' AS description,
            COALESCE(
                ARRAY(SELECT jsonb_array_elements_text(task->'what_and_how')),
                '{}'::text[]
            ) AS what_and_how,
            COALESCE(
                ARRAY(SELECT jsonb_array_elements_text(task->'success_criteria')),
                '{}'::text[]
            ) AS success_criteria,
            COALESCE(
                ARRAY(SELECT jsonb_array_elements_text(task->'kill_criteria')),
                '{}'::text[]
            ) AS kill_criteria,
            -- Map old statuses to new values
            CASE
                WHEN COALESCE(st.task_statuses->>(task->>'id'), 'todo') = 'doing' THEN 'in_progress'
                WHEN COALESCE(st.task_statuses->>(task->>'id'), 'todo') = 'done' THEN 'done'
                ELSE 'todo'
            END AS status,
            COALESCE(task->>'priority', 'medium') AS priority,
            COALESCE(task->>'category', 'implementation') AS category,
            task->>'timeline' AS timeline,
            -- Parse timeline to estimated_duration_days
            CASE
                -- Handle common patterns: "2 weeks", "1 month", "3 days"
                WHEN task->>'timeline' ~* '(\d+)\s*(week|wk)s?' THEN
                    (regexp_match(task->>'timeline', '(\d+)', 'i'))[1]::int * 5
                WHEN task->>'timeline' ~* '(\d+)\s*(month|mo)s?' THEN
                    (regexp_match(task->>'timeline', '(\d+)', 'i'))[1]::int * 20
                WHEN task->>'timeline' ~* '(\d+)\s*(day|d)s?' THEN
                    (regexp_match(task->>'timeline', '(\d+)', 'i'))[1]::int
                ELSE NULL
            END AS estimated_duration_days,
            COALESCE((task->>'confidence')::numeric, 0.0) AS confidence,
            task->>'source_section' AS source_section,
            (task->>'sub_problem_index')::int AS sub_problem_index,
            -- Use array position as sort_order
            row_number() OVER (PARTITION BY st.session_id ORDER BY task_idx) - 1 AS sort_order,
            st.extracted_at AS created_at,
            st.extracted_at AS updated_at
        FROM session_tasks st
        CROSS JOIN LATERAL jsonb_array_elements(st.tasks) WITH ORDINALITY AS t(task, task_idx)
        WHERE
            -- Only migrate tasks that have required fields
            task->>'id' IS NOT NULL
            AND task->>'title' IS NOT NULL
            AND task->>'description' IS NOT NULL
            -- Don't migrate if already migrated (in case of re-run)
            AND NOT EXISTS (
                SELECT 1 FROM actions a
                WHERE a.source_session_id = st.session_id
                AND a.title = task->>'title'
            );

        -- Log migration results
        DO $$
        DECLARE
            migrated_count int;
        BEGIN
            SELECT COUNT(*) INTO migrated_count FROM actions;
            RAISE NOTICE 'Migrated % tasks from session_tasks to actions table', migrated_count;
        END $$;
    """)


def downgrade() -> None:
    """Remove migrated actions (destructive - only use if needed)."""
    # WARNING: This will delete all migrated actions
    # In production, you may want to keep this data
    op.execute("""
        -- Delete all actions that came from session_tasks
        DELETE FROM actions
        WHERE source_session_id IN (SELECT session_id FROM session_tasks);

        RAISE NOTICE 'Deleted all migrated actions from actions table';
    """)
