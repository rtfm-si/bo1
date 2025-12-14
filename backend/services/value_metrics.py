"""Value metrics service for dashboard display.

Extracts key business metrics from user context and calculates trends
from metric history. Used for the dashboard ValueMetricsPanel component.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.services.trend_calculator import TrendDirection, calculate_trend

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Classification of metric types for color coding."""

    HIGHER_IS_BETTER = "higher_is_better"  # Revenue, customers, growth → green=up, red=down
    LOWER_IS_BETTER = "lower_is_better"  # Churn, costs → green=down, red=up
    NEUTRAL = "neutral"  # Team size, etc. → no color coding


# Metric type classifications
METRIC_CLASSIFICATIONS: dict[str, MetricType] = {
    # Higher is better (green for increase)
    "revenue": MetricType.HIGHER_IS_BETTER,
    "customers": MetricType.HIGHER_IS_BETTER,
    "growth_rate": MetricType.HIGHER_IS_BETTER,
    "mau_bucket": MetricType.HIGHER_IS_BETTER,
    "mrr": MetricType.HIGHER_IS_BETTER,
    "arr": MetricType.HIGHER_IS_BETTER,
    "conversion_rate": MetricType.HIGHER_IS_BETTER,
    "retention_rate": MetricType.HIGHER_IS_BETTER,
    "nps_score": MetricType.HIGHER_IS_BETTER,
    "ltv": MetricType.HIGHER_IS_BETTER,
    "arpu": MetricType.HIGHER_IS_BETTER,
    "sales": MetricType.HIGHER_IS_BETTER,
    "profit": MetricType.HIGHER_IS_BETTER,
    "margin": MetricType.HIGHER_IS_BETTER,
    # Lower is better (green for decrease)
    "churn": MetricType.LOWER_IS_BETTER,
    "churn_rate": MetricType.LOWER_IS_BETTER,
    "costs": MetricType.LOWER_IS_BETTER,
    "cac": MetricType.LOWER_IS_BETTER,
    "burn_rate": MetricType.LOWER_IS_BETTER,
    "support_tickets": MetricType.LOWER_IS_BETTER,
    "bug_count": MetricType.LOWER_IS_BETTER,
    "bounce_rate": MetricType.LOWER_IS_BETTER,
    # Neutral (no inherent direction preference)
    "team_size": MetricType.NEUTRAL,
    "headcount": MetricType.NEUTRAL,
    "traffic_range": MetricType.NEUTRAL,
}

# Key metric fields to extract (in priority order)
KEY_METRIC_FIELDS = [
    "revenue",
    "customers",
    "growth_rate",
    "mau_bucket",
    "team_size",
    "churn_rate",
    "mrr",
    "arr",
]

# Human-readable labels for metric fields
METRIC_LABELS: dict[str, str] = {
    "revenue": "Revenue",
    "customers": "Customers",
    "growth_rate": "Growth Rate",
    "mau_bucket": "Monthly Active Users",
    "team_size": "Team Size",
    "churn_rate": "Churn Rate",
    "mrr": "MRR",
    "arr": "ARR",
    "conversion_rate": "Conversion Rate",
    "retention_rate": "Retention Rate",
    "nps_score": "NPS Score",
    "ltv": "Customer LTV",
    "arpu": "ARPU",
    "cac": "Customer Acquisition Cost",
    "burn_rate": "Burn Rate",
    "sales": "Sales",
    "profit": "Profit",
    "margin": "Margin",
    "traffic_range": "Traffic",
    "headcount": "Headcount",
}


@dataclass
class ValueMetric:
    """A single value metric with trend information."""

    name: str  # Field name (e.g., "revenue")
    label: str  # Human-readable label (e.g., "Revenue")
    current_value: str | float | int | None  # Current display value
    previous_value: str | float | int | None = None  # Previous value for comparison
    change_percent: float | None = None  # Percentage change
    trend_direction: str = "stable"  # "improving", "worsening", "stable", "insufficient_data"
    metric_type: str = "neutral"  # "higher_is_better", "lower_is_better", "neutral"
    last_updated: datetime | None = None  # When this metric was last updated
    is_positive_change: bool | None = None  # True if change is good, False if bad, None if neutral


@dataclass
class ValueMetricsResult:
    """Result of value metrics extraction."""

    metrics: list[ValueMetric] = field(default_factory=list)
    has_context: bool = False
    has_history: bool = False


