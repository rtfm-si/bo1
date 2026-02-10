"""Pydantic models for Board of One API.

Defines request/response models for all API endpoints with validation,
examples, and security constraints.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.api.utils.honeypot import HoneypotMixin

# Valid constraint types (mirrors bo1.models.problem.ConstraintType)
VALID_CONSTRAINT_TYPES = {
    "budget",
    "time",
    "resource",
    "regulatory",
    "technical",
    "ethical",
    "other",
}


class ConstraintInput(BaseModel):
    """Input model for a single constraint."""

    type: str = Field(
        ..., description="Constraint type (budget/time/resource/regulatory/technical/ethical/other)"
    )
    description: str = Field(
        ..., min_length=5, max_length=500, description="Constraint description"
    )
    value: Any | None = Field(
        None, description="Optional constraint value (e.g., dollar amount, date)"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate constraint type is allowed."""
        v = v.strip().lower()
        if v not in VALID_CONSTRAINT_TYPES:
            raise ValueError(
                f"Invalid constraint type: {v}. Must be one of: {', '.join(sorted(VALID_CONSTRAINT_TYPES))}"
            )
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Sanitize constraint description."""
        v = v.strip()
        if re.search(r"<script[^>]*>", v, re.IGNORECASE):
            raise ValueError("Constraint description cannot contain script tags")
        return v


class CreateSessionRequest(HoneypotMixin):
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
    template_id: str | None = Field(
        None,
        description="Optional template UUID to track which template was used to create this session",
    )
    constraints: list[ConstraintInput] | None = Field(
        None,
        description="Optional constraints for the deliberation (max 10)",
        examples=[
            [
                {
                    "type": "budget",
                    "description": "Total budget must not exceed $500K",
                    "value": 500000,
                }
            ]
        ],
    )

    @field_validator("constraints")
    @classmethod
    def validate_constraints(cls, v: list[ConstraintInput] | None) -> list[ConstraintInput] | None:
        """Validate constraint list length."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 constraints allowed")
        return v

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
    """API response model for session information (user-facing subset).

    This is a **response model** exposing only fields relevant to end users.
    Internal tracking fields (recovery_needed, has_untracked_costs, checkpoints,
    A/B variants, billable_portion, termination details) are excluded for:
    - Privacy: users don't need internal cost/recovery state
    - Security: checkpoint indices are implementation details
    - Simplicity: dashboard only needs summary counts

    For the full domain model, see `bo1/models/session.py:Session`.
    See `docs/adr/007-domain-response-model-separation.md` for rationale.

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
    # Meeting credits (returned on session creation when prepaid credit was used)
    meeting_credits_remaining: int | None = Field(
        None,
        description="Remaining meeting credits after this session (if session used prepaid credit)",
    )


class SessionListResponse(BaseModel):
    """Response model for session list.

    Attributes:
        sessions: List of session summaries
        total: Total number of sessions
        limit: Page size
        offset: Page offset
        has_more: Whether more sessions exist beyond current page
        next_offset: Offset for next page (None if no more pages)
    """

    sessions: list[SessionResponse] = Field(..., description="List of session summaries")
    total: int = Field(..., description="Total number of sessions")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")
    has_more: bool = Field(..., description="Whether more sessions exist beyond current page")
    next_offset: int | None = Field(None, description="Offset for next page (None if no more)")


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
        reconnect_count: Number of SSE reconnections (admin debugging)
    """

    id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Current status")
    phase: str | None = Field(None, description="Current phase")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    problem: dict[str, Any] = Field(..., description="Problem details")
    state: dict[str, Any] | None = Field(None, description="Full deliberation state")
    metrics: dict[str, Any] | None = Field(None, description="Session metrics")
    reconnect_count: int | None = Field(None, description="SSE reconnection count (admin only)")


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
    """Standard API error response with structured error code.

    This matches the format produced by `http_error()` helper.
    All API errors return this structure for consistent client handling.

    Attributes:
        error_code: Machine-readable error code from ErrorCode enum
        message: Human-readable error message
    """

    error_code: str = Field(
        ...,
        description="Machine-readable error code for client handling and log aggregation",
        examples=["API_NOT_FOUND", "API_FORBIDDEN", "API_BAD_REQUEST"],
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
        examples=["Session not found", "Access denied", "Invalid request parameters"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_NOT_FOUND",
                    "message": "Session not found",
                },
                {
                    "error_code": "API_FORBIDDEN",
                    "message": "Not authorized to access this resource",
                },
                {
                    "error_code": "API_BAD_REQUEST",
                    "message": "Invalid session status for this operation",
                },
            ]
        }
    }


class NotFoundErrorResponse(ErrorResponse):
    """Error response for 404 Not Found.

    Used when a requested resource doesn't exist.
    """

    error_code: str = Field(
        "API_NOT_FOUND",
        description="Error code for not found errors",
    )
    message: str = Field(
        "Resource not found",
        description="Not found error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_NOT_FOUND",
                    "message": "Session not found",
                },
                {
                    "error_code": "API_NOT_FOUND",
                    "message": "Action not found",
                },
            ]
        }
    }


class ForbiddenErrorResponse(ErrorResponse):
    """Error response for 403 Forbidden.

    Used when the user is authenticated but lacks permission.
    """

    error_code: str = Field(
        "API_FORBIDDEN",
        description="Error code for authorization failures",
    )
    message: str = Field(
        "Access denied",
        description="Forbidden error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_FORBIDDEN",
                    "message": "Not authorized to access this session",
                },
                {
                    "error_code": "API_FORBIDDEN",
                    "message": "Workspace access required",
                },
            ]
        }
    }


class UnauthorizedErrorResponse(ErrorResponse):
    """Error response for 401 Unauthorized.

    Used when authentication is missing or invalid.
    """

    error_code: str = Field(
        "API_UNAUTHORIZED",
        description="Error code for authentication failures",
    )
    message: str = Field(
        "Authentication required",
        description="Unauthorized error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_UNAUTHORIZED",
                    "message": "Authentication required",
                },
                {
                    "error_code": "AUTH_TOKEN_ERROR",
                    "message": "Invalid or expired token",
                },
            ]
        }
    }


class BadRequestErrorResponse(ErrorResponse):
    """Error response for 400 Bad Request.

    Used for validation errors and malformed requests.
    """

    error_code: str = Field(
        "API_BAD_REQUEST",
        description="Error code for bad request errors",
    )
    message: str = Field(
        "Invalid request",
        description="Bad request error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_BAD_REQUEST",
                    "message": "Cannot start session with status: completed",
                },
                {
                    "error_code": "VALIDATION_ERROR",
                    "message": "Invalid session ID format",
                },
            ]
        }
    }


class ConflictErrorResponse(ErrorResponse):
    """Error response for 409 Conflict.

    Used when the request conflicts with current state.
    """

    error_code: str = Field(
        "API_CONFLICT",
        description="Error code for conflict errors",
    )
    message: str = Field(
        "Resource conflict",
        description="Conflict error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_CONFLICT",
                    "message": "Session is already running",
                },
                {
                    "error_code": "API_CONFLICT",
                    "message": "Action already completed",
                },
            ]
        }
    }


class InternalErrorResponse(ErrorResponse):
    """Error response for 500 Internal Server Error.

    Used for unexpected server-side failures.
    """

    error_code: str = Field(
        "API_REQUEST_ERROR",
        description="Error code for internal server errors",
    )
    message: str = Field(
        "An unexpected error occurred",
        description="Internal error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_REQUEST_ERROR",
                    "message": "An unexpected error occurred",
                },
                {
                    "error_code": "GRAPH_EXECUTION_FAILED",
                    "message": "Failed to execute deliberation graph",
                },
            ]
        }
    }


class GoneErrorResponse(ErrorResponse):
    """Error response for 410 Gone.

    Used when a resource is no longer available (e.g., expired invitation).
    """

    error_code: str = Field(
        "API_GONE",
        description="Error code for gone resources",
    )
    message: str = Field(
        "Resource no longer available",
        description="Gone error message",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error_code": "API_GONE",
                    "message": "Invitation has expired",
                },
            ]
        }
    }


