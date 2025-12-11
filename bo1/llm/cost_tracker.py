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

from bo1.state.database import db_session

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
        # Ensure non-negative: with high cache hit rates, reported token counts can vary
        regular_input = max(0, input_tokens - cache_read_tokens - cache_creation_tokens)
        input_cost = (regular_input / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing["cache_write"]
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]

        # Ensure total cost is non-negative (safeguard for edge cases)
        total_cost = max(0.0, input_cost + output_cost + cache_write_cost + cache_read_cost)

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
    def _emit_prometheus_metrics(record: CostRecord) -> None:
        """Emit Prometheus metrics for Grafana dashboards.

        Args:
            record: CostRecord with all API call details
        """
        try:
            from backend.api.metrics import prom_metrics

            # Record request duration
            if record.latency_ms:
                prom_metrics.observe_llm_request(
                    provider=record.provider,
                    model=record.model_name,
                    operation=record.operation_type,
                    duration_seconds=record.latency_ms / 1000.0,
                    node=record.node_name,
                )

            # Record token usage
            prom_metrics.record_tokens(
                provider=record.provider,
                model=record.model_name,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                cache_read_tokens=record.cache_read_tokens,
                cache_write_tokens=record.cache_creation_tokens,
            )

            # Record cost
            prom_metrics.record_cost(
                provider=record.provider,
                model=record.model_name,
                cost_dollars=record.total_cost,
            )
        except ImportError:
            # Metrics not available (e.g., in CLI mode)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit Prometheus metrics: {e}")

    @staticmethod
    def _emit_cache_metrics(record: CostRecord) -> None:
        """Emit cache hit/miss metrics for monitoring (P1: prompt cache monitoring).

        Args:
            record: CostRecord with cache token info
        """
        try:
            from backend.api.metrics import metrics, prom_metrics

            # Track cache hits/misses (in-memory metrics)
            if record.cache_hit:
                metrics.increment("llm.cache.hits")
                # Track tokens saved from cache
                if record.cache_read_tokens > 0:
                    metrics.observe("llm.cache.tokens_saved", float(record.cache_read_tokens))
                # Track cost saved (difference vs without cache)
                if (
                    record.cost_without_optimization
                    and record.total_cost < record.cost_without_optimization
                ):
                    cost_saved = record.cost_without_optimization - record.total_cost
                    metrics.observe("llm.cache.cost_saved", cost_saved)
            else:
                metrics.increment("llm.cache.misses")

            # Prometheus metrics for Grafana
            prom_metrics.record_cache_hit(record.cache_hit)
        except ImportError:
            # Metrics not available (e.g., in CLI mode)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit cache metrics: {e}")

    @staticmethod
    def _check_token_budget(record: CostRecord) -> None:
        """Check if input tokens exceed budget threshold and log warning.

        Helps identify bloated prompts that may need optimization.

        Args:
            record: CostRecord with input token count and context
        """
        try:
            from bo1.config import get_settings

            settings = get_settings()
            threshold = settings.token_budget_warning_threshold

            if record.input_tokens > threshold:
                prompt_name = record.metadata.get("prompt_name", "unknown")
                logger.warning(
                    f"Token budget exceeded: {record.input_tokens:,} tokens "
                    f"(threshold: {threshold:,}) | "
                    f"prompt={prompt_name} node={record.node_name} "
                    f"phase={record.phase} model={record.model_name}"
                )

                # Emit metric for monitoring dashboards
                try:
                    from backend.api.metrics import metrics

                    metrics.increment("llm.token_budget.violations")
                    metrics.observe("llm.input_tokens.exceeded", float(record.input_tokens))
                except ImportError:
                    pass

        except Exception as e:
            logger.debug(f"Failed to check token budget: {e}")

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
                record.input_cost = max(0.0, costs[0])
                record.output_cost = max(0.0, costs[1])
                record.cache_write_cost = max(0.0, costs[2])
                record.cache_read_cost = max(0.0, costs[3])
                record.total_cost = max(0.0, costs[4])
                record.cost_without_optimization = max(0.0, costs[5]) if costs[5] else None
                if record.cache_read_tokens > 0:
                    record.optimization_type = "prompt_cache"

            elif provider == "voyage":
                record.total_cost = max(
                    0.0,
                    CostTracker.calculate_voyage_cost(
                        record.model_name or "voyage-3", record.input_tokens
                    ),
                )

            elif provider == "brave":
                record.total_cost = max(
                    0.0, CostTracker.calculate_brave_cost(record.operation_type)
                )

            elif provider == "tavily":
                record.total_cost = max(
                    0.0, CostTracker.calculate_tavily_cost(record.operation_type)
                )

            # Final safeguard: ensure all costs are non-negative (DB constraint requires total_cost >= 0)
            record.total_cost = max(0.0, record.total_cost)
            record.input_cost = max(0.0, record.input_cost)
            record.output_cost = max(0.0, record.output_cost)
            record.cache_write_cost = max(0.0, record.cache_write_cost)
            record.cache_read_cost = max(0.0, record.cache_read_cost)

            # Emit cache metrics (P1: prompt cache monitoring)
            CostTracker._emit_cache_metrics(record)

            # Check token budget and emit warning (P2: token budget tracking)
            CostTracker._check_token_budget(record)

            # Emit Prometheus metrics for Grafana dashboards
            CostTracker._emit_prometheus_metrics(record)

            # Log to database
            CostTracker.log_cost(record)

    # Track sessions that have already received warnings (to avoid duplicates)
    _warned_sessions: set[str] = set()
    _exceeded_sessions: set[str] = set()

    @classmethod
    def check_budget(
        cls,
        session_id: str,
        current_cost: float,
        budget: float | None = None,
        warning_threshold: float | None = None,
    ) -> tuple[bool, bool]:
        """Check if session cost has crossed budget thresholds.

        Emits warnings/alerts via logging and Prometheus metrics.
        Tracks state to avoid duplicate warnings per session.

        Args:
            session_id: Session identifier
            current_cost: Current cumulative cost for session
            budget: Cost budget in USD (default: from settings)
            warning_threshold: Warning threshold 0-1 (default: from settings)

        Returns:
            Tuple of (warning_triggered, exceeded_triggered) - True only on first crossing

        Examples:
            >>> warning, exceeded = CostTracker.check_budget("bo1_abc", 0.45)
            >>> if warning:
            ...     print("Budget warning triggered!")
        """
        from bo1.config import get_settings

        settings = get_settings()
        budget = budget or settings.session_cost_budget
        warning_threshold = warning_threshold or settings.cost_warning_threshold

        warning_triggered = False
        exceeded_triggered = False

        percent_used = current_cost / budget if budget > 0 else 0.0

        # Check warning threshold (80% by default)
        if percent_used >= warning_threshold and session_id not in cls._warned_sessions:
            cls._warned_sessions.add(session_id)
            warning_triggered = True
            logger.warning(
                f"Cost budget warning: session={session_id} "
                f"cost=${current_cost:.4f} budget=${budget:.2f} "
                f"used={percent_used:.1%} threshold={warning_threshold:.0%}"
            )
            # Emit Prometheus metric
            cls._emit_budget_alert_metric(session_id, "warning", current_cost, budget)

        # Check exceeded threshold (100%)
        if percent_used >= 1.0 and session_id not in cls._exceeded_sessions:
            cls._exceeded_sessions.add(session_id)
            exceeded_triggered = True
            logger.warning(
                f"Cost budget EXCEEDED: session={session_id} "
                f"cost=${current_cost:.4f} budget=${budget:.2f} "
                f"used={percent_used:.1%}"
            )
            # Emit Prometheus metric
            cls._emit_budget_alert_metric(session_id, "exceeded", current_cost, budget)

        return warning_triggered, exceeded_triggered

    @staticmethod
    def _emit_budget_alert_metric(
        session_id: str, alert_type: str, current_cost: float, budget: float
    ) -> None:
        """Emit Prometheus metric for budget alert.

        Args:
            session_id: Session identifier
            alert_type: Alert type ('warning' or 'exceeded')
            current_cost: Current cost
            budget: Budget threshold
        """
        try:
            from backend.api.metrics import prom_metrics

            prom_metrics.record_budget_alert(alert_type, current_cost, budget)
        except ImportError:
            # Metrics not available (e.g., in CLI mode)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit budget alert metric: {e}")

    @classmethod
    def reset_session_budget_state(cls, session_id: str) -> None:
        """Reset budget tracking state for a session (for testing).

        Args:
            session_id: Session identifier to reset
        """
        cls._warned_sessions.discard(session_id)
        cls._exceeded_sessions.discard(session_id)

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

    @staticmethod
    def get_subproblem_costs(session_id: str) -> list[dict[str, Any]]:
        """Get cost breakdown by sub-problem for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of cost breakdowns per sub-problem:
            [
                {
                    "sub_problem_index": int | None,  # None = overhead (facilitator, decomposition)
                    "label": str,  # "Sub-problem 0", "Sub-problem 1", or "Overhead"
                    "total_cost": float,
                    "api_calls": int,
                    "total_tokens": int,
                    "by_provider": {"anthropic": float, "voyage": float, ...},
                    "by_phase": {"decomposition": float, "deliberation": float, ...}
                },
                ...
            ]

        Examples:
            >>> costs = CostTracker.get_subproblem_costs("bo1_abc123")
            >>> for sp in costs:
            ...     print(f"{sp['label']}: ${sp['total_cost']:.4f}")
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        sub_problem_index,
                        COUNT(*) as api_calls,
                        SUM(total_cost) as total_cost,
                        SUM(total_tokens) as total_tokens,
                        SUM(CASE WHEN provider = 'anthropic' THEN total_cost ELSE 0 END) as anthropic_cost,
                        SUM(CASE WHEN provider = 'voyage' THEN total_cost ELSE 0 END) as voyage_cost,
                        SUM(CASE WHEN provider = 'brave' THEN total_cost ELSE 0 END) as brave_cost,
                        SUM(CASE WHEN provider = 'tavily' THEN total_cost ELSE 0 END) as tavily_cost,
                        SUM(CASE WHEN phase = 'decomposition' THEN total_cost ELSE 0 END) as decomposition_cost,
                        SUM(CASE WHEN phase = 'deliberation' THEN total_cost ELSE 0 END) as deliberation_cost,
                        SUM(CASE WHEN phase = 'synthesis' THEN total_cost ELSE 0 END) as synthesis_cost
                    FROM api_costs
                    WHERE session_id = %s
                    GROUP BY sub_problem_index
                    ORDER BY sub_problem_index NULLS FIRST
                    """,
                    (session_id,),
                )

                results = []
                for row in cur.fetchall():
                    sp_index = row[0]
                    label = f"Sub-problem {sp_index}" if sp_index is not None else "Overhead"
                    results.append(
                        {
                            "sub_problem_index": sp_index,
                            "label": label,
                            "api_calls": row[1] or 0,
                            "total_cost": float(row[2] or 0),
                            "total_tokens": row[3] or 0,
                            "by_provider": {
                                "anthropic": float(row[4] or 0),
                                "voyage": float(row[5] or 0),
                                "brave": float(row[6] or 0),
                                "tavily": float(row[7] or 0),
                            },
                            "by_phase": {
                                "decomposition": float(row[8] or 0),
                                "deliberation": float(row[9] or 0),
                                "synthesis": float(row[10] or 0),
                            },
                        }
                    )

                return results
