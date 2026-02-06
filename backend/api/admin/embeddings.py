"""Admin API endpoints for embedding visualization.

Provides:
- GET /api/admin/embeddings/stats - Embedding counts and storage estimates
- GET /api/admin/embeddings/sample - Sample embeddings with 2D coordinates
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.api.dependencies import get_redis_manager
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.services.embedding_visualizer import (
    compute_2d_coordinates,
    compute_clusters,
    generate_cluster_labels,
    get_distinct_categories,
    get_embedding_stats,
    get_sample_embeddings,
    get_total_embedding_count,
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
    cluster_id: int = Field(0, description="Cluster assignment (0 if clustering disabled)")


class ClusterInfo(BaseModel):
    """Information about a cluster of embeddings."""

    id: int = Field(..., description="Cluster ID (0-indexed)")
    label: str = Field(..., description="Human-readable cluster label")
    count: int = Field(..., description="Number of points in cluster")
    centroid: dict[str, float] = Field(..., description="Centroid coordinates {x, y}")


class CategoryCount(BaseModel):
    """Category with embedding count."""

    category: str = Field(..., description="Category name")
    count: int = Field(..., description="Number of embeddings")


class EmbeddingSampleResponse(BaseModel):
    """Response model for embedding sample with 2D coordinates."""

    points: list[EmbeddingPoint] = Field(..., description="Embedding points with 2D coords")
    method: str = Field(..., description="Reduction method used (pca/umap)")
    total_available: int = Field(..., description="Total embeddings in database")
    clusters: list[ClusterInfo] = Field(
        default_factory=list, description="Cluster info if clustering enabled"
    )


class CategoriesResponse(BaseModel):
    """Response model for research cache categories."""

    categories: list[CategoryCount] = Field(..., description="List of categories with counts")


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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get embedding stats")
async def get_stats(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> EmbeddingStatsResponse:
    """Get embedding storage statistics."""
    import asyncio

    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(None, get_embedding_stats)
    logger.info("Admin: Retrieved embedding statistics")
    return EmbeddingStatsResponse(**stats)


@router.get(
    "/embeddings/categories",
    response_model=CategoriesResponse,
    summary="Get research cache categories",
    description="Get distinct categories from research cache for filtering (admin only).",
    responses={
        200: {"description": "Categories retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get embedding categories")
async def get_categories(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> CategoriesResponse:
    """Get distinct research cache categories for filtering."""
    categories = get_distinct_categories()
    logger.info(f"Admin: Retrieved {len(categories)} embedding categories")
    return CategoriesResponse(categories=[CategoryCount(**c) for c in categories])


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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get embedding sample")
async def get_sample(
    request: Request,
    embedding_type: Literal["all", "contributions", "research", "context"] = Query(
        "all", description="Filter by embedding type"
    ),
    category: str | None = Query(None, description="Filter research embeddings by category"),
    limit: int = Query(500, ge=10, le=1000, description="Max samples to return"),
    method: Literal["pca", "umap"] = Query("pca", description="Dimensionality reduction method"),
    _admin: str = Depends(require_admin_any),
) -> EmbeddingSampleResponse:
    """Get sample embeddings with 2D coordinates for visualization."""
    import asyncio
    import json
    from collections import Counter

    # Check cache first (include category in cache key)
    cache_key = f"admin:embeddings:sample:{embedding_type}:{category or 'all'}:{limit}:{method}"
    redis_manager = get_redis_manager()
    redis = redis_manager.redis if redis_manager.is_available else None

    if redis:
        cached = redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            logger.info(f"Admin: Returning cached embedding sample ({len(data['points'])} points)")
            return EmbeddingSampleResponse(**data)

    # Run CPU-heavy work off the event loop
    def _compute() -> EmbeddingSampleResponse:
        total = get_total_embedding_count()
        samples = get_sample_embeddings(
            embedding_type=embedding_type, limit=limit, category=category
        )
        points = compute_2d_coordinates(samples, method=method)

        # Compute clusters if we have enough points
        clusters: list[ClusterInfo] = []
        if len(points) >= 20:
            coords = [(p["x"], p["y"]) for p in points]
            previews = [p["preview"] for p in points]
            cluster_assignments, centroids = compute_clusters(coords)
            cluster_labels = generate_cluster_labels(
                cluster_assignments, previews, centroids, coords
            )

            for i, p in enumerate(points):
                p["cluster_id"] = cluster_assignments[i]

            cluster_counts = Counter(cluster_assignments)
            for cluster_id in range(len(centroids)):
                cx, cy = centroids[cluster_id]
                clusters.append(
                    ClusterInfo(
                        id=cluster_id,
                        label=cluster_labels[cluster_id],
                        count=cluster_counts.get(cluster_id, 0),
                        centroid={"x": cx, "y": cy},
                    )
                )

        return EmbeddingSampleResponse(
            points=[EmbeddingPoint(**p) for p in points],
            method=method,
            total_available=total,
            clusters=clusters,
        )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, _compute)

    # Cache result
    if redis:
        redis.setex(cache_key, EMBEDDING_CACHE_TTL, json.dumps(response.model_dump()))

    logger.info(
        f"Admin: Retrieved embedding sample ({len(response.points)} points, method={method}, clusters={len(response.clusters)})"
    )
    return response