class RateLimitResponse(BaseModel):
    """Response model for rate limit exceeded (HTTP 429).

    This model documents the shape of rate limit error responses for OpenAPI.
    Used in `responses={429: {"model": RateLimitResponse}}` on rate-limited endpoints.

    Attributes:
        detail: Human-readable error message
        error_code: Machine-readable error code ("rate_limited")
        retry_after: Seconds until rate limit resets (also in Retry-After header)
    """

    detail: str = Field(
        "Too many requests. Please try again later.",
        description="Human-readable error message",
    )
    error_code: str = Field(
        "rate_limited",
        description="Machine-readable error code for client handling",
    )
    retry_after: int = Field(
        ...,
        description="Seconds until the rate limit window resets. Also provided in Retry-After header.",
        examples=[60],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Too many requests. Please try again later.",
                    "error_code": "rate_limited",
                    "retry_after": 60,
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
    FAILED = "failed"
    ABANDONED = "abandoned"
    REPLANNED = "replanned"


class TaskStatusUpdate(BaseModel):
    """Request model for updating task status.

    Attributes:
        status: New status for the task
    """

    status: str = Field(
        ...,
        description="New task status",
        pattern="^(todo|doing|done|in_progress|blocked|in_review|cancelled)$",
        examples=["todo", "doing", "done", "in_progress"],
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
    source_session_status: str | None = Field(
        default=None,
        description="Status of source session (completed/failed). 'failed' indicates action from acknowledged failure.",
    )
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
    # Post-mortem fields (z28 migration)
    lessons_learned: str | None = Field(
        default=None, description="User reflection on lessons learned from this action"
    )
    went_well: str | None = Field(
        default=None, description="User reflection on what went well during this action"
    )


class ActionCreate(BaseModel):
    """Request model for creating a new action.

    Attributes:
        title: Short action title
        description: Full action description
        what_and_how: Steps to complete (max 20 items, max 1000 chars each)
        success_criteria: Success measures (max 20 items, max 500 chars each)
        kill_criteria: Abandonment conditions (max 20 items, max 500 chars each)
        priority: Priority level
        category: Action category
        timeline: Human-readable timeline
        estimated_duration_days: Duration in business days
        target_start_date: User-set target start
        target_end_date: User-set target end
    """

    title: str = Field(..., min_length=1, max_length=500, description="Action title")
    description: str = Field(..., min_length=1, max_length=10000, description="Action description")
    what_and_how: list[str] = Field(
        default_factory=list, description="Steps to complete (max 20 items, max 1000 chars each)"
    )
    success_criteria: list[str] = Field(
        default_factory=list, description="Success measures (max 20 items, max 500 chars each)"
    )
    kill_criteria: list[str] = Field(
        default_factory=list,
        description="Abandonment conditions (max 20 items, max 500 chars each)",
    )
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

    @field_validator("what_and_how")
    @classmethod
    def validate_what_and_how(cls, v: list[str]) -> list[str]:
        """Validate what_and_how list: max 20 items, max 1000 chars each."""
        if len(v) > 20:
            raise ValueError("what_and_how cannot exceed 20 items")
        for i, item in enumerate(v):
            if len(item) > 1000:
                raise ValueError(f"what_and_how item {i + 1} exceeds 1000 characters")
        return v

    @field_validator("success_criteria")
    @classmethod
    def validate_success_criteria(cls, v: list[str]) -> list[str]:
        """Validate success_criteria list: max 20 items, max 500 chars each."""
        if len(v) > 20:
            raise ValueError("success_criteria cannot exceed 20 items")
        for i, item in enumerate(v):
            if len(item) > 500:
                raise ValueError(f"success_criteria item {i + 1} exceeds 500 characters")
        return v

    @field_validator("kill_criteria")
    @classmethod
    def validate_kill_criteria(cls, v: list[str]) -> list[str]:
        """Validate kill_criteria list: max 20 items, max 500 chars each."""
        if len(v) > 20:
            raise ValueError("kill_criteria cannot exceed 20 items")
        for i, item in enumerate(v):
            if len(item) > 500:
                raise ValueError(f"kill_criteria item {i + 1} exceeds 500 characters")
        return v


class ActionUpdate(BaseModel):
    """Request model for updating an action.

    Attributes:
        title: Updated title
        description: Updated description
        what_and_how: Updated steps (max 20 items, max 1000 chars each)
        success_criteria: Updated success measures (max 20 items, max 500 chars each)
        kill_criteria: Updated abandonment conditions (max 20 items, max 500 chars each)
        priority: Updated priority
        category: Updated category
        timeline: Updated timeline
        estimated_duration_days: Updated duration
        target_start_date: Updated target start
        target_end_date: Updated target end
    """

    title: str | None = Field(None, min_length=1, max_length=500, description="Updated title")
    description: str | None = Field(
        None, min_length=1, max_length=10000, description="Updated description"
    )
    what_and_how: list[str] | None = Field(
        None, description="Updated steps (max 20 items, max 1000 chars each)"
    )
    success_criteria: list[str] | None = Field(
        None, description="Updated success measures (max 20 items, max 500 chars each)"
    )
    kill_criteria: list[str] | None = Field(
        None, description="Updated abandonment conditions (max 20 items, max 500 chars each)"
    )
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

    @field_validator("what_and_how")
    @classmethod
    def validate_what_and_how(cls, v: list[str] | None) -> list[str] | None:
        """Validate what_and_how list: max 20 items, max 1000 chars each."""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("what_and_how cannot exceed 20 items")
        for i, item in enumerate(v):
            if len(item) > 1000:
                raise ValueError(f"what_and_how item {i + 1} exceeds 1000 characters")
        return v

    @field_validator("success_criteria")
    @classmethod
    def validate_success_criteria(cls, v: list[str] | None) -> list[str] | None:
        """Validate success_criteria list: max 20 items, max 500 chars each."""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("success_criteria cannot exceed 20 items")
        for i, item in enumerate(v):
            if len(item) > 500:
                raise ValueError(f"success_criteria item {i + 1} exceeds 500 characters")
        return v

    @field_validator("kill_criteria")
    @classmethod
    def validate_kill_criteria(cls, v: list[str] | None) -> list[str] | None:
        """Validate kill_criteria list: max 20 items, max 500 chars each."""
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("kill_criteria cannot exceed 20 items")
        for i, item in enumerate(v):
            if len(item) > 500:
                raise ValueError(f"kill_criteria item {i + 1} exceeds 500 characters")
        return v


class ActionStatusUpdate(BaseModel):
    """Request model for updating action status.

    Attributes:
        status: New status
        blocking_reason: Reason for blocked status (required if status is 'blocked', max 2000 chars)
        auto_unblock: Auto-unblock when dependencies complete
        cancellation_reason: Reason for cancelled status (required if status is 'cancelled', max 2000 chars)
        failure_reason_category: Category of failure (blocker/scope_creep/dependency/unknown)
        replan_suggested_at: Timestamp when replanning suggestion was shown
    """

    status: str = Field(
        ...,
        pattern="^(todo|in_progress|blocked|in_review|done|cancelled|failed|abandoned|replanned)$",
        description="New status",
    )
    blocking_reason: str | None = Field(
        None, max_length=2000, description="Reason for blocked status (max 2000 chars)"
    )
    auto_unblock: bool = Field(default=False, description="Auto-unblock when dependencies complete")
    cancellation_reason: str | None = Field(
        None, max_length=2000, description="Reason for cancelled status (max 2000 chars)"
    )
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
        blocking_reason: Why the action is blocked (max 2000 chars for detailed reasons)
        auto_unblock: Whether to auto-unblock when dependencies complete
    """

    blocking_reason: str = Field(
        ..., min_length=1, max_length=2000, description="Why the action is blocked (max 2000 chars)"
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


class ActionCloseRequest(BaseModel):
    """Request model for closing an action as failed or abandoned.

    Attributes:
        status: Target status - must be 'failed' or 'abandoned'
        reason: Reason for closing the action
    """

    status: str = Field(
        ...,
        pattern="^(failed|abandoned)$",
        description="Target status: 'failed' or 'abandoned'",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Reason for closing the action",
    )


class ActionCloseResponse(BaseModel):
    """Response model for closing an action.

    Attributes:
        action_id: Closed action ID
        status: New status (failed or abandoned)
        message: Success message
    """

    action_id: str = Field(..., description="Closed action ID")
    status: str = Field(..., description="New status")
    message: str = Field(..., description="Success message")


class ActionCloneReplanRequest(BaseModel):
    """Request model for replanning an action by cloning it.

    This creates a new action based on the original failed/abandoned action,
    with optional modifications. The original action is marked as 'replanned'.

    Attributes:
        new_steps: Optional new what_and_how steps (defaults to original)
        new_target_date: Optional new target end date (YYYY-MM-DD)
    """

    new_steps: list[str] | None = Field(
        None,
        description="New what_and_how steps (defaults to original if not provided)",
    )
    new_target_date: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="New target end date (YYYY-MM-DD)",
    )


class ActionCloneReplanResponse(BaseModel):
    """Response model for clone-replan operation.

    Attributes:
        new_action_id: ID of the newly created action
        original_action_id: ID of the original action (now marked as 'replanned')
        message: Success message
    """

    new_action_id: str = Field(..., description="New action ID")
    original_action_id: str = Field(..., description="Original action ID")
    message: str = Field(..., description="Success message")


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
        page: Current page (1-indexed)
        per_page: Items per page
        has_more: Whether more projects exist beyond current page
        next_offset: Offset for next page (None if no more pages)
    """

    projects: list[ProjectDetailResponse] = Field(..., description="List of projects")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more projects exist beyond current page")
    next_offset: int | None = Field(None, description="Offset for next page (None if no more)")


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


class UnassignedCountResponse(BaseModel):
    """Response model for unassigned actions count.

    Attributes:
        unassigned_count: Number of actions not assigned to any project
        min_required: Minimum actions required for autogeneration
        can_autogenerate: Whether autogen is available
    """

    unassigned_count: int = Field(..., description="Actions without project assignment")
    min_required: int = Field(..., description="Minimum actions for autogeneration")
    can_autogenerate: bool = Field(..., description="Whether autogen threshold is met")


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
# Activities by Date (Heatmap Tooltip)
# =============================================================================


class ActivityItem(BaseModel):
    """Individual activity item for a given date."""

    id: str = Field(..., description="Item ID")
    type: str = Field(
        ...,
        description="Activity type (session, action_completed, action_started, mentor_session, planned_start, planned_due)",
    )
    title: str = Field(..., description="Activity title/description")
    subtitle: str | None = Field(
        None, description="Optional subtitle (e.g. session problem statement)"
    )
    url: str | None = Field(None, description="Link to detail page")
    timestamp: str | None = Field(None, description="ISO timestamp")


class DateActivitiesResponse(BaseModel):
    """Response model for activities on a specific date."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    activities: list[ActivityItem] = Field(..., description="Activities on this date")
    total: int = Field(..., description="Total number of activities")


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
# Kanban Column Preferences
# =============================================================================

# Valid statuses for kanban columns
VALID_KANBAN_STATUSES = {
    ActionStatus.TODO,
    ActionStatus.IN_PROGRESS,
    ActionStatus.BLOCKED,
    ActionStatus.IN_REVIEW,
    ActionStatus.DONE,
    ActionStatus.CANCELLED,
    ActionStatus.FAILED,
    ActionStatus.ABANDONED,
    ActionStatus.REPLANNED,
}


class KanbanColumn(BaseModel):
    """Single kanban column configuration.

    Attributes:
        id: Column identifier (must be a valid ActionStatus)
        title: Display title for the column
        color: Optional hex color code for the column
    """

    id: str = Field(..., description="Column ID (ActionStatus value)")
    title: str = Field(..., min_length=1, max_length=50, description="Display title")
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color")


class KanbanColumnsResponse(BaseModel):
    """Response for kanban columns preference endpoint."""

    columns: list[KanbanColumn] = Field(..., description="User's kanban columns")


class KanbanColumnsUpdate(BaseModel):
    """Request model for updating kanban columns.

    Attributes:
        columns: List of column configurations (1-8 columns, unique IDs)
    """

    columns: list[KanbanColumn] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Kanban columns (1-8, unique IDs)",
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


# =============================================================================
# PII Detection Models
# =============================================================================


class PiiType(str, Enum):
    """Types of PII that can be detected in datasets."""

    EMAIL = "email"
    SSN = "ssn"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"


class PiiWarning(BaseModel):
    """Warning about potential PII detected in a column.

    Attributes:
        column_name: Name of the column containing potential PII
        pii_type: Type of PII detected
        confidence: Confidence score (0.0-1.0)
        sample_values: Masked sample values showing the pattern
        match_count: Number of matches found in sample
    """

    column_name: str = Field(..., description="Column name with potential PII")
    pii_type: PiiType = Field(..., description="Type of PII detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    sample_values: list[str] = Field(
        default_factory=list, description="Masked sample values (max 3)"
    )
    match_count: int = Field(..., ge=0, description="Number of matches in sample")


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
        warnings: CSV validation warnings (e.g., injection patterns detected)
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
    warnings: list[str] | None = Field(None, description="CSV validation warnings")
    pii_warnings: list[PiiWarning] | None = Field(
        None, description="Potential PII detected in columns"
    )
    pii_acknowledged_at: str | None = Field(
        None, description="Timestamp when user acknowledged PII warning (ISO)"
    )


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
        has_more: Whether more datasets exist beyond current page
        next_offset: Offset for next page (None if no more pages)
    """

    datasets: list[DatasetResponse] = Field(..., description="List of datasets")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")
    has_more: bool = Field(..., description="Whether more datasets exist beyond current page")
    next_offset: int | None = Field(None, description="Offset for next page (None if no more)")


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
# Dataset Favourites & Reports Models
# =============================================================================


class FavouriteType(str, Enum):
    """Type of favourited item."""

    chart = "chart"
    insight = "insight"
    message = "message"


class DatasetFavouriteCreate(BaseModel):
    """Request to create a favourite.

    Attributes:
        favourite_type: Type of item being favourited
        analysis_id: ID of analysis (for chart type)
        message_id: ID of message (for message type)
        insight_data: Insight data (for insight type from DataInsightsPanel)
        title: Display title
        content: Text content/description
        chart_spec: Chart specification if applicable
        figure_json: Plotly figure JSON if applicable
        user_note: Optional user annotation
    """

    favourite_type: FavouriteType = Field(..., description="Type of favourited item")
    analysis_id: str | None = Field(None, description="Analysis ID for chart favourites")
    message_id: str | None = Field(None, description="Message ID for message favourites")
    insight_data: dict[str, Any] | None = Field(
        None, description="Insight data for insight favourites"
    )
    title: str | None = Field(None, max_length=500, description="Display title")
    content: str | None = Field(None, max_length=5000, description="Text content")
    chart_spec: dict[str, Any] | None = Field(None, description="Chart specification")
    figure_json: dict[str, Any] | None = Field(None, description="Plotly figure JSON")
    user_note: str | None = Field(None, max_length=2000, description="User annotation")


class DatasetFavouriteUpdate(BaseModel):
    """Request to update a favourite."""

    user_note: str | None = Field(None, max_length=2000, description="User annotation")
    sort_order: int | None = Field(None, ge=0, description="Sort order")


class DatasetFavouriteResponse(BaseModel):
    """Response model for a favourite.

    Attributes:
        id: Favourite UUID
        dataset_id: Dataset UUID
        favourite_type: Type of favourited item
        analysis_id: Analysis ID if chart type
        message_id: Message ID if message type
        insight_data: Insight data if insight type
        title: Display title
        content: Text content
        chart_spec: Chart specification
        figure_json: Plotly figure JSON
        user_note: User annotation
        sort_order: Sort order
        created_at: Creation timestamp
    """

    id: str = Field(..., description="Favourite UUID")
    dataset_id: str = Field(..., description="Dataset UUID")
    favourite_type: FavouriteType = Field(..., description="Type of favourited item")
    analysis_id: str | None = Field(None, description="Analysis ID")
    message_id: str | None = Field(None, description="Message ID")
    insight_data: dict[str, Any] | None = Field(None, description="Insight data")
    title: str | None = Field(None, description="Display title")
    content: str | None = Field(None, description="Text content")
    chart_spec: dict[str, Any] | None = Field(None, description="Chart specification")
    figure_json: dict[str, Any] | None = Field(None, description="Plotly figure JSON")
    user_note: str | None = Field(None, description="User annotation")
    sort_order: int = Field(0, description="Sort order")
    created_at: str = Field(..., description="Creation timestamp")


class DatasetFavouriteListResponse(BaseModel):
    """Response model for listing favourites."""

    favourites: list[DatasetFavouriteResponse] = Field(..., description="List of favourites")
    total: int = Field(..., description="Total count")


class ReportSection(BaseModel):
    """A section within a generated report."""

    section_type: str = Field(
        ...,
        description="Section type: executive_summary|key_findings|analysis|recommendations|data_notes",
    )
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content (markdown)")
    chart_refs: list[str] = Field(
        default_factory=list, description="IDs of charts referenced in this section"
    )


class DatasetReportCreate(BaseModel):
    """Request to generate a report."""

    favourite_ids: list[str] | None = Field(
        None, description="Specific favourites to include (all if omitted)"
    )
    title: str | None = Field(
        None, max_length=255, description="Report title (auto-generated if omitted)"
    )


class DatasetReportResponse(BaseModel):
    """Response model for a generated report.

    Attributes:
        id: Report UUID
        dataset_id: Dataset UUID (None if dataset was deleted)
        title: Report title
        executive_summary: Brief executive summary
        sections: Structured report sections
        favourite_ids: IDs of favourites used
        model_used: LLM model used for generation
        tokens_used: Tokens consumed
        created_at: Creation timestamp
    """

    id: str = Field(..., description="Report UUID")
    dataset_id: str | None = Field(None, description="Dataset UUID (null if dataset deleted)")
    title: str = Field(..., description="Report title")
    executive_summary: str | None = Field(None, description="Executive summary")
    sections: list[ReportSection] = Field(..., description="Report sections")
    favourite_ids: list[str] = Field(..., description="Favourites used in report")
    favourites: list[DatasetFavouriteResponse] | None = Field(
        None, description="Full favourite data for rendering"
    )
    model_used: str | None = Field(None, description="LLM model used")
    tokens_used: int | None = Field(None, description="Tokens consumed")
    created_at: str = Field(..., description="Creation timestamp")


class DatasetReportListResponse(BaseModel):
    """Response model for listing reports."""

    reports: list[DatasetReportResponse] = Field(..., description="List of reports")
    total: int = Field(..., description="Total count")


class AllReportItem(BaseModel):
    """Report item with dataset information for cross-dataset listing.

    Attributes:
        id: Report UUID
        dataset_id: Dataset UUID (None if dataset was deleted)
        dataset_name: Dataset name for display (None if deleted)
        title: Report title
        executive_summary: Brief executive summary
        created_at: Creation timestamp
    """

    id: str = Field(..., description="Report UUID")
    dataset_id: str | None = Field(None, description="Dataset UUID (null if dataset deleted)")
    dataset_name: str | None = Field(None, description="Dataset name (null if deleted)")
    title: str = Field(..., description="Report title")
    executive_summary: str | None = Field(None, description="Executive summary")
    created_at: str = Field(..., description="Creation timestamp")


class AllReportsListResponse(BaseModel):
    """Response model for listing all reports across datasets."""

    reports: list[AllReportItem] = Field(..., description="List of reports with dataset info")
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
    cache_hit_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall cache hit rate (0.0-1.0)"
    )
    prompt_cache_hit_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Anthropic prompt cache effectiveness (0.0-1.0)",
    )
    total_saved: float = Field(default=0.0, ge=0.0, description="Cost savings from caching (USD)")


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


