"""Complexity assessment agent for adaptive deliberation parameters.

Analyzes problem complexity across 5 dimensions to determine optimal:
- max_rounds (3-6)
- num_experts per round (3-5)
"""

import logging
from typing import Any

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.prompts.complexity_prompts import (
    COMPLEXITY_ASSESSMENT_SYSTEM_PROMPT,
    compose_complexity_assessment_request,
)

logger = logging.getLogger(__name__)


class ComplexityAssessor:
    """Assess problem complexity to enable adaptive deliberation parameters.

    This agent evaluates problems across 5 dimensions:
    1. Scope breadth (number of domains)
    2. Dependencies (interconnectedness)
    3. Ambiguity (clarity of requirements)
    4. Stakeholders (parties affected)
    5. Novelty (precedent availability)

    Based on overall complexity (0.0-1.0), it recommends:
    - Rounds: 3-6 (simple to complex)
    - Experts: 3-5 (focused to diverse)

    Example:
        >>> assessor = ComplexityAssessor()
        >>> response = await assessor.assess_complexity(
        ...     problem_description="Should I use PostgreSQL or MySQL?",
        ...     context="Building a B2B SaaS app",
        ...     sub_problems=[{"id": "sp_001", "goal": "Database selection"}]
        ... )
        >>> # response contains complexity scores and recommendations
    """

    def __init__(self) -> None:
        """Initialize complexity assessor with prompt broker."""
        self.broker = PromptBroker()

    async def assess_complexity(
        self,
        problem_description: str,
        context: str = "",
        sub_problems: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Assess problem complexity and recommend deliberation parameters.

        Args:
            problem_description: The main problem statement
            context: Additional context about the problem
            sub_problems: Optional list of sub-problem dicts for context

        Returns:
            LLMResponse with JSON containing:
            - scope_breadth: 0.0-1.0
            - dependencies: 0.0-1.0
            - ambiguity: 0.0-1.0
            - stakeholders: 0.0-1.0
            - novelty: 0.0-1.0
            - overall_complexity: 0.0-1.0
            - recommended_rounds: 3-6
            - recommended_experts: 3-5
            - reasoning: str

        Example:
            >>> response = await assessor.assess_complexity(
            ...     problem_description="Should I pivot from B2B to B2C?",
            ...     context="18 months in, $500K ARR, team of 5",
            ...     sub_problems=[
            ...         {"id": "sp_001", "goal": "Market analysis"},
            ...         {"id": "sp_002", "goal": "Product changes"},
            ...         {"id": "sp_003", "goal": "Financial model"}
            ...     ]
            ... )
            >>> # Parse response.content as JSON to get complexity scores
        """
        logger.info("Assessing problem complexity for adaptive parameters")

        # Compose prompt
        user_message = compose_complexity_assessment_request(
            problem_description=problem_description,
            context=context,
            sub_problems=sub_problems,
        )

        # Create request
        request = PromptRequest(
            system=COMPLEXITY_ASSESSMENT_SYSTEM_PROMPT,
            user_message=user_message,
            model="haiku",  # Use Haiku for fast, cheap complexity assessment
            max_tokens=500,
            phase="complexity_assessment",
            agent_type="ComplexityAssessor",
        )

        # Call LLM
        response = await self.broker.call(request)

        logger.info(
            f"Complexity assessment complete (cost: ${response.cost_total:.4f}, "
            f"tokens: {response.total_tokens})"
        )

        return response


def get_adaptive_max_rounds(complexity_score: float) -> int:
    """Calculate max rounds based on overall complexity.

    Maps complexity to round limits:
    - 0.0-0.3: 3 rounds (simple)
    - 0.3-0.5: 4 rounds (moderate)
    - 0.5-0.7: 5 rounds (complex)
    - 0.7-1.0: 6 rounds (highly complex)

    Args:
        complexity_score: Overall complexity (0.0-1.0)

    Returns:
        Recommended max rounds (3-6)

    Example:
        >>> get_adaptive_max_rounds(0.2)
        3  # Simple problem
        >>> get_adaptive_max_rounds(0.8)
        6  # Complex problem
    """
    if complexity_score < 0.3:
        return 3  # Simple: quick resolution
    elif complexity_score < 0.5:
        return 4  # Moderate: standard debate
    elif complexity_score < 0.7:
        return 5  # Complex: extended discussion
    else:
        return 6  # Highly complex: full deliberation


def get_adaptive_num_experts(complexity_score: float) -> int:
    """Calculate number of experts per round based on complexity.

    Maps complexity to expert count:
    - 0.0-0.3: 3 experts (focused panel)
    - 0.3-0.7: 4 experts (balanced panel)
    - 0.7-1.0: 5 experts (diverse perspectives)

    Args:
        complexity_score: Overall complexity (0.0-1.0)

    Returns:
        Recommended experts per round (3-5)

    Example:
        >>> get_adaptive_num_experts(0.2)
        3  # Simple: focused panel
        >>> get_adaptive_num_experts(0.8)
        5  # Complex: diverse panel
    """
    if complexity_score < 0.3:
        return 3  # Simple: focused panel
    elif complexity_score < 0.7:
        return 4  # Moderate/Complex: balanced panel
    else:
        return 5  # Highly complex: diverse perspectives


def validate_complexity_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize complexity assessment results.

    Ensures all scores are in valid ranges and provides fallbacks.

    Args:
        assessment: Parsed complexity assessment JSON

    Returns:
        Validated assessment with guaranteed valid values

    Example:
        >>> assessment = {"overall_complexity": 1.5, "recommended_rounds": 10}
        >>> validated = validate_complexity_assessment(assessment)
        >>> validated["overall_complexity"]
        1.0  # Clamped to max
        >>> validated["recommended_rounds"]
        6  # Clamped to max
    """
    # Clamp dimension scores to 0.0-1.0
    for dimension in [
        "scope_breadth",
        "dependencies",
        "ambiguity",
        "stakeholders",
        "novelty",
        "overall_complexity",
    ]:
        if dimension in assessment:
            value = assessment[dimension]
            if isinstance(value, (int, float)):
                assessment[dimension] = max(0.0, min(1.0, float(value)))
            else:
                logger.warning(f"Invalid {dimension} value: {value}, using default 0.5")
                assessment[dimension] = 0.5

    # Clamp recommended_rounds to 3-6
    if "recommended_rounds" in assessment:
        rounds = assessment["recommended_rounds"]
        if isinstance(rounds, (int, float)):
            assessment["recommended_rounds"] = max(3, min(6, int(rounds)))
        else:
            logger.warning(f"Invalid recommended_rounds: {rounds}, using default 4")
            assessment["recommended_rounds"] = 4

    # Clamp recommended_experts to 3-5
    if "recommended_experts" in assessment:
        experts = assessment["recommended_experts"]
        if isinstance(experts, (int, float)):
            assessment["recommended_experts"] = max(3, min(5, int(experts)))
        else:
            logger.warning(f"Invalid recommended_experts: {experts}, using default 4")
            assessment["recommended_experts"] = 4

    # Ensure reasoning exists
    if "reasoning" not in assessment or not assessment["reasoning"]:
        assessment["reasoning"] = "Complexity assessment completed"

    return assessment
