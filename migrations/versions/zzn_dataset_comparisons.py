"""Add dataset_comparisons table.

Stores comparison results between two datasets (e.g., Jan vs Feb sales,
Cohort A vs Cohort B). Enables side-by-side analysis.

Revision ID: zzn_dataset_comparisons
Revises: zzm_dataset_investigations
Create Date: 2025-01-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "zzn_dataset_comparisons"
down_revision: str | Sequence[str] | None = "zzm_dataset_investigations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset_comparisons table."""
    op.create_table(
        "dataset_comparisons",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column(
            "dataset_a_id", UUID, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "dataset_b_id", UUID, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
        ),
        # Comparison metadata
        sa.Column("name", sa.String(255), nullable=True),  # Optional name like "Jan vs Feb 2024"
        # Results stored as JSONB
        sa.Column(
            "schema_comparison", JSONB, nullable=True
        ),  # common cols, only_in_a, only_in_b, type mismatches
        sa.Column("statistics_comparison", JSONB, nullable=True),  # per-column stat deltas
        sa.Column(
            "key_metrics_comparison", JSONB, nullable=True
        ),  # metric % changes with significance
        sa.Column("insights", JSONB, nullable=True),  # LLM-generated interpretation
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Indexes for efficient lookups
    op.create_index(
        "idx_dataset_comparisons_user",
        "dataset_comparisons",
        ["user_id"],
    )
    op.create_index(
        "idx_dataset_comparisons_dataset_a",
        "dataset_comparisons",
        ["dataset_a_id"],
    )
    op.create_index(
        "idx_dataset_comparisons_dataset_b",
        "dataset_comparisons",
        ["dataset_b_id"],
    )
    # Composite index for finding comparisons involving a specific dataset
    op.create_index(
        "idx_dataset_comparisons_both",
        "dataset_comparisons",
        ["dataset_a_id", "dataset_b_id"],
    )

    # RLS policies
    op.execute("""
        ALTER TABLE dataset_comparisons ENABLE ROW LEVEL SECURITY;

        CREATE POLICY dataset_comparisons_user_isolation ON dataset_comparisons
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY dataset_comparisons_user_insert ON dataset_comparisons
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)


def downgrade() -> None:
    """Drop dataset_comparisons table."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS dataset_comparisons_user_isolation ON dataset_comparisons;")
    op.execute("DROP POLICY IF EXISTS dataset_comparisons_user_insert ON dataset_comparisons;")

    # Drop indexes and table
    op.drop_index("idx_dataset_comparisons_both", table_name="dataset_comparisons")
    op.drop_index("idx_dataset_comparisons_dataset_b", table_name="dataset_comparisons")
    op.drop_index("idx_dataset_comparisons_dataset_a", table_name="dataset_comparisons")
    op.drop_index("idx_dataset_comparisons_user", table_name="dataset_comparisons")
    op.drop_table("dataset_comparisons")
