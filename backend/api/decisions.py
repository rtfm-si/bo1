"""Public decisions endpoints (no auth required).

Provides:
- GET /api/v1/decisions - List published decisions (all or by category)
- GET /api/v1/decisions/categories - Get categories with counts
- GET /api/v1/decisions/{category}/{slug} - Get decision by category and slug
- POST /api/v1/decisions/{category}/{slug}/view - Track page view
- POST /api/v1/decisions/{category}/{slug}/click - Track CTA click
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.middleware.rate_limit import limiter
from backend.api.models import (
    DECISION_CATEGORIES,
    CategoriesResponse,
    CategoryWithCount,
    DecisionListResponse,
    DecisionPublicResponse,
    DecisionResponse,
)
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.decision_repository import decision_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/decisions", tags=["decisions"])


def _decision_to_public_response(d: dict[str, Any]) -> DecisionPublicResponse:
    """Convert decision dict to public response (no admin fields)."""
    return DecisionPublicResponse(
        category=d["category"],
        slug=d["slug"],
        title=d["title"],
        meta_description=d.get("meta_description"),
        founder_context=d.get("founder_context"),
        expert_perspectives=d.get("expert_perspectives"),
        synthesis=d.get("synthesis"),
        faqs=d.get("faqs"),
        published_at=d.get("published_at"),
    )


def _decision_to_list_response(d: dict[str, Any]) -> DecisionResponse:
    """Convert decision dict to list response."""
    return DecisionResponse(
        id=str(d["id"]),
        session_id=str(d["session_id"]) if d.get("session_id") else None,
        category=d["category"],
        slug=d["slug"],
        title=d["title"],
        meta_description=d.get("meta_description"),
        founder_context=d.get("founder_context"),
        expert_perspectives=d.get("expert_perspectives"),
        synthesis=d.get("synthesis"),
        faqs=d.get("faqs"),
        related_decision_ids=d.get("related_decision_ids"),
        status=d.get("status", "published"),
        published_at=d.get("published_at"),
        created_at=d["created_at"] if "created_at" in d else d.get("published_at"),
        updated_at=d["updated_at"] if "updated_at" in d else d.get("published_at"),
        view_count=d.get("view_count", 0),
        click_through_count=d.get("click_through_count", 0),
    )


@router.get(
    "",
    response_model=DecisionListResponse,
    summary="List published decisions",
    description="List all published decisions. No authentication required.",
)
@limiter.limit("60/minute")
@handle_api_errors("list public decisions")
async def list_published_decisions(
    request: Request,
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> DecisionListResponse:
    """List published decisions for public consumption."""
    if category:
        decisions = decision_repository.list_published_by_category(category)
        # Apply pagination manually since list_published_by_category doesn't support it
        total = len(decisions)
        decisions = decisions[offset : offset + limit]
    else:
        decisions = decision_repository.list_all_published()
        total = len(decisions)
        decisions = decisions[offset : offset + limit]

    return DecisionListResponse(
        decisions=[_decision_to_list_response(d) for d in decisions],
        total=total,
    )


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    summary="Get decision categories",
    description="Get list of categories with published decision counts.",
)
@limiter.limit("60/minute")
@handle_api_errors("get decision categories")
async def get_categories(request: Request) -> CategoriesResponse:
    """Get categories with published counts."""
    categories = decision_repository.get_categories_with_counts()

    # Include all categories, even with 0 count
    category_counts = {c["category"]: c["count"] for c in categories}
    all_categories = [
        CategoryWithCount(category=cat, count=category_counts.get(cat, 0))
        for cat in DECISION_CATEGORIES
    ]

    return CategoriesResponse(categories=all_categories)


@router.get(
    "/{category}/{slug}",
    response_model=DecisionPublicResponse,
    summary="Get decision by category and slug",
    description="Get a published decision by its category and URL slug.",
)
@limiter.limit("60/minute")
@handle_api_errors("get public decision")
async def get_decision_by_slug(
    request: Request,
    category: str,
    slug: str,
) -> DecisionPublicResponse:
    """Get a published decision by category and slug."""
    decision = decision_repository.get_by_category_slug(category, slug)

    if not decision:
        raise HTTPException(
            status_code=404,
            detail={"error": "Not found", "message": f"Decision '{category}/{slug}' not found"},
        )

    return _decision_to_public_response(decision)


@router.post(
    "/{category}/{slug}/view",
    status_code=204,
    summary="Track decision page view",
    description="Increment view counter for a published decision. Rate limited per IP.",
)
@limiter.limit("10/minute")
@handle_api_errors("track decision view")
async def track_view(request: Request, category: str, slug: str) -> None:
    """Track a page view for analytics."""
    success = decision_repository.increment_view(slug)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": "Not found", "message": f"Decision '{category}/{slug}' not found"},
        )


@router.post(
    "/{category}/{slug}/click",
    status_code=204,
    summary="Track decision CTA click",
    description="Increment click-through counter when user clicks CTA. Rate limited per IP.",
)
@limiter.limit("5/minute")
@handle_api_errors("track decision click")
async def track_click(request: Request, category: str, slug: str) -> None:
    """Track a CTA click-through for analytics."""
    success = decision_repository.increment_click(slug)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"error": "Not found", "message": f"Decision '{category}/{slug}' not found"},
        )


@router.get(
    "/{category}/{slug}/related",
    summary="Get related decisions",
    description="Get related published decisions for a decision page.",
)
@limiter.limit("60/minute")
@handle_api_errors("get related decisions")
async def get_related_decisions(
    request: Request,
    category: str,
    slug: str,
    limit: int = Query(5, ge=1, le=10, description="Max results"),
) -> DecisionListResponse:
    """Get related decisions for cross-linking."""
    decision = decision_repository.get_by_category_slug(category, slug)

    if not decision:
        raise HTTPException(
            status_code=404,
            detail={"error": "Not found", "message": f"Decision '{category}/{slug}' not found"},
        )

    related = decision_repository.get_related(decision["id"], limit=limit)

    return DecisionListResponse(
        decisions=[_decision_to_list_response(d) for d in related],
        total=len(related),
    )
