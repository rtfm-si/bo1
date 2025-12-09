"""Session model for Board of One.

Provides type-safe session handling with Pydantic validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionStatus(str, Enum):
    """Session lifecycle status."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class Session(BaseModel):
    """Session model matching PostgreSQL sessions table.

    Provides type-safe access to session data with validation.
    """

    id: str = Field(..., description="Session identifier (e.g., bo1_uuid)")
    user_id: str = Field(..., description="User who created the session")
    problem_statement: str = Field(..., description="Original problem statement")
    problem_context: dict[str, Any] | None = Field(None, description="Additional context as JSONB")
    status: SessionStatus = Field(SessionStatus.CREATED, description="Current session status")
    phase: str | None = Field(None, description="Current deliberation phase")
    total_cost: float | None = Field(None, description="Total cost in USD")
    round_number: int | None = Field(None, description="Current round number")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    synthesis_text: str | None = Field(None, description="Final synthesis text")
    final_recommendation: str | None = Field(None, description="Final recommendation")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "bo1_abc123",
                    "user_id": "user_456",
                    "problem_statement": "How should we allocate marketing budget?",
                    "status": "running",
                    "phase": "discussion",
                    "total_cost": 0.15,
                    "round_number": 3,
                }
            ]
        },
    )

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Session":
        """Create Session from database row dict.

        Args:
            row: Dict from psycopg2 cursor with session columns

        Returns:
            Session instance with validated data

        Example:
            >>> row = {"id": "bo1_123", "user_id": "u1", ...}
            >>> session = Session.from_db_row(row)
        """
        # Handle status as string or enum
        status = row.get("status", "created")
        if isinstance(status, str):
            status = SessionStatus(status)

        return cls(
            id=row["id"],
            user_id=row["user_id"],
            problem_statement=row["problem_statement"],
            problem_context=row.get("problem_context"),
            status=status,
            phase=row.get("phase"),
            total_cost=row.get("total_cost"),
            round_number=row.get("round_number"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            synthesis_text=row.get("synthesis_text"),
            final_recommendation=row.get("final_recommendation"),
        )
