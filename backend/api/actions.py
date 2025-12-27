"""Actions API endpoints for global action management.

Provides:
- GET /api/v1/actions - Get all user actions across sessions
- GET /api/v1/actions/{action_id} - Get single action details
- POST /api/v1/actions/{action_id}/start - Start an action
- POST /api/v1/actions/{action_id}/complete - Complete an action
- PATCH /api/v1/actions/{action_id}/status - Update action status
"""

import logging
from datetime import UTC, datetime
from typing import Any

import redis
from fastapi import APIRouter, Depends, Query, Request

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import limiter
from backend.api.models import (
    ActionBlockedResponse,
    ActionCloneReplanRequest,
    ActionCloneReplanResponse,
    ActionCloseRequest,
    ActionCloseResponse,
    ActionCompletedResponse,
    ActionCompleteRequest,
    ActionDatesResponse,
    ActionDatesUpdate,
    ActionDeletedResponse,
    ActionDetailResponse,
    ActionProgressUpdate,
    ActionRemindersResponse,
    ActionReplanContextResponse,
    ActionStartedResponse,
    ActionStatsResponse,
    ActionStatsTotals,
    ActionStatusUpdate,
    ActionStatusUpdatedResponse,
    ActionTagsUpdate,
    ActionUnblockedResponse,
    ActionUpdateCreate,
    ActionUpdateResponse,
    ActionUpdatesResponse,
    ActionVariance,
    AllActionsResponse,
    BlockActionRequest,
    DailyActionStat,
    DependencyAddedResponse,
    DependencyCreate,
    DependencyListResponse,
    DependencyRemovedResponse,
    DependencyResponse,
    ErrorResponse,
    EscalateBlockerRequest,
    EscalateBlockerResponse,
    GanttActionData,
    GanttDependency,
    GeneratedProjectInfo,
    GlobalGanttResponse,
    IncompleteDependencyInfo,
    RateLimitResponse,
    RelatedAction,
    ReminderSettingsResponse,
    ReminderSettingsUpdate,
    ReminderSnoozedResponse,
    ReplanRequest,
    ReplanResponse,
    SnoozeReminderRequest,
    TagResponse,
    UnblockActionRequest,
    UnblockPathsResponse,
    UnblockSuggestionModel,
)
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.degradation import check_pool_health
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.blocker_analyzer import get_blocker_analyzer
from backend.services.gantt_service import GanttColorService
from bo1.config import get_settings
from bo1.constants import GanttColorStrategy
from bo1.logging.errors import ErrorCode, log_error
from bo1.services.replanning_service import replanning_service
from bo1.state.database import db_session
from bo1.state.repositories.action_repository import action_repository
from bo1.state.repositories.session_repository import session_repository
from bo1.state.repositories.tag_repository import tag_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/actions", tags=["actions"])


def _tasks_with_statuses_and_session(
    tasks: list[dict[str, Any]],
    task_statuses: dict[str, str],
    session_id: str,
    problem_statement: str,
) -> list[dict[str, Any]]:
    """Merge tasks with their statuses and add session context.

    Args:
        tasks: List of task dictionaries
        task_statuses: Mapping of task_id -> status
        session_id: Session identifier
        problem_statement: Session problem statement (decision)

    Returns:
        List of task dicts with status and session context
    """
    result = []
    for task in tasks:
        task_id = task.get("id", "")
        status = task_statuses.get(task_id, "todo")
        result.append(
            {
                "id": task_id,
                "title": task.get("title", ""),
                "description": task.get("description", ""),
                "what_and_how": task.get("what_and_how", []),
                "success_criteria": task.get("success_criteria", []),
                "kill_criteria": task.get("kill_criteria", []),
                "dependencies": task.get("dependencies", []),
                "timeline": task.get("timeline", ""),
                "priority": task.get("priority", "medium"),
                "category": task.get("category", "implementation"),
                "source_section": task.get("source_section"),
                "confidence": task.get("confidence", 0.0),
                "sub_problem_index": task.get("sub_problem_index"),
                "status": status,
                "session_id": session_id,
                "problem_statement": problem_statement,
            }
        )
    return result


def _count_by_status(tasks: list[dict[str, Any]]) -> dict[str, int]:
    """Count tasks by status.

    Args:
        tasks: List of tasks with status field

    Returns:
        Dict mapping status -> count
    """
    counts = {"todo": 0, "doing": 0, "done": 0}
    for task in tasks:
        status = task.get("status", "todo")
        if status in counts:
            counts[status] += 1
    return counts


