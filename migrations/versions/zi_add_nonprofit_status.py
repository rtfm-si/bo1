"""Add nonprofit status fields to users table.

Revision ID: zi_add_nonprofit_status
Revises: zh_add_key_metrics_config
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zi_add_nonprofit_status"
down_revision: str | Sequence[str] | None = "zh_add_key_metrics_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nonprofit tracking columns to users table.

    Columns:
    - is_nonprofit: boolean flag indicating verified nonprofit status
    - nonprofit_verified_at: timestamp when nonprofit status was verified
    - nonprofit_org_name: name of the nonprofit organization
    """
    op.add_column(
        "users",
        sa.Column(
            "is_nonprofit",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether user is verified as nonprofit/charity",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "nonprofit_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When nonprofit status was verified",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "nonprofit_org_name",
            sa.Text(),
            nullable=True,
            comment="Name of the nonprofit organization",
        ),
    )


def downgrade() -> None:
    """Remove nonprofit columns from users table."""
    op.drop_column("users", "nonprofit_org_name")
    op.drop_column("users", "nonprofit_verified_at")
    op.drop_column("users", "is_nonprofit")
