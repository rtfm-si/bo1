"""Pydantic models for Board of One API.

Defines request/response models for all API endpoints with validation,
examples, and security constraints.
"""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CreateSessionRequest(BaseModel):
    """Request model for creating a new deliberation session.

    Attributes:
        problem_statement: The strategic question to deliberate on
        problem_context: Optional context dictionary for the problem
    """

    problem_statement: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description=(
            "Strategic question for deliberation. "
            "Security: Input is validated against injection patterns. "
            "Rejected: <script> tags (XSS), SQL injection patterns "
            "(DROP TABLE, DELETE FROM, UNION SELECT, etc.)."
        ),
        examples=["Should we invest $500K in expanding to the European market?"],
    )
    problem_context: dict[str, Any] | None = Field(
        None,
        description="Optional context dictionary (max 50KB)",
        examples=[{"budget": 500000, "timeline": "Q2 2025", "market": "B2B SaaS"}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "problem_statement": "Should we invest $500K in expanding to the European market?",
                    "problem_context": {
                        "budget": 500000,
                        "timeline": "Q2 2025",
                        "current_markets": ["US", "Canada"],
                        "target_market": "EU (Germany, France, UK)",
                    },
                },
                {
                    "problem_statement": "What pricing strategy should we use for our new SaaS product?",
                    "problem_context": {
                        "product": "AI-powered project management",
                        "target_customer": "Small businesses (10-50 employees)",
                        "competitors": ["Asana", "Monday.com", "ClickUp"],
                        "cost_per_user": 5.0,
                    },
                },
            ]
        }
    }

    @field_validator("problem_statement")
    @classmethod
    def validate_problem_statement(cls, v: str) -> str:
        """Validate problem statement for malicious content.

        Args:
            v: Problem statement to validate

        Returns:
            Validated problem statement

        Raises:
            ValueError: If problem statement contains malicious content
        """
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check for empty string
        if not v:
            raise ValueError("Problem statement cannot be empty")

        # Check for script tags (XSS prevention)
        if re.search(r"<script[^>]*>", v, re.IGNORECASE):
            raise ValueError("Problem statement cannot contain script tags")

        # Check for SQL injection patterns
        sql_patterns = [
            r";\s*drop\s+table",
            r";\s*delete\s+from",
            r";\s*truncate\s+table",
            r"union\s+select",
            r"insert\s+into",
        ]
        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Problem statement contains invalid SQL patterns")

        return v

    @field_validator("problem_context")
    @classmethod
    def validate_problem_context(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate problem context size.

        Args:
            v: Problem context to validate

        Returns:
            Validated problem context

        Raises:
            ValueError: If context exceeds size limit
        """
        if v is None:
            return v

        # Estimate size (rough JSON serialization size)
        import json

        context_size = len(json.dumps(v))
        if context_size > 50000:  # 50KB limit
            raise ValueError("Problem context exceeds 50KB limit")

        return v


class SessionResponse(BaseModel):
    """Response model for session information.

    Attributes:
        id: Unique session identifier (UUID)
        status: Current session status
        phase: Current deliberation phase
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        last_activity_at: Last activity timestamp (state change, API call, etc.)
        problem_statement: Truncated problem statement
        cost: Total cost so far (if available)
        expert_count: Number of experts consulted (for dashboard cards)
        contribution_count: Total contributions (for dashboard cards)
        task_count: Number of extracted tasks (for dashboard cards)
        focus_area_count: Number of focus areas/sub-problems (for dashboard cards)
    """

    id: str = Field(..., description="Unique session identifier (UUID)")
    status: str = Field(
        ...,
        description="Current session status",
        examples=["active", "completed", "failed", "paused", "created", "deleted"],
    )
    phase: str | None = Field(
        None,
        description="Current deliberation phase",
        examples=["decompose", "discussion", "voting", "synthesis"],
    )
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_activity_at: datetime | None = Field(
        None, description="Last activity timestamp (state change, API call, etc.)"
    )
    problem_statement: str = Field(..., description="Problem statement (truncated for list view)")
    cost: float | None = Field(None, description="Total cost so far (USD)")
    # Summary counts for dashboard cards
    expert_count: int | None = Field(None, description="Number of experts consulted")
    contribution_count: int | None = Field(None, description="Total expert contributions")
    task_count: int | None = Field(None, description="Number of extracted action items")
    focus_area_count: int | None = Field(None, description="Number of focus areas analyzed")


class SessionListResponse(BaseModel):
    """Response model for session list.

    Attributes:
        sessions: List of session summaries
        total: Total number of sessions
        limit: Page size
        offset: Page offset
    """

    sessions: list[SessionResponse] = Field(..., description="List of session summaries")
    total: int = Field(..., description="Total number of sessions")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class SessionDetailResponse(BaseModel):
    """Response model for detailed session information.

    Attributes:
        id: Session identifier
        status: Current status
        phase: Current phase
        created_at: Creation timestamp
        updated_at: Last update timestamp
        problem: Problem details
        state: Full deliberation state (if available)
        metrics: Session metrics (rounds, costs, etc.)
    """

    id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Current status")
    phase: str | None = Field(None, description="Current phase")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    problem: dict[str, Any] = Field(..., description="Problem details")
    state: dict[str, Any] | None = Field(None, description="Full deliberation state")
    metrics: dict[str, Any] | None = Field(None, description="Session metrics")


class ControlResponse(BaseModel):
    """Response model for deliberation control actions.

    Attributes:
        session_id: Session identifier
        action: Action performed
        status: Result status
        message: Human-readable message
    """

    session_id: str = Field(..., description="Session identifier")
    action: str = Field(
        ..., description="Action performed", examples=["start", "pause", "resume", "kill"]
    )
    status: str = Field(..., description="Result status", examples=["success", "failed"])
    message: str = Field(..., description="Human-readable message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "action": "start",
                    "status": "success",
                    "message": "Deliberation started in background",
                },
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "action": "kill",
                    "status": "success",
                    "message": "Deliberation killed. Reason: User requested stop",
                },
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Response model for API errors.

    Attributes:
        error: Error type
        message: Error message
        details: Optional error details
    """

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Optional error details")


# =============================================================================
# Action/Task Models (Kanban)
# =============================================================================


class ActionStatus(str):
    """Action status enum values."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskStatusUpdate(BaseModel):
    """Request model for updating task status.

    Attributes:
        status: New status for the task
    """

    status: str = Field(
        ...,
        description="New task status",
        pattern="^(todo|doing|done)$",
        examples=["todo", "doing", "done"],
    )


class TaskWithStatus(BaseModel):
    """Task with its current status.

    Attributes:
        id: Task identifier
        title: Short task title
        description: Task description
        what_and_how: Steps to complete the task
        success_criteria: How to measure success
        kill_criteria: When to abandon the task
        dependencies: Prerequisites
        timeline: Estimated duration
        priority: Task priority
        category: Task category
        source_section: Where this task came from
        confidence: AI confidence in extraction
        sub_problem_index: Which focus area this belongs to
        status: Current status (todo/doing/done)
    """

    id: str = Field(..., description="Task identifier")
    title: str = Field(..., description="Short task title")
    description: str = Field(..., description="Task description")
    what_and_how: list[str] = Field(default_factory=list, description="Steps to complete")
    success_criteria: list[str] = Field(default_factory=list, description="Success measures")
    kill_criteria: list[str] = Field(default_factory=list, description="Abandonment conditions")
    dependencies: list[str] = Field(default_factory=list, description="Prerequisites")
    timeline: str = Field(..., description="Estimated duration")
    priority: str = Field(..., description="high/medium/low")
    category: str = Field(..., description="implementation/research/decision/communication")
    source_section: str | None = Field(None, description="Source synthesis section")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence")
    sub_problem_index: int | None = Field(None, description="Focus area index")
    status: str = Field(default="todo", description="Current status")


class SessionActionsResponse(BaseModel):
    """Response model for session actions.

    Attributes:
        session_id: Session identifier
        tasks: List of tasks with statuses
        total_tasks: Total task count
        by_status: Count of tasks per status
    """

    session_id: str = Field(..., description="Session identifier")
    tasks: list[TaskWithStatus] = Field(..., description="Tasks with statuses")
    total_tasks: int = Field(..., description="Total task count")
    by_status: dict[str, int] = Field(
        ...,
        description="Tasks grouped by status",
        examples=[{"todo": 3, "doing": 1, "done": 2}],
    )


class AllActionsResponse(BaseModel):
    """Response model for all user actions across sessions.

    Attributes:
        sessions: List of sessions with their tasks
        total_tasks: Total tasks across all sessions
        by_status: Global count per status
    """

    sessions: list[dict[str, Any]] = Field(..., description="Sessions with tasks")
    total_tasks: int = Field(..., description="Total tasks across all sessions")
    by_status: dict[str, int] = Field(..., description="Global status counts")


class ActionDetailResponse(BaseModel):
    """Response model for a single action's full details.

    Attributes:
        id: Action identifier (UUID)
        title: Action title
        description: Full action description
        what_and_how: Steps to complete the action
        success_criteria: Measurable success conditions
        kill_criteria: Conditions to stop/abandon action
        dependencies: Required preconditions
        timeline: Expected timeline
        priority: Priority level (high/medium/low)
        category: Action category
        source_section: Which part of synthesis this came from
        confidence: AI confidence in the action
        sub_problem_index: Which sub-problem this relates to
        status: Current status (todo/in_progress/blocked/in_review/done/cancelled)
        session_id: Parent session ID
        problem_statement: Session's problem statement (decision)
        estimated_duration_days: Duration in business days
        target_start_date: User-set target start date
        target_end_date: User-set target end date
        estimated_start_date: Auto-calculated start date
        estimated_end_date: Auto-calculated end date
        actual_start_date: Actual start timestamp
        actual_end_date: Actual completion timestamp
        blocking_reason: Reason for blocked status
        blocked_at: When action was blocked
        auto_unblock: Auto-unblock when dependencies complete
    """

    id: str = Field(..., description="Action identifier (UUID)")
    title: str = Field(..., description="Action title")
    description: str = Field(..., description="Full action description")
    what_and_how: list[str] = Field(default_factory=list, description="Steps to complete")
    success_criteria: list[str] = Field(default_factory=list, description="Success conditions")
    kill_criteria: list[str] = Field(default_factory=list, description="Stop conditions")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies")
    timeline: str = Field(default="", description="Expected timeline")
    priority: str = Field(default="medium", description="Priority level")
    category: str = Field(default="implementation", description="Action category")
    source_section: str | None = Field(default=None, description="Source section")
    confidence: float = Field(default=0.0, description="AI confidence")
    sub_problem_index: int | None = Field(default=None, description="Sub-problem index")
    status: str = Field(default="todo", description="Current status")
    session_id: str = Field(..., description="Parent session ID")
    problem_statement: str = Field(..., description="Session decision")
    estimated_duration_days: int | None = Field(
        default=None, description="Duration in business days"
    )
    target_start_date: str | None = Field(
        default=None, description="User-set target start date (ISO)"
    )
    target_end_date: str | None = Field(default=None, description="User-set target end date (ISO)")
    estimated_start_date: str | None = Field(
        default=None, description="Auto-calculated start date (ISO)"
    )
    estimated_end_date: str | None = Field(
        default=None, description="Auto-calculated end date (ISO)"
    )
    actual_start_date: str | None = Field(default=None, description="Actual start timestamp (ISO)")
    actual_end_date: str | None = Field(
        default=None, description="Actual completion timestamp (ISO)"
    )
    blocking_reason: str | None = Field(default=None, description="Reason for blocked status")
    blocked_at: str | None = Field(default=None, description="When action was blocked (ISO)")
    auto_unblock: bool = Field(default=False, description="Auto-unblock when dependencies complete")
    # Replanning fields
    replan_session_id: str | None = Field(
        default=None, description="ID of replanning session if one exists"
    )
    replan_requested_at: str | None = Field(
        default=None, description="When replanning was requested (ISO)"
    )
    replanning_reason: str | None = Field(
        default=None, description="User-provided reason for replanning"
    )
    can_replan: bool = Field(
        default=False, description="Whether this action can be replanned (blocked status)"
    )


class ActionCreate(BaseModel):
    """Request model for creating a new action.

    Attributes:
        title: Short action title
        description: Full action description
        what_and_how: Steps to complete
        success_criteria: Success measures
        kill_criteria: Abandonment conditions
        priority: Priority level
        category: Action category
        timeline: Human-readable timeline
        estimated_duration_days: Duration in business days
        target_start_date: User-set target start
        target_end_date: User-set target end
    """

    title: str = Field(..., min_length=1, max_length=500, description="Action title")
    description: str = Field(..., min_length=1, description="Action description")
    what_and_how: list[str] = Field(default_factory=list, description="Steps to complete")
    success_criteria: list[str] = Field(default_factory=list, description="Success measures")
    kill_criteria: list[str] = Field(default_factory=list, description="Abandonment conditions")
    priority: str = Field(
        default="medium", pattern="^(high|medium|low)$", description="Priority level"
    )
    category: str = Field(
        default="implementation",
        pattern="^(implementation|research|decision|communication)$",
        description="Action category",
    )
    timeline: str | None = Field(None, description="Human-readable timeline")
    estimated_duration_days: int | None = Field(None, ge=1, description="Duration in business days")
    target_start_date: str | None = Field(None, description="Target start date (ISO)")
    target_end_date: str | None = Field(None, description="Target end date (ISO)")


class ActionUpdate(BaseModel):
    """Request model for updating an action.

    Attributes:
        title: Updated title
        description: Updated description
        what_and_how: Updated steps
        success_criteria: Updated success measures
        kill_criteria: Updated abandonment conditions
        priority: Updated priority
        category: Updated category
        timeline: Updated timeline
        estimated_duration_days: Updated duration
        target_start_date: Updated target start
        target_end_date: Updated target end
    """

    title: str | None = Field(None, min_length=1, max_length=500, description="Updated title")
    description: str | None = Field(None, min_length=1, description="Updated description")
    what_and_how: list[str] | None = Field(None, description="Updated steps")
    success_criteria: list[str] | None = Field(None, description="Updated success measures")
    kill_criteria: list[str] | None = Field(None, description="Updated abandonment conditions")
    priority: str | None = Field(
        None, pattern="^(high|medium|low)$", description="Updated priority"
    )
    category: str | None = Field(
        None,
        pattern="^(implementation|research|decision|communication)$",
        description="Updated category",
    )
    timeline: str | None = Field(None, description="Updated timeline")
    estimated_duration_days: int | None = Field(None, ge=1, description="Updated duration")
    target_start_date: str | None = Field(None, description="Updated target start (ISO)")
    target_end_date: str | None = Field(None, description="Updated target end (ISO)")


class ActionStatusUpdate(BaseModel):
    """Request model for updating action status.

    Attributes:
        status: New status
        blocking_reason: Reason for blocked status (required if status is 'blocked')
        auto_unblock: Auto-unblock when dependencies complete
    """

    status: str = Field(
        ...,
        pattern="^(todo|in_progress|blocked|in_review|done|cancelled)$",
        description="New status",
    )
    blocking_reason: str | None = Field(None, description="Reason for blocked status")
    auto_unblock: bool = Field(default=False, description="Auto-unblock when dependencies complete")


class ActionDatesUpdate(BaseModel):
    """Request model for updating action dates.

    All fields are optional - only provided fields will be updated.

    Attributes:
        target_start_date: User-set target start date (YYYY-MM-DD)
        target_end_date: User-set target end date (YYYY-MM-DD)
        timeline: Human-readable timeline (e.g., "2 weeks")
    """

    target_start_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Target start date (YYYY-MM-DD)",
    )
    target_end_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Target end date (YYYY-MM-DD)",
    )
    timeline: str | None = Field(
        None,
        max_length=100,
        description="Human-readable timeline (e.g., '2 weeks')",
    )


class ActionDatesResponse(BaseModel):
    """Response model for action dates update.

    Attributes:
        action_id: Action UUID
        target_start_date: Updated target start date
        target_end_date: Updated target end date
        estimated_start_date: Calculated estimated start date
        estimated_end_date: Calculated estimated end date
        estimated_duration_days: Duration in business days
        cascade_updated: Number of dependent actions updated
    """

    action_id: str
    target_start_date: str | None
    target_end_date: str | None
    estimated_start_date: str | None
    estimated_end_date: str | None
    estimated_duration_days: int | None
    cascade_updated: int = Field(description="Number of dependent actions updated")


class ActionResponse(BaseModel):
    """Response model for a single action (summary view).

    Attributes:
        id: Action UUID
        title: Action title
        status: Current status
        priority: Priority level
        category: Action category
        timeline: Human-readable timeline
        estimated_duration_days: Duration in business days
        target_start_date: Target start date
        estimated_start_date: Calculated start date
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(..., description="Action UUID")
    title: str = Field(..., description="Action title")
    status: str = Field(..., description="Current status")
    priority: str = Field(..., description="Priority level")
    category: str = Field(..., description="Action category")
    timeline: str | None = Field(None, description="Human-readable timeline")
    estimated_duration_days: int | None = Field(None, description="Duration in business days")
    target_start_date: str | None = Field(None, description="Target start date (ISO)")
    estimated_start_date: str | None = Field(None, description="Calculated start date (ISO)")
    created_at: str = Field(..., description="Creation timestamp (ISO)")
    updated_at: str = Field(..., description="Last update timestamp (ISO)")


# =============================================================================
# Dependency Models
# =============================================================================


class DependencyCreate(BaseModel):
    """Request model for creating a dependency.

    Attributes:
        depends_on_action_id: UUID of the action this depends on
        dependency_type: Type of dependency relationship
        lag_days: Days of buffer between dependency completion and action start
    """

    depends_on_action_id: str = Field(..., description="UUID of the action this depends on")
    dependency_type: str = Field(
        default="finish_to_start",
        pattern="^(finish_to_start|start_to_start|finish_to_finish)$",
        description="Type of dependency relationship",
    )
    lag_days: int = Field(default=0, ge=-30, le=365, description="Days of buffer/lag")


class DependencyResponse(BaseModel):
    """Response model for a dependency.

    Attributes:
        action_id: UUID of the action with the dependency
        depends_on_action_id: UUID of the action being depended on
        depends_on_title: Title of the depended-on action
        depends_on_status: Status of the depended-on action
        dependency_type: Type of dependency
        lag_days: Buffer days
        created_at: When dependency was created
    """

    action_id: str = Field(..., description="UUID of the action with the dependency")
    depends_on_action_id: str = Field(..., description="UUID of the action being depended on")
    depends_on_title: str = Field(..., description="Title of the depended-on action")
    depends_on_status: str = Field(..., description="Status of the depended-on action")
    dependency_type: str = Field(..., description="Type of dependency")
    lag_days: int = Field(..., description="Buffer days")
    created_at: str = Field(..., description="When dependency was created (ISO)")


class DependencyListResponse(BaseModel):
    """Response model for listing dependencies.

    Attributes:
        action_id: UUID of the action
        dependencies: List of dependencies
        has_incomplete: Whether there are incomplete dependencies
    """

    action_id: str = Field(..., description="UUID of the action")
    dependencies: list[DependencyResponse] = Field(..., description="List of dependencies")
    has_incomplete: bool = Field(..., description="Whether there are incomplete dependencies")


class BlockActionRequest(BaseModel):
    """Request model for blocking an action.

    Attributes:
        blocking_reason: Why the action is blocked
        auto_unblock: Whether to auto-unblock when dependencies complete
    """

    blocking_reason: str = Field(
        ..., min_length=1, max_length=500, description="Why the action is blocked"
    )
    auto_unblock: bool = Field(default=False, description="Auto-unblock when dependencies complete")


class UnblockActionRequest(BaseModel):
    """Request model for unblocking an action.

    Attributes:
        target_status: Status to transition to after unblocking
    """

    target_status: str = Field(
        default="todo",
        pattern="^(todo|in_progress)$",
        description="Status to transition to",
    )


class ReplanRequest(BaseModel):
    """Request model for requesting AI replanning of a blocked action.

    Attributes:
        additional_context: Optional user-provided context about why replanning is needed
    """

    additional_context: str | None = Field(
        None,
        max_length=5000,
        description="Additional context about why replanning is needed",
    )


class ReplanResponse(BaseModel):
    """Response model for replan request.

    Attributes:
        session_id: ID of the newly created replanning session
        action_id: ID of the original blocked action
        message: Success/info message
        redirect_url: URL to redirect to for the meeting
        is_existing: Whether this is an existing replanning session
    """

    session_id: str = Field(..., description="Replanning session ID")
    action_id: str = Field(..., description="Original action ID")
    message: str = Field(..., description="Success/info message")
    redirect_url: str = Field(..., description="URL to redirect to")
    is_existing: bool = Field(
        default=False, description="Whether this is an existing replanning session"
    )


# =============================================================================
# Project Models
# =============================================================================


class ProjectCreate(BaseModel):
    """Request model for creating a project.

    Attributes:
        name: Project name
        description: Project description
        target_start_date: Target start date (YYYY-MM-DD)
        target_end_date: Target end date (YYYY-MM-DD)
        color: Hex color for visualization
        icon: Emoji or icon name
    """

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, max_length=5000, description="Project description")
    target_start_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Target start date (YYYY-MM-DD)",
    )
    target_end_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Target end date (YYYY-MM-DD)",
    )
    color: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color (e.g., #3B82F6)",
    )
    icon: str | None = Field(None, max_length=50, description="Emoji or icon name")


