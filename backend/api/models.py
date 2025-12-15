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
    dataset_id: str | None = Field(
        None,
        description="Optional dataset UUID to attach for data-driven deliberations",
    )
    workspace_id: str | None = Field(
        None,
        description="Optional workspace UUID to scope the session to a team workspace",
    )
    context_ids: dict[str, list[str]] | None = Field(
        None,
        description="Optional context to inject: {meetings: [...ids], actions: [...ids], datasets: [...ids]}",
        examples=[{"meetings": ["bo1_abc123"], "actions": ["uuid-1"], "datasets": ["uuid-2"]}],
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

        # Check for basic SQL injection patterns
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

        # Check for advanced SQL injection patterns (EXEC, xp_cmdshell, etc.)
        from bo1.prompts.sanitizer import detect_sql_injection

        sql_detection = detect_sql_injection(v)
        if sql_detection:
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
        promo_credits_remaining: Remaining promo credits after session creation (if used promo)
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
    # Stale insights warning (only on creation)
    stale_insights: list[dict[str, Any]] | None = Field(
        None,
        description="List of stale insights (>30 days old) for user warning during creation",
    )
    # Stale metrics warning (only on creation)
    stale_metrics: list[dict[str, Any]] | None = Field(
        None,
        description="List of stale business metrics requiring refresh before meeting",
    )
    # Promo credits (returned on session creation when promo was used)
    promo_credits_remaining: int | None = Field(
        None,
        description="Remaining promo credits after this session (if session used promo credit)",
    )


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
        detail: Error message (FastAPI HTTPException format)
        error_code: Optional structured error code for client handling
        session_id: Optional session ID for context
        status: Optional status field for conflict errors
    """

    detail: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Structured error code for client handling")
    session_id: str | None = Field(None, description="Session ID for context")
    status: str | None = Field(None, description="Session status (for conflict errors)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Session not found",
                    "session_id": "bo1_abc123",
                },
                {
                    "detail": "Not authorized to access this session",
                    "error_code": "FORBIDDEN",
                },
                {
                    "detail": "Session already completed",
                    "status": "completed",
                    "session_id": "bo1_abc123",
                    "error_code": "SESSION_ALREADY_COMPLETED",
                },
                {
                    "detail": "Internal server error",
                    "error_code": "GRAPH_EXECUTION_FAILED",
                },
            ]
        }
    }


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
    # Cancellation fields
    cancellation_reason: str | None = Field(
        default=None, description="Reason for cancellation (what went wrong)"
    )
    cancelled_at: str | None = Field(default=None, description="When action was cancelled (ISO)")
    # Project assignment
    project_id: str | None = Field(default=None, description="Assigned project ID (UUID)")
    # Progress tracking
    progress_type: str = Field(
        default="status_only", description="Progress tracking type: percentage, points, status_only"
    )
    progress_value: int | None = Field(
        default=None, ge=0, description="Progress value: 0-100 for %, 0+ for points"
    )
    estimated_effort_points: int | None = Field(
        default=None, ge=1, description="Estimated effort in story points"
    )
    scheduled_start_date: str | None = Field(
        default=None, description="Original planned start date (ISO)"
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
        cancellation_reason: Reason for cancelled status (required if status is 'cancelled')
        failure_reason_category: Category of failure (blocker/scope_creep/dependency/unknown)
        replan_suggested_at: Timestamp when replanning suggestion was shown
    """

    status: str = Field(
        ...,
        pattern="^(todo|in_progress|blocked|in_review|done|cancelled)$",
        description="New status",
    )
    blocking_reason: str | None = Field(None, description="Reason for blocked status")
    auto_unblock: bool = Field(default=False, description="Auto-unblock when dependencies complete")
    cancellation_reason: str | None = Field(None, description="Reason for cancelled status")
    failure_reason_category: str | None = Field(
        None,
        pattern="^(blocker|scope_creep|dependency|unknown)$",
        description="Category of failure reason",
    )
    replan_suggested_at: datetime | None = Field(
        None, description="When replanning suggestion was shown"
    )


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


class ActionProgressUpdate(BaseModel):
    """Request model for updating action progress.

    Attributes:
        progress_type: Type of progress tracking (percentage, points, status_only)
        progress_value: Progress value (0-100 for %, 0+ for points)
        actual_start_date: When work actually began (ISO format)
        actual_finish_date: When work completed (ISO format)
        estimated_effort_points: Estimated effort in story points
    """

    progress_type: str = Field(
        ...,
        pattern="^(percentage|points|status_only)$",
        description="Progress tracking type",
    )
    progress_value: int | None = Field(
        None, ge=0, description="Progress value (0-100 for %, 0+ for points)"
    )
    actual_start_date: str | None = Field(None, description="Actual start date (ISO format)")
    actual_finish_date: str | None = Field(None, description="Actual finish date (ISO format)")
    estimated_effort_points: int | None = Field(None, ge=1, description="Estimated effort points")


class ActionVariance(BaseModel):
    """Response model for action schedule variance analysis.

    Attributes:
        action_id: Action UUID
        planned_duration_days: Difference between scheduled_start and target_end
        actual_duration_days: Difference between actual_start and actual_finish
        variance_days: Difference between planned and actual duration
        risk_level: Risk status (EARLY, ON_TIME, LATE)
        progress_percent: Current progress percentage (if tracked)
    """

    action_id: str = Field(..., description="Action UUID")
    planned_duration_days: int | None = Field(None, description="Planned duration (days)")
    actual_duration_days: int | None = Field(None, description="Actual duration (days)")
    variance_days: int | None = Field(None, description="Variance from plan (days)")
    risk_level: str = Field(
        default="ON_TIME",
        pattern="^(EARLY|ON_TIME|LATE)$",
        description="Schedule risk status",
    )
    progress_percent: int | None = Field(None, ge=0, le=100, description="Progress as percentage")


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
        status_color: Hex color for status (Gantt coloring)
        priority_color: Hex color for priority (Gantt coloring)
        project_color: Hex color for project (Gantt coloring)
        progress_type: Progress tracking type
        progress_value: Current progress value
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
    status_color: str | None = Field(None, description="Hex color for status")
    priority_color: str | None = Field(None, description="Hex color for priority")
    project_color: str | None = Field(None, description="Hex color for project")
    progress_type: str = Field(default="status_only", description="Progress tracking type")
    progress_value: int | None = Field(None, ge=0, description="Current progress value")


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
        version: Project version number (1, 2, 3, etc)
        source_project_id: ID of source project if versioned from another
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
    version: int = Field(default=1, description="Project version number")
    source_project_id: str | None = Field(None, description="Source project ID if versioned")
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


class CreateProjectMeetingRequest(BaseModel):
    """Request model for creating a meeting from a project.

    Attributes:
        problem_statement: Optional problem statement (if not provided, defaults to project-focused)
        include_project_context: Whether to include project info in context
    """

    problem_statement: str | None = Field(
        None,
        min_length=10,
        max_length=10000,
        description="Problem statement for the meeting (optional - defaults to project delivery focus)",
    )
    include_project_context: bool = Field(
        True,
        description="Include project description and actions in meeting context",
    )


# Session-Project linking (from session perspective)
class SessionProjectLink(BaseModel):
    """Request model for linking projects to a session.

    Attributes:
        project_ids: List of project UUIDs to link
        relationship: Type of relationship for all links
    """

    project_ids: list[str] = Field(..., description="List of project UUIDs to link")
    relationship: str = Field(
        default="discusses",
        pattern="^(discusses|created_from|replanning)$",
        description="Type of relationship",
    )


class SessionProjectResponse(BaseModel):
    """Response model for a linked project.

    Attributes:
        project_id: Project UUID
        name: Project name
        description: Project description
        status: Project status
        progress_percent: Project progress
        relationship: Link relationship type
        linked_at: When the link was created
    """

    project_id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Project description")
    status: str = Field(..., description="Project status")
    progress_percent: int = Field(0, description="Project progress (0-100)")
    relationship: str = Field(..., description="Link relationship type")
    linked_at: str | None = Field(None, description="When the link was created")


class SessionProjectsResponse(BaseModel):
    """Response model for session's linked projects.

    Attributes:
        session_id: Session identifier
        projects: List of linked projects
    """

    session_id: str = Field(..., description="Session identifier")
    projects: list[SessionProjectResponse] = Field(
        default_factory=list, description="List of linked projects"
    )


class AvailableProjectResponse(BaseModel):
    """Response model for a project available for linking.

    Attributes:
        id: Project UUID
        name: Project name
        description: Project description
        status: Project status
        progress_percent: Project progress
        is_linked: Whether already linked to this session
    """

    id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Project description")
    status: str = Field(..., description="Project status")
    progress_percent: int = Field(0, description="Project progress (0-100)")
    is_linked: bool = Field(False, description="Whether already linked to this session")


class AvailableProjectsResponse(BaseModel):
    """Response model for projects available for linking to a session.

    Attributes:
        session_id: Session identifier
        projects: List of available projects
    """

    session_id: str = Field(..., description="Session identifier")
    projects: list[AvailableProjectResponse] = Field(
        default_factory=list, description="List of available projects"
    )


# =========================================================================
# Project Autogeneration Models
# =========================================================================


class AutogenSuggestion(BaseModel):
    """A suggested project from action clustering.

    Attributes:
        id: Unique identifier for this suggestion
        name: Suggested project name
        description: Suggested project description
        action_ids: List of action UUIDs for this project
        confidence: Confidence score (0.0-1.0)
        rationale: Why these actions form a coherent project
    """

    id: str = Field(..., description="Suggestion identifier")
    name: str = Field(..., description="Suggested project name")
    description: str = Field("", description="Suggested project description")
    action_ids: list[str] = Field(default_factory=list, description="Action UUIDs")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    rationale: str = Field("", description="Rationale for grouping")


class AutogenSuggestionsResponse(BaseModel):
    """Response model for autogenerate suggestions.

    Attributes:
        suggestions: List of project suggestions
        unassigned_count: Total unassigned actions count
        min_required: Minimum actions required for autogen
    """

    suggestions: list[AutogenSuggestion] = Field(
        default_factory=list, description="List of project suggestions"
    )
    unassigned_count: int = Field(0, description="Total unassigned actions")
    min_required: int = Field(3, description="Minimum actions for autogen")


class AutogenCreateRequest(BaseModel):
    """Request model for creating projects from suggestions.

    Attributes:
        suggestions: List of suggestions to create
        workspace_id: Optional workspace for created projects
    """

    suggestions: list[AutogenSuggestion] = Field(
        ..., description="Suggestions to create as projects"
    )
    workspace_id: str | None = Field(None, description="Workspace for projects")


class AutogenCreateResponse(BaseModel):
    """Response model for created projects from autogen.

    Attributes:
        created_projects: List of created project details
        count: Number of projects created
    """

    created_projects: list["ProjectDetailResponse"] = Field(
        default_factory=list, description="Created projects"
    )
    count: int = Field(0, description="Number of projects created")


# =========================================================================
# Context-Based Project Suggestions
# =========================================================================


class ContextProjectSuggestion(BaseModel):
    """A suggested project derived from business context.

    Attributes:
        id: Unique identifier for this suggestion
        name: Suggested project name
        description: Project description
        rationale: Why this project aligns with user's priorities
        category: Project category (strategy/growth/operations/product/marketing/finance)
        priority: Suggested priority (high/medium/low)
    """

    id: str = Field(..., description="Suggestion identifier")
    name: str = Field(..., description="Suggested project name")
    description: str = Field("", description="Project description")
    rationale: str = Field("", description="Why this aligns with priorities")
    category: str = Field("strategy", description="Project category")
    priority: str = Field("medium", description="Suggested priority")


class ContextSuggestionsResponse(BaseModel):
    """Response model for context-based project suggestions.

    Attributes:
        suggestions: List of project suggestions
        context_completeness: How complete the user's context is (0.0-1.0)
        has_minimum_context: Whether minimum context is available
        missing_fields: Fields that would improve suggestions
    """

    suggestions: list[ContextProjectSuggestion] = Field(
        default_factory=list, description="List of project suggestions"
    )
    context_completeness: float = Field(0.0, description="Context completeness score")
    has_minimum_context: bool = Field(False, description="Has minimum required context")
    missing_fields: list[str] = Field(
        default_factory=list, description="Fields that would improve suggestions"
    )


class ContextCreateRequest(BaseModel):
    """Request model for creating projects from context suggestions.

    Attributes:
        suggestions: List of suggestions to create
        workspace_id: Optional workspace for created projects
    """

    suggestions: list[ContextProjectSuggestion] = Field(
        ..., description="Suggestions to create as projects"
    )
    workspace_id: str | None = Field(None, description="Workspace for projects")


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
        status_color: Hex color for status (Gantt coloring)
        priority_color: Hex color for priority (Gantt coloring)
        project_color: Hex color for project (Gantt coloring)
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
    status_color: str | None = Field(None, description="Hex color for status")
    priority_color: str | None = Field(None, description="Hex color for priority")
    project_color: str | None = Field(None, description="Hex color for project")


class GanttDependency(BaseModel):
    """Dependency data for Gantt chart.

    Attributes:
        action_id: Source action UUID
        depends_on_id: Target action UUID
        dependency_type: Dependency type
        lag_days: Buffer days
    """

    action_id: str = Field(..., description="Source action UUID")
    depends_on_id: str = Field(..., description="Target action UUID")
    dependency_type: str = Field(..., description="Dependency type")
    lag_days: int = Field(..., description="Buffer days")


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


# =============================================================================
# Action Stats Models (Dashboard Progress Visualization)
# =============================================================================


class DailyActionStat(BaseModel):
    """Daily activity statistics for dashboard heatmap.

    Attributes:
        date: Date (YYYY-MM-DD)
        completed_count: Actions completed on this date
        in_progress_count: Actions started (transitioned to in_progress) on this date
        sessions_run: Sessions run on this date
        mentor_sessions: Mentor chat sessions on this date
        estimated_starts: Future actions with start_date on this date (not yet started)
        estimated_completions: Future actions with due_date on this date (not yet completed)
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    completed_count: int = Field(default=0, description="Actions completed")
    in_progress_count: int = Field(default=0, description="Actions started (in_progress)")
    sessions_run: int = Field(default=0, description="Sessions run (started)")
    mentor_sessions: int = Field(default=0, description="Mentor chat sessions")
    estimated_starts: int = Field(default=0, description="Future planned starts (start_date)")
    estimated_completions: int = Field(default=0, description="Future due dates (due_date)")


class ActionStatsTotals(BaseModel):
    """Total action counts by status.

    Attributes:
        completed: Total completed actions
        in_progress: Total in-progress actions
        todo: Total todo actions
    """

    completed: int = Field(default=0, description="Total completed")
    in_progress: int = Field(default=0, description="Total in progress")
    todo: int = Field(default=0, description="Total to do")


class ActionStatsResponse(BaseModel):
    """Response model for action statistics.

    Attributes:
        daily: Daily action stats for last N days
        totals: Total counts by status
    """

    daily: list[DailyActionStat] = Field(..., description="Daily stats")
    totals: ActionStatsTotals = Field(..., description="Total counts")


# =============================================================================
# Action Reminder Models
# =============================================================================


class ActionReminderResponse(BaseModel):
    """Response model for a pending action reminder.

    Attributes:
        action_id: Action UUID
        action_title: Action title
        reminder_type: Type of reminder (start_overdue, deadline_approaching)
        due_date: Relevant date (start date or deadline)
        days_overdue: Days past start date (for start_overdue type)
        days_until_deadline: Days until deadline (for deadline_approaching type)
        session_id: Source meeting ID
        problem_statement: Meeting context
    """

    action_id: str = Field(..., description="Action UUID")
    action_title: str = Field(..., description="Action title")
    reminder_type: str = Field(
        ...,
        description="Reminder type: start_overdue or deadline_approaching",
        pattern="^(start_overdue|deadline_approaching)$",
    )
    due_date: str | None = Field(None, description="Relevant date as ISO string")
    days_overdue: int | None = Field(None, description="Days past start date")
    days_until_deadline: int | None = Field(None, description="Days until deadline")
    session_id: str = Field(..., description="Source meeting ID")
    problem_statement: str = Field(default="", description="Meeting context")


class ActionRemindersResponse(BaseModel):
    """Response model for list of pending reminders.

    Attributes:
        reminders: List of pending reminders
        total: Total count
    """

    reminders: list[ActionReminderResponse] = Field(..., description="Pending reminders")
    total: int = Field(..., description="Total reminder count")


class ReminderSettingsResponse(BaseModel):
    """Response model for action reminder settings.

    Attributes:
        action_id: Action UUID
        reminders_enabled: Whether reminders are enabled
        reminder_frequency_days: Days between reminders
        snoozed_until: Reminder snoozed until this time
        last_reminder_sent_at: When last reminder was sent
    """

    action_id: str = Field(..., description="Action UUID")
    reminders_enabled: bool = Field(..., description="Reminders enabled")
    reminder_frequency_days: int = Field(..., description="Days between reminders")
    snoozed_until: str | None = Field(None, description="Snoozed until ISO datetime")
    last_reminder_sent_at: str | None = Field(None, description="Last sent ISO datetime")


class ReminderSettingsUpdate(BaseModel):
    """Request model for updating reminder settings.

    Attributes:
        reminders_enabled: Enable/disable reminders
        reminder_frequency_days: Days between reminders (1-14)
    """

    reminders_enabled: bool | None = Field(None, description="Enable/disable reminders")
    reminder_frequency_days: int | None = Field(
        None,
        ge=1,
        le=14,
        description="Days between reminders (1-14)",
    )


class SnoozeReminderRequest(BaseModel):
    """Request model for snoozing a reminder.

    Attributes:
        snooze_days: Days to snooze (1-14)
    """

    snooze_days: int = Field(
        default=1,
        ge=1,
        le=14,
        description="Days to snooze reminders (1-14)",
    )


class UserReminderPreferences(BaseModel):
    """Response model for user reminder preferences.

    Attributes:
        default_reminder_frequency_days: Default frequency for new actions
    """

    default_reminder_frequency_days: int = Field(
        ...,
        description="Default reminder frequency in days",
    )


class UserReminderPreferencesUpdate(BaseModel):
    """Request model for updating user reminder preferences.

    Attributes:
        default_reminder_frequency_days: Default frequency for new actions (1-14)
    """

    default_reminder_frequency_days: int = Field(
        ...,
        ge=1,
        le=14,
        description="Default reminder frequency in days (1-14)",
    )


# =============================================================================
# Dataset Models (Data Analysis Platform)
# =============================================================================


class SourceType(str):
    """Dataset source type enum values."""

    CSV = "csv"
    SHEETS = "sheets"
    API = "api"


class DatasetCreate(BaseModel):
    """Request model for creating a dataset.

    Attributes:
        name: Dataset name
        description: Optional description
        source_type: Source type (csv, sheets, api)
        source_uri: Original source location (e.g., Google Sheets URL)
    """

    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: str | None = Field(None, max_length=5000, description="Dataset description")
    source_type: str = Field(
        default="csv",
        pattern="^(csv|sheets|api)$",
        description="Source type",
    )
    source_uri: str | None = Field(None, description="Original source location")


class DatasetProfileResponse(BaseModel):
    """Response model for a dataset column profile.

    Attributes:
        id: Profile UUID
        column_name: Column name
        data_type: Inferred data type
        null_count: Count of null values
        unique_count: Count of unique values
        min_value: Minimum value
        max_value: Maximum value
        mean_value: Mean value (numeric columns)
        sample_values: Sample values list
    """

    id: str = Field(..., description="Profile UUID")
    column_name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Inferred data type")
    null_count: int | None = Field(None, description="Null value count")
    unique_count: int | None = Field(None, description="Unique value count")
    min_value: str | None = Field(None, description="Minimum value")
    max_value: str | None = Field(None, description="Maximum value")
    mean_value: float | None = Field(None, description="Mean value")
    sample_values: list[Any] | None = Field(None, description="Sample values")


class DatasetResponse(BaseModel):
    """Response model for a dataset.

    Attributes:
        id: Dataset UUID
        user_id: Owner user ID
        name: Dataset name
        description: Dataset description
        source_type: Source type
        source_uri: Original source location
        file_key: Spaces object key
        storage_path: Storage prefix path (e.g., user_id)
        row_count: Number of rows
        column_count: Number of columns
        file_size_bytes: File size in bytes
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(..., description="Dataset UUID")
    user_id: str = Field(..., description="Owner user ID")
    name: str = Field(..., description="Dataset name")
    description: str | None = Field(None, description="Dataset description")
    source_type: str = Field(..., description="Source type")
    source_uri: str | None = Field(None, description="Original source location")
    file_key: str | None = Field(None, description="Spaces object key")
    storage_path: str | None = Field(None, description="Storage prefix path")
    row_count: int | None = Field(None, description="Number of rows")
    column_count: int | None = Field(None, description="Number of columns")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    created_at: str = Field(..., description="Creation timestamp (ISO)")
    updated_at: str = Field(..., description="Last update timestamp (ISO)")


class DatasetDetailResponse(DatasetResponse):
    """Response model for dataset with profile.

    Attributes:
        profiles: Column profiles
        summary: LLM-generated dataset summary
    """

    profiles: list[DatasetProfileResponse] = Field(
        default_factory=list, description="Column profiles"
    )
    summary: str | None = Field(None, description="LLM-generated dataset summary")


class DatasetListResponse(BaseModel):
    """Response model for listing datasets.

    Attributes:
        datasets: List of datasets
        total: Total count
        limit: Page size
        offset: Page offset
    """

    datasets: list[DatasetResponse] = Field(..., description="List of datasets")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


# =============================================================================
# Query Models (Data Analysis Platform - EPIC 3)
# =============================================================================


class FilterOperator(str):
    """Filter operator enum values."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    CONTAINS = "contains"
    IN = "in"


class AggregateFunction(str):
    """Aggregate function enum values."""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    DISTINCT = "distinct"


class TrendInterval(str):
    """Trend interval enum values."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class CorrelationMethod(str):
    """Correlation method enum values."""

    PEARSON = "pearson"
    SPEARMAN = "spearman"


class QueryType(str):
    """Query type enum values."""

    FILTER = "filter"
    AGGREGATE = "aggregate"
    TREND = "trend"
    COMPARE = "compare"
    CORRELATE = "correlate"


class FilterSpec(BaseModel):
    """Filter specification for query operations.

    Attributes:
        field: Column name to filter on
        operator: Filter operator
        value: Value to compare against
    """

    field: str = Field(..., min_length=1, description="Column name to filter on")
    operator: str = Field(
        ...,
        pattern="^(eq|ne|gt|lt|gte|lte|contains|in)$",
        description="Filter operator",
    )
    value: Any = Field(..., description="Value to compare against")


class AggregateSpec(BaseModel):
    """Aggregate specification for query operations.

    Attributes:
        field: Column name to aggregate
        function: Aggregate function
        alias: Optional output column name
    """

    field: str = Field(..., min_length=1, description="Column name to aggregate")
    function: str = Field(
        ...,
        pattern="^(sum|avg|min|max|count|distinct)$",
        description="Aggregate function",
    )
    alias: str | None = Field(None, description="Output column name")


class GroupBySpec(BaseModel):
    """GroupBy specification for query operations.

    Attributes:
        fields: Columns to group by
        aggregates: Aggregations to apply
    """

    fields: list[str] = Field(..., min_length=1, description="Columns to group by")
    aggregates: list[AggregateSpec] = Field(..., min_length=1, description="Aggregations to apply")


class TrendSpec(BaseModel):
    """Trend specification for time-series analysis.

    Attributes:
        date_field: Column containing date/datetime values
        value_field: Column to compute trends on
        interval: Time interval for grouping
        aggregate_function: How to aggregate values within intervals
    """

    date_field: str = Field(..., min_length=1, description="Date column")
    value_field: str = Field(..., min_length=1, description="Value column")
    interval: str = Field(
        default="month",
        pattern="^(day|week|month|quarter|year)$",
        description="Time interval",
    )
    aggregate_function: str = Field(
        default="sum",
        pattern="^(sum|avg|min|max|count)$",
        description="Aggregate function for interval",
    )


class CompareSpec(BaseModel):
    """Comparison specification for category analysis.

    Attributes:
        group_field: Column to group/segment by
        value_field: Column to compare
        comparison_type: Type of comparison (absolute or percentage)
        aggregate_function: How to aggregate values per group
    """

    group_field: str = Field(..., min_length=1, description="Column to segment by")
    value_field: str = Field(..., min_length=1, description="Column to compare")
    comparison_type: str = Field(
        default="absolute",
        pattern="^(absolute|percentage)$",
        description="Comparison type",
    )
    aggregate_function: str = Field(
        default="sum",
        pattern="^(sum|avg|min|max|count)$",
        description="Aggregate function",
    )


class CorrelateSpec(BaseModel):
    """Correlation specification for column relationship analysis.

    Attributes:
        field_a: First column for correlation
        field_b: Second column for correlation
        method: Correlation method
    """

    field_a: str = Field(..., min_length=1, description="First column")
    field_b: str = Field(..., min_length=1, description="Second column")
    method: str = Field(
        default="pearson",
        pattern="^(pearson|spearman)$",
        description="Correlation method",
    )


class QuerySpec(BaseModel):
    """Full query specification.

    Attributes:
        query_type: Type of query operation
        filters: Filter conditions (for all query types)
        group_by: GroupBy specification (for aggregate)
        trend: Trend specification (for trend)
        compare: Comparison specification (for compare)
        correlate: Correlation specification (for correlate)
        limit: Maximum rows to return
        offset: Rows to skip
    """

    query_type: str = Field(
        ...,
        pattern="^(filter|aggregate|trend|compare|correlate)$",
        description="Query type",
    )
    filters: list[FilterSpec] | None = Field(None, description="Filter conditions")
    group_by: GroupBySpec | None = Field(None, description="GroupBy specification")
    trend: TrendSpec | None = Field(None, description="Trend specification")
    compare: CompareSpec | None = Field(None, description="Comparison specification")
    correlate: CorrelateSpec | None = Field(None, description="Correlation specification")
    limit: int = Field(default=100, ge=1, le=1000, description="Max rows to return")
    offset: int = Field(default=0, ge=0, description="Rows to skip")


class QueryResultResponse(BaseModel):
    """Response model for query results.

    Attributes:
        rows: Query result rows
        columns: Column names
        total_count: Total rows before pagination
        has_more: Whether more rows exist
        query_type: Type of query executed
    """

    rows: list[dict[str, Any]] = Field(..., description="Query result rows")
    columns: list[str] = Field(..., description="Column names")
    total_count: int = Field(..., description="Total rows before pagination")
    has_more: bool = Field(..., description="Whether more rows exist")
    query_type: str = Field(..., description="Type of query executed")


# =============================================================================
# Chart Models
# =============================================================================


class ChartSpec(BaseModel):
    """Chart specification for generating visualizations.

    Attributes:
        chart_type: Type of chart to generate
        x_field: Column for x-axis
        y_field: Column for y-axis (or values for pie)
        group_field: Optional column for grouping/coloring
        title: Chart title
        filters: Optional filters to apply before charting
    """

    chart_type: str = Field(
        ...,
        pattern="^(line|bar|pie|scatter)$",
        description="Chart type: line, bar, pie, or scatter",
    )
    x_field: str = Field(..., min_length=1, description="Column for x-axis (or names for pie)")
    y_field: str = Field(..., min_length=1, description="Column for y-axis (or values for pie)")
    group_field: str | None = Field(None, description="Optional column for grouping/coloring")
    title: str | None = Field(None, max_length=200, description="Chart title")
    filters: list[FilterSpec] | None = Field(None, description="Optional filters before charting")
    width: int = Field(default=800, ge=200, le=2000, description="Chart width in pixels")
    height: int = Field(default=600, ge=200, le=2000, description="Chart height in pixels")


class ChartResultResponse(BaseModel):
    """Response model for chart generation.

    Attributes:
        figure_json: Plotly figure JSON for frontend rendering
        chart_type: Type of chart generated
        width: Chart width in pixels
        height: Chart height in pixels
        row_count: Number of data points in chart
        analysis_id: ID of saved analysis record (if persisted)
    """

    figure_json: dict[str, Any] = Field(
        ..., description="Plotly figure JSON for frontend rendering"
    )
    chart_type: str = Field(..., description="Type of chart generated")
    width: int = Field(..., description="Chart width in pixels")
    height: int = Field(..., description="Chart height in pixels")
    row_count: int = Field(..., description="Number of data points in chart")
    analysis_id: str | None = Field(None, description="ID of saved analysis record")


class DatasetAnalysisResponse(BaseModel):
    """Response model for a dataset analysis.

    Attributes:
        id: Analysis UUID
        dataset_id: Dataset UUID
        query_spec: Query specification used
        chart_spec: Chart specification used
        chart_url: Presigned URL to chart image
        title: Display title
        created_at: Creation timestamp
    """

    id: str = Field(..., description="Analysis UUID")
    dataset_id: str = Field(..., description="Dataset UUID")
    query_spec: dict[str, Any] | None = Field(None, description="Query specification")
    chart_spec: dict[str, Any] | None = Field(None, description="Chart specification")
    chart_url: str | None = Field(None, description="Presigned URL to chart image")
    title: str | None = Field(None, description="Display title")
    created_at: str = Field(..., description="Creation timestamp")


class DatasetAnalysisListResponse(BaseModel):
    """Response model for listing dataset analyses."""

    analyses: list[DatasetAnalysisResponse] = Field(..., description="List of analyses")
    total: int = Field(..., description="Total count")


# =============================================================================
# Dataset Q&A Models (EPIC 5)
# =============================================================================


class ImportSheetsRequest(BaseModel):
    """Request model for importing a Google Sheet as a dataset.

    Attributes:
        url: Google Sheets URL
        name: Optional dataset name (defaults to sheet title)
        description: Optional description
    """

    url: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Google Sheets URL",
    )
    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Dataset name (defaults to sheet title)",
    )
    description: str | None = Field(
        None,
        max_length=5000,
        description="Dataset description",
    )


