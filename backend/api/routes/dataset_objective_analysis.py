"""API routes for dataset objective analysis.

Provides endpoints for the objective-aligned dataset analysis feature that
connects data analysis to user business objectives.

Endpoints:
- POST /api/v1/datasets/{dataset_id}/analyze - Trigger full analysis pipeline
- GET /api/v1/datasets/{dataset_id}/objective-analysis - Get analysis results
- POST /api/v1/datasets/{dataset_id}/question - Ask objective-aware question
"""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode, log_error
from bo1.models.dataset_objective_analysis import (
    AnalysisMode,
    DataStory,
    Insight,
    RelevanceAssessment,
)
from bo1.state.repositories import user_repository
from bo1.state.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])

# Repository instance
dataset_repository = DatasetRepository()


# --- Request/Response Models ---


class AnalyzeRequest(BaseModel):
    """Request to trigger dataset analysis."""

    include_context: bool = Field(
        default=True, description="Whether to fetch business context for analysis"
    )
    objective_id: str | None = Field(
        None, description="Pre-selected objective index from 'What Data Do I Need?' flow"
    )
    force_mode: str | None = Field(
        None,
        description="Force analysis mode: 'objective_focused' or 'open_exploration' (auto-detect if None)",
    )


class AnalyzeResponse(BaseModel):
    """Response from triggering analysis."""

    analysis_id: str = Field(..., description="UUID of the analysis")
    analysis_mode: str = Field(..., description="Mode used: objective_focused or open_exploration")
    relevance_score: int | None = Field(None, description="Relevance to objectives (0-100)")
    status: str = Field(default="completed", description="Analysis status")


class ObjectiveAnalysisResponse(BaseModel):
    """Full objective analysis results."""

    id: str = Field(..., description="Analysis UUID")
    dataset_id: str = Field(..., description="Dataset UUID")
    analysis_mode: str = Field(..., description="Analysis mode used")
    relevance_score: int | None = Field(None, description="Relevance score 0-100")
    relevance_assessment: RelevanceAssessment | None = Field(
        None, description="Full relevance assessment"
    )
    data_story: DataStory | None = Field(None, description="Generated data narrative")
    insights: list[Insight] = Field(default_factory=list, description="Generated insights")
    created_at: datetime = Field(..., description="Analysis creation time")


class QuestionRequest(BaseModel):
    """Request to ask a question about the dataset."""

    question: str = Field(..., min_length=1, max_length=2000, description="Question to ask")
    conversation_id: str | None = Field(None, description="Continue existing conversation")
    include_chart: bool = Field(default=True, description="Include visualization in response")


class QuestionResponse(BaseModel):
    """Response to a dataset question."""

    answer: str = Field(..., description="Answer narrative in markdown")
    chart_spec: dict[str, Any] | None = Field(None, description="Chart configuration if applicable")
    relevant_objectives: list[str] = Field(
        default_factory=list, description="Objective indices this relates to"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list, description="Suggested follow-up questions"
    )
    conversation_id: str = Field(..., description="Conversation ID for continuity")
    confidence: str = Field(default="medium", description="Confidence level: high/medium/low")


# --- Helper Functions ---


def _get_dataset_or_404(dataset_id: str, user_id: str) -> dict[str, Any]:
    """Fetch dataset and verify ownership.

    Raises:
        HTTPException: If dataset not found
    """
    dataset = dataset_repository.get_by_id(dataset_id, user_id)
    if not dataset:
        raise http_error(ErrorCode.API_NOT_FOUND, "Dataset not found", status=404)
    return dataset


def _get_user_context(user_id: str) -> dict[str, Any] | None:
    """Fetch user's business context from repository."""
    return user_repository.get_context(user_id)


def _determine_analysis_mode(
    relevance_score: int | None,
    force_mode: str | None,
    selected_objective_id: str | None,
) -> AnalysisMode:
    """Determine which analysis mode to use.

    Args:
        relevance_score: Relevance assessment score (0-100)
        force_mode: User-specified mode override
        selected_objective_id: Pre-selected objective from "What Data Do I Need?" flow

    Returns:
        AnalysisMode enum value
    """
    # User forced a specific mode
    if force_mode:
        if force_mode == "objective_focused":
            return AnalysisMode.OBJECTIVE_FOCUSED
        elif force_mode == "open_exploration":
            return AnalysisMode.OPEN_EXPLORATION

    # Pre-selected objective means objective-focused
    if selected_objective_id is not None:
        return AnalysisMode.OBJECTIVE_FOCUSED

    # Auto-detect based on relevance score
    # High relevance (70+) -> objective focused
    # Low relevance (<70) -> open exploration
    if relevance_score is not None and relevance_score >= 70:
        return AnalysisMode.OBJECTIVE_FOCUSED

    return AnalysisMode.OPEN_EXPLORATION


