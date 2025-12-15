"""Admin API endpoints for embedding visualization.

Provides:
- GET /api/admin/embeddings/stats - Embedding counts and storage estimates
- GET /api/admin/embeddings/sample - Sample embeddings with 2D coordinates
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_redis_manager
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.services.embedding_visualizer import (
    compute_2d_coordinates,
    get_embedding_stats,
    get_sample_embeddings,
)
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Embeddings"])

# Cache TTL for reduced embeddings (5 minutes)
EMBEDDING_CACHE_TTL = 300


# ==============================================================================
# Response Models
# ==============================================================================


class EmbeddingStatsResponse(BaseModel):
    """Response model for embedding statistics."""

    total_embeddings: int = Field(..., description="Total embeddings stored")
    by_type: dict[str, int] = Field(..., description="Counts by embedding type")
    dimensions: int = Field(..., description="Embedding dimensions (e.g., 1024)")
    storage_estimate_mb: float = Field(..., description="Estimated storage in MB")
    umap_available: bool = Field(..., description="Whether UMAP is available")


class EmbeddingPoint(BaseModel):
    """A single embedding point with 2D coordinates."""

    x: float = Field(..., description="X coordinate (2D projection)")
    y: float = Field(..., description="Y coordinate (2D projection)")
    type: str = Field(..., description="Embedding type (contribution/research/context)")
    preview: str = Field(..., description="Text preview (first 100 chars)")
    metadata: dict[str, Any] = Field(..., description="Additional metadata")
    created_at: str = Field(..., description="When embedding was created")


class EmbeddingSampleResponse(BaseModel):
    """Response model for embedding sample with 2D coordinates."""

    points: list[EmbeddingPoint] = Field(..., description="Embedding points with 2D coords")
    method: str = Field(..., description="Reduction method used (pca/umap)")
    total_available: int = Field(..., description="Total embeddings in database")


# ==============================================================================
# Endpoints
# ==============================================================================


@router.get(
    "/embeddings/stats",
    response_model=EmbeddingStatsResponse,
    summary="Get embedding statistics",
    description="Get counts and storage estimates for stored embeddings (admin only).",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get embedding stats")
async def get_stats(
    _admin: str = Depends(require_admin_any),
) -> EmbeddingStatsResponse:
    """Get embedding storage statistics."""
    stats = get_embedding_stats()
    logger.info("Admin: Retrieved embedding statistics")
    return EmbeddingStatsResponse(**stats)


@router.get(
    "/embeddings/sample",
    response_model=EmbeddingSampleResponse,
    summary="Get embedding sample with 2D coordinates",
    description="Get sample embeddings reduced to 2D for visualization (admin only).",
    responses={
        200: {"description": "Sample retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get embedding sample")
async def get_sample(
    embedding_type: Literal["all", "contributions", "research", "context"] = Query(
        "all", description="Filter by embedding type"
    ),
    limit: int = Query(500, ge=10, le=1000, description="Max samples to return"),
    method: Literal["pca", "umap"] = Query("pca", description="Dimensionality reduction method"),
    _admin: str = Depends(require_admin_any),
) -> EmbeddingSampleResponse:
    """Get sample embeddings with 2D coordinates for visualization."""
    import json

    # Check cache first
    cache_key = f"admin:embeddings:sample:{embedding_type}:{limit}:{method}"
    redis_manager = get_redis_manager()
    redis = redis_manager.redis if redis_manager.is_available else None

    if redis:
        cached = redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            logger.info(f"Admin: Returning cached embedding sample ({len(data['points'])} points)")
            return EmbeddingSampleResponse(**data)

    # Get stats for total count
    stats = get_embedding_stats()

    # Get samples and compute 2D coordinates
    samples = get_sample_embeddings(embedding_type=embedding_type, limit=limit)
    points = compute_2d_coordinates(samples, method=method)

    response = EmbeddingSampleResponse(
        points=[EmbeddingPoint(**p) for p in points],
        method=method,
        total_available=stats["total_embeddings"],
    )

    # Cache result
    if redis:
        redis.setex(cache_key, EMBEDDING_CACHE_TTL, json.dumps(response.model_dump()))

    logger.info(f"Admin: Retrieved embedding sample ({len(points)} points, method={method})")
    return response
