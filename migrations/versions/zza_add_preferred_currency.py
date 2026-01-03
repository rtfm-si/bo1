"""Add preferred_currency column to users table.

Stores user's preferred currency for metric display (GBP/USD/EUR).
Default: GBP (UK-focused product).

Revision ID: zza_add_preferred_currency
Revises: zy_add_dataset_conversations
Create Date: 2026-01-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "zza_add_preferred_currency"
down_revision: str = "zy_add_dataset_conversations"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add preferred_currency column to users."""
    op.add_column(
        "users",
        sa.Column(
            "preferred_currency",
            sa.String(3),
            nullable=False,
            server_default="GBP",
            comment="Preferred currency for metric display: GBP, USD, EUR",
        ),
    )


def downgrade() -> None:
    """Remove preferred_currency column."""
    op.drop_column("users", "preferred_currency")
