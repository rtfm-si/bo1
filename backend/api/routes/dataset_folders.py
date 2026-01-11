"""Dataset folders API endpoints for hierarchical organization.

Provides:
- POST /api/v1/datasets/folders - Create folder
- GET /api/v1/datasets/folders - List user folders
- GET /api/v1/datasets/folders/tree - List folders as nested tree
- GET /api/v1/datasets/folders/tags - List all user's folder tags
- GET /api/v1/datasets/folders/{id} - Get folder with datasets
- PATCH /api/v1/datasets/folders/{id} - Update folder
- DELETE /api/v1/datasets/folders/{id} - Delete folder
- POST /api/v1/datasets/folders/{id}/datasets - Add datasets to folder
- DELETE /api/v1/datasets/folders/{id}/datasets/{dataset_id} - Remove from folder
- GET /api/v1/datasets/folders/{id}/datasets - List datasets in folder
"""

import logging

from fastapi import APIRouter, Depends, Query

from backend.api.middleware.auth import get_current_user
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode
from bo1.models.dataset_folder import (
    AddDatasetsRequest,
    AddDatasetsResponse,
    DatasetFolderCreate,
    DatasetFolderListResponse,
    DatasetFolderResponse,
    DatasetFolderTree,
    DatasetFolderTreeResponse,
    DatasetFolderUpdate,
    FolderDatasetResponse,
    FolderDatasetsListResponse,
    FolderTagsResponse,
)
from bo1.state.repositories.dataset_folder_repository import dataset_folder_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/datasets/folders")


@router.post("", response_model=DatasetFolderResponse, status_code=201)
@handle_api_errors("create folder")
async def create_folder(
    request: DatasetFolderCreate,
    user: dict = Depends(get_current_user),
) -> DatasetFolderResponse:
    """Create a new dataset folder."""
    user_id = user["user_id"]

    folder = dataset_folder_repository.create_folder(
        user_id=user_id,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
        parent_folder_id=request.parent_folder_id,
        tags=request.tags,
    )

    return DatasetFolderResponse.from_db_row(folder)


@router.get("", response_model=DatasetFolderListResponse)
@handle_api_errors("list folders")
async def list_folders(
    user: dict = Depends(get_current_user),
    parent_id: str | None = Query(None, description="Filter by parent folder"),
    tag: str | None = Query(None, description="Filter by tag"),
) -> DatasetFolderListResponse:
    """List user's dataset folders (flat list)."""
    user_id = user["user_id"]

    if parent_id or tag:
        folders = dataset_folder_repository.list_folders(
            user_id=user_id,
            parent_folder_id=parent_id,
            tag=tag,
        )
    else:
        folders = dataset_folder_repository.list_all_folders(user_id)

    return DatasetFolderListResponse(
        folders=[DatasetFolderResponse.from_db_row(f) for f in folders],
        total=len(folders),
    )


@router.get("/tree", response_model=DatasetFolderTreeResponse)
@handle_api_errors("list folder tree")
async def list_folders_tree(
    user: dict = Depends(get_current_user),
) -> DatasetFolderTreeResponse:
    """Get folder tree with nested children."""
    user_id = user["user_id"]
    folders = dataset_folder_repository.get_folder_tree(user_id)
    return DatasetFolderTreeResponse(
        folders=[_build_tree_node(f) for f in folders],
        total=len(folders),
    )


def _build_tree_node(folder: dict) -> DatasetFolderTree:
    """Recursively build tree node from folder dict."""
    return DatasetFolderTree(
        id=str(folder["id"]),
        name=folder["name"],
        description=folder.get("description"),
        color=folder.get("color"),
        icon=folder.get("icon"),
        parent_folder_id=str(folder["parent_folder_id"])
        if folder.get("parent_folder_id")
        else None,
        tags=folder.get("tags", []),
        dataset_count=folder.get("dataset_count", 0),
        created_at=folder["created_at"],
        updated_at=folder["updated_at"],
        children=[_build_tree_node(c) for c in folder.get("children", [])],
    )