class AskRequest(BaseModel):
    """Request model for dataset Q&A.

    Attributes:
        question: Natural language question about the dataset
        conversation_id: Optional conversation ID to continue a thread
    """

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Question about the dataset",
    )
    conversation_id: str | None = Field(
        None,
        description="Conversation ID to continue (omit for new conversation)",
    )


class ConversationMessage(BaseModel):
    """A single message in a dataset conversation.

    Attributes:
        role: Message role (user or assistant)
        content: Message content
        timestamp: When the message was created
        query_spec: Optional query spec if generated
        chart_spec: Optional chart spec if generated
        query_result: Optional query result summary
    """

    role: str = Field(..., pattern="^(user|assistant)$", description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")
    query_spec: dict[str, Any] | None = Field(None, description="Query spec if generated")
    chart_spec: dict[str, Any] | None = Field(None, description="Chart spec if generated")
    query_result: dict[str, Any] | None = Field(None, description="Query result summary")


class ConversationResponse(BaseModel):
    """Response model for a conversation.

    Attributes:
        id: Conversation UUID
        dataset_id: Dataset UUID
        created_at: Creation timestamp
        updated_at: Last message timestamp
        message_count: Number of messages
    """

    id: str = Field(..., description="Conversation UUID")
    dataset_id: str = Field(..., description="Dataset UUID")
    created_at: str = Field(..., description="Creation timestamp (ISO)")
    updated_at: str = Field(..., description="Last message timestamp (ISO)")
    message_count: int = Field(..., description="Number of messages")


class ConversationDetailResponse(ConversationResponse):
    """Response model for conversation with messages.

    Attributes:
        messages: List of conversation messages
    """

    messages: list[ConversationMessage] = Field(
        default_factory=list, description="Conversation messages"
    )


class ConversationListResponse(BaseModel):
    """Response model for listing conversations.

    Attributes:
        conversations: List of conversations
        total: Total count
    """

    conversations: list[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total count")


# =============================================================================
# Session Cost Breakdown Models
# =============================================================================


class ProviderCosts(BaseModel):
    """Cost breakdown by AI provider."""

    anthropic: float = Field(0.0, description="Anthropic (Claude) costs in USD")
    voyage: float = Field(0.0, description="Voyage AI (embeddings) costs in USD")
    brave: float = Field(0.0, description="Brave Search costs in USD")
    tavily: float = Field(0.0, description="Tavily Search costs in USD")


class PhaseCosts(BaseModel):
    """Cost breakdown by deliberation phase."""

    decomposition: float = Field(0.0, description="Decomposition phase costs in USD")
    deliberation: float = Field(0.0, description="Deliberation phase costs in USD")
    synthesis: float = Field(0.0, description="Synthesis phase costs in USD")


class SubProblemCost(BaseModel):
    """Cost breakdown for a single sub-problem.

    Attributes:
        sub_problem_index: Sub-problem index (None for overhead costs)
        label: Human-readable label (e.g., "Sub-problem 0" or "Overhead")
        total_cost: Total cost for this sub-problem in USD
        api_calls: Number of API calls
        total_tokens: Total tokens used
        by_provider: Breakdown by AI provider
        by_phase: Breakdown by deliberation phase
    """

    sub_problem_index: int | None = Field(None, description="Sub-problem index (null for overhead)")
    label: str = Field(..., description="Human-readable label")
    total_cost: float = Field(..., description="Total cost in USD")
    api_calls: int = Field(..., description="Number of API calls")
    total_tokens: int = Field(..., description="Total tokens used")
    by_provider: ProviderCosts = Field(..., description="Breakdown by provider")
    by_phase: PhaseCosts = Field(..., description="Breakdown by phase")


class SessionCostBreakdown(BaseModel):
    """Full cost breakdown for a session.

    Attributes:
        session_id: Session identifier
        total_cost: Total session cost in USD
        total_tokens: Total tokens used
        total_api_calls: Total API calls made
        by_provider: Total costs by provider
        by_sub_problem: Cost breakdown per sub-problem
    """

    session_id: str = Field(..., description="Session identifier")
    total_cost: float = Field(..., description="Total session cost in USD")
    total_tokens: int = Field(..., description="Total tokens used")
    total_api_calls: int = Field(..., description="Total API calls")
    by_provider: ProviderCosts = Field(..., description="Total costs by provider")
    by_sub_problem: list[SubProblemCost] = Field(
        default_factory=list, description="Cost breakdown per sub-problem"
    )


# =============================================================================
# Admin Cost Analytics Models
# =============================================================================


class CostSummaryResponse(BaseModel):
    """Cost totals for different time periods.

    Attributes:
        today: Total cost today in USD
        this_week: Total cost this week in USD
        this_month: Total cost this month in USD
        all_time: Total cost all time in USD
        session_count_today: Sessions today
        session_count_week: Sessions this week
        session_count_month: Sessions this month
        session_count_total: Total sessions
    """

    today: float = Field(default=0.0, description="Total cost today (USD)")
    this_week: float = Field(default=0.0, description="Total cost this week (USD)")
    this_month: float = Field(default=0.0, description="Total cost this month (USD)")
    all_time: float = Field(default=0.0, description="Total cost all time (USD)")
    session_count_today: int = Field(default=0, description="Sessions today")
    session_count_week: int = Field(default=0, description="Sessions this week")
    session_count_month: int = Field(default=0, description="Sessions this month")
    session_count_total: int = Field(default=0, description="Total sessions")


class UserCostItem(BaseModel):
    """Cost summary for a single user.

    Attributes:
        user_id: User identifier
        email: User email (if available)
        total_cost: Total cost in USD
        session_count: Number of sessions
    """

    user_id: str = Field(..., description="User identifier")
    email: str | None = Field(None, description="User email")
    total_cost: float = Field(..., description="Total cost (USD)")
    session_count: int = Field(..., description="Number of sessions")


class UserCostsResponse(BaseModel):
    """Response for per-user cost breakdown.

    Attributes:
        users: List of user cost items
        total: Total number of users
        limit: Page size
        offset: Page offset
    """

    users: list[UserCostItem] = Field(..., description="User cost items")
    total: int = Field(..., description="Total users with costs")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class DailyCostItem(BaseModel):
    """Cost summary for a single day.

    Attributes:
        date: Date (YYYY-MM-DD)
        total_cost: Total cost in USD
        session_count: Number of sessions
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    total_cost: float = Field(..., description="Total cost (USD)")
    session_count: int = Field(..., description="Number of sessions")


class DailyCostsResponse(BaseModel):
    """Response for daily cost breakdown.

    Attributes:
        days: List of daily cost items
        start_date: Start of date range
        end_date: End of date range
    """

    days: list[DailyCostItem] = Field(..., description="Daily cost items")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


# =============================================================================
# User Cost Tracking (Admin Only)
# =============================================================================


class UserCostPeriodItem(BaseModel):
    """Cost totals for a user's billing period (admin only).

    Attributes:
        user_id: User identifier
        period_start: Start of period (YYYY-MM-DD)
        period_end: End of period (YYYY-MM-DD)
        total_cost_cents: Total cost in cents
        session_count: Number of sessions
    """

    user_id: str = Field(..., description="User identifier")
    period_start: str = Field(..., description="Period start (YYYY-MM-DD)")
    period_end: str = Field(..., description="Period end (YYYY-MM-DD)")
    total_cost_cents: int = Field(..., description="Total cost in cents")
    session_count: int = Field(..., description="Number of sessions")


class UserBudgetSettingsItem(BaseModel):
    """Budget settings for a user (admin only).

    Attributes:
        user_id: User identifier
        monthly_cost_limit_cents: Monthly limit in cents (null = unlimited)
        alert_threshold_pct: Percentage threshold for alerting
        hard_limit_enabled: Whether to block when limit exceeded
    """

    user_id: str = Field(..., description="User identifier")
    monthly_cost_limit_cents: int | None = Field(None, description="Monthly limit (cents)")
    alert_threshold_pct: int = Field(80, description="Alert threshold percentage")
    hard_limit_enabled: bool = Field(False, description="Block when exceeded")


class UserCostDetailResponse(BaseModel):
    """Detailed cost info for a user (admin only).

    Attributes:
        user_id: User identifier
        email: User email
        current_period: Current period cost data
        budget_settings: Budget configuration
        history: Historical periods
    """

    user_id: str = Field(..., description="User identifier")
    email: str | None = Field(None, description="User email")
    current_period: UserCostPeriodItem | None = Field(None, description="Current period")
    budget_settings: UserBudgetSettingsItem | None = Field(None, description="Budget settings")
    history: list[UserCostPeriodItem] = Field(default_factory=list, description="History")


class TopUsersCostResponse(BaseModel):
    """Top users by cost (admin only, abuse detection).

    Attributes:
        period_start: Period queried
        users: List of users sorted by cost descending
    """

    period_start: str = Field(..., description="Period start (YYYY-MM-DD)")
    users: list[UserCostPeriodItem] = Field(..., description="Users by cost desc")


class UpdateBudgetSettingsRequest(BaseModel):
    """Request to update user budget settings (admin only).

    Attributes:
        monthly_cost_limit_cents: Monthly limit in cents (null = unlimited)
        alert_threshold_pct: Percentage threshold for alerting
        hard_limit_enabled: Whether to block when limit exceeded
    """

    monthly_cost_limit_cents: int | None = Field(None, description="Monthly limit (cents)")
    alert_threshold_pct: int | None = Field(None, ge=1, le=100, description="Alert threshold %")
    hard_limit_enabled: bool | None = Field(None, description="Block when exceeded")


# =============================================================================
# Session Termination Models
# =============================================================================


class TerminationRequest(BaseModel):
    """Request to terminate a session early.

    Attributes:
        termination_type: Type of termination action
        reason: User-provided reason for termination (optional)
    """

    termination_type: str = Field(
        ...,
        description="Type of termination: blocker_identified, user_cancelled, continue_best_effort",
        pattern="^(blocker_identified|user_cancelled|continue_best_effort)$",
    )
    reason: str | None = Field(
        None,
        max_length=2000,
        description="User-provided reason for termination",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "termination_type": "blocker_identified",
                    "reason": "Missing critical market data for Europe",
                },
                {
                    "termination_type": "continue_best_effort",
                    "reason": "Need results now despite incomplete analysis",
                },
                {
                    "termination_type": "user_cancelled",
                    "reason": "No longer relevant",
                },
            ]
        }
    }


class TerminationResponse(BaseModel):
    """Response after terminating a session.

    Attributes:
        session_id: Session identifier
        status: New session status
        terminated_at: Termination timestamp
        termination_type: Type of termination
        billable_portion: Fraction of session to bill (0.0-1.0)
        completed_sub_problems: Number of sub-problems completed
        total_sub_problems: Total number of sub-problems
        synthesis_available: Whether synthesis is available (for continue_best_effort)
    """

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="New session status")
    terminated_at: datetime = Field(..., description="Termination timestamp (UTC)")
    termination_type: str = Field(..., description="Type of termination")
    billable_portion: float = Field(..., ge=0.0, le=1.0, description="Fraction of session to bill")
    completed_sub_problems: int = Field(..., description="Sub-problems completed")
    total_sub_problems: int = Field(..., description="Total sub-problems")
    synthesis_available: bool = Field(..., description="Whether early synthesis is available")


# ============================================================================
# Promotions Models
# ============================================================================


class PromotionType(str):
    """Promotion type constants."""

    GOODWILL_CREDITS = "goodwill_credits"
    PERCENTAGE_DISCOUNT = "percentage_discount"
    FLAT_DISCOUNT = "flat_discount"
    EXTRA_DELIBERATIONS = "extra_deliberations"


class UserPromotionStatus(str):
    """User promotion status constants."""

    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"


class Promotion(BaseModel):
    """Promotion response model.

    Attributes:
        id: Unique promotion identifier (UUID)
        code: Unique promo code string
        type: Type of promotion (goodwill_credits, percentage_discount, etc.)
        value: Promotion value (percentage, flat amount, or number of credits)
        max_uses: Maximum number of uses (null = unlimited)
        uses_count: Current number of times promo has been used
        expires_at: Expiration timestamp (null = never expires)
        created_at: Creation timestamp
        deleted_at: Soft-delete timestamp (null = active)
    """

    id: str = Field(..., description="Unique promotion identifier (UUID)")
    code: str = Field(..., min_length=3, max_length=50, description="Unique promo code")
    type: str = Field(
        ...,
        description="Promotion type: goodwill_credits, percentage_discount, flat_discount, extra_deliberations",
    )
    value: float = Field(..., gt=0, description="Promotion value")
    max_uses: int | None = Field(None, description="Maximum uses (null = unlimited)")
    uses_count: int = Field(0, ge=0, description="Current usage count")
    expires_at: datetime | None = Field(None, description="Expiration timestamp (UTC)")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    deleted_at: datetime | None = Field(None, description="Soft-delete timestamp (null = active)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "code": "WELCOME10",
                    "type": "percentage_discount",
                    "value": 10.0,
                    "max_uses": 1000,
                    "uses_count": 42,
                    "expires_at": None,
                    "created_at": "2025-01-01T00:00:00Z",
                    "deleted_at": None,
                }
            ]
        }
    }

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate promotion type."""
        valid_types = {
            PromotionType.GOODWILL_CREDITS,
            PromotionType.PERCENTAGE_DISCOUNT,
            PromotionType.FLAT_DISCOUNT,
            PromotionType.EXTRA_DELIBERATIONS,
        }
        if v not in valid_types:
            raise ValueError(f"Invalid promotion type: {v}. Must be one of: {valid_types}")
        return v


class UserPromotion(BaseModel):
    """User's applied promotion response model.

    Attributes:
        id: Unique user_promotion identifier (UUID)
        promotion: Nested promotion details
        applied_at: When the user applied the promo
        deliberations_remaining: Remaining credits (for credit-type promos)
        discount_applied: Discount amount applied (for discount-type promos)
        status: Current status (active, exhausted, expired)
    """

    id: str = Field(..., description="Unique identifier (UUID)")
    promotion: Promotion = Field(..., description="Promotion details")
    applied_at: datetime = Field(..., description="When promo was applied (UTC)")
    deliberations_remaining: int | None = Field(
        None, description="Remaining credits (credit promos only)"
    )
    discount_applied: float | None = Field(
        None, description="Discount applied (discount promos only)"
    )
    status: str = Field(..., description="Status: active, exhausted, expired")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "promotion": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "code": "GOODWILL5",
                        "type": "extra_deliberations",
                        "value": 5.0,
                        "max_uses": None,
                        "uses_count": 100,
                        "expires_at": None,
                        "created_at": "2025-01-01T00:00:00Z",
                        "deleted_at": None,
                    },
                    "applied_at": "2025-01-15T10:30:00Z",
                    "deliberations_remaining": 3,
                    "discount_applied": None,
                    "status": "active",
                }
            ]
        }
    }

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate user promotion status."""
        valid_statuses = {
            UserPromotionStatus.ACTIVE,
            UserPromotionStatus.EXHAUSTED,
            UserPromotionStatus.EXPIRED,
        }
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of: {valid_statuses}")
        return v


class AddPromotionRequest(BaseModel):
    """Admin request to create a new promotion.

    Attributes:
        code: Unique promo code (3-50 chars, alphanumeric + underscore)
        type: Promotion type
        value: Promotion value (> 0)
        max_uses: Optional maximum uses
        expires_at: Optional expiration timestamp
    """

    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Z0-9_]+$",
        description="Promo code (uppercase alphanumeric + underscore)",
    )
    type: str = Field(..., description="Promotion type")
    value: float = Field(..., gt=0, description="Promotion value")
    max_uses: int | None = Field(None, gt=0, description="Maximum uses (null = unlimited)")
    expires_at: datetime | None = Field(None, description="Expiration timestamp (UTC)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "SUMMER2025",
                    "type": "percentage_discount",
                    "value": 20.0,
                    "max_uses": 500,
                    "expires_at": "2025-08-31T23:59:59Z",
                }
            ]
        }
    }

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate promotion type."""
        valid_types = {
            PromotionType.GOODWILL_CREDITS,
            PromotionType.PERCENTAGE_DISCOUNT,
            PromotionType.FLAT_DISCOUNT,
            PromotionType.EXTRA_DELIBERATIONS,
        }
        if v not in valid_types:
            raise ValueError(f"Invalid promotion type: {v}. Must be one of: {valid_types}")
        return v


