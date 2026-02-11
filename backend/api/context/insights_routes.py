"""Insight-related endpoints for context management.

Provides:
- GET /v1/context/insights - Get accumulated insights from meetings
- PATCH /v1/context/insights/{question_hash} - Update a clarification insight
- DELETE /v1/context/insights/{question_hash} - Delete a clarification insight
- GET /v1/context/demo-questions - Get personalized demo questions
- DELETE /v1/context/demo-questions - Clear cached demo questions
- POST /v1/context/insights/{question_key}/enrich - Enrich insight with market context
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from backend.api.context.models import (
    ClarificationInsight,
    InsightCategory,
    InsightEnrichResponse,
    InsightMetricResponse,
    InsightsResponse,
    UpdateInsightRequest,
)
from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


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
        403: ERROR_403_RESPONSE,
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
            # Build metric response if present
            metric_response = None
            if data.get("metric"):
                m = data["metric"]
                metric_response = InsightMetricResponse(
                    value=m.get("value"),
                    unit=m.get("unit"),
                    metric_type=m.get("metric_type"),
                    period=m.get("period"),
                    raw_text=m.get("raw_text"),
                )

            # Parse category
            category = None
            if data.get("category"):
                try:
                    category = InsightCategory(data["category"])
                except ValueError:
                    category = InsightCategory.UNCATEGORIZED

            # New format with metadata (including structured fields)
            clarifications.append(
                ClarificationInsight(
                    question=question,
                    answer=data.get("answer", ""),
                    answered_at=data.get("answered_at"),
                    session_id=data.get("session_id"),
                    category=category,
                    metric=metric_response,
                    confidence_score=data.get("confidence_score"),
                    summary=data.get("summary"),
                    key_entities=data.get("key_entities"),
                    parsed_at=data.get("parsed_at"),
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


@router.patch(
    "/v1/context/insights/{question_hash}",
    response_model=ClarificationInsight,
    summary="Update a clarification insight",
    description="""
    Update a user's answer to a clarifying question.

    The question_hash is a URL-safe base64 encoding of the question text.
    When updated, the answer and updated timestamp are persisted, allowing
    users to keep their responses current as their business evolves.
    """,
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("update insight")
async def update_insight(
    question_hash: str,
    request: UpdateInsightRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ClarificationInsight:
    """Update a specific clarification insight."""
    import base64

    user_id = extract_user_id(user)

    # Load context first
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    clarifications = context_data.get("clarifications", {})

    # Decode the question from the hash
    question = None
    try:
        # Add padding if stripped (frontend removes trailing =)
        padded_hash = (
            question_hash + "=" * (4 - len(question_hash) % 4)
            if len(question_hash) % 4
            else question_hash
        )
        question = base64.urlsafe_b64decode(padded_hash.encode()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode question hash: {e}")
        # Try to find by matching hash against all questions
        for q in clarifications:
            q_hash = base64.urlsafe_b64encode(q.encode()).decode().rstrip("=")
            if q_hash == question_hash:
                question = q
                break

    if not question or question not in clarifications:
        raise http_error(ErrorCode.API_NOT_FOUND, "Clarification not found", status=404)

    # Validate the new value before storing
    from backend.services.insight_parser import is_valid_insight_response

    if not is_valid_insight_response(request.value):
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            "Invalid insight response: please provide a meaningful answer",
            status=400,
        )

    # Get existing clarification data
    existing = clarifications[question]
    if isinstance(existing, str):
        # Legacy format, convert to new format
        existing = {"answer": existing, "answered_at": None, "source": "meeting"}

    # Update the answer and timestamp
    existing["answer"] = request.value
    existing["updated_at"] = datetime.now(UTC).isoformat()
    if request.note:
        existing["update_note"] = request.note

    # Re-parse with Haiku for structured fields
    try:
        from backend.services.insight_parser import parse_insight

        structured = await parse_insight(request.value)
        existing["category"] = structured.category.value
        existing["confidence_score"] = structured.confidence_score
        if structured.metric:
            existing["metric"] = {
                "value": structured.metric.value,
                "unit": structured.metric.unit,
                "metric_type": structured.metric.metric_type,
                "period": structured.metric.period,
                "raw_text": structured.metric.raw_text,
            }
        else:
            existing.pop("metric", None)
        if structured.summary:
            existing["summary"] = structured.summary
        else:
            existing.pop("summary", None)
        if structured.key_entities:
            existing["key_entities"] = structured.key_entities
        else:
            existing.pop("key_entities", None)
        existing["parsed_at"] = structured.parsed_at
    except Exception as parse_err:
        logger.debug(f"Insight parsing failed during update (non-blocking): {parse_err}")
        existing["category"] = "uncategorized"
        existing["confidence_score"] = 0.0

    # Validate entry before storage
    from backend.api.context.services import normalize_clarification_for_storage

    clarifications[question] = normalize_clarification_for_storage(existing)
    context_data["clarifications"] = clarifications

    # Save updated context
    user_repository.save_context(user_id, context_data)
    logger.info(f"Updated clarification insight for user {user_id}: {question[:50]}...")

    # Auto-sync to business_metrics if metric was extracted with good confidence
    try:
        from backend.api.context.services import (
            CATEGORY_TO_METRIC_KEY,
            DEFAULT_CONFIDENCE_THRESHOLD,
            METRIC_DISPLAY_NAMES,
        )
        from bo1.state.repositories.metrics_repository import metrics_repository

        category = existing.get("category")
        confidence = existing.get("confidence_score", 0.0)
        metric_data = existing.get("metric")

        if (
            category
            and category in CATEGORY_TO_METRIC_KEY
            and CATEGORY_TO_METRIC_KEY[category]
            and confidence >= DEFAULT_CONFIDENCE_THRESHOLD
            and metric_data
            and metric_data.get("value") is not None
        ):
            metric_key = CATEGORY_TO_METRIC_KEY[category]
            name = METRIC_DISPLAY_NAMES.get(metric_key, metric_key.replace("_", " ").title())
            metrics_repository.save_metric(
                user_id=user_id,
                metric_key=metric_key,
                value=float(metric_data["value"]),
                name=name,
                value_unit=metric_data.get("unit"),
                source="clarification",
                is_predefined=False,
            )
            logger.debug(f"Auto-saved metric {metric_key} from clarification for {user_id}")
    except Exception as metric_err:
        # Non-blocking: don't fail the request if metric save fails
        logger.warning(f"Failed to auto-save metric from clarification: {metric_err}")

    # Build metric response if present
    metric_response = None
    if existing.get("metric"):
        m = existing["metric"]
        metric_response = InsightMetricResponse(
            value=m.get("value"),
            unit=m.get("unit"),
            metric_type=m.get("metric_type"),
            period=m.get("period"),
            raw_text=m.get("raw_text"),
        )

    # Return updated insight with structured fields
    return ClarificationInsight(
        question=question,
        answer=existing["answer"],
        answered_at=existing.get("answered_at"),
        session_id=existing.get("session_id"),
        category=InsightCategory(existing.get("category", "uncategorized")),
        metric=metric_response,
        confidence_score=existing.get("confidence_score"),
        summary=existing.get("summary"),
        key_entities=existing.get("key_entities"),
        parsed_at=existing.get("parsed_at"),
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
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("delete insight")
async def delete_insight(
    question_hash: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a specific clarification insight."""
    import base64

    user_id = extract_user_id(user)

    # Load context first
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    clarifications = context_data.get("clarifications", {})

    # Decode the question from the hash
    question = None
    try:
        # Add padding if stripped (frontend removes trailing =)
        padded_hash = (
            question_hash + "=" * (4 - len(question_hash) % 4)
            if len(question_hash) % 4
            else question_hash
        )
        question = base64.urlsafe_b64decode(padded_hash.encode()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode question hash: {e}")
        # Try to find by matching hash against all questions
        for q in clarifications:
            q_hash = base64.urlsafe_b64encode(q.encode()).decode().rstrip("=")
            if q_hash == question_hash:
                question = q
                break

    if not question or question not in clarifications:
        raise http_error(ErrorCode.API_NOT_FOUND, "Clarification not found", status=404)

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
        403: ERROR_403_RESPONSE,
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
    responses={403: ERROR_403_RESPONSE},
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


# =============================================================================
# Insight Market Context Enrichment Endpoints
# =============================================================================


async def _enrich_insight_background(
    user_id: str,
    question_key: str,
    metric_key: str,
    metric_value: float,
    industry: str,
) -> None:
    """Background task to enrich an insight with market context.

    Non-blocking: errors are logged but don't affect the user response.
    """
    try:
        from backend.services.insight_enrichment import (
            InsightEnrichmentService,
            market_context_to_dict,
        )

        service = InsightEnrichmentService()
        result = await service.enrich_insight(
            metric_key=metric_key,
            metric_value=metric_value,
            industry=industry,
        )

        if result is None:
            logger.debug(f"No market context available for {metric_key} in {industry}")
            return

        # Load and update the insight
        context_data = user_repository.get_context(user_id) or {}
        clarifications = context_data.get("clarifications", {})

        if question_key not in clarifications:
            logger.warning(f"Insight {question_key} not found for enrichment")
            return

        # Add market context to the insight
        clarifications[question_key]["market_context"] = market_context_to_dict(result)
        context_data["clarifications"] = clarifications
        user_repository.save_context(user_id, context_data)

        logger.info(
            f"Enriched insight {question_key} for user {user_id}: "
            f"percentile={result.percentile_position}"
        )
    except Exception as e:
        logger.warning(f"Background insight enrichment failed: {e}")


@router.post(
    "/v1/context/insights/{question_key}/enrich",
    response_model=InsightEnrichResponse,
    summary="Enrich an insight with market context",
    description="""
    Manually trigger market context enrichment for a specific insight.

    Finds matching industry benchmarks and adds percentile comparison data
    to the insight. Useful for:
    - Re-enriching insights after industry changes
    - Enriching older insights that were created before this feature

    **Requirements:**
    - User must have an industry set in context
    - Insight must have a metric with a numeric value

    **Cost:** ~$0.005-0.01 if cache miss (web research + LLM extraction)
    """,
    responses={
        200: {
            "description": "Enrichment completed (check enriched field)",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "enriched": True,
                        "percentile_position": 45,
                        "comparison_text": "Your CAC ($50) is in the 45th percentile for SaaS (below average)",
                    }
                }
            },
        },
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@handle_api_errors("enrich insight")
async def enrich_insight(
    question_key: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> InsightEnrichResponse:
    """Manually enrich an insight with market context."""
    from backend.services.insight_enrichment import (
        InsightEnrichmentService,
        market_context_to_dict,
    )

    user_id = extract_user_id(user)

    # Load context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(
            code=ErrorCode.API_NOT_FOUND,
            message="No context found",
            status=404,
        )

    # Check industry
    industry = context_data.get("industry")
    if not industry:
        return InsightEnrichResponse(
            success=False,
            enriched=False,
            error="No industry set in context. Set your industry first.",
        )

    # Find the insight
    clarifications = context_data.get("clarifications", {})
    if question_key not in clarifications:
        raise http_error(
            code=ErrorCode.API_NOT_FOUND,
            message=f"Insight not found: {question_key}",
            status=404,
        )

    insight = clarifications[question_key]

    # Extract metric info
    metric_key = insight.get("metric_key")
    metric_data = insight.get("metric")
    metric_value = metric_data.get("value") if metric_data else None

    if not metric_key or metric_value is None:
        return InsightEnrichResponse(
            success=False,
            enriched=False,
            error="Insight has no metric value to compare against benchmarks",
        )

    # Run enrichment
    service = InsightEnrichmentService()
    result = await service.enrich_insight(
        metric_key=metric_key,
        metric_value=float(metric_value),
        industry=industry,
    )

    if result is None:
        return InsightEnrichResponse(
            success=True,
            enriched=False,
            error=f"No benchmark data available for {metric_key} in {industry}",
        )

    # Save enrichment to insight
    clarifications[question_key]["market_context"] = market_context_to_dict(result)
    context_data["clarifications"] = clarifications
    user_repository.save_context(user_id, context_data)

    logger.info(
        f"Manually enriched insight {question_key} for user {user_id}: "
        f"percentile={result.percentile_position}"
    )

    return InsightEnrichResponse(
        success=True,
        enriched=True,
        percentile_position=result.percentile_position,
        comparison_text=result.comparison_text,
    )
