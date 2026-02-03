"""Project model for Board of One.

Provides type-safe project handling with Pydantic validation.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bo1.models.util import coerce_enum, normalize_uuid, normalize_uuid_required


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Project(BaseModel):
    """Project model matching PostgreSQL projects table.

    Projects are value-delivery containers that group related actions.
    """

    # Identity
    id: str = Field(..., description="Project UUID")
    user_id: str = Field(..., description="Owner of the project")

    # Core fields
    name: str = Field(..., description="Project name", max_length=255)
    description: str | None = Field(None, description="Project description and goals")

    # Status
    status: ProjectStatus = Field(ProjectStatus.ACTIVE, description="Current project status")

    # Date fields
    target_start_date: date | None = Field(None, description="User-set target start date")
    target_end_date: date | None = Field(None, description="User-set target end date")
    estimated_start_date: date | None = Field(
        None, description="Calculated: min(actions.estimated_start_date)"
    )
    estimated_end_date: date | None = Field(
        None, description="Calculated: max(actions.estimated_end_date)"
    )
    actual_start_date: datetime | None = Field(None, description="When first action started")
    actual_end_date: datetime | None = Field(None, description="When all actions completed")

    # Progress tracking
    progress_percent: int = Field(0, description="Calculated from completed actions", ge=0, le=100)
    total_actions: int = Field(0, description="Total number of actions in project", ge=0)
    completed_actions: int = Field(0, description="Number of completed actions", ge=0)

    # Visual customization
    color: str | None = Field(None, description="Hex color for Gantt visualization", max_length=7)
    icon: str | None = Field(None, description="Emoji or icon name", max_length=50)

    # Workspace scope (from av1 migration)
    workspace_id: str | None = Field(
        None, description="Workspace UUID (NULL for personal projects)"
    )

    # Versioning (from ay1 migration)
    version: int = Field(1, description="Version number for project versioning (v1, v2, etc)")
    source_project_id: str | None = Field(
        None, description="ID of the project this was versioned from"
    )

    # Timestamps
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "user_456",
                    "name": "Q1 Marketing Campaign",
                    "description": "Launch new product marketing",
                    "status": "active",
                    "progress_percent": 45,
                }
            ]
        },
    )

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Project":
        """Create Project from database row dict.

        Args:
            row: Dict from psycopg2 cursor with project columns

        Returns:
            Project instance with validated data

        Example:
            >>> row = {"id": "uuid", "user_id": "u1", "name": "Test", ...}
            >>> project = Project.from_db_row(row)
        """
        return cls(
            # Identity
            id=normalize_uuid_required(row["id"]),
            user_id=row["user_id"],
            # Core fields
            name=row["name"],
            description=row.get("description"),
            # Status
            status=coerce_enum(row.get("status"), ProjectStatus, ProjectStatus.ACTIVE),
            # Dates
            target_start_date=row.get("target_start_date"),
            target_end_date=row.get("target_end_date"),
            estimated_start_date=row.get("estimated_start_date"),
            estimated_end_date=row.get("estimated_end_date"),
            actual_start_date=row.get("actual_start_date"),
            actual_end_date=row.get("actual_end_date"),
            # Progress
            progress_percent=row.get("progress_percent", 0),
            total_actions=row.get("total_actions", 0),
            completed_actions=row.get("completed_actions", 0),
            # Visual
            color=row.get("color"),
            icon=row.get("icon"),
            # Workspace
            workspace_id=normalize_uuid(row.get("workspace_id")),
            # Versioning
            version=row.get("version", 1),
            source_project_id=normalize_uuid(row.get("source_project_id")),
            # Timestamps
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