class ApplyPromoToUserRequest(BaseModel):
    """Admin request to apply a promo code to a user.

    Attributes:
        user_id: Target user ID
        code: Promo code to apply
    """

    user_id: str = Field(..., description="Target user ID (UUID)")
    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Promo code to apply",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"user_id": "550e8400-e29b-41d4-a716-446655440000", "code": "WELCOME10"},
            ]
        }
    }

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Normalize promo code."""
        return v.strip().upper()


class UserPromotionBrief(BaseModel):
    """Brief promotion info for user lists."""

    id: str = Field(..., description="User promotion ID")
    promotion_id: str = Field(..., description="Promotion ID")
    promotion_code: str = Field(..., description="Promo code")
    promotion_type: str = Field(..., description="Promotion type")
    promotion_value: float = Field(..., description="Promotion value")
    status: str = Field(..., description="Status: active, exhausted, expired")
    applied_at: datetime = Field(..., description="When applied")
    deliberations_remaining: int | None = Field(None, description="Remaining credits")
    discount_applied: float | None = Field(None, description="Discount amount")


class UserWithPromotionsResponse(BaseModel):
    """User with their active promotions."""

    user_id: str = Field(..., description="User ID")
    email: str | None = Field(None, description="User email")
    promotions: list[UserPromotionBrief] = Field(
        default_factory=list, description="Active promotions"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "promotions": [
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440001",
                            "promotion_id": "770e8400-e29b-41d4-a716-446655440002",
                            "promotion_code": "WELCOME10",
                            "promotion_type": "percentage_discount",
                            "promotion_value": 10.0,
                            "status": "active",
                            "applied_at": "2025-01-15T10:30:00Z",
                            "deliberations_remaining": None,
                            "discount_applied": 10.0,
                        }
                    ],
                }
            ]
        }
    }


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


class FeedbackCreate(HoneypotMixin):
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
# User Ratings (Thumbs Up/Down) Models
# ============================================================================


class RatingEntityType:
    """Valid entity types for ratings."""

    MEETING = "meeting"
    ACTION = "action"


class RatingCreate(BaseModel):
    """Request model for submitting a rating.

    Attributes:
        entity_type: Type of entity being rated ('meeting' or 'action')
        entity_id: UUID of the entity
        rating: -1 (thumbs down) or 1 (thumbs up)
        comment: Optional comment explaining the rating
    """

    entity_type: str = Field(
        ...,
        description="Type of entity being rated ('meeting' or 'action')",
    )
    entity_id: str = Field(
        ...,
        min_length=1,
        description="UUID of the entity being rated",
    )
    rating: int = Field(
        ...,
        ge=-1,
        le=1,
        description="Rating value: -1 (thumbs down) or 1 (thumbs up)",
    )
    comment: str | None = Field(
        None,
        max_length=1000,
        description="Optional comment explaining the rating",
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type."""
        valid_types = {RatingEntityType.MEETING, RatingEntityType.ACTION}
        if v not in valid_types:
            raise ValueError(f"Invalid entity_type. Must be one of: {valid_types}")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        """Validate rating is -1 or 1."""
        if v not in (-1, 1):
            raise ValueError("Rating must be -1 (thumbs down) or 1 (thumbs up)")
        return v


