"""User GDPR endpoints for data export and account deletion.

Provides:
- GET /api/v1/user/export - Export user data (Art. 15)
- DELETE /api/v1/user/delete - Delete user account (Art. 17)
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from backend.api.middleware.auth import get_current_user
from backend.api.models import ErrorResponse
from backend.services.audit import (
    get_recent_deletion_request,
    get_recent_export_request,
    log_gdpr_event,
)
from backend.services.gdpr import GDPRError, collect_user_data, delete_user_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.get(
    "/export",
    summary="Export user data (GDPR Art. 15)",
    description="""
    Export all user data as JSON file. Rate limited to 1 request per 24 hours.

    Includes:
    - User profile
    - Business context
    - Sessions (meetings)
    - Actions
    - Datasets (metadata only)
    - Projects
    - GDPR audit log
    """,
    responses={
        200: {"description": "JSON file with all user data"},
        429: {"description": "Rate limit exceeded (1 per 24h)", "model": ErrorResponse},
        500: {"description": "Export failed", "model": ErrorResponse},
    },
)
async def export_user_data(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Export all user data as downloadable JSON."""
    user_id = user["user_id"]
    client_ip = _get_client_ip(request)

    # Rate limit: 1 export per 24 hours
    recent = get_recent_export_request(user_id, window_hours=24)
    if recent:
        last_export = recent["created_at"]
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "You can only request data export once every 24 hours.",
                "last_export": last_export.isoformat() if last_export else None,
            },
        )

    # Log the export request
    log_gdpr_event(
        user_id=user_id,
        action="export_requested",
        ip_address=client_ip,
    )

    try:
        # Collect all user data
        data = collect_user_data(user_id)

        # Log completion
        log_gdpr_event(
            user_id=user_id,
            action="export_completed",
            details={"record_count": sum(len(v) for v in data.values() if isinstance(v, list))},
            ip_address=client_ip,
        )

        # Return as downloadable JSON file
        filename = f"boardof_one_export_{user_id[:8]}_{datetime.now(UTC).strftime('%Y%m%d')}.json"
        content = json.dumps(data, indent=2, default=str)

        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    except GDPRError as e:
        logger.error(f"GDPR export failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete(
    "/delete",
    summary="Delete user account (GDPR Art. 17)",
    description="""
    Permanently delete user account and anonymize associated data.

    **WARNING**: This action is irreversible.

    What happens:
    - User profile: Deleted
    - Business context: Deleted
    - Sessions: Anonymized (user_id removed, problem statement hashed)
    - Actions: Anonymized (user_id removed, titles cleared)
    - Datasets: Deleted (including files from storage)
    - Projects: Deleted

    Rate limited to 1 request per 24 hours.
    """,
    responses={
        200: {"description": "Account deleted successfully"},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Deletion failed", "model": ErrorResponse},
    },
)
async def delete_user_account(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete user account and anonymize data."""
    user_id = user["user_id"]
    client_ip = _get_client_ip(request)

    # Check for recent deletion request (prevent accidental double-deletion)
    recent = get_recent_deletion_request(user_id, window_hours=24)
    if recent:
        if recent["action"] == "deletion_completed":
            raise HTTPException(
                status_code=410,
                detail={
                    "error": "Account already deleted",
                    "message": "This account has already been deleted.",
                },
            )
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Deletion pending",
                "message": "A deletion request is already in progress.",
            },
        )

    # Log the deletion request
    log_gdpr_event(
        user_id=user_id,
        action="deletion_requested",
        ip_address=client_ip,
    )

    try:
        # Perform deletion
        summary = delete_user_data(user_id)

        # Log completion
        log_gdpr_event(
            user_id=user_id,
            action="deletion_completed",
            details=summary,
            ip_address=client_ip,
        )

        # Delete SuperTokens session (logout)
        try:
            from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user

            await revoke_all_sessions_for_user(user_id)
        except Exception as e:
            logger.warning(f"Failed to revoke SuperTokens sessions: {e}")

        return {
            "status": "deleted",
            "message": "Your account and data have been deleted.",
            "summary": {
                "sessions_anonymized": summary.get("sessions_anonymized", 0),
                "actions_anonymized": summary.get("actions_anonymized", 0),
                "datasets_deleted": summary.get("datasets_deleted", 0),
            },
        }

    except GDPRError as e:
        # Log failure
        log_gdpr_event(
            user_id=user_id,
            action="deletion_failed",
            details={"error": str(e)},
            ip_address=client_ip,
        )
        logger.error(f"GDPR deletion failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
