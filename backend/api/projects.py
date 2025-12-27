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

from fastapi import APIRouter, Depends, Query

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    AutogenCreateRequest,
    AutogenCreateResponse,
    AutogenSuggestion,
    AutogenSuggestionsResponse,
    ContextCreateRequest,
    ContextProjectSuggestion,
    ContextSuggestionsResponse,
    CreateProjectMeetingRequest,
    GanttResponse,
    ProjectActionsResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectSessionLink,
    ProjectStatusUpdate,
    ProjectUpdate,
    SessionResponse,
    UnassignedCountResponse,
)
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.pagination import make_page_pagination_fields
from bo1.logging.errors import ErrorCode, log_error
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
        "version": project.get("version", 1),
        "source_project_id": (
            str(project["source_project_id"]) if project.get("source_project_id") else None
        ),
        "created_at": (project["created_at"].isoformat() if project.get("created_at") else None),
        "updated_at": (project["updated_at"].isoformat() if project.get("updated_at") else None),
    }


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="Get all projects",
    description="Get all projects for the current user with optional filtering",
)
@handle_api_errors("get projects")
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

    pagination = make_page_pagination_fields(total, page, per_page)
    return {
        "projects": [_format_project_response(p) for p in projects],
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": pagination["has_more"],
        "next_offset": pagination["next_offset"],
    }


@router.post(
    "",
    response_model=ProjectDetailResponse,
    status_code=201,
    summary="Create a project",
    description="Create a new project",
)
@handle_api_errors("create project")
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
@handle_api_errors("get project")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> ProjectDetailResponse:
    """Get a single project by ID."""
    user_id = user["user_id"]

    project = project_repository.get(project_id)
    if not project:
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)

    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

    return _format_project_response(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Update a project",
    description="Update project fields",
)
@handle_api_errors("update project")
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
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

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
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)

    return _format_project_response(updated)


