"""FastAPI router for context metric endpoints.

Provides:
- GET  /v1/context/metric-suggestions - Get metric suggestions from insights
- POST /v1/context/apply-metric-suggestion - Apply a metric suggestion
- GET  /v1/context/metrics/calculable - List calculable metrics
- GET  /v1/context/metrics/{metric_key}/questions - Get calculation questions
- POST /v1/context/metrics/{metric_key}/calculate - Calculate a metric from Q&A
- GET  /v1/context/metrics/suggestions - Get business metric suggestions
- POST /v1/context/metrics/suggestions/apply - Apply a business metric suggestion
- POST /v1/context/metrics/suggestions/dismiss - Dismiss a business metric suggestion
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from backend.api.context.models import (
    ApplyBusinessMetricSuggestionRequest,
    ApplyBusinessMetricSuggestionResponse,
    ApplyMetricSuggestionRequest,
    ApplyMetricSuggestionResponse,
    AvailableMetricsResponse,
    BusinessMetricSuggestion,
    BusinessMetricSuggestionsResponse,
    DismissBusinessMetricSuggestionRequest,
    MetricCalculationRequest,
    MetricCalculationResponse,
    MetricFormulaResponse,
    MetricQuestionDef,
    MetricSuggestion,
    MetricSuggestionsResponse,
)
from backend.api.context.services import (
    CATEGORY_TO_FIELD_MAPPING,
    append_benchmark_history,
    get_metrics_from_insights,
    update_benchmark_timestamps,
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
    "/v1/context/metric-suggestions",
    response_model=MetricSuggestionsResponse,
    summary="Get metric suggestions from insights",
    description="""
    Get suggestions for auto-populating context metrics from clarification insights.

    Analyzes user's clarification answers (from meetings) and extracts metric data
    that could be used to populate context fields like revenue, customers, growth_rate,
    and team_size.

    **Filtering:**
    - Only insights with confidence >= 0.6 are suggested
    - Only insights from the last 90 days are considered
    - Suggestions are deduplicated per field (highest confidence wins)
    - Suggestions matching current values are excluded

    **Use Cases:**
    - Show "Suggested from insights" panel on key-metrics page
    - Help users keep context metrics in sync with their meeting data
    """,
    responses={
        200: {
            "description": "Suggestions retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "suggestions": [
                            {
                                "field": "revenue",
                                "current_value": "$45,000",
                                "suggested_value": "$50,000",
                                "source_question": "What's your current MRR?",
                                "confidence": 0.85,
                                "answered_at": "2025-12-28T10:30:00Z",
                            }
                        ],
                        "count": 1,
                    }
                }
            },
        },
        403: ERROR_403_RESPONSE,
    },
)
@handle_api_errors("get metric suggestions")
async def get_metric_suggestions(
    user: dict[str, Any] = Depends(get_current_user),
) -> MetricSuggestionsResponse:
    """Get metric suggestions from clarification insights."""
    user_id = extract_user_id(user)

    # Load context from database
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return MetricSuggestionsResponse(success=True, suggestions=[], count=0)

    # Get clarifications from context
    clarifications = context_data.get("clarifications", {})
    if not clarifications:
        return MetricSuggestionsResponse(success=True, suggestions=[], count=0)

    # Extract suggestions
    raw_suggestions = get_metrics_from_insights(clarifications, context_data)

    # Convert to response models
    suggestions = [
        MetricSuggestion(
            field=s["field"],
            current_value=s.get("current_value"),
            suggested_value=s["suggested_value"],
            source_question=s["source_question"],
            confidence=s["confidence"],
            answered_at=s.get("answered_at"),
        )
        for s in raw_suggestions
    ]

    logger.info(f"Found {len(suggestions)} metric suggestions for user {user_id}")

    return MetricSuggestionsResponse(
        success=True,
        suggestions=suggestions,
        count=len(suggestions),
    )


@router.post(
    "/v1/context/apply-metric-suggestion",
    response_model=ApplyMetricSuggestionResponse,
    summary="Apply a metric suggestion to context",
    description="""
    Apply a single metric suggestion to update the user's context.

    Updates the specified context field with the provided value. The source_question
    is recorded in benchmark_history metadata for audit trail.

    **Allowed Fields:**
    - revenue
    - customers
    - growth_rate
    - team_size

    **Use Cases:**
    - User clicks "Apply" on a suggestion in the key-metrics page
    - Bulk "Apply All" iterates through this endpoint
    """,
    responses={
        200: {
            "description": "Suggestion applied successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "field": "revenue",
                        "new_value": "$50,000",
                    }
                }
            },
        },
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
    },
)
@handle_api_errors("apply metric suggestion")
async def apply_metric_suggestion(
    request: ApplyMetricSuggestionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ApplyMetricSuggestionResponse:
    """Apply a metric suggestion to update context."""
    user_id = extract_user_id(user)

    # Validate field is allowed
    allowed_fields = set(CATEGORY_TO_FIELD_MAPPING.values())
    if request.field not in allowed_fields:
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            f"Field '{request.field}' not allowed. Must be one of: {', '.join(sorted(allowed_fields))}",
            status=400,
        )

    # Load existing context - save a copy BEFORE modifying for change detection
    context_data = user_repository.get_context(user_id) or {}
    existing_context = dict(context_data.items())  # shallow copy

    # Update the field
    context_data[request.field] = request.value

    # Update benchmark timestamps (compare new vs existing)
    context_data["benchmark_timestamps"] = update_benchmark_timestamps(
        context_data, existing_context
    )

    # Append to benchmark history with source tracking
    history = append_benchmark_history(context_data, existing_context)
    if history:
        context_data["benchmark_history"] = history
        # Add source metadata to latest entry
        if request.field in history and history[request.field]:
            latest = history[request.field][0]
            latest["source"] = "insight_suggestion"
            if request.source_question:
                latest["source_question"] = request.source_question[:200]

    # Save context (legacy dual-write for backward compat)
    user_repository.save_context(user_id, context_data)

    # Also upsert to business_metrics table (primary storage going forward)
    try:
        from backend.api.context.services import (
            CATEGORY_TO_METRIC_KEY,
            METRIC_DISPLAY_NAMES,
        )
        from bo1.state.repositories.metrics_repository import metrics_repository

        # Map field to metric_key via reverse lookup
        field_to_metric_key = {v: k for k, v in CATEGORY_TO_FIELD_MAPPING.items()}
        category = field_to_metric_key.get(request.field)
        if category and category in CATEGORY_TO_METRIC_KEY:
            metric_key = CATEGORY_TO_METRIC_KEY[category]
            if metric_key:
                # Try to parse numeric value
                value_str = str(request.value).replace("$", "").replace(",", "").replace("%", "")
                if value_str.endswith(("k", "K")):
                    numeric_val = float(value_str[:-1]) * 1000
                elif value_str.endswith(("m", "M")):
                    numeric_val = float(value_str[:-1]) * 1_000_000
                else:
                    try:
                        numeric_val = float(value_str)
                    except ValueError:
                        numeric_val = None

                if numeric_val is not None:
                    name = METRIC_DISPLAY_NAMES.get(
                        metric_key, metric_key.replace("_", " ").title()
                    )
                    metrics_repository.save_metric(
                        user_id=user_id,
                        metric_key=metric_key,
                        value=numeric_val,
                        name=name,
                        source="clarification",
                        is_predefined=False,
                    )
                    logger.debug(f"Synced metric {metric_key}={numeric_val} to business_metrics")
    except Exception as e:
        # Non-blocking: don't fail if business_metrics sync fails
        logger.warning(f"Failed to sync metric suggestion to business_metrics: {e}")

    logger.info(f"Applied metric suggestion for user {user_id}: {request.field}={request.value}")

    return ApplyMetricSuggestionResponse(
        success=True,
        field=request.field,
        new_value=request.value,
    )


# =============================================================================
# Metric Calculation Endpoints (Q&A-guided metric derivation)
# =============================================================================


@router.get(
    "/v1/context/metrics/calculable",
    response_model=AvailableMetricsResponse,
    summary="List metrics with calculation support",
    description="""
    Get a list of metric keys that have Q&A-guided calculation support.

    These metrics can be derived through guided questions rather than
    direct input of the final value.
    """,
    responses={
        200: {
            "description": "Available metrics listed",
            "content": {
                "application/json": {
                    "example": {
                        "metrics": [
                            "mrr",
                            "arr",
                            "churn",
                            "nps",
                            "cac",
                            "ltv",
                            "burn_rate",
                            "runway",
                        ]
                    }
                }
            },
        },
    },
)
async def get_calculable_metrics() -> AvailableMetricsResponse:
    """List metrics with calculation support."""
    from backend.api.context.metric_questions import get_available_metrics

    return AvailableMetricsResponse(metrics=get_available_metrics())


@router.get(
    "/v1/context/metrics/{metric_key}/questions",
    response_model=MetricFormulaResponse,
    summary="Get calculation questions for a metric",
    description="""
    Get the guided Q&A questions for calculating a specific metric.

    Returns a list of questions with input types (currency, number, percent)
    and help text to guide the user through deriving the metric value.
    """,
    responses={
        200: {
            "description": "Questions retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "metric_key": "churn",
                        "questions": [
                            {
                                "id": "customers_lost",
                                "question": "How many customers did you lose this month?",
                                "input_type": "number",
                                "placeholder": "5",
                                "help_text": "Customers who canceled or didn't renew",
                            },
                            {
                                "id": "customers_start",
                                "question": "How many customers did you have at the start of the month?",
                                "input_type": "number",
                                "placeholder": "100",
                                "help_text": "Total active customers at month start",
                            },
                        ],
                        "result_unit": "%",
                    }
                }
            },
        },
        404: ERROR_404_RESPONSE,
    },
)
async def get_metric_questions(metric_key: str) -> MetricFormulaResponse:
    """Get calculation questions for a metric."""
    from backend.api.context.metric_questions import get_metric_questions as get_questions

    formula = get_questions(metric_key)
    if not formula:
        raise http_error(
            code=ErrorCode.API_NOT_FOUND,
            message=f"No calculation support for metric: {metric_key}",
            status=404,
        )

    return MetricFormulaResponse(
        metric_key=metric_key,
        questions=[
            MetricQuestionDef(
                id=q["id"],
                question=q["question"],
                input_type=q["input_type"].value,
                placeholder=q["placeholder"],
                help_text=q.get("help_text"),
            )
            for q in formula["questions"]
        ],
        result_unit=formula["result_unit"],
    )


@router.post(
    "/v1/context/metrics/{metric_key}/calculate",
    response_model=MetricCalculationResponse,
    summary="Calculate a metric from Q&A answers",
    description="""
    Calculate a metric value from user-provided answers to guided questions.

    Optionally stores the Q&A answers as a ClarificationInsight with
    source_type="calculation" for future reference.

    **Process:**
    1. Validates all required answers are provided
    2. Applies the metric formula to calculate the value
    3. Optionally saves the calculation as an insight
    4. Returns the calculated value and formula used
    """,
    responses={
        200: {
            "description": "Metric calculated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "calculated_value": 5.0,
                        "formula_used": "(customers_lost / customers_start * 100)",
                        "result_unit": "%",
                        "confidence": 1.0,
                        "insight_saved": True,
                    }
                }
            },
        },
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@handle_api_errors("calculate metric")
async def calculate_metric(
    metric_key: str,
    request: MetricCalculationRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> MetricCalculationResponse:
    """Calculate a metric from Q&A answers."""
    from backend.api.context.metric_questions import (
        calculate_metric as calc_metric,
    )
    from backend.api.context.metric_questions import (
        get_metric_questions as get_questions,
    )

    user_id = extract_user_id(user)

    # Get formula definition
    formula = get_questions(metric_key)
    if not formula:
        raise http_error(
            code=ErrorCode.API_NOT_FOUND,
            message=f"No calculation support for metric: {metric_key}",
            status=404,
        )

    # Convert answers to dict
    answers_dict = {a.question_id: a.value for a in request.answers}

    # Calculate
    try:
        calculated_value, formula_used = calc_metric(metric_key, answers_dict)
    except ValueError as e:
        raise http_error(
            code=ErrorCode.VALIDATION_ERROR,
            message=str(e),
            status=400,
        ) from e

    insight_saved = False

    # Optionally save as insight
    if request.save_insight:
        try:
            # Build a summary of the calculation as the "answer"
            answer_parts = []
            for q in formula["questions"]:
                qid = q["id"]
                if qid in answers_dict:
                    answer_parts.append(f"{q['question']}: {answers_dict[qid]}")
            answer_summary = "; ".join(answer_parts)

            # Create the clarification entry
            from backend.api.context.models import (
                ClarificationStorageEntry,
                InsightCategory,
                InsightMetricResponse,
            )

            now = datetime.now(UTC)
            entry = ClarificationStorageEntry(
                answer=answer_summary,
                answered_at=now,
                source="calculation",
                metric_key=metric_key,
                category=InsightCategory.REVENUE
                if metric_key in ("mrr", "arr", "burn_rate", "runway", "gross_margin")
                else InsightCategory.CUSTOMERS
                if metric_key in ("churn", "nps", "cac", "ltv", "ltv_cac_ratio")
                else InsightCategory.GROWTH
                if metric_key in ("aov", "conversion_rate", "return_rate")
                else InsightCategory.UNCATEGORIZED,
                metric=InsightMetricResponse(
                    value=calculated_value,
                    unit=formula["result_unit"],
                    metric_type=metric_key,
                    raw_text=f"Calculated {metric_key}: {calculated_value}{formula['result_unit']}",
                ),
                confidence_score=1.0,
                summary=f"Calculated {metric_key} = {calculated_value}{formula['result_unit']}",
                parsed_at=now,
            )

            # Load and update clarifications
            context_data = user_repository.get_context(user_id) or {}
            clarifications = context_data.get("clarifications", {})

            # Use metric key as question key for calculation insights
            question_key = f"[Calculation] {metric_key.upper()}"
            clarifications[question_key] = entry.model_dump(mode="json")

            context_data["clarifications"] = clarifications
            user_repository.save_context(user_id, context_data)
            insight_saved = True

            logger.info(
                f"Saved metric calculation insight for user {user_id}: {metric_key}={calculated_value}"
            )

            # Trigger async market context enrichment
            industry = context_data.get("industry")
            if industry and metric_key:
                import asyncio

                asyncio.create_task(
                    _enrich_insight_background(
                        user_id=user_id,
                        question_key=question_key,
                        metric_key=metric_key,
                        metric_value=calculated_value,
                        industry=industry,
                    )
                )
        except Exception as e:
            # Non-blocking: log but don't fail
            logger.warning(f"Failed to save calculation insight: {e}")

    return MetricCalculationResponse(
        success=True,
        calculated_value=calculated_value,
        formula_used=formula_used,
        result_unit=formula["result_unit"],
        confidence=1.0,
        insight_saved=insight_saved,
    )


# =============================================================================
# Business Metric Insight Suggestion Endpoints
# =============================================================================


@router.get(
    "/v1/context/metrics/suggestions",
    response_model=BusinessMetricSuggestionsResponse,
    summary="Get business metric suggestions from insights",
    description="""
    Get suggestions for auto-populating business metrics from clarification insights.

    Uses keyword-based matching to detect metric values in user's clarification answers
    (from meetings and calculations) and map them to specific business metrics like
    MRR, churn, CAC, LTV, etc.

    **Matching factors:**
    - Category match (insight category → metric category)
    - Keyword presence in question/answer text
    - Value pattern extraction from text

    **Filtering:**
    - Only suggestions with confidence >= 0.5 are returned
    - Only insights from the last 90 days are considered
    - Suggestions matching current metric values are excluded
    - Dismissed suggestions are excluded

    **Use Cases:**
    - Show "Suggested from insights" panel on business metrics page
    - Help users keep metrics in sync with their meeting data
    """,
    responses={
        200: {
            "description": "Suggestions retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "suggestions": [
                            {
                                "metric_key": "mrr",
                                "metric_name": "Monthly Recurring Revenue",
                                "current_value": 45000,
                                "suggested_value": "$50,000",
                                "source_question": "What's your current MRR?",
                                "confidence": 0.85,
                                "answered_at": "2025-12-28T10:30:00Z",
                                "is_dismissed": False,
                            }
                        ],
                        "count": 1,
                    }
                }
            },
        },
        403: ERROR_403_RESPONSE,
    },
)
@handle_api_errors("get business metric suggestions")
async def get_business_metric_suggestions(
    user: dict[str, Any] = Depends(get_current_user),
) -> BusinessMetricSuggestionsResponse:
    """Get business metric suggestions from clarification insights."""
    from backend.api.context.metric_mapping import get_insight_metric_suggestions

    user_id = extract_user_id(user)

    # Load context from database
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return BusinessMetricSuggestionsResponse(success=True, suggestions=[], count=0)

    # Get clarifications from context
    clarifications = context_data.get("clarifications", {})
    if not clarifications:
        return BusinessMetricSuggestionsResponse(success=True, suggestions=[], count=0)

    # Get current metric values
    from bo1.state.repositories.metrics_repository import metrics_repository

    existing_metrics: dict[str, Any] = {}
    try:
        user_metrics = metrics_repository.get_business_metrics(user_id)
        for m in user_metrics:
            if m.get("value") is not None:
                existing_metrics[m["metric_key"]] = m["value"]
    except Exception as e:
        logger.warning(f"Failed to load user metrics: {e}")

    # Get dismissed suggestions from context
    dismissed = set(context_data.get("dismissed_metric_suggestions", []))

    # Extract suggestions
    raw_suggestions = get_insight_metric_suggestions(
        clarifications,
        existing_metrics,
        confidence_threshold=0.5,
        max_age_days=90,
    )

    # Get metric templates for names
    templates = metrics_repository.get_templates()
    template_names = {t["metric_key"]: t["name"] for t in templates}

    # Convert to response models, filtering dismissed
    suggestions = []
    for s in raw_suggestions:
        key = f"{s['metric_key']}:{s['source_question']}"
        if key in dismissed:
            continue

        suggestions.append(
            BusinessMetricSuggestion(
                metric_key=s["metric_key"],
                metric_name=template_names.get(s["metric_key"]),
                current_value=s.get("current_value"),
                suggested_value=str(s["suggested_value"]),
                source_question=s["source_question"],
                confidence=s["confidence"],
                answered_at=s.get("answered_at"),
                is_dismissed=False,
            )
        )

    logger.info(f"Found {len(suggestions)} business metric suggestions for user {user_id}")

    return BusinessMetricSuggestionsResponse(
        success=True,
        suggestions=suggestions,
        count=len(suggestions),
    )


@router.post(
    "/v1/context/metrics/suggestions/apply",
    response_model=ApplyBusinessMetricSuggestionResponse,
    summary="Apply a business metric suggestion",
    description="""
    Apply a business metric suggestion to update the metric value.

    Updates the specified business metric with the provided value. The source_question
    is recorded for audit trail.

    **Use Cases:**
    - User clicks "Apply" on a suggestion in the metrics page
    """,
    responses={
        200: {
            "description": "Suggestion applied successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "metric_key": "mrr",
                        "new_value": 50000,
                    }
                }
            },
        },
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@handle_api_errors("apply business metric suggestion")
async def apply_business_metric_suggestion(
    request: ApplyBusinessMetricSuggestionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ApplyBusinessMetricSuggestionResponse:
    """Apply a business metric suggestion."""
    from bo1.state.repositories.metrics_repository import metrics_repository

    user_id = extract_user_id(user)

    # Update the metric
    result = metrics_repository.update_metric_value(
        user_id=user_id,
        metric_key=request.metric_key,
        value=request.value,
        source="insight",
    )

    if not result:
        # Metric doesn't exist - try to create from template
        result = metrics_repository.save_metric(
            user_id=user_id,
            metric_key=request.metric_key,
            value=request.value,
            source="insight",
            is_predefined=True,
        )
        if not result:
            raise http_error(
                code=ErrorCode.API_NOT_FOUND,
                message=f"Metric not found and could not be created: {request.metric_key}",
                status=404,
            )

    logger.info(
        f"Applied business metric suggestion for user {user_id}: {request.metric_key}={request.value}"
    )

    return ApplyBusinessMetricSuggestionResponse(
        success=True,
        metric_key=request.metric_key,
        new_value=request.value,
    )


@router.post(
    "/v1/context/metrics/suggestions/dismiss",
    response_model=ApplyBusinessMetricSuggestionResponse,
    summary="Dismiss a business metric suggestion",
    description="""
    Dismiss a business metric suggestion to prevent it from appearing again.

    Stores the dismissal in user context. The suggestion can be un-dismissed by
    clearing dismissed suggestions.
    """,
    responses={
        200: {
            "description": "Suggestion dismissed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "metric_key": "mrr",
                        "new_value": 0,
                    }
                }
            },
        },
        403: ERROR_403_RESPONSE,
    },
)
@handle_api_errors("dismiss business metric suggestion")
async def dismiss_business_metric_suggestion(
    request: DismissBusinessMetricSuggestionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ApplyBusinessMetricSuggestionResponse:
    """Dismiss a business metric suggestion."""
    user_id = extract_user_id(user)

    # Load context
    context_data = user_repository.get_context(user_id) or {}

    # Add to dismissed set
    dismissed = set(context_data.get("dismissed_metric_suggestions", []))
    key = f"{request.metric_key}:{request.source_question}"
    dismissed.add(key)

    context_data["dismissed_metric_suggestions"] = list(dismissed)
    user_repository.save_context(user_id, context_data)

    logger.info(f"Dismissed business metric suggestion for user {user_id}: {request.metric_key}")

    return ApplyBusinessMetricSuggestionResponse(
        success=True,
        metric_key=request.metric_key,
        new_value=0,  # Placeholder
    )


# =============================================================================
# Private helpers
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
