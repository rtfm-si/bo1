"""Add homepage_featured columns to published_decisions.

Revision ID: zzz_featured_decisions
Revises: zzz_add_benchmark_timestamps
Create Date: 2026-02-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zzz_featured_decisions"
down_revision: str | Sequence[str] | None = "zzz_add_benchmark_timestamps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add homepage_featured and homepage_order columns."""
    # Add homepage_featured boolean column
    op.add_column(
        "published_decisions",
        sa.Column(
            "homepage_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this decision appears on homepage",
        ),
    )

    # Add homepage_order for sorting featured decisions
    op.add_column(
        "published_decisions",
        sa.Column(
            "homepage_order",
            sa.Integer(),
            nullable=True,
            comment="Sort order for homepage display (lower = first)",
        ),
    )

    # Partial index for efficient homepage queries
    op.create_index(
        "ix_published_decisions_homepage",
        "published_decisions",
        ["homepage_featured", "homepage_order"],
        postgresql_where=sa.text("homepage_featured = true"),
    )


def downgrade() -> None:
    """Remove homepage_featured columns."""
    op.drop_index("ix_published_decisions_homepage", table_name="published_decisions")
    op.drop_column("published_decisions", "homepage_order")
    op.drop_column("published_decisions", "homepage_featured")
