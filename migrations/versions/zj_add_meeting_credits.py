"""Add meeting_credits column to users table.

Revision ID: zj_add_meeting_credits
Revises: zi_add_nonprofit_status
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zj_add_meeting_credits"
down_revision: str | Sequence[str] | None = "zi_add_nonprofit_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add meeting_credits column for one-time bundle purchases.

    Columns:
    - meeting_credits: number of prepaid meetings remaining
    """
    op.add_column(
        "users",
        sa.Column(
            "meeting_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of prepaid meeting credits from bundle purchases",
        ),
    )
    # Index for finding users with credits
    op.create_index(
        "ix_users_meeting_credits",
        "users",
        ["meeting_credits"],
        postgresql_where=sa.text("meeting_credits > 0"),
    )


def downgrade() -> None:
    """Remove meeting_credits from users table."""
    op.drop_index("ix_users_meeting_credits", table_name="users")
    op.drop_column("users", "meeting_credits")
