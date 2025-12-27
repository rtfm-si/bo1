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
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter

from bo1.constants import CostAnomalyConfig
from bo1.logging import ErrorCode, log_error
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# =============================================================================
# Aggregation Cache Prometheus Metrics
# =============================================================================
aggregation_cache_hits = Counter(
    "aggregation_cache_hits_total",
    "Total session cost aggregation cache hits",
)
aggregation_cache_misses = Counter(
    "aggregation_cache_misses_total",
    "Total session cost aggregation cache misses",
)

# =============================================================================
# Batch Buffer Configuration
# =============================================================================
BATCH_SIZE = 100  # Flush when buffer exceeds this
BATCH_INTERVAL_SECONDS = 30  # Flush if time since last flush exceeds this
MAX_BUFFER_SIZE = 200  # Cap buffer size to prevent memory growth on repeated failures

# =============================================================================
# Cost Retry Queue Configuration
# =============================================================================
COST_RETRY_QUEUE_KEY = "cost_retry_queue"  # Redis key for retry queue
COST_RETRY_ALERT_THRESHOLD = 100  # Alert if queue exceeds this depth

# =============================================================================
# Aggregation Cache Configuration
# =============================================================================
AGGREGATION_CACHE_TTL_SECONDS = 60  # 60s TTL for session cost aggregations
AGGREGATION_CACHE_MAX_SIZE = 500  # Max cached sessions (sessions typically short-lived)


class AggregationCache:
    """Thread-safe LRU cache with TTL for session cost aggregations.

    Reduces database load by caching get_session_costs() results for 60 seconds.
    Cache is invalidated when new costs are flushed for a session.

    Similar pattern to SessionMetadataCache but specialized for cost aggregations.
    """

    def __init__(
        self,
        max_size: int = AGGREGATION_CACHE_MAX_SIZE,
        ttl_seconds: int = AGGREGATION_CACHE_TTL_SECONDS,
    ) -> None:
        """Initialize cache with size and TTL limits.

        Args:
            max_size: Maximum entries before LRU eviction
            ttl_seconds: Entry expiration time in seconds
        """
        self._cache: OrderedDict[str, tuple[dict[str, Any], float]] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Get cached aggregation if present and not expired.

        Args:
            session_id: Session identifier

        Returns:
            Cached cost aggregation dict or None if missing/expired
        """
        with self._lock:
            if session_id not in self._cache:
                return None

            value, timestamp = self._cache[session_id]

            # Check TTL expiry
            if time.monotonic() - timestamp > self._ttl_seconds:
                del self._cache[session_id]
                return None

            # Move to end for LRU
            self._cache.move_to_end(session_id)
            return value

    def set(self, session_id: str, result: dict[str, Any]) -> None:
        """Store aggregation result in cache.

        Args:
            session_id: Session identifier
            result: Aggregated cost dict
        """
        with self._lock:
            # Remove if exists to update timestamp
            if session_id in self._cache:
                del self._cache[session_id]

            # Evict LRU entries if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            # Add with current timestamp
            self._cache[session_id] = (result, time.monotonic())

    def invalidate(self, session_id: str) -> bool:
        """Remove entry from cache (called when new costs are flushed).

        Args:
            session_id: Session identifier

        Returns:
            True if entry was removed, False if not present
        """
        with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                logger.debug(f"Invalidated aggregation cache for session {session_id}")
                return True
            return False

    def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached entries
        """
        with self._lock:
            return len(self._cache)


