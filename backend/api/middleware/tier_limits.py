"""Tier-based usage limit enforcement middleware.

Provides FastAPI dependencies for enforcing tier limits on:
- Meeting creation (monthly limit)
- Dataset uploads (total limit)
- Mentor chats (daily limit)
"""

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.services.usage_tracking import (
    UsageResult,
    check_limit,
    get_effective_tier,
    increment_usage,
)
from bo1.constants import UsageMetrics

logger = logging.getLogger(__name__)


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
        }
        super().__init__(status_code=429, detail=detail)


def _get_user_tier(user: dict[str, Any]) -> tuple[str, str]:
    """Extract user ID and effective tier from user dict.

    Args:
        user: User data from auth middleware

    Returns:
        Tuple of (user_id, effective_tier)
    """
    user_id = extract_user_id(user)
    base_tier = user.get("subscription_tier", "free")
    effective_tier = get_effective_tier(user_id, base_tier)
    return user_id, effective_tier


async def require_meeting_limit(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> UsageResult:
    """Dependency that checks and enforces meeting creation limits.

    Should be added to POST /sessions endpoint.

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        UsageResult with current usage info

    Raises:
        TierLimitError: If user has exceeded their meeting limit
    """
    user_id, tier = _get_user_tier(user)
    result = check_limit(user_id, UsageMetrics.MEETINGS_CREATED, tier)

    if not result.allowed:
        logger.warning(
            f"Meeting limit exceeded: user={user_id} tier={tier} "
            f"current={result.current} limit={result.limit}"
        )
        raise TierLimitError(result, "meetings_monthly")

    return result


async def require_dataset_limit(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> UsageResult:
    """Dependency that checks and enforces dataset upload limits.

    Should be added to POST /datasets/upload endpoint.

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        UsageResult with current usage info

    Raises:
        TierLimitError: If user has exceeded their dataset limit
    """
    user_id, tier = _get_user_tier(user)
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

    Args:
        request: FastAPI request
        user: Authenticated user

    Returns:
        UsageResult with current usage info

    Raises:
        TierLimitError: If user has exceeded their mentor chat limit
    """
    user_id, tier = _get_user_tier(user)
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
