"""Admin A/B experiment management endpoints.

Provides:
- Experiment CRUD
- Lifecycle management (start/pause/conclude)
- Variant assignment lookup
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services import experiments as exp_service
from bo1.logging.errors import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experiments", tags=["admin-experiments"])


# ==============================================================================
# Models
# ==============================================================================


class VariantModel(BaseModel):
    """Experiment variant."""

    name: str = Field(..., description="Variant name", examples=["control", "treatment"])
    weight: int = Field(50, ge=0, le=100, description="Variant weight (0-100)", examples=[50])


class ExperimentCreate(BaseModel):
    """Request to create an experiment."""

    name: str = Field(..., description="Unique experiment name", examples=["persona_count_test"])
    description: str | None = Field(None, description="Experiment description")
    variants: list[VariantModel] | None = Field(
        None,
        description="Variants (default: control/treatment 50/50)",
        examples=[[{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}]],
    )
    metrics: list[str] | None = Field(
        None,
        description="Metrics to track",
        examples=[["conversion_rate", "time_to_decision"]],
    )


class ExperimentUpdate(BaseModel):
    """Request to update an experiment (draft only)."""

    description: str | None = Field(None, description="New description")
    variants: list[VariantModel] | None = Field(None, description="New variants")
    metrics: list[str] | None = Field(None, description="New metrics")


class ExperimentResponse(BaseModel):
    """Experiment response."""

    id: str = Field(..., description="Experiment UUID")
    name: str = Field(..., description="Experiment name")
    description: str | None = Field(None, description="Description")
    status: str = Field(..., description="Status: draft, running, paused, concluded")
    variants: list[VariantModel] = Field(..., description="Variants")
    metrics: list[str] = Field(..., description="Metrics to track")
    start_date: str | None = Field(None, description="When experiment started (ISO 8601)")
    end_date: str | None = Field(None, description="When experiment concluded (ISO 8601)")
    created_at: str = Field(..., description="Created timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Updated timestamp (ISO 8601)")


class ExperimentListResponse(BaseModel):
    """List of experiments."""

    experiments: list[ExperimentResponse]
    total: int


class VariantAssignmentResponse(BaseModel):
    """Variant assignment response."""

    experiment_name: str
    user_id: str
    variant: str | None = Field(None, description="Assigned variant or null if not running")


def _to_response(exp: exp_service.Experiment) -> ExperimentResponse:
    """Convert experiment to response model."""
    return ExperimentResponse(
        id=str(exp.id),
        name=exp.name,
        description=exp.description,
        status=exp.status,
        variants=[VariantModel(name=v.name, weight=v.weight) for v in exp.variants],
        metrics=exp.metrics,
        start_date=exp.start_date.isoformat() if exp.start_date else None,
        end_date=exp.end_date.isoformat() if exp.end_date else None,
        created_at=exp.created_at.isoformat(),
        updated_at=exp.updated_at.isoformat(),
    )


# ==============================================================================
# Endpoints
# ==============================================================================


@router.get(
    "",
    response_model=ExperimentListResponse,
    summary="List experiments",
    description="Get all experiments, optionally filtered by status.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list experiments")
async def list_experiments(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    status: str | None = Query(None, description="Filter by status"),
) -> ExperimentListResponse:
    """List all experiments."""
    experiments = exp_service.list_experiments(status=status)
    return ExperimentListResponse(
        experiments=[_to_response(e) for e in experiments],
        total=len(experiments),
    )


@router.post(
    "",
    response_model=ExperimentResponse,
    summary="Create experiment",
    description="Create a new experiment in draft status.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create experiment")
async def create_experiment(
    request: Request,
    body: ExperimentCreate,
    _admin: dict = Depends(require_admin_any),
) -> ExperimentResponse:
    """Create a new experiment."""
    try:
        variants = (
            [{"name": v.name, "weight": v.weight} for v in body.variants] if body.variants else None
        )
        experiment = exp_service.create_experiment(
            name=body.name,
            description=body.description,
            variants=variants,
            metrics=body.metrics,
        )
        return _to_response(experiment)
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from None


@router.get(
    "/{experiment_id}",
    response_model=ExperimentResponse,
    summary="Get experiment",
    description="Get experiment details by ID.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get experiment")
async def get_experiment(
    request: Request,
    experiment_id: UUID,
    _admin: dict = Depends(require_admin_any),
) -> ExperimentResponse:
    """Get experiment by ID."""
    experiment = exp_service.get_experiment(experiment_id)
    if not experiment:
        raise http_error(ErrorCode.API_NOT_FOUND, "Experiment not found", status=404)
    return _to_response(experiment)


@router.patch(
    "/{experiment_id}",
    response_model=ExperimentResponse,
    summary="Update experiment",
    description="Update experiment (draft status only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update experiment")
async def update_experiment(
    request: Request,
    experiment_id: UUID,
    body: ExperimentUpdate,
    _admin: dict = Depends(require_admin_any),
) -> ExperimentResponse:
    """Update experiment (draft only)."""
    try:
        variants = (
            [{"name": v.name, "weight": v.weight} for v in body.variants] if body.variants else None
        )
        experiment = exp_service.update_experiment(
            experiment_id=experiment_id,
            description=body.description,
            variants=variants,
            metrics=body.metrics,
        )
        if not experiment:
            raise http_error(ErrorCode.API_NOT_FOUND, "Experiment not found", status=404)
        return _to_response(experiment)
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from None


@router.delete(
    "/{experiment_id}",
    summary="Delete experiment",
    description="Delete experiment (draft status only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete experiment")
async def delete_experiment(
    request: Request,
    experiment_id: UUID,
    _admin: dict = Depends(require_admin_any),
) -> dict:
    """Delete experiment (draft only)."""
    try:
        deleted = exp_service.delete_experiment(experiment_id)
        if not deleted:
            raise http_error(ErrorCode.API_NOT_FOUND, "Experiment not found", status=404)
        return {"status": "deleted", "id": str(experiment_id)}
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from None


@router.post(
    "/{experiment_id}/start",
    response_model=ExperimentResponse,
    summary="Start experiment",
    description="Start a draft or paused experiment.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("start experiment")
async def start_experiment(
    request: Request,
    experiment_id: UUID,
    _admin: dict = Depends(require_admin_any),
) -> ExperimentResponse:
    """Start experiment."""
    try:
        experiment = exp_service.start_experiment(experiment_id)
        if not experiment:
            raise http_error(ErrorCode.API_NOT_FOUND, "Experiment not found", status=404)
        return _to_response(experiment)
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from None


@router.post(
    "/{experiment_id}/pause",
    response_model=ExperimentResponse,
    summary="Pause experiment",
    description="Pause a running experiment.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("pause experiment")
async def pause_experiment(
    request: Request,
    experiment_id: UUID,
    _admin: dict = Depends(require_admin_any),
) -> ExperimentResponse:
    """Pause experiment."""
    try:
        experiment = exp_service.pause_experiment(experiment_id)
        if not experiment:
            raise http_error(ErrorCode.API_NOT_FOUND, "Experiment not found", status=404)
        return _to_response(experiment)
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from None


@router.post(
    "/{experiment_id}/conclude",
    response_model=ExperimentResponse,
    summary="Conclude experiment",
    description="Conclude an experiment (terminal state).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("conclude experiment")
async def conclude_experiment(
    request: Request,
    experiment_id: UUID,
    _admin: dict = Depends(require_admin_any),
) -> ExperimentResponse:
    """Conclude experiment."""
    try:
        experiment = exp_service.conclude_experiment(experiment_id)
        if not experiment:
            raise http_error(ErrorCode.API_NOT_FOUND, "Experiment not found", status=404)
        return _to_response(experiment)
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from None


@router.get(
    "/{experiment_name}/variant/{user_id}",
    response_model=VariantAssignmentResponse,
    summary="Get user variant",
    description="Get the variant a user is assigned to in an experiment.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get user variant")
async def get_user_variant(
    request: Request,
    experiment_name: str,
    user_id: str,
    _admin: dict = Depends(require_admin_any),
) -> VariantAssignmentResponse:
    """Get user's assigned variant."""
    variant = exp_service.get_user_variant(experiment_name, user_id)
    return VariantAssignmentResponse(
        experiment_name=experiment_name,
        user_id=user_id,
        variant=variant,
    )