# --- Endpoints ---


@router.post(
    "/{dataset_id}/analyze",
    response_model=AnalyzeResponse,
    summary="Trigger objective-aligned analysis",
    description="""
    Triggers the full analysis pipeline for a dataset.

    The pipeline:
    1. Fetches user's business context (objectives, north star)
    2. Assesses dataset relevance to objectives
    3. Generates objective-aligned or open exploration insights
    4. Compiles a data story narrative

    Analysis mode is determined by:
    - Pre-selected objective (from "What Data Do I Need?" flow) -> objective_focused
    - High relevance score (70+) -> objective_focused
    - Low relevance or no context -> open_exploration
    - force_mode parameter overrides auto-detection
    """,
)
@handle_api_errors("analyze dataset for objectives")
async def analyze_dataset(
    dataset_id: str,
    body: AnalyzeRequest | None = None,
    user: dict = Depends(get_current_user),
) -> AnalyzeResponse:
    """Triggers full analysis pipeline for a dataset."""
    user_id = extract_user_id(user)

    # Use defaults if no body provided
    if body is None:
        body = AnalyzeRequest()

    # Verify dataset exists and user has access
    _get_dataset_or_404(dataset_id, user_id)

    # Fetch business context if requested
    context_data = None
    if body.include_context:
        context_data = _get_user_context(user_id)

    # Check for existing analysis (may be used for cache invalidation later)
    _ = dataset_repository.get_objective_analysis(dataset_id, user_id)

    # TODO: Phase 1 - Implement full pipeline in bo1/analysis/pipeline.py
    # For now, create a placeholder analysis record

    # Determine analysis mode
    # In full implementation, this would come from relevance assessment
    relevance_score = None
    if context_data and context_data.get("strategic_objectives"):
        # Placeholder: would be calculated by relevance assessment
        relevance_score = 65  # Default to medium relevance

    analysis_mode = _determine_analysis_mode(
        relevance_score=relevance_score,
        force_mode=body.force_mode,
        selected_objective_id=body.objective_id,
    )

    # Generate analysis ID
    analysis_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Create analysis record
    # TODO: Replace with actual pipeline execution
    analysis_data = {
        "id": analysis_id,
        "dataset_id": dataset_id,
        "user_id": user_id,
        "analysis_mode": analysis_mode.value,
        "relevance_score": relevance_score,
        "relevance_assessment": None,  # TODO: Generate with LLM
        "data_story": None,  # TODO: Generate with LLM
        "insights": [],  # TODO: Generate with LLM
        "context_snapshot": context_data,
        "selected_objective_id": body.objective_id,
        "created_at": now,
        "updated_at": now,
    }

    # Save analysis (or update existing)
    saved_analysis = dataset_repository.save_objective_analysis(analysis_data)

    return AnalyzeResponse(
        analysis_id=saved_analysis["id"],
        analysis_mode=analysis_mode.value,
        relevance_score=relevance_score,
        status="completed",
    )


