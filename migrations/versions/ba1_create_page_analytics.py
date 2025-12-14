"""Create page_views and conversion_events tables for landing page analytics.

Tracks:
- Page views with geo data (country, region), referrer, session_id, duration
- Conversion events (signup_click, signup_complete) with source path

Revision ID: ba1_create_page_analytics
Revises: ax1_add_cost_calculator_defaults
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ba1_create_page_analytics"
down_revision: str | Sequence[str] | None = "ax1_add_cost_calculator_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create page_views and conversion_events tables."""
    # Create page_views table
    op.create_table(
        "page_views",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column("path", sa.String(500), nullable=False, comment="Page path (e.g., /, /pricing)"),
        sa.Column(
            "country", sa.String(2), nullable=True, comment="ISO 3166-1 alpha-2 country code"
        ),
        sa.Column("region", sa.String(100), nullable=True, comment="Region/state name"),
        sa.Column("city", sa.String(100), nullable=True, comment="City name (optional)"),
        sa.Column("referrer", sa.String(2000), nullable=True, comment="HTTP referer header"),
        sa.Column(
            "session_id",
            sa.String(64),
            nullable=False,
            index=True,
            comment="Visitor session identifier (fingerprint or cookie)",
        ),
        sa.Column("user_agent", sa.String(500), nullable=True, comment="Browser user agent"),
        sa.Column(
            "duration_ms", sa.Integer, nullable=True, comment="Time spent on page in milliseconds"
        ),
        sa.Column(
            "scroll_depth", sa.Integer, nullable=True, comment="Max scroll depth percentage (0-100)"
        ),
        sa.Column(
            "is_bot",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="Flagged as bot traffic",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional metadata (screen size, etc.)",
        ),
    )

    # Create conversion_events table
    op.create_table(
        "conversion_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column(
            "event_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="Event type: signup_click, signup_complete, cta_click",
        ),
        sa.Column(
            "source_path", sa.String(500), nullable=False, comment="Page where event occurred"
        ),
        sa.Column(
            "session_id",
            sa.String(64),
            nullable=False,
            index=True,
            comment="Visitor session identifier",
        ),
        sa.Column("element_id", sa.String(100), nullable=True, comment="ID of clicked element"),
        sa.Column("element_text", sa.String(200), nullable=True, comment="Text of clicked element"),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional event data",
        ),
    )

    # Create indexes for analytics queries
    # Index on timestamp directly - queries can use date range filters
    op.create_index(
        "ix_page_views_timestamp_path",
        "page_views",
        ["timestamp", "path"],
    )
    op.create_index(
        "ix_page_views_country",
        "page_views",
        ["country"],
        postgresql_where=sa.text("country IS NOT NULL"),
    )
    op.create_index(
        "ix_conversion_events_timestamp_type",
        "conversion_events",
        ["timestamp", "event_type"],
    )


def downgrade() -> None:
    """Drop page_views and conversion_events tables."""
    op.drop_index("ix_conversion_events_timestamp_type", table_name="conversion_events")
    op.drop_index("ix_page_views_country", table_name="page_views")
    op.drop_index("ix_page_views_timestamp_path", table_name="page_views")
    op.drop_table("conversion_events")
    op.drop_table("page_views")
