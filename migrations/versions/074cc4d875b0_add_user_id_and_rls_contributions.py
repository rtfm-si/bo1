"""add_user_id_and_rls_contributions.

Add user_id column to contributions table with RLS policies.
Critical security fix to prevent cross-user data leakage.

Revision ID: 074cc4d875b0
Revises: 1a74c9a84037
Create Date: 2025-11-30 21:28:38.322969

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "074cc4d875b0"
down_revision: str | Sequence[str] | None = "1a74c9a84037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column (idempotent - check if exists first)
    # Using raw SQL for IF NOT EXISTS support
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'contributions' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE contributions ADD COLUMN user_id VARCHAR(255);
            END IF;
        END $$;
    """)

    # Backfill user_id from sessions table (idempotent - only update NULL values)
    op.execute("""
        UPDATE contributions c
        SET user_id = s.user_id
        FROM sessions s
        WHERE c.session_id = s.id
        AND c.user_id IS NULL
    """)

    # Add foreign key constraint (idempotent - drop if exists first)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_contributions_user_id'
                AND table_name = 'contributions'
            ) THEN
                ALTER TABLE contributions DROP CONSTRAINT fk_contributions_user_id;
            END IF;

            ALTER TABLE contributions
            ADD CONSTRAINT fk_contributions_user_id
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        END $$;
    """)

    # Create index for efficient user queries (idempotent)
    op.execute("CREATE INDEX IF NOT EXISTS idx_contributions_user_id ON contributions (user_id)")

    # Enable RLS (idempotent)
    op.execute("ALTER TABLE contributions ENABLE ROW LEVEL SECURITY")

    # Create RLS policies (idempotent - drop if exists first)
    op.execute("DROP POLICY IF EXISTS contributions_user_isolation ON contributions")
    op.execute("""
        CREATE POLICY contributions_user_isolation ON contributions
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    op.execute("DROP POLICY IF EXISTS contributions_admin_access ON contributions")
    op.execute("""
        CREATE POLICY contributions_admin_access ON contributions
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
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS contributions_admin_access ON contributions")
    op.execute("DROP POLICY IF EXISTS contributions_user_isolation ON contributions")
    op.execute("ALTER TABLE contributions DISABLE ROW LEVEL SECURITY")

    # Drop index
    op.drop_index("idx_contributions_user_id", table_name="contributions")

    # Drop foreign key
    op.drop_constraint("fk_contributions_user_id", "contributions", type_="foreignkey")

    # Drop column
    op.drop_column("contributions", "user_id")