class ProjectUpdate(BaseModel):
    """Request model for updating a project.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: Project name
        description: Project description
        target_start_date: Target start date (YYYY-MM-DD)
        target_end_date: Target end date (YYYY-MM-DD)
        color: Hex color for visualization
        icon: Emoji or icon name
    """

    name: str | None = Field(None, min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, max_length=5000, description="Project description")
    target_start_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Target start date (YYYY-MM-DD)",
    )
    target_end_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Target end date (YYYY-MM-DD)",
    )
    color: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color (e.g., #3B82F6)",
    )
    icon: str | None = Field(None, max_length=50, description="Emoji or icon name")


class ProjectStatusUpdate(BaseModel):
    """Request model for updating project status.

    Attributes:
        status: New status (active, paused, completed, archived)
    """

    status: str = Field(
        ...,
        pattern="^(active|paused|completed|archived)$",
        description="New status",
    )


class ProjectDetailResponse(BaseModel):
    """Response model for project details.

    Attributes:
        id: Project UUID
        user_id: Owner user ID
        name: Project name
        description: Project description
        status: Current status
        target_start_date: Target start date (ISO)
        target_end_date: Target end date (ISO)
        estimated_start_date: Calculated start date (ISO)
        estimated_end_date: Calculated end date (ISO)
        actual_start_date: Actual start timestamp (ISO)
        actual_end_date: Actual completion timestamp (ISO)
        progress_percent: Progress percentage (0-100)
        total_actions: Total number of actions
        completed_actions: Number of completed actions
        color: Hex color for visualization
        icon: Emoji or icon name
        created_at: Creation timestamp (ISO)
        updated_at: Last update timestamp (ISO)
    """

    id: str = Field(..., description="Project UUID")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Project description")
    status: str = Field(..., description="Current status")
    target_start_date: str | None = Field(None, description="Target start date (ISO)")
    target_end_date: str | None = Field(None, description="Target end date (ISO)")
    estimated_start_date: str | None = Field(None, description="Calculated start date (ISO)")
    estimated_end_date: str | None = Field(None, description="Calculated end date (ISO)")
    actual_start_date: str | None = Field(None, description="Actual start timestamp (ISO)")
    actual_end_date: str | None = Field(None, description="Actual completion timestamp (ISO)")
    progress_percent: int = Field(default=0, description="Progress percentage (0-100)")
    total_actions: int = Field(default=0, description="Total number of actions")
    completed_actions: int = Field(default=0, description="Number of completed actions")
    color: str | None = Field(None, description="Hex color for visualization")
    icon: str | None = Field(None, description="Emoji or icon name")
    created_at: str | None = Field(None, description="Creation timestamp (ISO)")
    updated_at: str | None = Field(None, description="Last update timestamp (ISO)")


