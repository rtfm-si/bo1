"""Admin API endpoints for published decision management.

Provides:
- GET /api/admin/decisions - List decisions with filters
- POST /api/admin/decisions - Create decision
- GET /api/admin/decisions/{id} - Get decision by ID
- PATCH /api/admin/decisions/{id} - Update decision
- DELETE /api/admin/decisions/{id} - Delete decision
- POST /api/admin/decisions/{id}/publish - Publish decision
- POST /api/admin/decisions/{id}/unpublish - Unpublish decision
- POST /api/admin/decisions/generate - Generate decision from meeting
- GET /api/admin/decisions/categories - Get category list with counts
"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import (
    DECISION_CATEGORIES,
    CategoriesResponse,
    CategoryWithCount,
    DecisionCreate,
    DecisionGenerateRequest,
    DecisionListResponse,
    DecisionResponse,
    DecisionUpdate,
    ErrorResponse,
    FeaturedDecisionResponse,
    FeaturedDecisionsResponse,
    FeaturedOrderRequest,
    SEOBackfillResponse,
    TopicBankListResponse,
    TopicBankResponse,
)
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode
from bo1.state.repositories.decision_repository import decision_repository
from bo1.state.repositories.topic_bank_repository import topic_bank_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/decisions", tags=["Admin - Decisions"])


def _decision_to_response(d: dict) -> DecisionResponse:
    """Convert decision dict to response model."""
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
        status=d["status"],
        published_at=d.get("published_at"),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        view_count=d.get("view_count", 0),
        click_through_count=d.get("click_through_count", 0),
        homepage_featured=d.get("homepage_featured", False),
        homepage_order=d.get("homepage_order"),
        seo_keywords=d.get("seo_keywords"),
        meta_title=d.get("meta_title"),
    )


@router.get(
    "",
    response_model=DecisionListResponse,
    summary="List decisions",
    description="List all published decisions with optional filters.",
    responses={
        200: {"description": "Decisions retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list decisions")
async def list_decisions(
    request: Request,
    status: str | None = Query(None, description="Filter by status: draft, published"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _admin: str = Depends(require_admin_any),
) -> DecisionListResponse:
    """List decisions with optional filters."""
    decisions = decision_repository.list_decisions(
        status=status, category=category, limit=limit, offset=offset
    )
    total = decision_repository.count(status=status, category=category)

    logger.info(f"Admin: Listed {len(decisions)} decisions (status={status}, category={category})")

    return DecisionListResponse(
        decisions=[_decision_to_response(d) for d in decisions],
        total=total,
    )


@router.post(
    "",
    response_model=DecisionResponse,
    summary="Create decision",
    description="Create a new published decision (defaults to draft status).",
    responses={
        200: {"description": "Decision created successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create decision")
async def create_decision(
    request: Request,
    body: DecisionCreate,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Create a new published decision."""
    decision = decision_repository.create(
        title=body.title,
        category=body.category,
        founder_context=body.founder_context.model_dump() if body.founder_context else {},
        session_id=body.session_id,
        meta_description=body.meta_description,
        expert_perspectives=[p.model_dump() for p in body.expert_perspectives]
        if body.expert_perspectives
        else None,
        synthesis=body.synthesis,
        faqs=[f.model_dump() for f in body.faqs] if body.faqs else None,
    )

    logger.info(f"Admin: Created decision '{body.title}' (id={decision['id']})")

    return _decision_to_response(decision)


