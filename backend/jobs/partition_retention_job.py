"""Partition retention job for automated partition lifecycle management.

Daily job that:
- Creates partitions for the next 3 months
- Drops partitions older than the configured retention period

Run via cron:
    0 3 * * * python -m backend.jobs.partition_retention_job

Or invoke programmatically:
    from backend.jobs.partition_retention_job import run_retention_job
    results = run_retention_job()
"""

import logging
from datetime import UTC, datetime
from typing import Any

from backend.services.partition_manager import (
    PARTITIONED_TABLES,
    PartitionResult,
    drop_old_partitions,
    ensure_future_partitions,
    get_all_partition_stats,
)
from bo1.constants import PartitionRetention

logger = logging.getLogger(__name__)


def run_retention_job(
    months_ahead: int = 3,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute partition retention job.

    Creates future partitions and drops expired ones based on
    per-table retention periods defined in PartitionRetention.

    Args:
        months_ahead: Number of months to pre-create partitions for
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dict with job results including created/dropped partitions per table
    """
    started_at = datetime.now(UTC)
    logger.info(f"Starting partition retention job (dry_run={dry_run})")

    results: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "dry_run": dry_run,
        "tables": {},
        "summary": {
            "partitions_created": 0,
            "partitions_dropped": 0,
            "partitions_skipped": 0,
            "errors": 0,
        },
    }

    # Get current stats if dry_run for reporting
    if dry_run:
        current_stats = get_all_partition_stats()
        results["current_stats"] = {
            table: [
                {
                    "partition": p.partition_name,
                    "rows": p.row_count,
                    "size": p.total_size,
                }
                for p in partitions
            ]
            for table, partitions in current_stats.items()
        }

    for table in PARTITIONED_TABLES:
        table_results: dict[str, Any] = {
            "retention_days": PartitionRetention.get_retention_days(table),
            "created": [],
            "dropped": [],
            "skipped": [],
            "errors": [],
        }

        # Create future partitions
        if not dry_run:
            future_results = ensure_future_partitions(table, months_ahead)
            for result in future_results:
                _categorize_result(result, table_results, results["summary"])
        else:
            # Dry run: just report what would be created
            table_results["would_create"] = [
                f"{table}_{_get_month_suffix(i)}" for i in range(months_ahead + 1)
            ]

        # Drop old partitions
        if not dry_run:
            drop_results = drop_old_partitions(table)
            for result in drop_results:
                _categorize_result(result, table_results, results["summary"])
        else:
            # Dry run: would need to query to determine what would be dropped
            table_results["would_drop_older_than"] = f"{table_results['retention_days']} days"

        results["tables"][table] = table_results

    results["completed_at"] = datetime.now(UTC).isoformat()
    results["duration_ms"] = int((datetime.now(UTC) - started_at).total_seconds() * 1000)

    logger.info(
        f"Partition retention job complete: "
        f"created={results['summary']['partitions_created']}, "
        f"dropped={results['summary']['partitions_dropped']}, "
        f"errors={results['summary']['errors']}"
    )

    return results


def _categorize_result(
    result: PartitionResult,
    table_results: dict[str, Any],
    summary: dict[str, int],
) -> None:
    """Categorize a partition operation result."""
    if result.status == "created":
        table_results["created"].append(result.partition_name)
        summary["partitions_created"] += 1
    elif result.status == "dropped":
        table_results["dropped"].append(result.partition_name)
        summary["partitions_dropped"] += 1
    elif result.status == "already_exists":
        table_results["skipped"].append(result.partition_name)
        summary["partitions_skipped"] += 1
    elif result.status == "error":
        table_results["errors"].append(
            {"partition": result.partition_name, "message": result.message}
        )
        summary["errors"] += 1


def _get_month_suffix(months_from_now: int) -> str:
    """Get partition name suffix for a month offset from now."""
    now = datetime.now(UTC)
    year = now.year + (now.month + months_from_now - 1) // 12
    month = (now.month + months_from_now - 1) % 12 + 1
    return f"{year}_{month:02d}"


if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run partition retention job")
    parser.add_argument(
        "--months-ahead",
        type=int,
        default=3,
        help="Number of months ahead to create partitions (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done without making changes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    result = run_retention_job(
        months_ahead=args.months_ahead,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\nPartition Retention Job Results")
        print(f"{'=' * 40}")
        print(f"Started: {result['started_at']}")
        print(f"Duration: {result['duration_ms']}ms")
        print(f"Dry Run: {result['dry_run']}")
        print()
        print("Summary:")
        print(f"  Partitions created: {result['summary']['partitions_created']}")
        print(f"  Partitions dropped: {result['summary']['partitions_dropped']}")
        print(f"  Partitions skipped: {result['summary']['partitions_skipped']}")
        print(f"  Errors: {result['summary']['errors']}")
        print()
        for table, data in result["tables"].items():
            print(f"{table} (retention: {data['retention_days']} days):")
            if data.get("created"):
                print(f"  Created: {', '.join(data['created'])}")
            if data.get("dropped"):
                print(f"  Dropped: {', '.join(data['dropped'])}")
            if data.get("errors"):
                for err in data["errors"]:
                    print(f"  ERROR: {err['partition']}: {err['message']}")
