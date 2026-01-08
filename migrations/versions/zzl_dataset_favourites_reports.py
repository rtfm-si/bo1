"""Add dataset_favourites and dataset_reports tables.

Enables users to favourite charts/insights from dataset analysis
and generate consolidated reports from favourited items.

Revision ID: zzl_dataset_favourites_reports
Revises: zzk_add_column_descriptions
Create Date: 2025-01-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "zzl_dataset_favourites_reports"
down_revision: str | Sequence[str] | None = "zzk_add_column_descriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset_favourites and dataset_reports tables."""
    # Favourites table
    op.create_table(
        "dataset_favourites",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column(
            "dataset_id", UUID, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "favourite_type", sa.String(20), nullable=False
        ),  # 'chart' | 'insight' | 'message'
        # Reference to source (one of these will be set)
        sa.Column(
            "analysis_id",
            UUID,
            sa.ForeignKey("dataset_analyses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "message_id",
            UUID,
            sa.ForeignKey("dataset_messages.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("insight_data", JSONB, nullable=True),  # For insights not in messages
        # Cached display data
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("chart_spec", JSONB, nullable=True),
        sa.Column("figure_json", JSONB, nullable=True),
        # User annotations
        sa.Column("user_note", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        # Unique constraints
        sa.UniqueConstraint("user_id", "dataset_id", "analysis_id", name="uq_favourite_analysis"),
        sa.UniqueConstraint("user_id", "dataset_id", "message_id", name="uq_favourite_message"),
    )

    op.create_index(
        "idx_dataset_favourites_user_dataset",
        "dataset_favourites",
        ["user_id", "dataset_id", "sort_order"],
    )

    # Reports table
    op.create_table(
        "dataset_reports",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column(
            "dataset_id", UUID, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("report_content", JSONB, nullable=False),  # Structured report sections
        sa.Column("favourite_ids", ARRAY(UUID), nullable=False),  # Snapshot of favourites used
        # Generation metadata
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_dataset_reports_user_dataset",
        "dataset_reports",
        ["user_id", "dataset_id", "created_at"],
    )

    # RLS policies for favourites
    op.execute("""
        ALTER TABLE dataset_favourites ENABLE ROW LEVEL SECURITY;

        CREATE POLICY dataset_favourites_user_isolation ON dataset_favourites
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY dataset_favourites_user_insert ON dataset_favourites
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)

    # RLS policies for reports
    op.execute("""
        ALTER TABLE dataset_reports ENABLE ROW LEVEL SECURITY;

        CREATE POLICY dataset_reports_user_isolation ON dataset_reports
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY dataset_reports_user_insert ON dataset_reports
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)


def downgrade() -> None:
    """Drop dataset_favourites and dataset_reports tables."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS dataset_favourites_user_isolation ON dataset_favourites;")
    op.execute("DROP POLICY IF EXISTS dataset_favourites_user_insert ON dataset_favourites;")
    op.execute("DROP POLICY IF EXISTS dataset_reports_user_isolation ON dataset_reports;")
    op.execute("DROP POLICY IF EXISTS dataset_reports_user_insert ON dataset_reports;")

    # Drop tables
    op.drop_index("idx_dataset_reports_user_dataset", table_name="dataset_reports")
    op.drop_table("dataset_reports")
    op.drop_index("idx_dataset_favourites_user_dataset", table_name="dataset_favourites")
    op.drop_table("dataset_favourites")
