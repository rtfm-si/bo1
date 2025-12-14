#!/usr/bin/env python3
"""Backfill personal workspaces for existing users.

Creates a personal workspace for users who don't have one, and sets it
as their default workspace.

Usage:
    python -m backend.scripts.backfill_workspaces
    python -m backend.scripts.backfill_workspaces --dry-run
    python -m backend.scripts.backfill_workspaces --batch-size 50

Options:
    --dry-run: Show what would be done without making changes
    --batch-size: Number of users to process per batch (default: 100)
"""

import argparse
import logging
import sys

from bo1.state.database import db_session
from bo1.state.repositories.user_repository import user_repository
from bo1.state.repositories.workspace_repository import workspace_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def get_users_without_workspaces(batch_size: int = 100) -> list[dict]:
    """Get users who don't belong to any workspace.

    Returns:
        List of user dicts with id and email
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.email
                    FROM users u
                    LEFT JOIN workspace_members wm ON u.id = wm.user_id
                    WHERE wm.id IS NULL
                      AND u.deleted_at IS NULL
                    ORDER BY u.created_at
                    LIMIT %s
                    """,
                    (batch_size,),
                )
                rows = cur.fetchall()
                return [{"id": row[0], "email": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Failed to query users without workspaces: {e}")
        return []


def backfill_user_workspace(user_id: str, email: str, dry_run: bool = False) -> bool:
    """Create personal workspace for a user.

    Args:
        user_id: User identifier
        email: User email (for logging)
        dry_run: If True, don't actually create anything

    Returns:
        True if workspace was created (or would be in dry-run)
    """
    masked_email = email[:3] + "***@" + email.split("@")[1] if "@" in email else email

    if dry_run:
        logger.info(f"[DRY-RUN] Would create workspace for user {user_id} ({masked_email})")
        return True

    try:
        # Create personal workspace
        workspace = workspace_repository.create_workspace(
            name="Personal Workspace",
            owner_id=user_id,
        )

        # Set as default
        user_repository.set_default_workspace(user_id, workspace.id)

        logger.info(
            f"Created personal workspace for user {user_id} ({masked_email}): {workspace.id}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to create workspace for user {user_id}: {e}")
        return False


def run_backfill(batch_size: int = 100, dry_run: bool = False) -> tuple[int, int]:
    """Run the backfill process.

    Args:
        batch_size: Number of users to process per batch
        dry_run: If True, don't make changes

    Returns:
        Tuple of (success_count, failure_count)
    """
    total_success = 0
    total_failure = 0

    while True:
        users = get_users_without_workspaces(batch_size)
        if not users:
            logger.info("No more users without workspaces")
            break

        logger.info(f"Processing batch of {len(users)} users")

        for user in users:
            if backfill_user_workspace(user["id"], user["email"], dry_run):
                total_success += 1
            else:
                total_failure += 1

        # If dry-run, don't loop (we'd get same users)
        if dry_run:
            break

    return total_success, total_failure


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backfill personal workspaces for existing users")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of users to process per batch (default: 100)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("WORKSPACE BACKFILL")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be made")

    success, failure = run_backfill(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Workspaces created: {success}")
    logger.info(f"Failures: {failure}")

    if failure > 0:
        logger.warning("Some users could not be processed. Check logs for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