@router.get(
    "/{dataset_id}/objective-analysis",
    response_model=ObjectiveAnalysisResponse,
    summary="Get objective analysis results",
    description="""
    Returns the objective analysis results for a dataset.

    Includes:
    - Relevance assessment (score and objective matches)
    - Data story (narrative with objective sections)
    - Individual insights linked to objectives

    Returns 404 if no analysis has been run yet.
    """,
)
@handle_api_errors("get objective analysis")
async def get_objective_analysis(
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> ObjectiveAnalysisResponse:
    """Returns objective analysis results including relevance and data story."""
    user_id = extract_user_id(user)

    # Verify dataset exists
    _ = _get_dataset_or_404(dataset_id, user_id)

    # Fetch analysis
    analysis_data = dataset_repository.get_objective_analysis(dataset_id, user_id)
    if not analysis_data:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "No objective analysis found. Run POST /analyze first.",
            status=404,
        )

    # Parse stored data into Pydantic models
    relevance_assessment = None
    if analysis_data.get("relevance_assessment"):
        relevance_assessment = RelevanceAssessment.model_validate(
            analysis_data["relevance_assessment"]
        )

    data_story = None
    if analysis_data.get("data_story"):
        data_story = DataStory.model_validate(analysis_data["data_story"])

    insights = []
    if analysis_data.get("insights"):
        insights = [Insight.model_validate(i) for i in analysis_data["insights"]]

    return ObjectiveAnalysisResponse(
        id=analysis_data["id"],
        dataset_id=analysis_data["dataset_id"],
        analysis_mode=analysis_data["analysis_mode"],
        relevance_score=analysis_data.get("relevance_score"),
        relevance_assessment=relevance_assessment,
        data_story=data_story,
        insights=insights,
        created_at=analysis_data["created_at"],
    )


@router.post(
    "/{dataset_id}/question",
    response_model=QuestionResponse,
    summary="Ask objective-aware question",
    description="""
    Ask a question about the dataset with objective-aware response.

    The response:
    - Answers in plain business language
    - Connects to relevant objectives when applicable
    - Includes visualization if helpful
    - Suggests follow-up questions
    - Maintains conversation context for multi-turn Q&A

    This endpoint returns JSON directly. For streaming responses,
    use the existing /ask endpoint with SSE.
    """,
)
@handle_api_errors("ask objective question")
async def ask_objective_question(
    dataset_id: str,
    body: QuestionRequest,
    user: dict = Depends(get_current_user),
) -> QuestionResponse:
    """Ask a question with objective-aware response."""
    user_id = extract_user_id(user)

    # Verify dataset exists
    _get_dataset_or_404(dataset_id, user_id)

    # Get or create conversation ID
    conversation_id = body.conversation_id or str(uuid.uuid4())

    # Fetch user context for objective awareness (used when full pipeline implemented)
    _ = _get_user_context(user_id)

    # TODO: Phase 1 - Implement conversation prompt with objective context
    # For now, return placeholder response

    # Placeholder response
    return QuestionResponse(
        answer=f"Analysis of your question: '{body.question}'\n\n"
        "*(Full implementation pending - will connect to conversation prompt with objective context)*",
        chart_spec=None,
        relevant_objectives=[],
        follow_up_questions=[
            "What patterns do you see in this data?",
            "How does this compare to previous periods?",
        ],
        conversation_id=conversation_id,
        confidence="medium",
    )


@router.post(
    "/{dataset_id}/question/stream",
    summary="Ask question with streaming response",
    description="""
    Ask a question about the dataset with SSE streaming response.

    Streams the response as Server-Sent Events for real-time display.
    Includes thinking indicators, partial responses, and final answer.

    Event types:
    - thinking: Status update during processing
    - partial: Partial response chunk
    - chart: Chart specification (if include_chart=true)
    - complete: Final response with metadata
    - error: Error occurred
    """,
)
@handle_api_errors("ask objective question stream")
async def ask_objective_question_stream(
    dataset_id: str,
    body: QuestionRequest,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Ask a question with SSE streaming response."""
    user_id = extract_user_id(user)

    # Verify dataset exists
    _get_dataset_or_404(dataset_id, user_id)

    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate SSE stream for question response."""
        try:
            # Emit thinking status
            yield f"event: thinking\ndata: {json.dumps({'status': 'analyzing_question'})}\n\n"

            # Get or create conversation ID
            conversation_id = body.conversation_id or str(uuid.uuid4())

            # TODO: Implement actual streaming response with LLM
            # For now, emit placeholder response

            yield f"event: thinking\ndata: {json.dumps({'status': 'generating_response'})}\n\n"

            # Placeholder response
            response_data = {
                "answer": f"Analysis of your question: '{body.question}'\n\n"
                "*(Streaming implementation pending)*",
                "relevant_objectives": [],
                "follow_up_questions": [
                    "What patterns do you see?",
                    "How does this compare to expectations?",
                ],
                "conversation_id": conversation_id,
                "confidence": "medium",
            }

            yield f"event: complete\ndata: {json.dumps(response_data)}\n\n"

        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Question stream error: {e}",
                user_id=user_id,
                dataset_id=dataset_id,
            )
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
