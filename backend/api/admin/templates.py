"""Admin Meeting Templates API endpoints.

Admin-only endpoints for template management:
- GET /api/admin/templates - List all templates (including inactive)
- POST /api/admin/templates - Create a template
- PATCH /api/admin/templates/{id} - Update a template
- DELETE /api/admin/templates/{id} - Delete or deactivate a template
- GET /api/admin/templates/stats - Get template usage statistics
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends

from backend.api.middleware.admin import require_admin_any
from backend.api.models import (
    MeetingTemplate,
    MeetingTemplateCreate,
    MeetingTemplateListResponse,
    MeetingTemplateUpdate,
)
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories.template_repository import template_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["admin-templates"])


def _format_template_response(template: dict[str, Any]) -> MeetingTemplate:
    """Format template dict to MeetingTemplate response."""
    return MeetingTemplate(
        id=str(template["id"]),
        name=template["name"],
        slug=template["slug"],
        description=template["description"],
        category=template["category"],
        problem_statement_template=template["problem_statement_template"],
        context_hints=template.get("context_hints") or [],
        suggested_persona_traits=template.get("suggested_persona_traits") or [],
        is_builtin=template.get("is_builtin", False),
        version=template.get("version", 1),
        created_at=template["created_at"],
        updated_at=template["updated_at"],
    )


@router.get(
    "",
    response_model=MeetingTemplateListResponse,
    summary="List all templates (admin)",
    description="Get all templates including inactive ones for management.",
    responses={
        200: {"description": "Templates retrieved successfully"},
        403: {"description": "Admin access required"},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("list templates admin")
async def list_templates_admin(
    include_inactive: bool = True,
) -> MeetingTemplateListResponse:
    """List all templates for admin management.

    Args:
        include_inactive: Include deactivated templates (default True)

    Returns:
        MeetingTemplateListResponse with all templates
    """
    logger.info(f"Admin listing templates, include_inactive={include_inactive}")

    templates = template_repository.list_all(include_inactive=include_inactive)
    categories = template_repository.get_categories()

    return MeetingTemplateListResponse(
        templates=[_format_template_response(t) for t in templates],
        total=len(templates),
        categories=categories,
    )


@router.post(
    "",
    response_model=MeetingTemplate,
    summary="Create a template",
    description="Create a new meeting template.",
    responses={
        200: {"description": "Template created successfully"},
        400: {"description": "Slug already exists"},
        403: {"description": "Admin access required"},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("create template")
async def create_template(
    template_data: MeetingTemplateCreate,
) -> MeetingTemplate:
    """Create a new meeting template.

    Args:
        template_data: Template creation request

    Returns:
        Created MeetingTemplate
    """
    logger.info(f"Creating template name='{template_data.name}' slug='{template_data.slug}'")

    # Check for duplicate slug
    if template_repository.slug_exists(template_data.slug):
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Template with slug '{template_data.slug}' already exists",
            status=400,
        )

    try:
        template = template_repository.create(
            name=template_data.name,
            slug=template_data.slug,
            description=template_data.description,
            category=template_data.category,
            problem_statement_template=template_data.problem_statement_template,
            context_hints=template_data.context_hints,
            suggested_persona_traits=template_data.suggested_persona_traits,
        )
        return _format_template_response(template)
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to create template: {e}",
            slug=template_data.slug,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            "Failed to create template",
            status=500,
        ) from None


@router.patch(
    "/{template_id}",
    response_model=MeetingTemplate,
    summary="Update a template",
    description="Update an existing meeting template.",
    responses={
        200: {"description": "Template updated successfully"},
        404: {"description": "Template not found"},
        403: {"description": "Admin access required"},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("update template")
async def update_template(
    template_id: str,
    template_data: MeetingTemplateUpdate,
) -> MeetingTemplate:
    """Update an existing template.

    Args:
        template_id: Template UUID
        template_data: Template update request

    Returns:
        Updated MeetingTemplate
    """
    logger.info(f"Updating template {template_id}")

    template = template_repository.update(
        template_id=template_id,
        name=template_data.name,
        description=template_data.description,
        category=template_data.category,
        problem_statement_template=template_data.problem_statement_template,
        context_hints=template_data.context_hints,
        suggested_persona_traits=template_data.suggested_persona_traits,
        is_active=template_data.is_active,
    )

    if not template:
        raise http_error(ErrorCode.API_NOT_FOUND, "Template not found", status=404)

    return _format_template_response(template)


@router.delete(
    "/{template_id}",
    summary="Delete or deactivate a template",
    description="Delete a custom template or deactivate a builtin template.",
    responses={
        200: {"description": "Template deleted/deactivated successfully"},
        404: {"description": "Template not found"},
        403: {"description": "Admin access required"},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("delete template")
async def delete_template(
    template_id: str,
    hard_delete: bool = False,
) -> dict[str, Any]:
    """Delete or deactivate a template.

    Builtin templates can only be deactivated, not hard deleted.
    Custom templates can be hard deleted with the hard_delete flag.

    Args:
        template_id: Template UUID
        hard_delete: If True, hard delete custom templates

    Returns:
        Success message
    """
    logger.info(f"Deleting template {template_id}, hard_delete={hard_delete}")

    # Get template to check if builtin
    template = template_repository.get_by_id(template_id)
    if not template:
        raise http_error(ErrorCode.API_NOT_FOUND, "Template not found", status=404)

    if hard_delete and not template.get("is_builtin", False):
        # Hard delete non-builtin templates
        if template_repository.delete(template_id):
            return {"message": "Template deleted successfully", "template_id": template_id}
        raise http_error(ErrorCode.API_NOT_FOUND, "Template not found", status=404)
    else:
        # Soft delete (deactivate)
        result = template_repository.deactivate(template_id)
        if result:
            return {"message": "Template deactivated successfully", "template_id": template_id}
        raise http_error(ErrorCode.API_NOT_FOUND, "Template not found", status=404)


@router.post(
    "/{template_id}/activate",
    response_model=MeetingTemplate,
    summary="Activate a template",
    description="Reactivate a deactivated template.",
    responses={
        200: {"description": "Template activated successfully"},
        404: {"description": "Template not found"},
        403: {"description": "Admin access required"},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("activate template")
async def activate_template(
    template_id: str,
) -> MeetingTemplate:
    """Reactivate a deactivated template.

    Args:
        template_id: Template UUID

    Returns:
        Activated MeetingTemplate
    """
    logger.info(f"Activating template {template_id}")

    template = template_repository.activate(template_id)
    if not template:
        raise http_error(ErrorCode.API_NOT_FOUND, "Template not found", status=404)

    return _format_template_response(template)


@router.get(
    "/stats",
    summary="Get template usage statistics",
    description="Get usage statistics for all templates.",
    responses={
        200: {"description": "Stats retrieved successfully"},
        403: {"description": "Admin access required"},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("get template stats")
async def get_template_stats() -> dict[str, Any]:
    """Get template usage statistics.

    Returns:
        Dict with template usage stats
    """
    logger.info("Getting template usage stats")

    stats = template_repository.get_usage_stats()

    return {
        "templates": [
            {
                "id": str(s["id"]),
                "name": s["name"],
                "slug": s["slug"],
                "category": s["category"],
                "usage_count": s["usage_count"],
                "last_used_at": s["last_used_at"].isoformat() if s.get("last_used_at") else None,
            }
            for s in stats
        ],
        "total_templates": len(stats),
        "total_usage": sum(s["usage_count"] for s in stats),
    }