class ApplyPromoCodeRequest(BaseModel):
    """User request to apply a promo code.

    Attributes:
        code: The promo code to apply
    """

    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Promo code to apply",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"code": "WELCOME10"},
                {"code": "GOODWILL5"},
            ]
        }
    }

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Normalize and validate promo code."""
        # Normalize to uppercase
        v = v.strip().upper()
        if not v:
            raise ValueError("Promo code cannot be empty")
        # Allow alphanumeric and underscore
        if not re.match(r"^[A-Z0-9_]+$", v):
            raise ValueError("Promo code must be alphanumeric (letters, numbers, underscore)")
        return v


# =============================================================================
# Feedback Models
# =============================================================================


class FeedbackType:
    """Valid feedback types."""

    FEATURE_REQUEST = "feature_request"
    PROBLEM_REPORT = "problem_report"


class FeedbackStatus:
    """Valid feedback statuses."""

    NEW = "new"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    CLOSED = "closed"


class FeedbackCreate(BaseModel):
    """Request model for submitting feedback.

    Attributes:
        type: Feedback type (feature_request or problem_report)
        title: Brief title/summary
        description: Detailed description
        include_context: Whether to auto-attach context (for problem reports)
    """

    type: str = Field(
        ...,
        description="Feedback type (feature_request or problem_report)",
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Brief title/summary",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed description",
    )
    include_context: bool = Field(
        default=True,
        description="Whether to auto-attach context (for problem reports)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "feature_request",
                    "title": "Add dark mode support",
                    "description": "It would be great to have a dark mode option for the UI.",
                    "include_context": False,
                },
                {
                    "type": "problem_report",
                    "title": "Meeting page not loading",
                    "description": "When I click on a meeting, the page shows a spinner but never loads.",
                    "include_context": True,
                },
            ]
        }
    }

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate feedback type."""
        valid_types = {FeedbackType.FEATURE_REQUEST, FeedbackType.PROBLEM_REPORT}
        if v not in valid_types:
            raise ValueError(f"Invalid feedback type. Must be one of: {valid_types}")
        return v


