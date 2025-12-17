"""Insight staleness detection service.

Provides utilities for detecting stale insights and metrics, and formatting
insight context for meeting injection. Supports volatility-aware staleness.
"""

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel

from backend.services.trend_calculator import (
    VolatilityLevel,
    classify_volatility,
    get_staleness_threshold,
)
from bo1.state.repositories import user_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

# Default threshold for stale insights (30 days)
DEFAULT_STALENESS_DAYS = 30

# Max stale metrics to return (avoid overwhelming user)
MAX_STALE_METRICS = 3


class StalenessReason(str, Enum):
    """Reason why a metric is considered stale."""

    AGE = "age"  # Metric is older than threshold
    ACTION_AFFECTED = "action_affected"  # Related action was completed
    VOLATILITY = "volatility"  # High volatility metric needs refresh


class StaleInsight(BaseModel):
    """A stale insight requiring user attention."""

    question: str
    answer: str
    updated_at: datetime | None
    days_stale: int
    session_id: str | None = None


class StaleMetric(BaseModel):
    """A stale business context metric requiring user refresh."""

    field_name: str
    current_value: str | float | int | None
    updated_at: datetime | None
    days_since_update: int
    reason: StalenessReason
    volatility: VolatilityLevel
    threshold_days: int
    action_id: str | None = None  # If stale due to action completion


class InsightStalenessResult(BaseModel):
    """Result of staleness check."""

    has_stale_insights: bool
    stale_insights: list[StaleInsight]
    total_insights: int
    fresh_insights_count: int


def get_stale_insights(
    user_id: str,
    threshold_days: int = DEFAULT_STALENESS_DAYS,
) -> InsightStalenessResult:
    """Get insights that are older than threshold.

    Args:
        user_id: User ID to check insights for
        threshold_days: Number of days after which insight is considered stale

    Returns:
        InsightStalenessResult with list of stale insights
    """
    context_data = user_repository.get_context(user_id)

    if not context_data:
        logger.debug(f"No context found for user {user_id}")
        return InsightStalenessResult(
            has_stale_insights=False,
            stale_insights=[],
            total_insights=0,
            fresh_insights_count=0,
        )

    clarifications = context_data.get("clarifications", {})

    if not clarifications:
        logger.debug(f"No clarifications found for user {user_id}")
        return InsightStalenessResult(
            has_stale_insights=False,
            stale_insights=[],
            total_insights=0,
            fresh_insights_count=0,
        )

    now = datetime.now(UTC)
    threshold = now - timedelta(days=threshold_days)
    stale_insights: list[StaleInsight] = []
    fresh_count = 0

    for question, data in clarifications.items():
        # Handle both dict and string formats
        if isinstance(data, dict):
            answer = data.get("answer", "")
            updated_at_str = data.get("updated_at") or data.get("answered_at")
            session_id = data.get("session_id")
        else:
            answer = str(data)
            updated_at_str = None
            session_id = None

        # Parse timestamp
        updated_at: datetime | None = None
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Determine if stale
        # Insights without updated_at are treated as stale
        is_stale = updated_at is None or updated_at < threshold

        if is_stale:
            days_stale = (now - updated_at).days if updated_at else threshold_days + 1
            stale_insights.append(
                StaleInsight(
                    question=question,
                    answer=answer,
                    updated_at=updated_at,
                    days_stale=days_stale,
                    session_id=session_id,
                )
            )
        else:
            fresh_count += 1

    total = len(clarifications)
    has_stale = len(stale_insights) > 0

    logger.info(
        f"Staleness check for user {user_id}: {len(stale_insights)}/{total} stale "
        f"(threshold={threshold_days}d)"
    )

    return InsightStalenessResult(
        has_stale_insights=has_stale,
        stale_insights=stale_insights,
        total_insights=total,
        fresh_insights_count=fresh_count,
    )


