"""Add billing columns to workspaces table for per-workspace billing.

Revision ID: aq1_add_workspace_billing
Revises: ap1_add_promo_invoice_tracking
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aq1_add_workspace_billing"
down_revision: str | Sequence[str] | None = "ap1_add_promo_invoice_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add billing columns to workspaces table."""
    # Add Stripe customer ID for workspace billing
    op.add_column(
        "workspaces",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
    )

    # Add Stripe subscription ID
    op.add_column(
        "workspaces",
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
    )

    # Add billing email (can differ from owner email)
    op.add_column(
        "workspaces",
        sa.Column("billing_email", sa.String(255), nullable=True),
    )

    # Add subscription tier
    op.add_column(
        "workspaces",
        sa.Column(
            "subscription_tier",
            sa.String(32),
            nullable=False,
            server_default="free",
            comment="Subscription tier: free, starter, pro, enterprise",
        ),
    )

    # Add billing owner (who manages billing, can be reassigned)
    op.add_column(
        "workspaces",
        sa.Column(
            "billing_owner_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who manages billing (defaults to owner)",
        ),
    )

    # Index on stripe_customer_id for webhook lookups
    op.create_index(
        "ix_workspaces_stripe_customer_id",
        "workspaces",
        ["stripe_customer_id"],
        unique=True,
        postgresql_where=sa.text("stripe_customer_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove billing columns from workspaces table."""
    op.drop_index("ix_workspaces_stripe_customer_id", table_name="workspaces")
    op.drop_column("workspaces", "billing_owner_id")
    op.drop_column("workspaces", "subscription_tier")
    op.drop_column("workspaces", "billing_email")
    op.drop_column("workspaces", "stripe_subscription_id")
    op.drop_column("workspaces", "stripe_customer_id")