class FeedbackContext(BaseModel):
    """Auto-attached context for problem reports.

    Attributes:
        user_tier: User's subscription tier
        page_url: Page URL where problem occurred
        user_agent: Browser user agent
        timestamp: When the problem was reported
    """

    user_tier: str | None = Field(None, description="User's subscription tier")
    page_url: str | None = Field(None, description="Page URL where problem occurred")
    user_agent: str | None = Field(None, description="Browser user agent")
    timestamp: str | None = Field(None, description="Timestamp of report (ISO format)")


class FeedbackAnalysis(BaseModel):
    """Analysis result for feedback (sentiment and themes).

    Attributes:
        sentiment: Sentiment classification (positive, negative, neutral, mixed)
        sentiment_confidence: Confidence score (0.0-1.0)
        themes: List of theme tags (1-5 tags)
        analyzed_at: When analysis was performed
    """

    sentiment: str = Field(..., description="Sentiment: positive, negative, neutral, mixed")
    sentiment_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0-1)")
    themes: list[str] = Field(default_factory=list, description="Theme tags")
    analyzed_at: str | None = Field(None, description="Analysis timestamp (ISO)")


class FeedbackResponse(BaseModel):
    """Response model for a single feedback item.

    Attributes:
        id: Feedback UUID
        user_id: Submitter's user ID
        type: Feedback type
        title: Brief title/summary
        description: Detailed description
        context: Auto-attached context (if available)
        analysis: Sentiment and themes analysis (if available)
        status: Current status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str = Field(..., description="Feedback UUID")
    user_id: str = Field(..., description="Submitter's user ID")
    type: str = Field(..., description="Feedback type")
    title: str = Field(..., description="Brief title/summary")
    description: str = Field(..., description="Detailed description")
    context: dict | None = Field(None, description="Auto-attached context")
    analysis: FeedbackAnalysis | None = Field(None, description="Sentiment and themes analysis")
    status: str = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class FeedbackListResponse(BaseModel):
    """Response model for listing feedback items.

    Attributes:
        items: List of feedback items
        total: Total count (for pagination)
    """

    items: list[FeedbackResponse] = Field(..., description="List of feedback items")
    total: int = Field(..., description="Total count")


class FeedbackStatusUpdate(BaseModel):
    """Request model for updating feedback status.

    Attributes:
        status: New status (new, reviewing, resolved, closed)
    """

    status: str = Field(..., description="New status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status."""
        valid_statuses = {
            FeedbackStatus.NEW,
            FeedbackStatus.REVIEWING,
            FeedbackStatus.RESOLVED,
            FeedbackStatus.CLOSED,
        }
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class FeedbackStats(BaseModel):
    """Response model for feedback statistics.

    Attributes:
        total: Total feedback count
        by_type: Counts by type
        by_status: Counts by status
    """

    total: int = Field(..., description="Total feedback count")
    by_type: dict[str, int] = Field(..., description="Counts by type")
    by_status: dict[str, int] = Field(..., description="Counts by status")


