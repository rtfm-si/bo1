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
    """Result of checking meeting limits with promo fallback.

    Attributes:
        usage: The tier usage result
        uses_promo_credit: Whether this session will consume a promo credit
        promo_credits_remaining: Remaining promo credits after this session
    """

    usage: UsageResult
    uses_promo_credit: bool = False
    promo_credits_remaining: int = 0


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


async def require_meeting_limit(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> MeetingLimitResult:
    """Dependency that checks and enforces meeting creation limits.

    Should be added to POST /sessions endpoint.

    If tier limit is exceeded, checks for promo credits as fallback.
    Sets uses_promo_credit=True if falling back to promo credit.

    Considers workspace tier via X-Workspace-ID header.

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        MeetingLimitResult with usage info and promo credit status

    Raises:
        TierLimitError: If user has exceeded both tier limit and promo credits
    """
    user_id, tier = _get_user_tier(user, request)
    result = check_limit(user_id, UsageMetrics.MEETINGS_CREATED, tier)

    # Tier limit is fine - use tier allowance
    if result.allowed:
        return MeetingLimitResult(usage=result)

    # Tier limit exceeded - check promo credits as fallback
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

    # Both tier and promo limits exceeded
    logger.warning(
        f"Meeting limit exceeded: user={user_id} tier={tier} "
        f"current={result.current} limit={result.limit} promo_credits=0"
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
