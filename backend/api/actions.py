"""Actions API endpoints for global task management.

Provides:
- GET /api/v1/actions - Get all user actions across sessions
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.api.middleware.auth import get_current_user
from backend.api.models import AllActionsResponse
from bo1.state.repositories.session_repository import session_repository

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
    description="Get all actions/tasks across all completed sessions for the current user.",
    responses={
        200: {"description": "Actions retrieved successfully"},
    },
)
async def get_all_actions(
    user_data: dict = Depends(get_current_user),
    status_filter: str | None = Query(
        None,
        description="Filter by status (todo, doing, done)",
        pattern="^(todo|doing|done)$",
    ),
    limit: int = Query(100, ge=1, le=500, description="Max sessions to fetch"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> AllActionsResponse:
    """Get all actions/tasks for the current user across all sessions.

    Args:
        user_data: Current user from auth
        status_filter: Optional filter by task status
        limit: Maximum number of sessions to fetch
        offset: Pagination offset

    Returns:
        AllActionsResponse with all tasks grouped by session
    """
    user_id = user_data.get("user_id")
    logger.info(f"Fetching all actions for user {user_id}")

    # Get all tasks across sessions
    session_records = session_repository.get_user_tasks(
        user_id=user_id, status_filter=status_filter, limit=limit, offset=offset
    )

    # Process each session's tasks
    all_tasks: list[dict[str, Any]] = []
    sessions_data: list[dict[str, Any]] = []

    for record in session_records:
        session_id = record.get("session_id", "")
        tasks = record.get("tasks", [])
        task_statuses = record.get("task_statuses", {}) or {}
        problem_statement = record.get("problem_statement", "")
        session_status = record.get("session_status", "")
        created_at = record.get("created_at")
        extracted_at = record.get("extracted_at")

        # Skip sessions without tasks
        if not tasks:
            continue

        # Add session context to tasks
        tasks_with_context = _tasks_with_statuses_and_session(
            tasks, task_statuses, session_id, problem_statement
        )

        # Apply status filter if provided
        if status_filter:
            tasks_with_context = [t for t in tasks_with_context if t.get("status") == status_filter]

        if not tasks_with_context:
            continue

        all_tasks.extend(tasks_with_context)

        # Session summary
        by_status = _count_by_status(tasks_with_context)
        sessions_data.append(
            {
                "session_id": session_id,
                "problem_statement": problem_statement,
                "session_status": session_status,
                "created_at": created_at.isoformat() if created_at else None,
                "extracted_at": extracted_at.isoformat() if extracted_at else None,
                "tasks": tasks_with_context,
                "task_count": len(tasks_with_context),
                "by_status": by_status,
            }
        )

    # Calculate global status counts
    global_by_status = _count_by_status(all_tasks)

    logger.info(
        f"Found {len(all_tasks)} actions across {len(sessions_data)} sessions for user {user_id}"
    )

    return AllActionsResponse(
        sessions=sessions_data,
        total_tasks=len(all_tasks),
        by_status=global_by_status,
    )
