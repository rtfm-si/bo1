"""Research cache cleanup job for TTL enforcement.

Provides:
- cleanup_research_cache: Delete stale cache entries based on TTL
- Prometheus metrics for monitoring cleanup operations
"""

import logging
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter, Gauge

from bo1.constants import ResearchCacheConfig
from bo1.state.repositories import cache_repository

logger = logging.getLogger(__name__)

# Prometheus metrics
CLEANUP_TOTAL = Counter(
    "bo1_research_cache_cleanup_total",
    "Total research cache cleanup operations",
    ["status"],  # success, error
)

CLEANUP_DELETED = Counter(
    "bo1_research_cache_cleanup_deleted_total",
    "Total research cache entries deleted",
)

CACHE_SIZE = Gauge(
    "bo1_research_cache_size_total",
    "Current research cache size (entry count)",
)


def cleanup_research_cache(
    max_age_days: int | None = None,
    access_grace_days: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delete stale research cache entries.

    Args:
        max_age_days: Override TTL (default: ResearchCacheConfig.CLEANUP_TTL_DAYS)
        access_grace_days: Override grace period (default: ResearchCacheConfig.CLEANUP_ACCESS_GRACE_DAYS)
        dry_run: If True, only report what would be deleted without actually deleting

    Returns:
        Dict with cleanup statistics
    """
    ttl = max_age_days or ResearchCacheConfig.CLEANUP_TTL_DAYS
    grace = access_grace_days or ResearchCacheConfig.CLEANUP_ACCESS_GRACE_DAYS

    stats = {
        "entries_deleted": 0,
        "iterations": 0,
        "dry_run": dry_run,
        "max_age_days": ttl,
        "access_grace_days": grace,
        "run_at": datetime.now(UTC).isoformat(),
    }

    logger.info(
        f"Starting research cache cleanup (ttl={ttl} days, grace={grace} days, dry_run={dry_run})"
    )

    try:
        if dry_run:
            # Just count what would be deleted
            stale_entries = cache_repository.get_stale(days_old=ttl)
            stats["entries_deleted"] = len(stale_entries)
            logger.info(f"Dry run: would delete {stats['entries_deleted']} entries")
        else:
            # Delete in batches until no more stale entries
            total_deleted = 0
            iterations = 0
            max_iterations = 100  # Safety limit

            while iterations < max_iterations:
                deleted = cache_repository.delete_stale(
                    max_age_days=ttl,
                    access_grace_days=grace,
                )
                iterations += 1
                total_deleted += deleted

                if deleted == 0:
                    break

            stats["entries_deleted"] = total_deleted
            stats["iterations"] = iterations

            # Update metrics
            CLEANUP_DELETED.inc(total_deleted)

        # Get current cache size for metric
        cache_stats = cache_repository.get_stats()
        cache_size = cache_stats.get("total_cached_results", 0)
        CACHE_SIZE.set(cache_size)
        stats["cache_size_after"] = cache_size

        CLEANUP_TOTAL.labels(status="success").inc()
        logger.info(f"Research cache cleanup complete: {stats}")

    except Exception as e:
        CLEANUP_TOTAL.labels(status="error").inc()
        stats["error"] = str(e)
        logger.error(f"Research cache cleanup failed: {e}", exc_info=True)

    return stats


if __name__ == "__main__":
    # CLI entry point for cron jobs
    import argparse

    parser = argparse.ArgumentParser(description="Run research cache cleanup job")
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help=f"Override TTL in days (default: {ResearchCacheConfig.CLEANUP_TTL_DAYS})",
    )
    parser.add_argument(
        "--access-grace-days",
        type=int,
        default=None,
        help=f"Override access grace period in days (default: {ResearchCacheConfig.CLEANUP_ACCESS_GRACE_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    result = cleanup_research_cache(
        max_age_days=args.max_age_days,
        access_grace_days=args.access_grace_days,
        dry_run=args.dry_run,
    )

    print(f"Cleanup result: {result}")