@router.get(
    "",
    response_model=AllActionsResponse,
    summary="Get all user actions",
    description="Get all actions across all sessions for the current user. Supports filtering by status, project, session (meeting), and tags.",
    responses={
        200: {"description": "Actions retrieved successfully"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
)
@handle_api_errors("get all actions")
async def get_all_actions(
    user_data: dict = Depends(get_current_user),
    status_filter: str | None = Query(
        None,
        description="Filter by status",
        pattern="^(todo|in_progress|blocked|in_review|done|cancelled)$",
    ),
    project_id: str | None = Query(None, description="Filter by project UUID"),
    session_id: str | None = Query(None, description="Filter by meeting/session UUID"),
    tag_ids: str | None = Query(
        None,
        description="Filter by tag UUIDs (comma-separated). Actions must have ALL specified tags.",
    ),
    limit: int = Query(100, ge=1, le=500, description="Max actions to fetch"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> AllActionsResponse:
    """Get all actions for the current user across all sessions.

    Args:
        user_data: Current user from auth
        status_filter: Optional filter by action status
        project_id: Optional filter by project UUID
        session_id: Optional filter by meeting/session UUID
        tag_ids: Optional comma-separated tag UUIDs (AND logic - must have all tags)
        limit: Maximum number of actions to fetch
        offset: Pagination offset

    Returns:
        AllActionsResponse with all actions grouped by session
    """
    user_id = user_data.get("user_id")
    is_admin = user_data.get("is_admin", False)
    logger.info(f"Fetching all actions for user {user_id} (admin={is_admin})")

    # Parse tag_ids from comma-separated string
    tag_id_list: list[str] | None = None
    if tag_ids:
        tag_id_list = [t.strip() for t in tag_ids.split(",") if t.strip()]

    # Get all actions from actions table
    # P1-007: Non-admin users only see actions from completed meetings
    actions = action_repository.get_by_user(
        user_id=user_id,
        status_filter=status_filter,
        project_id=project_id,
        session_id=session_id,
        tag_ids=tag_id_list,
        limit=limit,
        offset=offset,
        is_admin=is_admin,
    )

    # Group actions by session
    sessions_map: dict[str, dict[str, Any]] = {}
    all_actions_list: list[dict[str, Any]] = []

    for action in actions:
        session_id = action.get("source_session_id", "")

        # Get session info if not already fetched
        if session_id not in sessions_map:
            session = session_repository.get(session_id)
            if session:
                sessions_map[session_id] = {
                    "session_id": session_id,
                    "problem_statement": session.get("problem_statement", ""),
                    "session_status": session.get("status", ""),
                    "created_at": session.get("created_at"),
                    "tasks": [],
                    "task_count": 0,
                }

        # Format action for response
        # Use updated_at if available, otherwise fallback to created_at
        updated_at = action.get("updated_at") or action.get("created_at")
        session_info = sessions_map.get(session_id, {})
        action_data = {
            "id": str(action.get("id", "")),
            "title": action.get("title", ""),
            "description": action.get("description", ""),
            "what_and_how": action.get("what_and_how", []),
            "success_criteria": action.get("success_criteria", []),
            "kill_criteria": action.get("kill_criteria", []),
            "dependencies": [],  # Dependencies will come from action_dependencies table in Phase 2
            "timeline": action.get("timeline", ""),
            "priority": action.get("priority", "medium"),
            "category": action.get("category", "implementation"),
            "source_section": action.get("source_section"),
            "confidence": float(action.get("confidence", 0.0)),
            "sub_problem_index": action.get("sub_problem_index"),
            "status": action.get("status", "todo"),
            "session_id": session_id,
            "source_session_status": session_info.get("session_status"),
            "problem_statement": session_info.get("problem_statement", ""),
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

        all_actions_list.append(action_data)

        if session_id in sessions_map:
            sessions_map[session_id]["tasks"].append(action_data)
            sessions_map[session_id]["task_count"] += 1

    # Calculate status counts per session and globally
    for session_data in sessions_map.values():
        session_data["by_status"] = _count_by_status(session_data["tasks"])
        # Convert created_at to ISO string
        if session_data.get("created_at"):
            session_data["created_at"] = session_data["created_at"].isoformat()
        session_data["extracted_at"] = None  # Actions don't have extraction time

    global_by_status = _count_by_status(all_actions_list)

    logger.info(
        f"Found {len(all_actions_list)} actions across {len(sessions_map)} sessions for user {user_id}"
    )

    return AllActionsResponse(
        sessions=list(sessions_map.values()),
        total_tasks=len(all_actions_list),
        by_status=global_by_status,
    )


# =============================================================================
# Global Gantt Endpoint (MUST be before /{action_id} routes)
# =============================================================================


@router.get(
    "/gantt",
    response_model=GlobalGanttResponse,
    summary="Get global Gantt data",
    description="Get all actions formatted for Gantt chart visualization across all projects/sessions.",
    responses={
        200: {"description": "Gantt data retrieved successfully"},
    },
)
@handle_api_errors("get global gantt data")
async def get_global_gantt(
    user_data: dict = Depends(get_current_user),
    status_filter: str | None = Query(
        None,
        description="Filter by status",
        pattern="^(todo|in_progress|blocked|in_review|done|cancelled)$",
    ),
    project_id: str | None = Query(None, description="Filter by project UUID"),
    session_id: str | None = Query(None, description="Filter by meeting/session UUID"),
    tag_ids: str | None = Query(
        None,
        description="Filter by tag UUIDs (comma-separated). Actions must have ALL specified tags.",
    ),
) -> GlobalGanttResponse:
    """Get global Gantt data for all user actions.

    Args:
        user_data: Current user from auth
        status_filter: Optional filter by action status
        project_id: Optional filter by project UUID
        session_id: Optional filter by meeting/session UUID
        tag_ids: Optional comma-separated tag UUIDs

    Returns:
        GlobalGanttResponse with actions and dependencies
    """
    from datetime import date, timedelta

    user_id = user_data.get("user_id")
    is_admin = user_data.get("is_admin", False)
    logger.info(f"Fetching global Gantt data for user {user_id} (admin={is_admin})")

    # Parse tag_ids
    tag_id_list: list[str] | None = None
    if tag_ids:
        tag_id_list = [t.strip() for t in tag_ids.split(",") if t.strip()]

    # Get all actions
    # P1-007: Non-admin users only see actions from completed meetings
    actions = action_repository.get_by_user(
        user_id=user_id,
        status_filter=status_filter,
        project_id=project_id,
        session_id=session_id,
        tag_ids=tag_id_list,
        limit=500,
        offset=0,
        is_admin=is_admin,
    )

    # Format for Gantt chart
    gantt_actions: list[GanttActionData] = []
    all_dependencies: list[GanttDependency] = []
    today = date.today()

    # First pass: collect all actions
    action_data_map: dict[str, dict] = {}
    action_ids: list[str] = []

    for action in actions:
        action_id = str(action.get("id", ""))
        action_data_map[action_id] = action
        action_ids.append(action_id)

    # Batch fetch all dependencies in single query (fixes N+1)
    deps_batch = action_repository.get_dependencies_batch(action_ids)

    # Build deps_map from batch result
    deps_map: dict[str, list[tuple[str, int]]] = {}  # action_id -> [(depends_on_id, lag_days)]
    for action_id in action_ids:
        deps_map[action_id] = []
        for dep in deps_batch.get(action_id, []):
            depends_on_id = str(dep.get("depends_on_action_id", ""))
            lag_days = dep.get("lag_days", 0)
            deps_map[action_id].append((depends_on_id, lag_days))
            all_dependencies.append(
                GanttDependency(
                    action_id=action_id,
                    depends_on_id=depends_on_id,
                    dependency_type=dep.get("dependency_type", "finish_to_start"),
                    lag_days=lag_days,
                )
            )

    # Auto-schedule: calculate dates based on dependencies (topological sort)
    # Track computed end dates for dependency resolution
    computed_end_dates: dict[str, date] = {}
    computed_start_dates: dict[str, date] = {}

    def compute_dates(action_id: str, visited: set[str]) -> tuple[date, date]:
        """Recursively compute start/end dates respecting dependencies."""
        if action_id in computed_end_dates:
            return computed_start_dates[action_id], computed_end_dates[action_id]

        # Prevent cycles
        if action_id in visited:
            return today, today + timedelta(days=7)
        visited.add(action_id)

        action = action_data_map.get(action_id)
        if not action:
            return today, today + timedelta(days=7)

        duration_days = action.get("estimated_duration_days") or 7

        # Check if action has explicit dates set
        explicit_start = action.get("target_start_date") or action.get("estimated_start_date")
        explicit_end = action.get("target_end_date") or action.get("estimated_end_date")

        # Calculate earliest start based on dependencies
        earliest_start = today
        action_deps = deps_map.get(action_id, [])

        if action_deps:
            for dep_id, lag_days in action_deps:
                if dep_id in action_data_map:
                    _, dep_end = compute_dates(dep_id, visited.copy())
                    dep_earliest = dep_end + timedelta(days=lag_days)
                    if dep_earliest > earliest_start:
                        earliest_start = dep_earliest

        # Use explicit dates if set, otherwise use computed
        if explicit_start:
            original_start = explicit_start
            start_date = max(explicit_start, earliest_start) if action_deps else explicit_start
        else:
            original_start = earliest_start
            start_date = earliest_start

        # Calculate how much we shifted the start due to dependencies
        start_shift = (start_date - original_start).days if start_date > original_start else 0

        if explicit_end:
            # Shift end date by same amount if start was pushed forward
            end_date = explicit_end + timedelta(days=start_shift)
        else:
            end_date = start_date + timedelta(days=duration_days)

        # Ensure end is always after start (minimum 1 day duration)
        if end_date <= start_date:
            end_date = start_date + timedelta(days=max(duration_days, 1))

        computed_start_dates[action_id] = start_date
        computed_end_dates[action_id] = end_date
        return start_date, end_date

    # Compute dates for all actions
    for action_id in action_data_map:
        compute_dates(action_id, set())

    # Second pass: build gantt_actions with computed dates and colors
    progress_map = {
        "todo": 0,
        "in_progress": 50,
        "blocked": 25,
        "in_review": 75,
        "done": 100,
        "cancelled": 100,
        "failed": 100,
        "abandoned": 100,
        "replanned": 100,
    }

    # Get user's preferred color strategy and initialize color service
    user_strategy = GanttColorStrategy.BY_STATUS
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT gantt_color_strategy FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if row and row.get("gantt_color_strategy"):
                    user_strategy = row["gantt_color_strategy"]
    except Exception as e:
        logger.warning(f"Failed to get user color strategy: {e}")

    # Initialize color service
    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=False)
    color_service = GanttColorService(redis_client)

    for action_id, action in action_data_map.items():
        start_date = computed_start_dates.get(action_id, today)
        end_date = computed_end_dates.get(action_id, today + timedelta(days=7))
        status = action.get("status", "todo")
        progress = progress_map.get(status, 0)
        priority = action.get("priority", "medium")
        project_index = action.get("project_index", 0)

        # Assign colors based on strategy
        colors = color_service.assign_action_colors(
            action_id=action_id,
            status=status,
            priority=priority,
            project_index=project_index,
            strategy=user_strategy,
        )

        # Build dependency string for frappe-gantt
        dep_ids = [dep_id for dep_id, _ in deps_map.get(action_id, [])]

        gantt_actions.append(
            GanttActionData(
                id=action_id,
                name=action.get("title", "Untitled"),
                start=start_date.isoformat()
                if hasattr(start_date, "isoformat")
                else str(start_date),
                end=end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
                progress=progress,
                dependencies=",".join(dep_ids),
                status=status,
                priority=priority,
                session_id=action.get("source_session_id", ""),
                status_color=colors.get("status_color"),
                priority_color=colors.get("priority_color"),
                project_color=colors.get("project_color"),
            )
        )

    return GlobalGanttResponse(
        actions=gantt_actions,
        dependencies=all_dependencies,
    )


# =============================================================================
# Action Reminders Endpoints
# =============================================================================


@router.get(
    "/reminders",
    response_model=ActionRemindersResponse,
    summary="Get pending action reminders",
    description="Get actions needing reminders (overdue start, approaching deadline).",
    responses={
        200: {"description": "Reminders retrieved successfully"},
    },
)
@handle_api_errors("get action reminders")
async def get_action_reminders(
    user_data: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100, description="Max reminders to return"),
) -> ActionRemindersResponse:
    """Get pending action reminders for the current user.

    Returns actions that:
    - Have overdue start dates (todo status with passed anticipated start)
    - Have approaching deadlines (within 3 days)
    - Respect reminder frequency settings
    - Are not snoozed

    Args:
        user_data: Current user from auth
        limit: Maximum reminders to return

    Returns:
        ActionRemindersResponse with pending reminders
    """
    from backend.api.models import ActionReminderResponse, ActionRemindersResponse
    from backend.services.action_reminders import get_pending_reminders

    user_id = user_data.get("user_id")
    logger.info(f"Fetching pending reminders for user {user_id}")

    reminders = get_pending_reminders(user_id, limit=limit)

    return ActionRemindersResponse(
        reminders=[
            ActionReminderResponse(
                action_id=r.action_id,
                action_title=r.action_title,
                reminder_type=r.reminder_type,
                due_date=r.due_date.isoformat() if r.due_date else None,
                days_overdue=r.days_overdue,
                days_until_deadline=r.days_until_deadline,
                session_id=r.session_id,
                problem_statement=r.problem_statement,
            )
            for r in reminders
        ],
        total=len(reminders),
    )


# =============================================================================
# Action Stats Endpoint (Dashboard Progress Visualization)
# =============================================================================


@router.get(
    "/stats",
    response_model=ActionStatsResponse,
    summary="Get action statistics",
    description="Get daily action completion/creation stats and totals for dashboard visualization.",
    responses={
        200: {"description": "Stats retrieved successfully"},
    },
)
@handle_api_errors("get action stats")
async def get_action_stats(
    user_data: dict = Depends(get_current_user),
    days: int = Query(30, ge=7, le=365, description="Number of days to include (7-365)"),
) -> ActionStatsResponse:
    """Get action statistics for dashboard progress visualization.

    Args:
        user_data: Current user from auth
        days: Number of days to include (default 30, max 365 for annual heatmap)

    Returns:
        ActionStatsResponse with daily stats and totals
    """
    user_id = user_data.get("user_id")
    logger.info(f"Fetching action stats for user {user_id} (last {days} days)")

    # Get daily stats using SQL aggregation
    # Extended date range: past + future for estimated activities
    daily_query = """
        WITH date_series AS (
            SELECT generate_series(
                CURRENT_DATE - INTERVAL '%s days',
                CURRENT_DATE + INTERVAL '180 days',
                '1 day'::interval
            )::date AS date
        ),
        completed_counts AS (
            SELECT DATE(actual_end_date) AS date, COUNT(*) AS count
            FROM actions
            WHERE user_id = %s
              AND status IN ('done', 'cancelled')
              AND actual_end_date IS NOT NULL
              AND actual_end_date >= CURRENT_DATE - INTERVAL '%s days'
              AND deleted_at IS NULL
            GROUP BY DATE(actual_end_date)
        ),
        in_progress_counts AS (
            SELECT DATE(actual_start_date) AS date, COUNT(*) AS count
            FROM actions
            WHERE user_id = %s
              AND actual_start_date IS NOT NULL
              AND actual_start_date >= CURRENT_DATE - INTERVAL '%s days'
              AND deleted_at IS NULL
            GROUP BY DATE(actual_start_date)
        ),
        meetings_run_counts AS (
            SELECT DATE(created_at) AS date, COUNT(*) AS count
            FROM sessions
            WHERE user_id = %s
              AND created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(created_at)
        ),
        mentor_session_counts AS (
            SELECT TO_DATE(period, 'YYYY-MM-DD') AS date, count
            FROM user_usage
            WHERE user_id = %s
              AND metric = 'mentor_chats'
              AND LENGTH(period) = 10
              AND TO_DATE(period, 'YYYY-MM-DD') >= CURRENT_DATE - INTERVAL '%s days'
        ),
        estimated_start_counts AS (
            SELECT DATE(COALESCE(target_start_date, estimated_start_date)) AS date, COUNT(*) AS count
            FROM actions
            WHERE user_id = %s
              AND COALESCE(target_start_date, estimated_start_date) >= CURRENT_DATE
              AND actual_start_date IS NULL
              AND status NOT IN ('done', 'cancelled')
              AND deleted_at IS NULL
            GROUP BY DATE(COALESCE(target_start_date, estimated_start_date))
        ),
        estimated_completion_counts AS (
            SELECT DATE(COALESCE(target_end_date, estimated_end_date)) AS date, COUNT(*) AS count
            FROM actions
            WHERE user_id = %s
              AND COALESCE(target_end_date, estimated_end_date) >= CURRENT_DATE
              AND status NOT IN ('done', 'cancelled')
              AND deleted_at IS NULL
            GROUP BY DATE(COALESCE(target_end_date, estimated_end_date))
        )
        SELECT
            ds.date,
            COALESCE(cc.count, 0) AS completed_count,
            COALESCE(ip.count, 0) AS in_progress_count,
            COALESCE(mr.count, 0) AS sessions_run,
            COALESCE(ms.count, 0) AS mentor_sessions,
            COALESCE(es.count, 0) AS estimated_starts,
            COALESCE(ec.count, 0) AS estimated_completions
        FROM date_series ds
        LEFT JOIN completed_counts cc ON ds.date = cc.date
        LEFT JOIN in_progress_counts ip ON ds.date = ip.date
        LEFT JOIN meetings_run_counts mr ON ds.date = mr.date
        LEFT JOIN mentor_session_counts ms ON ds.date = ms.date
        LEFT JOIN estimated_start_counts es ON ds.date = es.date
        LEFT JOIN estimated_completion_counts ec ON ds.date = ec.date
        ORDER BY ds.date DESC
    """

    daily_rows = execute_query(
        daily_query,
        (days, user_id, days, user_id, days, user_id, days, user_id, days, user_id, user_id),
        fetch="all",
    )

    daily_stats = [
        DailyActionStat(
            date=row["date"].isoformat(),
            completed_count=row["completed_count"],
            in_progress_count=row["in_progress_count"],
            sessions_run=row["sessions_run"],
            mentor_sessions=row["mentor_sessions"],
            estimated_starts=row["estimated_starts"],
            estimated_completions=row["estimated_completions"],
        )
        for row in (daily_rows or [])
    ]

    # Get totals by status
    totals_query = """
        SELECT
            COALESCE(SUM(CASE WHEN status IN ('done', 'cancelled') THEN 1 ELSE 0 END), 0) AS completed,
            COALESCE(SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END), 0) AS in_progress,
            COALESCE(SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END), 0) AS todo
        FROM actions
        WHERE user_id = %s AND deleted_at IS NULL
    """

    totals_row = execute_query(totals_query, (user_id,), fetch="one")

    totals = ActionStatsTotals(
        completed=totals_row["completed"] if totals_row else 0,
        in_progress=totals_row["in_progress"] if totals_row else 0,
        todo=totals_row["todo"] if totals_row else 0,
    )

    logger.info(f"Found {len(daily_stats)} daily stats for user {user_id}")

    return ActionStatsResponse(
        daily=daily_stats,
        totals=totals,
    )


# =============================================================================
# Action Detail Endpoints (parametric routes after static ones)
# =============================================================================


@router.get(
    "/{action_id}",
    response_model=ActionDetailResponse,
    summary="Get single action details",
    description="Get detailed information about a specific action.",
    responses={
        200: {"description": "Action details retrieved successfully"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        404: {"description": "Action not found", "model": ErrorResponse},
    },
)
@handle_api_errors("get action detail")
async def get_action_detail(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ActionDetailResponse:
    """Get detailed information about a specific action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ActionDetailResponse with full action details
    """
    user_id = user_data.get("user_id")
    is_admin = user_data.get("is_admin", False)
    logger.info(f"Fetching action {action_id} for user {user_id} (admin={is_admin})")

    # Get action from actions table
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Verify user ownership
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Get session for problem_statement and status check
    session_id = action.get("source_session_id", "")
    session = session_repository.get(session_id)
    problem_statement = session.get("problem_statement", "") if session else ""
    session_status = session.get("status", "") if session else ""

    # P1-007: Non-admin users only see actions from completed or acknowledged-failed meetings
    if session and not is_admin:
        is_completed = session_status == "completed"
        is_acknowledged_failure = (
            session_status == "failed" and session.get("failure_acknowledged_at") is not None
        )
        if not is_completed and not is_acknowledged_failure:
            raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Format dates as ISO strings
    def to_iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return ActionDetailResponse(
        id=str(action.get("id", "")),
        title=action.get("title", ""),
        description=action.get("description", ""),
        what_and_how=action.get("what_and_how", []),
        success_criteria=action.get("success_criteria", []),
        kill_criteria=action.get("kill_criteria", []),
        dependencies=[],  # Dependencies will come from action_dependencies table in Phase 2
        timeline=action.get("timeline", ""),
        priority=action.get("priority", "medium"),
        category=action.get("category", "implementation"),
        source_section=action.get("source_section"),
        confidence=float(action.get("confidence", 0.0)),
        sub_problem_index=action.get("sub_problem_index"),
        status=action.get("status", "todo"),
        session_id=session_id,
        source_session_status=session_status if session_status else None,
        problem_statement=problem_statement,
        estimated_duration_days=action.get("estimated_duration_days"),
        target_start_date=to_iso(action.get("target_start_date")),
        target_end_date=to_iso(action.get("target_end_date")),
        estimated_start_date=to_iso(action.get("estimated_start_date")),
        estimated_end_date=to_iso(action.get("estimated_end_date")),
        actual_start_date=to_iso(action.get("actual_start_date")),
        actual_end_date=to_iso(action.get("actual_end_date")),
        blocking_reason=action.get("blocking_reason"),
        blocked_at=to_iso(action.get("blocked_at")),
        auto_unblock=action.get("auto_unblock", False),
        cancellation_reason=action.get("cancellation_reason"),
        cancelled_at=to_iso(action.get("cancelled_at")),
        project_id=action.get("project_id"),
    )


@router.post(
    "/{action_id}/start",
    response_model=ActionStartedResponse,
    summary="Start an action",
    description="Mark action as in_progress and set actual_start_date.",
    responses={
        200: {"description": "Action started successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("start action")
async def start_action(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ActionStartedResponse:
    """Start an action (mark as in_progress).

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ActionStartedResponse with success message
    """
    user_id = user_data.get("user_id")
    logger.info(f"Starting action {action_id} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Start action
    success = action_repository.start_action(action_id, user_id)
    if not success:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Action cannot be started (already in progress or done)",
            400,
        )

    return ActionStartedResponse(message="Action started successfully", action_id=action_id)


@router.post(
    "/{action_id}/complete",
    response_model=ActionCompletedResponse,
    summary="Complete an action",
    description="Mark action as done and set actual_end_date. Auto-unblocks dependent actions.",
    responses={
        200: {"description": "Action completed successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("complete action")
async def complete_action(
    action_id: str,
    request: ActionCompleteRequest | None = None,
    user_data: dict = Depends(get_current_user),
) -> ActionCompletedResponse:
    """Complete an action (mark as done).

    Args:
        action_id: Action UUID
        request: Optional post-mortem data (lessons_learned, went_well)
        user_data: Current user from auth

    Returns:
        ActionCompletedResponse with success message and unblocked actions
    """
    user_id = user_data.get("user_id")
    logger.info(f"Completing action {action_id} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Extract post-mortem data if provided
    lessons_learned = request.lessons_learned if request else None
    went_well = request.went_well if request else None

    # Complete action with optional post-mortem
    success = action_repository.complete_action(
        action_id, user_id, lessons_learned=lessons_learned, went_well=went_well
    )
    if not success:
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "Action cannot be completed (already done)", 400
        )

    # Auto-unblock dependent actions
    unblocked_ids = action_repository.auto_unblock_dependents(action_id, user_id)
    if unblocked_ids:
        logger.info(f"Auto-unblocked {len(unblocked_ids)} actions after completing {action_id}")

    # Auto-generate project from completed action (non-blocking)
    generated_project = None
    try:
        from backend.services.project_generator import maybe_generate_project

        generated_project = await maybe_generate_project(action_id, user_id)
        if generated_project:
            logger.info(
                f"Auto-generated/linked project '{generated_project.get('name')}' "
                f"from action {action_id}"
            )
    except Exception as e:
        logger.debug(f"Project auto-generation failed (non-blocking): {e}")

    # Create 28-day delayed metric refresh triggers based on action content
    try:
        from backend.services.insight_staleness import (
            create_action_metric_triggers,
            extract_metrics_from_action,
        )
        from bo1.state.repositories import user_repository

        # Extract affected metrics from action title/description
        affected_metrics = extract_metrics_from_action(
            action.get("title", ""),
            action.get("description"),
        )

        if affected_metrics:
            context_data = user_repository.get_context(user_id)
            if context_data:
                # Only create triggers for metrics user has set
                valid_metrics = [m for m in affected_metrics if context_data.get(m)]
                if valid_metrics:
                    # Create triggers for 28 days from now
                    completed_at = datetime.now(UTC)
                    new_triggers = create_action_metric_triggers(
                        action_id=action_id,
                        action_title=action.get("title", ""),
                        completed_at=completed_at,
                        affected_metrics=valid_metrics,
                    )

                    # Append to existing triggers
                    existing_triggers = context_data.get("action_metric_triggers", [])
                    context_data["action_metric_triggers"] = existing_triggers + new_triggers
                    user_repository.save_context(user_id, context_data)
                    logger.info(
                        f"Created {len(new_triggers)} delayed metric triggers for action {action_id}"
                    )
    except Exception as e:
        logger.debug(f"Action metric trigger creation failed (non-blocking): {e}")

    project_info = None
    if generated_project:
        project_info = {
            "id": str(generated_project.get("id")),
            "name": generated_project.get("name"),
        }

    return ActionCompletedResponse(
        message="Action completed successfully",
        action_id=action_id,
        unblocked_actions=unblocked_ids,
        generated_project=project_info,
    )


@router.post(
    "/{action_id}/close",
    response_model=ActionCloseResponse,
    summary="Close an action",
    description="Mark action as failed or abandoned with a reason.",
    responses={
        200: {"description": "Action closed successfully"},
        400: {"description": "Invalid status transition"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("close action")
async def close_action(
    action_id: str,
    request: ActionCloseRequest,
    user_data: dict = Depends(get_current_user),
) -> ActionCloseResponse:
    """Close an action as failed or abandoned.

    Args:
        action_id: Action UUID
        request: Close request with status and reason
        user_data: Current user from auth

    Returns:
        ActionCloseResponse with closed action details
    """
    user_id = user_data.get("user_id")
    logger.info(f"Closing action {action_id} as {request.status} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Validate transition
    current_status = action.get("status", "todo")
    valid, error_msg = action_repository.validate_status_transition(current_status, request.status)
    if not valid:
        raise http_error(ErrorCode.VALIDATION_ERROR, error_msg, 400)

    # Close action with reason
    success = action_repository.update_status(
        action_id,
        request.status,
        user_id,
        cancellation_reason=request.reason,  # Reused for closure reason
    )
    if not success:
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to close action", 400)

    return ActionCloseResponse(
        action_id=action_id,
        status=request.status,
        message=f"Action closed as {request.status}",
    )


@router.post(
    "/{action_id}/clone-replan",
    response_model=ActionCloneReplanResponse,
    summary="Replan action by cloning",
    description="Create a new action from a failed/abandoned action. Original is marked as 'replanned'.",
    responses={
        200: {"description": "Action replanned successfully"},
        400: {"description": "Action cannot be replanned (wrong status)"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("clone-replan action")
async def clone_replan_action(
    action_id: str,
    request: ActionCloneReplanRequest,
    user_data: dict = Depends(get_current_user),
) -> ActionCloneReplanResponse:
    """Create a new action by replanning a failed/abandoned one.

    Args:
        action_id: Original action UUID
        request: Replan request with optional modifications
        user_data: Current user from auth

    Returns:
        ActionCloneReplanResponse with new action ID
    """
    from datetime import date as date_type

    user_id = user_data.get("user_id")
    logger.info(f"Clone-replanning action {action_id} for user {user_id}")

    # Parse target date if provided
    new_target_date = None
    if request.new_target_date:
        try:
            new_target_date = date_type.fromisoformat(request.new_target_date)
        except ValueError as err:
            raise http_error(
                ErrorCode.VALIDATION_ERROR, "Invalid date format. Use YYYY-MM-DD", 400
            ) from err

    # Replan action (creates new action, marks original as 'replanned')
    new_action = action_repository.replan_action(
        action_id,
        user_id,
        new_steps=request.new_steps,
        new_target_date=new_target_date,
    )

    if not new_action:
        # Check if action exists and has correct status
        action = action_repository.get(action_id)
        if not action:
            raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
        if action.get("user_id") != user_id:
            raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
        current_status = action.get("status", "")
        if current_status not in ("failed", "abandoned"):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                f"Only failed or abandoned actions can be replanned (current: {current_status})",
                400,
            )
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to replan action", 400)

    return ActionCloneReplanResponse(
        new_action_id=str(new_action["id"]),
        original_action_id=action_id,
        message="Action replanned successfully",
    )


@router.patch(
    "/{action_id}/status",
    response_model=ActionStatusUpdatedResponse,
    summary="Update action status",
    description="Update action status with optional blocking reason. Validates status transitions.",
    responses={
        200: {"description": "Action status updated successfully"},
        400: {"description": "Invalid status transition"},
        404: {"description": "Action not found"},
        503: {"description": "Service unavailable - database pool exhausted"},
    },
)
@handle_api_errors("update action status")
async def update_action_status(
    action_id: str,
    status_update: ActionStatusUpdate,
    user_data: dict = Depends(get_current_user),
    _pool_check: None = Depends(check_pool_health),
) -> ActionStatusUpdatedResponse:
    """Update action status.

    Args:
        action_id: Action UUID
        status_update: Status update request
        user_data: Current user from auth

    Returns:
        ActionStatusUpdatedResponse with success message and unblocked actions
    """
    user_id = user_data.get("user_id")
    logger.info(f"Updating action {action_id} status to {status_update.status} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Validate status transition
    current_status = action.get("status", "todo")
    is_valid, error = action_repository.validate_status_transition(
        current_status, status_update.status
    )
    if not is_valid:
        raise http_error(ErrorCode.VALIDATION_ERROR, error, 400)

    # Validate blocking_reason required for blocked status
    if status_update.status == "blocked" and not status_update.blocking_reason:
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "blocking_reason required when status is 'blocked'", 400
        )

    # Validate cancellation_reason required for cancelled status
    if status_update.status == "cancelled" and not status_update.cancellation_reason:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "cancellation_reason required when status is 'cancelled'",
            400,
        )

    # Auto-set replan_suggested_at when cancelling
    replan_suggested_at = status_update.replan_suggested_at
    if status_update.status == "cancelled" and not replan_suggested_at:
        replan_suggested_at = datetime.utcnow()

    # Update status
    success = action_repository.update_status(
        action_id=action_id,
        status=status_update.status,
        user_id=user_id,
        blocking_reason=status_update.blocking_reason,
        auto_unblock=status_update.auto_unblock,
        cancellation_reason=status_update.cancellation_reason,
        failure_reason_category=status_update.failure_reason_category,
        replan_suggested_at=replan_suggested_at,
    )

    if not success:
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to update action status", 400)

    # Auto-unblock dependent actions if completing
    unblocked_ids: list[str] = []
    if status_update.status in ("done", "cancelled"):
        unblocked_ids = action_repository.auto_unblock_dependents(action_id, user_id)
        if unblocked_ids:
            logger.info(
                f"Auto-unblocked {len(unblocked_ids)} actions after {status_update.status} on {action_id}"
            )

        # Remove from Google Calendar when completed/cancelled
        try:
            from backend.services.action_calendar_sync import remove_action_from_calendar

            remove_action_from_calendar(action_id, user_id)
        except Exception as e:
            logger.debug(f"Calendar removal failed (non-blocking): {e}")

    # Context Auto-Update: Extract business context from cancellation/blocking reasons
    # E.g., "Hired 2 more engineers" → team_size update
    notes_text = status_update.cancellation_reason or status_update.blocking_reason
    if notes_text:
        try:
            from backend.services.context_extractor import (
                ContextUpdateSource,
                extract_context_updates,
                filter_high_confidence_updates,
            )

            updates = await extract_context_updates(notes_text, None, ContextUpdateSource.ACTION)

            if updates:
                from bo1.state.repositories import user_repository

                existing_context = user_repository.get_context(user_id) or {}
                high_conf, low_conf = filter_high_confidence_updates(updates)

                # Auto-apply high confidence updates
                if high_conf:
                    metric_history = existing_context.get("context_metric_history", {})
                    for upd in high_conf:
                        existing_context[upd.field_name] = upd.new_value
                        logger.info(
                            f"Action {action_id}: Auto-applied context: "
                            f"{upd.field_name}={upd.new_value} (conf={upd.confidence:.2f})"
                        )

                        if upd.field_name not in metric_history:
                            metric_history[upd.field_name] = []
                        metric_history[upd.field_name].insert(
                            0,
                            {
                                "value": upd.new_value,
                                "recorded_at": upd.extracted_at,
                                "source_type": upd.source_type.value,
                                "source_id": action_id,
                            },
                        )
                        metric_history[upd.field_name] = metric_history[upd.field_name][:10]

                    existing_context["context_metric_history"] = metric_history

                # Queue low confidence updates for review
                if low_conf:
                    import uuid

                    pending = existing_context.get("pending_updates", [])
                    for upd in low_conf:
                        if len(pending) >= 5:
                            break
                        pending.append(
                            {
                                "id": str(uuid.uuid4())[:8],
                                "field_name": upd.field_name,
                                "new_value": upd.new_value,
                                "current_value": existing_context.get(upd.field_name),
                                "confidence": upd.confidence,
                                "source_type": upd.source_type.value,
                                "source_text": upd.source_text,
                                "extracted_at": upd.extracted_at,
                            }
                        )
                    existing_context["pending_updates"] = pending

                if high_conf or low_conf:
                    user_repository.save_context(user_id, existing_context)

        except Exception as e:
            # Non-blocking
            logger.debug(f"Context extraction from action failed (non-blocking): {e}")

    # Auto-generate project from completed action (when status is done)
    generated_project = None
    if status_update.status == "done":
        try:
            from backend.services.project_generator import maybe_generate_project

            generated_project = await maybe_generate_project(action_id, user_id)
            if generated_project:
                logger.info(
                    f"Auto-generated/linked project '{generated_project.get('name')}' "
                    f"from action {action_id}"
                )
        except Exception as e:
            logger.debug(f"Project auto-generation failed (non-blocking): {e}")

    project_info = None
    if generated_project:
        project_info = GeneratedProjectInfo(
            id=str(generated_project.get("id")),
            name=generated_project.get("name"),
        )

    return ActionStatusUpdatedResponse(
        message="Action status updated successfully",
        action_id=action_id,
        status=status_update.status,
        unblocked_actions=unblocked_ids,
        generated_project=project_info,
    )


# =============================================================================
# Replanning Context Endpoint
# =============================================================================


@router.get(
    "/{action_id}/replan-context",
    response_model=ActionReplanContextResponse,
    summary="Get replanning context for action",
    description="Get context for creating a new meeting to replan a cancelled action.",
    responses={
        200: {"description": "Context retrieved successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("get replan context")
async def get_replan_context(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ActionReplanContextResponse:
    """Get context for replanning a cancelled action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ActionReplanContextResponse with problem_statement, failure_reason, related_actions
    """
    from backend.services.action_context import extract_replan_context

    user_id = user_data.get("user_id")
    logger.info(f"Fetching replan context for action {action_id} (user={user_id})")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Extract context
    context = extract_replan_context(action_id)

    # Convert related_actions to typed models
    related = [
        RelatedAction(
            id=str(a.get("id", "")),
            title=a.get("title", ""),
            status=a.get("status", ""),
        )
        for a in context.get("related_actions", [])
    ]

    return ActionReplanContextResponse(
        action_id=context.get("action_id", str(action_id)),
        action_title=context.get("action_title", ""),
        problem_statement=context.get("problem_statement", ""),
        failure_reason_text=context.get("failure_reason_text", ""),
        failure_reason_category=context.get("failure_reason_category", "unknown"),
        related_actions=related,
        parent_session_id=context.get("parent_session_id"),
        business_context=context.get("business_context"),
    )


# =============================================================================
# Delete Endpoint
# =============================================================================


@router.delete(
    "/{action_id}",
    response_model=ActionDeletedResponse,
    summary="Delete action (soft delete)",
    description="Soft delete an action. Admin users can restore deleted actions.",
    responses={
        200: {"description": "Action deleted successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("delete action")
async def delete_action(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ActionDeletedResponse:
    """Soft delete an action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ActionDeletedResponse with success message
    """
    user_id = user_data.get("user_id")
    logger.info(f"Soft deleting action {action_id} for user {user_id}")

    # Get action and verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Check if already deleted (idempotent delete)
    if action.get("deleted_at") is not None:
        logger.info(f"Action {action_id} already deleted, returning success")
        return ActionDeletedResponse(
            message="Action deleted successfully",
            action_id=action_id,
        )

    # Soft delete
    success = action_repository.delete(action_id)
    if not success:
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to delete action", 400)

    logger.info(f"Successfully soft-deleted action {action_id}")

    return ActionDeletedResponse(
        message="Action deleted successfully",
        action_id=action_id,
    )


# =============================================================================
# Dependency Endpoints
# =============================================================================


@router.get(
    "/{action_id}/dependencies",
    response_model=DependencyListResponse,
    summary="Get action dependencies",
    description="Get all dependencies for an action (what this action depends on).",
    responses={
        200: {"description": "Dependencies retrieved successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("get action dependencies")
async def get_action_dependencies(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> DependencyListResponse:
    """Get all dependencies for an action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        DependencyListResponse with all dependencies
    """
    user_id = user_data.get("user_id")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Get dependencies
    dependencies = action_repository.get_dependencies(action_id)
    has_incomplete, _ = action_repository.has_incomplete_dependencies(action_id)

    return DependencyListResponse(
        action_id=action_id,
        dependencies=[
            DependencyResponse(
                action_id=str(dep["action_id"]),
                depends_on_action_id=str(dep["depends_on_action_id"]),
                depends_on_title=dep["depends_on_title"],
                depends_on_status=dep["depends_on_status"],
                dependency_type=dep["dependency_type"],
                lag_days=dep["lag_days"],
                created_at=dep["created_at"].isoformat() if dep["created_at"] else "",
            )
            for dep in dependencies
        ],
        has_incomplete=has_incomplete,
    )


@router.post(
    "/{action_id}/dependencies",
    response_model=DependencyAddedResponse,
    summary="Add action dependency",
    description="Add a dependency to an action. Auto-blocks if dependency is incomplete.",
    responses={
        200: {"description": "Dependency added successfully"},
        400: {"description": "Circular dependency or invalid action"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("add action dependency")
async def add_action_dependency(
    action_id: str,
    dependency: DependencyCreate,
    user_data: dict = Depends(get_current_user),
) -> DependencyAddedResponse:
    """Add a dependency to an action.

    Args:
        action_id: Action UUID
        dependency: Dependency details
        user_data: Current user from auth

    Returns:
        DependencyAddedResponse with auto-block info
    """
    user_id = user_data.get("user_id")
    logger.info(f"Adding dependency on {dependency.depends_on_action_id} to action {action_id}")

    # Verify ownership of source action
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Verify target action exists and belongs to user
    target_action = action_repository.get(dependency.depends_on_action_id)
    if not target_action:
        raise http_error(ErrorCode.NOT_FOUND, "Target action not found", 400)
    if target_action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Target action not found", 400)

    # Prevent self-dependency
    if action_id == dependency.depends_on_action_id:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Action cannot depend on itself", 400)

    # Add dependency
    result = action_repository.add_dependency(
        action_id=action_id,
        depends_on_action_id=dependency.depends_on_action_id,
        user_id=user_id,
        dependency_type=dependency.dependency_type,
        lag_days=dependency.lag_days,
    )

    if result is None:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Circular dependency detected. Adding this dependency would create a cycle.",
            400,
        )

    # Check if action was auto-blocked
    updated_action = action_repository.get(action_id)
    was_blocked = updated_action and updated_action.get("status") == "blocked"

    return DependencyAddedResponse(
        message="Dependency added successfully",
        action_id=action_id,
        depends_on_action_id=dependency.depends_on_action_id,
        auto_blocked=was_blocked,
        blocking_reason=updated_action.get("blocking_reason") if was_blocked else None,
    )


@router.delete(
    "/{action_id}/dependencies/{depends_on_id}",
    response_model=DependencyRemovedResponse,
    summary="Remove action dependency",
    description="Remove a dependency from an action. May auto-unblock if no more incomplete dependencies.",
    responses={
        200: {"description": "Dependency removed successfully"},
        404: {"description": "Action or dependency not found"},
    },
)
@handle_api_errors("remove action dependency")
async def remove_action_dependency(
    action_id: str,
    depends_on_id: str,
    user_data: dict = Depends(get_current_user),
) -> DependencyRemovedResponse:
    """Remove a dependency from an action.

    Args:
        action_id: Action UUID
        depends_on_id: UUID of the action being depended on
        user_data: Current user from auth

    Returns:
        DependencyRemovedResponse with auto-unblock info
    """
    user_id = user_data.get("user_id")
    logger.info(f"Removing dependency on {depends_on_id} from action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Get current status before removal
    was_blocked = action.get("status") == "blocked"

    # Remove dependency
    success = action_repository.remove_dependency(
        action_id=action_id,
        depends_on_action_id=depends_on_id,
        user_id=user_id,
    )

    if not success:
        raise http_error(ErrorCode.NOT_FOUND, "Dependency not found", 404)

    # Check if action was auto-unblocked
    updated_action = action_repository.get(action_id)
    was_unblocked = was_blocked and updated_action and updated_action.get("status") != "blocked"

    return DependencyRemovedResponse(
        message="Dependency removed successfully",
        action_id=action_id,
        depends_on_id=depends_on_id,
        auto_unblocked=was_unblocked,
        new_status=updated_action.get("status") if updated_action else None,
    )


# =============================================================================
# Block/Unblock Convenience Endpoints
# =============================================================================


@router.post(
    "/{action_id}/block",
    response_model=ActionBlockedResponse,
    summary="Block an action",
    description="Block an action with a reason. Validates status transition.",
    responses={
        200: {"description": "Action blocked successfully"},
        400: {"description": "Invalid status transition"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("block action")
async def block_action(
    action_id: str,
    block_request: BlockActionRequest,
    user_data: dict = Depends(get_current_user),
) -> ActionBlockedResponse:
    """Block an action with a reason.

    Args:
        action_id: Action UUID
        block_request: Block request with reason
        user_data: Current user from auth

    Returns:
        ActionBlockedResponse with success message
    """
    user_id = user_data.get("user_id")
    logger.info(f"Blocking action {action_id}: {block_request.blocking_reason}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Block action
    success = action_repository.block_action(
        action_id=action_id,
        user_id=user_id,
        blocking_reason=block_request.blocking_reason,
        auto_unblock=block_request.auto_unblock,
    )

    if not success:
        current_status = action.get("status", "unknown")
        raise http_error(
            ErrorCode.VALIDATION_ERROR, f"Cannot block action with status '{current_status}'", 400
        )

    return ActionBlockedResponse(
        message="Action blocked successfully",
        action_id=action_id,
        blocking_reason=block_request.blocking_reason,
        auto_unblock=block_request.auto_unblock,
    )


@router.post(
    "/{action_id}/unblock",
    response_model=ActionUnblockedResponse,
    summary="Unblock an action",
    description="Unblock a blocked action. Validates status transition.",
    responses={
        200: {"description": "Action unblocked successfully"},
        400: {"description": "Action not blocked or has incomplete dependencies"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("unblock action")
async def unblock_action(
    action_id: str,
    unblock_request: UnblockActionRequest | None = None,
    user_data: dict = Depends(get_current_user),
) -> ActionUnblockedResponse:
    """Unblock a blocked action.

    Args:
        action_id: Action UUID
        unblock_request: Optional unblock request with target status
        user_data: Current user from auth

    Returns:
        ActionUnblockedResponse with success message
    """
    user_id = user_data.get("user_id")
    target_status = unblock_request.target_status if unblock_request else "todo"
    logger.info(f"Unblocking action {action_id} to status '{target_status}'")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Check if action is blocked
    if action.get("status") != "blocked":
        raise http_error(ErrorCode.VALIDATION_ERROR, "Action is not blocked", 400)

    # Warn about incomplete dependencies (but allow unblock)
    has_incomplete, incomplete_deps = action_repository.has_incomplete_dependencies(action_id)

    # Unblock action
    success = action_repository.unblock_action(
        action_id=action_id,
        user_id=user_id,
        target_status=target_status,
    )

    if not success:
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to unblock action", 400)

    warning = None
    incomplete_dep_info = None
    if has_incomplete:
        warning = "Action has incomplete dependencies"
        incomplete_dep_info = [
            IncompleteDependencyInfo(
                id=str(dep["depends_on_action_id"]),
                title=dep["title"],
            )
            for dep in incomplete_deps
        ]

    return ActionUnblockedResponse(
        message="Action unblocked successfully",
        action_id=action_id,
        new_status=target_status,
        warning=warning,
        incomplete_dependencies=incomplete_dep_info,
    )


# =============================================================================
# Suggest Unblock Paths (AI-powered)
# =============================================================================


@router.post(
    "/{action_id}/suggest-unblock",
    response_model=UnblockPathsResponse,
    summary="Suggest ways to unblock a blocked action",
    description="Uses AI to generate 3-5 concrete suggestions for unblocking a stuck action.",
    responses={
        200: {"description": "Suggestions generated successfully"},
        400: {"description": "Action is not blocked", "model": ErrorResponse},
        404: {"description": "Action not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": RateLimitResponse},
    },
)
@limiter.limit("5/minute")
@handle_api_errors("suggest unblock paths")
async def suggest_unblock_paths(
    request: Request,
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> UnblockPathsResponse:
    """Generate AI suggestions for unblocking a blocked action.

    Rate limited to 5 requests per minute per user to control LLM costs.

    Args:
        request: FastAPI request (for rate limiter)
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        UnblockPathsResponse with 3-5 suggestions
    """
    user_id = user_data.get("user_id")
    logger.info(f"Generating unblock suggestions for action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Require blocked status
    if action.get("status") != "blocked":
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "Action must be blocked to suggest unblock paths", 400
        )

    # Get project name for context if available
    project_name = None
    project_id = action.get("project_id")
    if project_id:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name FROM projects WHERE id = %s",
                    (project_id,),
                )
                row = cur.fetchone()
                if row:
                    project_name = row["name"]

    # Generate suggestions
    analyzer = get_blocker_analyzer()
    suggestions = await analyzer.suggest_unblock_paths(
        title=action.get("name", ""),
        description=action.get("description"),
        blocking_reason=action.get("blocking_reason"),
        project_name=project_name,
    )

    return UnblockPathsResponse(
        action_id=action_id,
        suggestions=[
            UnblockSuggestionModel(
                approach=s.approach,
                rationale=s.rationale,
                effort_level=s.effort_level.value,
            )
            for s in suggestions
        ],
    )


# =============================================================================
# Escalate Blocker to Meeting
# =============================================================================


@router.post(
    "/{action_id}/escalate-blocker",
    response_model=EscalateBlockerResponse,
    summary="Escalate blocked action to a meeting",
    description="Create a focused meeting session to resolve a blocked action with AI personas.",
    responses={
        200: {"description": "Meeting created successfully"},
        400: {"description": "Action is not blocked", "model": ErrorResponse},
        404: {"description": "Action not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": RateLimitResponse},
    },
)
@limiter.limit("1/minute")
@handle_api_errors("escalate blocker")
async def escalate_blocker(
    request: Request,
    action_id: str,
    body: EscalateBlockerRequest | None = None,
    user_data: dict = Depends(get_current_user),
) -> EscalateBlockerResponse:
    """Escalate a blocked action to a meeting for AI-assisted resolution.

    Creates a deliberation session pre-populated with action context,
    blocking reason, and optional unblock suggestions.

    Rate limited to 1 request per minute per user.

    Args:
        request: FastAPI request (for rate limiter)
        action_id: Action UUID
        body: Optional request body with include_suggestions flag
        user_data: Current user from auth

    Returns:
        EscalateBlockerResponse with session_id and redirect_url
    """
    from backend.services.blocker_analyzer import escalate_blocked_action

    user_id = user_data.get("user_id")
    include_suggestions = body.include_suggestions if body else True

    logger.info(f"Escalating blocked action {action_id} to meeting for user {user_id}")

    try:
        result = await escalate_blocked_action(
            action_id=action_id,
            user_id=user_id,
            include_suggestions=include_suggestions,
        )
        return EscalateBlockerResponse(
            session_id=result["session_id"],
            redirect_url=result["redirect_url"],
        )
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "Action not found" or error_msg == "Not authorized":
            raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404) from None
        if error_msg == "Action is not blocked":
            raise http_error(ErrorCode.VALIDATION_ERROR, "Action is not blocked", 400) from None
        if error_msg == "Service temporarily unavailable":
            raise http_error(ErrorCode.SERVICE_UNAVAILABLE, error_msg, 503) from None
        raise http_error(ErrorCode.VALIDATION_ERROR, error_msg, 400) from None


# =============================================================================
# Replanning Endpoint
# =============================================================================


@router.post(
    "/{action_id}/replan",
    response_model=ReplanResponse,
    summary="Request AI replanning for blocked action",
    description="Creates a new deliberation session to help unblock the action with AI assistance.",
    responses={
        200: {"description": "Replanning session created or already exists"},
        400: {"description": "Action is not blocked"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("request replan")
async def request_replan(
    action_id: str,
    replan_request: ReplanRequest | None = None,
    user_data: dict = Depends(get_current_user),
) -> ReplanResponse:
    """Request AI replanning for a blocked action.

    Creates a new deliberation session that includes context about the blocked
    action, its dependencies, and the project it belongs to. The AI board will
    deliberate on alternative approaches to unblock the action.

    Args:
        action_id: Action UUID
        replan_request: Optional additional context from user
        user_data: Current user from auth

    Returns:
        ReplanResponse with session_id and redirect URL

    Raises:
        HTTPException: If action not found, not owned by user, or not blocked
    """
    user_id = user_data.get("user_id")
    additional_context = replan_request.additional_context if replan_request else None

    logger.info(f"User {user_id} requesting replan for action {action_id}")

    try:
        result = replanning_service.create_replan_session(
            action_id=action_id,
            user_id=user_id,
            additional_context=additional_context,
        )

        return ReplanResponse(
            session_id=result["session_id"],
            action_id=result["action_id"],
            message=result["message"],
            redirect_url=result["redirect_url"],
            is_existing=result.get("is_existing", False),
        )

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise http_error(ErrorCode.NOT_FOUND, error_msg, 404) from None
        elif "not blocked" in error_msg.lower():
            raise http_error(ErrorCode.VALIDATION_ERROR, error_msg, 400) from None
        else:
            raise http_error(ErrorCode.VALIDATION_ERROR, error_msg, 400) from None
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to create replan session: {e}",
            exc_info=True,
            action_id=action_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            "Failed to create replanning session. Please try again.",
            500,
        ) from None


# =============================================================================
# Date Management Endpoints
# =============================================================================


@router.patch(
    "/{action_id}/dates",
    response_model=ActionDatesResponse,
    summary="Update action dates",
    description="Update target dates and/or timeline. Triggers cascade recalculation for dependents.",
    responses={
        200: {"description": "Dates updated successfully"},
        400: {"description": "Invalid date format or date validation failed"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("update action dates")
async def update_action_dates(
    action_id: str,
    dates_update: ActionDatesUpdate,
    user_data: dict = Depends(get_current_user),
) -> ActionDatesResponse:
    """Update action dates and trigger cascade recalculation.

    Args:
        action_id: Action UUID
        dates_update: Dates update request
        user_data: Current user from auth

    Returns:
        ActionDatesResponse with updated dates and cascade count
    """
    from datetime import datetime

    from bo1.utils.timeline_parser import parse_timeline

    user_id = user_data.get("user_id")
    logger.info(f"Updating dates for action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Parse dates
    target_start = None
    target_end = None

    if dates_update.target_start_date:
        try:
            target_start = datetime.strptime(dates_update.target_start_date, "%Y-%m-%d").date()
        except ValueError:
            raise http_error(
                ErrorCode.VALIDATION_ERROR, "Invalid target_start_date format", 400
            ) from None

    if dates_update.target_end_date:
        try:
            target_end = datetime.strptime(dates_update.target_end_date, "%Y-%m-%d").date()
        except ValueError:
            raise http_error(
                ErrorCode.VALIDATION_ERROR, "Invalid target_end_date format", 400
            ) from None

    # Validate target_end >= target_start
    if target_start and target_end and target_end < target_start:
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "target_end_date must be >= target_start_date", 400
        )

    # Update timeline and estimated_duration_days if provided
    if dates_update.timeline:
        estimated_duration = parse_timeline(dates_update.timeline)

        # Direct SQL update for timeline (since update_dates doesn't handle timeline)
        execute_query(
            """
            UPDATE actions
            SET timeline = %s,
                estimated_duration_days = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (dates_update.timeline, estimated_duration, action_id),
            fetch="none",
        )

    # Update target dates if provided
    if target_start or target_end:
        action_repository.update_dates(
            action_id=action_id,
            user_id=user_id,
            target_start_date=target_start,
            target_end_date=target_end,
        )

    # Trigger cascade recalculation
    updated_ids = action_repository.recalculate_dates_cascade(action_id, user_id)

    # Get updated action
    updated_action = action_repository.get(action_id)

    # Sync to Google Calendar if connected (non-blocking)
    try:
        from backend.services.action_calendar_sync import sync_action_to_calendar

        sync_action_to_calendar(action_id, user_id)
    except Exception as e:
        logger.debug(f"Calendar sync failed (non-blocking): {e}")

    # Format dates as ISO strings
    def to_iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return ActionDatesResponse(
        action_id=action_id,
        target_start_date=to_iso(updated_action.get("target_start_date")),
        target_end_date=to_iso(updated_action.get("target_end_date")),
        estimated_start_date=to_iso(updated_action.get("estimated_start_date")),
        estimated_end_date=to_iso(updated_action.get("estimated_end_date")),
        estimated_duration_days=updated_action.get("estimated_duration_days"),
        cascade_updated=len(updated_ids),
    )


@router.post(
    "/{action_id}/recalculate-dates",
    response_model=ActionDatesResponse,
    summary="Recalculate action dates",
    description="Force recalculation of estimated dates based on dependencies.",
    responses={
        200: {"description": "Dates recalculated successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("recalculate action dates")
async def recalculate_action_dates(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ActionDatesResponse:
    """Force recalculation of estimated dates for an action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ActionDatesResponse with recalculated dates
    """
    user_id = user_data.get("user_id")
    logger.info(f"Recalculating dates for action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Trigger cascade recalculation
    updated_ids = action_repository.recalculate_dates_cascade(action_id, user_id)

    # Get updated action
    updated_action = action_repository.get(action_id)

    # Format dates as ISO strings
    def to_iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return ActionDatesResponse(
        action_id=action_id,
        target_start_date=to_iso(updated_action.get("target_start_date")),
        target_end_date=to_iso(updated_action.get("target_end_date")),
        estimated_start_date=to_iso(updated_action.get("estimated_start_date")),
        estimated_end_date=to_iso(updated_action.get("estimated_end_date")),
        estimated_duration_days=updated_action.get("estimated_duration_days"),
        cascade_updated=len(updated_ids),
    )


# =============================================================================
# Action Updates Endpoints (Phase 5)
# =============================================================================


@router.get(
    "/{action_id}/updates",
    response_model=ActionUpdatesResponse,
    summary="Get action updates",
    description="Get activity timeline for an action (progress updates, notes, status changes).",
    responses={
        200: {"description": "Updates retrieved successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("get action updates")
async def get_action_updates(
    action_id: str,
    user_data: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200, description="Max updates to fetch"),
) -> ActionUpdatesResponse:
    """Get activity updates for an action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth
        limit: Maximum number of updates to fetch

    Returns:
        ActionUpdatesResponse with activity timeline
    """
    user_id = user_data.get("user_id")
    logger.info(f"Fetching updates for action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Get updates
    updates = action_repository.get_updates(action_id, limit=limit)

    # Format response
    def to_iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return ActionUpdatesResponse(
        action_id=action_id,
        updates=[
            ActionUpdateResponse(
                id=update["id"],
                action_id=str(update["action_id"]),
                user_id=update["user_id"],
                update_type=update["update_type"],
                content=update.get("content"),
                old_status=update.get("old_status"),
                new_status=update.get("new_status"),
                old_date=to_iso(update.get("old_date")),
                new_date=to_iso(update.get("new_date")),
                date_field=update.get("date_field"),
                progress_percent=update.get("progress_percent"),
                created_at=to_iso(update.get("created_at")) or "",
            )
            for update in updates
        ],
        total=len(updates),
    )


@router.post(
    "/{action_id}/updates",
    response_model=ActionUpdateResponse,
    summary="Add action update",
    description="Add a progress update, blocker, or note to an action.",
    responses={
        200: {"description": "Update added successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("add action update")
async def add_action_update(
    action_id: str,
    update: ActionUpdateCreate,
    user_data: dict = Depends(get_current_user),
) -> ActionUpdateResponse:
    """Add an update to an action.

    Args:
        action_id: Action UUID
        update: Update details
        user_data: Current user from auth

    Returns:
        Created ActionUpdateResponse
    """
    user_id = user_data.get("user_id")
    logger.info(f"Adding {update.update_type} update to action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Validate progress_percent for progress updates
    if update.update_type == "progress" and update.progress_percent is None:
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "progress_percent is required for progress updates", 400
        )

    # Summarize content if enabled (clean up grammar/formatting)
    from backend.services.action_update_summarizer import summarize_action_update

    content = await summarize_action_update(
        content=update.content,
        update_type=update.update_type,
        user_id=user_id,
    )

    # Add update
    created = action_repository.add_update(
        action_id=action_id,
        user_id=user_id,
        update_type=update.update_type,
        content=content,
        progress_percent=update.progress_percent,
    )

    # Format response
    def to_iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None

    return ActionUpdateResponse(
        id=created["id"],
        action_id=str(created["action_id"]),
        user_id=created["user_id"],
        update_type=created["update_type"],
        content=created.get("content"),
        old_status=created.get("old_status"),
        new_status=created.get("new_status"),
        old_date=to_iso(created.get("old_date")),
        new_date=to_iso(created.get("new_date")),
        date_field=created.get("date_field"),
        progress_percent=created.get("progress_percent"),
        created_at=to_iso(created.get("created_at")) or "",
    )


# =============================================================================
# Action Tags Endpoints
# =============================================================================


@router.get(
    "/{action_id}/tags",
    response_model=list[TagResponse],
    summary="Get action tags",
    description="Get all tags assigned to an action.",
    responses={
        200: {"description": "Tags retrieved successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("get action tags")
async def get_action_tags(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> list[TagResponse]:
    """Get all tags for an action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        List of TagResponse
    """
    user_id = user_data.get("user_id")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Get tags
    tags = tag_repository.get_action_tags(action_id)

    return [
        TagResponse(
            id=str(tag["id"]),
            user_id=tag["user_id"],
            name=tag["name"],
            color=tag["color"],
            action_count=0,  # Not needed for action tags response
            created_at=tag["created_at"].isoformat() if tag.get("created_at") else "",
            updated_at=tag["updated_at"].isoformat() if tag.get("updated_at") else "",
        )
        for tag in tags
    ]


@router.put(
    "/{action_id}/tags",
    response_model=list[TagResponse],
    summary="Set action tags",
    description="Replace all tags for an action with the specified list.",
    responses={
        200: {"description": "Tags updated successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("set action tags")
async def set_action_tags(
    action_id: str,
    tags_update: ActionTagsUpdate,
    user_data: dict = Depends(get_current_user),
) -> list[TagResponse]:
    """Set tags for an action (replaces existing).

    Args:
        action_id: Action UUID
        tags_update: List of tag IDs to assign
        user_data: Current user from auth

    Returns:
        List of TagResponse with new tags
    """
    user_id = user_data.get("user_id")
    logger.info(f"Setting tags for action {action_id}: {tags_update.tag_ids}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Set tags
    tag_repository.set_action_tags(action_id, tags_update.tag_ids)

    # Return updated tags
    tags = tag_repository.get_action_tags(action_id)

    return [
        TagResponse(
            id=str(tag["id"]),
            user_id=tag["user_id"],
            name=tag["name"],
            color=tag["color"],
            action_count=0,
            created_at=tag["created_at"].isoformat() if tag.get("created_at") else "",
            updated_at=tag["updated_at"].isoformat() if tag.get("updated_at") else "",
        )
        for tag in tags
    ]


# =============================================================================
# Progress Tracking Endpoints
# =============================================================================


@router.patch(
    "/{action_id}/progress",
    response_model=ActionDetailResponse,
    summary="Update action progress",
    description="Update action progress tracking (percentage, points, or status-only) and actual dates.",
    responses={
        200: {"description": "Progress updated successfully"},
        400: {"description": "Invalid progress value or dates"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("update action progress")
async def update_action_progress(
    action_id: str,
    progress_update: ActionProgressUpdate,
    user_data: dict = Depends(get_current_user),
) -> ActionDetailResponse:
    """Update action progress tracking.

    Accepts progress_type (percentage, points, status_only), progress_value,
    and actual start/finish dates for variance analysis.

    Args:
        action_id: Action UUID
        progress_update: Progress update request
        user_data: Current user from auth

    Returns:
        Updated ActionDetailResponse
    """
    user_id = user_data.get("user_id")
    logger.info(f"Updating progress for action {action_id}: {progress_update.progress_type}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Validate progress_value for percentage type
    if progress_update.progress_type == "percentage":
        if progress_update.progress_value is None:
            raise http_error(
                ErrorCode.VALIDATION_ERROR, "progress_value required for percentage type", 400
            )
        if progress_update.progress_value < 0 or progress_update.progress_value > 100:
            raise http_error(
                ErrorCode.VALIDATION_ERROR, "progress_value must be 0-100 for percentage type", 400
            )

    # Update progress in database
    with db_session():
        action_repository.update_progress(
            action_id,
            progress_type=progress_update.progress_type,
            progress_value=progress_update.progress_value,
            actual_start_date=progress_update.actual_start_date,
            actual_finish_date=progress_update.actual_finish_date,
            estimated_effort_points=progress_update.estimated_effort_points,
        )

    # Fetch updated action
    updated = action_repository.get(action_id)
    if not updated:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found after update", 404)

    return _action_to_detail_response(updated)


@router.get(
    "/{action_id}/variance",
    response_model=ActionVariance,
    summary="Get action schedule variance",
    description="Calculate schedule variance (early/on-time/late) and effort analysis.",
    responses={
        200: {"description": "Variance calculated successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("get action variance")
async def get_action_variance(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ActionVariance:
    """Get action schedule variance analysis.

    Calculates variance between planned and actual durations,
    returns risk_level (EARLY, ON_TIME, LATE).

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ActionVariance with schedule analysis
    """
    user_id = user_data.get("user_id")
    logger.info(f"Getting variance for action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)
    if action.get("user_id") != user_id:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    # Calculate variance
    variance = action_repository.calculate_variance(action_id)

    return variance


# =============================================================================
# Action Reminder Settings Endpoints
# =============================================================================


@router.get(
    "/{action_id}/reminder-settings",
    response_model=ReminderSettingsResponse,
    summary="Get action reminder settings",
    description="Get reminder configuration for a specific action.",
    responses={
        200: {"description": "Settings retrieved successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("get reminder settings")
async def get_action_reminder_settings(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> ReminderSettingsResponse:
    """Get reminder settings for an action.

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        ReminderSettingsResponse with current settings
    """
    from backend.api.models import ReminderSettingsResponse
    from backend.services.action_reminders import get_reminder_settings

    user_id = user_data.get("user_id")

    settings = get_reminder_settings(action_id, user_id)
    if not settings:
        raise http_error(ErrorCode.API_NOT_FOUND, "Action not found", 404)

    return ReminderSettingsResponse(
        action_id=settings.action_id,
        reminders_enabled=settings.reminders_enabled,
        reminder_frequency_days=settings.reminder_frequency_days,
        snoozed_until=settings.snoozed_until.isoformat() if settings.snoozed_until else None,
        last_reminder_sent_at=settings.last_reminder_sent_at.isoformat()
        if settings.last_reminder_sent_at
        else None,
    )


@router.patch(
    "/{action_id}/reminder-settings",
    response_model=ReminderSettingsResponse,
    summary="Update action reminder settings",
    description="Update reminder frequency or enable/disable reminders for an action.",
    responses={
        200: {"description": "Settings updated successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("update reminder settings")
async def update_action_reminder_settings(
    action_id: str,
    settings_update: ReminderSettingsUpdate,
    user_data: dict = Depends(get_current_user),
) -> ReminderSettingsResponse:
    """Update reminder settings for an action.

    Args:
        action_id: Action UUID
        settings_update: Settings to update
        user_data: Current user from auth

    Returns:
        Updated ReminderSettingsResponse
    """
    from backend.api.models import ReminderSettingsResponse
    from backend.services.action_reminders import update_reminder_settings

    user_id = user_data.get("user_id")
    logger.info(f"Updating reminder settings for action {action_id}")

    settings = update_reminder_settings(
        action_id=action_id,
        user_id=user_id,
        reminders_enabled=settings_update.reminders_enabled,
        reminder_frequency_days=settings_update.reminder_frequency_days,
    )

    if not settings:
        raise http_error(ErrorCode.API_NOT_FOUND, "Action not found", 404)

    return ReminderSettingsResponse(
        action_id=settings.action_id,
        reminders_enabled=settings.reminders_enabled,
        reminder_frequency_days=settings.reminder_frequency_days,
        snoozed_until=settings.snoozed_until.isoformat() if settings.snoozed_until else None,
        last_reminder_sent_at=settings.last_reminder_sent_at.isoformat()
        if settings.last_reminder_sent_at
        else None,
    )


@router.post(
    "/{action_id}/snooze-reminder",
    response_model=ReminderSnoozedResponse,
    summary="Snooze action reminder",
    description="Delay reminder for this action by N days.",
    responses={
        200: {"description": "Reminder snoozed successfully"},
        404: {"description": "Action not found"},
    },
)
@handle_api_errors("snooze reminder")
async def snooze_action_reminder(
    action_id: str,
    snooze_request: SnoozeReminderRequest,
    user_data: dict = Depends(get_current_user),
) -> ReminderSnoozedResponse:
    """Snooze reminders for an action.

    Args:
        action_id: Action UUID
        snooze_request: Snooze configuration
        user_data: Current user from auth

    Returns:
        ReminderSnoozedResponse with snooze details
    """
    from backend.services.action_reminders import snooze_reminder

    user_id = user_data.get("user_id")
    logger.info(f"Snoozing reminder for action {action_id} by {snooze_request.snooze_days} days")

    success = snooze_reminder(
        action_id=action_id,
        user_id=user_id,
        snooze_days=snooze_request.snooze_days,
    )

    if not success:
        raise http_error(ErrorCode.NOT_FOUND, "Action not found", 404)

    return ReminderSnoozedResponse(
        message="Reminder snoozed successfully",
        action_id=action_id,
        snooze_days=snooze_request.snooze_days,
    )


def _action_to_detail_response(action: dict[str, Any]) -> ActionDetailResponse:
    """Convert action dict to ActionDetailResponse.

    Helper to convert database action to response model.
    """
    return ActionDetailResponse(
        id=str(action.get("id", "")),
        title=action.get("title", ""),
        description=action.get("description", ""),
        what_and_how=action.get("what_and_how", []),
        success_criteria=action.get("success_criteria", []),
        kill_criteria=action.get("kill_criteria", []),
        dependencies=action.get("dependencies", []),
        timeline=action.get("timeline"),
        priority=action.get("priority", "medium"),
        category=action.get("category", "implementation"),
        source_section=action.get("source_section"),
        confidence=float(action.get("confidence", 0.0)),
        sub_problem_index=action.get("sub_problem_index"),
        status=action.get("status", "todo"),
        session_id=action.get("source_session_id", ""),
        problem_statement=action.get("problem_statement", ""),
        estimated_duration_days=action.get("estimated_duration_days"),
        target_start_date=action.get("target_start_date").isoformat()
        if action.get("target_start_date")
        else None,
        target_end_date=action.get("target_end_date").isoformat()
        if action.get("target_end_date")
        else None,
        estimated_start_date=action.get("estimated_start_date").isoformat()
        if action.get("estimated_start_date")
        else None,
        estimated_end_date=action.get("estimated_end_date").isoformat()
        if action.get("estimated_end_date")
        else None,
        actual_start_date=action.get("actual_start_date").isoformat()
        if action.get("actual_start_date")
        else None,
        actual_end_date=action.get("actual_end_date").isoformat()
        if action.get("actual_end_date")
        else None,
        blocking_reason=action.get("blocking_reason"),
        blocked_at=action.get("blocked_at").isoformat() if action.get("blocked_at") else None,
        auto_unblock=action.get("auto_unblock", False),
        replan_session_id=action.get("replan_session_id"),
        replan_requested_at=action.get("replan_requested_at").isoformat()
        if action.get("replan_requested_at")
        else None,
        replanning_reason=action.get("replanning_reason"),
        can_replan=action.get("status") == "blocked",
        cancellation_reason=action.get("cancellation_reason"),
        cancelled_at=action.get("cancelled_at").isoformat() if action.get("cancelled_at") else None,
        project_id=action.get("project_id"),
        progress_type=action.get("progress_type", "status_only"),
        progress_value=action.get("progress_value"),
        estimated_effort_points=action.get("estimated_effort_points"),
        scheduled_start_date=action.get("scheduled_start_date").isoformat()
        if action.get("scheduled_start_date")
        else None,
    )
