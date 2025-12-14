"""Blog publishing scheduler job.

Publishes scheduled blog posts when their publication time is reached.
Designed to run hourly via cron/scheduler.
"""

import logging

from bo1.state.repositories.blog_repository import blog_repository

logger = logging.getLogger(__name__)


def publish_scheduled_posts() -> dict[str, int]:
    """Publish scheduled posts that have reached their publication time.

    Finds posts with status='scheduled' and published_at <= now,
    then updates them to status='published'.

    Returns:
        Dict with counts: {"published": N, "errors": N}
    """
    stats = {"published": 0, "errors": 0}

    logger.info("Running blog publisher job")

    try:
        # Get posts ready for publishing
        posts = blog_repository.get_scheduled_for_publish()

        if not posts:
            logger.info("No scheduled posts ready for publishing")
            return stats

        logger.info(f"Found {len(posts)} posts ready for publishing")

        for post in posts:
            try:
                result = blog_repository.publish(post["id"])
                if result:
                    stats["published"] += 1
                    logger.info(f"Published: '{post['title']}' (id={post['id']})")
                else:
                    stats["errors"] += 1
                    logger.error(f"Failed to publish post {post['id']}")
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Error publishing post {post['id']}: {e}")

        logger.info(
            f"Blog publisher complete: {stats['published']} published, {stats['errors']} errors"
        )

    except Exception as e:
        logger.error(f"Blog publisher job failed: {e}")
        raise

    return stats


async def async_publish_scheduled_posts() -> dict[str, int]:
    """Async wrapper for publish_scheduled_posts.

    For use with async job schedulers.
    """
    return publish_scheduled_posts()


# CLI entry point
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Publish scheduled blog posts")
    parser.add_argument("--dry-run", action="store_true", help="List posts without publishing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if args.dry_run:
        posts = blog_repository.get_scheduled_for_publish()
        if posts:
            print(f"\n{len(posts)} posts ready for publishing:")
            for p in posts:
                print(f"  - [{p['id']}] {p['title']} (scheduled: {p['published_at']})")
        else:
            print("No posts ready for publishing")
        sys.exit(0)

    stats = publish_scheduled_posts()
    print(f"\nPublished: {stats['published']}, Errors: {stats['errors']}")
    sys.exit(0 if stats["errors"] == 0 else 1)
