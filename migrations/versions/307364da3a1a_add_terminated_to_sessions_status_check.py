"""add_terminated_to_sessions_status_check

Revision ID: 307364da3a1a
Revises: zw_add_checkpoint_resume_fields
Create Date: 2025-12-31 18:08:42.022556

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "307364da3a1a"
down_revision: str | Sequence[str] | None = "zw_add_checkpoint_resume_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 'terminated' to sessions_status_check constraint."""
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_status_check")
    op.execute("""
        ALTER TABLE sessions ADD CONSTRAINT sessions_status_check
        CHECK (status::text = ANY (ARRAY[
            'created', 'running', 'completed', 'failed',
            'killed', 'deleted', 'paused', 'terminated'
        ]::text[]))
    """)


def downgrade() -> None:
    """Remove 'terminated' from sessions_status_check constraint."""
    op.execute("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_status_check")
    op.execute("""
        ALTER TABLE sessions ADD CONSTRAINT sessions_status_check
        CHECK (status::text = ANY (ARRAY[
            'created', 'running', 'completed', 'failed',
            'killed', 'deleted', 'paused'
        ]::text[]))
    """)
