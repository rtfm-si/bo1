"""Admin API endpoints for metrics management.

Provides:
- GET /api/admin/metrics - Get system metrics
- POST /api/admin/metrics/reset - Reset all metrics
"""

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.metrics import metrics
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.errors import handle_api_errors
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
@handle_api_errors("get metrics")
async def get_metrics(
    _admin: str = Depends(require_admin_any),
) -> dict[str, Any]:
    """Get all system metrics (admin only)."""
    return metrics.get_stats()


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
@handle_api_errors("reset metrics")
async def reset_metrics(
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Reset all metrics to zero (admin only)."""
    metrics.reset()
    logger.info("Admin: Reset all metrics")

    return ControlResponse(
        session_id="",
        action="reset_metrics",
        status="success",
        message="All metrics reset successfully",
    )
