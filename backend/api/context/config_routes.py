"""Context configuration endpoints.

Provides:
- GET /v1/context/key-metrics - Get key metrics
- PUT /v1/context/key-metrics/config - Update key metrics config
- GET /v1/context/working-pattern - Get working pattern
- PUT /v1/context/working-pattern - Update working pattern
- GET /v1/context/heatmap-depth - Get heatmap history depth
- PUT /v1/context/heatmap-depth - Update heatmap history depth
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from backend.api.context.models import (
    HeatmapHistoryDepth,
    HeatmapHistoryDepthResponse,
    HeatmapHistoryDepthUpdate,
    KeyMetricConfigUpdate,
    KeyMetricDisplay,
    KeyMetricsResponse,
    WorkingPattern,
    WorkingPatternResponse,
    WorkingPatternUpdate,
)
from backend.api.context.services import get_key_metrics_for_user
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTEXT_RATE_LIMIT, limiter
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


# =============================================================================
# Key Metrics
# =============================================================================


@router.get(
    "/v1/context/key-metrics",
    response_model=KeyMetricsResponse,
    summary="Get key metrics",
    description="Returns user's prioritized key metrics with current values and trends.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("get key metrics")
async def get_key_metrics(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> KeyMetricsResponse:
    """Get user's key metrics with values and trends."""
    user_id = extract_user_id(user)

    # Get context and key metrics config
    context_data = user_repository.get_context(user_id)
    key_metrics_config = None
    if context_data:
        key_metrics_config = context_data.get("key_metrics_config")

    # Build metrics list
    metrics = get_key_metrics_for_user(context_data, key_metrics_config)

    # Count by importance
    now_count = sum(1 for m in metrics if m.get("importance") == "now")
    later_count = sum(1 for m in metrics if m.get("importance") == "later")
    monitor_count = sum(1 for m in metrics if m.get("importance") == "monitor")

    return KeyMetricsResponse(
        success=True,
        metrics=[KeyMetricDisplay(**m) for m in metrics],
        now_count=now_count,
        later_count=later_count,
        monitor_count=monitor_count,
    )


@router.put(
    "/v1/context/key-metrics/config",
    response_model=KeyMetricsResponse,
    summary="Update key metrics config",
    description="Update user's key metrics prioritization and configuration.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("update key metrics config")
async def update_key_metrics_config(
    request: Request,
    body: KeyMetricConfigUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> KeyMetricsResponse:
    """Update key metrics configuration."""
    user_id = extract_user_id(user)

    # Convert to storable format
    config_list = [m.model_dump() for m in body.metrics]

    # Save config
    user_repository.save_context(user_id, {"key_metrics_config": config_list})

    # Re-fetch and return updated metrics
    context_data = user_repository.get_context(user_id)
    metrics = get_key_metrics_for_user(context_data, config_list)

    now_count = sum(1 for m in metrics if m.get("importance") == "now")
    later_count = sum(1 for m in metrics if m.get("importance") == "later")
    monitor_count = sum(1 for m in metrics if m.get("importance") == "monitor")

    return KeyMetricsResponse(
        success=True,
        metrics=[KeyMetricDisplay(**m) for m in metrics],
        now_count=now_count,
        later_count=later_count,
        monitor_count=monitor_count,
    )


# =============================================================================
# Working Pattern (Activity Heatmap)
# =============================================================================


@router.get(
    "/v1/context/working-pattern",
    response_model=WorkingPatternResponse,
    summary="Get working pattern",
    description="Returns user's working days pattern for activity visualization. Defaults to Mon-Fri.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("get working pattern")
async def get_working_pattern(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkingPatternResponse:
    """Get user's working pattern (defaults to Mon-Fri)."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    working_pattern_data = context_data.get("working_pattern") if context_data else None

    if working_pattern_data and isinstance(working_pattern_data, dict):
        pattern = WorkingPattern(**working_pattern_data)
    else:
        pattern = WorkingPattern()  # Default Mon-Fri

    return WorkingPatternResponse(success=True, pattern=pattern)


@router.put(
    "/v1/context/working-pattern",
    response_model=WorkingPatternResponse,
    summary="Update working pattern",
    description="Update user's working days pattern. Used to grey out non-working days in ActivityHeatmap.",
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("update working pattern")
async def update_working_pattern(
    request: Request,
    body: WorkingPatternUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkingPatternResponse:
    """Update user's working pattern."""
    user_id = extract_user_id(user)

    # Validate days are in range 1-7
    invalid_days = [d for d in body.working_days if d < 1 or d > 7]
    if invalid_days:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid days: {invalid_days}. Days must be 1 (Mon) through 7 (Sun).",
            status=422,
        )

    # Build pattern (sorts and deduplicates)
    pattern = WorkingPattern(working_days=body.working_days)

    # Save to context
    user_repository.save_context(
        user_id, {"working_pattern": {"working_days": pattern.working_days}}
    )

    logger.info(f"Updated working pattern for user {user_id}: {pattern.working_days}")

    return WorkingPatternResponse(success=True, pattern=pattern)


# =============================================================================
# Heatmap History Depth (Activity Heatmap)
# =============================================================================


@router.get(
    "/v1/context/heatmap-depth",
    response_model=HeatmapHistoryDepthResponse,
    summary="Get heatmap history depth",
    description="Returns user's preferred activity heatmap history depth. Defaults to 3 months.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("get heatmap depth")
async def get_heatmap_depth(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> HeatmapHistoryDepthResponse:
    """Get user's heatmap history depth (defaults to 3 months)."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    history_months = context_data.get("heatmap_history_months") if context_data else None

    if history_months in (1, 3, 6):
        depth = HeatmapHistoryDepth(history_months=history_months)
    else:
        depth = HeatmapHistoryDepth()  # Default 3 months

    return HeatmapHistoryDepthResponse(success=True, depth=depth)


@router.put(
    "/v1/context/heatmap-depth",
    response_model=HeatmapHistoryDepthResponse,
    summary="Update heatmap history depth",
    description="Update user's preferred activity heatmap history depth (1, 3, or 6 months).",
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("update heatmap depth")
async def update_heatmap_depth(
    request: Request,
    body: HeatmapHistoryDepthUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> HeatmapHistoryDepthResponse:
    """Update user's heatmap history depth."""
    user_id = extract_user_id(user)

    # Save to context
    user_repository.save_context(user_id, {"heatmap_history_months": body.history_months})

    logger.info(f"Updated heatmap depth for user {user_id}: {body.history_months} months")

    depth = HeatmapHistoryDepth(history_months=body.history_months)
    return HeatmapHistoryDepthResponse(success=True, depth=depth)
