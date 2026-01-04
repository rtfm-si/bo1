#!/usr/bin/env python3
"""Migrate historical insights from clarifications JSONB to business_metrics table.

Extracts metric data from user_context.clarifications and inserts into business_metrics
with source='clarification' for traceability.

Usage:
    python -m backend.scripts.migrate_insights_to_metrics --dry-run
    python -m backend.scripts.migrate_insights_to_metrics --execute
    python -m backend.scripts.migrate_insights_to_metrics --execute --max-age-days 30

Options:
    --dry-run: Show what would be done without making changes (default)
    --execute: Actually perform the migration
    --max-age-days: Only migrate insights newer than N days (default: 90)
    --force: Overwrite existing manual metrics (default: skip)
    --batch-size: Number of users to process per batch (default: 100)
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.api.context.services import (
    CATEGORY_TO_METRIC_KEY,
    DEFAULT_CONFIDENCE_THRESHOLD,
    METRIC_DISPLAY_NAMES,
    validate_clarification_entry,
)
from bo1.state.database import db_session
from bo1.state.repositories.metrics_repository import metrics_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class MigrationStats:
    """Track migration statistics."""

    def __init__(self) -> None:
        """Initialize migration statistics counters."""
        self.users_processed = 0
        self.insights_found = 0
        self.metrics_migrated = 0
        self.skipped_low_confidence = 0
        self.skipped_no_metric = 0
        self.skipped_unmappable = 0
        self.skipped_too_old = 0
        self.skipped_existing = 0
        self.errors = 0

    def to_dict(self) -> dict[str, int]:
        """Convert stats to dictionary for JSON output."""
        return {
            "users_processed": self.users_processed,
            "insights_found": self.insights_found,
            "metrics_migrated": self.metrics_migrated,
            "skipped_low_confidence": self.skipped_low_confidence,
            "skipped_no_metric": self.skipped_no_metric,
            "skipped_unmappable": self.skipped_unmappable,
            "skipped_too_old": self.skipped_too_old,
            "skipped_existing": self.skipped_existing,
            "errors": self.errors,
        }


def get_users_with_clarifications(
    batch_size: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Get users who have non-empty clarifications JSONB.

    Returns:
        List of dicts with user_id and clarifications
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, clarifications
                    FROM user_context
                    WHERE clarifications IS NOT NULL
                      AND clarifications != '{}'::jsonb
                      AND clarifications != 'null'::jsonb
                    ORDER BY user_id
                    LIMIT %s OFFSET %s
                    """,
                    (batch_size, offset),
                )
                rows = cur.fetchall()
                return [{"user_id": row[0], "clarifications": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Failed to query users with clarifications: {e}")
        return []


def extract_metrics_from_clarifications(
    clarifications: dict[str, Any],
    max_age_days: int = 90,
    stats: MigrationStats | None = None,
) -> list[dict[str, Any]]:
    """Extract business metrics from clarifications JSONB.

    Args:
        clarifications: Raw clarifications dict from user_context
        max_age_days: Skip insights older than this
        stats: Optional stats tracker

    Returns:
        List of business_metrics row dicts
    """
    if not clarifications or not isinstance(clarifications, dict):
        return []

    cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
    metrics: list[dict[str, Any]] = []

    for question, entry_data in clarifications.items():
        if stats:
            stats.insights_found += 1

        try:
            # Validate entry
            entry = validate_clarification_entry(question, entry_data)

            # Check category is mappable
            category = entry.category
            if not category:
                if stats:
                    stats.skipped_unmappable += 1
                continue

            # Convert enum to string for lookup
            from backend.api.context.models import InsightCategory as CategoryEnum

            category_str = category.value if isinstance(category, CategoryEnum) else str(category)
            if category_str not in CATEGORY_TO_METRIC_KEY:
                if stats:
                    stats.skipped_unmappable += 1
                continue

            metric_key = CATEGORY_TO_METRIC_KEY[category_str]
            if metric_key is None:
                if stats:
                    stats.skipped_unmappable += 1
                continue

            # Check confidence threshold
            confidence = entry.confidence_score or 0.0
            if confidence < DEFAULT_CONFIDENCE_THRESHOLD:
                if stats:
                    stats.skipped_low_confidence += 1
                continue

            # Check metric data exists - handle both dict and model
            metric_data = entry.metric
            if not metric_data:
                if stats:
                    stats.skipped_no_metric += 1
                continue

            # Extract value from either dict or model
            if isinstance(metric_data, dict):
                value = metric_data.get("value")
            else:
                value = getattr(metric_data, "value", None)
            if value is None:
                if stats:
                    stats.skipped_no_metric += 1
                continue

            # Parse captured_at - handle both datetime and string
            captured_at = None
            parsed_at = entry.parsed_at
            answered_at = entry.answered_at

            if parsed_at:
                if isinstance(parsed_at, datetime):
                    captured_at = parsed_at
                elif isinstance(parsed_at, str):
                    try:
                        captured_at = datetime.fromisoformat(parsed_at.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

            if not captured_at and answered_at:
                if isinstance(answered_at, datetime):
                    captured_at = answered_at
                elif isinstance(answered_at, str):
                    try:
                        captured_at = datetime.fromisoformat(answered_at.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

            if not captured_at:
                captured_at = datetime.now(UTC)

            # Check age
            if captured_at < cutoff_date:
                if stats:
                    stats.skipped_too_old += 1
                continue

            # Build metric row - get unit from dict or model
            if isinstance(metric_data, dict):
                unit = metric_data.get("unit")
            else:
                unit = getattr(metric_data, "unit", None)
            name = METRIC_DISPLAY_NAMES.get(metric_key, metric_key.replace("_", " ").title())

            # Convert value to float
            try:
                numeric_value = float(value) if isinstance(value, (int, float, str)) else None
            except (ValueError, TypeError):
                numeric_value = None

            if numeric_value is None:
                if stats:
                    stats.skipped_no_metric += 1
                continue

            metrics.append(
                {
                    "metric_key": metric_key,
                    "name": name,
                    "value": numeric_value,
                    "value_unit": unit,
                    "captured_at": captured_at,
                    "source": "clarification",
                    "is_predefined": False,
                    "source_question": question,
                    "confidence": confidence,
                }
            )

        except Exception as e:
            logger.warning(f"Failed to process clarification '{question[:50]}': {e}")
            if stats:
                stats.errors += 1
            continue

    return metrics


def migrate_user_metrics(
    user_id: str,
    metrics: list[dict[str, Any]],
    force: bool = False,
    dry_run: bool = True,
    stats: MigrationStats | None = None,
) -> int:
    """Migrate metrics for a single user.

    Args:
        user_id: User identifier
        metrics: List of metric dicts to upsert
        force: Overwrite existing manual metrics
        dry_run: If True, don't actually save
        stats: Optional stats tracker

    Returns:
        Number of metrics migrated
    """
    migrated = 0

    for metric_data in metrics:
        metric_key = metric_data["metric_key"]

        # Check if metric already exists
        if not force:
            existing = metrics_repository.get_user_metric(user_id, metric_key)
            if existing and existing.get("source") == "manual":
                logger.debug(f"Skipping {metric_key} for {user_id}: manual value exists")
                if stats:
                    stats.skipped_existing += 1
                continue

        if dry_run:
            logger.info(
                f"[DRY-RUN] Would migrate {metric_key}={metric_data['value']} "
                f"for user {user_id[:8]}..."
            )
            migrated += 1
            continue

        try:
            metrics_repository.save_metric(
                user_id=user_id,
                metric_key=metric_key,
                value=metric_data["value"],
                name=metric_data["name"],
                value_unit=metric_data.get("value_unit"),
                source="clarification",
                is_predefined=False,
            )
            migrated += 1
            logger.debug(f"Migrated {metric_key}={metric_data['value']} for user {user_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to save metric {metric_key} for {user_id}: {e}")
            if stats:
                stats.errors += 1

    return migrated


def run_migration(
    batch_size: int = 100,
    max_age_days: int = 90,
    force: bool = False,
    dry_run: bool = True,
) -> MigrationStats:
    """Run the migration process.

    Args:
        batch_size: Number of users per batch
        max_age_days: Skip insights older than this
        force: Overwrite existing manual metrics
        dry_run: If True, don't make changes

    Returns:
        Migration statistics
    """
    stats = MigrationStats()
    offset = 0

    while True:
        users = get_users_with_clarifications(batch_size, offset)
        if not users:
            break

        logger.info(f"Processing batch of {len(users)} users (offset {offset})")

        for user_data in users:
            user_id = user_data["user_id"]
            clarifications = user_data["clarifications"]

            stats.users_processed += 1

            # Extract metrics
            metrics = extract_metrics_from_clarifications(
                clarifications,
                max_age_days=max_age_days,
                stats=stats,
            )

            if not metrics:
                continue

            # Migrate
            migrated = migrate_user_metrics(
                user_id=user_id,
                metrics=metrics,
                force=force,
                dry_run=dry_run,
                stats=stats,
            )
            stats.metrics_migrated += migrated

        offset += batch_size

        # In dry-run, only process first batch to show sample
        if dry_run and offset > 0:
            logger.info("[DRY-RUN] Stopping after first batch. Run with --execute to process all.")
            break

    return stats


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate historical insights to business_metrics table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be done without making changes (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the migration",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Only migrate insights newer than N days (default: 90)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing manual metrics (default: skip)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of users to process per batch (default: 100)",
    )

    args = parser.parse_args()

    # --execute overrides --dry-run
    dry_run = not args.execute

    logger.info("=" * 60)
    logger.info("INSIGHT TO METRICS MIGRATION")
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY RUN MODE - no changes will be made")
    else:
        logger.warning("EXECUTE MODE - changes will be saved to database")

    logger.info(f"Max age: {args.max_age_days} days")
    logger.info(f"Force overwrite: {args.force}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("")

    stats = run_migration(
        batch_size=args.batch_size,
        max_age_days=args.max_age_days,
        force=args.force,
        dry_run=dry_run,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Users processed: {stats.users_processed}")
    logger.info(f"Insights found: {stats.insights_found}")
    logger.info(f"Metrics migrated: {stats.metrics_migrated}")
    logger.info(f"Skipped (low confidence): {stats.skipped_low_confidence}")
    logger.info(f"Skipped (no metric data): {stats.skipped_no_metric}")
    logger.info(f"Skipped (unmappable category): {stats.skipped_unmappable}")
    logger.info(f"Skipped (too old): {stats.skipped_too_old}")
    logger.info(f"Skipped (existing manual): {stats.skipped_existing}")
    logger.info(f"Errors: {stats.errors}")

    # Output JSON for scripting
    print("\n--- JSON REPORT ---")
    print(json.dumps(stats.to_dict(), indent=2))

    if stats.errors > 0:
        logger.warning("Some entries could not be processed. Check logs for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
