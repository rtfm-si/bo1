"""FastAPI router for goal and objective progress endpoints.

Extracted from routes.py. Provides:
- GET /v1/context/goal-progress - Action completion stats (30-day window)
- GET /v1/context/goal-history - North star goal change history
- GET /v1/context/goal-staleness - Check if goal needs review
- GET /v1/context/objectives/progress - All objective progress
- PUT /v1/context/objectives/{index}/progress - Update objective progress
- DELETE /v1/context/objectives/{index}/progress - Remove objective progress
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from backend.api.context.models import (
    GoalHistoryEntry,
    GoalHistoryResponse,
    GoalProgressResponse,
    GoalStalenessResponse,
    ObjectiveProgress,
    ObjectiveProgressListResponse,
    ObjectiveProgressResponse,
    ObjectiveProgressUpdate,
)
from backend.api.context.services import GOAL_STALENESS_THRESHOLD_DAYS
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTEXT_RATE_LIMIT, limiter
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.logging.errors import log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


# =============================================================================
# Goal Progress Endpoints
# =============================================================================


@router.get(
    "/v1/context/goal-progress",
    response_model=GoalProgressResponse,
    summary="Get goal progress metrics",
    description="""
    Get action completion stats for the last 30 days.

    Returns:
    - Progress percentage (completed / total active actions)
    - Trend compared to previous 30-day period (up/down/stable)
    - Completed and total counts

    Useful for displaying goal progress on the dashboard.
    """,
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("get goal progress")
async def get_goal_progress(
    user: dict[str, Any] = Depends(get_current_user),
) -> GoalProgressResponse:
    """Get goal progress based on action completion."""
    from datetime import timedelta

    from bo1.state import db_session

    user_id = extract_user_id(user)

    # Calculate date ranges
    now = datetime.now(UTC)
    period_30d_start = now - timedelta(days=30)
    period_60d_start = now - timedelta(days=60)

    # Query action stats for current 30-day period
    with db_session(user_id=user_id) as conn:
        # Current period (last 30 days)
        result = execute_query(
            conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'done') as completed,
                COUNT(*) FILTER (WHERE status IN ('todo', 'in_progress', 'done')) as total
            FROM actions
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND (
                  completed_at >= %s
                  OR (status IN ('todo', 'in_progress') AND created_at <= %s)
              )
            """,
            (user_id, period_30d_start, now),
            user_id=user_id,
        )
        current = result.fetchone() if result else None
        current_completed = current[0] if current else 0
        current_total = current[1] if current else 0

        # Previous period (30-60 days ago)
        result = execute_query(
            conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'done') as completed,
                COUNT(*) FILTER (WHERE status IN ('todo', 'in_progress', 'done')) as total
            FROM actions
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND (
                  completed_at >= %s AND completed_at < %s
                  OR (status IN ('todo', 'in_progress') AND created_at <= %s AND created_at >= %s)
              )
            """,
            (user_id, period_60d_start, period_30d_start, period_30d_start, period_60d_start),
            user_id=user_id,
        )
        previous = result.fetchone() if result else None
        prev_completed = previous[0] if previous else 0
        prev_total = previous[1] if previous else 0

    # Calculate progress percentage
    progress_percent = 0
    if current_total > 0:
        progress_percent = min(100, int((current_completed / current_total) * 100))

    # Calculate trend
    current_rate = current_completed / current_total if current_total > 0 else 0
    prev_rate = prev_completed / prev_total if prev_total > 0 else 0

    if current_rate > prev_rate + 0.05:
        trend = "up"
    elif current_rate < prev_rate - 0.05:
        trend = "down"
    else:
        trend = "stable"

    logger.info(
        f"Goal progress for user {user_id}: {progress_percent}% ({current_completed}/{current_total}), trend={trend}"
    )

    return GoalProgressResponse(
        progress_percent=progress_percent,
        trend=trend,
        completed_count=current_completed,
        total_count=current_total,
    )


# =============================================================================
# Goal History Endpoints (North Star Goal Tracking)
# =============================================================================


@router.get(
    "/v1/context/goal-history",
    response_model=GoalHistoryResponse,
    summary="Get goal change history",
    description="""
    Retrieve the history of north star goal changes for the user.

    Returns up to 10 most recent goal changes, newest first.
    Each entry includes the goal text, when it was changed, and the previous goal.

    **Use Cases:**
    - Display goal evolution timeline in strategic context page
    - Show users how their focus has shifted over time
    """,
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("get goal history")
async def get_goal_history_endpoint(
    limit: int = 10,
    user: dict[str, Any] = Depends(get_current_user),
) -> GoalHistoryResponse:
    """Get history of goal changes."""
    from backend.services.goal_tracker import get_goal_history as fetch_goal_history

    user_id = extract_user_id(user)

    try:
        history = fetch_goal_history(user_id, limit=min(limit, 50))
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to fetch goal history for user {user_id}",
            user_id=user_id,
            error=str(e),
        )
        return GoalHistoryResponse(entries=[], count=0)

    entries = [
        GoalHistoryEntry(
            goal_text=h["goal_text"],
            changed_at=h["changed_at"],
            previous_goal=h["previous_goal"],
        )
        for h in history
    ]

    return GoalHistoryResponse(entries=entries, count=len(entries))


@router.get(
    "/v1/context/goal-staleness",
    response_model=GoalStalenessResponse,
    summary="Check goal staleness",
    description="""
    Check if the user's north star goal needs review.

    Returns:
    - Days since the goal was last changed
    - Whether to show a "Review your goal?" prompt (>30 days unchanged)
    - The current/last goal text

    **Use Cases:**
    - Dashboard banner prompting goal review
    - Strategic context page staleness indicator
    """,
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("check goal staleness")
async def check_goal_staleness(
    user: dict[str, Any] = Depends(get_current_user),
) -> GoalStalenessResponse:
    """Check if goal needs review based on staleness."""
    from backend.services.goal_tracker import get_days_since_last_change

    user_id = extract_user_id(user)

    # Get current goal from context
    context_data = user_repository.get_context(user_id)
    current_goal = context_data.get("north_star_goal") if context_data else None

    if not current_goal:
        return GoalStalenessResponse(
            days_since_change=None,
            should_prompt=False,
            last_goal=None,
        )

    # Get days since last change
    try:
        days = get_days_since_last_change(user_id)
    except Exception as e:
        logger.warning(f"Failed to check goal staleness for user {user_id}: {e}")
        days = None

    should_prompt = days is not None and days >= GOAL_STALENESS_THRESHOLD_DAYS

    return GoalStalenessResponse(
        days_since_change=days,
        should_prompt=should_prompt,
        last_goal=current_goal,
    )


# =============================================================================
# Strategic Objective Progress Endpoints
# =============================================================================


@router.get(
    "/v1/context/objectives/progress",
    response_model=ObjectiveProgressListResponse,
    summary="Get all objective progress",
    description="""
    Get progress for all strategic objectives.

    Returns each objective with its current progress data (if set).
    Progress includes current value, target value, and optional unit.

    **Use Cases:**
    - Dashboard goal banner progress display
    - Context overview progress tracking
    """,
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("get objective progress")
async def get_objectives_progress(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> ObjectiveProgressListResponse:
    """Get progress for all strategic objectives."""
    user_id = extract_user_id(user)

    # Get context data
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return ObjectiveProgressListResponse(objectives=[], count=0)

    objectives = context_data.get("strategic_objectives") or []
    progress_data = context_data.get("strategic_objectives_progress") or {}

    # Build response
    result = []
    progress_count = 0
    for idx, objective_text in enumerate(objectives):
        idx_str = str(idx)
        progress = None
        if idx_str in progress_data:
            try:
                progress = ObjectiveProgress(**progress_data[idx_str])
                progress_count += 1
            except Exception:
                logger.warning(f"Invalid progress data for objective {idx}")

        result.append(
            ObjectiveProgressResponse(
                objective_index=idx,
                objective_text=objective_text,
                progress=progress,
            )
        )

    return ObjectiveProgressListResponse(objectives=result, count=progress_count)


@router.put(
    "/v1/context/objectives/{objective_index}/progress",
    response_model=ObjectiveProgressResponse,
    summary="Update objective progress",
    description="""
    Update progress for a specific strategic objective.

    **Path Parameters:**
    - `objective_index`: Index of the objective (0-4)

    **Request Body:**
    - `current`: Current value (e.g., "$5K", "50%")
    - `target`: Target value (e.g., "$10K", "80%")
    - `unit`: Optional unit label (e.g., "MRR", "%")

    **Use Cases:**
    - Dashboard progress modal save
    - Quick progress update from goal banner
    """,
    responses={
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("update objective progress")
async def update_objective_progress(
    request: Request,
    objective_index: int,
    body: ObjectiveProgressUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> ObjectiveProgressResponse:
    """Update progress for a specific objective."""
    user_id = extract_user_id(user)

    # Validate index
    if objective_index < 0 or objective_index > 4:
        raise http_error(ErrorCode.API_BAD_REQUEST, "Objective index must be 0-4", status=400)

    # Get current context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    objectives = context_data.get("strategic_objectives") or []
    if objective_index >= len(objectives):
        raise http_error(
            ErrorCode.API_NOT_FOUND, f"Objective at index {objective_index} not found", status=404
        )

    # Update progress
    progress_data = context_data.get("strategic_objectives_progress") or {}
    now = datetime.now(UTC)

    progress_entry = {
        "current": body.current,
        "target": body.target,
        "unit": body.unit,
        "updated_at": now.isoformat(),
    }
    progress_data[str(objective_index)] = progress_entry

    # Save to database
    user_repository.save_context(user_id, {"strategic_objectives_progress": progress_data})

    return ObjectiveProgressResponse(
        objective_index=objective_index,
        objective_text=objectives[objective_index],
        progress=ObjectiveProgress(
            current=body.current,
            target=body.target,
            unit=body.unit,
            updated_at=now,
        ),
    )


@router.delete(
    "/v1/context/objectives/{objective_index}/progress",
    summary="Delete objective progress",
    description="Remove progress tracking for a specific objective.",
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("delete objective progress")
async def delete_objective_progress(
    request: Request,
    objective_index: int,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, bool]:
    """Delete progress for a specific objective."""
    user_id = extract_user_id(user)

    # Get current context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return {"success": True}

    progress_data = context_data.get("strategic_objectives_progress") or {}
    idx_str = str(objective_index)

    if idx_str in progress_data:
        del progress_data[idx_str]
        user_repository.save_context(user_id, {"strategic_objectives_progress": progress_data})

    return {"success": True}
