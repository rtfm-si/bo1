"""Session model for Board of One.

Provides type-safe session handling with Pydantic validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from bo1.models.util import FromDbRowMixin


class SessionStatus(str, Enum):
    """Session lifecycle status."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class Session(FromDbRowMixin):
    """Session model matching PostgreSQL sessions table.

    Provides type-safe access to session data with validation.
    """

    # Session IDs are not UUIDs (e.g., "bo1_abc123"), so exclude from UUID normalization
    _uuid_fields: ClassVar[set[str]] = {"workspace_id", "dataset_id", "template_id"}

    id: str = Field(..., description="Session identifier (e.g., bo1_uuid)")
    user_id: str = Field(..., description="User who created the session")
    problem_statement: str = Field(..., description="Original problem statement")
    problem_context: dict[str, Any] | None = Field(None, description="Additional context as JSONB")
    status: SessionStatus = Field(SessionStatus.CREATED, description="Current session status")
    phase: str = Field("problem_decomposition", description="Current deliberation phase")
    total_cost: float = Field(0.0, description="Total cost in USD")
    round_number: int = Field(0, description="Current round number")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    synthesis_text: str | None = Field(None, description="Final synthesis text")
    final_recommendation: str | None = Field(None, description="Final recommendation")
    # Termination fields (from z3_add_session_termination migration)
    terminated_at: datetime | None = Field(None, description="When session was terminated")
    termination_type: str | None = Field(
        None, description="Type: blocker_identified, user_cancelled, continue_best_effort"
    )
    termination_reason: str | None = Field(None, description="Human-readable termination reason")
    billable_portion: float | None = Field(None, description="Billable portion 0.0-1.0")
    # Count fields (from d1_add_session_counts migration)
    expert_count: int = Field(0, description="Number of experts in session")
    contribution_count: int = Field(0, description="Number of contributions in session")
    focus_area_count: int = Field(0, description="Number of focus areas in session")
    task_count: int = Field(0, description="Number of tasks in session")
    # Workspace scope (from aa2_add_workspace_to_sessions migration)
    workspace_id: str | None = Field(None, description="Workspace UUID (None = personal)")
    # Dataset scope (from g3_add_dataset_to_sessions migration)
    dataset_id: str | None = Field(None, description="Dataset UUID for analysis sessions")
    # Recovery flags (from c3_add_session_recovery_flags migration)
    has_untracked_costs: bool = Field(False, description="True when cost inserts failed")
    recovery_needed: bool = Field(False, description="True when in-flight contributions exist")
    # Failure acknowledgment (from z11_add_failure_acknowledged migration)
    failure_acknowledged_at: datetime | None = Field(
        None, description="When user acknowledged failed session"
    )
    # Meeting template (from z21_add_meeting_templates migration)
    template_id: str | None = Field(None, description="Template used to create this session")
    # A/B experiment (from ab1_add_persona_experiment migration)
    persona_count_variant: int | None = Field(None, description="A/B test variant: 3 or 5 personas")
    # Checkpoint resume fields (from zw_add_checkpoint_resume_fields migration)
    last_completed_sp_index: int | None = Field(
        None, description="Index of last successfully completed sub-problem (0-based)"
    )
    sp_checkpoint_at: datetime | None = Field(
        None, description="When last SP boundary checkpoint was saved"
    )
    total_sub_problems: int | None = Field(
        None, description="Total number of sub-problems in decomposition"
    )

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
