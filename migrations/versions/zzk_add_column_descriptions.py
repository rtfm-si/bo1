"""Add column_descriptions JSONB to datasets table.

Stores user-editable descriptions for each column in a dataset.
Format: {"column_name": "user description", ...}

Revision ID: zzk_add_column_descriptions
Revises: zzj_add_priority_to_metric_templates
Create Date: 2025-01-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "zzk_add_column_descriptions"
down_revision: str | Sequence[str] | None = "zzj_priority_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add column_descriptions JSONB field."""
    op.add_column(
        "datasets",
        sa.Column(
            "column_descriptions",
            JSONB,
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment="User-editable descriptions for columns: {column_name: description}",
        ),
    )


def downgrade() -> None:
    """Remove column_descriptions field."""
    op.drop_column("datasets", "column_descriptions")
