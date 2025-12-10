"""Fix datasets RLS policy to exclude soft-deleted records.

The original RLS policy did not filter out soft-deleted datasets (deleted_at IS NOT NULL).
This migration updates the policy to only return non-deleted datasets.

Revision ID: h2_fix_datasets_rls
Revises: h1_google_oauth_tokens
Create Date: 2025-12-10
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h2_fix_datasets_rls"
down_revision: str | Sequence[str] | None = "h1_google_oauth_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update datasets RLS policy to exclude soft-deleted records."""
    # Drop existing policy
    op.execute("DROP POLICY IF EXISTS users_own_datasets ON datasets;")

    # Create new policy with soft-delete filter
    op.execute("""
        CREATE POLICY users_own_datasets ON datasets
        FOR ALL
        USING (
            user_id = current_setting('app.current_user_id', true)
            AND deleted_at IS NULL
        );
    """)


def downgrade() -> None:
    """Restore original datasets RLS policy without soft-delete filter."""
    # Restore original policy without soft-delete filter
    op.execute("DROP POLICY IF EXISTS users_own_datasets ON datasets;")
    op.execute("""
        CREATE POLICY users_own_datasets ON datasets
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true));
    """)