# Module-level cache instance
_session_costs_cache = AggregationCache()


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

        # Timestamp
        created_at: When the API call was made (for partitioned table conflict resolution)

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
    # prompt_type categorizes LLM calls for per-prompt-type cache analysis
    # Valid values: persona_contribution, facilitator_decision, synthesis, decomposition,
    # context_collection, clarification, research_summary, task_extraction, embedding, search
    prompt_type: str | None = None
    # Feature type for fair usage tracking
    # Valid values: mentor_chat, dataset_qa, competitor_analysis, meeting
    feature: str | None = None

    # Performance
    latency_ms: int | None = None
    status: str = "success"
    error_message: str | None = None

    # Timestamp (set at record creation for idempotent retries)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

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
    Supports batched inserts to reduce database overhead during deliberation.

    Batch Behavior:
        - Costs are buffered in memory instead of immediate DB inserts
        - Buffer is flushed when: size > BATCH_SIZE, time > BATCH_INTERVAL_SECONDS,
          or explicit flush() called
        - Flush happens at session completion via EventCollector
        - Thread-safe via lock for concurrent sessions
    """

    # Batch buffer state (class-level for singleton behavior)
    _pending_costs: list[CostRecord] = []
    _last_flush_time: datetime = datetime.now(UTC)
    _buffer_lock: threading.Lock = threading.Lock()

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

    @classmethod
    def log_cost(cls, record: CostRecord) -> str:
        """Buffer cost record for batch insert (writes to DB on flush).

        Costs are buffered in memory and flushed to database when:
        - Buffer size exceeds BATCH_SIZE (50)
        - Time since last flush exceeds BATCH_INTERVAL_SECONDS (30s)
        - Explicit flush() is called (at session completion)

        Args:
            record: CostRecord to buffer

        Returns:
            request_id of the buffered record (UUID string)

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

        # Store request_id in record metadata for tracking
        record.metadata["request_id"] = request_id

        with cls._buffer_lock:
            cls._pending_costs.append(record)
            buffer_size = len(cls._pending_costs)

            logger.debug(
                f"Buffered API cost: {record.provider}/{record.operation_type} "
                f"${record.total_cost:.6f} (buffer size: {buffer_size})"
            )

            # Check if auto-flush needed
            time_since_flush = (datetime.now(UTC) - cls._last_flush_time).total_seconds()
            should_flush = buffer_size >= BATCH_SIZE or time_since_flush >= BATCH_INTERVAL_SECONDS

        # Flush outside lock to avoid holding lock during DB operation
        if should_flush:
            cls._flush_batch()

        return request_id

    @classmethod
    def _flush_batch(cls) -> int:
        """Flush buffered costs to database using batch insert.

        Uses executemany() for efficient batch insertion.
        Thread-safe: acquires lock to swap buffer.
        Instrumented with Prometheus metrics for observability.

        Returns:
            Number of records flushed
        """
        # Swap buffer under lock (minimize lock hold time)
        with cls._buffer_lock:
            if not cls._pending_costs:
                return 0
            to_flush = cls._pending_costs
            cls._pending_costs = []
            cls._last_flush_time = datetime.now(UTC)

        batch_size = len(to_flush)
        logger.info(f"Flushing {batch_size} cost records to database")

        # Start timing for metrics
        flush_start = time.perf_counter()

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    # Build batch insert data
                    insert_data = []
                    daily_aggregates: dict[tuple[str, str, str], tuple[float, int]] = {}
                    for record in to_flush:
                        request_id = record.metadata.get("request_id", str(uuid.uuid4()))
                        # Merge prompt_type into metadata for per-prompt-type cache analysis
                        metadata = dict(record.metadata)
                        if record.prompt_type:
                            metadata["prompt_type"] = record.prompt_type
                        insert_data.append(
                            (
                                request_id,
                                record.created_at,  # Include created_at for conflict resolution
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
                                json.dumps(metadata),
                                record.feature,  # Feature for fair usage tracking
                            )
                        )
                        # Aggregate for daily_user_feature_costs upsert
                        if record.user_id and record.feature:
                            date_str = record.created_at.strftime("%Y-%m-%d")
                            key = (record.user_id, record.feature, date_str)
                            if key in daily_aggregates:
                                existing_cost, existing_count = daily_aggregates[key]
                                daily_aggregates[key] = (
                                    existing_cost + record.total_cost,
                                    existing_count + 1,
                                )
                            else:
                                daily_aggregates[key] = (record.total_cost, 1)

                    # IDEMPOTENCY FIX: Use ON CONFLICT DO NOTHING to prevent double-tracking
                    # on graph retries. The api_costs table is partitioned by created_at, so the
                    # unique index is (request_id, created_at). We include created_at in the insert
                    # and conflict target to match the composite unique constraint.
                    cur.executemany(
                        """
                        INSERT INTO api_costs (
                            request_id, created_at, session_id, user_id,
                            provider, model_name, operation_type,
                            node_name, phase, persona_name, round_number, sub_problem_index,
                            input_tokens, output_tokens,
                            cache_creation_tokens, cache_read_tokens, cache_hit,
                            input_cost, output_cost, cache_write_cost, cache_read_cost, total_cost,
                            optimization_type, cost_without_optimization,
                            latency_ms, status, error_message,
                            metadata, feature
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s
                        )
                        ON CONFLICT (request_id, created_at) DO NOTHING
                        """,
                        insert_data,
                    )

                    # Upsert daily user feature costs for fair usage tracking
                    if daily_aggregates:
                        daily_upsert_data = [
                            (user_id, feature, date, cost, count)
                            for (user_id, feature, date), (cost, count) in daily_aggregates.items()
                        ]
                        cur.executemany(
                            """
                            INSERT INTO daily_user_feature_costs
                                (user_id, feature, date, total_cost, request_count)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (user_id, feature, date)
                            DO UPDATE SET
                                total_cost = daily_user_feature_costs.total_cost + EXCLUDED.total_cost,
                                request_count = daily_user_feature_costs.request_count + EXCLUDED.request_count,
                                updated_at = NOW()
                            """,
                            daily_upsert_data,
                        )

            # Record metrics on success
            flush_duration = time.perf_counter() - flush_start
            cls._record_flush_metrics(flush_duration, success=True)

            # Invalidate aggregation cache for affected sessions
            session_ids = {r.session_id for r in to_flush if r.session_id}
            for sid in session_ids:
                _session_costs_cache.invalidate(sid)
            if session_ids:
                logger.debug(f"Invalidated aggregation cache for {len(session_ids)} sessions")

            logger.info(f"Successfully flushed {batch_size} cost records")
            return batch_size

        except Exception as e:
            # Record metrics on failure
            flush_duration = time.perf_counter() - flush_start
            cls._record_flush_metrics(flush_duration, success=False)

            log_error(
                logger,
                ErrorCode.COST_FLUSH_ERROR,
                f"Failed to flush cost batch ({batch_size} records): {e}",
            )
            # Push failed records to Redis retry queue for resilience
            pushed_count = cls._push_to_retry_queue(to_flush)
            if pushed_count > 0:
                logger.info(f"Pushed {pushed_count} cost records to retry queue")
                # Mark affected sessions as having untracked costs
                cls._mark_sessions_untracked_costs(to_flush)
            else:
                # Redis also failed - fall back to buffer re-add
                with cls._buffer_lock:
                    space_available = MAX_BUFFER_SIZE - len(cls._pending_costs)
                    if space_available < len(to_flush):
                        evicted = len(to_flush) - space_available
                        to_flush = to_flush[evicted:]
                        logger.warning(f"Evicted {evicted} oldest cost records (buffer full)")
                    cls._pending_costs = to_flush + cls._pending_costs
            return 0

    @classmethod
    def flush(cls, session_id: str | None = None) -> int:
        """Explicitly flush buffered costs to database.

        Called by EventCollector at session completion and in error handlers.
        Idempotent - no-op if buffer empty.

        Args:
            session_id: Optional session ID for logging (not used for filtering)

        Returns:
            Number of records flushed
        """
        with cls._buffer_lock:
            buffer_size = len(cls._pending_costs)

        if buffer_size == 0:
            logger.debug(f"Cost buffer empty, nothing to flush (session={session_id})")
            return 0

        logger.info(f"Explicit flush requested (session={session_id}, buffer={buffer_size})")
        return cls._flush_batch()

    @classmethod
    def get_buffer_stats(cls) -> dict[str, Any]:
        """Get current buffer statistics for monitoring.

        Returns:
            Dict with buffer_size, last_flush_time, seconds_since_flush
        """
        with cls._buffer_lock:
            buffer_size = len(cls._pending_costs)
            last_flush = cls._last_flush_time

        seconds_since = (datetime.now(UTC) - last_flush).total_seconds()
        return {
            "buffer_size": buffer_size,
            "last_flush_time": last_flush.isoformat(),
            "seconds_since_flush": seconds_since,
        }

    @classmethod
    def _clear_buffer_for_testing(cls) -> None:
        """Clear buffer state (for testing only)."""
        with cls._buffer_lock:
            cls._pending_costs = []
            cls._last_flush_time = datetime.now(UTC)

    @staticmethod
    def _record_flush_metrics(duration_seconds: float, success: bool) -> None:
        """Record Prometheus metrics for cost flush operation.

        Args:
            duration_seconds: Time taken to flush batch
            success: Whether flush succeeded
        """
        try:
            from backend.api.middleware.metrics import (
                record_cost_flush,
                record_cost_flush_duration,
            )

            record_cost_flush_duration(duration_seconds)
            record_cost_flush(success)
        except ImportError:
            # Metrics not available (e.g., in CLI mode)
            pass
        except Exception as e:
            logger.debug(f"Failed to record flush metrics: {e}")

    @staticmethod
    def _update_retry_queue_metric(queue_depth: int) -> None:
        """Update Prometheus gauge for retry queue depth.

        Args:
            queue_depth: Current retry queue depth
        """
        try:
            from backend.api.middleware.metrics import set_cost_retry_queue_depth

            set_cost_retry_queue_depth(queue_depth)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to update retry queue metric: {e}")

    @classmethod
    def check_anomaly(
        cls,
        record: CostRecord,
        session_total: float | None = None,
    ) -> list[str]:
        """Check for cost anomalies and emit metrics/alerts.

        Called during record() to detect unusual cost patterns.

        Args:
            record: CostRecord to check
            session_total: Optional cumulative session cost (if known)

        Returns:
            List of anomaly types detected (empty if none)
        """
        if not CostAnomalyConfig.is_enabled():
            return []

        anomalies: list[str] = []

        # Check for negative cost (data corruption)
        if record.total_cost < 0:
            anomalies.append("negative_cost")
            log_error(
                logger,
                ErrorCode.COST_ANOMALY,
                f"Negative cost detected: ${record.total_cost:.6f}",
                session_id=record.session_id,
                model=record.model_name,
                provider=record.provider,
            )

        # Check single call threshold
        single_threshold = CostAnomalyConfig.get_single_call_threshold()
        if record.total_cost > single_threshold:
            anomalies.append("high_single_call")
            log_error(
                logger,
                ErrorCode.COST_ANOMALY,
                f"High single call cost: ${record.total_cost:.4f} (threshold: ${single_threshold:.2f})",
                session_id=record.session_id,
                model=record.model_name,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
            )

        # Check session total threshold
        if session_total is not None:
            session_threshold = CostAnomalyConfig.get_session_total_threshold()
            if session_total > session_threshold:
                anomalies.append("high_session_total")
                log_error(
                    logger,
                    ErrorCode.COST_ANOMALY,
                    f"High session total: ${session_total:.4f} (threshold: ${session_threshold:.2f})",
                    session_id=record.session_id,
                )

        # Emit Prometheus metrics for detected anomalies
        cls._record_anomaly_metrics(anomalies)

        # Send ntfy alerts for anomalies (non-blocking)
        if anomalies and CostAnomalyConfig.are_alerts_enabled():
            cls._send_anomaly_alerts(anomalies, record, session_total)

        return anomalies

    @classmethod
    def _send_anomaly_alerts(
        cls,
        anomalies: list[str],
        record: CostRecord,
        session_total: float | None = None,
    ) -> None:
        """Send ntfy alerts for detected anomalies (fire-and-forget).

        Uses asyncio to send alerts without blocking cost tracking.
        Failures are logged but do not propagate.

        Args:
            anomalies: List of anomaly types detected
            record: CostRecord with details
            session_total: Optional session total cost
        """
        import asyncio

        try:
            from backend.services.alerts import alert_cost_anomaly

            # Determine thresholds for context
            single_threshold = CostAnomalyConfig.get_single_call_threshold()
            session_threshold = CostAnomalyConfig.get_session_total_threshold()

            for anomaly_type in anomalies:
                # Determine threshold to include in alert
                threshold = None
                cost = record.total_cost
                if anomaly_type == "high_single_call":
                    threshold = single_threshold
                elif anomaly_type == "high_session_total":
                    cost = session_total or record.total_cost
                    threshold = session_threshold

                # Fire-and-forget async alert
                try:
                    loop = asyncio.get_running_loop()
                    # If in async context, schedule as task
                    loop.create_task(
                        alert_cost_anomaly(
                            anomaly_type=anomaly_type,
                            session_id=record.session_id,
                            cost=cost,
                            model=record.model_name,
                            provider=record.provider,
                            input_tokens=record.input_tokens,
                            output_tokens=record.output_tokens,
                            threshold=threshold,
                        )
                    )
                except RuntimeError:
                    # No running loop - run in new loop (sync context)
                    asyncio.run(
                        alert_cost_anomaly(
                            anomaly_type=anomaly_type,
                            session_id=record.session_id,
                            cost=cost,
                            model=record.model_name,
                            provider=record.provider,
                            input_tokens=record.input_tokens,
                            output_tokens=record.output_tokens,
                            threshold=threshold,
                        )
                    )

        except ImportError:
            logger.debug("Alert service not available for cost anomaly alerts")
        except Exception as e:
            # Never fail cost tracking due to alerting failure
            logger.debug(f"Failed to send cost anomaly alert: {e}")

    @staticmethod
    def _record_anomaly_metrics(anomalies: list[str]) -> None:
        """Emit Prometheus counter for each anomaly type.

        Args:
            anomalies: List of anomaly types detected
        """
        if not anomalies:
            return

        try:
            from backend.api.middleware.metrics import record_cost_anomaly

            for anomaly_type in anomalies:
                record_cost_anomaly(anomaly_type)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to record anomaly metrics: {e}")

    @classmethod
    def _push_to_retry_queue(cls, records: list[CostRecord]) -> int:
        """Push failed cost records to Redis retry queue.

        Args:
            records: List of CostRecord objects to queue

        Returns:
            Number of records successfully pushed
        """
        try:
            import redis

            from bo1.config import get_settings

            settings = get_settings()
            redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

            pushed = 0
            for record in records:
                retry_data = {
                    "request_id": record.metadata.get("request_id", str(uuid.uuid4())),
                    "created_at": record.created_at.isoformat(),  # Preserve for conflict resolution
                    "session_id": record.session_id,
                    "user_id": record.user_id,
                    "provider": record.provider,
                    "model_name": record.model_name,
                    "operation_type": record.operation_type,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "cache_creation_tokens": record.cache_creation_tokens,
                    "cache_read_tokens": record.cache_read_tokens,
                    "total_cost": record.total_cost,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": "DB flush failed",
                }
                redis_client.rpush(COST_RETRY_QUEUE_KEY, json.dumps(retry_data))
                pushed += 1

            # Check queue depth and alert if too deep
            queue_depth = redis_client.llen(COST_RETRY_QUEUE_KEY)

            # Update Prometheus gauge
            cls._update_retry_queue_metric(queue_depth)

            if queue_depth > COST_RETRY_ALERT_THRESHOLD:
                logger.warning(
                    f"Cost retry queue depth ({queue_depth}) exceeds threshold "
                    f"({COST_RETRY_ALERT_THRESHOLD})"
                )
                cls._send_retry_queue_alert(queue_depth)

            return pushed

        except Exception as e:
            log_error(
                logger, ErrorCode.COST_RETRY_ERROR, f"Failed to push to Redis retry queue: {e}"
            )
            return 0

    @classmethod
    def _mark_sessions_untracked_costs(cls, records: list[CostRecord]) -> None:
        """Mark sessions as having untracked costs.

        Args:
            records: List of CostRecord objects with session_ids to mark
        """
        session_ids = {r.session_id for r in records if r.session_id}
        if not session_ids:
            return

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE sessions
                        SET has_untracked_costs = TRUE
                        WHERE id = ANY(%s)
                        """,
                        (list(session_ids),),
                    )
                    updated = cur.rowcount or 0
                    if updated > 0:
                        logger.info(f"Marked {updated} sessions as having untracked costs")
        except Exception as e:
            log_error(
                logger, ErrorCode.DB_WRITE_ERROR, f"Failed to mark sessions as untracked: {e}"
            )

    @staticmethod
    def _send_retry_queue_alert(queue_depth: int) -> None:
        """Send alert when retry queue is too deep.

        Args:
            queue_depth: Current queue depth
        """
        try:
            from bo1.config import get_settings

            settings = get_settings()
            if not settings.ntfy_topic_alerts:
                return

            import httpx

            httpx.post(
                f"https://ntfy.sh/{settings.ntfy_topic_alerts}",
                content=f"Cost retry queue depth: {queue_depth} (threshold: {COST_RETRY_ALERT_THRESHOLD})",
                headers={
                    "Title": "Bo1 Cost Tracking Alert",
                    "Priority": "high"
                    if queue_depth > COST_RETRY_ALERT_THRESHOLD * 2
                    else "default",
                    "Tags": "warning,cost",
                },
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"Failed to send ntfy alert: {e}")

    @classmethod
    def get_retry_queue_depth(cls) -> int:
        """Get current retry queue depth.

        Returns:
            Number of records in retry queue
        """
        try:
            import redis

            from bo1.config import get_settings

            settings = get_settings()
            redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            return redis_client.llen(COST_RETRY_QUEUE_KEY)
        except Exception:
            return 0

    @classmethod
    def pop_retry_batch(cls, batch_size: int = 50) -> list[dict[str, Any]]:
        """Pop a batch of records from the retry queue.

        Used by cost_retry_job worker.

        Args:
            batch_size: Maximum records to pop

        Returns:
            List of retry record dicts
        """
        try:
            import redis

            from bo1.config import get_settings

            settings = get_settings()
            redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

            records = []
            for _ in range(batch_size):
                data = redis_client.lpop(COST_RETRY_QUEUE_KEY)
                if data is None:
                    break
                records.append(json.loads(data))

            return records
        except Exception as e:
            log_error(logger, ErrorCode.COST_RETRY_ERROR, f"Failed to pop from retry queue: {e}")
            return []

    @classmethod
    def clear_session_untracked_flag(cls, session_id: str) -> bool:
        """Clear untracked costs flag after successful retry.

        Args:
            session_id: Session to clear flag for

        Returns:
            True if flag was cleared
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE sessions
                        SET has_untracked_costs = FALSE
                        WHERE id = %s AND has_untracked_costs = TRUE
                        """,
                        (session_id,),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            log_error(
                logger, ErrorCode.DB_WRITE_ERROR, f"Failed to clear untracked costs flag: {e}"
            )
            return False

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
        prompt_type: str | None = None,
        feature: str | None = None,
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
            prompt_type: Prompt type for cache analysis (optional). Valid values:
                persona_contribution, facilitator_decision, synthesis, decomposition,
                context_collection, clarification, research_summary, task_extraction,
                embedding, search
            feature: Feature type for fair usage tracking (optional). Valid values:
                mentor_chat, dataset_qa, competitor_analysis, meeting
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
            ...     phase="deliberation",
            ...     prompt_type="persona_contribution",
            ...     feature="meeting"
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
            prompt_type=prompt_type,
            feature=feature,
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

            # Check for cost anomalies (high single call, negative cost)
            CostTracker.check_anomaly(record)

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
        """Get aggregated costs for a session (cached with 60s TTL).

        Uses in-memory cache to reduce database load. Cache is invalidated
        when new costs are flushed for the session.

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
                "cache_hit_rate": float,
                "prompt_cache_hit_rate": float  # Anthropic prompt cache effectiveness (0.0-1.0)
            }

        Examples:
            >>> costs = CostTracker.get_session_costs("bo1_abc123")
            >>> print(f"Total cost: ${costs['total_cost']:.4f}")
            >>> print(f"Cache savings: ${costs['total_saved']:.4f}")
            >>> print(f"Cache hit rate: {costs['cache_hit_rate']:.1%}")
        """
        # Check cache first
        cached = _session_costs_cache.get(session_id)
        if cached is not None:
            aggregation_cache_hits.inc()
            return cached

        # Cache miss - query database
        aggregation_cache_misses.inc()
        result = CostTracker._query_session_costs(session_id)

        # Cache the result
        _session_costs_cache.set(session_id, result)
        return result

    @staticmethod
    def _query_session_costs(session_id: str) -> dict[str, Any]:
        """Query database for session cost aggregations (internal, uncached).

        Args:
            session_id: Session identifier

        Returns:
            Aggregated cost dict
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # partition: api_costs - Include created_at filter for partition pruning
                # Sessions typically complete within 7 days; use 30 days for safety margin
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
                        AVG(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hit_rate,
                        SUM(CASE WHEN provider = 'anthropic' THEN cache_read_tokens ELSE 0 END) as prompt_cache_read_tokens,
                        SUM(CASE WHEN provider = 'anthropic' THEN cache_read_tokens + cache_creation_tokens + input_tokens ELSE 0 END) as prompt_cache_total_tokens
                    FROM api_costs
                    WHERE session_id = %s
                      AND created_at >= NOW() - INTERVAL '30 days'
                    """,
                    (session_id,),
                )

                row = cur.fetchone()
                if row:
                    # Calculate prompt cache hit rate (Anthropic prompt caching)
                    prompt_cache_read = row[9] or 0
                    prompt_cache_total = row[10] or 0
                    prompt_cache_hit_rate = (
                        float(prompt_cache_read) / float(prompt_cache_total)
                        if prompt_cache_total > 0
                        else 0.0
                    )
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
                        "prompt_cache_hit_rate": prompt_cache_hit_rate,
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
                    "prompt_cache_hit_rate": 0.0,
                }

    @staticmethod
    def invalidate_session_costs_cache(session_id: str) -> bool:
        """Invalidate the aggregation cache for a session.

        Called after flushing new costs to ensure stale data is evicted.

        Args:
            session_id: Session identifier

        Returns:
            True if entry was invalidated, False if not cached
        """
        return _session_costs_cache.invalidate(session_id)

    @classmethod
    def get_cache_metrics(cls) -> dict[str, Any]:
        """Get aggregated cache metrics across all cache systems.

        Aggregates from:
        - Prompt cache: Anthropic native cache (from api_costs table)
        - Research cache: PostgreSQL semantic cache (from cache_repository)
        - LLM cache: Redis deterministic cache (from get_llm_cache)

        Returns:
            Unified cache metrics dict:
            {
                "prompt": {"hit_rate": float, "hits": int, "misses": int, "total": int},
                "research": {"hit_rate": float, "hits": int, "misses": int, "total": int},
                "llm": {"hit_rate": float, "hits": int, "misses": int, "total": int},
                "aggregate": {"hit_rate": float, "total_hits": int, "total_requests": int}
            }
        """
        result: dict[str, Any] = {
            "prompt": {"hit_rate": 0.0, "hits": 0, "misses": 0, "total": 0},
            "research": {"hit_rate": 0.0, "hits": 0, "misses": 0, "total": 0},
            "llm": {"hit_rate": 0.0, "hits": 0, "misses": 0, "total": 0},
            "aggregate": {"hit_rate": 0.0, "total_hits": 0, "total_requests": 0},
        }

        # 1. Prompt cache (Anthropic native) - query from api_costs (24h window)
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) FILTER (WHERE cache_hit = true) as hits,
                            COUNT(*) FILTER (WHERE cache_hit = false) as misses,
                            COUNT(*) as total
                        FROM api_costs
                        WHERE provider = 'anthropic'
                          AND created_at >= NOW() - INTERVAL '24 hours'
                        """
                    )
                    row = cur.fetchone()
                    if row:
                        hits = row[0] or 0
                        misses = row[1] or 0
                        total = row[2] or 0
                        result["prompt"] = {
                            "hit_rate": hits / total if total > 0 else 0.0,
                            "hits": hits,
                            "misses": misses,
                            "total": total,
                        }
        except Exception as e:
            logger.debug(f"Failed to get prompt cache metrics: {e}")

        # 2. Research cache (PostgreSQL semantic)
        try:
            from bo1.state.repositories.cache_repository import cache_repository

            research_stats = cache_repository.get_hit_rate_metrics(1)  # 1 day
            hits = research_stats.get("cache_hits", 0)
            total = research_stats.get("total_queries", 0)
            misses = total - hits
            result["research"] = {
                "hit_rate": hits / total if total > 0 else 0.0,
                "hits": hits,
                "misses": misses,
                "total": total,
            }
        except Exception as e:
            logger.debug(f"Failed to get research cache metrics: {e}")

        # 3. LLM cache (Redis deterministic)
        try:
            from bo1.llm.cache import get_llm_cache

            llm_cache = get_llm_cache()
            llm_stats = llm_cache.get_stats()
            hits = llm_stats.get("hits", 0)
            misses = llm_stats.get("misses", 0)
            total = hits + misses
            result["llm"] = {
                "hit_rate": llm_stats.get("hit_rate", 0.0),
                "hits": hits,
                "misses": misses,
                "total": total,
            }
        except Exception as e:
            logger.debug(f"Failed to get LLM cache metrics: {e}")

        # Aggregate
        total_hits = result["prompt"]["hits"] + result["research"]["hits"] + result["llm"]["hits"]
        total_requests = (
            result["prompt"]["total"] + result["research"]["total"] + result["llm"]["total"]
        )
        result["aggregate"] = {
            "hit_rate": total_hits / total_requests if total_requests > 0 else 0.0,
            "total_hits": total_hits,
            "total_requests": total_requests,
        }

        # Emit Prometheus gauge updates
        cls._emit_cache_rate_gauges(result)

        return result

    @staticmethod
    def _emit_cache_rate_gauges(metrics: dict[str, Any]) -> None:
        """Emit Prometheus gauge values for cache hit rates.

        Args:
            metrics: Cache metrics dict from get_cache_metrics()
        """
        try:
            from backend.api.metrics import prom_metrics

            for cache_type in ("prompt", "research", "llm"):
                if cache_type in metrics:
                    prom_metrics.update_cache_hit_rate(cache_type, metrics[cache_type]["hit_rate"])
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to emit cache rate gauges: {e}")

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
                # partition: api_costs - Include created_at filter for partition pruning
                # Sessions typically complete within 7 days; use 30 days for safety margin
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
                      AND created_at >= NOW() - INTERVAL '30 days'
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
