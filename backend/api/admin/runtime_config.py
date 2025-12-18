"""Admin runtime config endpoints.

Provides admin-only endpoints for emergency configuration toggles:
- GET /api/admin/runtime-config - list all overrides with effective values
- PATCH /api/admin/runtime-config/{key} - set override value
- DELETE /api/admin/runtime-config/{key} - clear override (revert to env var)

All changes are audit logged.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.models import ErrorResponse
from backend.api.utils.auth_helpers import require_admin_role
from backend.api.utils.errors import handle_api_errors
from backend.services import runtime_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime-config", tags=["admin"])


# Request/Response models


class RuntimeConfigItem(BaseModel):
    """Single runtime config item."""

    key: str = Field(..., description="Config key name")
    override_value: bool | None = Field(None, description="Current override (None if not set)")
    default_value: bool | None = Field(None, description="Value from env/settings")
    effective_value: bool | None = Field(None, description="Value that will be used")
    is_overridden: bool = Field(..., description="True if override is active")


class RuntimeConfigResponse(BaseModel):
    """Response for listing runtime config."""

    items: list[RuntimeConfigItem] = Field(..., description="Config items")
    count: int = Field(..., description="Number of configurable items")


class UpdateRuntimeConfigRequest(BaseModel):
    """Request to set runtime config override."""

    value: bool = Field(..., description="Override value to set")


@router.get(
    "",
    response_model=RuntimeConfigResponse,
    summary="List runtime config overrides (admin only)",
    responses={
        200: {"description": "Config retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("list runtime config")
async def list_runtime_config(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RuntimeConfigResponse:
    """List all runtime config items with override status.

    Returns:
        All configurable items with their current/default/effective values
    """
    require_admin_role(current_user)

    overrides = runtime_config.get_all_overrides()
    items = [
        RuntimeConfigItem(
            key=v["key"],
            override_value=v["override_value"],
            default_value=v["default_value"],
            effective_value=v["effective_value"],
            is_overridden=v["is_overridden"],
        )
        for v in overrides.values()
    ]

    return RuntimeConfigResponse(items=items, count=len(items))


@router.patch(
    "/{key}",
    response_model=RuntimeConfigItem,
    summary="Set runtime config override (admin only)",
    responses={
        200: {"description": "Override set successfully"},
        400: {"description": "Invalid key or value", "model": ErrorResponse},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("set runtime config")
async def set_runtime_config(
    request: UpdateRuntimeConfigRequest,
    key: str = Path(..., description="Config key name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RuntimeConfigItem:
    """Set runtime config override.

    This immediately changes the effective value for all requests.
    Use to emergency-disable security features without restart.

    Args:
        request: Override value to set
        key: Config key name (must be whitelisted)
        current_user: Current authenticated user

    Returns:
        Updated config item
    """
    require_admin_role(current_user)

    # Validate key is allowed
    if key not in runtime_config.ALLOWED_OVERRIDES:
        raise HTTPException(
            status_code=400,
            detail=f"Key '{key}' is not configurable. Allowed keys: {list(runtime_config.ALLOWED_OVERRIDES.keys())}",
        )

    # Set the override
    success = runtime_config.set_override(key, request.value)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to set override. Check Redis connectivity.",
        )

    # Audit log
    logger.warning(
        "ADMIN_RUNTIME_CONFIG_CHANGE: admin=%s key=%s value=%s",
        current_user.get("id"),
        key,
        request.value,
    )

    # Return updated state
    overrides = runtime_config.get_all_overrides()
    item = overrides[key]

    return RuntimeConfigItem(
        key=item["key"],
        override_value=item["override_value"],
        default_value=item["default_value"],
        effective_value=item["effective_value"],
        is_overridden=item["is_overridden"],
    )


@router.delete(
    "/{key}",
    response_model=RuntimeConfigItem,
    summary="Clear runtime config override (admin only)",
    responses={
        200: {"description": "Override cleared successfully"},
        400: {"description": "Invalid key", "model": ErrorResponse},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("clear runtime config")
async def clear_runtime_config(
    key: str = Path(..., description="Config key name"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RuntimeConfigItem:
    """Clear runtime config override (revert to env var).

    Args:
        key: Config key name
        current_user: Current authenticated user

    Returns:
        Updated config item (now using default value)
    """
    require_admin_role(current_user)

    # Validate key is allowed
    if key not in runtime_config.ALLOWED_OVERRIDES:
        raise HTTPException(
            status_code=400,
            detail=f"Key '{key}' is not configurable. Allowed keys: {list(runtime_config.ALLOWED_OVERRIDES.keys())}",
        )

    # Clear the override
    success = runtime_config.clear_override(key)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to clear override. Check Redis connectivity.",
        )

    # Audit log
    logger.warning(
        "ADMIN_RUNTIME_CONFIG_CLEAR: admin=%s key=%s",
        current_user.get("id"),
        key,
    )

    # Return updated state
    overrides = runtime_config.get_all_overrides()
    item = overrides[key]

    return RuntimeConfigItem(
        key=item["key"],
        override_value=item["override_value"],
        default_value=item["default_value"],
        effective_value=item["effective_value"],
        is_overridden=item["is_overridden"],
    )
