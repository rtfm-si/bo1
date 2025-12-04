"""Actions API endpoints for global action management.

Provides:
- GET /api/v1/actions - Get all user actions across sessions
- GET /api/v1/actions/{action_id} - Get single action details
- POST /api/v1/actions/{action_id}/start - Start an action
- POST /api/v1/actions/{action_id}/complete - Complete an action
- PATCH /api/v1/actions/{action_id}/status - Update action status
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    ActionDatesResponse,
    ActionDatesUpdate,
    ActionDetailResponse,
    ActionStatusUpdate,
    ActionTagsUpdate,
    ActionUpdateCreate,
    ActionUpdateResponse,
    ActionUpdatesResponse,
    AllActionsResponse,
    BlockActionRequest,
    DependencyCreate,
    DependencyListResponse,
    DependencyResponse,
    GanttActionData,
    GanttDependency,
    GlobalGanttResponse,
    ReplanRequest,
    ReplanResponse,
    TagResponse,
    UnblockActionRequest,
)
from bo1.services.replanning_service import replanning_service
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
    },
)
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
    logger.info(f"Fetching all actions for user {user_id}")

    # Parse tag_ids from comma-separated string
    tag_id_list: list[str] | None = None
    if tag_ids:
        tag_id_list = [t.strip() for t in tag_ids.split(",") if t.strip()]

    # Get all actions from actions table
    actions = action_repository.get_by_user(
        user_id=user_id,
        status_filter=status_filter,
        project_id=project_id,
        session_id=session_id,
        tag_ids=tag_id_list,
        limit=limit,
        offset=offset,
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
            "problem_statement": sessions_map.get(session_id, {}).get("problem_statement", ""),
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
    logger.info(f"Fetching global Gantt data for user {user_id}")

    # Parse tag_ids
    tag_id_list: list[str] | None = None
    if tag_ids:
        tag_id_list = [t.strip() for t in tag_ids.split(",") if t.strip()]

    # Get all actions
    actions = action_repository.get_by_user(
        user_id=user_id,
        status_filter=status_filter,
        project_id=project_id,
        session_id=session_id,
        tag_ids=tag_id_list,
        limit=500,
        offset=0,
    )

    # Format for Gantt chart
    gantt_actions: list[GanttActionData] = []
    all_dependencies: list[GanttDependency] = []
    today = date.today()

    for action in actions:
        action_id = str(action.get("id", ""))

        # Calculate dates
        start_date = action.get("target_start_date") or action.get("estimated_start_date")
        end_date = action.get("target_end_date") or action.get("estimated_end_date")
        duration_days = action.get("estimated_duration_days") or 7

        # Default to today if no dates
        if not start_date:
            start_date = today
        if not end_date:
            end_date = start_date + timedelta(days=duration_days)

        # Map status to progress
        status = action.get("status", "todo")
        progress_map = {
            "todo": 0,
            "in_progress": 50,
            "blocked": 25,
            "in_review": 75,
            "done": 100,
            "cancelled": 100,
        }
        progress = progress_map.get(status, 0)

        gantt_actions.append(
            GanttActionData(
                id=action_id,
                name=action.get("title", "Untitled"),
                start=start_date.isoformat()
                if hasattr(start_date, "isoformat")
                else str(start_date),
                end=end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
                progress=progress,
                dependencies="",  # Will be populated from dependencies table
                status=status,
                priority=action.get("priority", "medium"),
                session_id=action.get("source_session_id", ""),
            )
        )

        # Get dependencies for this action
        deps = action_repository.get_dependencies(action_id)
        for dep in deps:
            all_dependencies.append(
                GanttDependency(
                    action_id=action_id,
                    depends_on_id=str(dep.get("depends_on_action_id", "")),
                    dependency_type=dep.get("dependency_type", "finish_to_start"),
                    lag_days=dep.get("lag_days", 0),
                )
            )

    # Update dependencies string in gantt_actions
    deps_map: dict[str, list[str]] = {}
    for dep in all_dependencies:
        if dep.action_id not in deps_map:
            deps_map[dep.action_id] = []
        deps_map[dep.action_id].append(dep.depends_on_id)

    for action in gantt_actions:
        if action.id in deps_map:
            action.dependencies = ",".join(deps_map[action.id])

    return GlobalGanttResponse(
        actions=gantt_actions,
        dependencies=all_dependencies,
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
        404: {"description": "Action not found"},
    },
)
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
    logger.info(f"Fetching action {action_id} for user {user_id}")

    # Get action from actions table
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Verify user ownership
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Get session for problem_statement
    session_id = action.get("source_session_id", "")
    session = session_repository.get(session_id)
    problem_statement = session.get("problem_statement", "") if session else ""

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
    )


@router.post(
    "/{action_id}/start",
    summary="Start an action",
    description="Mark action as in_progress and set actual_start_date.",
    responses={
        200: {"description": "Action started successfully"},
        404: {"description": "Action not found"},
    },
)
async def start_action(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Start an action (mark as in_progress).

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        Success message
    """
    user_id = user_data.get("user_id")
    logger.info(f"Starting action {action_id} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Start action
    success = action_repository.start_action(action_id, user_id)
    if not success:
        raise HTTPException(
            status_code=400, detail="Action cannot be started (already in progress or done)"
        )

    return {"message": "Action started successfully", "action_id": action_id}


@router.post(
    "/{action_id}/complete",
    summary="Complete an action",
    description="Mark action as done and set actual_end_date. Auto-unblocks dependent actions.",
    responses={
        200: {"description": "Action completed successfully"},
        404: {"description": "Action not found"},
    },
)
async def complete_action(
    action_id: str,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Complete an action (mark as done).

    Args:
        action_id: Action UUID
        user_data: Current user from auth

    Returns:
        Success message with list of auto-unblocked actions
    """
    user_id = user_data.get("user_id")
    logger.info(f"Completing action {action_id} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Complete action
    success = action_repository.complete_action(action_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Action cannot be completed (already done)")

    # Auto-unblock dependent actions
    unblocked_ids = action_repository.auto_unblock_dependents(action_id, user_id)
    if unblocked_ids:
        logger.info(f"Auto-unblocked {len(unblocked_ids)} actions after completing {action_id}")

    return {
        "message": "Action completed successfully",
        "action_id": action_id,
        "unblocked_actions": unblocked_ids,
    }


@router.patch(
    "/{action_id}/status",
    summary="Update action status",
    description="Update action status with optional blocking reason. Validates status transitions.",
    responses={
        200: {"description": "Action status updated successfully"},
        400: {"description": "Invalid status transition"},
        404: {"description": "Action not found"},
    },
)
async def update_action_status(
    action_id: str,
    status_update: ActionStatusUpdate,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Update action status.

    Args:
        action_id: Action UUID
        status_update: Status update request
        user_data: Current user from auth

    Returns:
        Success message with list of auto-unblocked actions (if completing)
    """
    user_id = user_data.get("user_id")
    logger.info(f"Updating action {action_id} status to {status_update.status} for user {user_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Validate status transition
    current_status = action.get("status", "todo")
    is_valid, error = action_repository.validate_status_transition(
        current_status, status_update.status
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Validate blocking_reason required for blocked status
    if status_update.status == "blocked" and not status_update.blocking_reason:
        raise HTTPException(
            status_code=400, detail="blocking_reason required when status is 'blocked'"
        )

    # Update status
    success = action_repository.update_status(
        action_id=action_id,
        status=status_update.status,
        user_id=user_id,
        blocking_reason=status_update.blocking_reason,
        auto_unblock=status_update.auto_unblock,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update action status")

    # Auto-unblock dependent actions if completing
    unblocked_ids: list[str] = []
    if status_update.status in ("done", "cancelled"):
        unblocked_ids = action_repository.auto_unblock_dependents(action_id, user_id)
        if unblocked_ids:
            logger.info(
                f"Auto-unblocked {len(unblocked_ids)} actions after {status_update.status} on {action_id}"
            )

    return {
        "message": "Action status updated successfully",
        "action_id": action_id,
        "status": status_update.status,
        "unblocked_actions": unblocked_ids,
    }


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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

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
    summary="Add action dependency",
    description="Add a dependency to an action. Auto-blocks if dependency is incomplete.",
    responses={
        200: {"description": "Dependency added successfully"},
        400: {"description": "Circular dependency or invalid action"},
        404: {"description": "Action not found"},
    },
)
async def add_action_dependency(
    action_id: str,
    dependency: DependencyCreate,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a dependency to an action.

    Args:
        action_id: Action UUID
        dependency: Dependency details
        user_data: Current user from auth

    Returns:
        Success message with auto-block info
    """
    user_id = user_data.get("user_id")
    logger.info(f"Adding dependency on {dependency.depends_on_action_id} to action {action_id}")

    # Verify ownership of source action
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Verify target action exists and belongs to user
    target_action = action_repository.get(dependency.depends_on_action_id)
    if not target_action:
        raise HTTPException(status_code=400, detail="Target action not found")
    if target_action.get("user_id") != user_id:
        raise HTTPException(status_code=400, detail="Target action not found")

    # Prevent self-dependency
    if action_id == dependency.depends_on_action_id:
        raise HTTPException(status_code=400, detail="Action cannot depend on itself")

    # Add dependency
    result = action_repository.add_dependency(
        action_id=action_id,
        depends_on_action_id=dependency.depends_on_action_id,
        user_id=user_id,
        dependency_type=dependency.dependency_type,
        lag_days=dependency.lag_days,
    )

    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Circular dependency detected. Adding this dependency would create a cycle.",
        )

    # Check if action was auto-blocked
    updated_action = action_repository.get(action_id)
    was_blocked = updated_action and updated_action.get("status") == "blocked"

    return {
        "message": "Dependency added successfully",
        "action_id": action_id,
        "depends_on_action_id": dependency.depends_on_action_id,
        "auto_blocked": was_blocked,
        "blocking_reason": updated_action.get("blocking_reason") if was_blocked else None,
    }


@router.delete(
    "/{action_id}/dependencies/{depends_on_id}",
    summary="Remove action dependency",
    description="Remove a dependency from an action. May auto-unblock if no more incomplete dependencies.",
    responses={
        200: {"description": "Dependency removed successfully"},
        404: {"description": "Action or dependency not found"},
    },
)
async def remove_action_dependency(
    action_id: str,
    depends_on_id: str,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Remove a dependency from an action.

    Args:
        action_id: Action UUID
        depends_on_id: UUID of the action being depended on
        user_data: Current user from auth

    Returns:
        Success message with auto-unblock info
    """
    user_id = user_data.get("user_id")
    logger.info(f"Removing dependency on {depends_on_id} from action {action_id}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Get current status before removal
    was_blocked = action.get("status") == "blocked"

    # Remove dependency
    success = action_repository.remove_dependency(
        action_id=action_id,
        depends_on_action_id=depends_on_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Dependency not found")

    # Check if action was auto-unblocked
    updated_action = action_repository.get(action_id)
    was_unblocked = was_blocked and updated_action and updated_action.get("status") != "blocked"

    return {
        "message": "Dependency removed successfully",
        "action_id": action_id,
        "depends_on_id": depends_on_id,
        "auto_unblocked": was_unblocked,
        "new_status": updated_action.get("status") if updated_action else None,
    }


# =============================================================================
# Block/Unblock Convenience Endpoints
# =============================================================================


@router.post(
    "/{action_id}/block",
    summary="Block an action",
    description="Block an action with a reason. Validates status transition.",
    responses={
        200: {"description": "Action blocked successfully"},
        400: {"description": "Invalid status transition"},
        404: {"description": "Action not found"},
    },
)
async def block_action(
    action_id: str,
    block_request: BlockActionRequest,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Block an action with a reason.

    Args:
        action_id: Action UUID
        block_request: Block request with reason
        user_data: Current user from auth

    Returns:
        Success message
    """
    user_id = user_data.get("user_id")
    logger.info(f"Blocking action {action_id}: {block_request.blocking_reason}")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Block action
    success = action_repository.block_action(
        action_id=action_id,
        user_id=user_id,
        blocking_reason=block_request.blocking_reason,
        auto_unblock=block_request.auto_unblock,
    )

    if not success:
        current_status = action.get("status", "unknown")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot block action with status '{current_status}'",
        )

    return {
        "message": "Action blocked successfully",
        "action_id": action_id,
        "blocking_reason": block_request.blocking_reason,
        "auto_unblock": block_request.auto_unblock,
    }


@router.post(
    "/{action_id}/unblock",
    summary="Unblock an action",
    description="Unblock a blocked action. Validates status transition.",
    responses={
        200: {"description": "Action unblocked successfully"},
        400: {"description": "Action not blocked or has incomplete dependencies"},
        404: {"description": "Action not found"},
    },
)
async def unblock_action(
    action_id: str,
    unblock_request: UnblockActionRequest | None = None,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Unblock a blocked action.

    Args:
        action_id: Action UUID
        unblock_request: Optional unblock request with target status
        user_data: Current user from auth

    Returns:
        Success message
    """
    user_id = user_data.get("user_id")
    target_status = unblock_request.target_status if unblock_request else "todo"
    logger.info(f"Unblocking action {action_id} to status '{target_status}'")

    # Verify ownership
    action = action_repository.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Check if action is blocked
    if action.get("status") != "blocked":
        raise HTTPException(status_code=400, detail="Action is not blocked")

    # Warn about incomplete dependencies (but allow unblock)
    has_incomplete, incomplete_deps = action_repository.has_incomplete_dependencies(action_id)

    # Unblock action
    success = action_repository.unblock_action(
        action_id=action_id,
        user_id=user_id,
        target_status=target_status,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to unblock action")

    response: dict[str, Any] = {
        "message": "Action unblocked successfully",
        "action_id": action_id,
        "new_status": target_status,
    }

    if has_incomplete:
        response["warning"] = "Action has incomplete dependencies"
        response["incomplete_dependencies"] = [
            {"id": str(dep["depends_on_action_id"]), "title": dep["title"]}
            for dep in incomplete_deps
        ]

    return response


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
            raise HTTPException(status_code=404, detail=error_msg) from None
        elif "not blocked" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg) from None
        else:
            raise HTTPException(status_code=400, detail=error_msg) from None
    except Exception as e:
        logger.error(f"Failed to create replan session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create replanning session. Please try again.",
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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Parse dates
    target_start = None
    target_end = None

    if dates_update.target_start_date:
        try:
            target_start = datetime.strptime(dates_update.target_start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid target_start_date format"
            ) from None

    if dates_update.target_end_date:
        try:
            target_end = datetime.strptime(dates_update.target_end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target_end_date format") from None

    # Validate target_end >= target_start
    if target_start and target_end and target_end < target_start:
        raise HTTPException(status_code=400, detail="target_end_date must be >= target_start_date")

    # Update timeline and estimated_duration_days if provided
    if dates_update.timeline:
        estimated_duration = parse_timeline(dates_update.timeline)

        # Direct SQL update for timeline (since update_dates doesn't handle timeline)
        from bo1.state.database import db_session

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET timeline = %s,
                        estimated_duration_days = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (dates_update.timeline, estimated_duration, action_id),
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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

    # Validate progress_percent for progress updates
    if update.update_type == "progress" and update.progress_percent is None:
        raise HTTPException(
            status_code=400,
            detail="progress_percent is required for progress updates",
        )

    # Add update
    created = action_repository.add_update(
        action_id=action_id,
        user_id=user_id,
        update_type=update.update_type,
        content=update.content,
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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

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
        raise HTTPException(status_code=404, detail="Action not found")
    if action.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Action not found")

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