class RatingResponse(BaseModel):
    """Response model for a rating.

    Attributes:
        id: Rating UUID
        user_id: User who submitted the rating
        entity_type: Type of entity rated
        entity_id: UUID of the rated entity
        rating: Rating value (-1 or 1)
        comment: Optional comment
        created_at: When the rating was created/updated
    """

    id: str = Field(..., description="Rating UUID")
    user_id: str = Field(..., description="User ID")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity UUID")
    rating: int = Field(..., description="Rating value (-1 or 1)")
    comment: str | None = Field(None, description="Optional comment")
    created_at: datetime = Field(..., description="Creation timestamp")


class RatingMetrics(BaseModel):
    """Aggregated rating metrics.

    Attributes:
        period_days: Number of days in the period
        total: Total ratings in period
        thumbs_up: Count of positive ratings
        thumbs_down: Count of negative ratings
        thumbs_up_pct: Percentage of positive ratings
        by_type: Breakdown by entity type
    """

    period_days: int = Field(..., description="Days in period")
    total: int = Field(..., description="Total ratings")
    thumbs_up: int = Field(..., description="Positive ratings count")
    thumbs_down: int = Field(..., description="Negative ratings count")
    thumbs_up_pct: float = Field(..., description="Positive rating percentage")
    by_type: dict[str, dict[str, int]] = Field(..., description="Breakdown by entity type")


class RatingTrendItem(BaseModel):
    """Daily rating trend data point.

    Attributes:
        date: Date (ISO format)
        up: Thumbs up count
        down: Thumbs down count
        total: Total ratings
    """

    date: str = Field(..., description="Date (ISO format)")
    up: int = Field(..., description="Thumbs up count")
    down: int = Field(..., description="Thumbs down count")
    total: int = Field(..., description="Total ratings")


class NegativeRatingItem(BaseModel):
    """A negative rating with context for admin triage.

    Attributes:
        id: Rating UUID
        user_id: User who rated
        user_email: User's email
        entity_type: Type of entity
        entity_id: Entity UUID
        entity_title: Title/name of the entity
        comment: Optional comment
        created_at: When rated
    """

    id: str = Field(..., description="Rating UUID")
    user_id: str = Field(..., description="User ID")
    user_email: str | None = Field(None, description="User email")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity UUID")
    entity_title: str | None = Field(None, description="Entity title")
    comment: str | None = Field(None, description="Comment")
    created_at: datetime = Field(..., description="Timestamp")


class NegativeRatingsResponse(BaseModel):
    """Response model for negative ratings list.

    Attributes:
        items: List of negative ratings
    """

    items: list[NegativeRatingItem] = Field(..., description="Negative ratings")


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
# Published Decisions Models (SEO Decision Library)
# ============================================================================


DECISION_CATEGORIES = [
    "hiring",
    "pricing",
    "fundraising",
    "marketing",
    "strategy",
    "product",
    "operations",
    "growth",
]


class DecisionStatus:
    """Valid decision statuses."""

    DRAFT = "draft"
    PUBLISHED = "published"


class FounderContextModel(BaseModel):
    """Founder context for decision pages."""

    stage: str | None = Field(None, description="Business stage (e.g., '£50-200k ARR')")
    constraints: list[str] | None = Field(None, description="Key constraints")
    situation: str | None = Field(None, description="Current situation description")


class ExpertPerspectiveModel(BaseModel):
    """Expert perspective from deliberation."""

    persona_name: str = Field(..., description="Expert name (e.g., 'Growth Operator')")
    persona_code: str | None = Field(None, description="Persona code if from session")
    quote: str = Field(..., description="Expert's viewpoint/recommendation")


class FAQModel(BaseModel):
    """FAQ item for schema markup."""

    question: str = Field(..., description="FAQ question")
    answer: str = Field(..., description="FAQ answer")


