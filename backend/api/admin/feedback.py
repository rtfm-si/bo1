"""Admin API endpoints for feedback management.

Provides:
- GET /api/admin/feedback - List all feedback with filters
- GET /api/admin/feedback/stats - Get feedback statistics
- GET /api/admin/feedback/analysis-summary - Get sentiment/theme aggregation
- GET /api/admin/feedback/by-theme/{theme} - List feedback by theme
- GET /api/admin/feedback/{id} - Get single feedback item
- PATCH /api/admin/feedback/{id} - Update feedback status
"""

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import (
    ErrorResponse,
    FeedbackAnalysisSummary,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStats,
    FeedbackStatus,
    FeedbackStatusUpdate,
    FeedbackType,
    ThemeCount,
)
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging import ErrorCode
from bo1.state.repositories.feedback_repository import feedback_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["Admin - Feedback"])


@router.get(
    "",
    response_model=FeedbackListResponse,
    summary="List all feedback",
    description="List all feedback submissions with optional filters.",
    responses={
        200: {"description": "Feedback list retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list feedback")
async def list_feedback(
    request: Request,
    _admin: str = Depends(require_admin_any),
    type: str | None = Query(None, description="Filter by type (feature_request, problem_report)"),
    status: str | None = Query(
        None, description="Filter by status (new, reviewing, resolved, closed)"
    ),
    sentiment: str | None = Query(
        None, description="Filter by sentiment (positive, negative, neutral, mixed)"
    ),
    theme: str | None = Query(
        None, description="Filter by theme tag (e.g., usability, performance)"
    ),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
) -> FeedbackListResponse:
    """List all feedback (admin view)."""
    # Validate type filter
    if type and type not in {FeedbackType.FEATURE_REQUEST, FeedbackType.PROBLEM_REPORT}:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid type filter. Must be one of: feature_request, problem_report",
            status=400,
        )

    # Validate status filter
    if status and status not in {
        FeedbackStatus.NEW,
        FeedbackStatus.REVIEWING,
        FeedbackStatus.RESOLVED,
        FeedbackStatus.CLOSED,
    }:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid status filter. Must be one of: new, reviewing, resolved, closed",
            status=400,
        )

    # Validate sentiment filter
    if sentiment and sentiment not in {"positive", "negative", "neutral", "mixed"}:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid sentiment filter. Must be one of: positive, negative, neutral, mixed",
            status=400,
        )

    items = feedback_repository.list_feedback(
        feedback_type=type,
        status=status,
        sentiment=sentiment,
        theme=theme,
        limit=limit,
        offset=offset,
    )
    total = feedback_repository.count_feedback(
        feedback_type=type, status=status, sentiment=sentiment, theme=theme
    )

    logger.info(f"Admin: Listed {len(items)} feedback items (total={total})")

    return FeedbackListResponse(
        items=[FeedbackResponse(**item) for item in items],
        total=total,
    )


@router.get(
    "/stats",
    response_model=FeedbackStats,
    summary="Get feedback statistics",
    description="Get counts of feedback by type and status.",
    responses={
        200: {"description": "Stats retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feedback stats")
async def get_feedback_stats(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> FeedbackStats:
    """Get feedback statistics."""
    stats = feedback_repository.get_stats()
    logger.info(f"Admin: Retrieved feedback stats (total={stats['total']})")
    return FeedbackStats(**stats)


@router.get(
    "/analysis-summary",
    response_model=FeedbackAnalysisSummary,
    summary="Get feedback analysis summary",
    description="Get aggregated sentiment distribution and top themes.",
    responses={
        200: {"description": "Analysis summary retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feedback analysis summary")
async def get_feedback_analysis_summary(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> FeedbackAnalysisSummary:
    """Get aggregated feedback analysis (sentiment + themes)."""
    summary = feedback_repository.get_analysis_summary()
    logger.info(f"Admin: Retrieved analysis summary (analyzed={summary['analyzed_count']})")
    return FeedbackAnalysisSummary(
        analyzed_count=summary["analyzed_count"],
        sentiment_counts=summary["sentiment_counts"],
        top_themes=[ThemeCount(**t) for t in summary["top_themes"]],
    )


@router.get(
    "/by-theme/{theme}",
    response_model=FeedbackListResponse,
    summary="Get feedback by theme",
    description="List feedback items that mention a specific theme.",
    responses={
        200: {"description": "Feedback list retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feedback by theme")
async def get_feedback_by_theme(
    request: Request,
    theme: str = Path(..., description="Theme tag to filter by"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    _admin: str = Depends(require_admin_any),
) -> FeedbackListResponse:
    """Get feedback items that mention a specific theme."""
    items = feedback_repository.get_feedback_by_theme(theme, limit=limit)
    logger.info(f"Admin: Retrieved {len(items)} feedback items for theme '{theme}'")
    return FeedbackListResponse(
        items=[FeedbackResponse(**item) for item in items],
        total=len(items),
    )


@router.get(
    "/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Get feedback item",
    description="Get a single feedback item by ID.",
    responses={
        200: {"description": "Feedback retrieved successfully"},
        404: {"description": "Feedback not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feedback")
async def get_feedback(
    request: Request,
    feedback_id: str,
    _admin: str = Depends(require_admin_any),
) -> FeedbackResponse:
    """Get a single feedback item."""
    item = feedback_repository.get_feedback_by_id(feedback_id)
    if not item:
        raise http_error(ErrorCode.API_NOT_FOUND, "Feedback not found", status=404)

    return FeedbackResponse(**item)


@router.patch(
    "/{feedback_id}",
    response_model=FeedbackResponse,
    summary="Update feedback status",
    description="Update the status of a feedback item.",
    responses={
        200: {"description": "Status updated successfully"},
        404: {"description": "Feedback not found", "model": ErrorResponse},
        400: {"description": "Invalid status", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update feedback status")
async def update_feedback_status(
    request: Request,
    feedback_id: str,
    body: FeedbackStatusUpdate,
    _admin: str = Depends(require_admin_any),
) -> FeedbackResponse:
    """Update feedback status."""
    # Verify exists
    existing = feedback_repository.get_feedback_by_id(feedback_id)
    if not existing:
        raise http_error(ErrorCode.API_NOT_FOUND, "Feedback not found", status=404)

    updated = feedback_repository.update_status(feedback_id, body.status)
    if not updated:
        raise http_error(ErrorCode.API_NOT_FOUND, "Feedback not found", status=404)

    logger.info(
        f"Admin: Updated feedback {feedback_id} status to {body.status} (was {existing['status']})"
    )

    return FeedbackResponse(**updated)
