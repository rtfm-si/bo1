"""Daily cost summary aggregation job.

Aggregates api_costs by provider and category into daily_cost_summary table.
Designed to run at 00:05 UTC daily via scheduler.

Categories:
- llm_inference: Anthropic completions
- embeddings: Voyage embeddings
- search: Brave/Tavily searches
- email: Resend email (from fixed costs, not api_costs)
- storage: DO Spaces (from fixed costs)
- compute: DO Droplet (from fixed costs)
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Provider to category mapping
PROVIDER_CATEGORY_MAP = {
    "anthropic": "llm_inference",
    "voyage": "embeddings",
    "brave": "search",
    "tavily": "search",
    "openai": "llm_inference",
}


def aggregate_daily_costs(target_date: date | None = None) -> dict[str, Any]:
    """Aggregate api_costs for a specific date into daily_cost_summary.

    Args:
        target_date: Date to aggregate (default: yesterday)

    Returns:
        Dict with aggregation statistics
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    logger.info(f"Aggregating costs for {target_date}")

    stats = {
        "date": target_date.isoformat(),
        "providers_processed": 0,
        "total_amount": 0.0,
        "total_requests": 0,
    }

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get aggregated costs by provider for the target date
                cur.execute(
                    """
                    SELECT
                        provider,
                        COUNT(*) as request_count,
                        COALESCE(SUM(total_cost), 0) as total_amount
                    FROM api_costs
                    WHERE created_at >= %s::date
                      AND created_at < (%s::date + INTERVAL '1 day')
                    GROUP BY provider
                    """,
                    (target_date, target_date),
                )

                rows = cur.fetchall()
                if not rows:
                    logger.info(f"No api_costs found for {target_date}")
                    return stats

                # Upsert each provider's daily summary
                for row in rows:
                    provider = row["provider"]
                    request_count = row["request_count"]
                    amount = float(row["total_amount"])

                    # Determine category from provider
                    category = PROVIDER_CATEGORY_MAP.get(provider, "other")

                    # Upsert into daily_cost_summary
                    cur.execute(
                        """
                        INSERT INTO daily_cost_summary (date, provider, category, amount_usd, request_count)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (date, provider, category)
                        DO UPDATE SET
                            amount_usd = EXCLUDED.amount_usd,
                            request_count = EXCLUDED.request_count,
                            updated_at = NOW()
                        """,
                        (target_date, provider, category, amount, request_count),
                    )

                    stats["providers_processed"] += 1
                    stats["total_amount"] += amount
                    stats["total_requests"] += request_count

                    logger.debug(f"Aggregated {provider}: ${amount:.4f} ({request_count} requests)")

        logger.info(
            f"Cost aggregation complete for {target_date}: "
            f"{stats['providers_processed']} providers, "
            f"${stats['total_amount']:.4f} total"
        )
        return stats

    except Exception as e:
        logger.error(f"Cost aggregation failed for {target_date}: {e}")
        raise


def backfill_daily_summaries(days: int = 30) -> dict[str, Any]:
    """Backfill daily cost summaries for the past N days.

    Args:
        days: Number of days to backfill

    Returns:
        Dict with backfill statistics
    """
    logger.info(f"Backfilling cost summaries for last {days} days")

    stats = {
        "days_processed": 0,
        "total_amount": 0.0,
        "total_requests": 0,
    }

    today = date.today()
    for i in range(1, days + 1):
        target_date = today - timedelta(days=i)
        day_stats = aggregate_daily_costs(target_date)
        stats["days_processed"] += 1
        stats["total_amount"] += day_stats["total_amount"]
        stats["total_requests"] += day_stats["total_requests"]

    logger.info(f"Backfill complete: {stats['days_processed']} days processed")
    return stats


def run_daily_cost_summary() -> dict[str, Any]:
    """Run the daily cost summary job.

    Aggregates yesterday's costs into daily_cost_summary table.

    Returns:
        Dict with job statistics
    """
    logger.info("Starting daily cost summary job")

    try:
        stats = aggregate_daily_costs()
        stats["run_at"] = datetime.now(UTC).isoformat()
        logger.info(f"Daily cost summary job complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Daily cost summary job failed: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run daily cost summary job")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date (YYYY-MM-DD), default: yesterday",
    )
    parser.add_argument(
        "--backfill",
        type=int,
        default=None,
        help="Backfill N days instead of single day",
    )
    args = parser.parse_args()

    if args.backfill:
        result = backfill_daily_summaries(args.backfill)
    elif args.date:
        target = date.fromisoformat(args.date)
        result = aggregate_daily_costs(target)
    else:
        result = run_daily_cost_summary()

    print(f"Result: {result}")
