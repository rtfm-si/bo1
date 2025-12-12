"""Add data_retention_days column to users table.

Revision ID: r1_add_user_retention_setting
Revises: q1_add_api_audit_log
Create Date: 2025-12-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "r1_add_user_retention_setting"
down_revision: str | Sequence[str] | None = "q1_add_api_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add data_retention_days column with constraints."""
    op.add_column(
        "users",
        sa.Column(
            "data_retention_days",
            sa.Integer,
            nullable=False,
            server_default="365",
        ),
    )
    # Add check constraint: 30 <= data_retention_days <= 730
    op.create_check_constraint(
        "ck_users_data_retention_days_range",
        "users",
        "data_retention_days >= 30 AND data_retention_days <= 730",
    )


def downgrade() -> None:
    """Remove data_retention_days column."""
    op.drop_constraint("ck_users_data_retention_days_range", "users", type_="check")
    op.drop_column("users", "data_retention_days")