class DecisionCreate(BaseModel):
    """Request model for creating a published decision."""

    title: str = Field(..., min_length=10, max_length=200, description="Decision question (H1)")
    category: str = Field(..., description="Category: hiring, pricing, fundraising, etc.")
    founder_context: FounderContextModel = Field(..., description="Founder context for display")
    session_id: str | None = Field(None, description="Source session UUID (optional)")
    meta_description: str | None = Field(None, max_length=300, description="SEO description")
    expert_perspectives: list[ExpertPerspectiveModel] | None = Field(
        None, description="Expert viewpoints"
    )
    synthesis: str | None = Field(None, description="Board synthesis/recommendation")
    faqs: list[FAQModel] | None = Field(None, description="FAQ pairs for schema")
    featured_image_url: str | None = Field(None, max_length=500, description="OG image URL")
    seo_keywords: list[str] | None = Field(None, description="SEO keywords array")
    meta_title: str | None = Field(
        None, max_length=100, description="SEO-optimized title (50-60 chars)"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category."""
        if v not in DECISION_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {DECISION_CATEGORIES}")
        return v


class DecisionUpdate(BaseModel):
    """Request model for updating a published decision."""

    title: str | None = Field(None, min_length=10, max_length=200, description="Decision question")
    category: str | None = Field(None, description="Category")
    slug: str | None = Field(None, max_length=100, description="URL slug (rename)")
    meta_description: str | None = Field(None, max_length=300, description="SEO description")
    founder_context: FounderContextModel | None = Field(None, description="Founder context")
    expert_perspectives: list[ExpertPerspectiveModel] | None = Field(
        None, description="Expert viewpoints"
    )
    synthesis: str | None = Field(None, description="Synthesis/recommendation")
    faqs: list[FAQModel] | None = Field(None, description="FAQ pairs")
    related_decision_ids: list[str] | None = Field(None, description="Related decision UUIDs")
    status: str | None = Field(None, description="draft or published")
    featured_image_url: str | None = Field(None, max_length=500, description="OG image URL")
    seo_keywords: list[str] | None = Field(None, description="SEO keywords array")
    meta_title: str | None = Field(
        None, max_length=100, description="SEO-optimized title (50-60 chars)"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Validate category if provided."""
        if v is None:
            return v
        if v not in DECISION_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {DECISION_CATEGORIES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status if provided."""
        if v is None:
            return v
        valid = {DecisionStatus.DRAFT, DecisionStatus.PUBLISHED}
        if v not in valid:
            raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class DecisionResponse(BaseModel):
    """Response model for a published decision."""

    id: str = Field(..., description="Decision UUID")
    session_id: str | None = Field(None, description="Source session UUID")
    category: str = Field(..., description="Category")
    slug: str = Field(..., description="URL slug")
    title: str = Field(..., description="Decision question (H1)")
    meta_description: str | None = Field(None, description="SEO description")
    founder_context: dict[str, Any] | None = Field(None, description="Founder context")
    expert_perspectives: list[dict[str, Any]] | None = Field(None, description="Expert viewpoints")
    synthesis: str | None = Field(None, description="Board synthesis")
    faqs: list[dict[str, Any]] | None = Field(None, description="FAQ pairs")
    related_decision_ids: list[str] | None = Field(None, description="Related decision UUIDs")
    status: str = Field(..., description="draft or published")
    published_at: datetime | None = Field(None, description="Publication datetime")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    view_count: int = Field(default=0, description="View count")
    click_through_count: int = Field(default=0, description="CTA click count")
    homepage_featured: bool = Field(default=False, description="Featured on homepage")
    homepage_order: int | None = Field(None, description="Homepage display order")
    featured_image_url: str | None = Field(None, description="OG image URL")
    seo_keywords: list[str] | None = Field(None, description="SEO keywords array")
    reading_time_minutes: int | None = Field(None, description="Reading time in minutes")
    meta_title: str | None = Field(None, description="SEO-optimized title (50-60 chars)")


class DecisionListResponse(BaseModel):
    """Response model for decision list."""

    decisions: list[DecisionResponse] = Field(..., description="List of decisions")
    total: int = Field(..., description="Total count")


class DecisionPublicResponse(BaseModel):
    """Public response model for decision page (no admin fields)."""

    category: str = Field(..., description="Category")
    slug: str = Field(..., description="URL slug")
    title: str = Field(..., description="Decision question (H1)")
    meta_description: str | None = Field(None, description="SEO description")
    founder_context: dict[str, Any] | None = Field(None, description="Founder context")
    expert_perspectives: list[dict[str, Any]] | None = Field(None, description="Expert viewpoints")
    synthesis: str | None = Field(None, description="Board synthesis")
    faqs: list[dict[str, Any]] | None = Field(None, description="FAQ pairs")
    published_at: datetime | None = Field(None, description="Publication datetime")
    featured_image_url: str | None = Field(None, description="OG image URL")
    seo_keywords: list[str] | None = Field(None, description="SEO keywords array")
    reading_time_minutes: int | None = Field(None, description="Reading time in minutes")
    meta_title: str | None = Field(None, description="SEO-optimized title (50-60 chars)")


class CategoryWithCount(BaseModel):
    """Category with decision count."""

    category: str = Field(..., description="Category name")
    count: int = Field(..., description="Number of published decisions")


class CategoriesResponse(BaseModel):
    """Response model for category listing."""

    categories: list[CategoryWithCount] = Field(..., description="Categories with counts")


class FeaturedDecisionResponse(BaseModel):
    """Public response model for featured homepage decisions."""

    id: str = Field(..., description="Decision UUID")
    category: str = Field(..., description="Category")
    slug: str = Field(..., description="URL slug")
    title: str = Field(..., description="Decision question")
    meta_description: str | None = Field(None, description="SEO description")
    synthesis: str | None = Field(None, description="Board synthesis/recommendation")
    homepage_order: int | None = Field(None, description="Display order")


class FeaturedDecisionsResponse(BaseModel):
    """Response model for featured decisions list."""

    decisions: list[FeaturedDecisionResponse] = Field(..., description="Featured decisions")


class FeaturedOrderRequest(BaseModel):
    """Request model for reordering featured decisions."""

    decision_ids: list[str] = Field(
        ..., min_length=1, max_length=10, description="Ordered list of decision UUIDs"
    )


class SEOBackfillResponse(BaseModel):
    """Response model for SEO backfill operation."""

    enriched: int = Field(..., description="Number of decisions enriched")
    skipped: int = Field(..., description="Number of decisions skipped (already had SEO)")
    failed: int = Field(..., description="Number of decisions that failed enrichment")


class DecisionGenerateRequest(BaseModel):
    """Request model for generating decision from question."""

    question: str = Field(
        ..., min_length=10, max_length=500, description="Decision question to deliberate"
    )
    category: str = Field(..., description="Category for the decision")
    founder_context: FounderContextModel = Field(..., description="Founder context to inject")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category."""
        if v not in DECISION_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {DECISION_CATEGORIES}")
        return v


# ============================================================================
# Decision Topic Bank Models
# ============================================================================


class TopicBankResponse(BaseModel):
    """Response model for a banked decision topic."""

    id: str = Field(..., description="Topic UUID")
    title: str = Field(..., description="Decision-framed title")
    description: str = Field(..., description="2-3 sentence dilemma summary")
    category: str = Field(..., description="Decision category")
    keywords: list[str] = Field(default_factory=list, description="SEO target keywords")
    seo_score: float = Field(..., description="0-1 search intent signal")
    reasoning: str = Field(..., description="Why this topic should be considered")
    bo1_alignment: str = Field(..., description="How Bo1 features solve this")
    source: str = Field(..., description="Research source")
    status: str = Field(..., description="banked|used|dismissed")
    researched_at: datetime | None = Field(None, description="When topic was researched")
    used_at: datetime | None = Field(None, description="When topic was used as draft")


class TopicBankListResponse(BaseModel):
    """Response model for topic bank listing."""

    topics: list[TopicBankResponse] = Field(..., description="Banked topics")
    total: int = Field(..., description="Total count")


class TopicProposalResponse(BaseModel):
    """Response model for a proposed blog topic."""

    title: str = Field(..., description="Proposed topic title")
    rationale: str = Field(..., description="Why this topic is suggested")
    suggested_keywords: list[str] = Field(..., description="SEO keywords")
    source: str = Field(..., description="Source: web-research, llm-generated")


class TopicProposalsResponse(BaseModel):
    """Response model for topic proposals."""

    topics: list[TopicProposalResponse] = Field(..., description="Proposed topics")


# ============================================================================
# Generic Response Models
# ============================================================================


class MessageResponse(BaseModel):
    """Generic response for endpoints that return a simple status/message.

    Used for: task status updates, operation confirmations, etc.
    """

    status: str = Field(..., description="Operation status (e.g., 'success')")
    message: str = Field(..., description="Human-readable message")


class CheckpointStateResponse(BaseModel):
    """Response model for session checkpoint state (resume capability).

    Used by /sessions/{id}/checkpoint-state to show resumable progress.
    """

    session_id: str = Field(..., description="Session identifier")
    completed_sub_problems: int = Field(0, description="Number of completed sub-problems")
    total_sub_problems: int | None = Field(None, description="Total sub-problems in session")
    last_checkpoint_at: datetime | None = Field(None, description="When last checkpoint was saved")
    can_resume: bool = Field(False, description="Whether session can be resumed from checkpoint")
    status: str = Field(..., description="Current session status")
    phase: str | None = Field(None, description="Current session phase")


class WhitelistCheckResponse(BaseModel):
    """Response for whitelist/beta access check endpoints."""

    is_whitelisted: bool = Field(..., description="Whether the email is whitelisted")


# ============================================================================
# Action Operation Response Models
# ============================================================================


class ActionStartedResponse(BaseModel):
    """Response for starting an action."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the started action")


class ActionCompleteRequest(BaseModel):
    """Request model for completing an action with optional post-mortem.

    Attributes:
        lessons_learned: Optional reflection on lessons learned (max 500 chars)
        went_well: Optional reflection on what went well (max 500 chars)
    """

    lessons_learned: str | None = Field(
        None,
        max_length=500,
        description="Reflection on lessons learned from this action",
    )
    went_well: str | None = Field(
        None,
        max_length=500,
        description="Reflection on what went well during this action",
    )


class ActionCompletedResponse(BaseModel):
    """Response for completing an action."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the completed action")
    unblocked_actions: list[str] = Field(
        default_factory=list, description="UUIDs of actions auto-unblocked by this completion"
    )
    generated_project: dict[str, str] | None = Field(
        None, description="Auto-generated project info (id, name) if created"
    )


class GeneratedProjectInfo(BaseModel):
    """Project info returned when auto-generated from action."""

    id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")


class ActionStatusUpdatedResponse(BaseModel):
    """Response for updating action status."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the action")
    status: str = Field(..., description="New status value")
    unblocked_actions: list[str] = Field(
        default_factory=list, description="UUIDs of actions auto-unblocked"
    )
    generated_project: GeneratedProjectInfo | None = Field(
        None, description="Auto-generated project info if created"
    )


class RelatedAction(BaseModel):
    """Summary of a related action for replan context."""

    id: str = Field(..., description="Action UUID")
    title: str = Field(..., description="Action title")
    status: str = Field(..., description="Action status")


class ActionReplanContextResponse(BaseModel):
    """Response for getting replan context for a cancelled action."""

    action_id: str = Field(..., description="UUID of the action")
    action_title: str = Field(..., description="Title of the action")
    problem_statement: str = Field(..., description="Problem statement from parent session")
    failure_reason_text: str = Field(..., description="Original cancellation reason")
    failure_reason_category: str = Field(
        ..., description="Category: blocker/scope_creep/dependency/unknown"
    )
    related_actions: list[RelatedAction] = Field(
        default_factory=list, description="Related actions from same session/project"
    )
    parent_session_id: str | None = Field(None, description="UUID of parent session")
    business_context: dict[str, Any] | None = Field(None, description="User's business context")


class ActionDeletedResponse(BaseModel):
    """Response for soft-deleting an action."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the deleted action")


