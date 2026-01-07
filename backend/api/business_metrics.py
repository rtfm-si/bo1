"""Business metrics API endpoints (Layer 3 context).

Provides:
- GET /api/v1/business-metrics - Get user's metrics with templates
- GET /api/v1/business-metrics/templates - Get metric templates
- PUT /api/v1/business-metrics/{key} - Update a metric value
- POST /api/v1/business-metrics - Create a custom metric
- DELETE /api/v1/business-metrics/{key} - Delete a custom metric
- POST /api/v1/business-metrics/initialize - Initialize predefined metrics
"""

import asyncio
import logging
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2 import DatabaseError, OperationalError
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories.metrics_repository import metrics_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["business-metrics"])


# =============================================================================
# Enums and Models
# =============================================================================


class MetricCategory(str, Enum):
    """Metric category types."""

    FINANCIAL = "financial"
    GROWTH = "growth"
    RETENTION = "retention"
    EFFICIENCY = "efficiency"
    CUSTOM = "custom"


class MetricSource(str, Enum):
    """Source of metric value."""

    MANUAL = "manual"
    CLARIFICATION = "clarification"
    INTEGRATION = "integration"


class MetricTemplate(BaseModel):
    """Predefined metric template."""

    metric_key: str = Field(..., description="Unique metric identifier")
    name: str = Field(..., description="Display name")
    definition: str = Field(..., description="What this metric measures")
    importance: str = Field(..., description="Why this metric matters")
    category: MetricCategory = Field(..., description="Metric category")
    value_unit: str = Field(..., description="Unit of measurement ($, %, months, ratio)")
    display_order: int = Field(..., description="Sort order")
    applies_to: list[str] = Field(..., description="Business models this applies to")
    priority: int = Field(2, description="Priority level (1=high, 2=medium, 3=low)")


class UserMetric(BaseModel):
    """User's metric with value."""

    id: str = Field(..., description="Metric record ID")
    user_id: str = Field(..., description="User ID")
    metric_key: str = Field(..., description="Unique metric identifier")
    name: str = Field(..., description="Display name")
    definition: str | None = Field(None, description="What this metric measures")
    importance: str | None = Field(None, description="Why this metric matters")
    category: MetricCategory | None = Field(None, description="Metric category")
    value: float | None = Field(None, description="Current value")
    value_unit: str | None = Field(None, description="Unit of measurement")
    captured_at: str | None = Field(None, description="When value was captured")
    source: MetricSource = Field(MetricSource.MANUAL, description="Source of value")
    is_predefined: bool = Field(False, description="Based on template")
    is_relevant: bool = Field(True, description="Whether metric is relevant to user")
    display_order: int = Field(0, description="Sort order")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class MetricsResponse(BaseModel):
    """Response containing user metrics and unfilled templates."""

    metrics: list[UserMetric] = Field(..., description="User's saved metrics")
    templates: list[MetricTemplate] = Field(..., description="Unfilled template metrics")
    hidden_metrics: list[UserMetric] = Field(
        default_factory=list, description="Hidden/dismissed metrics (is_relevant=false)"
    )


class UpdateMetricRequest(BaseModel):
    """Request to update a metric value."""

    value: float | None = Field(None, description="New metric value")
    source: MetricSource = Field(MetricSource.MANUAL, description="Source of value")


class CreateMetricRequest(BaseModel):
    """Request to create a custom metric."""

    metric_key: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique metric key (lowercase, underscores)",
    )
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    definition: str | None = Field(None, max_length=500, description="What it measures")
    importance: str | None = Field(None, max_length=500, description="Why it matters")
    category: MetricCategory = Field(MetricCategory.CUSTOM, description="Metric category")
    value_unit: str = Field(..., max_length=20, description="Unit ($, %, etc)")
    value: float | None = Field(None, description="Initial value")


class SetRelevanceRequest(BaseModel):
    """Request to set metric relevance."""

    is_relevant: bool = Field(..., description="Whether metric is relevant to user")


# =============================================================================
# Helper Functions
# =============================================================================


def _format_metric(metric: dict[str, Any]) -> dict[str, Any]:
    """Format a metric record for API response."""
    return {
        "id": str(metric.get("id", "")),
        "user_id": metric.get("user_id", ""),
        "metric_key": metric.get("metric_key", ""),
        "name": metric.get("name", ""),
        "definition": metric.get("definition"),
        "importance": metric.get("importance"),
        "category": metric.get("category"),
        "value": float(metric["value"]) if metric.get("value") is not None else None,
        "value_unit": metric.get("value_unit"),
        "captured_at": (metric["captured_at"].isoformat() if metric.get("captured_at") else None),
        "source": metric.get("source", "manual"),
        "is_predefined": metric.get("is_predefined", False),
        "is_relevant": metric.get("is_relevant", True),
        "display_order": metric.get("display_order", 0),
        "created_at": (metric["created_at"].isoformat() if metric.get("created_at") else ""),
        "updated_at": (metric["updated_at"].isoformat() if metric.get("updated_at") else ""),
    }


