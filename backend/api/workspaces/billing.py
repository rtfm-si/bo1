"""Workspace billing API routes.

Provides:
- POST /api/v1/workspaces/{id}/billing/checkout - Create checkout session
- POST /api/v1/workspaces/{id}/billing/portal - Create portal session
- GET /api/v1/workspaces/{id}/billing - Get billing info
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.workspace_auth import WorkspaceAccessChecker
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
)
from backend.services.workspace_billing import (
    WorkspaceBillingError,
    workspace_billing_service,
)
from bo1.logging.errors import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/workspaces", tags=["workspace-billing"])


# =============================================================================
# Models
# =============================================================================


class WorkspaceBillingInfoResponse(BaseModel):
    """Response model for workspace billing info."""

    workspace_id: str = Field(..., description="Workspace UUID")
    workspace_name: str = Field(..., description="Workspace name")
    tier: str = Field(..., description="Current subscription tier")
    billing_email: str | None = Field(None, description="Billing email address")
    has_billing_account: bool = Field(..., description="Whether Stripe customer exists")
    is_billing_owner: bool = Field(..., description="Whether current user is the billing owner")
    can_manage_billing: bool = Field(..., description="Whether current user can manage billing")


class WorkspaceCheckoutRequest(BaseModel):
    """Request to create a workspace checkout session."""

    price_id: str = Field(..., description="Stripe price ID (price_...)")


class WorkspaceCheckoutResponse(BaseModel):
    """Response from workspace checkout session creation."""

    session_id: str = Field(..., description="Stripe checkout session ID")
    url: str = Field(..., description="Checkout URL to redirect user to")


class WorkspacePortalResponse(BaseModel):
    """Response from workspace portal session creation."""

    url: str = Field(..., description="Billing portal URL")


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/{workspace_id}/billing",
    response_model=WorkspaceBillingInfoResponse,
    summary="Get workspace billing info",
    description="Returns billing information for a workspace.",
    responses={400: ERROR_400_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("get workspace billing")
async def get_workspace_billing(
    workspace_id: uuid.UUID = Path(..., description="Workspace UUID"),
    user: dict[str, Any] = Depends(get_current_user),
    _access: None = Depends(WorkspaceAccessChecker()),
) -> WorkspaceBillingInfoResponse:
    """Get billing information for a workspace.

    Any workspace member can view billing info.
    """
    user_id = extract_user_id(user)

    try:
        info = workspace_billing_service.get_billing_info(workspace_id, user_id)
    except WorkspaceBillingError as e:
        if e.code == "not_found":
            raise http_error(ErrorCode.API_NOT_FOUND, e.message, status=404) from e
        raise http_error(ErrorCode.API_BAD_REQUEST, e.message, status=400) from e

    # Check if user can manage billing (owner, billing owner, or admin)
    from backend.api.workspaces.models import MemberRole
    from backend.services.workspace_auth import check_role

    is_owner = info.owner_id == user_id
    is_admin = check_role(workspace_id, user_id, MemberRole.ADMIN)
    can_manage = info.is_billing_owner or is_owner or is_admin

    return WorkspaceBillingInfoResponse(
        workspace_id=str(info.workspace_id),
        workspace_name=info.workspace_name,
        tier=info.tier,
        billing_email=info.billing_email,
        has_billing_account=info.stripe_customer_id is not None,
        is_billing_owner=info.is_billing_owner,
        can_manage_billing=can_manage,
    )


@router.post(
    "/{workspace_id}/billing/checkout",
    response_model=WorkspaceCheckoutResponse,
    summary="Create workspace checkout session",
    description="Creates a Stripe checkout session for workspace subscription upgrade.",
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("create workspace checkout")
async def create_workspace_checkout(
    request: WorkspaceCheckoutRequest,
    workspace_id: uuid.UUID = Path(..., description="Workspace UUID"),
    user: dict[str, Any] = Depends(get_current_user),
    _access: None = Depends(WorkspaceAccessChecker()),
) -> WorkspaceCheckoutResponse:
    """Create a Stripe checkout session for workspace.

    Requires owner or admin role.
    """
    user_id = extract_user_id(user)

    try:
        result = await workspace_billing_service.create_checkout_session(
            workspace_id=workspace_id,
            user_id=user_id,
            price_id=request.price_id,
        )
    except WorkspaceBillingError as e:
        if e.code == "not_found":
            raise http_error(ErrorCode.API_NOT_FOUND, e.message, status=404) from e
        if e.code == "permission_denied":
            raise http_error(ErrorCode.API_FORBIDDEN, e.message, status=403) from e
        raise http_error(ErrorCode.API_BAD_REQUEST, e.message, status=400) from e

    logger.info(f"Created workspace checkout for {workspace_id} by {user_id}")

    return WorkspaceCheckoutResponse(
        session_id=result.session_id,
        url=result.url,
    )


@router.post(
    "/{workspace_id}/billing/portal",
    response_model=WorkspacePortalResponse,
    summary="Create workspace billing portal session",
    description="Creates a Stripe billing portal session for workspace subscription management.",
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("create workspace portal")
async def create_workspace_portal(
    workspace_id: uuid.UUID = Path(..., description="Workspace UUID"),
    user: dict[str, Any] = Depends(get_current_user),
    _access: None = Depends(WorkspaceAccessChecker()),
) -> WorkspacePortalResponse:
    """Create a Stripe billing portal session for workspace.

    Requires billing owner, owner, or admin role.
    """
    user_id = extract_user_id(user)

    try:
        url = await workspace_billing_service.create_portal_session(
            workspace_id=workspace_id,
            user_id=user_id,
        )
    except WorkspaceBillingError as e:
        if e.code == "not_found":
            raise http_error(ErrorCode.API_NOT_FOUND, e.message, status=404) from e
        if e.code == "permission_denied":
            raise http_error(ErrorCode.API_FORBIDDEN, e.message, status=403) from e
        if e.code == "no_billing_account":
            raise http_error(ErrorCode.API_BAD_REQUEST, e.message, status=400) from e
        raise http_error(ErrorCode.API_BAD_REQUEST, e.message, status=400) from e

    logger.info(f"Created workspace billing portal for {workspace_id} by {user_id}")

    return WorkspacePortalResponse(url=url)
