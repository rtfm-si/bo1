"""Admin API endpoints for user impersonation.

Provides:
- POST /api/admin/impersonate/{user_id} - Start impersonation
- DELETE /api/admin/impersonate - End impersonation
- GET /api/admin/impersonate/status - Check impersonation status
- GET /api/admin/impersonate/history - Get impersonation audit log
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.admin.helpers import AdminQueryService, AdminUserService
from backend.api.admin.models import (
    EndImpersonationResponse,
    ImpersonationHistoryItem,
    ImpersonationHistoryResponse,
    ImpersonationSessionResponse,
    ImpersonationStatusResponse,
    StartImpersonationRequest,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.services.admin_impersonation import (
    ImpersonationSession,
    end_impersonation,
    get_active_impersonation,
    get_impersonation_history,
    start_impersonation,
)
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Impersonation"])


def _session_to_response(session: ImpersonationSession) -> ImpersonationSessionResponse:
    """Convert ImpersonationSession to response model."""
    now = datetime.now(UTC)
    remaining = max(0, int((session.expires_at - now).total_seconds()))
    return ImpersonationSessionResponse(
        admin_user_id=session.admin_user_id,
        target_user_id=session.target_user_id,
        target_email=session.target_email,
        reason=session.reason,
        is_write_mode=session.is_write_mode,
        started_at=session.started_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        remaining_seconds=remaining,
    )


@router.post(
    "/impersonate/{user_id}",
    response_model=ImpersonationSessionResponse,
    summary="Start impersonation session",
    description="Start impersonating a target user. Admin will see the app as that user.",
    responses={
        200: {"description": "Impersonation started successfully"},
        400: {"description": "Cannot impersonate self or another admin", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "Target user not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("start impersonation")
async def start_impersonation_endpoint(
    user_id: str,
    request: StartImpersonationRequest,
    admin_id: str = Depends(require_admin_any),
) -> ImpersonationSessionResponse:
    """Start impersonating a target user."""
    # Cannot impersonate self
    if user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot impersonate yourself",
        )

    # Check if target user exists
    if not AdminQueryService.user_exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}",
        )

    # Cannot impersonate another admin (security measure)
    target_user = AdminQueryService.get_user(user_id)
    if target_user.is_admin:
        raise HTTPException(
            status_code=400,
            detail="Cannot impersonate another admin user",
        )

    # Start impersonation
    session = start_impersonation(
        admin_id=admin_id,
        target_user_id=user_id,
        reason=request.reason,
        write_mode=request.write_mode,
        duration_minutes=request.duration_minutes,
    )

    if not session:
        raise HTTPException(
            status_code=500,
            detail="Failed to start impersonation session",
        )

    # Log admin action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="impersonation_started",
        resource_type="user",
        resource_id=user_id,
        details={
            "reason": request.reason,
            "write_mode": request.write_mode,
            "duration_minutes": request.duration_minutes,
        },
    )

    logger.info(
        f"Admin {admin_id} started impersonation of {user_id} "
        f"(write_mode={request.write_mode}, duration={request.duration_minutes}m)"
    )

    return _session_to_response(session)


@router.delete(
    "/impersonate",
    response_model=EndImpersonationResponse,
    summary="End impersonation session",
    description="End the current impersonation session and return to admin view.",
    responses={
        200: {"description": "Impersonation ended successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("end impersonation")
async def end_impersonation_endpoint(
    admin_id: str = Depends(require_admin_any),
) -> EndImpersonationResponse:
    """End the current impersonation session."""
    # Get current session for logging
    session = get_active_impersonation(admin_id)
    target_user_id = session.target_user_id if session else None

    ended = end_impersonation(admin_id)

    if ended and target_user_id:
        # Log admin action
        AdminUserService.log_admin_action(
            admin_id=admin_id,
            action="impersonation_ended",
            resource_type="user",
            resource_id=target_user_id,
        )
        logger.info(f"Admin {admin_id} ended impersonation of {target_user_id}")

    return EndImpersonationResponse(
        ended=ended,
        message="Impersonation session ended" if ended else "No active impersonation session",
    )


@router.get(
    "/impersonate/status",
    response_model=ImpersonationStatusResponse,
    summary="Get impersonation status",
    description="Check if admin is currently impersonating a user.",
    responses={
        200: {"description": "Status retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get impersonation status")
async def get_impersonation_status(
    admin_id: str = Depends(require_admin_any),
) -> ImpersonationStatusResponse:
    """Check if admin is currently impersonating a user."""
    session = get_active_impersonation(admin_id)

    if session:
        return ImpersonationStatusResponse(
            is_impersonating=True,
            session=_session_to_response(session),
        )

    return ImpersonationStatusResponse(
        is_impersonating=False,
        session=None,
    )


@router.get(
    "/impersonate/history",
    response_model=ImpersonationHistoryResponse,
    summary="Get impersonation history",
    description="Get audit log of impersonation sessions.",
    responses={
        200: {"description": "History retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get impersonation history")
async def get_impersonation_history_endpoint(
    admin_user_id: str | None = Query(None, description="Filter by admin user ID"),
    target_user_id: str | None = Query(None, description="Filter by target user ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    _admin: str = Depends(require_admin_any),
) -> ImpersonationHistoryResponse:
    """Get audit log of impersonation sessions."""
    history = get_impersonation_history(
        admin_id=admin_user_id,
        target_user_id=target_user_id,
        limit=limit,
    )

    sessions = [
        ImpersonationHistoryItem(
            id=item["id"],
            admin_user_id=item["admin_user_id"],
            admin_email=item["admin_email"],
            target_user_id=item["target_user_id"],
            target_email=item["target_email"],
            reason=item["reason"],
            is_write_mode=item["is_write_mode"],
            started_at=item["started_at"].isoformat() if item["started_at"] else "",
            expires_at=item["expires_at"].isoformat() if item["expires_at"] else "",
            ended_at=item["ended_at"].isoformat() if item["ended_at"] else None,
        )
        for item in history
    ]

    return ImpersonationHistoryResponse(
        total=len(sessions),
        sessions=sessions,
        limit=limit,
    )
