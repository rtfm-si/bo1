"""Add user_id and RLS policies to recommendations table.

Adds user_id column to recommendations table for RLS enforcement.
Backfills from sessions table and creates user isolation + admin access policies.

Revision ID: z14_add_recommendations_user_id_rls
Revises: z13_add_session_task_count
Create Date: 2025-12-22
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z14_recommendations_rls"
down_revision: str | Sequence[str] | None = "z13_add_session_task_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add user_id column and RLS policies to recommendations."""
    # 1. Add user_id column (nullable initially)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'recommendations' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE recommendations ADD COLUMN user_id VARCHAR(255);
            END IF;
        END $$;
    """)

    # 2. Backfill user_id from sessions table (only for existing records with NULL user_id)
    op.execute("""
        UPDATE recommendations r
        SET user_id = s.user_id
        FROM sessions s
        WHERE r.session_id = s.id
        AND r.user_id IS NULL
        AND s.user_id IS NOT NULL
    """)

    # 3. Add foreign key constraint (idempotent)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_recommendations_user_id'
                AND table_name = 'recommendations'
            ) THEN
                ALTER TABLE recommendations DROP CONSTRAINT fk_recommendations_user_id;
            END IF;

            ALTER TABLE recommendations
            ADD CONSTRAINT fk_recommendations_user_id
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        END $$;
    """)

    # 4. Create index for efficient user queries (idempotent)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations (user_id)"
    )

    # 5. Create RLS policies (idempotent - drop if exists first)
    # Note: RLS is already enabled on this table from 80cf34f1b577 migration
    op.execute("DROP POLICY IF EXISTS recommendations_user_isolation ON recommendations")
    op.execute("""
        CREATE POLICY recommendations_user_isolation ON recommendations
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    op.execute("DROP POLICY IF EXISTS recommendations_admin_access ON recommendations")
    op.execute("""
        CREATE POLICY recommendations_admin_access ON recommendations
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
    """Remove user_id column and RLS policies from recommendations."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS recommendations_admin_access ON recommendations")
    op.execute("DROP POLICY IF EXISTS recommendations_user_isolation ON recommendations")

    # Drop index
    op.execute("DROP INDEX IF EXISTS idx_recommendations_user_id")

    # Drop foreign key
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_recommendations_user_id'
                AND table_name = 'recommendations'
            ) THEN
                ALTER TABLE recommendations DROP CONSTRAINT fk_recommendations_user_id;
            END IF;
        END $$;
    """)

    # Drop column
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'recommendations' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE recommendations DROP COLUMN user_id;
            END IF;
        END $$;
    """)