def _format_template(template: dict[str, Any]) -> dict[str, Any]:
    """Format a template record for API response."""
    return {
        "metric_key": template.get("metric_key", ""),
        "name": template.get("name", ""),
        "definition": template.get("definition", ""),
        "importance": template.get("importance", ""),
        "category": template.get("category", ""),
        "value_unit": template.get("value_unit", ""),
        "display_order": template.get("display_order", 0),
        "applies_to": template.get("applies_to", ["all"]),
        "priority": template.get("priority", 2),
    }


def detect_business_model_from_context(user_id: str) -> str | None:
    """Detect business model from user's BusinessContext.

    Maps user-provided business_model text to template filter keys.
    Returns None if no context or unrecognized model.

    Args:
        user_id: User identifier

    Returns:
        Normalized business model key (saas, ecommerce, d2c, marketplace) or None
    """
    from bo1.state.repositories import user_repository

    try:
        context = user_repository.get_context(user_id)
        if not context:
            return None

        business_model = context.get("business_model")
        if not business_model:
            return None

        # Normalize text to lowercase for matching
        model_lower = business_model.lower().strip()

        # Map common variations to standard keys
        # SaaS variants
        if any(
            term in model_lower
            for term in ["saas", "software as a service", "subscription software"]
        ):
            return "saas"

        # E-commerce / D2C variants
        if any(
            term in model_lower
            for term in ["d2c", "direct to consumer", "direct-to-consumer", "dtc"]
        ):
            return "d2c"

        if any(
            term in model_lower for term in ["ecommerce", "e-commerce", "online store", "retail"]
        ):
            return "ecommerce"

        # Marketplace variants
        if any(term in model_lower for term in ["marketplace", "two-sided", "platform"]):
            return "marketplace"

        # Service/agency variants
        if any(term in model_lower for term in ["agency", "consulting", "service", "freelance"]):
            return "service"

        # No recognized model - return None to show all templates
        return None

    except Exception as e:
        logger.warning(f"Failed to detect business model for {user_id}: {e}")
        return None


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/v1/business-metrics",
    response_model=MetricsResponse,
    summary="Get user's business metrics with templates",
    description="""
    Get the authenticated user's saved business metrics along with unfilled template metrics.

    Returns:
    - metrics: User's saved metrics with values (relevant only by default)
    - templates: Predefined metrics not yet saved (for display/initialization), ordered by priority
    - hidden_metrics: Metrics marked as not relevant (only when include_irrelevant=true)

    If business_model is not passed, auto-detects from user's BusinessContext.
    Templates are ordered by priority (1=high first) then display_order.
    """,
)
@handle_api_errors("get metrics")
async def get_metrics(
    business_model: str | None = Query(
        None,
        description="Filter templates by business model. Auto-detected from context if not provided.",
        examples=["saas", "ecommerce", "d2c"],
    ),
    include_irrelevant: bool = Query(
        False,
        description="Include hidden/irrelevant metrics in response",
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> MetricsResponse:
    """Get user's metrics with templates."""
    try:
        user_id = extract_user_id(user)

        # Auto-detect business model from context if not explicitly passed
        effective_model = business_model
        if effective_model is None:
            effective_model = detect_business_model_from_context(user_id)
            if effective_model:
                logger.debug(f"Auto-detected business model '{effective_model}' for user {user_id}")

        result = metrics_repository.get_metrics_with_templates(
            user_id, effective_model, include_irrelevant=include_irrelevant
        )

        return MetricsResponse(
            metrics=[_format_metric(m) for m in result["metrics"]],
            templates=[_format_template(t) for t in result["templates"]],
            hidden_metrics=[_format_metric(m) for m in result.get("hidden_metrics", [])],
        )

    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Database error getting metrics: {e}",
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.DB_QUERY_ERROR, "Database error while retrieving metrics", status=500
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error getting metrics: {e}",
            exc_info=True,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to get metrics: {str(e)}", status=500
        ) from e


@router.get(
    "/v1/business-metrics/templates",
    response_model=list[MetricTemplate],
    summary="Get metric templates",
    description="""
    Get predefined metric templates, optionally filtered by business model.

    Templates include standard SaaS metrics like MRR, CAC, Churn, etc.
    """,
)
@handle_api_errors("get templates")
async def get_templates(
    business_model: str | None = Query(
        None,
        description="Filter by business model",
        examples=["saas", "ecommerce"],
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[MetricTemplate]:
    """Get metric templates."""
    try:
        templates = metrics_repository.get_templates(business_model)
        return [_format_template(t) for t in templates]

    except (DatabaseError, OperationalError) as e:
        log_error(logger, ErrorCode.DB_QUERY_ERROR, f"Database error getting templates: {e}")
        raise http_error(
            ErrorCode.DB_QUERY_ERROR, "Database error while retrieving templates", status=500
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error getting templates: {e}",
            exc_info=True,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to get templates: {str(e)}", status=500
        ) from e


@router.put(
    "/v1/business-metrics/{metric_key}",
    response_model=UserMetric,
    summary="Update a metric value",
    description="""
    Update the value of an existing metric.

    If the metric doesn't exist but is a predefined template, it will be created
    with the template defaults and the provided value.
    """,
)
@handle_api_errors("update metric")
async def update_metric(
    metric_key: str,
    request: UpdateMetricRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserMetric:
    """Update a metric value."""
    try:
        user_id = extract_user_id(user)

        # Check if metric exists
        existing = metrics_repository.get_user_metric(user_id, metric_key)

        if existing:
            # Update existing
            result = metrics_repository.update_metric_value(
                user_id=user_id,
                metric_key=metric_key,
                value=Decimal(str(request.value)) if request.value is not None else None,
                source=request.source.value,
            )
            if not result:
                raise http_error(ErrorCode.API_NOT_FOUND, "Metric not found", status=404)
        else:
            # Check if it's a template
            template = metrics_repository.get_template(metric_key)
            if not template:
                raise http_error(
                    ErrorCode.API_NOT_FOUND,
                    f"Metric '{metric_key}' not found. Create it first with POST /v1/business-metrics",
                    status=404,
                )

            # Create from template
            result = metrics_repository.save_metric(
                user_id=user_id,
                metric_key=metric_key,
                value=Decimal(str(request.value)) if request.value is not None else None,
                source=request.source.value,
                is_predefined=True,
            )

        logger.info(f"Updated metric {metric_key} for user {user_id}")
        return _format_metric(result)

    except HTTPException:
        raise
    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Database error updating metric: {e}",
            user_id=user_id,
            metric_key=metric_key,
        )
        raise http_error(
            ErrorCode.DB_WRITE_ERROR, "Database error while updating metric", status=500
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error updating metric: {e}",
            exc_info=True,
            user_id=user_id,
            metric_key=metric_key,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to update metric: {str(e)}", status=500
        ) from e


@router.patch(
    "/v1/business-metrics/{metric_key}/relevance",
    response_model=UserMetric,
    summary="Set metric relevance",
    description="""
    Set whether a predefined metric is relevant to the user.

    Setting is_relevant=false hides the metric from the default view but keeps
    it recoverable. Only works for predefined metrics - use DELETE for custom metrics.
    """,
)
@handle_api_errors("set metric relevance")
async def set_metric_relevance(
    metric_key: str,
    request: SetRelevanceRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserMetric:
    """Set metric relevance (show/hide)."""
    try:
        user_id = extract_user_id(user)

        # Check if it exists
        existing = metrics_repository.get_user_metric(user_id, metric_key)
        if not existing:
            raise http_error(ErrorCode.API_NOT_FOUND, "Metric not found", status=404)

        if not existing.get("is_predefined"):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "Cannot set relevance for custom metrics. Use DELETE instead.",
                status=400,
            )

        result = metrics_repository.set_metric_relevance(
            user_id=user_id,
            metric_key=metric_key,
            is_relevant=request.is_relevant,
        )

        if not result:
            raise http_error(
                ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to update metric", status=500
            )

        logger.info(
            f"Set metric {metric_key} relevance to {request.is_relevant} for user {user_id}"
        )
        return _format_metric(result)

    except HTTPException:
        raise
    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Database error setting metric relevance: {e}",
            user_id=user_id,
            metric_key=metric_key,
        )
        raise http_error(
            ErrorCode.DB_WRITE_ERROR, "Database error while updating metric", status=500
        ) from e
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error setting metric relevance: {e}",
            exc_info=True,
            user_id=user_id,
            metric_key=metric_key,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to update metric: {str(e)}", status=500
        ) from e


@router.post(
    "/v1/business-metrics",
    response_model=UserMetric,
    status_code=201,
    summary="Create a custom metric",
    description="""
    Create a new custom metric.

    Use this for business-specific metrics not covered by templates.
    The metric_key must be unique and follow the pattern: lowercase letters,
    numbers, and underscores only.
    """,
)
@handle_api_errors("create metric")
async def create_metric(
    request: CreateMetricRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserMetric:
    """Create a custom metric."""
    try:
        user_id = extract_user_id(user)

        # Check for conflicts with templates
        template = metrics_repository.get_template(request.metric_key)
        if template:
            raise http_error(
                ErrorCode.API_CONFLICT,
                f"Metric key '{request.metric_key}' conflicts with predefined template. "
                "Use PUT /v1/business-metrics/{key} to set its value instead.",
                status=409,
            )

        # Check for existing user metric
        existing = metrics_repository.get_user_metric(user_id, request.metric_key)
        if existing:
            raise http_error(
                ErrorCode.API_CONFLICT,
                f"Metric '{request.metric_key}' already exists",
                status=409,
            )

        # Create the metric
        result = metrics_repository.save_metric(
            user_id=user_id,
            metric_key=request.metric_key,
            value=Decimal(str(request.value)) if request.value is not None else None,
            name=request.name,
            definition=request.definition,
            importance=request.importance,
            category=request.category.value,
            value_unit=request.value_unit,
            is_predefined=False,
        )

        logger.info(f"Created custom metric {request.metric_key} for user {user_id}")
        return _format_metric(result)

    except HTTPException:
        raise
    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Database error creating metric: {e}",
            user_id=user_id,
            metric_key=request.metric_key,
        )
        raise http_error(
            ErrorCode.DB_WRITE_ERROR, "Database error while creating metric", status=500
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error creating metric: {e}",
            exc_info=True,
            user_id=user_id,
            metric_key=request.metric_key,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to create metric: {str(e)}", status=500
        ) from e


@router.delete(
    "/v1/business-metrics/{metric_key}",
    response_model=dict[str, str],
    summary="Delete a custom metric",
    description="""
    Delete a custom metric.

    Predefined metrics cannot be deleted - their values can only be cleared
    by setting value to null via PUT.
    """,
)
@handle_api_errors("delete metric")
async def delete_metric(
    metric_key: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a custom metric."""
    try:
        user_id = extract_user_id(user)

        # Check if it exists and is custom
        existing = metrics_repository.get_user_metric(user_id, metric_key)
        if not existing:
            raise http_error(ErrorCode.API_NOT_FOUND, "Metric not found", status=404)

        if existing.get("is_predefined"):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "Cannot delete predefined metrics. Set value to null instead.",
                status=400,
            )

        deleted = metrics_repository.delete_metric(user_id, metric_key)
        if not deleted:
            raise http_error(ErrorCode.API_NOT_FOUND, "Metric not found", status=404)

        logger.info(f"Deleted metric {metric_key} for user {user_id}")
        return {"status": "deleted"}

    except HTTPException:
        raise
    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Database error deleting metric: {e}",
            user_id=user_id,
            metric_key=metric_key,
        )
        raise http_error(
            ErrorCode.DB_WRITE_ERROR, "Database error while deleting metric", status=500
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error deleting metric: {e}",
            exc_info=True,
            user_id=user_id,
            metric_key=metric_key,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to delete metric: {str(e)}", status=500
        ) from e


@router.post(
    "/v1/business-metrics/initialize",
    response_model=list[UserMetric],
    summary="Initialize predefined metrics",
    description="""
    Initialize all predefined metrics for the user with null values.

    This creates metric entries from templates so they appear in the user's
    metric list. Useful for onboarding - creates all applicable metrics
    based on business model.

    Skips metrics that already exist.
    """,
)
@handle_api_errors("initialize metrics")
async def initialize_metrics(
    business_model: str | None = Query(
        None,
        description="Filter templates by business model",
        examples=["saas"],
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[UserMetric]:
    """Initialize predefined metrics from templates."""
    try:
        user_id = extract_user_id(user)

        metrics = metrics_repository.initialize_predefined_metrics(user_id, business_model)

        logger.info(f"Initialized {len(metrics)} metrics for user {user_id}")
        return [_format_metric(m) for m in metrics]

    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Database error initializing metrics: {e}",
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.DB_WRITE_ERROR, "Database error while initializing metrics", status=500
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error initializing metrics: {e}",
            exc_info=True,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to initialize metrics: {str(e)}", status=500
        ) from e
