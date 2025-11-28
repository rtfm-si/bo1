"""Centralized cost tracking for all AI API calls.

Tracks costs across all providers (Anthropic, Voyage, Brave, Tavily) with:
- Token usage tracking (input, output, cache creation, cache read)
- Cost breakdown by component (input, output, cache write, cache read)
- Optimization tracking (prompt cache, semantic cache, etc.)
- Context attribution (session, user, node, phase, persona, round)
- Performance metrics (latency, status, errors)
- PostgreSQL persistence for analytics

Usage:
    # Track an API call with context manager
    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name="claude-sonnet-4-5-20250929",
        session_id=session_id,
        node_name="parallel_round_node",
        phase="deliberation"
    ) as record:
        response = await client.call(...)
        record.input_tokens = response.usage.input_tokens
        record.output_tokens = response.usage.output_tokens
        record.cache_creation_tokens = response.usage.cache_creation_tokens
        record.cache_read_tokens = response.usage.cache_read_tokens
        # Cost is automatically calculated and logged on exit

    # Get session cost summary
    costs = CostTracker.get_session_costs(session_id)
    print(f"Total cost: ${costs['total_cost']:.4f}")
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from bo1.state.postgres_manager import db_session

logger = logging.getLogger(__name__)


# =============================================================================
# Pricing Constants (per 1M tokens or per query)
# Last updated: 2025-11-28
# =============================================================================

ANTHROPIC_PRICING = {
    # Claude Sonnet 4.5
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,  # $3 per 1M input tokens
        "output": 15.00,  # $15 per 1M output tokens
        "cache_write": 3.75,  # $3.75 per 1M (1.25x input)
        "cache_read": 0.30,  # $0.30 per 1M (0.1x input)
    },
    # Claude Haiku 4.5
    "claude-haiku-4-5-20251001": {
        "input": 1.00,
        "output": 5.00,
        "cache_write": 1.25,
        "cache_read": 0.10,
    },
    # Claude Opus 4
    "claude-opus-4-20250514": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    # Claude 3.5 Haiku (for testing)
    "claude-3-5-haiku-20241022": {
        "input": 0.80,
        "output": 4.00,
        "cache_write": 1.00,
        "cache_read": 0.08,
    },
}

VOYAGE_PRICING = {
    # Voyage AI embeddings (per 1M tokens)
    "voyage-3": {
        "embedding": 0.06,  # $0.06 per 1M tokens
    },
    "voyage-3-lite": {
        "embedding": 0.02,  # $0.02 per 1M tokens
    },
    "voyage-3-large": {
        "embedding": 0.18,  # $0.18 per 1M tokens
    },
}

BRAVE_PRICING = {
    # Brave Search API (per query)
    "web_search": 0.003,  # $3 per 1K queries = $0.003/query
    "ai_search": 0.005,  # $5 per 1K queries = $0.005/query
}

TAVILY_PRICING = {
    # Tavily API (per query)
    "basic_search": 0.001,  # 1 credit = ~$0.001
    "advanced_search": 0.002,  # 2 credits = ~$0.002
}


@dataclass
class CostRecord:
    """Record of a single API call cost.

    Attributes:
        provider: Provider name (anthropic, voyage, brave, tavily)
        model_name: Model identifier (e.g., claude-sonnet-4-5-20250929)
        operation_type: Operation type (completion, embedding, search)

        # Token usage (Anthropic/Voyage)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Tokens written to cache
        cache_read_tokens: Tokens read from cache

        # Cost breakdown (USD)
        input_cost: Cost of input tokens
        output_cost: Cost of output tokens
        cache_write_cost: Cost of writing to cache
        cache_read_cost: Cost of reading from cache
        total_cost: Total cost (sum of above)

        # Optimization tracking
        optimization_type: Type of optimization (prompt_cache, semantic_cache, batch, none)
        cost_without_optimization: What it would have cost without optimization

        # Context attribution
        session_id: Session identifier
        user_id: User identifier
        node_name: Graph node name (e.g., parallel_round_node)
        phase: Deliberation phase (decomposition, deliberation, synthesis)
        persona_name: Persona name (for contributions)
        round_number: Round number (for deliberation)
        sub_problem_index: Sub-problem index (for parallel processing)

        # Performance metrics
        latency_ms: Latency in milliseconds
        status: Status (success, error, timeout)
        error_message: Error message if failed

        # Flexible metadata
        metadata: Additional metadata as dict
    """

    provider: str
    model_name: str | None
    operation_type: str

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    # Costs
    input_cost: float = 0.0
    output_cost: float = 0.0
    cache_write_cost: float = 0.0
    cache_read_cost: float = 0.0
    total_cost: float = 0.0

    # Optimization
    optimization_type: str | None = None  # prompt_cache, semantic_cache, batch
    cost_without_optimization: float | None = None

    # Context
    session_id: str | None = None
    user_id: str | None = None
    node_name: str | None = None
    phase: str | None = None
    persona_name: str | None = None
    round_number: int | None = None
    sub_problem_index: int | None = None

    # Performance
    latency_ms: int | None = None
    status: str = "success"
    error_message: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cache_hit(self) -> bool:
        """Check if this call had a cache hit."""
        return self.cache_read_tokens > 0

    @property
    def cost_saved(self) -> float:
        """Calculate cost saved by optimization."""
        if self.cost_without_optimization:
            return self.cost_without_optimization - self.total_cost
        return 0.0


class CostTracker:
    """Track and persist API costs to database.

    Static methods for calculating and logging API costs across all providers.
    """

    @staticmethod
    def calculate_anthropic_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> tuple[float, float, float, float, float, float]:
        """Calculate Anthropic API cost with cache breakdown.

        Args:
            model: Model name (e.g., claude-sonnet-4-5-20250929)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_creation_tokens: Tokens written to cache (optional)
            cache_read_tokens: Tokens read from cache (optional)

        Returns:
            Tuple of (input_cost, output_cost, cache_write_cost, cache_read_cost,
                     total_cost, cost_without_cache)

        Examples:
            >>> costs = CostTracker.calculate_anthropic_cost(
            ...     "claude-sonnet-4-5-20250929",
            ...     input_tokens=1000,
            ...     output_tokens=200,
            ...     cache_read_tokens=500
            ... )
            >>> input_cost, output_cost, cache_write, cache_read, total, without_cache = costs
            >>> print(f"Total: ${total:.6f}, Saved: ${without_cache - total:.6f}")
        """
        pricing = ANTHROPIC_PRICING.get(model, ANTHROPIC_PRICING["claude-sonnet-4-5-20250929"])

        # Regular tokens (non-cached input)
        regular_input = input_tokens - cache_read_tokens - cache_creation_tokens
        input_cost = (regular_input / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing["cache_write"]
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]

        total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

        # What it would have cost without caching
        cost_without_cache = (input_tokens / 1_000_000) * pricing["input"] + (
            output_tokens / 1_000_000
        ) * pricing["output"]

        return (
            input_cost,
            output_cost,
            cache_write_cost,
            cache_read_cost,
            total_cost,
            cost_without_cache,
        )

    @staticmethod
    def calculate_voyage_cost(model: str, total_tokens: int) -> float:
        """Calculate Voyage AI embedding cost.

        Args:
            model: Model name (e.g., voyage-3)
            total_tokens: Total number of tokens

        Returns:
            Cost in USD

        Examples:
            >>> cost = CostTracker.calculate_voyage_cost("voyage-3", 1000)
            >>> print(f"Embedding cost: ${cost:.8f}")
        """
        pricing = VOYAGE_PRICING.get(model, VOYAGE_PRICING["voyage-3"])
        return (total_tokens / 1_000_000) * pricing["embedding"]

    @staticmethod
    def calculate_brave_cost(search_type: str = "web_search") -> float:
        """Calculate Brave Search cost per query.

        Args:
            search_type: Search type (web_search, ai_search)

        Returns:
            Cost in USD per query

        Examples:
            >>> cost = CostTracker.calculate_brave_cost("web_search")
            >>> print(f"Search cost: ${cost:.6f}")
        """
        return BRAVE_PRICING.get(search_type, BRAVE_PRICING["web_search"])

    @staticmethod
    def calculate_tavily_cost(search_type: str = "basic_search") -> float:
        """Calculate Tavily cost per query.

        Args:
            search_type: Search type (basic_search, advanced_search)

        Returns:
            Cost in USD per query

        Examples:
            >>> cost = CostTracker.calculate_tavily_cost("basic_search")
            >>> print(f"Search cost: ${cost:.6f}")
        """
        return TAVILY_PRICING.get(search_type, TAVILY_PRICING["basic_search"])

    @staticmethod
    def log_cost(record: CostRecord) -> str:
        """Persist cost record to database.

        Args:
            record: CostRecord to persist

        Returns:
            request_id of the logged record (UUID string)

        Examples:
            >>> record = CostRecord(
            ...     provider="anthropic",
            ...     model_name="claude-sonnet-4-5-20250929",
            ...     operation_type="completion",
            ...     input_tokens=1000,
            ...     output_tokens=200,
            ...     total_cost=0.006
            ... )
            >>> request_id = CostTracker.log_cost(record)
        """
        request_id = str(uuid.uuid4())

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO api_costs (
                            request_id, session_id, user_id,
                            provider, model_name, operation_type,
                            node_name, phase, persona_name, round_number, sub_problem_index,
                            input_tokens, output_tokens,
                            cache_creation_tokens, cache_read_tokens, cache_hit,
                            input_cost, output_cost, cache_write_cost, cache_read_cost, total_cost,
                            optimization_type, cost_without_optimization,
                            latency_ms, status, error_message,
                            metadata
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s
                        )
                        """,
                        (
                            request_id,
                            record.session_id,
                            record.user_id,
                            record.provider,
                            record.model_name,
                            record.operation_type,
                            record.node_name,
                            record.phase,
                            record.persona_name,
                            record.round_number,
                            record.sub_problem_index,
                            record.input_tokens,
                            record.output_tokens,
                            record.cache_creation_tokens,
                            record.cache_read_tokens,
                            record.cache_hit,
                            record.input_cost,
                            record.output_cost,
                            record.cache_write_cost,
                            record.cache_read_cost,
                            record.total_cost,
                            record.optimization_type,
                            record.cost_without_optimization,
                            record.latency_ms,
                            record.status,
                            record.error_message,
                            json.dumps(record.metadata),
                        ),
                    )

            logger.debug(
                f"Logged API cost: {record.provider}/{record.operation_type} "
                f"${record.total_cost:.6f} (saved: ${record.cost_saved:.6f})"
            )

        except Exception as e:
            logger.error(f"Failed to log API cost: {e}")
            # Don't raise - cost tracking should never block the main flow

        return request_id

    @staticmethod
    @contextmanager
    def track_call(
        provider: str,
        operation_type: str,
        model_name: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        node_name: str | None = None,
        phase: str | None = None,
        **context: Any,
    ) -> Generator[CostRecord, None, None]:
        """Context manager to track an API call.

        Automatically calculates costs and logs to database on exit.

        Args:
            provider: Provider name (anthropic, voyage, brave, tavily)
            operation_type: Operation type (completion, embedding, search)
            model_name: Model identifier (optional)
            session_id: Session identifier (optional)
            user_id: User identifier (optional)
            node_name: Graph node name (optional)
            phase: Deliberation phase (optional)
            **context: Additional context fields (persona_name, round_number, etc.)

        Yields:
            CostRecord to populate with usage data

        Examples:
            >>> with CostTracker.track_call(
            ...     provider="anthropic",
            ...     operation_type="completion",
            ...     model_name="claude-sonnet-4-5-20250929",
            ...     session_id=session_id,
            ...     node_name="parallel_round_node",
            ...     phase="deliberation"
            ... ) as record:
            ...     response = await client.call(...)
            ...     record.input_tokens = response.usage.input_tokens
            ...     record.output_tokens = response.usage.output_tokens
            ...     # Cost calculated and logged automatically on exit
        """
        record = CostRecord(
            provider=provider,
            model_name=model_name,
            operation_type=operation_type,
            session_id=session_id,
            user_id=user_id,
            node_name=node_name,
            phase=phase,
            persona_name=context.get("persona_name"),
            round_number=context.get("round_number"),
            sub_problem_index=context.get("sub_problem_index"),
            metadata=context.get("metadata", {}),
        )

        start_time = time.perf_counter()

        try:
            yield record
            record.status = "success"
        except Exception as e:
            record.status = "error"
            record.error_message = str(e)
            raise
        finally:
            # Calculate latency
            record.latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Calculate costs based on provider
            if provider == "anthropic" and record.model_name:
                costs = CostTracker.calculate_anthropic_cost(
                    record.model_name,
                    record.input_tokens,
                    record.output_tokens,
                    record.cache_creation_tokens,
                    record.cache_read_tokens,
                )
                record.input_cost = costs[0]
                record.output_cost = costs[1]
                record.cache_write_cost = costs[2]
                record.cache_read_cost = costs[3]
                record.total_cost = costs[4]
                record.cost_without_optimization = costs[5]
                if record.cache_read_tokens > 0:
                    record.optimization_type = "prompt_cache"

            elif provider == "voyage":
                record.total_cost = CostTracker.calculate_voyage_cost(
                    record.model_name or "voyage-3", record.input_tokens
                )

            elif provider == "brave":
                record.total_cost = CostTracker.calculate_brave_cost(record.operation_type)

            elif provider == "tavily":
                record.total_cost = CostTracker.calculate_tavily_cost(record.operation_type)

            # Log to database
            CostTracker.log_cost(record)

    @staticmethod
    def get_session_costs(session_id: str) -> dict[str, Any]:
        """Get aggregated costs for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with aggregated cost metrics:
            {
                "total_calls": int,
                "total_cost": float,
                "by_provider": {
                    "anthropic": float,
                    "voyage": float,
                    "brave": float,
                    "tavily": float
                },
                "total_tokens": int,
                "total_saved": float,
                "cache_hit_rate": float
            }

        Examples:
            >>> costs = CostTracker.get_session_costs("bo1_abc123")
            >>> print(f"Total cost: ${costs['total_cost']:.4f}")
            >>> print(f"Cache savings: ${costs['total_saved']:.4f}")
            >>> print(f"Cache hit rate: {costs['cache_hit_rate']:.1%}")
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_calls,
                        SUM(total_cost) as total_cost,
                        SUM(CASE WHEN provider = 'anthropic' THEN total_cost ELSE 0 END) as anthropic_cost,
                        SUM(CASE WHEN provider = 'voyage' THEN total_cost ELSE 0 END) as voyage_cost,
                        SUM(CASE WHEN provider = 'brave' THEN total_cost ELSE 0 END) as brave_cost,
                        SUM(CASE WHEN provider = 'tavily' THEN total_cost ELSE 0 END) as tavily_cost,
                        SUM(total_tokens) as total_tokens,
                        SUM(cost_saved) as total_saved,
                        AVG(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hit_rate
                    FROM api_costs
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )

                row = cur.fetchone()
                if row:
                    return {
                        "total_calls": row[0] or 0,
                        "total_cost": float(row[1] or 0),
                        "by_provider": {
                            "anthropic": float(row[2] or 0),
                            "voyage": float(row[3] or 0),
                            "brave": float(row[4] or 0),
                            "tavily": float(row[5] or 0),
                        },
                        "total_tokens": row[6] or 0,
                        "total_saved": float(row[7] or 0),
                        "cache_hit_rate": float(row[8] or 0),
                    }
                return {
                    "total_calls": 0,
                    "total_cost": 0.0,
                    "by_provider": {
                        "anthropic": 0.0,
                        "voyage": 0.0,
                        "brave": 0.0,
                        "tavily": 0.0,
                    },
                    "total_tokens": 0,
                    "total_saved": 0.0,
                    "cache_hit_rate": 0.0,
                }