@router.delete(
    "/{project_id}",
    status_code=204,
    summary="Archive a project",
    description="Archive a project (soft delete)",
)
@handle_api_errors("delete project")
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Archive a project (soft delete)."""
    user_id = user["user_id"]

    success = project_repository.delete(project_id, user_id)
    if not success:
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)

    return None


@router.patch(
    "/{project_id}/status",
    response_model=ProjectDetailResponse,
    summary="Update project status",
    description="Update project status with validation",
)
@handle_api_errors("update project status")
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
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), 400) from None

    if not updated:
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)

    return _format_project_response(updated)


@router.post(
    "/{project_id}/versions",
    response_model=ProjectDetailResponse,
    status_code=201,
    summary="Create new project version",
    description="Create a new version of a completed project",
)
@handle_api_errors("create project version")
async def create_project_version(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> ProjectDetailResponse:
    """Create a new version of a completed project.

    Completed projects cannot be reopened. Instead, create a new version
    which starts fresh as an active project (v2, v3, etc).
    """
    user_id = user["user_id"]

    try:
        new_project = project_repository.create_new_version(
            project_id=project_id,
            user_id=user_id,
        )
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), 400) from None

    if not new_project:
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)

    return _format_project_response(new_project)


# =========================================================================
# Project Actions
# =========================================================================


@router.get(
    "/{project_id}/actions",
    response_model=ProjectActionsResponse,
    summary="Get project actions",
    description="Get all actions for a project",
)
@handle_api_errors("get project actions")
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
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

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
        raise http_error(ErrorCode.NOT_FOUND, "Action or project not found, or access denied", 404)

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
        raise http_error(ErrorCode.NOT_FOUND, "Action not found or access denied", 404)

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
@handle_api_errors("get gantt data")
async def get_gantt_data(
    project_id: str,
    user: dict = Depends(get_current_user),
) -> GanttResponse:
    """Get Gantt chart data for a project."""
    user_id = user["user_id"]

    # Verify ownership
    project = project_repository.get(project_id)
    if not project:
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

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
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

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
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

    success = project_repository.unlink_session(project_id, session_id)
    if not success:
        raise http_error(ErrorCode.NOT_FOUND, "Session link not found", 404)

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
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

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


@router.post(
    "/{project_id}/meetings",
    response_model=SessionResponse,
    status_code=201,
    summary="Create meeting for project",
    description="Create a new deliberation meeting focused on project delivery",
)
@handle_api_errors("create project meeting")
async def create_project_meeting(
    project_id: str,
    request: CreateProjectMeetingRequest,
    user: dict = Depends(get_current_user),
) -> SessionResponse:
    """Create a meeting linked to a project.

    Creates a new deliberation session pre-linked to the project.
    Optionally includes project context (description, pending actions).
    """
    from backend.api.dependencies import get_redis_manager
    from bo1.state.repositories.session_repository import SessionRepository

    user_id = user["user_id"]

    # Verify project ownership
    project = project_repository.get(project_id)
    if not project:
        raise http_error(ErrorCode.NOT_FOUND, "Project not found", 404)
    if project["user_id"] != user_id:
        raise http_error(ErrorCode.AUTH_ERROR, "Access denied", 403)

    # Build problem statement if not provided
    problem_statement = request.problem_statement
    if not problem_statement:
        problem_statement = (
            f"How should we approach delivery and next steps for the {project['name']} project?"
        )

    # Build context if requested
    problem_context: dict[str, Any] = {}
    if request.include_project_context:
        problem_context["project_name"] = project["name"]
        if project.get("description"):
            problem_context["project_description"] = project["description"]

        # Get pending actions for context
        _, actions = project_repository.get_actions(
            project_id=project_id,
            status="todo",
            page=1,
            per_page=10,
        )
        if actions:
            problem_context["pending_actions"] = [
                {
                    "title": a["title"],
                    "priority": a.get("priority", "medium"),
                    "timeline": a.get("timeline"),
                }
                for a in actions
            ]

    # Create session
    redis_manager = get_redis_manager()
    if not redis_manager.is_available:
        raise http_error(ErrorCode.SERVICE_UNAVAILABLE, "Service temporarily unavailable", 503)

    # Generate session ID via Redis manager
    session_id = redis_manager.create_session()
    session_repository = SessionRepository()

    session = session_repository.create(
        session_id=session_id,
        user_id=user_id,
        problem_statement=problem_statement,
        problem_context=problem_context if problem_context else None,
    )

    if not session:
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to create session", 500)

    # Link session to project
    project_repository.link_session(
        project_id=project_id,
        session_id=session_id,
        relationship="discusses",
    )

    # Format response
    return {
        "id": session_id,
        "status": session.get("status", "created"),
        "problem_statement": problem_statement,
        "phase": session.get("phase", "created"),
        "created_at": session["created_at"].isoformat() if session.get("created_at") else None,
        "updated_at": session["updated_at"].isoformat() if session.get("updated_at") else None,
        "last_activity_at": None,
    }


# =========================================================================
# Project Autogeneration
# =========================================================================


@router.get(
    "/autogenerate-suggestions",
    response_model=AutogenSuggestionsResponse,
    summary="Get autogenerate suggestions",
    description="Analyze unassigned actions and suggest project groupings",
)
@handle_api_errors("get autogen suggestions")
async def get_autogen_suggestions(
    user: dict = Depends(get_current_user),
) -> AutogenSuggestionsResponse:
    """Get project suggestions from unassigned actions.

    Analyzes unassigned actions using LLM to identify coherent groupings
    and returns suggestions for user review.
    """
    from backend.services.project_autogen import (
        MIN_ACTIONS_FOR_AUTOGEN,
        get_unassigned_action_count,
    )
    from backend.services.project_autogen import (
        get_autogen_suggestions as get_suggestions,
    )

    user_id = user["user_id"]

    # Get unassigned count first
    unassigned_count = get_unassigned_action_count(user_id)

    # If not enough actions, return early
    if unassigned_count < MIN_ACTIONS_FOR_AUTOGEN:
        return {
            "suggestions": [],
            "unassigned_count": unassigned_count,
            "min_required": MIN_ACTIONS_FOR_AUTOGEN,
        }

    # Get suggestions from LLM
    suggestions = await get_suggestions(user_id)

    # Convert to response model format
    response_suggestions = [
        AutogenSuggestion(
            id=s.id,
            name=s.name,
            description=s.description,
            action_ids=s.action_ids,
            confidence=s.confidence,
            rationale=s.rationale,
        )
        for s in suggestions
    ]

    return {
        "suggestions": response_suggestions,
        "unassigned_count": unassigned_count,
        "min_required": MIN_ACTIONS_FOR_AUTOGEN,
    }


@router.post(
    "/autogenerate",
    response_model=AutogenCreateResponse,
    status_code=201,
    summary="Create projects from suggestions",
    description="Create projects from selected autogenerate suggestions",
)
@handle_api_errors("create from autogen")
async def create_from_autogen(
    request: AutogenCreateRequest,
    user: dict = Depends(get_current_user),
) -> AutogenCreateResponse:
    """Create projects from selected suggestions.

    Creates projects from the provided suggestions and assigns
    the corresponding actions to each project.
    """
    from backend.services.project_autogen import (
        AutogenProjectSuggestion,
        create_projects_from_suggestions,
    )

    user_id = user["user_id"]

    if not request.suggestions:
        return {"created_projects": [], "count": 0}

    # Convert request suggestions to service dataclass
    service_suggestions = [
        AutogenProjectSuggestion(
            id=s.id,
            name=s.name,
            description=s.description,
            action_ids=s.action_ids,
            confidence=s.confidence,
            rationale=s.rationale,
        )
        for s in request.suggestions
    ]

    # Create projects
    created = await create_projects_from_suggestions(
        suggestions=service_suggestions,
        user_id=user_id,
        workspace_id=request.workspace_id,
    )

    # Format responses
    formatted_projects = [_format_project_response(p) for p in created]

    return {
        "created_projects": formatted_projects,
        "count": len(formatted_projects),
    }


@router.get(
    "/unassigned-count",
    response_model=UnassignedCountResponse,
    summary="Get unassigned actions count",
    description="Get the count of actions not assigned to any project",
)
@handle_api_errors("get unassigned count")
async def get_unassigned_count(
    user: dict = Depends(get_current_user),
) -> UnassignedCountResponse:
    """Get count of unassigned actions."""
    from backend.services.project_autogen import (
        MIN_ACTIONS_FOR_AUTOGEN,
        get_unassigned_action_count,
    )

    user_id = user["user_id"]
    count = get_unassigned_action_count(user_id)

    return UnassignedCountResponse(
        unassigned_count=count,
        min_required=MIN_ACTIONS_FOR_AUTOGEN,
        can_autogenerate=count >= MIN_ACTIONS_FOR_AUTOGEN,
    )


# =========================================================================
# Context-Based Project Suggestions
# =========================================================================


@router.get(
    "/context-suggestions",
    response_model=ContextSuggestionsResponse,
    summary="Get context-based project suggestions",
    description="Generate project suggestions from user's business context",
)
@handle_api_errors("get context suggestions")
async def get_context_suggestions(
    user: dict = Depends(get_current_user),
) -> ContextSuggestionsResponse:
    """Get project suggestions based on business context.

    Analyzes the user's business context (primary_objective, industry, etc.)
    and suggests strategic projects aligned with their priorities.
    """
    from backend.services.context_project_suggester import (
        get_context_completeness,
        suggest_from_context,
    )

    user_id = user["user_id"]

    # Check context completeness first
    completeness = get_context_completeness(user_id)

    if not completeness["has_minimum"]:
        return {
            "suggestions": [],
            "context_completeness": completeness["completeness"],
            "has_minimum_context": False,
            "missing_fields": completeness["missing_required"]
            + completeness["missing_recommended"],
        }

    # Get suggestions from LLM
    suggestions = await suggest_from_context(user_id)

    # Convert to response model format
    response_suggestions = [
        ContextProjectSuggestion(
            id=s.id,
            name=s.name,
            description=s.description,
            rationale=s.rationale,
            category=s.category,
            priority=s.priority,
        )
        for s in suggestions
    ]

    return {
        "suggestions": response_suggestions,
        "context_completeness": completeness["completeness"],
        "has_minimum_context": True,
        "missing_fields": completeness["missing_recommended"],
    }


@router.post(
    "/context-suggestions",
    response_model=AutogenCreateResponse,
    status_code=201,
    summary="Create projects from context suggestions",
    description="Create projects from selected context-based suggestions",
)
@handle_api_errors("create from context suggestions")
async def create_from_context_suggestions(
    request: ContextCreateRequest,
    user: dict = Depends(get_current_user),
) -> AutogenCreateResponse:
    """Create projects from selected context suggestions.

    Creates projects from the provided suggestions.
    """
    user_id = user["user_id"]

    if not request.suggestions:
        return {"created_projects": [], "count": 0}

    created_projects = []

    for suggestion in request.suggestions:
        # Create project
        project = project_repository.create(
            user_id=user_id,
            name=suggestion.name,
            description=suggestion.description,
        )

        if not project:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to create project: {suggestion.name}",
                user_id=user_id,
            )
            continue

        project_id = str(project["id"])

        # Update workspace_id if provided
        if request.workspace_id:
            from bo1.state.database import db_session

            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE projects SET workspace_id = %s WHERE id = %s",
                        (request.workspace_id, project_id),
                    )

        # Get updated project
        updated_project = project_repository.get(project_id)
        if updated_project:
            created_projects.append(_format_project_response(updated_project))

    return {
        "created_projects": created_projects,
        "count": len(created_projects),
    }
