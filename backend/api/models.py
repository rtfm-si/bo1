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
        description="Strategic question for deliberation",
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
