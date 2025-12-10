"""Create dataset_analyses table.

Stores query/chart results for analysis history and gallery display.

Revision ID: g2_dataset_analyses
Revises: g1_add_dataset_summary
Create Date: 2025-12-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "g2_dataset_analyses"
down_revision: str | Sequence[str] | None = "g1_add_dataset_summary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset_analyses table."""
    op.create_table(
        "dataset_analyses",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        # Query/chart specs
        sa.Column("query_spec", JSONB, nullable=True),
        sa.Column("chart_spec", JSONB, nullable=True),
        # Preview of query results (first 10 rows)
        sa.Column("query_result_preview", JSONB, nullable=True),
        # Chart storage in Spaces
        sa.Column("chart_key", sa.String(length=500), nullable=True),
        # Title for gallery display
        sa.Column("title", sa.String(length=255), nullable=True),
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
            name="fk_dataset_analyses_dataset_id",
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_dataset_analyses_dataset_created",
        "dataset_analyses",
        ["dataset_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_dataset_analyses_user_id", "dataset_analyses", ["user_id"])

    # Enable RLS
    op.execute("ALTER TABLE dataset_analyses ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY users_own_dataset_analyses ON dataset_analyses
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true));
    """)


def downgrade() -> None:
    """Drop dataset_analyses table."""
    op.execute("DROP POLICY IF EXISTS users_own_dataset_analyses ON dataset_analyses;")
    op.drop_table("dataset_analyses")
