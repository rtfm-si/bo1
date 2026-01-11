"""API routes for objective data requirements.

Provides endpoints for the "What Data Do I Need?" feature that helps users
understand what data they should collect to analyze specific objectives.

Endpoints:
- GET /api/v1/objectives/{objective_id}/data-requirements - Requirements for specific objective
- GET /api/v1/objectives/data-requirements - Requirements for all active objectives
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.analysis.prompts.data_requirements import (
    DATA_REQUIREMENTS_SYSTEM_PROMPT,
    build_data_requirements_prompt,
    parse_data_requirements_response,
)
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error
from bo1.models.dataset_objective_analysis import (
    DataPriority,
    DataRequirements,
    DataSource,
    EssentialData,
    ValuableAddition,
)
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/objectives", tags=["objectives"])


# --- Response Models ---


class ObjectiveSummary(BaseModel):
    """Summary of an objective with its index identifier."""

    index: int = Field(..., description="Objective index (0-based)")
    name: str = Field(..., description="Objective text")
    has_progress: bool = Field(default=False, description="Whether progress tracking is set")
    current_value: str | None = Field(None, description="Current progress value if set")
    target_value: str | None = Field(None, description="Target value if set")


class ObjectiveDataRequirementsResponse(BaseModel):
    """Response for data requirements for a specific objective."""

    objective: ObjectiveSummary = Field(..., description="The objective being analyzed")
    requirements: DataRequirements = Field(..., description="Data requirements for this objective")
    generated_at: datetime = Field(..., description="When requirements were generated")
    model_used: str = Field(..., description="LLM model used for generation")


class ObjectiveRequirementsSummary(BaseModel):
    """Summary of data requirements for one objective."""

    index: int = Field(..., description="Objective index")
    name: str = Field(..., description="Objective text")
    requirements_summary: str = Field(..., description="Brief summary of data needs")
    essential_data_count: int = Field(..., description="Number of essential data types needed")


class AllObjectivesRequirementsResponse(BaseModel):
    """Response for data requirements across all objectives."""

    objectives: list[ObjectiveRequirementsSummary] = Field(
        default_factory=list, description="Summary for each objective"
    )
    count: int = Field(..., description="Number of objectives")
    north_star_goal: str | None = Field(None, description="User's north star goal if set")


# --- Helper Functions ---


def _get_user_context(user_id: str) -> dict[str, Any] | None:
    """Fetch user's business context from repository."""
    return user_repository.get_context(user_id)


def _get_objective_by_index(
    context_data: dict[str, Any], objective_index: int
) -> tuple[str, dict[str, Any] | None]:
    """Get objective text and progress by index.

    Args:
        context_data: User's business context
        objective_index: 0-based index of the objective

    Returns:
        Tuple of (objective_text, progress_data or None)

    Raises:
        HTTPException: If objective not found
    """
    objectives = context_data.get("strategic_objectives") or []
    if objective_index < 0 or objective_index >= len(objectives):
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            f"Objective at index {objective_index} not found",
            status=404,
        )

    objective_text = objectives[objective_index]
    progress_data = (context_data.get("strategic_objectives_progress") or {}).get(
        str(objective_index)
    )

    return objective_text, progress_data


