"""Onboarding API endpoints.

Provides:
- GET /api/v1/onboarding/status - Get onboarding progress
- POST /api/v1/onboarding/step - Mark step as completed
- POST /api/v1/onboarding/complete - Mark onboarding as complete
- POST /api/v1/onboarding/tour/complete - Mark driver.js tour as complete
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import execute_query, get_single_value
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


class OnboardingStep(str, Enum):
    """Onboarding step identifiers for driver.js tour."""

    BUSINESS_CONTEXT = "business_context"
    FIRST_MEETING = "first_meeting"
    EXPERT_PANEL = "expert_panel"
    RESULTS = "results"


class OnboardingStatus(BaseModel):
    """Onboarding status response model."""

    tour_completed: bool = Field(False, description="Whether user completed the driver.js tour")
    tour_completed_at: datetime | None = Field(None, description="When tour was completed")
    steps_completed: list[str] = Field(
        default_factory=list, description="List of completed step names"
    )
    context_setup: bool = Field(False, description="Whether business context has been set up")
    first_meeting_id: str | None = Field(None, description="ID of user's first meeting")
    needs_onboarding: bool = Field(True, description="Whether user should see onboarding flow")


class StepCompleteRequest(BaseModel):
    """Request to mark an onboarding step as complete."""

    step: OnboardingStep = Field(..., description="Step to mark as completed")


class TourCompleteRequest(BaseModel):
    """Request to mark the driver.js tour as complete."""

    first_meeting_id: str | None = Field(None, description="Optional ID of user's first meeting")


def _get_onboarding_record(user_id: str) -> dict[str, Any] | None:
    """Get user's onboarding record from database."""
    try:
        row = execute_query(
            """
            SELECT tour_completed, tour_completed_at, steps_completed,
                   first_meeting_id, created_at, updated_at
            FROM user_onboarding
            WHERE user_id = %s
            """,
            (user_id,),
            fetch="one",
        )
        return dict(row) if row else None
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ONBOARDING_ERROR,
            f"Failed to get onboarding record: {e}",
            user_id=user_id,
        )
        return None


def _ensure_onboarding_record(user_id: str) -> dict[str, Any]:
    """Ensure user has an onboarding record, creating if needed."""
    try:
        row = execute_query(
            """
            INSERT INTO user_onboarding (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO UPDATE SET updated_at = NOW()
            RETURNING tour_completed, tour_completed_at, steps_completed,
                      first_meeting_id, created_at, updated_at
            """,
            (user_id,),
            fetch="one",
        )
        return dict(row) if row else {}
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ONBOARDING_ERROR,
            f"Failed to ensure onboarding record: {e}",
            user_id=user_id,
        )
        return {}


def _check_context_setup(user_id: str) -> bool:
    """Check if user has set up business context."""
    try:
        return bool(
            get_single_value(
                "SELECT onboarding_completed FROM user_context WHERE user_id = %s",
                (user_id,),
                column="onboarding_completed",
                default=False,
            )
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ONBOARDING_ERROR,
            f"Failed to check context setup: {e}",
            user_id=user_id,
        )
        return False


@router.get(
    "/status",
    response_model=OnboardingStatus,
    summary="Get onboarding status",
    description="""
    Get the user's onboarding progress including:
    - Tour completion status
    - Completed onboarding steps
    - Business context setup status
    - First meeting ID (if any)

    Use this to determine whether to show the onboarding flow or tour.
    """,
)
@handle_api_errors("get onboarding status")
async def get_onboarding_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> OnboardingStatus:
    """Get user's onboarding status."""
    user_id = extract_user_id(user)

    # Get onboarding record
    record = _get_onboarding_record(user_id)
    context_setup = _check_context_setup(user_id)

    if not record:
        # User has no onboarding record yet
        return OnboardingStatus(
            tour_completed=False,
            tour_completed_at=None,
            steps_completed=[],
            context_setup=context_setup,
            first_meeting_id=None,
            needs_onboarding=not context_setup,
        )

    # Determine if user still needs onboarding
    tour_done = record.get("tour_completed", False)
    needs_onboarding = not context_setup and not tour_done

    return OnboardingStatus(
        tour_completed=tour_done,
        tour_completed_at=record.get("tour_completed_at"),
        steps_completed=record.get("steps_completed", []),
        context_setup=context_setup,
        first_meeting_id=record.get("first_meeting_id"),
        needs_onboarding=needs_onboarding,
    )


