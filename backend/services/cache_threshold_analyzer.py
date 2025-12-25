"""Cache threshold analyzer service for optimizing research cache hit rates.

Provides:
- Threshold recommendation algorithm based on hit rate data
- Analysis of near-miss distribution to tune similarity thresholds
- Prometheus metrics for threshold recommendations
"""

from bo1.constants import SimilarityCacheThresholds
from bo1.state.repositories import cache_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

# Thresholds for recommendation algorithm
LOW_HIT_RATE_THRESHOLD = 10.0  # Below 10% hit rate = too strict
HIGH_HIT_RATE_THRESHOLD = 60.0  # Above 60% hit rate = possible false positives
NEAR_MISS_SIMILARITY_THRESHOLD = 0.80  # Avg near-miss similarity to consider lowering

# Recommended threshold adjustments
LOWER_THRESHOLD = 0.80  # When hit rate is too low
RAISE_THRESHOLD = 0.88  # When hit rate is too high
DEFAULT_THRESHOLD = SimilarityCacheThresholds.RESEARCH_CACHE  # 0.85


def calculate_recommended_threshold(
    hit_rate_30d: float,
    avg_similarity_on_hit: float,
    near_miss_count: int = 0,
) -> dict:
    """Calculate recommended similarity threshold based on cache performance.

    Algorithm:
    - If hit rate <10% and avg near-miss similarity >0.80 → recommend lowering to 0.80
    - If hit rate >60% and many false positives reported → recommend raising to 0.88
    - Otherwise maintain current (0.85)

    Args:
        hit_rate_30d: Cache hit rate percentage over last 30 days
        avg_similarity_on_hit: Average similarity score for cache hits
        near_miss_count: Number of near-misses in the 0.70-0.85 range

    Returns:
        Dictionary with current, recommended threshold and reason
    """
    current_threshold = SimilarityCacheThresholds.RESEARCH_CACHE
    recommended = current_threshold
    reason = "Current threshold performing optimally"
    confidence = "high"

    # Check for low hit rate
    if hit_rate_30d < LOW_HIT_RATE_THRESHOLD:
        if near_miss_count > 10 or avg_similarity_on_hit > NEAR_MISS_SIMILARITY_THRESHOLD:
            recommended = LOWER_THRESHOLD
            reason = (
                f"Hit rate ({hit_rate_30d:.1f}%) is below {LOW_HIT_RATE_THRESHOLD}% "
                f"with {near_miss_count} near-misses. Lowering threshold may capture more hits."
            )
            confidence = "medium" if near_miss_count > 20 else "low"
        else:
            reason = (
                f"Hit rate ({hit_rate_30d:.1f}%) is low but insufficient near-miss data. "
                "Continue monitoring before adjusting."
            )
            confidence = "low"

    # Check for high hit rate (potential false positives)
    elif hit_rate_30d > HIGH_HIT_RATE_THRESHOLD:
        if avg_similarity_on_hit < 0.90:
            recommended = RAISE_THRESHOLD
            reason = (
                f"Hit rate ({hit_rate_30d:.1f}%) is above {HIGH_HIT_RATE_THRESHOLD}% "
                f"with avg similarity {avg_similarity_on_hit:.2f}. "
                "Consider raising threshold to reduce false positives."
            )
            confidence = "medium"
        else:
            reason = (
                f"Hit rate ({hit_rate_30d:.1f}%) is high but similarity scores are strong. "
                "No adjustment needed."
            )

    logger.info(
        f"Threshold recommendation: current={current_threshold}, "
        f"recommended={recommended}, hit_rate={hit_rate_30d:.1f}%, "
        f"reason={reason}"
    )

    return {
        "current_threshold": current_threshold,
        "recommended_threshold": recommended,
        "change_needed": recommended != current_threshold,
        "reason": reason,
        "confidence": confidence,
        "metrics": {
            "hit_rate_30d": hit_rate_30d,
            "avg_similarity_on_hit": avg_similarity_on_hit,
            "near_miss_count": near_miss_count,
        },
    }


def get_full_cache_metrics() -> dict:
    """Get comprehensive cache metrics for admin dashboard.

    Returns:
        Dictionary with all cache metrics including multi-period hit rates,
        miss distribution, and threshold recommendation.
    """
    # Get hit rate metrics for different periods
    metrics_1d = cache_repository.get_hit_rate_metrics(1)
    metrics_7d = cache_repository.get_hit_rate_metrics(7)
    metrics_30d = cache_repository.get_hit_rate_metrics(30)

    # Get average similarity on hits
    avg_similarity = cache_repository.get_avg_similarity_on_hit(30)

    # Get miss distribution
    miss_distribution = cache_repository.get_miss_similarity_distribution()
    near_miss_count = sum(bucket["count"] for bucket in miss_distribution)

    # Get basic stats
    basic_stats = cache_repository.get_stats()

    # Calculate recommendation
    recommendation = calculate_recommended_threshold(
        hit_rate_30d=metrics_30d["hit_rate"],
        avg_similarity_on_hit=avg_similarity,
        near_miss_count=near_miss_count,
    )

    return {
        "hit_rate_1d": metrics_1d["hit_rate"],
        "hit_rate_7d": metrics_7d["hit_rate"],
        "hit_rate_30d": metrics_30d["hit_rate"],
        "total_queries_1d": metrics_1d["total_queries"],
        "total_queries_7d": metrics_7d["total_queries"],
        "total_queries_30d": metrics_30d["total_queries"],
        "cache_hits_1d": metrics_1d["cache_hits"],
        "cache_hits_7d": metrics_7d["cache_hits"],
        "cache_hits_30d": metrics_30d["cache_hits"],
        "avg_similarity_on_hit": avg_similarity,
        "miss_distribution": miss_distribution,
        "current_threshold": SimilarityCacheThresholds.RESEARCH_CACHE,
        "recommended_threshold": recommendation["recommended_threshold"],
        "recommendation_reason": recommendation["reason"],
        "recommendation_confidence": recommendation["confidence"],
        "total_cached_results": basic_stats["total_cached_results"],
        "cost_savings_30d": basic_stats["cost_savings_30d"],
    }
