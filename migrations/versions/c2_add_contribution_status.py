"""Add status column to contributions for in-flight tracking.

Supports session state recovery:
- in_flight: Contribution persisted before LangGraph checkpoint
- committed: Successfully checkpointed
- rolled_back: Discarded during recovery

Revision ID: c2_add_contribution_status
Revises: ba2_create_blog_posts
Create Date: 2025-12-14

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2_add_contribution_status"
down_revision: str | None = "ba2_create_blog_posts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add status column to contributions table."""
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'contributions' AND column_name = 'status'
            ) THEN
                ALTER TABLE contributions ADD COLUMN status VARCHAR(20) DEFAULT 'committed';
            END IF;
        END $$;
    """)

    # Create index for finding in-flight contributions during recovery
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contributions_status
        ON contributions (status)
        WHERE status = 'in_flight'
    """)

    # Add check constraint for valid status values
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.constraint_column_usage
                WHERE constraint_name = 'chk_contributions_status'
            ) THEN
                ALTER TABLE contributions
                ADD CONSTRAINT chk_contributions_status
                CHECK (status IN ('in_flight', 'committed', 'rolled_back'));
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove status column from contributions table."""
    op.execute("ALTER TABLE contributions DROP CONSTRAINT IF EXISTS chk_contributions_status")
    op.execute("DROP INDEX IF EXISTS idx_contributions_status")
    op.execute("ALTER TABLE contributions DROP COLUMN IF EXISTS status")
