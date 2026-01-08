"""Add multi_dataset_analyses table.

Stores cross-dataset anomaly detection results for 2-5 datasets.
Enables multi-dataset comparison with schema drift and outlier detection.

Revision ID: zzq_multi_dataset_analyses
Revises: zzp_persist_reports_on_delete
Create Date: 2025-01-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "zzq_multi_dataset_analyses"
down_revision: str | Sequence[str] | None = "zzp_persist_reports_on_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create multi_dataset_analyses table."""
    op.create_table(
        "multi_dataset_analyses",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("auth.users.id"), nullable=False),
        # Dataset IDs (2-5 datasets)
        sa.Column("dataset_ids", ARRAY(UUID), nullable=False),
        # Metadata
        sa.Column("name", sa.String(255), nullable=True),  # Optional name like "Q1 2024 Analysis"
        # Results stored as JSONB
        sa.Column(
            "common_schema", JSONB, nullable=True
        ),  # Common columns, partial columns, type consensus
        sa.Column("anomalies", JSONB, nullable=True),  # List of detected anomalies with severity
        sa.Column("dataset_summaries", JSONB, nullable=True),  # Per-dataset summary stats
        sa.Column(
            "pairwise_comparisons", JSONB, nullable=True
        ),  # Results from DatasetComparator for each pair
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Indexes for efficient lookups
    op.create_index(
        "idx_multi_dataset_analyses_user",
        "multi_dataset_analyses",
        ["user_id"],
    )
    op.create_index(
        "idx_multi_dataset_analyses_created",
        "multi_dataset_analyses",
        ["user_id", "created_at"],
    )
    # GIN index for searching dataset_ids array
    op.create_index(
        "idx_multi_dataset_analyses_datasets_gin",
        "multi_dataset_analyses",
        ["dataset_ids"],
        postgresql_using="gin",
    )

    # RLS policies
    op.execute("""
        ALTER TABLE multi_dataset_analyses ENABLE ROW LEVEL SECURITY;

        CREATE POLICY multi_dataset_analyses_user_isolation ON multi_dataset_analyses
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY multi_dataset_analyses_user_insert ON multi_dataset_analyses
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)


def downgrade() -> None:
    """Drop multi_dataset_analyses table."""
    # Drop RLS policies
    op.execute(
        "DROP POLICY IF EXISTS multi_dataset_analyses_user_isolation ON multi_dataset_analyses;"
    )
    op.execute(
        "DROP POLICY IF EXISTS multi_dataset_analyses_user_insert ON multi_dataset_analyses;"
    )

    # Drop indexes and table
    op.drop_index("idx_multi_dataset_analyses_datasets_gin", table_name="multi_dataset_analyses")
    op.drop_index("idx_multi_dataset_analyses_created", table_name="multi_dataset_analyses")
    op.drop_index("idx_multi_dataset_analyses_user", table_name="multi_dataset_analyses")
    op.drop_table("multi_dataset_analyses")
