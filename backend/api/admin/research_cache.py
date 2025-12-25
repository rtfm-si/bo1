"""Admin API endpoints for research cache management.

Provides:
- GET /api/admin/research-cache/stats - Get research cache statistics
- GET /api/admin/research-cache/metrics - Get detailed cache metrics with threshold recommendation
- DELETE /api/admin/research-cache/{cache_id} - Delete cached research result
- GET /api/admin/research-cache/stale - Get stale research cache entries
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.admin.models import CacheMetricsResponse, ResearchCacheStats, StaleEntriesResponse
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.errors import handle_api_errors
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Research Cache"])


@router.get(
    "/research-cache/stats",
    response_model=ResearchCacheStats,
    summary="Get research cache statistics",
    description="Get analytics and statistics for the research cache (admin only).",
    responses={
        200: {"description": "Cache statistics retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get research cache stats")
async def get_research_cache_stats(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> ResearchCacheStats:
    """Get research cache analytics and statistics."""
    from bo1.state.repositories import cache_repository

    stats = cache_repository.get_stats()
    logger.info("Admin: Retrieved research cache statistics")
    return ResearchCacheStats(**stats)


@router.get(
    "/research-cache/metrics",
    response_model=CacheMetricsResponse,
    summary="Get detailed cache metrics with threshold recommendation",
    description="Get multi-period hit rates, miss distribution, and similarity threshold recommendation.",
    responses={
        200: {"description": "Cache metrics retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get research cache metrics")
async def get_research_cache_metrics(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> CacheMetricsResponse:
    """Get detailed cache metrics including threshold recommendation."""
    from backend.services.cache_threshold_analyzer import get_full_cache_metrics

    metrics = get_full_cache_metrics()
    logger.info(
        f"Admin: Retrieved cache metrics - hit_rate_30d={metrics['hit_rate_30d']:.1f}%, "
        f"recommended_threshold={metrics['recommended_threshold']}"
    )
    return CacheMetricsResponse(**metrics)


@router.delete(
    "/research-cache/{cache_id}",
    response_model=ControlResponse,
    summary="Delete cached research result",
    description="Delete a specific research cache entry by ID (admin only).",
    responses={
        200: {"description": "Cache entry deleted successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        404: {"description": "Cache entry not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete research cache entry")
async def delete_research_cache_entry(
    request: Request,
    cache_id: str,
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Delete a specific research cache entry."""
    from bo1.state.repositories import cache_repository

    deleted = cache_repository.delete(cache_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Research cache entry not found: {cache_id}",
        )

    logger.info(f"Admin: Deleted research cache entry {cache_id}")

    return ControlResponse(
        session_id=cache_id,
        action="delete_cache",
        status="success",
        message=f"Research cache entry deleted: {cache_id}",
    )


@router.get(
    "/research-cache/stale",
    response_model=StaleEntriesResponse,
    summary="Get stale research cache entries",
    description="Get research cache entries older than specified days (admin only).",
    responses={
        200: {"description": "Stale entries retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get stale research cache entries")
async def get_stale_research_cache_entries(
    request: Request,
    days_old: int = Query(90, ge=1, le=365, description="Number of days to consider stale"),
    _admin: str = Depends(require_admin_any),
) -> StaleEntriesResponse:
    """Get research cache entries older than specified days."""
    from bo1.state.repositories import cache_repository

    entries = cache_repository.get_stale(days_old)
    logger.info(f"Admin: Retrieved {len(entries)} stale research cache entries (>{days_old} days)")

    return StaleEntriesResponse(
        stale_count=len(entries),
        entries=entries,
    )
