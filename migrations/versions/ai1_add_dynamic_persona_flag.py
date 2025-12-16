"""Add is_dynamic column to personas table for dynamic persona support.

Revision ID: ai1_add_dynamic_persona_flag
Revises: 436ba3057ce9
Create Date: 2025-12-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ai1_add_dynamic_persona_flag"
down_revision: str | Sequence[str] | None = "436ba3057ce9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_dynamic column to personas table."""
    op.add_column(
        "personas",
        sa.Column(
            "is_dynamic",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True for personas auto-generated during meetings",
        ),
    )


def downgrade() -> None:
    """Remove is_dynamic column."""
    op.drop_column("personas", "is_dynamic")
