"""Add final_recommendation column to sessions table.

Revision ID: b1_add_final_rec
Revises: a9_create_tags_table
Create Date: 2025-12-04

Adds final_recommendation column to store the final recommendation
text from deliberation synthesis.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "b1_add_final_rec"
down_revision = "a9_create_tags_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add final_recommendation column to sessions table."""
    # Check if column already exists (idempotent)
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("sessions")]

    if "final_recommendation" not in columns:
        op.add_column(
            "sessions",
            sa.Column("final_recommendation", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Remove final_recommendation column from sessions table."""
    op.drop_column("sessions", "final_recommendation")
