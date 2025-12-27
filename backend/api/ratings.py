"""User ratings API endpoints (thumbs up/down feedback).

Provides:
- POST /api/v1/ratings - Submit rating for meeting or action
- GET /api/v1/ratings/{entity_type}/{entity_id} - Get user's rating for entity
- GET /api/v1/admin/ratings/metrics - Aggregated metrics (admin only)
- GET /api/v1/admin/ratings/negative - Recent negative ratings (admin only)
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import (
    ErrorResponse,
    NegativeRatingItem,
    NegativeRatingsResponse,
    RatingCreate,
    RatingMetrics,
    RatingResponse,
    RatingTrendItem,
)
from backend.api.utils.errors import handle_api_errors
from bo1.security import sanitize_for_prompt
from bo1.state.repositories.ratings_repository import ratings_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/ratings", tags=["ratings"])
admin_router = APIRouter(prefix="/v1/admin/ratings", tags=["admin"])


@router.post(
    "",
    response_model=RatingResponse,
    summary="Submit rating",
    description="Submit a thumbs up (+1) or thumbs down (-1) rating for a meeting or action.",
    responses={
        200: {"description": "Rating submitted successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
    },
)
@handle_api_errors("submit rating")
async def submit_rating(
    body: RatingCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> RatingResponse:
    """Submit a rating for a meeting or action.

    Upserts: if user already rated this entity, updates the rating.
    """
    user_id = user["user_id"]

    # Sanitize optional comment
    safe_comment = sanitize_for_prompt(body.comment) if body.comment else None

    rating = ratings_repository.upsert_rating(
        user_id=user_id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        rating=body.rating,
        comment=safe_comment,
    )

    logger.info(
        f"Rating submitted: user={user_id} entity={body.entity_type}/{body.entity_id} rating={body.rating}"
    )

    return RatingResponse(**rating)


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=RatingResponse | None,
    summary="Get user's rating",
    description="Get the current user's rating for a specific entity.",
    responses={
        200: {"description": "Rating found (or null if not rated)"},
        400: {"description": "Invalid entity_type", "model": ErrorResponse},
    },
)
@handle_api_errors("get rating")
async def get_rating(
    entity_type: str,
    entity_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> RatingResponse | None:
    """Get the current user's rating for an entity."""
    if entity_type not in ("meeting", "action"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid entity_type", "message": "Must be 'meeting' or 'action'"},
        )

    user_id = user["user_id"]
    rating = ratings_repository.get_user_rating(user_id, entity_type, entity_id)

    if not rating:
        return None

    return RatingResponse(**rating)


# ============================================================================
# Admin endpoints
# ============================================================================


@admin_router.get(
    "/metrics",
    response_model=RatingMetrics,
    summary="Get rating metrics",
    description="Get aggregated rating metrics (admin only).",
    responses={
        200: {"description": "Metrics returned successfully"},
        403: {"description": "Not authorized", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get rating metrics")
async def get_rating_metrics(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    _admin: dict[str, Any] = Depends(require_admin_any),
) -> RatingMetrics:
    """Get aggregated rating metrics for admin dashboard."""
    metrics = ratings_repository.get_metrics(days=days)
    return RatingMetrics(**metrics)


@admin_router.get(
    "/trend",
    response_model=list[RatingTrendItem],
    summary="Get rating trend",
    description="Get daily rating trend data (admin only).",
    responses={
        200: {"description": "Trend data returned successfully"},
        403: {"description": "Not authorized", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get rating trend")
async def get_rating_trend(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="Period in days"),
    _admin: dict[str, Any] = Depends(require_admin_any),
) -> list[RatingTrendItem]:
    """Get daily rating trend for admin dashboard."""
    trend = ratings_repository.get_trend(days=days)
    return [RatingTrendItem(**item) for item in trend]


@admin_router.get(
    "/negative",
    response_model=NegativeRatingsResponse,
    summary="Get negative ratings",
    description="Get recent thumbs-down ratings for triage (admin only).",
    responses={
        200: {"description": "Negative ratings returned successfully"},
        403: {"description": "Not authorized", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get negative ratings")
async def get_negative_ratings(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Max items to return"),
    _admin: dict[str, Any] = Depends(require_admin_any),
) -> NegativeRatingsResponse:
    """Get recent negative ratings for admin triage."""
    items = ratings_repository.get_recent_negative(limit=limit)
    return NegativeRatingsResponse(items=[NegativeRatingItem(**item) for item in items])
