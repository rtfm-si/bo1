"""Research metrics tracking for success rate and effectiveness analysis.

Tracks research success rate by depth (basic vs deep) and keyword routing.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class ResearchMetric:
    """Single research metric entry.

    Attributes:
        query: Research query
        research_depth: "basic" or "deep"
        keywords_matched: Keywords that triggered this depth
        success: Whether research returned useful results
        cached: Whether result came from cache
        sources_count: Number of sources returned
        confidence: Confidence level of result
        cost_usd: Cost of research
        response_time_ms: Response time in milliseconds
        timestamp: When research was performed
    """

    query: str
    research_depth: Literal["basic", "deep"]
    keywords_matched: list[str]
    success: bool
    cached: bool
    sources_count: int
    confidence: str
    cost_usd: float
    response_time_ms: float
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


def track_research_metric(metric: ResearchMetric) -> None:
    """Track a research metric to database.

    Args:
        metric: ResearchMetric to track

    Example:
        >>> metric = ResearchMetric(
        ...     query="competitor pricing",
        ...     research_depth="deep",
        ...     keywords_matched=["competitor", "pricing"],
        ...     success=True,
        ...     cached=False,
        ...     sources_count=5,
        ...     confidence="high",
        ...     cost_usd=0.025,
        ...     response_time_ms=1250.5,
        ... )
        >>> track_research_metric(metric)
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO research_metrics (
                        query, research_depth, keywords_matched, success,
                        cached, sources_count, confidence, cost_usd,
                        response_time_ms, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        metric.query,
                        metric.research_depth,
                        json.dumps(metric.keywords_matched),  # Store as JSON array
                        metric.success,
                        metric.cached,
                        metric.sources_count,
                        metric.confidence,
                        metric.cost_usd,
                        metric.response_time_ms,
                        metric.timestamp,
                    ),
                )
        logger.debug(
            f"Tracked research metric: {metric.query[:50]}... (depth={metric.research_depth})"
        )
    except Exception as e:
        # Don't fail research on metrics tracking error
        logger.warning(f"Failed to track research metric: {e}")


def get_research_success_rate(
    depth: Literal["basic", "deep"] | None = None,
    days: int = 30,
) -> dict[str, float]:
    """Get research success rate by depth.

    Args:
        depth: Filter by research depth (None = all)
        days: Number of days to analyze (default: 30)

    Returns:
        Dictionary with success rate statistics:
        {
            "total_requests": int,
            "successful_requests": int,
            "success_rate": float (0-100),
            "avg_sources": float,
            "avg_cost_usd": float,
            "avg_response_time_ms": float,
            "cache_hit_rate": float (0-100),
        }

    Example:
        >>> stats = get_research_success_rate(depth="deep", days=7)
        >>> print(f"Deep research success rate: {stats['success_rate']:.1f}%")
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        COUNT(*) as total_requests,
                        COUNT(*) FILTER (WHERE success = true) as successful_requests,
                        AVG(sources_count) as avg_sources,
                        AVG(cost_usd) as avg_cost_usd,
                        AVG(response_time_ms) as avg_response_time_ms,
                        COUNT(*) FILTER (WHERE cached = true) as cache_hits
                    FROM research_metrics
                    WHERE timestamp >= NOW() - INTERVAL '%s days'
                """

                params: list[int | str] = [days]

                if depth:
                    query += " AND research_depth = %s"
                    params.append(depth)

                cur.execute(query, params)
                result = cur.fetchone()

                if not result or result["total_requests"] == 0:
                    return {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "success_rate": 0.0,
                        "avg_sources": 0.0,
                        "avg_cost_usd": 0.0,
                        "avg_response_time_ms": 0.0,
                        "cache_hit_rate": 0.0,
                    }

                total = result["total_requests"]
                successful = result["successful_requests"]
                cache_hits = result["cache_hits"]

                return {
                    "total_requests": total,
                    "successful_requests": successful,
                    "success_rate": (successful / total * 100) if total > 0 else 0.0,
                    "avg_sources": float(result["avg_sources"] or 0.0),
                    "avg_cost_usd": float(result["avg_cost_usd"] or 0.0),
                    "avg_response_time_ms": float(result["avg_response_time_ms"] or 0.0),
                    "cache_hit_rate": (cache_hits / total * 100) if total > 0 else 0.0,
                }

    except Exception as e:
        logger.error(f"Failed to get research success rate: {e}")
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "success_rate": 0.0,
            "avg_sources": 0.0,
            "avg_cost_usd": 0.0,
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
        }


def get_keyword_routing_effectiveness(days: int = 30) -> list[dict[str, Any]]:
    """Get effectiveness of keyword routing for depth selection.

    Analyzes which keywords trigger deep research and their success rates.

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        List of keyword statistics:
        [
            {
                "keyword": "competitor",
                "total_uses": 10,
                "success_rate": 90.0,
                "avg_sources": 4.5,
                "depth_distribution": {"deep": 8, "basic": 2},
            },
            ...
        ]

    Example:
        >>> stats = get_keyword_routing_effectiveness(days=7)
        >>> for kw in stats:
        ...     print(f"{kw['keyword']}: {kw['success_rate']:.1f}% success")
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Query to extract keywords from JSON array and aggregate
                cur.execute(
                    """
                    WITH keyword_metrics AS (
                        SELECT
                            jsonb_array_elements_text(keywords_matched::jsonb) as keyword,
                            research_depth,
                            success,
                            sources_count
                        FROM research_metrics
                        WHERE timestamp >= NOW() - INTERVAL '%s days'
                    )
                    SELECT
                        keyword,
                        COUNT(*) as total_uses,
                        COUNT(*) FILTER (WHERE success = true) as successful_uses,
                        AVG(sources_count) as avg_sources,
                        COUNT(*) FILTER (WHERE research_depth = 'deep') as deep_count,
                        COUNT(*) FILTER (WHERE research_depth = 'basic') as basic_count
                    FROM keyword_metrics
                    GROUP BY keyword
                    ORDER BY total_uses DESC
                    LIMIT 20
                    """,
                    (days,),
                )

                results = []
                for row in cur.fetchall():
                    total = row["total_uses"]
                    successful = row["successful_uses"]

                    results.append(
                        {
                            "keyword": row["keyword"],
                            "total_uses": total,
                            "success_rate": (successful / total * 100) if total > 0 else 0.0,
                            "avg_sources": float(row["avg_sources"] or 0.0),
                            "depth_distribution": {
                                "deep": row["deep_count"],
                                "basic": row["basic_count"],
                            },
                        }
                    )

                return results

    except Exception as e:
        logger.error(f"Failed to get keyword routing effectiveness: {e}")
        return []


def get_research_metrics_summary(days: int = 30) -> dict[str, Any]:
    """Get comprehensive research metrics summary.

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        Dictionary with comprehensive metrics:
        {
            "basic_research": {...},  # Success rate for basic research
            "deep_research": {...},   # Success rate for deep research
            "keyword_routing": [...], # Keyword effectiveness
            "overall": {...},         # Overall statistics
        }

    Example:
        >>> summary = get_research_metrics_summary(days=7)
        >>> print(f"Basic: {summary['basic_research']['success_rate']:.1f}%")
        >>> print(f"Deep: {summary['deep_research']['success_rate']:.1f}%")
    """
    return {
        "basic_research": get_research_success_rate(depth="basic", days=days),
        "deep_research": get_research_success_rate(depth="deep", days=days),
        "keyword_routing": get_keyword_routing_effectiveness(days=days),
        "overall": get_research_success_rate(depth=None, days=days),
    }