@router.post(
    "/step",
    response_model=OnboardingStatus,
    summary="Mark onboarding step as complete",
    description="""
    Mark a specific onboarding step as completed.

    Available steps:
    - `business_context`: User has set up their business context
    - `first_meeting`: User has started their first meeting
    - `expert_panel`: User has viewed the expert panel
    - `results`: User has viewed meeting results

    This is used by driver.js to track tour progress.
    """,
)
@handle_api_errors("complete onboarding step")
async def complete_step(
    request: StepCompleteRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> OnboardingStatus:
    """Mark an onboarding step as complete."""
    user_id = extract_user_id(user)

    # Ensure record exists
    _ensure_onboarding_record(user_id)

    # Add step to completed list if not already there
    row = execute_query(
        """
        UPDATE user_onboarding
        SET steps_completed = (
            SELECT jsonb_agg(DISTINCT elem)
            FROM (
                SELECT jsonb_array_elements(steps_completed) AS elem
                UNION
                SELECT %s::jsonb
            ) sub
        ),
        updated_at = NOW()
        WHERE user_id = %s
        RETURNING tour_completed, tour_completed_at, steps_completed,
                  first_meeting_id
        """,
        (f'"{request.step.value}"', user_id),
        fetch="one",
    )

    if not row:
        raise http_error(ErrorCode.DB_QUERY_ERROR, "Failed to update step", 500)

    context_setup = _check_context_setup(user_id)
    tour_done = row.get("tour_completed", False)

    return OnboardingStatus(
        tour_completed=tour_done,
        tour_completed_at=row.get("tour_completed_at"),
        steps_completed=row.get("steps_completed", []),
        context_setup=context_setup,
        first_meeting_id=row.get("first_meeting_id"),
        needs_onboarding=not context_setup and not tour_done,
    )


@router.post(
    "/tour/complete",
    response_model=OnboardingStatus,
    summary="Mark driver.js tour as complete",
    description="""
    Mark the driver.js onboarding tour as complete.

    Call this when the user finishes or dismisses the guided tour.
    Optionally include the first_meeting_id if the user created a meeting during the tour.
    """,
)
@handle_api_errors("complete tour")
async def complete_tour(
    request: TourCompleteRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> OnboardingStatus:
    """Mark the tour as complete."""
    user_id = extract_user_id(user)

    # Ensure record exists
    _ensure_onboarding_record(user_id)

    # Update tour completion
    if request and request.first_meeting_id:
        row = execute_query(
            """
            UPDATE user_onboarding
            SET tour_completed = true,
                tour_completed_at = NOW(),
                first_meeting_id = %s,
                updated_at = NOW()
            WHERE user_id = %s
            RETURNING tour_completed, tour_completed_at, steps_completed,
                      first_meeting_id
            """,
            (request.first_meeting_id, user_id),
            fetch="one",
        )
    else:
        row = execute_query(
            """
            UPDATE user_onboarding
            SET tour_completed = true,
                tour_completed_at = NOW(),
                updated_at = NOW()
            WHERE user_id = %s
            RETURNING tour_completed, tour_completed_at, steps_completed,
                      first_meeting_id
            """,
            (user_id,),
            fetch="one",
        )

    if not row:
        raise http_error(ErrorCode.DB_QUERY_ERROR, "Failed to complete tour", 500)

    context_setup = _check_context_setup(user_id)

    return OnboardingStatus(
        tour_completed=True,
        tour_completed_at=row.get("tour_completed_at"),
        steps_completed=row.get("steps_completed", []),
        context_setup=context_setup,
        first_meeting_id=row.get("first_meeting_id"),
        needs_onboarding=False,  # Tour is done, no more onboarding
    )


@router.post(
    "/skip",
    response_model=OnboardingStatus,
    summary="Skip onboarding",
    description="""
    Skip the onboarding flow entirely.

    This marks the tour as complete so the user won't see onboarding prompts.
    Useful for returning users who don't want to go through the tour.
    """,
)
@handle_api_errors("skip onboarding")
async def skip_onboarding(
    user: dict[str, Any] = Depends(get_current_user),
) -> OnboardingStatus:
    """Skip onboarding entirely."""
    user_id = extract_user_id(user)

    # Ensure record exists and mark as skipped
    row = execute_query(
        """
        INSERT INTO user_onboarding (user_id, tour_completed, tour_completed_at)
        VALUES (%s, true, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            tour_completed = true,
            tour_completed_at = NOW(),
            updated_at = NOW()
        RETURNING tour_completed, tour_completed_at, steps_completed,
                  first_meeting_id
        """,
        (user_id,),
        fetch="one",
    )

    if not row:
        raise http_error(ErrorCode.DB_QUERY_ERROR, "Failed to skip onboarding", 500)

    context_setup = _check_context_setup(user_id)

    return OnboardingStatus(
        tour_completed=True,
        tour_completed_at=row.get("tour_completed_at"),
        steps_completed=row.get("steps_completed", []),
        context_setup=context_setup,
        first_meeting_id=row.get("first_meeting_id"),
        needs_onboarding=False,
    )


@router.post(
    "/reset",
    response_model=OnboardingStatus,
    summary="Reset onboarding tour",
    description="""
    Reset the onboarding tour so the user can take it again.

    This clears the tour completion status while preserving first_meeting_id.
    Useful for users who want to revisit the guided tour.
    """,
)
@handle_api_errors("reset onboarding")
async def reset_onboarding(
    user: dict[str, Any] = Depends(get_current_user),
) -> OnboardingStatus:
    """Reset onboarding tour to allow restart."""
    user_id = extract_user_id(user)

    # Reset tour_completed but preserve first_meeting_id
    row = execute_query(
        """
        INSERT INTO user_onboarding (user_id, tour_completed, tour_completed_at, steps_completed)
        VALUES (%s, false, NULL, '[]'::jsonb)
        ON CONFLICT (user_id) DO UPDATE SET
            tour_completed = false,
            tour_completed_at = NULL,
            steps_completed = '[]'::jsonb,
            updated_at = NOW()
        RETURNING tour_completed, tour_completed_at, steps_completed,
                  first_meeting_id
        """,
        (user_id,),
        fetch="one",
    )

    if not row:
        raise http_error(ErrorCode.DB_QUERY_ERROR, "Failed to reset onboarding", 500)

    context_setup = _check_context_setup(user_id)

    return OnboardingStatus(
        tour_completed=False,
        tour_completed_at=None,
        steps_completed=[],
        context_setup=context_setup,
        first_meeting_id=row.get("first_meeting_id"),
        needs_onboarding=True,
    )