class ProjectListResponse(BaseModel):
    """Response model for listing projects.

    Attributes:
        projects: List of projects
        total: Total count
        page: Current page
        per_page: Items per page
    """

    projects: list[ProjectDetailResponse] = Field(..., description="List of projects")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")


class ProjectActionSummary(BaseModel):
    """Summary of an action within a project.

    Attributes:
        id: Action UUID
        session_id: Session UUID the action belongs to
        title: Action title
        description: Action description
        status: Current status
        priority: Priority level
        category: Action category
        timeline: Human-readable timeline
        estimated_duration_days: Duration in business days
        estimated_start_date: Calculated start date (ISO)
        estimated_end_date: Calculated end date (ISO)
        blocking_reason: Why action is blocked (if applicable)
    """

    id: str = Field(..., description="Action UUID")
    session_id: str = Field(default="", description="Session UUID the action belongs to")
    title: str = Field(..., description="Action title")
    description: str = Field(default="", description="Action description")
    status: str = Field(..., description="Current status")
    priority: str = Field(default="medium", description="Priority level")
    category: str = Field(default="implementation", description="Action category")
    timeline: str | None = Field(None, description="Human-readable timeline")
    estimated_duration_days: int | None = Field(None, description="Duration in business days")
    estimated_start_date: str | None = Field(None, description="Calculated start date (ISO)")
    estimated_end_date: str | None = Field(None, description="Calculated end date (ISO)")
    blocking_reason: str | None = Field(None, description="Why action is blocked")


