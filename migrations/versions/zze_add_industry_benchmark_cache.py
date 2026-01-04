"""Add industry benchmark cache for research-based benchmarks.

When no peer benchmark data exists for an industry, we fall back to
research-based benchmarks via Brave/Tavily searches. This table caches
the results globally (shared across all users in same industry).

Also adds research metrics tracking for admin analytics.

Revision ID: zze_add_industry_benchmark_cache
Revises: zzd_add_clarification_source_indexes
Create Date: 2026-01-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "zze_add_industry_benchmark_cache"
down_revision: str | Sequence[str] | None = "zzd_add_clarification_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create industry benchmark cache and research metrics tables."""
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Industry benchmark cache - global cache for research-based benchmarks
    op.create_table(
        "industry_benchmark_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("industry", sa.String(length=255), nullable=False),
        sa.Column(
            "industry_normalized",
            sa.String(length=255),
            nullable=False,
            comment="Lowercase, trimmed industry for matching",
        ),
        # pgvector embedding for similarity search
        sa.Column(
            "industry_embedding",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
            comment="Voyage AI 1024-dim embedding for similarity matching",
        ),
        # Benchmark data as JSONB
        sa.Column(
            "benchmarks",
            postgresql.JSONB(),
            nullable=False,
            comment="Structured benchmark metrics: [{metric, p25, p50, p75, source_url, confidence}, ...]",
        ),
        sa.Column(
            "sources",
            postgresql.JSONB(),
            nullable=True,
            comment="Source URLs and citations",
        ),
        # Metadata
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True,
            comment="Overall confidence score (0-1)",
        ),
        sa.Column(
            "metrics_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of metrics extracted",
        ),
        sa.Column(
            "search_queries",
            postgresql.JSONB(),
            nullable=True,
            comment="Queries used to find these benchmarks",
        ),
        # Timestamps
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            comment="30-day TTL for freshness",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Unique constraint on normalized industry name
    op.create_index(
        "idx_industry_benchmark_cache_industry",
        "industry_benchmark_cache",
        ["industry_normalized"],
        unique=True,
    )

    # Index for expiry cleanup
    op.create_index(
        "idx_industry_benchmark_cache_expires",
        "industry_benchmark_cache",
        ["expires_at"],
    )

    # NOTE: pgvector HNSW index will be added in a separate migration
    # after we confirm the embedding column works. For now, we store
    # embeddings as ARRAY(Float) which can be cast to vector later.

    # Research metrics table - track search effectiveness for admin analytics
    op.create_table(
        "industry_benchmark_research_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("industry", sa.String(length=255), nullable=False),
        sa.Column(
            "query_pattern",
            sa.String(length=500),
            nullable=False,
            comment="Search query used",
        ),
        sa.Column(
            "search_provider",
            sa.String(length=50),
            nullable=False,
            comment="brave or tavily",
        ),
        sa.Column(
            "source_url",
            sa.Text(),
            nullable=True,
            comment="URL that provided useful data",
        ),
        sa.Column(
            "metrics_extracted",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of metrics extracted from this source",
        ),
        sa.Column(
            "confidence_avg",
            sa.Float(),
            nullable=True,
            comment="Average confidence of extracted metrics",
        ),
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this search returned useful results",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if search failed",
        ),
        sa.Column(
            "cost_usd",
            sa.Float(),
            nullable=True,
            comment="Cost of this search operation",
        ),
        sa.Column(
            "searched_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for admin analytics queries
    op.create_index(
        "idx_benchmark_research_metrics_industry",
        "industry_benchmark_research_metrics",
        ["industry"],
    )

    op.create_index(
        "idx_benchmark_research_metrics_searched",
        "industry_benchmark_research_metrics",
        ["searched_at"],
    )

    op.create_index(
        "idx_benchmark_research_metrics_provider",
        "industry_benchmark_research_metrics",
        ["search_provider"],
    )


def downgrade() -> None:
    """Drop industry benchmark cache and research metrics tables."""
    op.drop_table("industry_benchmark_research_metrics")
    op.drop_table("industry_benchmark_cache")
