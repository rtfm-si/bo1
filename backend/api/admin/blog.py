"""Admin API endpoints for blog post management.

Provides:
- GET /api/admin/blog/posts - List posts with filters
- POST /api/admin/blog/posts - Create draft post
- GET /api/admin/blog/posts/{id} - Get post by ID
- PATCH /api/admin/blog/posts/{id} - Update post
- DELETE /api/admin/blog/posts/{id} - Delete post
- POST /api/admin/blog/generate - AI generate post
- GET /api/admin/blog/topics - Discover topics
"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import (
    BlogGenerateRequest,
    BlogGenerateResponse,
    BlogPostCreate,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostUpdate,
    ErrorResponse,
    TopicProposalResponse,
    TopicProposalsResponse,
    TopicResponse,
    TopicsResponse,
)
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.content_generator import generate_blog_post
from backend.services.topic_discovery import (
    TopicDiscoveryError,
    discover_topics,
    filter_topics,
    propose_topics,
)
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories.blog_repository import blog_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/blog", tags=["Admin - Blog"])


@router.get(
    "/posts",
    response_model=BlogPostListResponse,
    summary="List blog posts",
    description="List all blog posts with optional status filter.",
    responses={
        200: {"description": "Posts retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list blog posts")
async def list_posts(
    request: Request,
    status: str | None = Query(None, description="Filter by status: draft, scheduled, published"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _admin: str = Depends(require_admin_any),
) -> BlogPostListResponse:
    """List blog posts with optional filters."""
    posts = blog_repository.list(status=status, limit=limit, offset=offset)
    total = blog_repository.count(status=status)

    logger.info(f"Admin: Listed {len(posts)} blog posts (status={status})")

    return BlogPostListResponse(
        posts=[
            BlogPostResponse(id=str(p["id"]), **{k: v for k, v in p.items() if k != "id"})
            for p in posts
        ],
        total=total,
    )


@router.post(
    "/posts",
    response_model=BlogPostResponse,
    summary="Create blog post",
    description="Create a new blog post (defaults to draft status).",
    responses={
        200: {"description": "Post created successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create blog post")
async def create_post(
    request: Request,
    body: BlogPostCreate,
    admin_id: str = Depends(require_admin_any),
) -> BlogPostResponse:
    """Create a new blog post."""
    post = blog_repository.create(
        title=body.title,
        content=body.content,
        excerpt=body.excerpt,
        status=body.status,
        published_at=body.published_at,
        seo_keywords=body.seo_keywords,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        author_id=admin_id,
    )

    logger.info(f"Admin: Created blog post '{body.title}' (id={post['id']})")

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})


@router.get(
    "/posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Get blog post",
    description="Get a blog post by ID.",
    responses={
        200: {"description": "Post retrieved successfully"},
        404: {"description": "Post not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get blog post")
async def get_post(
    request: Request,
    post_id: str,
    _admin: str = Depends(require_admin_any),
) -> BlogPostResponse:
    """Get a blog post by ID."""
    post = blog_repository.get_by_id(post_id)

    if not post:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Blog post {post_id} not found", status=404)

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})


@router.patch(
    "/posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Update blog post",
    description="Update blog post fields.",
    responses={
        200: {"description": "Post updated successfully"},
        404: {"description": "Post not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update blog post")
async def update_post(
    request: Request,
    post_id: str,
    body: BlogPostUpdate,
    _admin: str = Depends(require_admin_any),
) -> BlogPostResponse:
    """Update a blog post."""
    # Build update kwargs (only non-None fields)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    post = blog_repository.update(post_id, **updates)

    if not post:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Blog post {post_id} not found", status=404)

    logger.info(f"Admin: Updated blog post {post_id} (fields: {list(updates.keys())})")

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})


@router.delete(
    "/posts/{post_id}",
    summary="Delete blog post",
    description="Delete a blog post (hard delete).",
    responses={
        200: {"description": "Post deleted successfully"},
        404: {"description": "Post not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete blog post")
async def delete_post(
    request: Request,
    post_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Delete a blog post."""
    deleted = blog_repository.delete(post_id)

    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Blog post {post_id} not found", status=404)

    logger.info(f"Admin: Deleted blog post {post_id}")

    return {"success": True, "message": f"Blog post {post_id} deleted"}


