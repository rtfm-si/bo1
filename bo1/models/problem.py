"""Problem domain models for Board of One.

Defines the core problem decomposition models.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConstraintType(str, Enum):
    """Types of constraints that can be applied to problems."""

    BUDGET = "budget"
    TIME = "time"
    RESOURCE = "resource"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"
    ETHICAL = "ethical"
    OTHER = "other"


class Constraint(BaseModel):
    """A constraint on the problem or sub-problem."""

    type: ConstraintType = Field(..., description="Type of constraint")
    description: str = Field(..., description="Human-readable description of the constraint")
    value: Any | None = Field(
        None, description="Optional quantitative value (e.g., $10000, 30 days)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "budget",
                    "description": "Maximum budget for implementation",
                    "value": 50000,
                },
                {
                    "type": "time",
                    "description": "Must be completed within 3 months",
                    "value": "90 days",
                },
            ]
        }
    )


class SubProblem(BaseModel):
    """A decomposed sub-problem within a larger problem."""

    id: str = Field(..., description="Unique identifier for this sub-problem")
    goal: str = Field(..., description="The specific goal or question to address")
    context: str = Field(..., description="Relevant context and background for this sub-problem")
    complexity_score: int = Field(
        ..., ge=1, le=10, description="Complexity rating from 1 (simple) to 10 (very complex)"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of sub-problem IDs that must be resolved first",
    )
    constraints: list[Constraint] = Field(
        default_factory=list, description="Specific constraints for this sub-problem"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "sp_001",
                    "goal": "Determine optimal pricing tier structure",
                    "context": "SaaS product targeting SMBs, need to balance affordability with revenue goals",
                    "complexity_score": 6,
                    "dependencies": [],
                    "constraints": [
                        {
                            "type": "budget",
                            "description": "Market research budget",
                            "value": 5000,
                        }
                    ],
                }
            ]
        }
    )


class Problem(BaseModel):
    """The main problem statement and decomposition."""

    title: str = Field(..., description="Short title for the problem")
    description: str = Field(..., description="Detailed description of the problem to solve")
    context: str = Field(
        ...,
        description="Background context, business situation, or personal circumstances",
    )
    constraints: list[Constraint] = Field(
        default_factory=list, description="Global constraints applying to all sub-problems"
    )
    sub_problems: list[SubProblem] = Field(
        default_factory=list,
        description="Decomposed sub-problems (1-5 typically)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "SaaS Pricing Strategy",
                    "description": "Determine optimal pricing model for new B2B SaaS product",
                    "context": "Solo founder, $50K runway, launching in 6 months",
                    "constraints": [
                        {
                            "type": "budget",
                            "description": "Total development budget",
                            "value": 50000,
                        },
                        {
                            "type": "time",
                            "description": "Launch deadline",
                            "value": "6 months",
                        },
                    ],
                    "sub_problems": [
                        {
                            "id": "sp_001",
                            "goal": "Determine pricing tier structure",
                            "context": "Need to balance affordability with revenue",
                            "complexity_score": 6,
                            "dependencies": [],
                            "constraints": [],
                        }
                    ],
                }
            ]
        }
    )

    def get_sub_problem(self, sub_problem_id: str) -> SubProblem | None:
        """Get a sub-problem by ID.

        Args:
            sub_problem_id: The ID of the sub-problem to retrieve

        Returns:
            The SubProblem if found, None otherwise
        """
        for sp in self.sub_problems:
            if sp.id == sub_problem_id:
                return sp
        return None

    def is_atomic(self) -> bool:
        """Check if this is an atomic problem (no decomposition needed).

        Returns:
            True if there are no sub-problems or only 1 sub-problem
        """
        return len(self.sub_problems) <= 1
