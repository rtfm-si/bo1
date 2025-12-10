"""Create datasets and dataset_profiles tables.

Data ingestion foundation for the data analysis platform.

Revision ID: f1_create_datasets
Revises: e1_add_clarifications
Create Date: 2025-12-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "f1_create_datasets"
down_revision: str | Sequence[str] | None = "e1_add_clarifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create datasets and dataset_profiles tables."""
    # Create datasets table
    op.create_table(
        "datasets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Source type: csv, sheets, or future integrations
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
            server_default="csv",
        ),
        # Original source location (Sheets URL, etc.)
        sa.Column("source_uri", sa.Text, nullable=True),
        # Spaces object key (path in bucket)
        sa.Column("file_key", sa.String(length=500), nullable=True),
        # Dataset metadata
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("column_count", sa.Integer, nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Soft delete
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Check constraint for source_type
        sa.CheckConstraint(
            "source_type IN ('csv', 'sheets', 'api')",
            name="ck_datasets_source_type",
        ),
    )

    # Create dataset_profiles table (per-column statistics)
    op.create_table(
        "dataset_profiles",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", UUID(as_uuid=True), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        # Inferred data type (string, integer, float, date, currency, percentage, etc.)
        sa.Column("data_type", sa.String(length=50), nullable=False),
        # Statistics
        sa.Column("null_count", sa.Integer, nullable=True),
        sa.Column("unique_count", sa.Integer, nullable=True),
        sa.Column("min_value", sa.String(length=255), nullable=True),
        sa.Column("max_value", sa.String(length=255), nullable=True),
        sa.Column("mean_value", sa.Float, nullable=True),
        # Sample values for preview
        sa.Column("sample_values", JSONB, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Foreign key constraint
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_dataset_profiles_dataset_id",
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])
    op.create_index("ix_datasets_created_at", "datasets", ["created_at"])
    op.create_index("ix_datasets_deleted_at", "datasets", ["deleted_at"])
    op.create_index("ix_dataset_profiles_dataset_id", "dataset_profiles", ["dataset_id"])

    # Create updated_at trigger for datasets
    op.execute("""
        CREATE OR REPLACE FUNCTION update_datasets_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER update_datasets_updated_at
        BEFORE UPDATE ON datasets
        FOR EACH ROW
        EXECUTE FUNCTION update_datasets_updated_at();
    """)

    # Enable RLS on datasets
    op.execute("ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY users_own_datasets ON datasets
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true));
    """)

    # Enable RLS on dataset_profiles (via dataset ownership)
    op.execute("ALTER TABLE dataset_profiles ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY users_own_dataset_profiles ON dataset_profiles
        FOR ALL
        USING (
            dataset_id IN (
                SELECT id FROM datasets
                WHERE user_id = current_setting('app.current_user_id', true)
            )
        );
    """)


def downgrade() -> None:
    """Drop datasets and dataset_profiles tables."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS users_own_dataset_profiles ON dataset_profiles;")
    op.execute("DROP POLICY IF EXISTS users_own_datasets ON datasets;")

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS update_datasets_updated_at ON datasets;")
    op.execute("DROP FUNCTION IF EXISTS update_datasets_updated_at;")

    # Drop tables (profiles first due to FK)
    op.drop_table("dataset_profiles")
    op.drop_table("datasets")
