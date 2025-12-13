"""User feedback API endpoint.

Provides:
- POST /api/v1/feedback - Submit feature request or problem report
Rate limited to 5 submissions per hour per user.

Feedback is analyzed with Claude Haiku for sentiment and theme extraction.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    ErrorResponse,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackType,
)
from backend.api.utils.errors import handle_api_errors
from backend.services.feedback_analyzer import analyze_feedback
from backend.services.usage_tracking import get_effective_tier
from bo1.state.repositories.feedback_repository import feedback_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])

# Rate limit: 5 submissions per hour
FEEDBACK_RATE_LIMIT = 5
FEEDBACK_RATE_WINDOW_HOURS = 1


@router.post(
    "",
    response_model=FeedbackResponse,
    summary="Submit feedback",
    description="Submit a feature request or problem report. Rate limited to 5/hour.",
    responses={
        200: {"description": "Feedback submitted successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
    },
)
@handle_api_errors("submit feedback")
async def submit_feedback(
    request: Request,
    body: FeedbackCreate,
    user: dict[str, Any] = Depends(get_current_user),
    user_agent: str | None = Header(None, alias="User-Agent"),
    referer: str | None = Header(None, alias="Referer"),
) -> FeedbackResponse:
    """Submit feedback (feature request or problem report).

    For problem reports, can optionally auto-attach context (tier, URL, etc.)
    """
    user_id = user["user_id"]

    # Check rate limit
    recent_count = feedback_repository.get_user_recent_count(
        user_id, hours=FEEDBACK_RATE_WINDOW_HOURS
    )
    if recent_count >= FEEDBACK_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"You can submit up to {FEEDBACK_RATE_LIMIT} feedback items per hour. Please try again later.",
            },
        )

    # Build context for problem reports (if requested)
    context = None
    if body.type == FeedbackType.PROBLEM_REPORT and body.include_context:
        tier = get_effective_tier(user_id)
        context = {
            "user_tier": tier,
            "page_url": referer,
            "user_agent": user_agent,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Analyze feedback with Haiku (sentiment + themes)
    analysis_dict = None
    try:
        analysis = await analyze_feedback(body.title, body.description)
        if analysis:
            analysis_dict = analysis.to_dict()
            logger.debug(
                f"Feedback analyzed: sentiment={analysis.sentiment.value} themes={analysis.themes}"
            )
    except Exception as e:
        # Don't fail submission if analysis fails
        logger.warning(f"Feedback analysis failed (will store without): {e}")

    # Create feedback
    feedback = feedback_repository.create_feedback(
        user_id=user_id,
        feedback_type=body.type,
        title=body.title,
        description=body.description,
        context=context,
        analysis=analysis_dict,
    )

    logger.info(f"Feedback submitted: type={body.type} user={user_id} title='{body.title[:30]}...'")

    return FeedbackResponse(**feedback)
