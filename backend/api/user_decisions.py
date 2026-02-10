"""User decision API endpoints (Decision Gate).

Provides:
- POST /api/v1/sessions/{session_id}/decision - Upsert decision
- GET  /api/v1/sessions/{session_id}/decision - Get decision
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from backend.api.dependencies import VerifiedSession
from backend.api.middleware.rate_limit import CONTROL_RATE_LIMIT, limiter
from backend.api.models import (
    ErrorResponse,
    UserDecisionCreate,
    UserDecisionResponse,
)
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.openapi_security import CSRFTokenDep, SessionAuthDep
from backend.api.utils.responses import ERROR_400_RESPONSE, ERROR_404_RESPONSE
from backend.api.utils.validation import validate_session_id
from bo1.state.repositories.user_decision_repository import user_decision_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions/{session_id}/decision", tags=["decisions"])


@router.post(
    "",
    response_model=UserDecisionResponse,
    summary="Submit or update decision",
    responses={
        200: {"description": "Decision saved"},
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("submit decision")
async def submit_decision(
    request: Request,
    session_id: str,
    body: UserDecisionCreate,
    session_data: VerifiedSession,
    _auth: SessionAuthDep,
    _csrf: CSRFTokenDep,
) -> UserDecisionResponse:
    """Upsert a user decision for a session."""
    session_id = validate_session_id(session_id)
    user_id, metadata = session_data

    # Verify session is completed
    status = metadata.get("status", "")
    if status != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Session not completed",
                "message": "Decisions can only be made for completed sessions.",
            },
        )

    decision = user_decision_repository.upsert(
        session_id=session_id,
        user_id=user_id,
        chosen_option_id=body.chosen_option_id,
        chosen_option_label=body.chosen_option_label,
        chosen_option_description=body.chosen_option_description,
        rationale=body.rationale,
        matrix_snapshot=body.matrix_snapshot,
        decision_source=body.decision_source,
    )

    logger.info(f"Decision saved: session={session_id} option={body.chosen_option_id}")
    return UserDecisionResponse(**decision.model_dump())


@router.get(
    "",
    response_model=UserDecisionResponse,
    summary="Get decision for session",
    responses={
        200: {"description": "Decision found"},
        404: {"description": "No decision found", "model": ErrorResponse},
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("get decision")
async def get_decision(
    request: Request,
    session_id: str,
    session_data: VerifiedSession,
    _auth: SessionAuthDep,
) -> UserDecisionResponse:
    """Get the user decision for a session."""
    session_id = validate_session_id(session_id)
    user_id, _metadata = session_data

    decision = user_decision_repository.get_by_session(session_id, user_id)
    if not decision:
        raise HTTPException(status_code=404, detail="No decision found for this session")

    return UserDecisionResponse(**decision.model_dump())