class ProjectActionsResponse(BaseModel):
    """Response model for listing project actions.

    Attributes:
        actions: List of actions
        total: Total count
        page: Current page
        per_page: Items per page
    """

    actions: list[ProjectActionSummary] = Field(..., description="List of actions")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")


class ProjectActionAssignment(BaseModel):
    """Request model for assigning an action to a project.

    Attributes:
        action_id: Action UUID to assign
    """

    action_id: str = Field(..., description="Action UUID to assign")


class ProjectSessionLink(BaseModel):
    """Request model for linking a session to a project.

    Attributes:
        session_id: Session ID to link
        relationship: Type of relationship
    """

    session_id: str = Field(..., description="Session ID to link")
    relationship: str = Field(
        default="discusses",
        pattern="^(discusses|created_from|replanning)$",
        description="Type of relationship",
    )


class GanttActionData(BaseModel):
    """Action data for Gantt chart (frappe-gantt format).

    Attributes:
        id: Action UUID
        name: Action name/title
        start: Start date (ISO)
        end: End date (ISO)
        progress: Progress percentage (0-100)
        dependencies: Comma-separated list of dependency IDs
        status: Current status
        priority: Priority level
        session_id: Source session ID
    """

    id: str = Field(..., description="Action UUID")
    name: str = Field(..., description="Action name/title")
    start: str = Field(..., description="Start date (ISO)")
    end: str = Field(..., description="End date (ISO)")
    progress: int = Field(0, description="Progress percentage (0-100)")
    dependencies: str = Field("", description="Comma-separated dependency IDs")
    status: str = Field(..., description="Current status")
    priority: str = Field(..., description="Priority level")
    session_id: str = Field("", description="Source session ID")


