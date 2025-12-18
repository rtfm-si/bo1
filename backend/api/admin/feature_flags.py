"""Admin feature flag endpoints.

Provides admin-only endpoints for:
- Listing all feature flags
- Creating, updating, and deleting flags
- Managing per-user overrides

All endpoints require admin authentication.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.auth_helpers import require_admin_role
from backend.api.utils.errors import handle_api_errors
from backend.services import feature_flags as ff

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-flags", tags=["admin"])


# Request/Response models


class FeatureFlagItem(BaseModel):
    """Feature flag item."""

    id: str = Field(..., description="Flag UUID")
    name: str = Field(..., description="Unique flag name")
    description: str | None = Field(None, description="Flag description")
    enabled: bool = Field(..., description="Global enabled state")
    rollout_pct: int = Field(..., ge=0, le=100, description="Rollout percentage")
    tiers: list[str] = Field(default_factory=list, description="Allowed tiers")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class FeatureFlagListResponse(BaseModel):
    """Response for listing feature flags."""

    flags: list[FeatureFlagItem] = Field(..., description="List of flags")
    count: int = Field(..., description="Total flag count")


class CreateFeatureFlagRequest(BaseModel):
    """Request to create a feature flag."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique flag name")
    description: str | None = Field(None, max_length=500, description="Description")
    enabled: bool = Field(False, description="Global enabled state")
    rollout_pct: int = Field(100, ge=0, le=100, description="Rollout percentage")
    tiers: list[str] = Field(default_factory=list, description="Allowed tiers")


class UpdateFeatureFlagRequest(BaseModel):
    """Request to update a feature flag."""

    description: str | None = Field(None, max_length=500, description="Description")
    enabled: bool | None = Field(None, description="Global enabled state")
    rollout_pct: int | None = Field(None, ge=0, le=100, description="Rollout percentage")
    tiers: list[str] | None = Field(None, description="Allowed tiers")


class SetUserOverrideRequest(BaseModel):
    """Request to set a user override."""

    user_id: str = Field(..., description="User ID")
    enabled: bool = Field(..., description="Override value")


class UserOverrideResponse(BaseModel):
    """Response for user override operations."""

    flag_name: str = Field(..., description="Flag name")
    user_id: str = Field(..., description="User ID")
    enabled: bool = Field(..., description="Override value")


class DeleteOverrideRequest(BaseModel):
    """Request to delete a user override."""

    user_id: str = Field(..., description="User ID")


def _flag_to_item(flag: ff.FeatureFlag) -> FeatureFlagItem:
    """Convert service flag to API item."""
    return FeatureFlagItem(
        id=str(flag.id),
        name=flag.name,
        description=flag.description,
        enabled=flag.enabled,
        rollout_pct=flag.rollout_pct,
        tiers=flag.tiers,
        created_at=flag.created_at.isoformat(),
        updated_at=flag.updated_at.isoformat(),
    )


