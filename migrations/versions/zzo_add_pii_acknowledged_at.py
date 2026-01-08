"""Add pii_acknowledged_at column to datasets.

Tracks when user acknowledged PII warning during upload.

Revision ID: zzo_add_pii_acknowledged_at
Revises: zzn_dataset_comparisons
Create Date: 2026-01-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zzo_add_pii_acknowledged_at"
down_revision: str | Sequence[str] | None = "zzn_dataset_comparisons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add pii_acknowledged_at column."""
    op.add_column(
        "datasets",
        sa.Column(
            "pii_acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when user acknowledged PII warning",
        ),
    )


def downgrade() -> None:
    """Remove pii_acknowledged_at column."""
    op.drop_column("datasets", "pii_acknowledged_at")
