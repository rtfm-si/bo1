"""Add context tables.

Add tables for context collection and research caching:
- user_context: Persistent business context per user
- session_clarifications: Expert clarification questions during deliberation
- research_cache: External research results with semantic embeddings

Revision ID: 71a746e3c1d9
Revises: 396e8f26d0a5
Create Date: 2025-11-16 16:15:46.494425
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "71a746e3c1d9"
down_revision: str | Sequence[str] | None = "396e8f26d0a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # user_context table - Persistent business context per user
    op.create_table(
        "user_context",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("business_model", sa.Text, nullable=True),
        sa.Column("target_market", sa.Text, nullable=True),
        sa.Column("product_description", sa.Text, nullable=True),
        sa.Column("revenue", sa.Text, nullable=True),
        sa.Column("customers", sa.Text, nullable=True),
        sa.Column("growth_rate", sa.Text, nullable=True),
        sa.Column("competitors", sa.Text, nullable=True),
        sa.Column("website", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="user_context_unique_user"),
    )
    op.create_index("idx_user_context_user_id", "user_context", ["user_id"])

    # session_clarifications table - Expert questions during deliberation
    op.create_table(
        "session_clarifications",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("asked_by_persona", sa.Text, nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("asked_at_round", sa.Integer, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_clarifications_session", "session_clarifications", ["session_id"])

    # Add CHECK constraint for priority
    op.create_check_constraint(
        "session_clarifications_priority_check",
        "session_clarifications",
        "priority IN ('CRITICAL', 'NICE_TO_HAVE')",
    )

    # research_cache table - External research with semantic embeddings
    op.create_table(
        "research_cache",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column(
            "question_embedding", sa.dialects.postgresql.ARRAY(sa.Float), nullable=True
        ),  # vector(1024) for Voyage AI voyage-3
        sa.Column("answer_summary", sa.Text, nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=True),
        sa.Column("sources", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("source_count", sa.Integer, nullable=True),
        sa.Column("category", sa.Text, nullable=True),
        sa.Column("industry", sa.Text, nullable=True),
        sa.Column(
            "research_date",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("access_count", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("freshness_days", sa.Integer, server_default=sa.text("90"), nullable=False),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("research_cost_usd", sa.Numeric(10, 6), nullable=True),
    )

    # Note: ivfflat index for vector similarity search requires pgvector extension
    # The extension was already enabled in the initial migration
    # For now, we'll use a GIN index on the question text for full-text search
    # Vector indexing will be added when we properly configure pgvector types

    op.create_index("idx_research_cache_category", "research_cache", ["category"])
    op.create_index("idx_research_cache_industry", "research_cache", ["industry"])

    # Add CHECK constraint for confidence
    op.create_check_constraint(
        "research_cache_confidence_check",
        "research_cache",
        "confidence IN ('high', 'medium', 'low')",
    )

    # Enable RLS on new tables
    op.execute("ALTER TABLE user_context ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE session_clarifications ENABLE ROW LEVEL SECURITY")
    # research_cache is shared across users (no RLS needed)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table("research_cache")
    op.drop_table("session_clarifications")
    op.drop_table("user_context")
