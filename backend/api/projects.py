"""Projects API endpoints for project management.

Provides:
- GET /api/v1/projects - Get all user projects
- POST /api/v1/projects - Create a new project
- GET /api/v1/projects/{id} - Get project details
- PATCH /api/v1/projects/{id} - Update a project
- DELETE /api/v1/projects/{id} - Archive a project
- PATCH /api/v1/projects/{id}/status - Update project status
- GET /api/v1/projects/{id}/actions - Get project's actions
- POST /api/v1/projects/{id}/actions/{action_id} - Assign action to project
- DELETE /api/v1/projects/{id}/actions/{action_id} - Remove action from project
- GET /api/v1/projects/{id}/gantt - Get Gantt chart data
- POST /api/v1/projects/{id}/sessions - Link session to project
- DELETE /api/v1/projects/{id}/sessions/{session_id} - Unlink session
"""

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    GanttResponse,
    ProjectActionsResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectSessionLink,
    ProjectStatusUpdate,
    ProjectUpdate,
)
from bo1.state.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/projects", tags=["projects"])

# Singleton repository instance
project_repository = ProjectRepository()


def _format_project_response(project: dict) -> dict:
    """Format project dict for API response.

    Converts date objects to ISO strings and ensures consistent format.
    """
    return {
        "id": str(project["id"]),
        "user_id": project["user_id"],
        "name": project["name"],
        "description": project.get("description"),
        "status": project["status"],
        "target_start_date": (
            project["target_start_date"].isoformat() if project.get("target_start_date") else None
        ),
        "target_end_date": (
            project["target_end_date"].isoformat() if project.get("target_end_date") else None
        ),
        "estimated_start_date": (
            project["estimated_start_date"].isoformat()
            if project.get("estimated_start_date")
            else None
        ),
        "estimated_end_date": (
            project["estimated_end_date"].isoformat() if project.get("estimated_end_date") else None
        ),
        "actual_start_date": (
            project["actual_start_date"].isoformat() if project.get("actual_start_date") else None
        ),
        "actual_end_date": (
            project["actual_end_date"].isoformat() if project.get("actual_end_date") else None
        ),
        "progress_percent": project.get("progress_percent", 0),
        "total_actions": project.get("total_actions", 0),
        "completed_actions": project.get("completed_actions", 0),
        "color": project.get("color"),
        "icon": project.get("icon"),
        "created_at": (project["created_at"].isoformat() if project.get("created_at") else None),
        "updated_at": (project["updated_at"].isoformat() if project.get("updated_at") else None),
    }


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="Get all projects",
    description="Get all projects for the current user with optional filtering",
)
async def get_projects(
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    user: dict = Depends(get_current_user),
) -> ProjectListResponse:
    """Get all projects for the current user."""
    user_id = user["user_id"]

    total, projects = project_repository.get_by_user(
        user_id=user_id,
        status=status,
        page=page,
        per_page=per_page,
    )

    return {
        "projects": [_format_project_response(p) for p in projects],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post(
    "",
    response_model=ProjectDetailResponse,
    status_code=201,
    summary="Create a project",
    description="Create a new project",
)
async def create_project(
    request: ProjectCreate,
    user: dict = Depends(get_current_user),
) -> ProjectDetailResponse:
    """Create a new project."""
    user_id = user["user_id"]

    # Parse dates if provided
    target_start = None
    target_end = None
    if request.target_start_date:
        target_start = date.fromisoformat(request.target_start_date)
    if request.target_end_date:
        target_end = date.fromisoformat(request.target_end_date)

    project = project_repository.create(
        user_id=user_id,
        name=request.name,
        description=request.description,
        target_start_date=target_start,
        target_end_date=target_end,
        color=request.color,
        icon=request.icon,
    )

    return _format_project_response(project)


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get project details",
    description="Get detailed information about a specific project",
)
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> ProjectDetailResponse:
    """Get a single project by ID."""
    user_id = user["user_id"]

    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _format_project_response(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Update a project",
    description="Update project fields",
)
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    user: dict = Depends(get_current_user),
) -> ProjectDetailResponse:
    """Update a project's basic fields."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Parse dates if provided
    target_start = None
    target_end = None
    if request.target_start_date:
        target_start = date.fromisoformat(request.target_start_date)
    if request.target_end_date:
        target_end = date.fromisoformat(request.target_end_date)

    updated = project_repository.update(
        project_id=project_id,
        name=request.name,
        description=request.description,
        target_start_date=target_start,
        target_end_date=target_end,
        color=request.color,
        icon=request.icon,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")

    return _format_project_response(updated)


@router.delete(
    "/{project_id}",
    status_code=204,
    summary="Archive a project",
    description="Archive a project (soft delete)",
)
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Archive a project (soft delete)."""
    user_id = user["user_id"]

    success = project_repository.delete(project_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return None


@router.patch(
    "/{project_id}/status",
    response_model=ProjectDetailResponse,
    summary="Update project status",
    description="Update project status with validation",
)
async def update_project_status(
    project_id: str,
    request: ProjectStatusUpdate,
    user: dict = Depends(get_current_user),
) -> ProjectDetailResponse:
    """Update a project's status."""
    user_id = user["user_id"]

    try:
        updated = project_repository.update_status(
            project_id=project_id,
            new_status=request.status,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")

    return _format_project_response(updated)


# =========================================================================
# Project Actions
# =========================================================================


@router.get(
    "/{project_id}/actions",
    response_model=ProjectActionsResponse,
    summary="Get project actions",
    description="Get all actions for a project",
)
async def get_project_actions(
    project_id: str,
    status: str | None = Query(None, description="Filter by action status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    user: dict = Depends(get_current_user),
) -> ProjectActionsResponse:
    """Get all actions for a project."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    total, actions = project_repository.get_actions(
        project_id=project_id,
        status=status,
        page=page,
        per_page=per_page,
    )

    # Format action responses
    formatted_actions = []
    for action in actions:
        formatted_actions.append(
            {
                "id": str(action["id"]),
                "session_id": action.get("session_id", ""),
                "title": action["title"],
                "description": action.get("description", ""),
                "status": action["status"],
                "priority": action.get("priority", "medium"),
                "category": action.get("category", "implementation"),
                "timeline": action.get("timeline"),
                "estimated_duration_days": action.get("estimated_duration_days"),
                "estimated_start_date": (
                    action["estimated_start_date"].isoformat()
                    if action.get("estimated_start_date")
                    else None
                ),
                "estimated_end_date": (
                    action["estimated_end_date"].isoformat()
                    if action.get("estimated_end_date")
                    else None
                ),
                "blocking_reason": action.get("blocking_reason"),
            }
        )

    return {
        "actions": formatted_actions,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post(
    "/{project_id}/actions/{action_id}",
    status_code=204,
    summary="Assign action to project",
    description="Assign an action to this project",
)
async def assign_action_to_project(
    project_id: str,
    action_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Assign an action to a project."""
    user_id = user["user_id"]

    success = project_repository.assign_action(
        action_id=action_id,
        project_id=project_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Action or project not found, or access denied")

    return None


@router.delete(
    "/{project_id}/actions/{action_id}",
    status_code=204,
    summary="Remove action from project",
    description="Remove an action from this project",
)
async def remove_action_from_project(
    project_id: str,
    action_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Remove an action from a project."""
    user_id = user["user_id"]

    success = project_repository.unassign_action(
        action_id=action_id,
        user_id=user_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Action not found or access denied")

    return None


# =========================================================================
# Gantt Chart
# =========================================================================


@router.get(
    "/{project_id}/gantt",
    response_model=GanttResponse,
    summary="Get Gantt chart data",
    description="Get timeline data for Gantt chart visualization",
)
async def get_gantt_data(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> GanttResponse:
    """Get Gantt chart data for a project."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    gantt_data = project_repository.get_gantt_data(project_id)

    return gantt_data


# =========================================================================
# Session Linking
# =========================================================================


@router.post(
    "/{project_id}/sessions",
    status_code=201,
    summary="Link session to project",
    description="Link a deliberation session to this project",
)
async def link_session_to_project(
    project_id: str,
    request: ProjectSessionLink,
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Link a session to a project."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    link = project_repository.link_session(
        project_id=project_id,
        session_id=request.session_id,
        relationship=request.relationship,
    )

    return {
        "project_id": str(project_id),
        "session_id": request.session_id,
        "relationship": link["relationship"] if link else request.relationship,
    }


@router.delete(
    "/{project_id}/sessions/{session_id}",
    status_code=204,
    summary="Unlink session from project",
    description="Remove a session link from this project",
)
async def unlink_session_from_project(
    project_id: str,
    session_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Unlink a session from a project."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    success = project_repository.unlink_session(project_id, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session link not found")

    return None


@router.get(
    "/{project_id}/sessions",
    summary="Get project sessions",
    description="Get all sessions linked to this project",
)
async def get_project_sessions(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, list[dict[str, Any]]]:
    """Get all sessions linked to a project."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    sessions = project_repository.get_sessions(project_id)

    return {
        "sessions": [
            {
                "session_id": s["session_id"],
                "relationship": s["relationship"],
                "problem_statement": s.get("problem_statement", ""),
                "session_status": s.get("session_status", ""),
                "created_at": (s["created_at"].isoformat() if s.get("created_at") else None),
            }
            for s in sessions
        ]
    }
