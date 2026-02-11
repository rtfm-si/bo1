"""Public blog endpoints (no auth required).

Provides:
- GET /api/v1/blog/posts - List published posts
- GET /api/v1/blog/posts/{slug} - Get post by slug
- POST /api/v1/blog/posts/{slug}/view - Track page view
- POST /api/v1/blog/posts/{slug}/click - Track CTA click
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.middleware.rate_limit import limiter
from backend.api.models import BlogPostListResponse, BlogPostResponse
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.blog_repository import blog_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/blog", tags=["blog"])


def _blog_not_found(slug: str) -> HTTPException:
    return HTTPException(
        status_code=404, detail={"error": "Not found", "message": f"Blog post '{slug}' not found"}
    )


@router.get(
    "/posts",
    response_model=BlogPostListResponse,
    summary="List published blog posts",
    description="List all published blog posts. No authentication required.",
)
@limiter.limit("60/minute")
@handle_api_errors("list public blog posts")
async def list_published_posts(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> BlogPostListResponse:
    """List published blog posts for public consumption."""
    posts = blog_repository.list(status="published", limit=limit, offset=offset)
    total = blog_repository.count(status="published")

    return BlogPostListResponse(
        posts=[
            BlogPostResponse(id=str(p["id"]), **{k: v for k, v in p.items() if k != "id"})
            for p in posts
        ],
        total=total,
    )


@router.get(
    "/posts/{slug}",
    response_model=BlogPostResponse,
    summary="Get blog post by slug",
    description="Get a published blog post by its URL slug. Returns 404 if not found or not published.",
)
@limiter.limit("60/minute")
@handle_api_errors("get public blog post")
async def get_post_by_slug(
    request: Request,
    slug: str,
) -> BlogPostResponse:
    """Get a published blog post by slug."""
    post = blog_repository.get_by_slug(slug)

    if not post:
        raise _blog_not_found(slug)

    # Only return published posts
    if post.get("status") != "published":
        raise _blog_not_found(slug)

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})


@router.post(
    "/posts/{slug}/view",
    status_code=204,
    summary="Track blog post view",
    description="Increment view counter for a published blog post. Rate limited per IP.",
)
@limiter.limit("10/minute")  # Prevent gaming - max 10 views per minute per IP
@handle_api_errors("track blog view")
async def track_view(request: Request, slug: str) -> None:
    """Track a page view for analytics."""
    success = blog_repository.increment_view(slug)
    if not success:
        raise _blog_not_found(slug)


@router.post(
    "/posts/{slug}/click",
    status_code=204,
    summary="Track blog post CTA click",
    description="Increment click-through counter when user clicks CTA. Rate limited per IP.",
)
@limiter.limit("5/minute")  # Even stricter - max 5 clicks per minute per IP
@handle_api_errors("track blog click")
async def track_click(request: Request, slug: str) -> None:
    """Track a CTA click-through for analytics."""
    success = blog_repository.increment_click(slug)
    if not success:
        raise _blog_not_found(slug)
