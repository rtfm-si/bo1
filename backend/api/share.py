"""Public session share endpoints (no authentication required).

Provides:
- GET /api/v1/share/{token} - Access shared session data
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.services.session_share import SessionShareService
from bo1.state.repositories.session_repository import session_repository
from bo1.state.repositories.user_repository import user_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/share", tags=["share"])


@router.get(
    "/{token}",
    summary="Get shared session (public, no auth required)",
    description="Retrieve session data via a public share token. No authentication required.",
    responses={
        200: {"description": "Session data retrieved successfully"},
        404: {"description": "Share token not found", "model": ErrorResponse},
        410: {"description": "Share has expired", "model": ErrorResponse},
    },
)
@handle_api_errors("get shared session")
async def get_shared_session(
    token: str,
) -> dict[str, Any]:
    """Get shared session data via public token.

    Args:
        token: Share token

    Returns:
        Dict with session metadata (redacted for public view)

    Raises:
        HTTPException: If token invalid or expired
    """
    try:
        # Look up share record
        share = session_repository.get_share_by_token(token)

        if not share:
            raise HTTPException(
                status_code=404,
                detail="Share token not found or has been revoked",
            )

        # Check if expired
        expires_at = share.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        if SessionShareService.is_expired(expires_at):
            raise HTTPException(
                status_code=410,
                detail="This share link has expired",
            )

        # Get session data
        session_id = share.get("session_id")
        session = session_repository.get_session_by_id(session_id)

        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found",
            )

        # Get owner name (email)
        owner_id = session.get("user_id")
        owner = user_repository.get_by_id(owner_id)
        owner_name = owner.get("email", "Unknown") if owner else "Unknown"

        # Redact sensitive data for public view
        return {
            "session_id": session_id,
            "title": session.get("problem_statement", "Untitled"),
            "created_at": session.get("created_at"),
            "owner_name": owner_name,
            "expires_at": expires_at.isoformat()
            if isinstance(expires_at, datetime)
            else expires_at,
            "is_active": not SessionShareService.is_expired(expires_at),
            # Full session data (synthesis, conclusions, etc.)
            "synthesis": session.get("synthesis"),
            "conclusion": session.get("conclusion"),
            "problem_context": session.get("problem_context"),
            # Note: sensitive fields like participant emails are NOT included
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get shared session {token}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve shared session",
        ) from e
