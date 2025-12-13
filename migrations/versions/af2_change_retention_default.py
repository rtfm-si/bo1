"""Change retention default to 730 days and allow -1 (forever).

This migration:
1. Updates the default data_retention_days to 730 (2 years)
2. Updates the check constraint to allow -1 (forever) OR 365-1095 (1-3 years)
3. Existing users keep their current settings (no data migration)

Revision ID: af2_change_retention_default
Revises: 436ba3057ce9
Create Date: 2025-12-13

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "af2_change_retention_default"
down_revision: str | Sequence[str] | None = "436ba3057ce9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change retention default and allow forever (-1)."""
    # Step 1: Drop the old constraint
    op.drop_constraint("ck_users_data_retention_days_range", "users", type_="check")

    # Step 2: Create new constraint allowing -1 (forever) OR 365-1095
    op.create_check_constraint(
        "ck_users_data_retention_days_range",
        "users",
        "data_retention_days = -1 OR (data_retention_days >= 365 AND data_retention_days <= 1095)",
    )

    # Step 3: Update the column default to 730 (2 years)
    op.alter_column(
        "users",
        "data_retention_days",
        server_default="730",
    )


def downgrade() -> None:
    """Revert to previous retention constraints."""
    # Step 1: Update any users with -1 to old max (1095, which fits old constraint)
    op.execute(
        """
        UPDATE users
        SET data_retention_days = 1095
        WHERE data_retention_days = -1
        """
    )

    # Step 2: Drop the new constraint
    op.drop_constraint("ck_users_data_retention_days_range", "users", type_="check")

    # Step 3: Restore old constraint (365-3650)
    op.create_check_constraint(
        "ck_users_data_retention_days_range",
        "users",
        "data_retention_days >= 365 AND data_retention_days <= 3650",
    )

    # Step 4: Restore old default
    op.alter_column(
        "users",
        "data_retention_days",
        server_default="365",
    )
