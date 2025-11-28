"""Create api_costs table.

Comprehensive API cost tracking for all AI services (Anthropic, Voyage, Brave, Tavily).
Tracks token usage, costs, cache metrics, and optimization savings.

Revision ID: c7d8e9f0a1b2
Revises: ba10a10c032f
Create Date: 2025-11-28 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: str | Sequence[str] | None = "ba10a10c032f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ============================================================================
    # 1. api_costs: Centralized cost tracking for all AI services
    # ============================================================================

    op.create_table(
        "api_costs",
        sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column(
            "request_id",
            UUID(as_uuid=True),
            nullable=False,
            unique=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        # Session linkage
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        # Provider & operation
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("operation_type", sa.String(length=50), nullable=False),
        # Context (for attribution)
        sa.Column("node_name", sa.String(length=100), nullable=True),
        sa.Column("phase", sa.String(length=50), nullable=True),
        sa.Column("persona_name", sa.String(length=100), nullable=True),
        sa.Column("round_number", sa.Integer(), nullable=True),
        sa.Column("sub_problem_index", sa.Integer(), nullable=True),
        # Token usage
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_tokens",
            sa.Integer(),
            sa.Computed("input_tokens + output_tokens", persisted=True),
            nullable=True,
        ),
        # Cache metrics (Anthropic)
        sa.Column("cache_creation_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_read_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
        # Cost breakdown (USD)
        sa.Column(
            "input_cost", sa.Numeric(precision=12, scale=8), nullable=False, server_default="0"
        ),
        sa.Column(
            "output_cost", sa.Numeric(precision=12, scale=8), nullable=False, server_default="0"
        ),
        sa.Column(
            "cache_write_cost",
            sa.Numeric(precision=12, scale=8),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "cache_read_cost", sa.Numeric(precision=12, scale=8), nullable=False, server_default="0"
        ),
        sa.Column("total_cost", sa.Numeric(precision=12, scale=8), nullable=False),
        # Optimization tracking
        sa.Column("optimization_type", sa.String(length=50), nullable=True),
        sa.Column("cost_without_optimization", sa.Numeric(precision=12, scale=8), nullable=True),
        # Performance
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Metadata
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        # Foreign keys
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        # Constraints
        sa.CheckConstraint(
            "provider IN ('anthropic', 'voyage', 'brave', 'tavily')", name="check_provider"
        ),
        sa.CheckConstraint("total_cost >= 0", name="check_cost_positive"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ============================================================================
    # 2. Indexes for common queries
    # ============================================================================

    # Session and user lookups
    op.create_index("idx_api_costs_session", "api_costs", ["session_id"])
    op.create_index("idx_api_costs_user", "api_costs", ["user_id"])

    # Time-based queries
    op.create_index(
        "idx_api_costs_created",
        "api_costs",
        ["created_at"],
        postgresql_using="btree",
        postgresql_ops={"created_at": "DESC"},
    )

    # Provider and model filtering
    op.create_index("idx_api_costs_provider", "api_costs", ["provider", "model_name"])

    # Node and phase filtering
    op.create_index("idx_api_costs_node", "api_costs", ["node_name"])
    op.create_index("idx_api_costs_phase", "api_costs", ["phase"])

    # Composite index for cost analysis
    op.create_index(
        "idx_api_costs_analysis",
        "api_costs",
        [sa.text("created_at DESC"), "session_id", "provider", "total_cost"],
    )

    # GIN index for JSONB metadata queries
    op.create_index("idx_api_costs_metadata", "api_costs", ["metadata"], postgresql_using="gin")

    # ============================================================================
    # 3. Add table and column comments
    # ============================================================================

    op.execute("""
        COMMENT ON TABLE api_costs IS 'Centralized cost tracking for all AI API calls (Anthropic, Voyage, Brave, Tavily)';
        COMMENT ON COLUMN api_costs.request_id IS 'Unique request identifier (UUID)';
        COMMENT ON COLUMN api_costs.session_id IS 'Session identifier (matches sessions.id)';
        COMMENT ON COLUMN api_costs.user_id IS 'User identifier (matches users.id)';
        COMMENT ON COLUMN api_costs.provider IS 'AI provider (anthropic, voyage, brave, tavily)';
        COMMENT ON COLUMN api_costs.model_name IS 'Model name (e.g., claude-sonnet-4-5, voyage-3)';
        COMMENT ON COLUMN api_costs.operation_type IS 'Operation type (completion, embedding, search)';
        COMMENT ON COLUMN api_costs.node_name IS 'Graph node name (e.g., parallel_round_node)';
        COMMENT ON COLUMN api_costs.phase IS 'Deliberation phase (decomposition, deliberation, synthesis)';
        COMMENT ON COLUMN api_costs.persona_name IS 'Persona name for persona contributions';
        COMMENT ON COLUMN api_costs.round_number IS 'Round number in deliberation';
        COMMENT ON COLUMN api_costs.sub_problem_index IS 'Sub-problem index in parallel deliberation';
        COMMENT ON COLUMN api_costs.input_tokens IS 'Input tokens (regular + cache)';
        COMMENT ON COLUMN api_costs.output_tokens IS 'Output tokens';
        COMMENT ON COLUMN api_costs.total_tokens IS 'Total tokens (computed: input + output)';
        COMMENT ON COLUMN api_costs.cache_creation_tokens IS 'Tokens written to prompt cache (Anthropic)';
        COMMENT ON COLUMN api_costs.cache_read_tokens IS 'Tokens read from prompt cache (Anthropic)';
        COMMENT ON COLUMN api_costs.cache_hit IS 'Whether this call hit the cache';
        COMMENT ON COLUMN api_costs.input_cost IS 'Cost for input tokens (USD)';
        COMMENT ON COLUMN api_costs.output_cost IS 'Cost for output tokens (USD)';
        COMMENT ON COLUMN api_costs.cache_write_cost IS 'Cost for cache write tokens (USD)';
        COMMENT ON COLUMN api_costs.cache_read_cost IS 'Cost for cache read tokens (USD)';
        COMMENT ON COLUMN api_costs.total_cost IS 'Total cost (USD)';
        COMMENT ON COLUMN api_costs.optimization_type IS 'Optimization type (prompt_cache, semantic_cache, batch, none)';
        COMMENT ON COLUMN api_costs.cost_without_optimization IS 'What it would have cost without optimization (USD)';
        COMMENT ON COLUMN api_costs.latency_ms IS 'API call latency in milliseconds';
        COMMENT ON COLUMN api_costs.status IS 'Call status (success, error, timeout)';
        COMMENT ON COLUMN api_costs.error_message IS 'Error message if status is error';
        COMMENT ON COLUMN api_costs.metadata IS 'Flexible JSONB metadata for additional context';
    """)

    # ============================================================================
    # 4. session_cost_summary materialized view
    # ============================================================================

    op.execute("""
        CREATE MATERIALIZED VIEW session_cost_summary AS
        SELECT
            session_id,
            user_id,

            -- Total costs
            COUNT(*) as total_api_calls,
            SUM(total_cost) as total_cost,

            -- By provider
            SUM(CASE WHEN provider = 'anthropic' THEN total_cost ELSE 0 END) as anthropic_cost,
            SUM(CASE WHEN provider = 'voyage' THEN total_cost ELSE 0 END) as voyage_cost,
            SUM(CASE WHEN provider = 'brave' THEN total_cost ELSE 0 END) as brave_cost,
            SUM(CASE WHEN provider = 'tavily' THEN total_cost ELSE 0 END) as tavily_cost,

            -- By phase
            SUM(CASE WHEN phase = 'decomposition' THEN total_cost ELSE 0 END) as decomposition_cost,
            SUM(CASE WHEN phase = 'deliberation' THEN total_cost ELSE 0 END) as deliberation_cost,
            SUM(CASE WHEN phase = 'synthesis' THEN total_cost ELSE 0 END) as synthesis_cost,

            -- Token totals
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            SUM(total_tokens) as total_tokens,

            -- Cache metrics
            SUM(cache_read_tokens) as total_cache_read_tokens,
            SUM(cache_creation_tokens) as total_cache_creation_tokens,
            AVG(CASE WHEN provider = 'anthropic' THEN cache_hit::int ELSE NULL END) as cache_hit_rate,

            -- Optimization savings
            SUM(COALESCE(cost_without_optimization, total_cost) - total_cost) as total_cost_saved,
            SUM(cost_without_optimization) as cost_without_optimization,

            -- Performance
            AVG(latency_ms) as avg_latency_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,

            -- Timestamps
            MIN(created_at) as first_call_at,
            MAX(created_at) as last_call_at

        FROM api_costs
        GROUP BY session_id, user_id
    """)

    # Create unique index on materialized view
    op.create_index(
        "idx_session_cost_summary",
        "session_cost_summary",
        ["session_id"],
        unique=True,
    )

    # Add comment on view
    op.execute("""
        COMMENT ON MATERIALIZED VIEW session_cost_summary IS 'Pre-aggregated cost summary per session for fast queries';
    """)

    # Create refresh function
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_session_cost_summary()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY session_cost_summary;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        COMMENT ON FUNCTION refresh_session_cost_summary() IS 'Refresh session_cost_summary materialized view (call after session completes)';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop refresh function
    op.execute("DROP FUNCTION IF EXISTS refresh_session_cost_summary()")

    # Drop materialized view
    op.drop_index("idx_session_cost_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS session_cost_summary")

    # Drop indexes
    op.drop_index("idx_api_costs_metadata", table_name="api_costs")
    op.drop_index("idx_api_costs_analysis", table_name="api_costs")
    op.drop_index("idx_api_costs_phase", table_name="api_costs")
    op.drop_index("idx_api_costs_node", table_name="api_costs")
    op.drop_index("idx_api_costs_provider", table_name="api_costs")
    op.drop_index("idx_api_costs_created", table_name="api_costs")
    op.drop_index("idx_api_costs_user", table_name="api_costs")
    op.drop_index("idx_api_costs_session", table_name="api_costs")

    # Drop table
    op.drop_table("api_costs")
