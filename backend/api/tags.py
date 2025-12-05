"""Tags API endpoints for user-generated tag management.

Provides:
- GET /api/v1/tags - Get all user's tags
- POST /api/v1/tags - Create a new tag
- PATCH /api/v1/tags/{tag_id} - Update a tag
- DELETE /api/v1/tags/{tag_id} - Delete a tag
- GET /api/v1/actions/{action_id}/tags - Get tags for an action
- PUT /api/v1/actions/{action_id}/tags - Set tags for an action
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    TagCreate,
    TagListResponse,
    TagResponse,
    TagUpdate,
)
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.tag_repository import tag_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tags", tags=["tags"])


def _format_tag_response(tag: dict[str, Any]) -> TagResponse:
    """Format tag dict to TagResponse."""
    return TagResponse(
        id=str(tag["id"]),
        user_id=tag["user_id"],
        name=tag["name"],
        color=tag["color"],
        action_count=tag.get("action_count", 0),
        created_at=tag["created_at"].isoformat() if tag.get("created_at") else "",
        updated_at=tag["updated_at"].isoformat() if tag.get("updated_at") else "",
    )


@router.get(
    "",
    response_model=TagListResponse,
    summary="Get all user tags",
    description="Get all tags for the current user.",
    responses={
        200: {"description": "Tags retrieved successfully"},
    },
)
@handle_api_errors("get tags")
async def get_tags(
    user_data: dict = Depends(get_current_user),
) -> TagListResponse:
    """Get all tags for the current user.

    Args:
        user_data: Current user from auth

    Returns:
        TagListResponse with all user's tags
    """
    user_id = user_data.get("user_id")
    logger.info(f"Fetching tags for user {user_id}")

    tags = tag_repository.get_by_user(user_id)

    return TagListResponse(
        tags=[_format_tag_response(tag) for tag in tags],
        total=len(tags),
    )


@router.post(
    "",
    response_model=TagResponse,
    summary="Create a tag",
    description="Create a new tag for the current user.",
    responses={
        200: {"description": "Tag created successfully"},
        400: {"description": "Tag name already exists"},
    },
)
@handle_api_errors("create tag")
async def create_tag(
    tag_data: TagCreate,
    user_data: dict = Depends(get_current_user),
) -> TagResponse:
    """Create a new tag.

    Args:
        tag_data: Tag creation request
        user_data: Current user from auth

    Returns:
        Created TagResponse
    """
    user_id = user_data.get("user_id")
    logger.info(f"Creating tag '{tag_data.name}' for user {user_id}")

    try:
        tag = tag_repository.create(
            user_id=user_id,
            name=tag_data.name,
            color=tag_data.color,
        )
        return _format_tag_response(tag)
    except Exception as e:
        if "uq_tags_user_name" in str(e) or "duplicate key" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail=f"Tag '{tag_data.name}' already exists",
            ) from None
        logger.error(f"Failed to create tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tag") from None


@router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update a tag",
    description="Update an existing tag.",
    responses={
        200: {"description": "Tag updated successfully"},
        404: {"description": "Tag not found"},
    },
)
@handle_api_errors("update tag")
async def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    user_data: dict = Depends(get_current_user),
) -> TagResponse:
    """Update an existing tag.

    Args:
        tag_id: Tag UUID
        tag_data: Tag update request
        user_data: Current user from auth

    Returns:
        Updated TagResponse
    """
    user_id = user_data.get("user_id")
    logger.info(f"Updating tag {tag_id} for user {user_id}")

    tag = tag_repository.update(
        tag_id=tag_id,
        user_id=user_id,
        name=tag_data.name,
        color=tag_data.color,
    )

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return _format_tag_response(tag)


@router.delete(
    "/{tag_id}",
    summary="Delete a tag",
    description="Delete a tag (removes from all actions).",
    responses={
        200: {"description": "Tag deleted successfully"},
        404: {"description": "Tag not found"},
    },
)
@handle_api_errors("delete tag")
async def delete_tag(
    tag_id: str,
    user_data: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a tag.

    Args:
        tag_id: Tag UUID
        user_data: Current user from auth

    Returns:
        Success message
    """
    user_id = user_data.get("user_id")
    logger.info(f"Deleting tag {tag_id} for user {user_id}")

    if not tag_repository.delete(tag_id, user_id):
        raise HTTPException(status_code=404, detail="Tag not found")

    return {"message": "Tag deleted successfully", "tag_id": tag_id}
