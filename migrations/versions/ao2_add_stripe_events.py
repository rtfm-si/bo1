"""Add stripe_events table for webhook idempotency.

Revision ID: ao2_add_stripe_events
Revises: ao1_add_stripe_customer
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ao2_add_stripe_events"
down_revision: str | None = "ao1_add_stripe_customer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create stripe_events table for webhook idempotency."""
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "event_id",
            sa.String(255),
            nullable=False,
            comment="Stripe event ID (evt_...)",
        ),
        sa.Column(
            "event_type",
            sa.String(100),
            nullable=False,
            comment="Event type (e.g., checkout.session.completed)",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.String(255),
            nullable=True,
            comment="Associated Stripe customer ID",
        ),
        sa.Column(
            "subscription_id",
            sa.String(255),
            nullable=True,
            comment="Associated subscription ID if applicable",
        ),
        sa.Column(
            "payload_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 hash of event payload for verification",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Primary index for idempotency checks
    op.create_index(
        "ix_stripe_events_event_id",
        "stripe_events",
        ["event_id"],
        unique=True,
    )
    # Index for customer-based queries
    op.create_index(
        "ix_stripe_events_customer_id",
        "stripe_events",
        ["customer_id"],
    )
    # Index for cleanup of old events
    op.create_index(
        "ix_stripe_events_processed_at",
        "stripe_events",
        ["processed_at"],
    )


def downgrade() -> None:
    """Drop stripe_events table."""
    op.drop_index("ix_stripe_events_processed_at", table_name="stripe_events")
    op.drop_index("ix_stripe_events_customer_id", table_name="stripe_events")
    op.drop_index("ix_stripe_events_event_id", table_name="stripe_events")
    op.drop_table("stripe_events")