class DependencyAddedResponse(BaseModel):
    """Response for adding a dependency."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the action")
    depends_on_action_id: str = Field(..., description="UUID of the dependency target")
    auto_blocked: bool = Field(..., description="Whether action was auto-blocked")
    blocking_reason: str | None = Field(None, description="Blocking reason if auto-blocked")


class DependencyRemovedResponse(BaseModel):
    """Response for removing a dependency."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the action")
    depends_on_id: str = Field(..., description="UUID of the removed dependency target")
    auto_unblocked: bool = Field(..., description="Whether action was auto-unblocked")
    new_status: str | None = Field(None, description="New status if changed")


class ActionBlockedResponse(BaseModel):
    """Response for blocking an action."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the action")
    blocking_reason: str = Field(..., description="Reason for blocking")
    auto_unblock: bool = Field(..., description="Whether auto-unblock is enabled")


class IncompleteDependencyInfo(BaseModel):
    """Info about an incomplete dependency (warning in unblock response)."""

    id: str = Field(..., description="Dependency action UUID")
    title: str = Field(..., description="Dependency action title")


class ActionUnblockedResponse(BaseModel):
    """Response for unblocking an action."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the action")
    new_status: str = Field(..., description="New status after unblocking")
    warning: str | None = Field(None, description="Warning about incomplete dependencies")
    incomplete_dependencies: list[IncompleteDependencyInfo] | None = Field(
        None, description="List of incomplete dependencies if warning present"
    )


class ReminderSnoozedResponse(BaseModel):
    """Response for snoozing an action reminder."""

    message: str = Field(..., description="Success message")
    action_id: str = Field(..., description="UUID of the action")
    snooze_days: int = Field(..., description="Number of days snoozed")


# =============================================================================
# Unblock Suggestions
# =============================================================================


class UnblockSuggestionModel(BaseModel):
    """A single suggestion for unblocking a blocked action."""

    approach: str = Field(
        ...,
        description="The suggested approach to unblock",
        max_length=500,
        examples=["Break the task into smaller sub-tasks"],
    )
    rationale: str = Field(
        ...,
        description="Why this approach might work",
        max_length=500,
        examples=["Large tasks often get blocked because they're overwhelming"],
    )
    effort_level: str = Field(
        ...,
        description="Estimated effort level",
        pattern="^(low|medium|high)$",
        examples=["low"],
    )


class UnblockPathsResponse(BaseModel):
    """Response containing suggested paths to unblock an action."""

    action_id: str = Field(..., description="UUID of the blocked action")
    suggestions: list[UnblockSuggestionModel] = Field(
        ...,
        description="List of 3-5 suggestions to unblock",
        min_length=1,
        max_length=5,
    )


class EscalateBlockerRequest(BaseModel):
    """Request model for escalating a blocked action to a meeting."""

    include_suggestions: bool = Field(
        default=True,
        description="Include prior unblock suggestions in meeting context",
    )


class EscalateBlockerResponse(BaseModel):
    """Response model for blocker escalation."""

    session_id: str = Field(..., description="ID of the created meeting session")
    redirect_url: str = Field(..., description="URL to redirect to the meeting")


class SSEEvent(BaseModel):
    """A single SSE event from history."""

    event_type: str = Field(..., description="Type of event")
    data: dict[str, Any] = Field(..., description="Event payload")
    sequence: int = Field(default=0, description="Event sequence number")


class EventHistoryResponse(BaseModel):
    """Response for getting session event history."""

    session_id: str = Field(..., description="Session UUID")
    events: list[dict[str, Any]] = Field(..., description="List of events")
    count: int = Field(..., description="Number of events returned")
    last_event_id: str | None = Field(None, description="Last event ID for resume support")
    can_resume: bool = Field(..., description="Whether session can be resumed")


# =============================================================================
# Meeting Templates
# =============================================================================


class MeetingTemplate(BaseModel):
    """Response model for a meeting template.

    Templates pre-populate problem statements and suggest context for common
    decision scenarios like product launches, pricing changes, etc.
    """

    id: str = Field(..., description="Template UUID")
    name: str = Field(..., description="Display name")
    slug: str = Field(..., description="URL-friendly identifier")
    description: str = Field(..., description="Short description for gallery")
    category: str = Field(..., description="Template category (strategy, pricing, product, growth)")
    problem_statement_template: str = Field(
        ..., description="Pre-filled problem statement with placeholders"
    )
    context_hints: list[str] = Field(
        default_factory=list, description="Suggested context fields to fill"
    )
    suggested_persona_traits: list[str] = Field(
        default_factory=list, description="Traits for persona hints"
    )
    is_builtin: bool = Field(default=False, description="True for system templates")
    version: int = Field(default=1, description="Template version")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class MeetingTemplateCreate(BaseModel):
    """Request model for creating a meeting template (admin only).

    Attributes:
        name: Display name (2-100 chars)
        slug: URL-friendly identifier (2-50 chars, alphanumeric + hyphens)
        description: Gallery description (10-500 chars)
        category: Template category
        problem_statement_template: Pre-filled problem statement with [placeholders]
        context_hints: Suggested context fields
        suggested_persona_traits: Traits for persona generation
    """

    name: str = Field(..., min_length=2, max_length=100, description="Display name")
    slug: str = Field(
        ...,
        min_length=2,
        max_length=50,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly identifier (lowercase, hyphens allowed)",
    )
    description: str = Field(..., min_length=10, max_length=500, description="Gallery description")
    category: str = Field(
        ...,
        pattern=r"^(strategy|pricing|product|growth|operations|team)$",
        description="Template category",
    )
    problem_statement_template: str = Field(
        ...,
        min_length=20,
        max_length=2000,
        description="Problem statement with [placeholders]",
    )
    context_hints: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Suggested context fields (max 20)",
    )
    suggested_persona_traits: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Persona trait hints (max 10)",
    )

    @field_validator("context_hints")
    @classmethod
    def validate_context_hints(cls, v: list[str]) -> list[str]:
        """Validate context hints are reasonable."""
        if len(v) > 20:
            raise ValueError("Maximum 20 context hints allowed")
        for hint in v:
            if len(hint) > 100:
                raise ValueError("Context hint too long (max 100 chars)")
        return v

    @field_validator("suggested_persona_traits")
    @classmethod
    def validate_persona_traits(cls, v: list[str]) -> list[str]:
        """Validate persona traits are reasonable."""
        if len(v) > 10:
            raise ValueError("Maximum 10 persona traits allowed")
        for trait in v:
            if len(trait) > 50:
                raise ValueError("Persona trait too long (max 50 chars)")
        return v


class MeetingTemplateUpdate(BaseModel):
    """Request model for updating a meeting template (admin only)."""

    name: str | None = Field(None, min_length=2, max_length=100, description="Updated name")
    description: str | None = Field(
        None, min_length=10, max_length=500, description="Updated description"
    )
    category: str | None = Field(
        None,
        pattern=r"^(strategy|pricing|product|growth|operations|team)$",
        description="Updated category",
    )
    problem_statement_template: str | None = Field(
        None,
        min_length=20,
        max_length=2000,
        description="Updated problem statement",
    )
    context_hints: list[str] | None = Field(None, description="Updated context hints")
    suggested_persona_traits: list[str] | None = Field(None, description="Updated traits")
    is_active: bool | None = Field(None, description="Activate/deactivate template")


class MeetingTemplateListResponse(BaseModel):
    """Response model for template gallery."""

    templates: list[MeetingTemplate] = Field(..., description="List of templates")
    total: int = Field(..., description="Total count")
    categories: list[str] = Field(..., description="Available categories for filtering")


# =============================================================================
# Dataset Insight Models (Business Intelligence)
# =============================================================================


class BusinessDomain(str, Enum):
    """Detected business domain of the dataset."""

    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    SERVICES = "services"
    MARKETING = "marketing"
    FINANCE = "finance"
    OPERATIONS = "operations"
    HR = "hr"
    PRODUCT = "product"
    UNKNOWN = "unknown"


class SemanticColumnType(str, Enum):
    """Business-semantic column types (beyond technical types)."""

    # Financial
    REVENUE = "revenue"
    PRICE = "price"
    COST = "cost"
    MARGIN = "margin"
    DISCOUNT = "discount"

    # Identifiers
    CUSTOMER_ID = "customer_id"
    ORDER_ID = "order_id"
    PRODUCT_ID = "product_id"
    TRANSACTION_ID = "transaction_id"

    # Contact
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    COMPANY = "company"

    # Temporal
    ORDER_DATE = "order_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    EVENT_DATE = "event_date"

    # Quantities
    QUANTITY = "quantity"
    COUNT = "count"
    UNITS = "units"

    # Rates
    CONVERSION_RATE = "conversion_rate"
    PERCENTAGE = "percentage"
    RATE = "rate"

    # Categories
    STATUS = "status"
    CATEGORY = "category"
    TYPE = "type"
    CHANNEL = "channel"
    SOURCE = "source"

    # Location
    COUNTRY = "country"
    REGION = "region"
    CITY = "city"
    ADDRESS = "address"

    # Product
    PRODUCT_NAME = "product_name"
    SKU = "sku"
    DESCRIPTION = "description"

    # Generic
    METRIC = "metric"
    DIMENSION = "dimension"
    UNKNOWN = "unknown"


