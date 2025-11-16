"""Reusable Pydantic type annotations for Board of One models.

Provides standardized type constraints for common field patterns to ensure
consistency and reduce duplication across model definitions.
"""

from datetime import datetime
from typing import Annotated

from pydantic import Field


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now()


# Score/confidence types (0-1 range)
Score = Annotated[float, Field(ge=0.0, le=1.0)]
"""Float constrained to 0.0-1.0 range (inclusive)."""

OptionalScore = Annotated[float | None, Field(ge=0.0, le=1.0, default=None)]
"""Optional float constrained to 0.0-1.0 range."""

# Specific score types (for clarity)
Confidence = Annotated[float, Field(ge=0.0, le=1.0, description="Confidence level (0-1)")]
"""Confidence level constrained to 0.0-1.0 range."""

Weight = Annotated[float, Field(ge=0.0, le=2.0, description="Weighting factor (0-2)")]
"""Weighting factor constrained to 0.0-2.0 range (typically 0.8-1.2)."""

Temperature = Annotated[float, Field(ge=0.0, le=2.0, description="LLM temperature (0-2)")]
"""LLM temperature parameter constrained to 0.0-2.0 range."""

ComplexityScore = Annotated[int, Field(ge=1, le=10, description="Complexity rating (1-10)")]
"""Complexity rating constrained to 1-10 integer range."""

# Timestamp types
Timestamp = Annotated[datetime, Field(default_factory=_utc_now)]
"""Auto-generated timestamp field using current UTC time."""
