"""Dataset folder models for hierarchical organization.

Pydantic models for folder management supporting:
- Folder CRUD with tags
- Dataset membership
- Nested folder trees
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DatasetFolderBase(BaseModel):
    """Base fields for dataset folders."""

    name: str = Field(..., min_length=1, max_length=100, description="Folder name")
    description: str | None = Field(None, max_length=500, description="Optional description")
    color: str | None = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color e.g. #FF5733"
    )
    icon: str | None = Field(None, max_length=50, description="Icon name")


class DatasetFolderCreate(DatasetFolderBase):
    """Request model for creating a folder."""

    parent_folder_id: str | None = Field(None, description="Parent folder UUID for nesting")
    tags: list[str] = Field(default_factory=list, description="Tags for the folder")


class DatasetFolderUpdate(BaseModel):
    """Request model for updating a folder."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)
    parent_folder_id: str | None = Field(None, description="New parent folder or null for root")
    tags: list[str] | None = Field(None, description="Replace tags if provided")


class DatasetFolderResponse(DatasetFolderBase):
    """Response model for a folder."""

    id: str = Field(..., description="Folder UUID")
    parent_folder_id: str | None = Field(None, description="Parent folder UUID")
    tags: list[str] = Field(default_factory=list, description="Folder tags")
    dataset_count: int = Field(0, description="Number of datasets in folder")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "DatasetFolderResponse":
        """Create response from database row dict."""
        id_val = row["id"]
        if hasattr(id_val, "hex"):
            id_val = str(id_val)

        parent_id = row.get("parent_folder_id")
        if parent_id and hasattr(parent_id, "hex"):
            parent_id = str(parent_id)

        return cls(
            id=id_val,
            name=row["name"],
            description=row.get("description"),
            color=row.get("color"),
            icon=row.get("icon"),
            parent_folder_id=parent_id,
            tags=row.get("tags", []),
            dataset_count=row.get("dataset_count", 0),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class DatasetFolderTree(DatasetFolderResponse):
    """Folder with nested children for tree view."""

    children: list["DatasetFolderTree"] = Field(default_factory=list, description="Child folders")


class DatasetFolderListResponse(BaseModel):
    """Response for listing folders."""

    folders: list[DatasetFolderResponse] = Field(default_factory=list)
    total: int = Field(0, description="Total folder count")


class DatasetFolderTreeResponse(BaseModel):
    """Response for folder tree."""

    folders: list[DatasetFolderTree] = Field(default_factory=list)
    total: int = Field(0, description="Total folder count")


class AddDatasetsRequest(BaseModel):
    """Request to add datasets to a folder."""

    dataset_ids: list[str] = Field(..., min_length=1, description="Dataset UUIDs to add")


class FolderDatasetResponse(BaseModel):
    """Basic dataset info for folder membership listing."""

    id: str = Field(..., description="Dataset UUID")
    name: str = Field(..., description="Dataset name")
    added_at: datetime = Field(..., description="When added to folder")

    model_config = ConfigDict(from_attributes=True)


class FolderDatasetsListResponse(BaseModel):
    """Response listing datasets in a folder."""

    datasets: list[FolderDatasetResponse] = Field(default_factory=list)
    total: int = Field(0)


class FolderTagsResponse(BaseModel):
    """Response listing all unique folder tags for a user."""

    tags: list[str] = Field(default_factory=list)


class AddDatasetsResponse(BaseModel):
    """Response for adding datasets to a folder."""

    added: int = Field(..., description="Number of datasets added")
    total_requested: int = Field(..., description="Total datasets requested")