def format_insights_for_context(
    user_id: str,
    include_freshness: bool = True,
    max_insights: int = 20,
) -> str | None:
    """Format user insights for injection into meeting context.

    Args:
        user_id: User ID to get insights for
        include_freshness: Whether to include freshness indicators
        max_insights: Maximum number of insights to include

    Returns:
        Formatted context string or None if no insights
    """
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return None

    clarifications = context_data.get("clarifications", {})

    if not clarifications:
        return None

    now = datetime.now(UTC)
    lines: list[str] = []

    # Sort by updated_at (newest first), with None at end
    sorted_items = sorted(
        clarifications.items(),
        key=lambda x: _get_updated_at(x[1]) or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    for question, data in sorted_items[:max_insights]:
        if isinstance(data, dict):
            answer = data.get("answer", "")
            updated_at = _get_updated_at(data)
        else:
            answer = str(data)
            updated_at = None

        # Format freshness indicator
        freshness = ""
        if include_freshness and updated_at:
            days_ago = (now - updated_at).days
            if days_ago == 0:
                freshness = " (today)"
            elif days_ago == 1:
                freshness = " (yesterday)"
            elif days_ago < 7:
                freshness = f" ({days_ago} days ago)"
            elif days_ago < 30:
                weeks = days_ago // 7
                freshness = f" ({weeks} week{'s' if weeks > 1 else ''} ago)"
            elif days_ago < 365:
                months = days_ago // 30
                freshness = f" ({months} month{'s' if months > 1 else ''} ago)"
            else:
                freshness = " (over a year ago - may be outdated)"
        elif include_freshness and not updated_at:
            freshness = " (date unknown)"

        lines.append(f"• {question}{freshness}")
        lines.append(f"  → {answer}")

    if not lines:
        return None

    return "\n".join(lines)


def _get_updated_at(data: Any) -> datetime | None:
    """Extract updated_at timestamp from insight data."""
    if not isinstance(data, dict):
        return None

    ts_str = data.get("updated_at") or data.get("answered_at")
    if not ts_str:
        return None

    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# =============================================================================
# Stale Metric Detection (Volatility-Aware)
# =============================================================================


class StaleMetricsResult(BaseModel):
    """Result of stale metrics check."""

    has_stale_metrics: bool
    stale_metrics: list[StaleMetric]
    total_metrics_checked: int


# Metrics that can be refreshed by user
REFRESHABLE_METRICS = {
    "revenue",
    "customers",
    "growth_rate",
    "team_size",
    "mau_bucket",
    "competitors",
    "business_stage",
    "primary_objective",
}


def get_stale_metrics_for_session(
    user_id: str,
    action_affected_fields: list[str] | None = None,
    max_results: int = MAX_STALE_METRICS,
) -> StaleMetricsResult:
    """Get metrics that are stale and need refreshing before a meeting.

    Considers:
    1. Age-based staleness (per volatility level threshold)
    2. Action-affected metrics (fields related to completed actions)
    3. Volatility classification (higher volatility = shorter threshold)

    Args:
        user_id: User ID to check metrics for
        action_affected_fields: Fields affected by recent actions (flag for refresh)
        max_results: Maximum number of stale metrics to return

    Returns:
        StaleMetricsResult with prioritized list of stale metrics
    """
    context_data = user_repository.get_context(user_id)

    if not context_data:
        logger.debug(f"No context found for user {user_id}")
        return StaleMetricsResult(
            has_stale_metrics=False,
            stale_metrics=[],
            total_metrics_checked=0,
        )

    metric_history = context_data.get("context_metric_history", {})
    now = datetime.now(UTC)
    stale_metrics: list[StaleMetric] = []
    metrics_checked = 0

    # Check each refreshable metric
    for field_name in REFRESHABLE_METRICS:
        current_value = context_data.get(field_name)

        # Skip if no value exists
        if current_value is None:
            continue

        metrics_checked += 1
        history = metric_history.get(field_name, [])

        # Classify volatility
        volatility = classify_volatility(field_name, history)
        threshold_days = get_staleness_threshold(volatility)

        # Get last update time
        updated_at: datetime | None = None
        if history:
            try:
                updated_at = datetime.fromisoformat(
                    history[0].get("recorded_at", "").replace("Z", "+00:00")
                )
            except (ValueError, AttributeError, IndexError):
                pass

        # Check for action-affected staleness first (highest priority)
        if action_affected_fields and field_name in action_affected_fields:
            stale_metrics.append(
                StaleMetric(
                    field_name=field_name,
                    current_value=current_value,
                    updated_at=updated_at,
                    days_since_update=(now - updated_at).days if updated_at else 999,
                    reason=StalenessReason.ACTION_AFFECTED,
                    volatility=volatility,
                    threshold_days=threshold_days,
                )
            )
            continue

        # Check age-based staleness
        if updated_at is None:
            # No history - use default threshold and mark as stale
            stale_metrics.append(
                StaleMetric(
                    field_name=field_name,
                    current_value=current_value,
                    updated_at=None,
                    days_since_update=999,
                    reason=StalenessReason.AGE,
                    volatility=volatility,
                    threshold_days=threshold_days,
                )
            )
        else:
            days_since_update = (now - updated_at).days
            if days_since_update > threshold_days:
                stale_metrics.append(
                    StaleMetric(
                        field_name=field_name,
                        current_value=current_value,
                        updated_at=updated_at,
                        days_since_update=days_since_update,
                        reason=StalenessReason.AGE,
                        volatility=volatility,
                        threshold_days=threshold_days,
                    )
                )

    # Sort by priority: action_affected first, then by days_since_update
    stale_metrics.sort(
        key=lambda m: (
            0 if m.reason == StalenessReason.ACTION_AFFECTED else 1,
            -m.days_since_update,  # More stale = higher priority
        )
    )

    # Limit to max results
    stale_metrics = stale_metrics[:max_results]

    has_stale = len(stale_metrics) > 0

    logger.info(
        f"Stale metrics check for user {user_id}: {len(stale_metrics)}/{metrics_checked} stale"
    )

    return StaleMetricsResult(
        has_stale_metrics=has_stale,
        stale_metrics=stale_metrics,
        total_metrics_checked=metrics_checked,
    )


# =============================================================================
# Benchmark Staleness (for Monthly Check-ins)
# =============================================================================

# Benchmark-specific threshold: 30 days for monthly check-ins
BENCHMARK_STALENESS_DAYS = 30


class StaleBenchmark(BaseModel):
    """A stale benchmark value requiring user check-in."""

    field_name: str
    display_name: str
    current_value: float | int | str | None
    updated_at: datetime | None
    days_since_update: int


class StaleBenchmarksResult(BaseModel):
    """Result of stale benchmarks check."""

    has_stale_benchmarks: bool
    stale_benchmarks: list[StaleBenchmark]
    total_benchmarks_checked: int


# Benchmark metric fields (matches BENCHMARK_METRIC_FIELDS in services.py)
BENCHMARK_FIELDS = {
    "revenue",
    "customers",
    "growth_rate",
    "team_size",
    "mau_bucket",
    "revenue_stage",
    "traffic_range",
}

# Human-friendly display names
BENCHMARK_DISPLAY_NAMES = {
    "revenue": "Revenue",
    "customers": "Customer count",
    "growth_rate": "Growth rate",
    "team_size": "Team size",
    "mau_bucket": "Monthly active users",
    "revenue_stage": "Revenue stage",
    "traffic_range": "Traffic range",
}


def get_stale_benchmarks(
    user_id: str,
    threshold_days: int = BENCHMARK_STALENESS_DAYS,
) -> StaleBenchmarksResult:
    """Get benchmark metrics that are stale and need user check-in.

    Uses benchmark_timestamps to determine when each benchmark was last set.
    A benchmark is stale if:
    1. It has a value but no timestamp (never confirmed)
    2. It was last updated more than threshold_days ago

    Args:
        user_id: User ID to check benchmarks for
        threshold_days: Number of days after which benchmark is stale (default 30)

    Returns:
        StaleBenchmarksResult with list of stale benchmarks
    """
    context_data = user_repository.get_context(user_id)

    if not context_data:
        logger.debug(f"No context found for user {user_id}")
        return StaleBenchmarksResult(
            has_stale_benchmarks=False,
            stale_benchmarks=[],
            total_benchmarks_checked=0,
        )

    benchmark_timestamps = context_data.get("benchmark_timestamps", {})
    now = datetime.now(UTC)
    stale_benchmarks: list[StaleBenchmark] = []
    benchmarks_checked = 0

    for field_name in BENCHMARK_FIELDS:
        current_value = context_data.get(field_name)

        # Skip if no value exists
        if current_value is None:
            continue

        benchmarks_checked += 1

        # Get last update timestamp
        timestamp_str = benchmark_timestamps.get(field_name)
        updated_at: datetime | None = None
        if timestamp_str:
            try:
                updated_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Calculate days since update
        if updated_at:
            days_since_update = (now - updated_at).days
            is_stale = days_since_update > threshold_days
        else:
            # No timestamp = never confirmed = stale
            days_since_update = 999
            is_stale = True

        if is_stale:
            stale_benchmarks.append(
                StaleBenchmark(
                    field_name=field_name,
                    display_name=BENCHMARK_DISPLAY_NAMES.get(field_name, field_name),
                    current_value=current_value,
                    updated_at=updated_at,
                    days_since_update=days_since_update,
                )
            )

    # Sort by days_since_update (most stale first)
    stale_benchmarks.sort(key=lambda b: -b.days_since_update)

    has_stale = len(stale_benchmarks) > 0

    logger.info(
        f"Stale benchmarks check for user {user_id}: {len(stale_benchmarks)}/{benchmarks_checked} stale"
    )

    return StaleBenchmarksResult(
        has_stale_benchmarks=has_stale,
        stale_benchmarks=stale_benchmarks,
        total_benchmarks_checked=benchmarks_checked,
    )