class GanttDependency(BaseModel):
    """Dependency data for Gantt chart.

    Attributes:
        from_: Source action UUID
        to: Target action UUID
        type: Dependency type
        lag_days: Buffer days
    """

    from_: str = Field(..., alias="from", description="Source action UUID")
    to: str = Field(..., description="Target action UUID")
    type: str = Field(..., description="Dependency type")
    lag_days: int = Field(..., description="Buffer days")

    model_config = {"populate_by_name": True}


class GanttProjectData(BaseModel):
    """Project summary for Gantt chart.

    Attributes:
        id: Project UUID
        name: Project name
        status: Current status
        estimated_start_date: Start date (ISO)
        estimated_end_date: End date (ISO)
        progress_percent: Progress percentage
        color: Hex color
    """

    id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    status: str = Field(..., description="Current status")
    estimated_start_date: str | None = Field(None, description="Start date (ISO)")
    estimated_end_date: str | None = Field(None, description="End date (ISO)")
    progress_percent: int = Field(default=0, description="Progress percentage")
    color: str | None = Field(None, description="Hex color")


class GanttResponse(BaseModel):
    """Response model for Gantt chart data.

    Attributes:
        project: Project summary
        actions: List of actions
        dependencies: List of dependencies
    """

    project: GanttProjectData = Field(..., description="Project summary")
    actions: list[GanttActionData] = Field(..., description="List of actions")
    dependencies: list[GanttDependency] = Field(..., description="List of dependencies")


