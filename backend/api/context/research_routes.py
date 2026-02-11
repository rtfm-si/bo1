"""FastAPI router for research-related context endpoints.

Provides:
- GET /api/v1/context/recent-research - Get recent research items
- GET /api/v1/context/research-embeddings - Get research embeddings for visualization
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from backend.api.context.models import (
    RecentResearchItem,
    RecentResearchResponse,
    ResearchCategory,
    ResearchEmbeddingsResponse,
    ResearchPoint,
    ResearchSource,
)
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTEXT_RATE_LIMIT, limiter
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.responses import ERROR_403_RESPONSE
from bo1.state.repositories import cache_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


@router.get(
    "/v1/context/recent-research",
    response_model=RecentResearchResponse,
    summary="Get recent research",
    description="Returns user's recent research items for dashboard widget display.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("get recent research")
async def get_recent_research(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum items to return"),
    user: dict[str, Any] = Depends(get_current_user),
) -> RecentResearchResponse:
    """Get user's recent research items for dashboard display."""
    user_id = extract_user_id(user)

    # Get recent research from cache
    research_entries = cache_repository.get_user_recent_research(user_id, limit=limit)

    if not research_entries:
        return RecentResearchResponse(
            success=True,
            research=[],
            total_count=0,
        )

    # Get total count
    total_count = cache_repository.get_user_research_total_count(user_id)

    # Transform to response model
    research_items = []
    for entry in research_entries:
        # Parse sources from JSON if present
        sources = []
        if entry.get("sources"):
            for src in entry["sources"]:
                if isinstance(src, dict):
                    sources.append(
                        ResearchSource(
                            url=src.get("url"),
                            title=src.get("title"),
                            snippet=src.get("snippet"),
                        )
                    )
                elif isinstance(src, str):
                    # Legacy format: just URLs
                    sources.append(ResearchSource(url=src))

        research_items.append(
            RecentResearchItem(
                id=entry["id"],
                question=entry.get("question", ""),
                summary=entry.get("answer_summary"),
                sources=sources,
                category=entry.get("category"),
                created_at=entry.get("created_at", ""),
            )
        )

    return RecentResearchResponse(
        success=True,
        research=research_items,
        total_count=total_count,
    )


# =============================================================================
# Research Embeddings Visualization
# =============================================================================


@router.get(
    "/v1/context/research-embeddings",
    response_model=ResearchEmbeddingsResponse,
    summary="Get research embeddings for visualization",
    description="Returns user's research topics as 2D coordinates for scatter plot visualization.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("get research embeddings")
async def get_research_embeddings(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> ResearchEmbeddingsResponse:
    """Get user's research embeddings reduced to 2D for visualization."""
    from backend.services.embedding_visualizer import reduce_dimensions

    user_id = extract_user_id(user)

    # Get user's research with embeddings (limit 100)
    research_entries = cache_repository.get_user_research_with_embeddings(user_id, limit=100)

    if not research_entries:
        # No research data - return empty response
        return ResearchEmbeddingsResponse(
            success=True,
            points=[],
            categories=[],
            total_count=0,
        )

    # Get category counts for legend
    category_counts = cache_repository.get_user_research_category_counts(user_id)
    categories = [ResearchCategory(name=c["name"], count=c["count"]) for c in category_counts]

    # Get total count (may exceed 100 limit)
    total_count = cache_repository.get_user_research_total_count(user_id)

    # Extract embeddings and reduce to 2D using PCA
    embeddings = [entry["embedding"] for entry in research_entries]
    coords = reduce_dimensions(embeddings, method="pca", n_components=2)

    # Build points with 2D coordinates
    points = []
    for entry, (x, y) in zip(research_entries, coords, strict=True):
        points.append(
            ResearchPoint(
                x=float(x),
                y=float(y),
                preview=entry["preview"] or "",
                category=entry["category"],
                created_at=entry["created_at"] or "",
            )
        )

    logger.info(f"Returned {len(points)} research embeddings for user {user_id}")

    return ResearchEmbeddingsResponse(
        success=True,
        points=points,
        categories=categories,
        total_count=total_count,
    )
