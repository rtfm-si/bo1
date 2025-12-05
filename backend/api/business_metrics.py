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
from backend.api.utils.errors import handle_api_errors
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
    display_order: int = Field(0, description="Sort order")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class MetricsResponse(BaseModel):
    """Response containing user metrics and unfilled templates."""

    metrics: list[UserMetric] = Field(..., description="User's saved metrics")
    templates: list[MetricTemplate] = Field(..., description="Unfilled template metrics")


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
    }


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
    - metrics: User's saved metrics with values
    - templates: Predefined metrics not yet saved (for display/initialization)

    Optionally filter templates by business model (saas, ecommerce, marketplace).
    """,
)
@handle_api_errors("get metrics")
async def get_metrics(
    business_model: str | None = Query(
        None,
        description="Filter templates by business model",
        examples=["saas", "ecommerce"],
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> MetricsResponse:
    """Get user's metrics with templates."""
    try:
        user_id = extract_user_id(user)

        result = metrics_repository.get_metrics_with_templates(user_id, business_model)

        return MetricsResponse(
            metrics=[_format_metric(m) for m in result["metrics"]],
            templates=[_format_template(t) for t in result["templates"]],
        )

    except (DatabaseError, OperationalError) as e:
        logger.error(f"Database error getting metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving metrics",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error getting metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}",
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
        logger.error(f"Database error getting templates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving templates",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error getting templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get templates: {str(e)}",
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
                raise HTTPException(status_code=404, detail="Metric not found")
        else:
            # Check if it's a template
            template = metrics_repository.get_template(metric_key)
            if not template:
                raise HTTPException(
                    status_code=404,
                    detail=f"Metric '{metric_key}' not found. Create it first with POST /v1/business-metrics",
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
        logger.error(f"Database error updating metric: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while updating metric",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error updating metric: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update metric: {str(e)}",
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
            raise HTTPException(
                status_code=409,
                detail=f"Metric key '{request.metric_key}' conflicts with predefined template. "
                "Use PUT /v1/business-metrics/{key} to set its value instead.",
            )

        # Check for existing user metric
        existing = metrics_repository.get_user_metric(user_id, request.metric_key)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Metric '{request.metric_key}' already exists",
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
        logger.error(f"Database error creating metric: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while creating metric",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error creating metric: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create metric: {str(e)}",
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
            raise HTTPException(status_code=404, detail="Metric not found")

        if existing.get("is_predefined"):
            raise HTTPException(
                status_code=400,
                detail="Cannot delete predefined metrics. Set value to null instead.",
            )

        deleted = metrics_repository.delete_metric(user_id, metric_key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Metric not found")

        logger.info(f"Deleted metric {metric_key} for user {user_id}")
        return {"status": "deleted"}

    except HTTPException:
        raise
    except (DatabaseError, OperationalError) as e:
        logger.error(f"Database error deleting metric: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while deleting metric",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error deleting metric: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete metric: {str(e)}",
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
        logger.error(f"Database error initializing metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while initializing metrics",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error initializing metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize metrics: {str(e)}",
        ) from e