@router.get("/tags", response_model=FolderTagsResponse)
@handle_api_errors("list folder tags")
async def list_tags(
    user: dict = Depends(get_current_user),
) -> FolderTagsResponse:
    """List all unique folder tags for the user."""
    user_id = user["user_id"]
    tags = dataset_folder_repository.get_all_tags(user_id)
    return FolderTagsResponse(tags=tags)


@router.get("/{folder_id}", response_model=DatasetFolderResponse)
@handle_api_errors("get folder")
async def get_folder(
    folder_id: str,
    user: dict = Depends(get_current_user),
) -> DatasetFolderResponse:
    """Get a folder by ID."""
    user_id = user["user_id"]
    folder = dataset_folder_repository.get_folder(folder_id, user_id)
    if not folder:
        raise http_error(ErrorCode.API_NOT_FOUND, "Folder not found", status=404)
    return DatasetFolderResponse.from_db_row(folder)


@router.patch("/{folder_id}", response_model=DatasetFolderResponse)
@handle_api_errors("update folder")
async def update_folder(
    folder_id: str,
    request: DatasetFolderUpdate,
    user: dict = Depends(get_current_user),
) -> DatasetFolderResponse:
    """Update a folder."""
    user_id = user["user_id"]

    # Check if clearing parent (moving to root)
    clear_parent = request.parent_folder_id == ""

    folder = dataset_folder_repository.update_folder(
        folder_id=folder_id,
        user_id=user_id,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
        parent_folder_id=request.parent_folder_id if not clear_parent else None,
        tags=request.tags,
        clear_parent=clear_parent,
    )

    if not folder:
        raise http_error(ErrorCode.API_NOT_FOUND, "Folder not found", status=404)

    return DatasetFolderResponse.from_db_row(folder)


@router.delete("/{folder_id}", status_code=204, response_model=None)
@handle_api_errors("delete folder")
async def delete_folder(
    folder_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a folder. Datasets are removed from folder (not deleted)."""
    user_id = user["user_id"]
    deleted = dataset_folder_repository.delete_folder(folder_id, user_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Folder not found", status=404)


@router.post("/{folder_id}/datasets", response_model=AddDatasetsResponse)
@handle_api_errors("add datasets to folder")
async def add_datasets_to_folder(
    folder_id: str,
    request: AddDatasetsRequest,
    user: dict = Depends(get_current_user),
) -> AddDatasetsResponse:
    """Add datasets to a folder."""
    user_id = user["user_id"]

    # Verify folder exists
    folder = dataset_folder_repository.get_folder(folder_id, user_id)
    if not folder:
        raise http_error(ErrorCode.API_NOT_FOUND, "Folder not found", status=404)

    added = dataset_folder_repository.add_datasets_to_folder(
        folder_id=folder_id,
        dataset_ids=request.dataset_ids,
        user_id=user_id,
    )

    return AddDatasetsResponse(added=added, total_requested=len(request.dataset_ids))


@router.delete("/{folder_id}/datasets/{dataset_id}", status_code=204, response_model=None)
@handle_api_errors("remove dataset from folder")
async def remove_dataset_from_folder(
    folder_id: str,
    dataset_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Remove a dataset from a folder."""
    user_id = user["user_id"]
    removed = dataset_folder_repository.remove_dataset_from_folder(
        folder_id=folder_id,
        dataset_id=dataset_id,
        user_id=user_id,
    )
    if not removed:
        raise http_error(ErrorCode.API_NOT_FOUND, "Folder or dataset not found", status=404)


@router.get("/{folder_id}/datasets", response_model=FolderDatasetsListResponse)
@handle_api_errors("list folder datasets")
async def get_folder_datasets(
    folder_id: str,
    user: dict = Depends(get_current_user),
) -> FolderDatasetsListResponse:
    """List datasets in a folder."""
    user_id = user["user_id"]

    # Verify folder exists
    folder = dataset_folder_repository.get_folder(folder_id, user_id)
    if not folder:
        raise http_error(ErrorCode.API_NOT_FOUND, "Folder not found", status=404)

    datasets = dataset_folder_repository.get_folder_datasets(folder_id, user_id)
    return FolderDatasetsListResponse(
        datasets=[
            FolderDatasetResponse(
                id=str(d["id"]),
                name=d["name"],
                added_at=d["added_at"],
            )
            for d in datasets
        ],
        total=len(datasets),
    )
