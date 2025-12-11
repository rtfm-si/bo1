"""Contribution summary models for Board of One.

Defines schema for LLM-generated contribution summaries.
"""

from pydantic import BaseModel, Field, field_validator


class ContributionSummary(BaseModel):
    """Structured summary of an expert contribution.

    Used by EventCollector to validate LLM output schema.
    """

    concise: str = Field(
        default="",
        max_length=500,
        description="1-2 sentence summary (25-40 words)",
    )
    looking_for: str = Field(
        default="",
        max_length=200,
        description="What the expert is analyzing (15-25 words)",
    )
    value_added: str = Field(
        default="",
        max_length=200,
        description="Unique insight or perspective (15-25 words)",
    )
    concerns: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="2-3 specific concerns (10-15 words each)",
    )
    questions: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="1-2 specific questions (10-15 words each)",
    )
    parse_error: bool = Field(
        default=False,
        description="True if this is a fallback due to parsing failure",
    )
    schema_valid: bool = Field(
        default=True,
        description="True if LLM output passed schema validation",
    )

    @field_validator("concerns", "questions", mode="before")
    @classmethod
    def coerce_to_list(cls, v: str | list[str] | None) -> list[str]:
        """Coerce string or None to list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)
