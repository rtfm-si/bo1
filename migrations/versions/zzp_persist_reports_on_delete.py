"""Persist dataset reports when dataset is deleted.

Changes FK constraint from CASCADE to SET NULL so reports survive dataset deletion.
Makes dataset_id nullable on dataset_reports table.

Revision ID: zzp_persist_reports_on_delete
Revises: zzo_add_pii_acknowledged_at
Create Date: 2026-01-08

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "zzp_persist_reports_on_delete"
down_revision: str | Sequence[str] | None = "zzo_add_pii_acknowledged_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change FK to SET NULL and make dataset_id nullable."""
    # Drop existing FK constraint with CASCADE
    op.drop_constraint(
        "dataset_reports_dataset_id_fkey",
        "dataset_reports",
        type_="foreignkey",
    )

    # Make column nullable
    op.alter_column(
        "dataset_reports",
        "dataset_id",
        existing_type=UUID,
        nullable=True,
    )

    # Add new FK constraint with SET NULL
    op.create_foreign_key(
        "dataset_reports_dataset_id_fkey",
        "dataset_reports",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Restore CASCADE FK and non-nullable dataset_id."""
    # Drop SET NULL FK constraint
    op.drop_constraint(
        "dataset_reports_dataset_id_fkey",
        "dataset_reports",
        type_="foreignkey",
    )

    # Note: This will fail if there are NULL dataset_ids
    # Those rows would need to be deleted first
    op.alter_column(
        "dataset_reports",
        "dataset_id",
        existing_type=UUID,
        nullable=False,
    )

    # Restore CASCADE FK constraint
    op.create_foreign_key(
        "dataset_reports_dataset_id_fkey",
        "dataset_reports",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="CASCADE",
    )
