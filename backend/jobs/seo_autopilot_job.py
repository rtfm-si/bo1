"""SEO Autopilot background job.

Runs daily to:
- Check which users have autopilot enabled
- Run topic discovery and article generation cycles
- Respect tier limits and frequency settings
"""

import asyncio
import logging
from datetime import UTC, datetime

from backend.services.seo_autopilot import run_autopilot_for_all_users

logger = logging.getLogger(__name__)


def run_seo_autopilot_job() -> dict:
    """Run the SEO autopilot job for all enabled users.

    This job should be scheduled to run once per day (e.g., at 9am UTC).
    The frequency_per_week setting in each user's config determines
    how many articles are generated per week.

    For weekly scheduling:
    - frequency=1: Run on Mondays only
    - frequency=3: Run on Mon, Wed, Fri
    - frequency=7: Run daily

    Returns:
        Dict with stats: {users_processed, articles_generated, articles_queued,
                         articles_published, errors, tier_limits_reached}
    """
    start_time = datetime.now(UTC)
    logger.info("Starting SEO autopilot job")

    try:
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            stats = loop.run_until_complete(run_autopilot_for_all_users())
        finally:
            loop.close()

        duration = (datetime.now(UTC) - start_time).total_seconds()

        logger.info(
            f"SEO autopilot job complete in {duration:.1f}s: "
            f"users={stats['users_processed']}, "
            f"articles={stats['articles_generated']}, "
            f"queued={stats['articles_queued']}, "
            f"published={stats['articles_published']}, "
            f"errors={stats['errors']}"
        )

        return stats

    except Exception as e:
        logger.error(f"SEO autopilot job failed: {e}")
        return {
            "users_processed": 0,
            "articles_generated": 0,
            "articles_queued": 0,
            "articles_published": 0,
            "errors": 1,
            "tier_limits_reached": 0,
            "error_message": str(e),
        }


def should_run_today(frequency_per_week: int) -> bool:
    """Determine if autopilot should run today based on frequency.

    Args:
        frequency_per_week: How many times per week to run (1-7)

    Returns:
        True if should run today
    """
    today = datetime.now(UTC)
    weekday = today.weekday()  # Monday=0, Sunday=6

    if frequency_per_week >= 7:
        return True
    elif frequency_per_week >= 5:
        # Mon-Fri
        return weekday < 5
    elif frequency_per_week >= 3:
        # Mon, Wed, Fri
        return weekday in [0, 2, 4]
    elif frequency_per_week >= 2:
        # Mon, Thu
        return weekday in [0, 3]
    else:
        # Mon only
        return weekday == 0


if __name__ == "__main__":
    # Allow running directly for testing
    logging.basicConfig(level=logging.INFO)
    result = run_seo_autopilot_job()
    print(f"Result: {result}")