def get_metric_type(field_name: str) -> MetricType:
    """Get the metric type classification for a field.

    Args:
        field_name: The metric field name

    Returns:
        MetricType classification
    """
    # Exact match first
    if field_name in METRIC_CLASSIFICATIONS:
        return METRIC_CLASSIFICATIONS[field_name]

    # Check for partial matches (e.g., "monthly_revenue" → "revenue")
    lower_name = field_name.lower()
    for key, metric_type in METRIC_CLASSIFICATIONS.items():
        if key in lower_name:
            return metric_type

    return MetricType.NEUTRAL


def determine_is_positive_change(
    trend_direction: TrendDirection,
    metric_type: MetricType,
) -> bool | None:
    """Determine if a change is positive (good) based on metric type.

    Args:
        trend_direction: The direction of the trend
        metric_type: The type of metric

    Returns:
        True if positive/good change, False if negative/bad, None if neutral
    """
    if trend_direction == TrendDirection.STABLE:
        return None
    if trend_direction == TrendDirection.INSUFFICIENT_DATA:
        return None

    if metric_type == MetricType.HIGHER_IS_BETTER:
        return trend_direction == TrendDirection.IMPROVING
    elif metric_type == MetricType.LOWER_IS_BETTER:
        # For lower-is-better metrics, "worsening" (increasing) is bad
        # and "improving" (decreasing) is good
        return trend_direction == TrendDirection.IMPROVING
    else:
        return None


def extract_value_metrics(
    context_data: dict[str, Any] | None,
    max_metrics: int = 5,
) -> ValueMetricsResult:
    """Extract key value metrics from user context with trends.

    Args:
        context_data: User's business context dictionary
        max_metrics: Maximum number of metrics to return (default 5)

    Returns:
        ValueMetricsResult with list of metrics
    """
    if not context_data:
        return ValueMetricsResult(metrics=[], has_context=False, has_history=False)

    metrics: list[ValueMetric] = []
    metric_history = context_data.get("context_metric_history", {})
    has_history = bool(metric_history)

    # First pass: collect metrics with values
    metric_candidates: list[tuple[str, Any, list[dict] | None]] = []

    for field_name in KEY_METRIC_FIELDS:
        current_value = context_data.get(field_name)
        if current_value is not None and current_value != "":
            history = metric_history.get(field_name) if metric_history else None
            metric_candidates.append((field_name, current_value, history))

    # Also check metric history for fields not in base context
    for field_name, history in metric_history.items():
        if field_name not in KEY_METRIC_FIELDS and history:
            # Use most recent history value
            current_value = history[0].get("value") if history else None
            if current_value is not None:
                metric_candidates.append((field_name, current_value, history))

    # Process candidates into metrics
    for field_name, current_value, history in metric_candidates[:max_metrics]:
        label = METRIC_LABELS.get(field_name, field_name.replace("_", " ").title())
        metric_type = get_metric_type(field_name)

        # Calculate trend if we have history
        trend = calculate_trend(field_name, history) if history else None

        # Determine last updated time
        last_updated = None
        if history and len(history) > 0:
            recorded_at = history[0].get("recorded_at")
            if recorded_at:
                try:
                    last_updated = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

        # Determine if change is positive
        is_positive = None
        if trend and trend.direction not in (
            TrendDirection.STABLE,
            TrendDirection.INSUFFICIENT_DATA,
        ):
            is_positive = determine_is_positive_change(trend.direction, metric_type)

        value_metric = ValueMetric(
            name=field_name,
            label=label,
            current_value=current_value,
            previous_value=trend.previous_value if trend else None,
            change_percent=trend.change_percent if trend else None,
            trend_direction=trend.direction.value if trend else "insufficient_data",
            metric_type=metric_type.value,
            last_updated=last_updated,
            is_positive_change=is_positive,
        )
        metrics.append(value_metric)

    return ValueMetricsResult(
        metrics=metrics,
        has_context=bool(context_data),
        has_history=has_history,
    )


def format_metric_value(value: Any, field_name: str = "") -> str:
    """Format a metric value for display.

    Args:
        value: The raw metric value
        field_name: Optional field name for context-aware formatting

    Returns:
        Formatted string for display
    """
    if value is None:
        return "—"

    # Already a formatted string
    if isinstance(value, str):
        return value

    # Format numbers based on field type
    if isinstance(value, (int, float)):
        field_lower = field_name.lower()

        # Currency fields
        if any(k in field_lower for k in ["revenue", "mrr", "arr", "cac", "ltv", "arpu", "cost"]):
            if value >= 1_000_000:
                return f"${value / 1_000_000:.1f}M"
            elif value >= 1_000:
                return f"${value / 1_000:.1f}K"
            else:
                return f"${value:,.0f}"

        # Percentage fields
        if any(k in field_lower for k in ["rate", "churn", "growth", "margin", "conversion"]):
            return f"{value:.1f}%"

        # Count fields
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:,.0f}"

    return str(value)