@router.get(
    "/featured",
    response_model=FeaturedDecisionsResponse,
    summary="Get featured decisions",
    description="Get decisions marked as featured for homepage display.",
    responses={
        200: {"description": "Featured decisions retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list featured decisions")
async def list_featured_decisions(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> FeaturedDecisionsResponse:
    """Get featured homepage decisions."""
    decisions = decision_repository.list_featured_for_homepage(limit=10)

    return FeaturedDecisionsResponse(
        decisions=[
            FeaturedDecisionResponse(
                id=str(d["id"]),
                category=d["category"],
                slug=d["slug"],
                title=d["title"],
                meta_description=d.get("meta_description"),
                synthesis=d.get("synthesis"),
                homepage_order=d.get("homepage_order"),
            )
            for d in decisions
        ]
    )


@router.put(
    "/featured/order",
    response_model=FeaturedDecisionsResponse,
    summary="Reorder featured decisions",
    description="Reorder featured decisions by providing ordered list of IDs.",
    responses={
        200: {"description": "Order updated successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("reorder featured decisions")
async def reorder_featured_decisions(
    request: Request,
    body: FeaturedOrderRequest,
    _admin: str = Depends(require_admin_any),
) -> FeaturedDecisionsResponse:
    """Reorder featured decisions."""
    decision_repository.update_homepage_order(body.decision_ids)
    logger.info(f"Admin: Reordered {len(body.decision_ids)} featured decisions")

    # Return updated list
    decisions = decision_repository.list_featured_for_homepage(limit=10)

    return FeaturedDecisionsResponse(
        decisions=[
            FeaturedDecisionResponse(
                id=str(d["id"]),
                category=d["category"],
                slug=d["slug"],
                title=d["title"],
                meta_description=d.get("meta_description"),
                synthesis=d.get("synthesis"),
                homepage_order=d.get("homepage_order"),
            )
            for d in decisions
        ]
    )


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    summary="Get categories",
    description="Get list of categories with published decision counts.",
    responses={
        200: {"description": "Categories retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get categories")
async def get_categories(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> CategoriesResponse:
    """Get categories with counts."""
    categories = decision_repository.get_categories_with_counts()

    # Include all categories, even with 0 count
    category_counts = {c["category"]: c["count"] for c in categories}
    all_categories = [
        CategoryWithCount(category=cat, count=category_counts.get(cat, 0))
        for cat in DECISION_CATEGORIES
    ]

    return CategoriesResponse(categories=all_categories)


# =========================================================================
# Topic Bank Routes
# =========================================================================


def _topic_to_response(t: dict) -> TopicBankResponse:
    """Convert topic dict to response model."""
    return TopicBankResponse(
        id=str(t["id"]),
        title=t["title"],
        description=t["description"],
        category=t["category"],
        keywords=t.get("keywords") or [],
        seo_score=t.get("seo_score", 0.0),
        reasoning=t["reasoning"],
        bo1_alignment=t["bo1_alignment"],
        source=t.get("source", "llm-generated"),
        status=t["status"],
        researched_at=t.get("researched_at"),
        used_at=t.get("used_at"),
    )


@router.post(
    "/research-topics",
    response_model=TopicBankListResponse,
    summary="Research decision topics",
    description="Run Brave+Tavily research to discover high-intent decision topics.",
    responses={
        200: {"description": "Topics researched and banked"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("research decision topics")
async def research_topics(
    request: Request,
    max_topics: int = Query(10, ge=1, le=25, description="Max topics to research"),
    _admin: str = Depends(require_admin_any),
) -> TopicBankListResponse:
    """Trigger topic research and bank results."""
    from backend.services.decision_topic_researcher import research_decision_topics

    topics = await research_decision_topics(max_topics=max_topics)
    logger.info(f"Admin: Researched {len(topics)} decision topics")

    return TopicBankListResponse(
        topics=[_topic_to_response(t) for t in topics],
        total=len(topics),
    )


@router.get(
    "/topic-bank",
    response_model=TopicBankListResponse,
    summary="List banked topics",
    description="List banked decision topics, sorted by SEO score.",
    responses={
        200: {"description": "Topics retrieved"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list topic bank")
async def list_topic_bank(
    request: Request,
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _admin: str = Depends(require_admin_any),
) -> TopicBankListResponse:
    """List banked topics sorted by SEO score."""
    topics = topic_bank_repository.list_banked(category=category, limit=limit, offset=offset)
    total = topic_bank_repository.count_banked(category=category)

    return TopicBankListResponse(
        topics=[_topic_to_response(t) for t in topics],
        total=total,
    )


@router.delete(
    "/topic-bank/{topic_id}",
    summary="Dismiss banked topic",
    description="Dismiss or delete a banked topic.",
    responses={
        200: {"description": "Topic dismissed"},
        404: {"description": "Topic not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("dismiss topic")
async def dismiss_topic(
    request: Request,
    topic_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Dismiss a banked topic."""
    dismissed = topic_bank_repository.dismiss(topic_id)

    if not dismissed:
        raise http_error(
            ErrorCode.API_NOT_FOUND, f"Topic {topic_id} not found or not banked", status=404
        )

    logger.info(f"Admin: Dismissed topic {topic_id}")
    return {"success": True, "message": f"Topic {topic_id} dismissed"}


@router.post(
    "/topic-bank/{topic_id}/use",
    response_model=DecisionResponse,
    summary="Use topic as draft decision",
    description="Create a draft decision pre-filled from a banked topic.",
    responses={
        200: {"description": "Draft decision created"},
        404: {"description": "Topic not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("use topic as draft")
async def use_topic_as_draft(
    request: Request,
    topic_id: str,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Create a draft decision from a banked topic."""
    topic = topic_bank_repository.mark_used(topic_id)

    if not topic:
        raise http_error(
            ErrorCode.API_NOT_FOUND, f"Topic {topic_id} not found or not banked", status=404
        )

    # Create draft decision pre-filled from topic
    decision = decision_repository.create(
        title=topic["title"],
        category=topic["category"],
        founder_context={"situation": topic["description"]},
        meta_description=topic["reasoning"],
        seo_keywords=topic.get("keywords") or [],
    )

    logger.info(f"Admin: Created draft from topic '{topic['title']}' (decision={decision['id']})")

    return _decision_to_response(decision)


@router.get(
    "/{decision_id}",
    response_model=DecisionResponse,
    summary="Get decision",
    description="Get a decision by ID.",
    responses={
        200: {"description": "Decision retrieved successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get decision")
async def get_decision(
    request: Request,
    decision_id: str,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Get a decision by ID."""
    decision = decision_repository.get_by_id(decision_id)

    if not decision:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    return _decision_to_response(decision)


@router.patch(
    "/{decision_id}",
    response_model=DecisionResponse,
    summary="Update decision",
    description="Update decision fields.",
    responses={
        200: {"description": "Decision updated successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update decision")
async def update_decision(
    request: Request,
    decision_id: str,
    body: DecisionUpdate,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Update a decision."""
    updates = {}

    if body.title is not None:
        updates["title"] = body.title
    if body.category is not None:
        updates["category"] = body.category
    if body.slug is not None:
        updates["slug"] = body.slug
    if body.meta_description is not None:
        updates["meta_description"] = body.meta_description
    if body.founder_context is not None:
        updates["founder_context"] = body.founder_context.model_dump()
    if body.expert_perspectives is not None:
        updates["expert_perspectives"] = [p.model_dump() for p in body.expert_perspectives]
    if body.synthesis is not None:
        updates["synthesis"] = body.synthesis
    if body.faqs is not None:
        updates["faqs"] = [f.model_dump() for f in body.faqs]
    if body.related_decision_ids is not None:
        updates["related_decision_ids"] = body.related_decision_ids
    if body.status is not None:
        updates["status"] = body.status
    if body.seo_keywords is not None:
        updates["seo_keywords"] = body.seo_keywords
    if body.meta_title is not None:
        updates["meta_title"] = body.meta_title

    decision = decision_repository.update(decision_id, **updates)

    if not decision:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    logger.info(f"Admin: Updated decision {decision_id} (fields: {list(updates.keys())})")

    return _decision_to_response(decision)


@router.delete(
    "/{decision_id}",
    summary="Delete decision",
    description="Delete a decision (hard delete).",
    responses={
        200: {"description": "Decision deleted successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete decision")
async def delete_decision(
    request: Request,
    decision_id: str,
    _admin: str = Depends(require_admin_any),
) -> dict:
    """Delete a decision."""
    deleted = decision_repository.delete(decision_id)

    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    logger.info(f"Admin: Deleted decision {decision_id}")

    return {"success": True, "message": f"Decision {decision_id} deleted"}


@router.post(
    "/{decision_id}/feature",
    response_model=DecisionResponse,
    summary="Feature decision on homepage",
    description="Add a decision to the homepage featured list.",
    responses={
        200: {"description": "Decision featured successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("feature decision")
async def feature_decision(
    request: Request,
    decision_id: str,
    order: int | None = Query(None, description="Display order (lower = first)"),
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Feature a decision on homepage."""
    decision = decision_repository.set_homepage_featured(decision_id, featured=True, order=order)

    if not decision:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    logger.info(f"Admin: Featured decision {decision_id} on homepage (order={order})")

    return _decision_to_response(decision)


@router.post(
    "/{decision_id}/unfeature",
    response_model=DecisionResponse,
    summary="Remove decision from homepage",
    description="Remove a decision from the homepage featured list.",
    responses={
        200: {"description": "Decision unfeatured successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("unfeature decision")
async def unfeature_decision(
    request: Request,
    decision_id: str,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Remove a decision from homepage."""
    decision = decision_repository.set_homepage_featured(decision_id, featured=False)

    if not decision:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    logger.info(f"Admin: Unfeatured decision {decision_id} from homepage")

    return _decision_to_response(decision)


@router.post(
    "/{decision_id}/publish",
    response_model=DecisionResponse,
    summary="Publish decision",
    description="Publish a decision immediately. Auto-enriches SEO fields if missing.",
    responses={
        200: {"description": "Decision published successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("publish decision")
async def publish_decision(
    request: Request,
    decision_id: str,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Publish a decision immediately.

    If the decision lacks SEO keywords, auto-enriches them using LLM.
    """
    decision = decision_repository.publish(decision_id)

    if not decision:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    # Auto-enrich SEO fields if missing
    if not decision.get("seo_keywords") and decision.get("synthesis"):
        try:
            from backend.services.seo_enrichment import enrich_decision_seo

            enrichment = await enrich_decision_seo(
                decision_id=decision_id,
                title=decision.get("title"),
                category=decision.get("category"),
                synthesis=decision.get("synthesis"),
            )
            decision = decision_repository.update(
                decision_id,
                seo_keywords=enrichment.seo_keywords,
                meta_title=enrichment.meta_title,
                related_decision_ids=enrichment.related_decision_ids,
            )
            logger.info(f"Admin: Auto-enriched SEO for decision {decision_id}")
        except Exception as e:
            # Log but don't fail publish if SEO enrichment fails
            logger.warning(f"SEO enrichment failed for {decision_id}: {e}")

    logger.info(f"Admin: Published decision {decision_id}")

    return _decision_to_response(decision)


@router.post(
    "/{decision_id}/unpublish",
    response_model=DecisionResponse,
    summary="Unpublish decision",
    description="Revert a decision to draft status.",
    responses={
        200: {"description": "Decision unpublished successfully"},
        404: {"description": "Decision not found", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("unpublish decision")
async def unpublish_decision(
    request: Request,
    decision_id: str,
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Unpublish a decision."""
    decision = decision_repository.unpublish(decision_id)

    if not decision:
        raise http_error(ErrorCode.API_NOT_FOUND, f"Decision {decision_id} not found", status=404)

    logger.info(f"Admin: Unpublished decision {decision_id}")

    return _decision_to_response(decision)


@router.post(
    "/generate",
    response_model=DecisionResponse,
    summary="Generate decision",
    description="Run a deliberation and create a decision page from it.",
    responses={
        200: {"description": "Decision generated successfully"},
        400: {"description": "Generation failed", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("generate decision")
async def generate_decision(
    request: Request,
    body: DecisionGenerateRequest,
    save_draft: bool = Query(True, description="Save as draft decision"),
    _admin: str = Depends(require_admin_any),
) -> DecisionResponse:
    """Generate a decision page by running a real deliberation.

    This endpoint:
    1. Creates an internal session with the question
    2. Runs a full deliberation
    3. Extracts expert perspectives and synthesis
    4. Creates a published decision in draft status
    """
    # Import here to avoid circular imports
    from backend.services.decision_generator import generate_decision_content

    content = await generate_decision_content(
        question=body.question,
        category=body.category,
        founder_context=body.founder_context.model_dump(),
    )

    if not save_draft:
        # Return without saving
        return DecisionResponse(
            id="",
            session_id=content.session_id,
            category=body.category,
            slug="",
            title=body.question,
            meta_description=content.meta_description,
            founder_context=body.founder_context.model_dump(),
            expert_perspectives=content.expert_perspectives,
            synthesis=content.synthesis,
            faqs=content.faqs,
            related_decision_ids=None,
            status="draft",
            published_at=None,
            created_at=content.created_at,
            updated_at=content.created_at,
            view_count=0,
            click_through_count=0,
            seo_keywords=content.seo_keywords,
        )

    # Save as draft
    decision = decision_repository.create(
        title=body.question,
        category=body.category,
        founder_context=body.founder_context.model_dump(),
        session_id=content.session_id,
        meta_description=content.meta_description,
        expert_perspectives=content.expert_perspectives,
        synthesis=content.synthesis,
        faqs=content.faqs,
        seo_keywords=content.seo_keywords,
    )

    logger.info(f"Admin: Generated decision '{body.question}' (id={decision['id']})")

    return _decision_to_response(decision)


@router.post(
    "/backfill-seo",
    response_model=SEOBackfillResponse,
    summary="Backfill SEO fields",
    description="Backfill SEO keywords and related decisions for decisions missing them.",
    responses={
        200: {"description": "Backfill completed"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("backfill seo")
async def backfill_seo(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Max decisions to process"),
    _admin: str = Depends(require_admin_any),
) -> SEOBackfillResponse:
    """Backfill SEO fields for decisions missing them.

    Processes decisions without seo_keywords, generating keywords and
    finding related decisions using LLM.
    """
    from backend.services.seo_enrichment import backfill_seo_fields

    results = await backfill_seo_fields(limit=limit)

    logger.info(f"Admin: SEO backfill complete - {results}")

    return SEOBackfillResponse(**results)
