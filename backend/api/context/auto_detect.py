"""Auto-detection of competitors from business context.

Provides background task for automatically detecting competitors when user
saves sufficient business context (company_name, industry, or product_description).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

# Rate limit: 1 auto-detect per user per 24 hours
AUTO_DETECT_COOLDOWN_HOURS = 24

# Minimum competitors before auto-detect triggers
MIN_COMPETITORS_FOR_SKIP = 3


def _get_redis_key(user_id: str) -> str:
    """Get Redis key for auto-detect timestamp."""
    return f"autodetect:competitor:{user_id}"


def _can_auto_detect(user_id: str) -> bool:
    """Check if auto-detection is allowed (rate limiting).

    Args:
        user_id: User ID

    Returns:
        True if auto-detection is allowed (not rate limited)
    """
    try:
        from backend.api.dependencies import get_redis_manager

        redis_manager = get_redis_manager()
        redis_key = _get_redis_key(user_id)
        last_detect = redis_manager.get(redis_key)

        if last_detect is None:
            return True

        # Parse timestamp
        try:
            last_dt = datetime.fromisoformat(
                last_detect.decode() if isinstance(last_detect, bytes) else last_detect
            )
            cooldown = timedelta(hours=AUTO_DETECT_COOLDOWN_HOURS)
            return datetime.now(UTC) >= last_dt + cooldown
        except (ValueError, AttributeError):
            return True

    except Exception as e:
        logger.warning(f"Redis error checking auto-detect rate limit: {e}")
        # Allow on Redis error (fail open)
        return True


def _record_auto_detect(user_id: str) -> None:
    """Record that auto-detection was triggered for rate limiting.

    Args:
        user_id: User ID
    """
    try:
        from backend.api.dependencies import get_redis_manager

        redis_manager = get_redis_manager()
        redis_key = _get_redis_key(user_id)
        # Store timestamp with 25-hour TTL (slightly more than cooldown)
        redis_manager.setex(redis_key, 90000, datetime.now(UTC).isoformat())
    except Exception as e:
        logger.warning(f"Failed to record auto-detect timestamp: {e}")


def should_trigger_auto_detect(user_id: str, context: dict[str, Any]) -> bool:
    """Check if auto-detection should be triggered after context save.

    Trigger conditions:
    - User has company_name OR (industry AND product_description)
    - User has fewer than MIN_COMPETITORS_FOR_SKIP managed competitors
    - Not rate limited (24h cooldown)

    Args:
        user_id: User ID
        context: Saved context data

    Returns:
        True if auto-detection should be triggered
    """
    # Check if user has sufficient context
    company_name = context.get("company_name")
    industry = context.get("industry")
    product_description = context.get("product_description")

    has_sufficient_context = bool(company_name) or (bool(industry) and bool(product_description))

    if not has_sufficient_context:
        logger.debug(f"User {user_id}: insufficient context for auto-detect")
        return False

    # Check competitor count
    managed_competitors = context.get("managed_competitors", [])
    if len(managed_competitors) >= MIN_COMPETITORS_FOR_SKIP:
        logger.debug(
            f"User {user_id}: already has {len(managed_competitors)} competitors, skipping"
        )
        return False

    # Check rate limit
    if not _can_auto_detect(user_id):
        logger.debug(f"User {user_id}: rate limited for auto-detect")
        return False

    return True


async def run_auto_detect_competitors(user_id: str) -> None:
    """Run competitor auto-detection in background.

    This function should be called without blocking the main request.
    It handles its own error logging and won't raise exceptions.

    Args:
        user_id: User ID
    """
    from backend.api.context.competitors import detect_competitors_for_user

    try:
        logger.info(f"Starting auto-detect competitors for user {user_id}")

        # Record that we're attempting (for rate limiting)
        _record_auto_detect(user_id)

        # Run detection
        result = await detect_competitors_for_user(user_id)

        if result.success:
            logger.info(f"Auto-detected {len(result.competitors)} competitors for user {user_id}")
            # Mark auto-detect as completed in context
            _mark_auto_detect_complete(user_id, len(result.competitors))
        else:
            logger.warning(f"Auto-detect failed for user {user_id}: {result.error}")

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Auto-detect competitors failed: {e}",
            user_id=user_id,
        )


def _mark_auto_detect_complete(user_id: str, count: int) -> None:
    """Mark auto-detection as complete in user context.

    Args:
        user_id: User ID
        count: Number of competitors detected
    """
    try:
        context = user_repository.get_context(user_id) or {}
        context["last_competitor_auto_detect"] = {
            "completed_at": datetime.now(UTC).isoformat(),
            "count": count,
        }
        user_repository.save_context(user_id, context)
    except Exception as e:
        logger.warning(f"Failed to mark auto-detect complete: {e}")


def get_auto_detect_status(user_id: str) -> dict[str, Any]:
    """Get auto-detection status for a user.

    Args:
        user_id: User ID

    Returns:
        Dict with status info:
        - needs_competitor_refresh: True if auto-detect should run
        - last_auto_detect_at: ISO timestamp of last detection
        - competitor_count: Current managed competitor count
    """
    context = user_repository.get_context(user_id) or {}

    # Get managed competitor count
    managed = context.get("managed_competitors", [])
    competitor_count = len(managed) if isinstance(managed, list) else 0

    # Check if refresh needed
    needs_refresh = should_trigger_auto_detect(user_id, context)

    # Get last auto-detect timestamp
    last_detect = context.get("last_competitor_auto_detect", {})
    last_at = last_detect.get("completed_at") if isinstance(last_detect, dict) else None

    return {
        "needs_competitor_refresh": needs_refresh,
        "last_auto_detect_at": last_at,
        "competitor_count": competitor_count,
    }
