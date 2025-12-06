"""add_user_id_to_facilitator_decisions.

Add user_id column to facilitator_decisions table for RLS support.
Backfills from sessions table and adds proper RLS policies.

Revision ID: b3_user_id_fac_decisions
Revises: b2_add_actions_soft_delete
Create Date: 2025-12-06

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3_user_id_fac_decisions"
down_revision: str | Sequence[str] | None = "b2_add_actions_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column (idempotent - check if exists first)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'facilitator_decisions' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE facilitator_decisions ADD COLUMN user_id VARCHAR(255);
            END IF;
        END $$;
    """)

    # Backfill user_id from sessions table (idempotent - only update NULL values)
    op.execute("""
        UPDATE facilitator_decisions fd
        SET user_id = s.user_id
        FROM sessions s
        WHERE fd.session_id = s.id
        AND fd.user_id IS NULL
    """)

    # Add foreign key constraint (idempotent - drop if exists first)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_facilitator_decisions_user_id'
                AND table_name = 'facilitator_decisions'
            ) THEN
                ALTER TABLE facilitator_decisions DROP CONSTRAINT fk_facilitator_decisions_user_id;
            END IF;

            ALTER TABLE facilitator_decisions
            ADD CONSTRAINT fk_facilitator_decisions_user_id
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        END $$;
    """)

    # Create index for efficient user queries (idempotent)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_facilitator_decisions_user_id "
        "ON facilitator_decisions (user_id)"
    )

    # Create RLS policies (idempotent - drop if exists first)
    # Note: RLS is already enabled on this table from original migration
    op.execute(
        "DROP POLICY IF EXISTS facilitator_decisions_user_isolation ON facilitator_decisions"
    )
    op.execute("""
        CREATE POLICY facilitator_decisions_user_isolation ON facilitator_decisions
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    op.execute("DROP POLICY IF EXISTS facilitator_decisions_admin_access ON facilitator_decisions")
    op.execute("""
        CREATE POLICY facilitator_decisions_admin_access ON facilitator_decisions
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
    op.execute("DROP POLICY IF EXISTS facilitator_decisions_admin_access ON facilitator_decisions")
    op.execute(
        "DROP POLICY IF EXISTS facilitator_decisions_user_isolation ON facilitator_decisions"
    )

    # Drop index
    op.execute("DROP INDEX IF EXISTS idx_facilitator_decisions_user_id")

    # Drop foreign key
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_facilitator_decisions_user_id'
                AND table_name = 'facilitator_decisions'
            ) THEN
                ALTER TABLE facilitator_decisions DROP CONSTRAINT fk_facilitator_decisions_user_id;
            END IF;
        END $$;
    """)

    # Drop column
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'facilitator_decisions' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE facilitator_decisions DROP COLUMN user_id;
            END IF;
        END $$;
    """)
