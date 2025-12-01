"""add_missing_recommendations_columns

Revision ID: 0eb64c2f78e5
Revises: f29ed88cde9d
Create Date: 2025-12-01 19:59:37.185787

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0eb64c2f78e5"
down_revision: str | Sequence[str] | None = "f29ed88cde9d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing columns to recommendations table if they don't exist."""
    # Check and add columns if they don't exist
    # This is idempotent - safe to run multiple times

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col["name"] for col in inspector.get_columns("recommendations")}

    # Add sub_problem_index if missing
    if "sub_problem_index" not in existing_columns:
        op.add_column("recommendations", sa.Column("sub_problem_index", sa.Integer, nullable=True))

    # Add persona_code if missing
    if "persona_code" not in existing_columns:
        op.add_column(
            "recommendations",
            sa.Column(
                "persona_code", sa.String(length=50), nullable=False, server_default="unknown"
            ),
        )
        # Remove server_default after adding the column
        op.alter_column("recommendations", "persona_code", server_default=None)

    # Add persona_name if missing
    if "persona_name" not in existing_columns:
        op.add_column(
            "recommendations", sa.Column("persona_name", sa.String(length=255), nullable=True)
        )

    # Add reasoning if missing
    if "reasoning" not in existing_columns:
        op.add_column("recommendations", sa.Column("reasoning", sa.Text, nullable=True))

    # Add confidence if missing
    if "confidence" not in existing_columns:
        op.add_column(
            "recommendations",
            sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        )

    # Add conditions if missing
    if "conditions" not in existing_columns:
        op.add_column("recommendations", sa.Column("conditions", sa.JSON, nullable=True))

    # Add weight if missing
    if "weight" not in existing_columns:
        op.add_column(
            "recommendations", sa.Column("weight", sa.Numeric(precision=3, scale=2), nullable=True)
        )

    # Add created_at if missing
    if "created_at" not in existing_columns:
        op.add_column(
            "recommendations",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    """Remove the columns we added."""
    # Note: Only drop columns that we added, not ones that were already there
    op.drop_column("recommendations", "created_at")
    op.drop_column("recommendations", "weight")
    op.drop_column("recommendations", "conditions")
    op.drop_column("recommendations", "confidence")
    op.drop_column("recommendations", "reasoning")
    op.drop_column("recommendations", "persona_name")
    op.drop_column("recommendations", "persona_code")
    op.drop_column("recommendations", "sub_problem_index")
