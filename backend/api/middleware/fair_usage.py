"""Fair Usage Middleware for LLM cost-heavy endpoints.

Provides dependency functions for FastAPI endpoints to check
fair usage limits before allowing expensive operations.
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from backend.api.middleware.auth import get_current_user
from backend.services.fair_usage import (
    FairUsageService,
    UsageCheckResult,
    UsageStatus,
    get_fair_usage_service,
)
from bo1.llm.context import set_cost_context

logger = logging.getLogger(__name__)


async def _check_fair_usage_impl(
    user: dict,
    feature: str,
    estimated_cost: float = 0.0,
    allow_soft_warning: bool = True,
) -> UsageCheckResult:
    """Internal implementation for fair usage check.

    Args:
        user: Current user dict (from get_current_user)
        feature: Feature name (mentor_chat, dataset_qa, competitor_analysis, meeting)
        estimated_cost: Estimated cost of the operation
        allow_soft_warning: If False, treat soft warnings as blocked

    Returns:
        UsageCheckResult

    Raises:
        HTTPException: 429 if hard blocked or soft warning when not allowed
    """
    user_id = user.get("user_id", "")
    tier = user.get("tier", "free")

    service = get_fair_usage_service()
    result = service.check_fair_usage(
        user_id=user_id,
        feature=feature,
        tier=tier,
        estimated_cost=estimated_cost,
    )

    # Set feature context for cost tracking
    set_cost_context(user_id=user_id, feature=feature)

    if result.status == UsageStatus.HARD_BLOCKED:
        logger.warning(
            f"Fair usage hard block: user={user_id} feature={feature} "
            f"cost={result.current_cost:.4f} limit={result.daily_limit:.2f}"
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error_code": "FAIR_USAGE_LIMIT_EXCEEDED",
                "message": result.message or "Daily usage limit exceeded",
                "current_cost": result.current_cost,
                "daily_limit": result.daily_limit,
                "percent_used": result.percent_used,
            },
        )

    if result.status == UsageStatus.SOFT_WARNING and not allow_soft_warning:
        logger.info(
            f"Fair usage soft warning (blocked): user={user_id} feature={feature} "
            f"cost={result.current_cost:.4f} limit={result.daily_limit:.2f}"
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error_code": "FAIR_USAGE_LIMIT_WARNING",
                "message": result.message or "Approaching daily usage limit",
                "current_cost": result.current_cost,
                "daily_limit": result.daily_limit,
                "percent_used": result.percent_used,
            },
        )

    if result.status == UsageStatus.SOFT_WARNING:
        logger.info(
            f"Fair usage soft warning: user={user_id} feature={feature} "
            f"cost={result.current_cost:.4f} ({result.percent_used:.0%} of limit)"
        )

    return result


def require_fair_usage(feature: str, estimated_cost: float = 0.0):
    """Create a dependency that checks fair usage for a feature.

    Usage:
        @router.post("/chat")
        async def chat(
            _usage: UsageCheckResult = Depends(require_fair_usage("mentor_chat"))
        ):
            ...

    Args:
        feature: Feature name (mentor_chat, dataset_qa, competitor_analysis, meeting)
        estimated_cost: Estimated cost of the operation

    Returns:
        FastAPI dependency that returns UsageCheckResult
    """

    async def dependency(
        user: Annotated[dict, Depends(get_current_user)],
    ) -> UsageCheckResult:
        return await _check_fair_usage_impl(
            user=user,
            feature=feature,
            estimated_cost=estimated_cost,
            allow_soft_warning=True,
        )

    return dependency


def require_fair_usage_strict(feature: str, estimated_cost: float = 0.0):
    """Create a dependency that blocks at soft warning threshold.

    Same as require_fair_usage but blocks at 80% instead of 100%.

    Args:
        feature: Feature name
        estimated_cost: Estimated cost of the operation

    Returns:
        FastAPI dependency that returns UsageCheckResult
    """

    async def dependency(
        user: Annotated[dict, Depends(get_current_user)],
    ) -> UsageCheckResult:
        return await _check_fair_usage_impl(
            user=user,
            feature=feature,
            estimated_cost=estimated_cost,
            allow_soft_warning=False,
        )

    return dependency


async def get_usage_status_header(result: UsageCheckResult) -> dict[str, str]:
    """Get HTTP headers to include fair usage status in response.

    Useful for frontend to show usage meter without extra API call.

    Args:
        result: UsageCheckResult from fair usage check

    Returns:
        Dict of headers to add to response
    """
    if result.daily_limit < 0:
        # Unlimited - no headers needed
        return {}

    return {
        "X-Fair-Usage-Status": result.status.value,
        "X-Fair-Usage-Percent": f"{result.percent_used:.2f}",
        "X-Fair-Usage-Remaining": f"{result.remaining:.4f}",
    }
