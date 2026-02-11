"""Decision outcome API endpoints (Outcome Tracking).

Provides:
- POST /api/v1/sessions/{session_id}/decision/outcome - Upsert outcome
- GET  /api/v1/sessions/{session_id}/decision/outcome - Get outcome
- GET  /api/v1/users/me/pending-followups - Decisions needing outcomes
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.api.dependencies import VerifiedSession
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTROL_RATE_LIMIT, limiter
from backend.api.models import (
    DecisionOutcomeCreate,
    DecisionOutcomeResponse,
    ErrorResponse,
    PendingFollowupResponse,
)
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.openapi_security import CSRFTokenDep, SessionAuthDep
from backend.api.utils.responses import ERROR_400_RESPONSE, ERROR_404_RESPONSE
from backend.api.utils.validation import validate_session_id
from bo1.state.repositories.decision_outcome_repository import decision_outcome_repository
from bo1.state.repositories.user_decision_repository import user_decision_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["decision-outcomes"])


def _decision_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="No decision found for this session")


# Session-scoped routes
session_router = APIRouter(prefix="/v1/sessions/{session_id}/decision/outcome")


@session_router.post(
    "",
    response_model=DecisionOutcomeResponse,
    summary="Submit or update decision outcome",
    responses={
        200: {"description": "Outcome saved"},
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("submit decision outcome")
async def submit_outcome(
    request: Request,
    session_id: str,
    body: DecisionOutcomeCreate,
    session_data: VerifiedSession,
    _auth: SessionAuthDep,
    _csrf: CSRFTokenDep,
) -> DecisionOutcomeResponse:
    """Upsert a decision outcome for a session's decision."""
    session_id = validate_session_id(session_id)
    user_id, _metadata = session_data

    # Verify session has a decision
    decision = user_decision_repository.get_by_session(session_id, user_id)
    if not decision:
        raise _decision_not_found()

    outcome = decision_outcome_repository.upsert(
        decision_id=decision.id,
        user_id=user_id,
        outcome_status=body.outcome_status,
        outcome_notes=body.outcome_notes,
        surprise_factor=body.surprise_factor,
        lessons_learned=body.lessons_learned,
        what_would_change=body.what_would_change,
    )

    logger.info(f"Outcome saved: decision={decision.id} status={body.outcome_status}")
    return DecisionOutcomeResponse(**outcome.model_dump())


@session_router.get(
    "",
    response_model=DecisionOutcomeResponse,
    summary="Get decision outcome",
    responses={
        200: {"description": "Outcome found"},
        404: {"description": "No outcome found", "model": ErrorResponse},
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("get decision outcome")
async def get_outcome(
    request: Request,
    session_id: str,
    session_data: VerifiedSession,
    _auth: SessionAuthDep,
) -> DecisionOutcomeResponse:
    """Get the outcome for a session's decision."""
    session_id = validate_session_id(session_id)
    user_id, _metadata = session_data

    decision = user_decision_repository.get_by_session(session_id, user_id)
    if not decision:
        raise _decision_not_found()

    outcome = decision_outcome_repository.get_by_decision(decision.id, user_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="No outcome recorded for this decision")

    return DecisionOutcomeResponse(**outcome.model_dump())


# User-scoped routes
followup_router = APIRouter(prefix="/v1/users/me")


@followup_router.get(
    "/pending-followups",
    response_model=list[PendingFollowupResponse],
    summary="Get decisions pending outcome recording",
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("get pending followups")
async def get_pending_followups(
    request: Request,
    _auth: SessionAuthDep,
    user: dict = Depends(get_current_user),
) -> list[PendingFollowupResponse]:
    """Get decisions older than 30 days that don't have outcomes yet."""
    user_id = extract_user_id(user)
    rows = decision_outcome_repository.list_pending_followups(user_id, age_days=30)
    return [PendingFollowupResponse(**r) for r in rows]


router.include_router(session_router)
router.include_router(followup_router)