class InsightSeverity(str, Enum):
    """Severity/importance of an insight."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightType(str, Enum):
    """Category of insight."""

    TREND = "trend"
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    BENCHMARK = "benchmark"


class DataIdentity(BaseModel):
    """What this dataset represents in business terms."""

    domain: BusinessDomain = Field(description="Business domain (e-commerce, SaaS, etc.)")
    confidence: float = Field(ge=0, le=1, description="Confidence in domain detection")
    entity_type: str = Field(description="What the rows represent (orders, customers, etc.)")
    description: str = Field(description="Plain English description of the data")
    time_range: str | None = Field(
        default=None, description="Detected time span if date columns exist"
    )


class HeadlineMetric(BaseModel):
    """Key metric displayed prominently."""

    label: str = Field(description="Metric name (e.g., 'Total Revenue')")
    value: str = Field(description="Formatted value (e.g., '$127,450')")
    context: str | None = Field(default=None, description="Additional context")
    trend: str | None = Field(default=None, description="Trend indicator")
    is_good: bool | None = Field(default=None, description="Whether this is positive/negative")


class Insight(BaseModel):
    """A single business insight."""

    type: InsightType
    severity: InsightSeverity
    headline: str = Field(description="Short headline")
    detail: str = Field(description="Full explanation")
    metric: str | None = Field(default=None, description="Related metric if applicable")
    action: str | None = Field(default=None, description="Suggested action")


class DataQualityScore(BaseModel):
    """Assessment of data quality and completeness."""

    overall_score: int = Field(ge=0, le=100, description="Overall quality score 0-100")
    completeness: int = Field(ge=0, le=100, description="Percentage of non-null values")
    consistency: int = Field(ge=0, le=100, description="Data consistency score")
    freshness: int | None = Field(default=None, ge=0, le=100, description="How recent the data is")
    issues: list[str] = Field(default_factory=list, description="Specific quality issues found")
    missing_data: list[str] = Field(
        default_factory=list, description="Important data that's missing"
    )
    suggestions: list[str] = Field(default_factory=list, description="How to improve the data")


class ColumnSemantic(BaseModel):
    """Semantic understanding of a column."""

    column_name: str
    technical_type: str = Field(description="Technical type (integer, float, etc.)")
    semantic_type: SemanticColumnType
    confidence: float = Field(ge=0, le=1)
    business_meaning: str = Field(description="Plain English explanation")
    sample_insight: str | None = Field(default=None, description="Quick insight about this column")


class UpdateColumnDescriptionRequest(BaseModel):
    """Request to update user-defined column description."""

    description: str = Field(
        ...,
        min_length=0,
        max_length=500,
        description="User's description of what this column represents",
    )


class SuggestedQuestion(BaseModel):
    """A question the user might want to explore."""

    question: str
    category: str = Field(description="Category (performance, trend, segment, etc.)")
    why_relevant: str = Field(description="Why this question matters for the data")


class SuggestedChart(BaseModel):
    """A chart suggestion auto-generated from dataset profiling."""

    chart_spec: "ChartSpec"
    title: str = Field(description="Human-readable chart title")
    rationale: str = Field(
        description="Why this chart is useful (e.g., 'Shows revenue distribution by category')"
    )


class ObjectiveAlignment(BaseModel):
    """Assessment of how well the dataset supports the user's stated objectives."""

    score: int = Field(ge=0, le=100, description="Overall alignment score 0-100")
    summary: str = Field(description="Brief explanation of alignment score")
    strengths: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="What this data can help with regarding objectives",
    )
    gaps: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="What's missing or would improve usefulness",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Specific actions to improve data usefulness for objectives",
    )


class DatasetInsights(BaseModel):
    """Complete structured intelligence for a dataset."""

    identity: DataIdentity
    headline_metrics: list[HeadlineMetric] = Field(max_length=5)
    insights: list[Insight] = Field(max_length=8)
    quality: DataQualityScore
    suggested_questions: list[SuggestedQuestion] = Field(max_length=5)
    column_semantics: list[ColumnSemantic]
    narrative_summary: str = Field(description="Prose summary for fallback display")
    suggested_charts: list[SuggestedChart] = Field(
        default_factory=list, max_length=5, description="Auto-generated chart suggestions"
    )
    objective_alignment: ObjectiveAlignment | None = Field(
        default=None,
        description="Assessment of data usefulness for user's stated objectives (enhanced insights only)",
    )


class DatasetInsightsResponse(BaseModel):
    """API response wrapper for insights."""

    insights: DatasetInsights | None = Field(
        None, description="Insights data, or null if not yet available"
    )
    generated_at: str
    model_used: str
    tokens_used: int
    cached: bool = False
    message: str | None = Field(
        None, description="Status message (e.g., when insights unavailable)"
    )


# =============================================================================
# Dataset Similarity Models
# =============================================================================


class SimilarDatasetItem(BaseModel):
    """A dataset similar to the query dataset."""

    dataset_id: str = Field(description="Dataset UUID")
    name: str = Field(description="Dataset name")
    similarity: float = Field(ge=0.0, le=1.0, description="Similarity score (0-1)")
    shared_columns: list[str] = Field(default_factory=list, description="Column names in common")
    insight_preview: str | None = Field(
        None, max_length=200, description="Preview of dataset summary/insight"
    )


class SimilarDatasetsResponse(BaseModel):
    """Response for similar datasets endpoint."""

    similar: list[SimilarDatasetItem] = Field(
        default_factory=list, max_length=10, description="Similar datasets"
    )
    query_dataset_id: str = Field(description="Source dataset ID for the query")
    threshold: float = Field(description="Similarity threshold used")


# =============================================================================
# Dataset Investigation Models (8 Deterministic Analyses)
# =============================================================================


class DatasetInvestigationResponse(BaseModel):
    """Response for dataset investigation (8 deterministic analyses).

    These analyses are computed locally without LLM and serve as both:
    1. "Key Insights" displayed to user after dataset loads
    2. Context fed to LLM for smarter "Next Steps" suggestions
    """

    id: str = Field(description="Investigation UUID")
    dataset_id: str = Field(description="Dataset UUID")
    column_roles: dict[str, Any] = Field(description="Column role inference analysis")
    missingness: dict[str, Any] = Field(description="Missingness + uniqueness + cardinality")
    descriptive_stats: dict[str, Any] = Field(description="Descriptive stats + heavy hitters")
    outliers: dict[str, Any] = Field(description="Outlier detection results")
    correlations: dict[str, Any] = Field(description="Correlation matrix + leakage hints")
    time_series_readiness: dict[str, Any] = Field(description="Time-series analysis")
    segmentation_suggestions: dict[str, Any] = Field(description="Segmentation builder results")
    data_quality: dict[str, Any] = Field(description="Data quality assessment")
    computed_at: str = Field(description="When investigation was computed")


# =============================================================================
# Dataset Business Context Models
# =============================================================================


class DatasetBusinessContextCreate(BaseModel):
    """Request to create/update business context for a dataset."""

    business_goal: str | None = Field(
        None, max_length=1000, description="User's business goal (e.g., 'Increase conversion rate')"
    )
    key_metrics: list[str] | None = Field(
        None, max_length=20, description="Key metrics to focus on (e.g., ['revenue', 'churn'])"
    )
    kpis: list[str] | None = Field(
        None, max_length=20, description="KPI targets (e.g., ['MRR > $50K', 'Churn < 5%'])"
    )
    objectives: str | None = Field(None, max_length=2000, description="Detailed objectives text")
    industry: str | None = Field(
        None, max_length=100, description="Industry (e.g., 'SaaS', 'E-commerce')"
    )
    additional_context: str | None = Field(
        None, max_length=5000, description="Any additional context"
    )


class DatasetBusinessContextResponse(BaseModel):
    """Response for dataset business context.

    When id is None, context is inherited from user's global business context.
    """

    id: str | None = Field(None, description="Business context UUID (None if from user context)")
    dataset_id: str = Field(description="Dataset UUID")
    business_goal: str | None = Field(None, description="User's business goal")
    key_metrics: list[str] | None = Field(default_factory=list, description="Key metrics")
    kpis: list[str] | None = Field(default_factory=list, description="KPI targets")
    objectives: str | None = Field(None, description="Detailed objectives")
    industry: str | None = Field(None, description="Industry")
    additional_context: str | None = Field(None, description="Additional context")
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")


# =============================================================================
# Dataset Update Models
# =============================================================================


class DatasetUpdate(BaseModel):
    """Request to update dataset metadata (name/description)."""

    name: str | None = Field(None, min_length=1, max_length=255, description="New dataset name")
    description: str | None = Field(None, max_length=1000, description="New dataset description")


# =============================================================================
# Dataset Comparison Models
# =============================================================================


class DatasetComparisonCreate(BaseModel):
    """Request to create a dataset comparison."""

    name: str | None = Field(None, max_length=255, description="Optional name for the comparison")