# =============================================================================
# Action Update Models (Phase 5)
# =============================================================================


class ActionUpdateCreate(BaseModel):
    """Request model for creating an action update.

    Attributes:
        update_type: Type of update (progress, blocker, note)
        content: Update content/message
        progress_percent: Progress percentage (0-100) for progress updates
    """

    update_type: str = Field(
        ...,
        pattern="^(progress|blocker|note)$",
        description="Type of update",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Update content/message",
    )
    progress_percent: int | None = Field(
        None,
        ge=0,
        le=100,
        description="Progress percentage (0-100) for progress updates",
    )


class ActionUpdateResponse(BaseModel):
    """Response model for a single action update.

    Attributes:
        id: Update ID
        action_id: Parent action UUID
        user_id: User who created the update
        update_type: Type of update
        content: Update content
        old_status: Previous status (for status_change)
        new_status: New status (for status_change)
        old_date: Previous date (for date_change)
        new_date: New date (for date_change)
        date_field: Which date changed (for date_change)
        progress_percent: Progress percentage (for progress updates)
        created_at: When update was created
    """

    id: int = Field(..., description="Update ID")
    action_id: str = Field(..., description="Parent action UUID")
    user_id: str = Field(..., description="User who created the update")
    update_type: str = Field(..., description="Type of update")
    content: str | None = Field(None, description="Update content")
    old_status: str | None = Field(None, description="Previous status")
    new_status: str | None = Field(None, description="New status")
    old_date: str | None = Field(None, description="Previous date (ISO)")
    new_date: str | None = Field(None, description="New date (ISO)")
    date_field: str | None = Field(None, description="Which date changed")
    progress_percent: int | None = Field(None, description="Progress percentage")
    created_at: str = Field(..., description="When update was created (ISO)")