async def _generate_data_requirements(
    objective_name: str,
    objective_description: str | None = None,
    target_value: str | None = None,
    current_value: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> tuple[DataRequirements, str]:
    """Generate data requirements using LLM.

    Args:
        objective_name: Name/text of the objective
        objective_description: Optional description
        target_value: Target to achieve
        current_value: Current progress
        industry: User's industry
        business_model: User's business model

    Returns:
        Tuple of (DataRequirements, model_used)
    """
    client = ClaudeClient()

    prompt = build_data_requirements_prompt(
        objective_name=objective_name,
        objective_description=objective_description,
        target_value=target_value,
        current_value=current_value,
        industry=industry,
        business_model=business_model,
    )

    response = await client.generate(
        system_prompt=DATA_REQUIREMENTS_SYSTEM_PROMPT,
        user_prompt=prompt,
        max_tokens=2000,
        temperature=0.3,
    )

    # Parse response
    parsed = parse_data_requirements_response(response.content)

    # Convert to Pydantic model
    requirements = DataRequirements(
        objective_summary=parsed.get("objective_summary", ""),
        essential_data=[
            EssentialData(
                name=e.get("name", ""),
                description=e.get("description", ""),
                example_columns=e.get("example_columns", []),
                why_essential=e.get("why_essential", ""),
                questions_answered=e.get("questions_answered", []),
            )
            for e in parsed.get("essential_data", [])
        ],
        valuable_additions=[
            ValuableAddition(
                name=v.get("name", ""),
                description=v.get("description", ""),
                insight_unlocked=v.get("insight_unlocked", ""),
                priority=DataPriority(v.get("priority", "medium").lower()),
            )
            for v in parsed.get("valuable_additions", [])
        ],
        data_sources=[
            DataSource(
                source_type=s.get("source_type", ""),
                example_tools=s.get("example_tools", []),
                typical_export_name=s.get("typical_export_name", ""),
                columns_typically_included=s.get("columns_typically_included", []),
            )
            for s in parsed.get("data_sources", [])
        ],
        analysis_preview=parsed.get("analysis_preview", ""),
    )

    return requirements, response.model


# --- Endpoints ---

# IMPORTANT: Static routes MUST be defined before parameterized routes.
# FastAPI matches routes in definition order, so /data-requirements must come
# before /{objective_index}/data-requirements to avoid "data-requirements" being
# captured as a path parameter value.


@router.get(
    "/data-requirements",
    response_model=AllObjectivesRequirementsResponse,
    summary="Get data requirements overview for all objectives",
    description="""
    Returns a summary of data requirements for all active objectives.

    This provides an overview of what data would help across all goals,
    without generating full requirements for each (which would be expensive).
    Use the /{objective_index}/data-requirements endpoint for full details.
    """,
)
@handle_api_errors("get all objectives data requirements")
async def get_all_data_requirements(
    include_summaries: bool = Query(
        True, description="Include brief requirement summaries (adds latency)"
    ),
    user: dict = Depends(get_current_user),
) -> AllObjectivesRequirementsResponse:
    """Returns data requirements overview for all active objectives."""
    user_id = extract_user_id(user)

    # Fetch user context
    context_data = _get_user_context(user_id)
    if not context_data:
        return AllObjectivesRequirementsResponse(objectives=[], count=0, north_star_goal=None)

    objectives = context_data.get("strategic_objectives") or []
    north_star = context_data.get("north_star_goal")

    # Build summaries for each objective
    result = []
    for idx, objective_text in enumerate(objectives):
        # Simple heuristic-based summary without LLM call
        summary = _generate_quick_requirements_summary(objective_text)

        result.append(
            ObjectiveRequirementsSummary(
                index=idx,
                name=objective_text,
                requirements_summary=summary,
                essential_data_count=_estimate_essential_data_count(objective_text),
            )
        )

    return AllObjectivesRequirementsResponse(
        objectives=result,
        count=len(result),
        north_star_goal=north_star,
    )


@router.get(
    "/{objective_index}/data-requirements",
    response_model=ObjectiveDataRequirementsResponse,
    summary="Get data requirements for specific objective",
    description="""
    Returns detailed data requirements for analyzing a specific objective.

    This endpoint is called from the upload page when a user selects an objective
    in the "What Data Do I Need?" flow. It explains what data types are essential,
    what would be valuable additions, and where to find this data.

    The objective_index is 0-based, matching the order in strategic_objectives.
    """,
)
@handle_api_errors("get objective data requirements")
async def get_data_requirements(
    objective_index: int,
    user: dict = Depends(get_current_user),
) -> ObjectiveDataRequirementsResponse:
    """Returns data requirements for analyzing a specific objective."""
    user_id = extract_user_id(user)

    # Fetch user context
    context_data = _get_user_context(user_id)
    if not context_data:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "No business context found. Please set up your context first.",
            status=404,
        )

    # Get objective
    objective_text, progress_data = _get_objective_by_index(context_data, objective_index)

    # Extract progress values if available
    current_value = None
    target_value = None
    if progress_data:
        current_value = progress_data.get("current")
        target_value = progress_data.get("target")

    # Get business context for better requirements
    industry = context_data.get("industry")
    business_model = context_data.get("business_model")

    # Generate requirements using LLM
    try:
        requirements, model_used = await _generate_data_requirements(
            objective_name=objective_text,
            target_value=target_value,
            current_value=current_value,
            industry=industry,
            business_model=business_model,
        )
    except ValueError as e:
        log_error(
            logger,
            ErrorCode.LLM_PARSE_ERROR,
            f"Failed to parse data requirements: {e}",
            user_id=user_id,
            objective_index=objective_index,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            "Failed to generate data requirements. Please try again.",
            status=500,
        ) from None
    except Exception as e:
        log_error(
            logger,
            ErrorCode.LLM_REQUEST_ERROR,
            f"Failed to generate data requirements: {e}",
            user_id=user_id,
            objective_index=objective_index,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            "Failed to generate data requirements. Please try again.",
            status=500,
        ) from None

    return ObjectiveDataRequirementsResponse(
        objective=ObjectiveSummary(
            index=objective_index,
            name=objective_text,
            has_progress=progress_data is not None,
            current_value=current_value,
            target_value=target_value,
        ),
        requirements=requirements,
        generated_at=datetime.utcnow(),
        model_used=model_used,
    )


def _generate_quick_requirements_summary(objective_text: str) -> str:
    """Generate a quick summary of data requirements without LLM.

    Uses keyword matching to provide a basic summary.
    """
    text_lower = objective_text.lower()

    # Common objective patterns and their data needs
    if any(word in text_lower for word in ["churn", "retention", "retain"]):
        return "Customer activity data, subscription/purchase history, and status indicators"
    elif any(word in text_lower for word in ["revenue", "mrr", "arr", "sales"]):
        return "Transaction data with amounts, dates, and customer identifiers"
    elif any(word in text_lower for word in ["cost", "expense", "spending"]):
        return "Expense records with categories, amounts, and dates"
    elif any(word in text_lower for word in ["conversion", "funnel", "signup"]):
        return "User journey data with stage transitions and timestamps"
    elif any(word in text_lower for word in ["satisfaction", "nps", "csat"]):
        return "Survey responses, feedback data, and customer identifiers"
    elif any(word in text_lower for word in ["growth", "expand", "scale"]):
        return "Historical metrics data with time series for trend analysis"
    elif any(word in text_lower for word in ["efficiency", "productivity"]):
        return "Process/operational data with timing and resource usage"
    else:
        return "Relevant business metrics with identifiers and timestamps"


def _estimate_essential_data_count(objective_text: str) -> int:
    """Estimate number of essential data types needed.

    Simple heuristic based on objective complexity.
    """
    text_lower = objective_text.lower()

    # More complex objectives need more data types
    if any(word in text_lower for word in ["churn", "retention"]):
        return 4  # Customer ID, activity, status, dates
    elif any(word in text_lower for word in ["revenue", "sales"]):
        return 3  # Transaction, amount, date
    elif any(word in text_lower for word in ["conversion", "funnel"]):
        return 4  # User ID, stages, timestamps, outcomes
    else:
        return 3  # Default minimum
