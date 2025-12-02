"""Admin API endpoints for research cache management.

Provides:
- GET /api/admin/research-cache/stats - Get research cache statistics
- DELETE /api/admin/research-cache/{cache_id} - Delete cached research result
- GET /api/admin/research-cache/stale - Get stale research cache entries
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.admin.models import ResearchCacheStats, StaleEntriesResponse
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ControlResponse, ErrorResponse
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
async def get_research_cache_stats(
    _admin: str = Depends(require_admin_any),
) -> ResearchCacheStats:
    """Get research cache analytics and statistics.

    Returns cache hit rates, cost savings, and top cached questions.

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ResearchCacheStats with analytics

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from bo1.state.postgres_manager import get_research_cache_stats as get_stats

        stats = get_stats()

        logger.info("Admin: Retrieved research cache statistics")

        return ResearchCacheStats(**stats)

    except Exception as e:
        logger.error(f"Admin: Failed to get research cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get research cache stats: {str(e)}",
        ) from e


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
async def delete_research_cache_entry(
    cache_id: str,
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Delete a specific research cache entry.

    Args:
        cache_id: Research cache entry ID (UUID)
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with deletion confirmation

    Raises:
        HTTPException: If cache entry not found or deletion fails
    """
    try:
        from bo1.state.postgres_manager import delete_research_cache_entry as delete_entry

        deleted = delete_entry(cache_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Research cache entry not found: {cache_id}",
            )

        logger.info(f"Admin: Deleted research cache entry {cache_id}")

        return ControlResponse(
            session_id=cache_id,  # Using session_id field for cache_id
            action="delete_cache",
            status="success",
            message=f"Research cache entry deleted: {cache_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to delete research cache entry {cache_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete research cache entry: {str(e)}",
        ) from e


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
async def get_stale_research_cache_entries(
    days_old: int = Query(90, ge=1, le=365, description="Number of days to consider stale"),
    _admin: str = Depends(require_admin_any),
) -> StaleEntriesResponse:
    """Get research cache entries older than specified days.

    This endpoint helps admins identify stale cache entries that may need refreshing.

    Args:
        days_old: Number of days to consider stale (1-365, default: 90)
        _admin_key: Admin API key (injected by dependency)

    Returns:
        StaleEntriesResponse with list of stale entries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from bo1.state.postgres_manager import get_stale_research_cache_entries as get_stale

        entries = get_stale(days_old)

        logger.info(
            f"Admin: Retrieved {len(entries)} stale research cache entries (>{days_old} days)"
        )

        return StaleEntriesResponse(
            stale_count=len(entries),
            entries=entries,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to get stale research cache entries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stale research cache entries: {str(e)}",
        ) from e
