"""Option card model for Decision Gate feature.

Represents a clustered option extracted from expert recommendations
at the end of deliberation.
"""

from pydantic import BaseModel, Field


class OptionCard(BaseModel):
    """A decision option extracted from expert recommendations."""

    id: str = Field(..., description="Option identifier (e.g., 'opt_001')")
    label: str = Field(..., description="Short option label")
    description: str = Field(..., description="Detailed option description")
    supporting_personas: list[str] = Field(
        default_factory=list, description="Persona codes that support this option"
    )
    confidence_range: tuple[float, float] = Field(
        ..., description="Min/max confidence from supporting personas"
    )
    conditions: list[str] = Field(default_factory=list, description="Key conditions or caveats")
    tradeoffs: list[str] = Field(default_factory=list, description="Known tradeoffs")
    risk_summary: str = Field(default="", description="Summary of risks for this option")
    criteria_scores: dict[str, float] | None = Field(
        default=None, description="Criterion name -> 0-1 score"
    )
    constraint_alignment: dict[str, str] | None = Field(
        default=None, description="Constraint description -> pass/tension/violation"
    )