class ActionUpdatesResponse(BaseModel):
    """Response model for listing action updates.

    Attributes:
        action_id: Action UUID
        updates: List of updates
        total: Total number of updates
    """

    action_id: str = Field(..., description="Action UUID")
    updates: list[ActionUpdateResponse] = Field(..., description="List of updates")
    total: int = Field(..., description="Total number of updates")


# =============================================================================
# Tag Models
# =============================================================================


class TagCreate(BaseModel):
    """Request model for creating a tag.

    Attributes:
        name: Tag name (unique per user)
        color: Hex color code (e.g., #6366F1)
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tag name (unique per user)",
    )
    color: str = Field(
        default="#6366F1",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code",
    )


class TagUpdate(BaseModel):
    """Request model for updating a tag.

    Attributes:
        name: New name (optional)
        color: New color (optional)
    """

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="New name",
    )
    color: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="New color",
    )


class TagResponse(BaseModel):
    """Response model for a tag.

    Attributes:
        id: Tag UUID
        user_id: Owner user ID
        name: Tag name
        color: Hex color code
        action_count: Number of actions with this tag
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(..., description="Tag UUID")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Tag name")
    color: str = Field(..., description="Hex color code")
    action_count: int = Field(default=0, description="Number of actions with this tag")
    created_at: str = Field(..., description="Creation timestamp (ISO)")
    updated_at: str = Field(..., description="Last update timestamp (ISO)")


class TagListResponse(BaseModel):
    """Response model for listing tags.

    Attributes:
        tags: List of tags
        total: Total count
    """

    tags: list[TagResponse] = Field(..., description="List of tags")
    total: int = Field(..., description="Total count")


class ActionTagsUpdate(BaseModel):
    """Request model for updating action tags.

    Attributes:
        tag_ids: List of tag UUIDs to set on the action
    """

    tag_ids: list[str] = Field(..., description="List of tag UUIDs")


class GlobalGanttResponse(BaseModel):
    """Response model for global Gantt chart data (all actions).

    Attributes:
        actions: List of actions with date data
        dependencies: List of dependencies
    """

    actions: list[GanttActionData] = Field(..., description="List of actions")
    dependencies: list[GanttDependency] = Field(..., description="List of dependencies")
