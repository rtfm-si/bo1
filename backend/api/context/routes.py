"""FastAPI router and endpoints for context management.

Provides:
- GET /api/v1/context - Get user's saved business context
- PUT /api/v1/context - Update user's business context
- DELETE /api/v1/context - Delete user's saved context
- GET /api/v1/context/refresh-check - Check if refresh prompt needed
- POST /api/v1/context/dismiss-refresh - Dismiss refresh prompt
- POST /api/v1/context/enrich - Enrich context from website
- POST /api/v1/context/competitors/detect - Auto-detect competitors
- POST /api/v1/context/trends/refresh - Refresh market trends
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.api.context.competitors import (
    detect_competitors_for_user,
    refresh_market_trends,
)
from backend.api.context.models import (
    BusinessContext,
    ClarificationInsight,
    CompetitorDetectRequest,
    CompetitorDetectResponse,
    ContextResponse,
    EnrichmentRequest,
    EnrichmentResponse,
    InsightsResponse,
    RefreshCheckResponse,
    TrendsRefreshRequest,
    TrendsRefreshResponse,
)
from backend.api.context.services import (
    context_data_to_model,
    context_model_to_dict,
    enriched_data_to_dict,
    enriched_to_context_model,
    merge_context,
)
from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors
from bo1.services.enrichment import EnrichmentService
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])

# Context refresh interval (3 months)
CONTEXT_REFRESH_DAYS = 90


@router.get(
    "/v1/context",
    response_model=ContextResponse,
    summary="Get user's saved business context",
    description="""
    Retrieve the authenticated user's saved business context.

    Business context is persistent across sessions and helps the AI personas
    provide more relevant recommendations. Context includes:
    - Business model and target market
    - Product/service description
    - Revenue and growth metrics
    - Competitor information

    **Use Cases:**
    - Check if user has saved context before starting deliberation
    - Display saved context in user profile
    - Pre-fill forms with existing context
    """,
    responses={
        200: {
            "description": "Context retrieved successfully (exists=true if saved, false if not)",
            "content": {
                "application/json": {
                    "examples": {
                        "with_context": {
                            "summary": "User has saved context",
                            "value": {
                                "exists": True,
                                "context": {
                                    "business_model": "B2B SaaS",
                                    "target_market": "Small businesses in North America",
                                    "product_description": "AI-powered project management tool",
                                    "revenue": 50000.0,
                                    "customers": 150,
                                    "growth_rate": 15.5,
                                    "competitors": ["Asana", "Monday.com", "Jira"],
                                    "website": "https://example.com",
                                },
                                "updated_at": "2025-01-15T12:00:00",
                            },
                        },
                        "no_context": {
                            "summary": "User has no saved context",
                            "value": {
                                "exists": False,
                                "context": None,
                                "updated_at": None,
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Database error"},
    },
)
@handle_api_errors("get context")
async def get_context(user: dict[str, Any] = Depends(get_current_user)) -> ContextResponse:
    """Get user's saved business context."""
    user_id = extract_user_id(user)

    # Load context from database
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return ContextResponse(exists=False, context=None, updated_at=None)

    # Parse into BusinessContext
    context = context_data_to_model(context_data)

    return ContextResponse(
        exists=True,
        context=context,
        updated_at=context_data.get("updated_at"),
    )


@router.put(
    "/v1/context",
    response_model=dict[str, str],
    summary="Update user's business context",
    description="""
    Create or update the authenticated user's business context.

    Business context is saved to PostgreSQL and persists across sessions.
    This context is used during deliberations to provide more relevant
    recommendations from AI personas.

    **Use Cases:**
    - Save business context during onboarding
    - Update context when business metrics change
    - Pre-populate context for faster deliberation setup

    **Note:** All fields are optional. Only provided fields will be saved.
    """,
    responses={
        200: {
            "description": "Context updated successfully",
            "content": {"application/json": {"example": {"status": "updated"}}},
        },
        500: {"description": "Database error"},
    },
)
@handle_api_errors("update context")
async def update_context(
    context: BusinessContext, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, str]:
    """Update user's business context."""
    user_id = extract_user_id(user)

    # Convert to dict for save function
    context_dict = context_model_to_dict(context)

    # Save to database
    user_repository.save_context(user_id, context_dict)

    logger.info(f"Updated context for user {user_id}")

    return {"status": "updated"}