class DatasetComparisonResponse(BaseModel):
    """Response for a dataset comparison."""

    id: str = Field(description="Comparison UUID")
    dataset_a_id: str = Field(description="First dataset UUID (baseline)")
    dataset_b_id: str = Field(description="Second dataset UUID (comparison)")
    dataset_a_name: str | None = Field(None, description="First dataset name")
    dataset_b_name: str | None = Field(None, description="Second dataset name")
    name: str | None = Field(None, description="Comparison name")
    schema_comparison: dict[str, Any] = Field(description="Schema comparison results")
    statistics_comparison: dict[str, Any] = Field(description="Statistics comparison results")
    key_metrics_comparison: dict[str, Any] = Field(description="Key metrics comparison")
    insights: list[str] = Field(default_factory=list, description="Generated insights")
    created_at: str = Field(description="When comparison was created")


class DatasetComparisonListResponse(BaseModel):
    """Response for list of comparisons."""

    comparisons: list[DatasetComparisonResponse] = Field(description="List of comparisons")
    total_count: int = Field(description="Total count")


# =============================================================================
# Multi-Dataset Analysis Models
# =============================================================================


class MultiDatasetAnalysisCreate(BaseModel):
    """Request to create a multi-dataset analysis."""

    dataset_ids: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of 2-5 dataset UUIDs to analyze",
    )
    name: str | None = Field(None, max_length=255, description="Optional name for the analysis")


class MultiDatasetAnomaly(BaseModel):
    """A detected anomaly across datasets."""

    anomaly_type: str = Field(
        description="Type: schema_drift, metric_outlier, type_mismatch, no_common_columns"
    )
    severity: str = Field(description="Severity: high, medium, low")
    description: str = Field(description="Human-readable description")
    affected_datasets: list[str] = Field(description="Names of affected datasets")
    column: str | None = Field(None, description="Affected column if applicable")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")


class MultiDatasetSummary(BaseModel):
    """Summary statistics for a single dataset in multi-analysis."""

    name: str = Field(description="Dataset name")
    row_count: int = Field(description="Number of rows")
    column_count: int = Field(description="Number of columns")
    columns: list[str] = Field(description="Column names")
    numeric_columns: list[str] = Field(description="Numeric column names")
    categorical_columns: list[str] = Field(description="Categorical column names")


class MultiDatasetCommonSchema(BaseModel):
    """Schema information common across all datasets."""

    common_columns: list[str] = Field(description="Columns present in ALL datasets")
    partial_columns: dict[str, list[str]] = Field(
        description="Columns with their presence: {column: [datasets]}"
    )
    type_consensus: dict[str, str] = Field(description="Most common type for each column")
    type_conflicts: dict[str, dict[str, str]] = Field(
        description="Type conflicts: {column: {dataset: type}}"
    )


class MultiDatasetAnalysisResponse(BaseModel):
    """Response for a multi-dataset analysis."""

    id: str = Field(description="Analysis UUID")
    dataset_ids: list[str] = Field(description="Analyzed dataset UUIDs")
    dataset_names: list[str] = Field(default_factory=list, description="Dataset names")
    name: str | None = Field(None, description="Analysis name")
    common_schema: MultiDatasetCommonSchema = Field(description="Common schema across datasets")
    anomalies: list[MultiDatasetAnomaly] = Field(
        default_factory=list, description="Detected anomalies"
    )
    dataset_summaries: list[MultiDatasetSummary] = Field(description="Per-dataset summaries")
    pairwise_comparisons: list[dict[str, Any]] = Field(
        default_factory=list, description="Pairwise comparison results"
    )
    created_at: str = Field(description="When analysis was created")


class MultiDatasetAnalysisListResponse(BaseModel):
    """Response for list of multi-dataset analyses."""

    analyses: list[MultiDatasetAnalysisResponse] = Field(description="List of analyses")
    total_count: int = Field(description="Total count")


# =============================================================================
# Dataset Fix/Cleaning Models (Data Quality Actions)
# =============================================================================


class DatasetFixAction(str, Enum):
    """Available data cleaning actions."""

    REMOVE_DUPLICATES = "remove_duplicates"
    FILL_NULLS = "fill_nulls"
    REMOVE_NULLS = "remove_nulls"
    TRIM_WHITESPACE = "trim_whitespace"


class DatasetFixRequest(BaseModel):
    """Request to fix data quality issues in a dataset.

    Attributes:
        action: Cleaning action to apply
        config: Action-specific configuration
    """

    action: DatasetFixAction = Field(..., description="Cleaning action to apply")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Action-specific config. "
            "remove_duplicates: {keep: 'first'|'last', subset: ['col1']}. "
            "fill_nulls: {column: 'col', strategy: 'mean'|'median'|'mode'|'zero'|'value', fill_value: 'x'}. "
            "remove_nulls: {columns: ['col1'], how: 'any'|'all'}. "
            "trim_whitespace: {} (no config needed)."
        ),
    )


class DatasetFixResponse(BaseModel):
    """Response from applying a data fix.

    Attributes:
        success: Whether fix was applied successfully
        rows_affected: Number of rows modified/removed
        new_row_count: Total rows after fix
        reanalysis_required: Whether dataset should be re-analyzed
        message: Human-readable result message
        stats: Detailed statistics from the cleaning operation
    """

    success: bool = Field(..., description="Whether fix was applied successfully")
    rows_affected: int = Field(..., description="Number of rows modified/removed")
    new_row_count: int = Field(..., description="Total rows after fix")
    reanalysis_required: bool = Field(
        default=True, description="Whether dataset should be re-analyzed"
    )
    message: str = Field(..., description="Human-readable result message")
    stats: dict[str, Any] = Field(
        default_factory=dict, description="Detailed statistics from cleaning operation"
    )


# =============================================================================
# User Decision (Decision Gate)
# =============================================================================


class UserDecisionCreate(BaseModel):
    """Request model for creating/updating a user decision."""

    chosen_option_id: str = Field(..., min_length=1, max_length=50)
    chosen_option_label: str = Field(..., min_length=1, max_length=200)
    chosen_option_description: str = Field(default="", max_length=2000)
    rationale: dict[str, Any] | None = Field(default=None)
    matrix_snapshot: dict[str, Any] | None = Field(default=None)
    decision_source: str = Field(default="direct", pattern="^(direct|matrix)$")


class UserDecisionResponse(BaseModel):
    """Response model for a user decision."""

    id: str
    session_id: str
    user_id: str
    chosen_option_id: str
    chosen_option_label: str
    chosen_option_description: str
    rationale: dict[str, Any] | None
    matrix_snapshot: dict[str, Any] | None
    decision_source: str
    created_at: datetime
    updated_at: datetime


# ---- Decision Outcome Models (Outcome Tracking) ----

VALID_OUTCOME_STATUSES = {"successful", "partially_successful", "unsuccessful", "too_early"}


class DecisionOutcomeCreate(BaseModel):
    """Request model for creating/updating a decision outcome."""

    outcome_status: str = Field(..., min_length=1, max_length=30)
    outcome_notes: str | None = Field(default=None, max_length=5000)
    surprise_factor: int | None = Field(default=None, ge=1, le=5)
    lessons_learned: str | None = Field(default=None, max_length=5000)
    what_would_change: str | None = Field(default=None, max_length=5000)

    @field_validator("outcome_status")
    @classmethod
    def validate_outcome_status(cls, v: str) -> str:
        """Validate outcome status is allowed."""
        v = v.strip().lower()
        if v not in VALID_OUTCOME_STATUSES:
            raise ValueError(
                f"Invalid outcome status: {v}. Must be one of: {', '.join(sorted(VALID_OUTCOME_STATUSES))}"
            )
        return v


class DecisionOutcomeResponse(BaseModel):
    """Response model for a decision outcome."""

    id: str
    decision_id: str
    user_id: str
    outcome_status: str
    outcome_notes: str | None
    surprise_factor: int | None
    lessons_learned: str | None
    what_would_change: str | None
    created_at: datetime
    updated_at: datetime


class PendingFollowupResponse(BaseModel):
    """Response model for a pending follow-up nudge."""

    decision_id: str
    session_id: str
    chosen_option_label: str
    decision_date: datetime
    days_ago: int


# =============================================================================
# Decision Patterns (Pattern Detection Dashboard)
# =============================================================================


class BiasFlag(BaseModel):
    """A detected decision-making bias."""

    bias_type: str = Field(..., description="e.g., overconfidence, matrix_aversion")
    description: str
    severity: str = Field(..., pattern="^(high|medium|low)$")


class ConfidenceCalibration(BaseModel):
    """Confidence vs actual outcome calibration."""

    avg_confidence: float | None = None
    success_rate: float | None = None
    total_with_outcomes: int = 0


class ConstraintAccuracy(BaseModel):
    """Constraint alignment accuracy across decisions."""

    total_with_constraints: int = 0
    violations_chosen: int = 0
    violations_successful: int = 0
    tensions_chosen: int = 0
    tensions_successful: int = 0


class MonthlyTrend(BaseModel):
    """Per-month decision statistics."""

    month: str
    total_decisions: int
    outcomes_recorded: int
    success_rate: float | None = None
    avg_confidence: float | None = None


class DecisionPatternsResponse(BaseModel):
    """Aggregated decision-making patterns for a user."""

    has_enough_data: bool
    total_decisions: int
    confidence_calibration: ConfidenceCalibration
    outcome_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Counts by outcome_status: successful, partially_successful, etc.",
    )
    matrix_usage_pct: float | None = None
    avg_surprise_factor: float | None = None
    bias_flags: list[BiasFlag] = Field(default_factory=list)
    constraint_accuracy: ConstraintAccuracy | None = None
    monthly_trends: list[MonthlyTrend] = Field(default_factory=list)
