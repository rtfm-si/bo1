"""Admin API endpoints for metrics management.

Provides:
- GET /api/admin/metrics - Get system metrics
- POST /api/admin/metrics/reset - Reset all metrics
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.api.metrics import metrics
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ControlResponse, ErrorResponse
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Metrics"])


@router.get(
    "/metrics",
    summary="Get system metrics",
    description="""
    Get all system metrics including API endpoint performance, LLM usage, and cache hit rates.

    Returns:
    - Counters: Success/error counts for API endpoints and LLM calls
    - Histograms: Latency distributions, token usage, costs

    Metrics reset on server restart.
    """,
    responses={
        200: {"description": "Metrics retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_metrics(
    _admin: str = Depends(require_admin_any),
) -> dict[str, Any]:
    """Get all system metrics (admin only).

    Returns counters and histogram statistics for:
    - API endpoint calls (success/error rates, latency)
    - LLM API calls (cache hits, token usage, costs)
    - Database queries (if instrumented)
    - Cache operations (hit rates)

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        Dict with counters and histograms

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        return metrics.get_stats()
    except Exception as e:
        logger.error(f"Admin: Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}",
        ) from e


@router.post(
    "/metrics/reset",
    summary="Reset all metrics",
    description="""
    Reset all metrics to zero.

    Use this to clear metrics after deployment or for debugging.
    Metrics automatically reset on server restart.
    """,
    responses={
        200: {"description": "Metrics reset successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def reset_metrics(
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Reset all metrics to zero (admin only).

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with reset confirmation

    Raises:
        HTTPException: If metrics reset fails
    """
    try:
        metrics.reset()
        logger.info("Admin: Reset all metrics")

        return ControlResponse(
            session_id="",  # Not session-specific
            action="reset_metrics",
            status="success",
            message="All metrics reset successfully",
        )
    except Exception as e:
        logger.error(f"Admin: Failed to reset metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset metrics: {str(e)}",
        ) from e