@router.delete(
    "/v1/context",
    response_model=dict[str, str],
    status_code=200,
    summary="Delete user's saved context",
    description="""
    Delete the authenticated user's saved business context.

    This permanently removes all saved business context from the database.
    Future deliberations will not have access to this context unless
    it is re-entered.

    **Use Cases:**
    - User wants to start fresh
    - User wants to remove outdated business information
    - Privacy: Remove all stored business data

    **Warning:** This action cannot be undone.
    """,
    responses={
        200: {
            "description": "Context deleted successfully",
            "content": {"application/json": {"example": {"status": "deleted"}}},
        },
        404: {"description": "No context found to delete"},
        500: {"description": "Database error"},
    },
)
@handle_api_errors("delete context")
async def delete_context(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    """Delete user's saved business context."""
    user_id = extract_user_id(user)

    # Delete from database
    deleted = user_repository.delete_context(user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="No context found to delete",
        )

    logger.info(f"Deleted context for user {user_id}")

    return {"status": "deleted"}


@router.post(
    "/v1/context/enrich",
    response_model=EnrichmentResponse,
    summary="Enrich context from website",
    description="""
    Analyze a website URL and extract business context information.

    Uses:
    - Website metadata (title, description, OG tags)
    - Brave Search API for company information
    - Claude AI for intelligent extraction

    **Auto-save**: The enriched data is automatically merged with existing
    context and saved. Empty fields are not overwritten.
    """,
    responses={
        200: {
            "description": "Enrichment completed (check success field)",
        },
        422: {"description": "Invalid URL format"},
        500: {"description": "Enrichment service error"},
    },
)
@handle_api_errors("enrich context")
async def enrich_context(
    request: EnrichmentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> EnrichmentResponse:
    """Enrich business context from website URL and auto-save."""
    try:
        user_id = extract_user_id(user)
        logger.info(f"Enriching context from {request.website_url} for user {user_id}")

        # Run enrichment
        service = EnrichmentService()
        try:
            enriched = await service.enrich_from_url(request.website_url)
        finally:
            await service.close()

        # Convert to BusinessContext
        context = enriched_to_context_model(enriched)

        # Auto-save: Merge enriched data with existing context
        existing_context = user_repository.get_context(user_id) or {}
        enriched_dict = enriched_data_to_dict(enriched)

        # Merge (preserve existing user values)
        merged_context = merge_context(existing_context, enriched_dict, preserve_existing=True)

        # Save merged context
        user_repository.save_context(user_id, merged_context)
        logger.info(f"Auto-saved enriched context for user {user_id}")

        return EnrichmentResponse(
            success=True,
            context=context,
            enrichment_source=enriched.enrichment_source,
            confidence=enriched.confidence,
        )

    except ValueError as e:
        logger.warning(f"Invalid URL: {e}")
        return EnrichmentResponse(
            success=False,
            error=f"Invalid URL: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        return EnrichmentResponse(
            success=False,
            error=f"Enrichment failed: {str(e)}",
        )


@router.get(
    "/v1/context/refresh-check",
    response_model=RefreshCheckResponse,
    summary="Check if context refresh needed",
    description=f"""
    Check if the user's business context needs refreshing.

    Returns true if:
    - No context exists
    - Context hasn't been updated in {CONTEXT_REFRESH_DAYS} days
    - Last refresh prompt was dismissed more than {CONTEXT_REFRESH_DAYS} days ago

    Use this to show "Are these details still correct?" prompts.
    """,
)
@handle_api_errors("check refresh needed")
async def check_refresh_needed(
    user: dict[str, Any] = Depends(get_current_user),
) -> RefreshCheckResponse:
    """Check if context refresh is needed."""
    user_id = extract_user_id(user)

    # Get context with extended fields
    row = execute_query(
        """
        SELECT updated_at, last_refresh_prompt, onboarding_completed
        FROM user_context
        WHERE user_id = %s
        """,
        (user_id,),
        fetch="one",
    )

    if not row:
        return RefreshCheckResponse(
            needs_refresh=True,
            last_updated=None,
            days_since_update=None,
        )

    updated_at = row.get("updated_at")
    last_refresh_prompt = row.get("last_refresh_prompt")
    onboarding_completed = row.get("onboarding_completed", False)

    # If onboarding not completed, don't show refresh prompts
    if not onboarding_completed:
        return RefreshCheckResponse(
            needs_refresh=False,
            last_updated=updated_at,
            days_since_update=None,
        )

    # Calculate days since update
    now = datetime.now(UTC)
    days_since_update = (now - updated_at).days if updated_at else None

    # Check if refresh needed
    needs_refresh = False
    if days_since_update is not None and days_since_update >= CONTEXT_REFRESH_DAYS:
        # Check if we already prompted recently
        if last_refresh_prompt:
            days_since_prompt = (now - last_refresh_prompt).days
            needs_refresh = days_since_prompt >= CONTEXT_REFRESH_DAYS
        else:
            needs_refresh = True

    return RefreshCheckResponse(
        needs_refresh=needs_refresh,
        last_updated=updated_at,
        days_since_update=days_since_update,
    )


@router.post(
    "/v1/context/dismiss-refresh",
    response_model=dict[str, str],
    summary="Dismiss refresh prompt",
    description="""
    Dismiss the "Are these details still correct?" refresh prompt.

    This updates the last_refresh_prompt timestamp so the user won't see
    the prompt again for another refresh interval.
    """,
)
@handle_api_errors("dismiss refresh prompt")
async def dismiss_refresh_prompt(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Dismiss the refresh prompt."""
    user_id = extract_user_id(user)

    result = execute_query(
        """
        UPDATE user_context
        SET last_refresh_prompt = NOW(), updated_at = updated_at
        WHERE user_id = %s
        RETURNING user_id
        """,
        (user_id,),
        fetch="one",
    )
    if not result:
        raise HTTPException(status_code=404, detail="No context found")

    return {"status": "dismissed"}


# =============================================================================
# Phase 3: Strategic Context Endpoints
# =============================================================================


@router.post(
    "/v1/context/competitors/detect",
    response_model=CompetitorDetectResponse,
    summary="Auto-detect competitors",
    description="""
    Automatically detect competitors using Tavily Search API.

    First checks if competitors were already detected during website enrichment.
    If not, uses Tavily to search G2, Capterra, and other review sites for
    high-quality competitor information.

    **Auto-save**: Detected competitors are automatically saved to Competitor Watch
    (up to the user's tier limit). Existing competitors are not duplicated.

    Returns a list of detected competitors with names, URLs, and descriptions.
    """,
)
@handle_api_errors("detect competitors")
async def detect_competitors(
    request: CompetitorDetectRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorDetectResponse:
    """Detect competitors using Tavily Search API and auto-save to Competitor Watch."""
    user_id = extract_user_id(user)
    industry = request.industry if request else None
    product_description = request.product_description if request else None

    return await detect_competitors_for_user(user_id, industry, product_description)


@router.post(
    "/v1/context/trends/refresh",
    response_model=TrendsRefreshResponse,
    summary="Refresh market trends",
    description="""
    Fetch current market trends for the user's industry using Brave Search API.

    Uses the industry from saved context or the request to search for
    recent trends and news.

    Returns a list of trends with sources.
    """,
)
@handle_api_errors("refresh trends")
async def refresh_trends(
    request: TrendsRefreshRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> TrendsRefreshResponse:
    """Refresh market trends using Brave Search."""
    user_id = extract_user_id(user)
    industry = request.industry if request else None

    return await refresh_market_trends(user_id, industry)


# =============================================================================
# Phase 4: Insights Endpoints (Clarifications from Meetings)
# =============================================================================


@router.get(
    "/v1/context/insights",
    response_model=InsightsResponse,
    summary="Get accumulated insights from meetings",
    description="""
    Retrieve insights accumulated from user's meetings.

    Currently includes:
    - **Clarifications**: Q&A pairs from clarifying questions answered during meetings

    These insights are automatically collected during meetings when users answer
    clarifying questions. They help improve future meetings by providing
    relevant context.

    **Use Cases:**
    - Display clarification history in settings
    - Show what the system has learned about the user's business
    - Allow users to review and potentially edit their responses
    """,
    responses={
        200: {
            "description": "Insights retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "clarifications": [
                            {
                                "question": "What is your primary revenue model?",
                                "answer": "Subscription-based SaaS with annual contracts",
                                "answered_at": "2025-01-15T12:00:00Z",
                                "session_id": "bo1_abc123",
                            }
                        ],
                        "total_count": 1,
                    }
                }
            },
        },
    },
)
@handle_api_errors("get insights")
async def get_insights(
    user: dict[str, Any] = Depends(get_current_user),
) -> InsightsResponse:
    """Get accumulated insights from user's meetings."""
    user_id = extract_user_id(user)

    # Load context from database
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return InsightsResponse(clarifications=[], total_count=0)

    # Extract clarifications from context
    raw_clarifications = context_data.get("clarifications", {})
    clarifications: list[ClarificationInsight] = []

    for question, data in raw_clarifications.items():
        if isinstance(data, dict):
            # New format with metadata
            clarifications.append(
                ClarificationInsight(
                    question=question,
                    answer=data.get("answer", ""),
                    answered_at=data.get("answered_at"),
                    session_id=data.get("session_id"),
                )
            )
        else:
            # Legacy format (string value only)
            clarifications.append(
                ClarificationInsight(
                    question=question,
                    answer=str(data),
                    answered_at=None,
                    session_id=None,
                )
            )

    # Sort by answered_at (newest first), with None values at the end
    clarifications.sort(
        key=lambda c: c.answered_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    logger.info(f"Retrieved {len(clarifications)} clarification insights for user {user_id}")

    return InsightsResponse(
        clarifications=clarifications,
        total_count=len(clarifications),
    )


@router.delete(
    "/v1/context/insights/{question_hash}",
    response_model=dict[str, str],
    summary="Delete a specific clarification insight",
    description="""
    Delete a specific clarification from the user's insights.

    The question_hash is a URL-safe base64 encoding of the question text.
    This allows deleting clarifications that may contain special characters.
    """,
)
@handle_api_errors("delete insight")
async def delete_insight(
    question_hash: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a specific clarification insight."""
    import base64

    user_id = extract_user_id(user)

    # Decode the question from the hash
    try:
        question = base64.urlsafe_b64decode(question_hash.encode()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode question hash: {e}")
        raise HTTPException(status_code=400, detail="Invalid question hash") from None

    # Load and update context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    clarifications = context_data.get("clarifications", {})
    if question not in clarifications:
        raise HTTPException(status_code=404, detail="Clarification not found")

    # Remove the clarification
    del clarifications[question]
    context_data["clarifications"] = clarifications

    # Save updated context
    user_repository.save_context(user_id, context_data)
    logger.info(f"Deleted clarification insight for user {user_id}: {question[:50]}...")

    return {"status": "deleted"}


# =============================================================================
# Phase 5: Onboarding Demo Questions
# =============================================================================


@router.get(
    "/v1/context/demo-questions",
    summary="Get personalized demo questions",
    description="""
    Get personalized business questions for new users based on their context.

    Uses the user's saved business context to generate relevant, actionable
    questions they can explore in their first meeting.

    **Features:**
    - Questions are cached for 7 days
    - Falls back to generic questions if no context or LLM fails
    - Uses "fast" tier (Haiku) to minimize cost

    **Use Cases:**
    - Onboarding flow: show suggested questions to new users
    - Help users get started with relevant decisions
    - Demonstrate platform value during first session
    """,
    responses={
        200: {
            "description": "Demo questions generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "questions": [
                            {
                                "question": "Should we expand to the European market this year?",
                                "category": "growth",
                                "relevance": "Given your growth rate and product maturity, international expansion could be timely.",
                            }
                        ],
                        "generated": True,
                        "cached": False,
                    }
                }
            },
        },
    },
)
@handle_api_errors("get demo questions")
async def get_demo_questions(
    refresh: bool = False,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get personalized demo questions based on user's context."""
    from backend.services.demo_questions import generate_demo_questions

    user_id = extract_user_id(user)

    # Get user's business context
    context_data = user_repository.get_context(user_id)

    # Generate questions
    result = await generate_demo_questions(
        user_id=user_id,
        context=context_data,
        force_refresh=refresh,
    )

    return {
        "questions": [q.model_dump() for q in result.questions],
        "generated": result.generated,
        "cached": result.cached,
    }


@router.delete(
    "/v1/context/demo-questions",
    summary="Clear cached demo questions",
    description="""
    Clear the cached demo questions for the current user.

    Use this when:
    - User updates their business context significantly
    - User wants fresh suggestions

    Next call to GET /demo-questions will regenerate.
    """,
)
@handle_api_errors("clear demo questions cache")
async def clear_demo_questions(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Clear cached demo questions."""
    from backend.services.demo_questions import clear_cached_questions

    user_id = extract_user_id(user)
    clear_cached_questions(user_id)

    return {"status": "cleared"}
