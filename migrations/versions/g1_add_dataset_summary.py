"""Add summary column to datasets table.

Stores LLM-generated natural language summaries of dataset profiles.

Revision ID: g1_add_dataset_summary
Revises: f1_create_datasets
Create Date: 2025-12-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1_add_dataset_summary"
down_revision: str | Sequence[str] | None = "f1_create_datasets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add summary column to datasets table."""
    op.add_column(
        "datasets",
        sa.Column("summary", sa.Text, nullable=True),
    )


def downgrade() -> None:
    """Remove summary column from datasets table."""
    op.drop_column("datasets", "summary")
