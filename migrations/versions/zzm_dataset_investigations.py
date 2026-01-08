"""Add dataset_investigations and dataset_business_context tables.

Stores pre-computed deterministic analyses (8 types) and user-provided
business context for enhanced insight generation.

Revision ID: zzm_dataset_investigations
Revises: zzl_dataset_favourites_reports
Create Date: 2025-01-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "zzm_dataset_investigations"
down_revision: str | Sequence[str] | None = "zzl_dataset_favourites_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset_investigations and dataset_business_context tables."""
    # Investigations table - stores 8 deterministic analyses
    op.create_table(
        "dataset_investigations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "dataset_id",
            UUID,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", UUID, nullable=False),
        # The 8 analysis results (JSONB for each)
        sa.Column("column_roles", JSONB, nullable=True),  # Analysis 1: semantic roles
        sa.Column("missingness", JSONB, nullable=True),  # Analysis 2: null/unique/cardinality
        sa.Column("descriptive_stats", JSONB, nullable=True),  # Analysis 3: stats + heavy hitters
        sa.Column("outliers", JSONB, nullable=True),  # Analysis 4: outlier detection
        sa.Column(
            "correlations", JSONB, nullable=True
        ),  # Analysis 5: correlation matrix + leakage hints
        sa.Column(
            "time_series_readiness", JSONB, nullable=True
        ),  # Analysis 6: date column analysis
        sa.Column(
            "segmentation_suggestions", JSONB, nullable=True
        ),  # Analysis 7: metric/dimension combos
        sa.Column("data_quality", JSONB, nullable=True),  # Analysis 8: quality assessment
        # Metadata
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_dataset_investigations_dataset",
        "dataset_investigations",
        ["dataset_id"],
    )

    # Business context table - user-provided context for enhanced insights
    op.create_table(
        "dataset_business_context",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "dataset_id",
            UUID,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", UUID, nullable=False),
        # User-provided context
        sa.Column("business_goal", sa.Text, nullable=True),
        sa.Column("key_metrics", sa.ARRAY(sa.Text), nullable=True),
        sa.Column("kpis", sa.ARRAY(sa.Text), nullable=True),
        sa.Column("objectives", sa.Text, nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("additional_context", sa.Text, nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_dataset_business_context_dataset",
        "dataset_business_context",
        ["dataset_id"],
    )

    # RLS policies for investigations
    op.execute("""
        ALTER TABLE dataset_investigations ENABLE ROW LEVEL SECURITY;

        CREATE POLICY dataset_investigations_user_isolation ON dataset_investigations
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY dataset_investigations_user_insert ON dataset_investigations
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)

    # RLS policies for business context
    op.execute("""
        ALTER TABLE dataset_business_context ENABLE ROW LEVEL SECURITY;

        CREATE POLICY dataset_business_context_user_isolation ON dataset_business_context
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY dataset_business_context_user_insert ON dataset_business_context
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)


def downgrade() -> None:
    """Drop dataset_investigations and dataset_business_context tables."""
    # Drop RLS policies
    op.execute(
        "DROP POLICY IF EXISTS dataset_investigations_user_isolation ON dataset_investigations;"
    )
    op.execute(
        "DROP POLICY IF EXISTS dataset_investigations_user_insert ON dataset_investigations;"
    )
    op.execute(
        "DROP POLICY IF EXISTS dataset_business_context_user_isolation ON dataset_business_context;"
    )
    op.execute(
        "DROP POLICY IF EXISTS dataset_business_context_user_insert ON dataset_business_context;"
    )

    # Drop tables
    op.drop_index("idx_dataset_business_context_dataset", table_name="dataset_business_context")
    op.drop_table("dataset_business_context")
    op.drop_index("idx_dataset_investigations_dataset", table_name="dataset_investigations")
    op.drop_table("dataset_investigations")
