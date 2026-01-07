"""Meeting Templates API endpoints.

Public endpoints:
- GET /api/v1/templates - List active templates for gallery
- GET /api/v1/templates/{slug} - Get template by slug

Templates pre-populate problem statements and suggest context for common
decision scenarios like product launches, pricing changes, etc.
"""

import logging
from typing import Any

from fastapi import APIRouter

from backend.api.models import (
    MeetingTemplate,
    MeetingTemplateListResponse,
)
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging import ErrorCode
from bo1.state.repositories.template_repository import template_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/templates", tags=["templates"])


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
    summary="List meeting templates",
    description="Get all active meeting templates for the template gallery.",
    responses={
        200: {"description": "Templates retrieved successfully"},
    },
)
@handle_api_errors("list templates")
async def list_templates(
    category: str | None = None,
) -> MeetingTemplateListResponse:
    """List all active templates for public gallery.

    Args:
        category: Optional category filter (strategy, pricing, product, growth)

    Returns:
        MeetingTemplateListResponse with templates and available categories
    """
    logger.info(f"Listing templates, category={category}")

    templates = template_repository.list_active(category=category)
    categories = template_repository.get_categories()

    return MeetingTemplateListResponse(
        templates=[_format_template_response(t) for t in templates],
        total=len(templates),
        categories=categories,
    )


@router.get(
    "/{slug}",
    response_model=MeetingTemplate,
    summary="Get template by slug",
    description="Get a specific template by its URL slug.",
    responses={
        200: {"description": "Template retrieved successfully"},
        404: {"description": "Template not found"},
    },
)
@handle_api_errors("get template")
async def get_template(
    slug: str,
) -> MeetingTemplate:
    """Get a template by slug.

    Args:
        slug: Template URL slug

    Returns:
        MeetingTemplate
    """
    logger.info(f"Getting template slug={slug}")

    template = template_repository.get_by_slug(slug)
    if not template:
        raise http_error(ErrorCode.API_NOT_FOUND, "Template not found", 404)

    return _format_template_response(template)
