"""Insight staleness detection service.

Provides utilities for detecting stale insights and formatting
insight context for meeting injection.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from bo1.state.repositories import user_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

# Default threshold for stale insights (30 days)
DEFAULT_STALENESS_DAYS = 30


class StaleInsight(BaseModel):
    """A stale insight requiring user attention."""

    question: str
    answer: str
    updated_at: datetime | None
    days_stale: int
    session_id: str | None = None


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
