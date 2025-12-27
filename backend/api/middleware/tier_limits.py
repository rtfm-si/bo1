"""Tier-based usage limit enforcement middleware.

Provides FastAPI dependencies for enforcing tier limits on:
- Meeting creation (monthly limit)
- Dataset uploads (total limit)
- Mentor chats (daily limit)

Meeting creation has a promo credit fallback - if tier limit is exceeded,
users with promo credits can still create meetings.

Workspace tier resolution:
- If user is in an active workspace context (X-Workspace-ID header), workspace tier
  overrides personal tier when workspace has a paid subscription.
- Free tier members get workspace tier benefits when in workspace context.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.services.promotion_service import check_deliberation_allowance
from backend.services.usage_tracking import (
    UsageResult,
    check_limit,
    get_effective_tier,
    increment_usage,
)
from bo1.constants import UsageMetrics
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)

# Tier priority order (higher value = better tier)
TIER_PRIORITY = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "enterprise": 3,
}


@dataclass
class MeetingLimitResult:
    """Result of checking meeting limits with promo/credit fallback.

    Attributes:
        usage: The tier usage result
        uses_promo_credit: Whether this session will consume a promo credit
        promo_credits_remaining: Remaining promo credits after this session
        uses_meeting_credit: Whether this session will consume a prepaid meeting credit
        meeting_credits_remaining: Remaining meeting credits after this session
    """

    usage: UsageResult
    uses_promo_credit: bool = False
    promo_credits_remaining: int = 0
    uses_meeting_credit: bool = False
    meeting_credits_remaining: int = 0


class TierLimitError(HTTPException):
    """Exception raised when tier limit is exceeded."""

    def __init__(self, result: UsageResult, metric: str) -> None:
        """Initialize tier limit error.

        Args:
            result: Usage check result
            metric: Which metric hit the limit
        """
        detail = {
            "error": "tier_limit_exceeded",
            "metric": metric,
            "current": result.current,
            "limit": result.limit,
            "remaining": result.remaining,
            "reset_at": result.reset_at.isoformat() if result.reset_at else None,
            "upgrade_prompt": "Upgrade your plan to increase your limits.",
            "upgrade_url": "/settings/billing",
        }
        super().__init__(status_code=429, detail=detail)


def _get_workspace_tier(workspace_id_str: str | None, user_id: str) -> str | None:
    """Get workspace tier if user has access to workspace.

    Args:
        workspace_id_str: Workspace ID string from header
        user_id: User ID for access check

    Returns:
        Workspace tier or None if not applicable
    """
    if not workspace_id_str:
        return None

    try:
        from bo1.state.repositories.workspace_repository import workspace_repository

        workspace_id = uuid.UUID(workspace_id_str)

        # Check user is member of workspace
        if not workspace_repository.is_member(workspace_id, user_id):
            logger.debug(
                f"User {user_id} not member of workspace {workspace_id}, ignoring workspace tier"
            )
            return None

        # Get workspace tier
        tier = workspace_repository.get_workspace_tier(workspace_id)
        logger.debug(f"Workspace {workspace_id} tier: {tier}")
        return tier

    except (ValueError, Exception) as e:
        logger.warning(f"Failed to get workspace tier: {e}")
        return None


def _get_user_tier(user: dict[str, Any], request: Request | None = None) -> tuple[str, str]:
    """Extract user ID and effective tier from user dict.

    Considers workspace tier if X-Workspace-ID header is present.
    Uses the better tier between personal and workspace.

    Args:
        user: User data from auth middleware
        request: Optional request for workspace header

    Returns:
        Tuple of (user_id, effective_tier)
    """
    user_id = extract_user_id(user)
    base_tier = user.get("subscription_tier", "free")
    effective_tier = get_effective_tier(user_id, base_tier)

    # Check for workspace context
    if request:
        workspace_id_str = request.headers.get("X-Workspace-ID")
        workspace_tier = _get_workspace_tier(workspace_id_str, user_id)

        if workspace_tier:
            # Use the better tier between personal and workspace
            user_priority = TIER_PRIORITY.get(effective_tier, 0)
            workspace_priority = TIER_PRIORITY.get(workspace_tier, 0)

            if workspace_priority > user_priority:
                logger.debug(
                    f"User {user_id} using workspace tier {workspace_tier} "
                    f"(over personal tier {effective_tier})"
                )
                effective_tier = workspace_tier

    return user_id, effective_tier


def _get_meeting_credits(user_id: str) -> int:
    """Get user's prepaid meeting credits.

    Args:
        user_id: User identifier

    Returns:
        Number of meeting credits remaining
    """
    from bo1.state.database import db_session

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT meeting_credits FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                return row[0] if row else 0
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get meeting credits for user {user_id}",
            user_id=user_id,
            error=str(e),
        )
        return 0


def _decrement_meeting_credit(user_id: str) -> int:
    """Decrement user's meeting credits by 1.

    Args:
        user_id: User identifier

    Returns:
        New credits remaining
    """
    from bo1.state.database import db_session

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET meeting_credits = meeting_credits - 1
                    WHERE id = %s AND meeting_credits > 0
                    RETURNING meeting_credits
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                new_credits = row[0] if row else 0
                logger.info(
                    f"Decremented meeting credit for user {user_id}: {new_credits} remaining"
                )
                return new_credits
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to decrement meeting credit for user {user_id}",
            user_id=user_id,
            error=str(e),
        )
        return 0


async def require_meeting_limit(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> MeetingLimitResult:
    """Dependency that checks and enforces meeting creation limits.

    Should be added to POST /sessions endpoint.

    Fallback order:
    1. Tier subscription limit
    2. Prepaid meeting credits (from bundle purchases)
    3. Promo credits

    Considers workspace tier via X-Workspace-ID header.

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        MeetingLimitResult with usage info and credit status

    Raises:
        TierLimitError: If user has exceeded all allowances
    """
    user_id, tier = _get_user_tier(user, request)
    result = check_limit(user_id, UsageMetrics.MEETINGS_CREATED, tier)

    # Tier limit is fine - use tier allowance
    if result.allowed:
        return MeetingLimitResult(usage=result)

    # Tier limit exceeded - check prepaid meeting credits
    meeting_credits = _get_meeting_credits(user_id)
    if meeting_credits > 0:
        logger.info(
            f"User {user_id} tier limit exceeded but has {meeting_credits} "
            f"meeting credits - allowing session with meeting credit"
        )
        return MeetingLimitResult(
            usage=result,
            uses_meeting_credit=True,
            meeting_credits_remaining=meeting_credits - 1,  # Will consume 1
        )

    # Check promo credits as last fallback
    allowance = check_deliberation_allowance(user_id)
    if allowance.has_credits:
        logger.info(
            f"User {user_id} tier limit exceeded but has {allowance.total_remaining} "
            f"promo credits - allowing session with promo credit"
        )
        return MeetingLimitResult(
            usage=result,
            uses_promo_credit=True,
            promo_credits_remaining=allowance.total_remaining - 1,  # Will consume 1
        )

    # All limits exceeded
    logger.warning(
        f"Meeting limit exceeded: user={user_id} tier={tier} "
        f"current={result.current} limit={result.limit} meeting_credits=0 promo_credits=0"
    )
    raise TierLimitError(result, "meetings_monthly")


async def require_dataset_limit(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> UsageResult:
    """Dependency that checks and enforces dataset upload limits.

    Should be added to POST /datasets/upload endpoint.
    Considers workspace tier via X-Workspace-ID header.

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        UsageResult with current usage info

    Raises:
        TierLimitError: If user has exceeded their dataset limit
    """
    user_id, tier = _get_user_tier(user, request)
    result = check_limit(user_id, UsageMetrics.DATASETS_UPLOADED, tier)

    if not result.allowed:
        logger.warning(
            f"Dataset limit exceeded: user={user_id} tier={tier} "
            f"current={result.current} limit={result.limit}"
        )
        raise TierLimitError(result, "datasets_total")

    return result


async def require_mentor_limit(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> UsageResult:
    """Dependency that checks and enforces mentor chat limits.

    Should be added to POST /mentor/chat endpoint.
    Considers workspace tier via X-Workspace-ID header.

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        UsageResult with current usage info

    Raises:
        TierLimitError: If user has exceeded their mentor chat limit
    """
    user_id, tier = _get_user_tier(user, request)
    result = check_limit(user_id, UsageMetrics.MENTOR_CHATS, tier)

    if not result.allowed:
        logger.warning(
            f"Mentor limit exceeded: user={user_id} tier={tier} "
            f"current={result.current} limit={result.limit}"
        )
        raise TierLimitError(result, "mentor_daily")

    return result


def record_meeting_usage(user_id: str) -> int:
    """Record a meeting creation after successful session start.

    Call this after session is successfully created.

    Args:
        user_id: User identifier

    Returns:
        New usage count
    """
    return increment_usage(user_id, UsageMetrics.MEETINGS_CREATED)


def record_dataset_usage(user_id: str) -> int:
    """Record a dataset upload after successful upload.

    Call this after dataset is successfully uploaded.

    Args:
        user_id: User identifier

    Returns:
        New usage count
    """
    return increment_usage(user_id, UsageMetrics.DATASETS_UPLOADED)


def record_mentor_usage(user_id: str) -> int:
    """Record a mentor chat message after successful response.

    Call this after mentor response is generated.

    Args:
        user_id: User identifier

    Returns:
        New usage count
    """
    return increment_usage(user_id, UsageMetrics.MENTOR_CHATS)
