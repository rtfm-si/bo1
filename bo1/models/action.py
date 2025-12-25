"""Action model for Board of One.

Provides type-safe action handling with Pydantic validation.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActionStatus(str, Enum):
    """Action lifecycle status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class ActionPriority(str, Enum):
    """Action priority levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionCategory(str, Enum):
    """Action category types."""

    IMPLEMENTATION = "implementation"
    RESEARCH = "research"
    DECISION = "decision"
    COMMUNICATION = "communication"


class FailureReasonCategory(str, Enum):
    """Failure reason category for replanning."""

    BLOCKER = "blocker"
    SCOPE_CREEP = "scope_creep"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class Action(BaseModel):
    """Action model matching PostgreSQL actions table.

    Provides type-safe access to action data with validation.
    All UUID fields are returned as strings from psycopg2.
    """

    # Identity
    id: str = Field(..., description="Action UUID")
    user_id: str = Field(..., description="User who owns the action")
    source_session_id: str = Field(..., description="Session this action came from")

    # Core fields
    title: str = Field(..., description="Short action title (5-10 words)")
    description: str = Field(..., description="Full action description")
    what_and_how: list[str] = Field(
        default_factory=list, description="Array of steps to complete the action"
    )
    success_criteria: list[str] = Field(
        default_factory=list, description="Array of success measures"
    )
    kill_criteria: list[str] = Field(
        default_factory=list, description="Array of abandonment conditions"
    )

    # Status and tracking
    status: ActionStatus = Field(ActionStatus.TODO, description="Current action status")
    priority: ActionPriority = Field(ActionPriority.MEDIUM, description="Action priority")
    category: ActionCategory = Field(ActionCategory.IMPLEMENTATION, description="Action category")
    sort_order: int = Field(0, description="User-defined sort order within status column")
    confidence: Decimal = Field(
        Decimal("0.0"), description="AI extraction confidence (0.0-1.0)", ge=0, le=1
    )
    source_section: str | None = Field(None, description="Which synthesis section this came from")
    sub_problem_index: int | None = Field(
        None, description="Which sub-problem/focus area this belongs to"
    )

    # Timeline fields
    timeline: str | None = Field(None, description="Human-readable timeline (e.g., '2 weeks')")
    estimated_duration_days: int | None = Field(
        None, description="Parsed duration in business days", gt=0
    )

    # Date fields (DATE for target/estimated, TIMESTAMPTZ for actual)
    target_start_date: date | None = Field(None, description="User-set target start date")
    target_end_date: date | None = Field(None, description="User-set target end date")
    estimated_start_date: date | None = Field(None, description="Auto-calculated from dependencies")
    estimated_end_date: date | None = Field(
        None, description="Auto-calculated from start + duration"
    )
    actual_start_date: datetime | None = Field(None, description="Actual start timestamp")
    actual_end_date: datetime | None = Field(None, description="Actual completion timestamp")

    # Blocking mechanism
    blocking_reason: str | None = Field(None, description="Reason for blocking")
    blocked_at: datetime | None = Field(None, description="When action was blocked")
    auto_unblock: bool = Field(False, description="Auto-unblock when dependencies complete")

    # Project link (from a7 migration)
    project_id: str | None = Field(None, description="Parent project UUID (optional)")

    # Replanning fields (from a8 migration)
    replan_session_id: str | None = Field(None, description="Session created to replan this action")
    replan_requested_at: datetime | None = Field(None, description="When replanning was requested")
    replanning_reason: str | None = Field(None, description="User-provided replanning context")

    # Extended replanning fields (from x1 migration)
    failure_reason_category: FailureReasonCategory | None = Field(
        None, description="Category of why action failed"
    )
    replan_suggested_at: datetime | None = Field(
        None, description="When replanning suggestion was shown"
    )
    replan_session_created_id: str | None = Field(
        None, description="Session created from replanning suggestion"
    )

    # Close/replan fields (from z4 migration)
    closure_reason: str | None = Field(
        None, description="Reason for closing action as failed/abandoned"
    )
    replanned_from_id: str | None = Field(
        None, description="Original action ID when created via replan"
    )

    # Soft delete (from b2 migration)
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp (NULL = active)")

    # Post-mortem fields (from z28 migration)
    lessons_learned: str | None = Field(None, description="User reflection on lessons learned")
    went_well: str | None = Field(None, description="User reflection on what went well")

    # Timestamps
    created_at: datetime = Field(..., description="Action creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "user_456",
                    "source_session_id": "bo1_abc123",
                    "title": "Implement user authentication",
                    "description": "Add OAuth login flow",
                    "status": "in_progress",
                    "priority": "high",
                    "category": "implementation",
                }
            ]
        },
    )

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Action":
        """Create Action from database row dict.

        Args:
            row: Dict from psycopg2 cursor with action columns

        Returns:
            Action instance with validated data

        Example:
            >>> row = {"id": "uuid", "user_id": "u1", "title": "Test", ...}
            >>> action = Action.from_db_row(row)
        """
        # Handle status as string or enum
        status = row.get("status", "todo")
        if isinstance(status, str):
            status = ActionStatus(status)

        # Handle priority as string or enum
        priority = row.get("priority", "medium")
        if isinstance(priority, str):
            priority = ActionPriority(priority)

        # Handle category as string or enum
        category = row.get("category", "implementation")
        if isinstance(category, str):
            category = ActionCategory(category)

        # Handle failure_reason_category as string or enum
        failure_reason_category = row.get("failure_reason_category")
        if isinstance(failure_reason_category, str):
            failure_reason_category = FailureReasonCategory(failure_reason_category)

        # Handle UUID fields (psycopg2 returns strings, not UUID objects)
        id_val = row["id"]
        if hasattr(id_val, "hex"):
            id_val = str(id_val)

        project_id = row.get("project_id")
        if project_id is not None and hasattr(project_id, "hex"):
            project_id = str(project_id)

        replanned_from_id = row.get("replanned_from_id")
        if replanned_from_id is not None and hasattr(replanned_from_id, "hex"):
            replanned_from_id = str(replanned_from_id)

        # Handle array fields (None → empty list)
        what_and_how = row.get("what_and_how") or []
        success_criteria = row.get("success_criteria") or []
        kill_criteria = row.get("kill_criteria") or []

        return cls(
            # Identity
            id=id_val,
            user_id=row["user_id"],
            source_session_id=row["source_session_id"],
            # Core fields
            title=row["title"],
            description=row["description"],
            what_and_how=what_and_how,
            success_criteria=success_criteria,
            kill_criteria=kill_criteria,
            # Status and tracking
            status=status,
            priority=priority,
            category=category,
            sort_order=row.get("sort_order", 0),
            confidence=Decimal(str(row.get("confidence", 0.0))),
            source_section=row.get("source_section"),
            sub_problem_index=row.get("sub_problem_index"),
            # Timeline
            timeline=row.get("timeline"),
            estimated_duration_days=row.get("estimated_duration_days"),
            # Dates
            target_start_date=row.get("target_start_date"),
            target_end_date=row.get("target_end_date"),
            estimated_start_date=row.get("estimated_start_date"),
            estimated_end_date=row.get("estimated_end_date"),
            actual_start_date=row.get("actual_start_date"),
            actual_end_date=row.get("actual_end_date"),
            # Blocking
            blocking_reason=row.get("blocking_reason"),
            blocked_at=row.get("blocked_at"),
            auto_unblock=row.get("auto_unblock", False),
            # Project link
            project_id=project_id,
            # Replanning (a8)
            replan_session_id=row.get("replan_session_id"),
            replan_requested_at=row.get("replan_requested_at"),
            replanning_reason=row.get("replanning_reason"),
            # Extended replanning (x1)
            failure_reason_category=failure_reason_category,
            replan_suggested_at=row.get("replan_suggested_at"),
            replan_session_created_id=row.get("replan_session_created_id"),
            # Close/replan (z4)
            closure_reason=row.get("closure_reason"),
            replanned_from_id=replanned_from_id,
            # Soft delete
            deleted_at=row.get("deleted_at"),
            # Post-mortem
            lessons_learned=row.get("lessons_learned"),
            went_well=row.get("went_well"),
            # Timestamps
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
