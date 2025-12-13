"""Add stripe customer and subscription columns.

Revision ID: ao1_add_stripe_customer
Revises: an1_add_session_context
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ao1_add_stripe_customer"
down_revision: str | None = "an1_add_session_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Stripe columns to users table."""
    # Add stripe_customer_id and stripe_subscription_id to users
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
    )
    # Index for quick lookups by Stripe customer ID (webhook processing)
    op.create_index(
        "ix_users_stripe_customer_id",
        "users",
        ["stripe_customer_id"],
        unique=True,
        postgresql_where=sa.text("stripe_customer_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove Stripe columns from users table."""
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