@router.get(
    "",
    response_model=FeatureFlagListResponse,
    summary="List all feature flags (admin only)",
    responses={
        200: {"description": "Flags retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list feature flags")
async def list_flags(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FeatureFlagListResponse:
    """List all feature flags.

    Args:
        request: FastAPI request object
        current_user: Current authenticated user

    Returns:
        List of all feature flags
    """
    require_admin_role(current_user)

    flags = ff.get_all_flags()
    items = [_flag_to_item(f) for f in flags]

    return FeatureFlagListResponse(flags=items, count=len(items))


@router.post(
    "",
    response_model=FeatureFlagItem,
    summary="Create a feature flag (admin only)",
    responses={
        200: {"description": "Flag created successfully"},
        400: {"description": "Flag already exists", "model": ErrorResponse},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create feature flag")
async def create_flag(
    request: Request,
    body: CreateFeatureFlagRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FeatureFlagItem:
    """Create a new feature flag.

    Args:
        request: FastAPI request object
        body: Flag creation request
        current_user: Current authenticated user

    Returns:
        Created flag
    """
    require_admin_role(current_user)

    try:
        flag = ff.create_flag(
            name=body.name,
            description=body.description,
            enabled=body.enabled,
            rollout_pct=body.rollout_pct,
            tiers=body.tiers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    logger.info("Admin %s created feature flag: %s", current_user.get("id"), body.name)
    return _flag_to_item(flag)


@router.get(
    "/{name}",
    response_model=FeatureFlagItem,
    summary="Get a feature flag (admin only)",
    responses={
        200: {"description": "Flag retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
        404: {"description": "Flag not found", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feature flag")
async def get_flag(
    request: Request,
    name: str = Path(..., description="Flag name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FeatureFlagItem:
    """Get a feature flag by name.

    Args:
        request: FastAPI request object
        name: Flag name
        current_user: Current authenticated user

    Returns:
        Feature flag
    """
    require_admin_role(current_user)

    flag = ff.get_flag(name)
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{name}' not found")

    return _flag_to_item(flag)


@router.patch(
    "/{name}",
    response_model=FeatureFlagItem,
    summary="Update a feature flag (admin only)",
    responses={
        200: {"description": "Flag updated successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
        404: {"description": "Flag not found", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update feature flag")
async def update_flag(
    request: Request,
    body: UpdateFeatureFlagRequest,
    name: str = Path(..., description="Flag name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FeatureFlagItem:
    """Update a feature flag.

    Args:
        request: FastAPI request object
        body: Update request
        name: Flag name
        current_user: Current authenticated user

    Returns:
        Updated flag
    """
    require_admin_role(current_user)

    flag = ff.update_flag(
        name=name,
        description=body.description,
        enabled=body.enabled,
        rollout_pct=body.rollout_pct,
        tiers=body.tiers,
    )

    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{name}' not found")

    logger.info("Admin %s updated feature flag: %s", current_user.get("id"), name)
    return _flag_to_item(flag)


@router.delete(
    "/{name}",
    summary="Delete a feature flag (admin only)",
    responses={
        200: {"description": "Flag deleted successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
        404: {"description": "Flag not found", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete feature flag")
async def delete_flag(
    request: Request,
    name: str = Path(..., description="Flag name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a feature flag.

    Args:
        request: FastAPI request object
        name: Flag name
        current_user: Current authenticated user

    Returns:
        Success message
    """
    require_admin_role(current_user)

    deleted = ff.delete_flag(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Flag '{name}' not found")

    logger.info("Admin %s deleted feature flag: %s", current_user.get("id"), name)
    return {"message": f"Flag '{name}' deleted"}


@router.post(
    "/{name}/override",
    response_model=UserOverrideResponse,
    summary="Set user override (admin only)",
    responses={
        200: {"description": "Override set successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
        404: {"description": "Flag not found", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("set user override")
async def set_override(
    request: Request,
    body: SetUserOverrideRequest,
    name: str = Path(..., description="Flag name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserOverrideResponse:
    """Set a per-user override for a flag.

    Args:
        request: FastAPI request object
        body: Override request
        name: Flag name
        current_user: Current authenticated user

    Returns:
        Override confirmation
    """
    require_admin_role(current_user)

    success = ff.set_user_override(name, body.user_id, body.enabled)
    if not success:
        raise HTTPException(status_code=404, detail=f"Flag '{name}' not found")

    logger.info(
        "Admin %s set override for flag %s, user %s: %s",
        current_user.get("id"),
        name,
        body.user_id,
        body.enabled,
    )

    return UserOverrideResponse(flag_name=name, user_id=body.user_id, enabled=body.enabled)


@router.delete(
    "/{name}/override",
    summary="Delete user override (admin only)",
    responses={
        200: {"description": "Override deleted successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
        404: {"description": "Flag or override not found", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete user override")
async def delete_override(
    request: Request,
    body: DeleteOverrideRequest,
    name: str = Path(..., description="Flag name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a per-user override for a flag.

    Args:
        request: FastAPI request object
        body: Override delete request
        name: Flag name
        current_user: Current authenticated user

    Returns:
        Success message
    """
    require_admin_role(current_user)

    deleted = ff.delete_user_override(name, body.user_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Override not found for flag '{name}', user '{body.user_id}'",
        )

    logger.info(
        "Admin %s deleted override for flag %s, user %s",
        current_user.get("id"),
        name,
        body.user_id,
    )

    return {"message": f"Override deleted for flag '{name}', user '{body.user_id}'"}
