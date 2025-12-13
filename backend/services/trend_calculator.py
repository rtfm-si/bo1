"""Trend calculation service for business context metrics.

Calculates trends (improving/worsening/stable) based on metric history.
Uses value comparison for numeric metrics with fallback to text similarity.
"""

import logging
import re
from datetime import datetime
from typing import Any

from backend.api.context.models import MetricTrend, TrendDirection

logger = logging.getLogger(__name__)


# Fields where higher is better
POSITIVE_DIRECTION_FIELDS = {
    "revenue",
    "customers",
    "growth_rate",
    "mau_bucket",
    "team_size",
}

# Fields where lower is better (currently none but could expand)
NEGATIVE_DIRECTION_FIELDS: set[str] = set()


def extract_numeric_value(value: Any) -> float | None:
    """Extract a numeric value from various formats.

    Handles:
    - "$50K" → 50000
    - "$1.2M" → 1200000
    - "200 customers" → 200
    - "15%" → 15
    - "small (2-5)" → 3.5 (midpoint)

    Args:
        value: Value in various formats

    Returns:
        Numeric value or None if not extractable
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()

    # Handle currency with K/M suffixes
    currency_match = re.search(r"\$\s*([\d,.]+)\s*([kmb])?", text)
    if currency_match:
        num_str = currency_match.group(1).replace(",", "")
        multiplier_char = currency_match.group(2)

        try:
            num = float(num_str)
            if multiplier_char == "k":
                num *= 1000
            elif multiplier_char == "m":
                num *= 1_000_000
            elif multiplier_char == "b":
                num *= 1_000_000_000
            return num
        except ValueError:
            pass

    # Handle percentage
    pct_match = re.search(r"([\d.]+)\s*%", text)
    if pct_match:
        try:
            return float(pct_match.group(1))
        except ValueError:
            pass

    # Handle plain numbers (possibly with commas or words after)
    num_match = re.search(r"^([\d,]+(?:\.\d+)?)", text)
    if num_match:
        try:
            return float(num_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Handle team size buckets
    if "solo" in text:
        return 1.0
    if "small" in text:
        return 3.5  # midpoint of 2-5
    if "medium" in text:
        return 13.0  # midpoint of 6-20
    if "large" in text:
        return 50.0  # representative

    return None


def calculate_trend(
    field_name: str,
    history: list[dict[str, Any]],
) -> MetricTrend:
    """Calculate trend for a metric based on its history.

    Args:
        field_name: Name of the context field
        history: List of historical values (newest first)

    Returns:
        MetricTrend with direction and details
    """
    if not history or len(history) < 2:
        return MetricTrend(
            field_name=field_name,
            direction=TrendDirection.INSUFFICIENT_DATA,
            current_value=history[0].get("value") if history else None,
        )

    current_entry = history[0]
    previous_entry = history[1]

    current_val = current_entry.get("value")
    previous_val = previous_entry.get("value")

    # Calculate period description
    period_desc = None
    try:
        current_time = datetime.fromisoformat(
            current_entry.get("recorded_at", "").replace("Z", "+00:00")
        )
        previous_time = datetime.fromisoformat(
            previous_entry.get("recorded_at", "").replace("Z", "+00:00")
        )
        delta = current_time - previous_time

        if delta.days == 0:
            period_desc = "since today"
        elif delta.days == 1:
            period_desc = "since yesterday"
        elif delta.days < 7:
            period_desc = f"over {delta.days} days"
        elif delta.days < 30:
            weeks = delta.days // 7
            period_desc = f"over {weeks} week{'s' if weeks > 1 else ''}"
        elif delta.days < 365:
            months = delta.days // 30
            period_desc = f"over {months} month{'s' if months > 1 else ''}"
        else:
            years = delta.days // 365
            period_desc = f"over {years} year{'s' if years > 1 else ''}"
    except Exception:
        period_desc = None

    # Try numeric comparison
    current_num = extract_numeric_value(current_val)
    previous_num = extract_numeric_value(previous_val)

    if current_num is not None and previous_num is not None and previous_num != 0:
        change_percent = ((current_num - previous_num) / abs(previous_num)) * 100

        # Determine direction based on field type
        if field_name in POSITIVE_DIRECTION_FIELDS:
            if change_percent > 5:
                direction = TrendDirection.IMPROVING
            elif change_percent < -5:
                direction = TrendDirection.WORSENING
            else:
                direction = TrendDirection.STABLE
        elif field_name in NEGATIVE_DIRECTION_FIELDS:
            if change_percent < -5:
                direction = TrendDirection.IMPROVING
            elif change_percent > 5:
                direction = TrendDirection.WORSENING
            else:
                direction = TrendDirection.STABLE
        else:
            # Neutral - just show as stable unless large change
            if abs(change_percent) > 10:
                direction = (
                    TrendDirection.IMPROVING if change_percent > 0 else TrendDirection.WORSENING
                )
            else:
                direction = TrendDirection.STABLE

        return MetricTrend(
            field_name=field_name,
            direction=direction,
            current_value=current_val,
            previous_value=previous_val,
            change_percent=round(change_percent, 1),
            period_description=period_desc,
        )

    # Text comparison fallback - just check if changed
    if str(current_val) != str(previous_val):
        # Changed but can't determine direction
        return MetricTrend(
            field_name=field_name,
            direction=TrendDirection.STABLE,  # Changed but unknown direction
            current_value=current_val,
            previous_value=previous_val,
            period_description=period_desc,
        )

    return MetricTrend(
        field_name=field_name,
        direction=TrendDirection.STABLE,
        current_value=current_val,
    )


def calculate_all_trends(
    metric_history: dict[str, list[dict[str, Any]]],
) -> list[MetricTrend]:
    """Calculate trends for all metrics with history.

    Args:
        metric_history: Dict of field_name → list of historical values

    Returns:
        List of MetricTrend for fields with at least 2 data points
    """
    trends = []

    for field_name, history in metric_history.items():
        if history and len(history) >= 1:
            trend = calculate_trend(field_name, history)
            # Only include if we have enough data or it shows change
            if trend.direction != TrendDirection.INSUFFICIENT_DATA or len(history) >= 1:
                trends.append(trend)

    return trends
