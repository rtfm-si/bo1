#!/usr/bin/env python3
"""Validate action_progress data against check constraints.

Checks that existing data in the actions table satisfies constraints
from the a2_add_action_progress migration:
- progress_value >= 0 (or NULL)
- progress_type IN ('percentage', 'points', 'status_only')
- If progress_type = 'percentage', progress_value must be 0-100

Usage:
    python -m backend.scripts.validate_action_progress
    python -m backend.scripts.validate_action_progress --verbose
    python -m backend.scripts.validate_action_progress --limit 100

Options:
    --verbose: Show sample violating rows
    --limit: Max violating rows to show (default: 10)
"""

import argparse
import logging
import sys

from bo1.state.database import db_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Valid progress types from migration
VALID_PROGRESS_TYPES = ("percentage", "points", "status_only")


def check_progress_value_negative() -> list[dict]:
    """Find rows where progress_value < 0."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, progress_value, progress_type, created_at
                    FROM actions
                    WHERE progress_value IS NOT NULL
                      AND progress_value < 0
                      AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row["id"],
                        "progress_value": row["progress_value"],
                        "progress_type": row["progress_type"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"Failed to check progress_value negative: {e}")
        return []


def check_progress_type_invalid() -> list[dict]:
    """Find rows where progress_type not in valid enum."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, progress_value, progress_type, created_at
                    FROM actions
                    WHERE progress_type IS NOT NULL
                      AND progress_type NOT IN ('percentage', 'points', 'status_only')
                      AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row["id"],
                        "progress_value": row["progress_value"],
                        "progress_type": row["progress_type"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"Failed to check progress_type invalid: {e}")
        return []


def check_percentage_out_of_range() -> list[dict]:
    """Find rows where progress_type='percentage' but value not in 0-100."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, progress_value, progress_type, created_at
                    FROM actions
                    WHERE progress_type = 'percentage'
                      AND progress_value IS NOT NULL
                      AND (progress_value < 0 OR progress_value > 100)
                      AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 100
                    """
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row["id"],
                        "progress_value": row["progress_value"],
                        "progress_type": row["progress_type"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"Failed to check percentage range: {e}")
        return []


def get_total_actions_count() -> int:
    """Get total count of non-deleted actions."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) as cnt
                    FROM actions
                    WHERE deleted_at IS NULL
                    """
                )
                row = cur.fetchone()
                return row["cnt"] if row else 0
    except Exception as e:
        logger.error(f"Failed to count actions: {e}")
        return 0


def check_constraints_exist() -> dict[str, bool]:
    """Check if check constraints exist in the database."""
    constraints = {
        "check_progress_value_valid": False,
        "check_progress_type_valid": False,
        "check_percentage_range": False,
    }
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT constraint_name
                    FROM information_schema.check_constraints
                    WHERE constraint_schema = 'public'
                      AND constraint_name IN (
                        'check_progress_value_valid',
                        'check_progress_type_valid',
                        'check_percentage_range'
                      )
                    """
                )
                for row in cur.fetchall():
                    constraints[row["constraint_name"]] = True
    except Exception as e:
        logger.error(f"Failed to check constraints: {e}")
    return constraints


def run_validation(verbose: bool = False, limit: int = 10) -> tuple[int, dict]:
    """Run all validation checks.

    Args:
        verbose: Show sample violating rows
        limit: Max rows to show when verbose

    Returns:
        Tuple of (total_violations, violations_by_type)
    """
    violations = {
        "negative_progress_value": check_progress_value_negative(),
        "invalid_progress_type": check_progress_type_invalid(),
        "percentage_out_of_range": check_percentage_out_of_range(),
    }

    total = sum(len(v) for v in violations.values())

    if verbose:
        for check_name, rows in violations.items():
            if rows:
                logger.info(f"\n{check_name} violations ({len(rows)} found):")
                for row in rows[:limit]:
                    logger.info(
                        f"  id={row['id']}, progress_value={row['progress_value']}, "
                        f"progress_type={row['progress_type']}"
                    )
                if len(rows) > limit:
                    logger.info(f"  ... and {len(rows) - limit} more")

    return total, {k: len(v) for k, v in violations.items()}


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate action_progress data against check constraints"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show sample violating rows",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max violating rows to show (default: 10)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ACTION PROGRESS DATA VALIDATION")
    logger.info("=" * 60)

    # Check total actions
    total_actions = get_total_actions_count()
    logger.info(f"Total actions in database: {total_actions}")

    # Check constraints exist
    logger.info("\nConstraint status:")
    constraints = check_constraints_exist()
    for name, exists in constraints.items():
        status = "✓ ACTIVE" if exists else "✗ MISSING"
        logger.info(f"  {name}: {status}")

    # Run validation
    logger.info("\nRunning validation checks...")
    total_violations, violation_counts = run_validation(
        verbose=args.verbose,
        limit=args.limit,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    for check_name, count in violation_counts.items():
        status = "✓" if count == 0 else "✗"
        logger.info(f"{status} {check_name}: {count} violations")
    logger.info("")
    logger.info(f"Total violations: {total_violations}")

    if total_violations > 0:
        logger.warning(
            "\nData violations found! Run data fix migration before applying check constraints."
        )
        return 1

    logger.info("\n✓ All data passes constraint validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
