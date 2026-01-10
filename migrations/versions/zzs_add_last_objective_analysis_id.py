"""Add last_objective_analysis_id to datasets and expires_at to dataset_objective_analyses.

These columns support:
- Quick access to the most recent objective analysis for a dataset
- Cache expiration for stale analysis results

Revision ID: zzs_last_analysis_id
Revises: zzr_dataset_objective_analyses
Create Date: 2026-01-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "zzs_last_analysis_id"
down_revision: str | Sequence[str] | None = "zzr_dataset_objective_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add last_objective_analysis_id to datasets and expires_at to analyses."""
    # Add expires_at column to dataset_objective_analyses
    op.add_column(
        "dataset_objective_analyses",
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Add last_objective_analysis_id to datasets table
    op.add_column(
        "datasets",
        sa.Column("last_objective_analysis_id", UUID, nullable=True),
    )

    # Create foreign key constraint
    op.create_foreign_key(
        "fk_datasets_last_objective_analysis",
        "datasets",
        "dataset_objective_analyses",
        ["last_objective_analysis_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for expires_at to support cache invalidation queries
    op.create_index(
        "idx_dataset_objective_analyses_expires",
        "dataset_objective_analyses",
        ["expires_at"],
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove added columns."""
    # Drop index
    op.drop_index(
        "idx_dataset_objective_analyses_expires",
        table_name="dataset_objective_analyses",
    )

    # Drop foreign key
    op.drop_constraint(
        "fk_datasets_last_objective_analysis",
        "datasets",
        type_="foreignkey",
    )

    # Drop columns
    op.drop_column("datasets", "last_objective_analysis_id")
    op.drop_column("dataset_objective_analyses", "expires_at")
