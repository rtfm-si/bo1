"""Extend data retention range from 30-730 to 365-3650 days.

This migration:
1. Updates existing users with retention < 365 days to the new minimum (365)
2. Updates the check constraint to enforce the new range (365-3650 days)

Revision ID: ac1_extend_retention_range
Revises: ab1_create_workspace_invitations
Create Date: 2025-12-13

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ac1_extend_retention_range"
down_revision: str | Sequence[str] | None = "ab1_create_workspace_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend retention range to 365-3650 days."""
    # Step 1: Update existing users with retention < 365 to the new minimum
    op.execute(
        """
        UPDATE users
        SET data_retention_days = 365
        WHERE data_retention_days < 365
        """
    )

    # Step 2: Drop the old constraint
    op.drop_constraint("ck_users_data_retention_days_range", "users", type_="check")

    # Step 3: Create new constraint with extended range (365-3650)
    op.create_check_constraint(
        "ck_users_data_retention_days_range",
        "users",
        "data_retention_days >= 365 AND data_retention_days <= 3650",
    )


def downgrade() -> None:
    """Revert retention range to 30-730 days."""
    # Step 1: Update users with retention > 730 to the old maximum
    op.execute(
        """
        UPDATE users
        SET data_retention_days = 730
        WHERE data_retention_days > 730
        """
    )

    # Step 2: Drop the new constraint
    op.drop_constraint("ck_users_data_retention_days_range", "users", type_="check")

    # Step 3: Restore old constraint (30-730)
    op.create_check_constraint(
        "ck_users_data_retention_days_range",
        "users",
        "data_retention_days >= 30 AND data_retention_days <= 730",
    )
