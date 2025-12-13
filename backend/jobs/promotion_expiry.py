"""Daily promotion expiry job.

Expires user_promotions for promotions that have passed their expires_at date.
Designed to be run as a scheduled background job (APScheduler).
"""

import logging

from bo1.state.repositories.promotion_repository import promotion_repository

logger = logging.getLogger(__name__)


def run_promotion_expiry() -> dict[str, int]:
    """Expire all promotions past their expires_at date.

    Marks user_promotions status as 'expired' for promotions that have
    passed their expiration timestamp.

    Returns:
        Dict with 'expired_count' indicating number of user_promotions marked expired
    """
    logger.info("Starting promotion expiry job")

    try:
        expired_count = promotion_repository.expire_promotions()
        logger.info(f"Promotion expiry complete: {expired_count} user_promotions expired")

        return {"expired_count": expired_count}

    except Exception as e:
        logger.error(f"Promotion expiry job failed: {e}")
        raise