@router.post(
    "/generate",
    response_model=BlogGenerateResponse,
    summary="Generate blog post",
    description="Use AI to generate a blog post from a topic.",
    responses={
        200: {"description": "Post generated successfully"},
        400: {"description": "Generation failed", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("generate blog post")
async def generate_post(
    request: Request,
    body: BlogGenerateRequest,
    save_draft: bool = Query(True, description="Save as draft post"),
    admin_id: str = Depends(require_admin_any),
) -> BlogGenerateResponse:
    """Generate a blog post using AI."""
    content = await generate_blog_post(
        topic=body.topic,
        keywords=body.keywords,
    )

    post_id = None
    if save_draft:
        post = blog_repository.create(
            title=content.title,
            content=content.content,
            excerpt=content.excerpt,
            status="draft",
            seo_keywords=body.keywords,
            generated_by_topic=body.topic,
            meta_title=content.meta_title,
            meta_description=content.meta_description,
            author_id=admin_id,
        )
        post_id = str(post["id"])
        logger.info(f"Admin: Generated and saved blog post '{content.title}' (id={post_id})")
    else:
        logger.info(f"Admin: Generated blog post '{content.title}' (not saved)")

    return BlogGenerateResponse(
        title=content.title,
        excerpt=content.excerpt,
        content=content.content,
        meta_title=content.meta_title,
        meta_description=content.meta_description,
        post_id=post_id,
    )


@router.get(
    "/topics",
    response_model=TopicsResponse,
    summary="Discover topics",
    description="Discover relevant blog topics using AI.",
    responses={
        200: {"description": "Topics discovered successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
        500: {"description": "Topic discovery failed", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("discover topics")
async def discover_blog_topics(
    request: Request,
    industry: str | None = Query(None, description="Industry vertical"),
    _admin: str = Depends(require_admin_any),
) -> TopicsResponse:
    """Discover relevant blog topics."""
    # Get existing topics to avoid duplication
    existing = blog_repository.list(limit=20)
    existing_topics = [p["title"] for p in existing]

    try:
        topics = await discover_topics(
            industry=industry,
            existing_topics=existing_topics,
        )
    except TopicDiscoveryError as e:
        log_error(
            logger,
            ErrorCode.LLM_API_ERROR,
            "Topic discovery failed",
            industry=industry,
            error_type=e.error_type,
            error=str(e),
        )
        if e.error_type == "rate_limit":
            raise http_error(ErrorCode.API_RATE_LIMIT, str(e), status=429) from e
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, str(e), status=500) from e

    filtered = filter_topics(topics, min_relevance=0.4, max_topics=10)

    logger.info(f"Admin: Discovered {len(filtered)} topics for industry={industry}")

    return TopicsResponse(
        topics=[
            TopicResponse(
                title=t.title,
                description=t.description,
                keywords=t.keywords,
                relevance_score=t.relevance_score,
                source=t.source,
            )
            for t in filtered
        ]
    )


@router.post(
    "/posts/{post_id}/publish",
    response_model=BlogPostResponse,
    summary="Publish blog post",
    description="Publish a blog post immediately.",
    responses={
        200: {"description": "Post published successfully"},
        404: {"description": "Post not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("publish blog post")
async def publish_post(
    request: Request,
    post_id: str,
    _admin: str = Depends(require_admin_any),
) -> BlogPostResponse:
    """Publish a blog post immediately."""
    post = blog_repository.publish(post_id)

    if not post:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Blog post {post_id} not found", status=404)

    logger.info(f"Admin: Published blog post {post_id}")

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})


@router.post(
    "/posts/{post_id}/schedule",
    response_model=BlogPostResponse,
    summary="Schedule blog post",
    description="Schedule a blog post for future publication.",
    responses={
        200: {"description": "Post scheduled successfully"},
        400: {"description": "Invalid schedule time", "model": ErrorResponse},
        404: {"description": "Post not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("schedule blog post")
async def schedule_post(
    request: Request,
    post_id: str,
    body: BlogPostUpdate,
    _admin: str = Depends(require_admin_any),
) -> BlogPostResponse:
    """Schedule a blog post for publication."""
    if not body.published_at:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "published_at datetime is required for scheduling",
            status=400,
        )

    post = blog_repository.schedule(post_id, body.published_at)

    if not post:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Blog post {post_id} not found", status=404)

    logger.info(f"Admin: Scheduled blog post {post_id} for {body.published_at}")

    return BlogPostResponse(id=str(post["id"]), **{k: v for k, v in post.items() if k != "id"})


@router.post(
    "/propose-topics",
    response_model=TopicProposalsResponse,
    summary="Propose blog topics",
    description="Get AI-suggested blog topics based on positioning gaps.",
    responses={
        200: {"description": "Topics proposed successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("propose blog topics")
async def propose_blog_topics(
    request: Request,
    count: int = Query(5, ge=1, le=10, description="Number of topics to propose"),
    _admin: str = Depends(require_admin_any),
) -> TopicProposalsResponse:
    """Propose blog topics based on positioning gaps and SEO strategy.

    Combines seed topics from SEO analysis with LLM-generated suggestions
    that align with Board of One's positioning.
    """
    # Get existing post titles to avoid duplication
    existing = blog_repository.list(limit=100)
    existing_titles = [p["title"] for p in existing]

    proposals = await propose_topics(existing_titles, count=count)

    logger.info(f"Admin: Proposed {len(proposals)} blog topics")

    return TopicProposalsResponse(
        topics=[
            TopicProposalResponse(
                title=p.title,
                rationale=p.rationale,
                suggested_keywords=p.suggested_keywords,
                source=p.source,
            )
            for p in proposals
        ]
    )
