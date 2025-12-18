"""Public blog endpoints (no auth required).

Provides:
- GET /api/v1/blog/posts - List published posts
- GET /api/v1/blog/posts/{slug} - Get post by slug
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.middleware.rate_limit import limiter
from backend.api.models import BlogPostListResponse, BlogPostResponse
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.blog_repository import blog_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/blog", tags=["blog"])


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
        raise HTTPException(
            status_code=404,
            detail={"error": "Not found", "message": f"Blog post '{slug}' not found"},
        )

    # Only return published posts
    if post.get("status") != "published":
        raise HTTPException(
            status_code=404,
            detail={"error": "Not found", "message": f"Blog post '{slug}' not found"},
        )

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})
