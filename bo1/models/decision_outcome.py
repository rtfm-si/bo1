"""Decision outcome model for Outcome Tracking.

Records what actually happened after a user made a decision,
enabling the feedback loop: Decision → Action → Outcome.
"""

from typing import ClassVar

from pydantic import Field

from bo1.models.util import AuditFieldsMixin, FromDbRowMixin


class DecisionOutcome(AuditFieldsMixin, FromDbRowMixin):
    """A recorded outcome for a user's decision."""

    id: str = Field(..., description="UUID primary key")
    decision_id: str = Field(..., description="FK to user_decisions.id")
    user_id: str = Field(..., description="User identifier")
    outcome_status: str = Field(
        ..., description="successful/partially_successful/unsuccessful/too_early"
    )
    outcome_notes: str | None = Field(default=None, description="What happened")
    surprise_factor: int | None = Field(
        default=None, description="1=expected, 5=totally unexpected"
    )
    lessons_learned: str | None = Field(default=None, description="Lessons from this outcome")
    what_would_change: str | None = Field(default=None, description="What would you do differently")

    _uuid_fields: ClassVar[set[str]] = {"id", "decision_id"}
