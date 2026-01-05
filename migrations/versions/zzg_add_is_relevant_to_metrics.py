"""Add is_relevant column to business_metrics.

Revision ID: zzg_add_is_relevant_to_metrics
Revises: zzf_remove_unused_fixed_costs
Create Date: 2026-01-04

Allows users to mark predefined metrics as "not relevant" so they
don't appear in the default view but can be restored later.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "zzg_add_is_relevant_to_metrics"
down_revision = "zzf_remove_unused_fixed_costs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_relevant column with default TRUE."""
    op.add_column(
        "business_metrics",
        sa.Column(
            "is_relevant",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
    )
    # Index for efficient filtering on user_id + is_relevant
    op.create_index(
        "ix_business_metrics_user_relevant",
        "business_metrics",
        ["user_id", "is_relevant"],
        postgresql_where=sa.text("is_relevant = TRUE"),
    )


def downgrade() -> None:
    """Remove is_relevant column and index."""
    op.drop_index("ix_business_metrics_user_relevant", table_name="business_metrics")
    op.drop_column("business_metrics", "is_relevant")