class ThemeCount(BaseModel):
    """Theme with its count."""

    theme: str = Field(..., description="Theme tag")
    count: int = Field(..., description="Number of feedback items with this theme")


class FeedbackAnalysisSummary(BaseModel):
    """Aggregated feedback analysis summary.

    Attributes:
        analyzed_count: Number of feedback items with analysis
        sentiment_counts: Distribution by sentiment
        top_themes: Most common themes with counts
    """

    analyzed_count: int = Field(..., description="Feedback items with analysis")
    sentiment_counts: dict[str, int] = Field(..., description="Counts by sentiment")
    top_themes: list[ThemeCount] = Field(..., description="Top themes with counts")


# ============================================================================
# Blog Post Models
# ============================================================================


class BlogPostStatus:
    """Valid blog post statuses."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class BlogPostCreate(BaseModel):
    """Request model for creating a blog post.

    Attributes:
        title: Post title
        content: Markdown content
        excerpt: Short excerpt for previews
        status: draft, scheduled, or published
        published_at: Scheduled publication datetime
        seo_keywords: Target keywords
        meta_title: Custom SEO title
        meta_description: Custom SEO description
    """

    title: str = Field(..., min_length=1, max_length=500, description="Post title")
    content: str = Field(..., min_length=1, description="Markdown content")
    excerpt: str | None = Field(None, max_length=500, description="Short excerpt")
    status: str = Field(default="draft", description="draft, scheduled, or published")
    published_at: datetime | None = Field(None, description="Scheduled publication datetime")
    seo_keywords: list[str] | None = Field(None, description="Target keywords")
    meta_title: str | None = Field(None, max_length=100, description="Custom SEO title")
    meta_description: str | None = Field(None, max_length=300, description="Custom SEO description")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status."""
        valid = {BlogPostStatus.DRAFT, BlogPostStatus.SCHEDULED, BlogPostStatus.PUBLISHED}
        if v not in valid:
            raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class BlogPostUpdate(BaseModel):
    """Request model for updating a blog post.

    All fields are optional - only provided fields are updated.
    """

    title: str | None = Field(None, min_length=1, max_length=500, description="Post title")
    content: str | None = Field(None, min_length=1, description="Markdown content")
    excerpt: str | None = Field(None, max_length=500, description="Short excerpt")
    status: str | None = Field(None, description="draft, scheduled, or published")
    published_at: datetime | None = Field(None, description="Scheduled publication datetime")
    seo_keywords: list[str] | None = Field(None, description="Target keywords")
    meta_title: str | None = Field(None, max_length=100, description="Custom SEO title")
    meta_description: str | None = Field(None, max_length=300, description="Custom SEO description")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status if provided."""
        if v is None:
            return v
        valid = {BlogPostStatus.DRAFT, BlogPostStatus.SCHEDULED, BlogPostStatus.PUBLISHED}
        if v not in valid:
            raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class BlogPostResponse(BaseModel):
    """Response model for a blog post."""

    id: str = Field(..., description="Post UUID")
    title: str = Field(..., description="Post title")
    slug: str = Field(..., description="URL slug")
    content: str | None = Field(None, description="Markdown content")
    excerpt: str | None = Field(None, description="Short excerpt")
    status: str = Field(..., description="draft, scheduled, or published")
    published_at: datetime | None = Field(None, description="Publication datetime")
    seo_keywords: list[str] | None = Field(None, description="Target keywords")
    generated_by_topic: str | None = Field(None, description="Topic that triggered generation")
    meta_title: str | None = Field(None, description="Custom SEO title")
    meta_description: str | None = Field(None, description="Custom SEO description")
    author_id: str | None = Field(None, description="Author user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class BlogPostListResponse(BaseModel):
    """Response model for blog post list."""

    posts: list[BlogPostResponse] = Field(..., description="List of posts")
    total: int = Field(..., description="Total count")


class BlogGenerateRequest(BaseModel):
    """Request model for AI blog post generation."""

    topic: str = Field(..., min_length=3, max_length=500, description="Topic to write about")
    keywords: list[str] | None = Field(None, description="Target SEO keywords")


class BlogGenerateResponse(BaseModel):
    """Response model for generated blog content."""

    title: str = Field(..., description="Generated title")
    excerpt: str = Field(..., description="Generated excerpt")
    content: str = Field(..., description="Generated markdown content")
    meta_title: str = Field(..., description="Generated SEO title")
    meta_description: str = Field(..., description="Generated SEO description")
    post_id: str | None = Field(None, description="Created post ID if saved")


class TopicResponse(BaseModel):
    """Response model for a discovered topic."""

    title: str = Field(..., description="Topic title")
    description: str = Field(..., description="Topic description")
    keywords: list[str] = Field(..., description="Suggested keywords")
    relevance_score: float = Field(..., description="Relevance score 0-1")
    source: str = Field(..., description="Source: context, trend, or gap")


class TopicsResponse(BaseModel):
    """Response model for topic discovery."""

    topics: list[TopicResponse] = Field(..., description="Discovered topics")


# ============================================================================
# Generic Response Models
# ============================================================================


class MessageResponse(BaseModel):
    """Generic response for endpoints that return a simple status/message.

    Used for: task status updates, operation confirmations, etc.
    """

    status: str = Field(..., description="Operation status (e.g., 'success')")
    message: str = Field(..., description="Human-readable message")


class WhitelistCheckResponse(BaseModel):
    """Response for whitelist/beta access check endpoints."""

    is_whitelisted: bool = Field(..., description="Whether the email is whitelisted")
