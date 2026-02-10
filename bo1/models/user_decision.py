"""User decision model for Decision Gate feature.

Records the human's final decision after deliberation, including
chosen option, rationale, and optional decision matrix snapshot.
"""

from typing import Any, ClassVar

from pydantic import Field

from bo1.models.util import AuditFieldsMixin, FromDbRowMixin


class UserDecision(AuditFieldsMixin, FromDbRowMixin):
    """A user's recorded decision for a deliberation session."""

    id: str = Field(..., description="UUID primary key")
    session_id: str = Field(..., description="Session identifier (bo1_ prefix)")
    user_id: str = Field(..., description="User identifier")
    chosen_option_id: str = Field(..., description="ID of the chosen option")
    chosen_option_label: str = Field(..., description="Label of the chosen option")
    chosen_option_description: str = Field(
        default="", description="Description of the chosen option"
    )
    rationale: dict[str, Any] | None = Field(default=None, description="Structured rationale JSONB")
    matrix_snapshot: dict[str, Any] | None = Field(
        default=None, description="Decision matrix snapshot JSONB"
    )
    decision_source: str = Field(
        default="direct", description="How decision was made: direct | matrix"
    )

    # session_id is NOT a UUID (uses bo1_ prefix)
    _uuid_fields: ClassVar[set[str]] = {"id"}
