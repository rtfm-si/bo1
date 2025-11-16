"""Factory functions for creating test data.

This module provides factory functions to create test objects with sensible
defaults, reducing boilerplate in test files.
"""

from datetime import datetime
from typing import Any

from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationMetrics


def create_test_problem(
    title: str = "Test Problem",
    description: str = "Test description for problem",
    context: str = "Test context",
    **kwargs: Any,
) -> Problem:
    """Create a test problem with sensible defaults.

    Args:
        title: Problem title (default: "Test Problem")
        description: Problem description (default: "Test description for problem")
        context: Problem context (default: "Test context")
        **kwargs: Additional keyword arguments passed to Problem constructor

    Returns:
        Problem instance with provided or default values
    """
    return Problem(
        title=title,
        description=description,
        context=context,
        **kwargs,
    )


def create_test_sub_problem(
    id: str = "sp_test_001",
    goal: str = "Test sub-problem goal",
    context: str = "Test sub-problem context",
    complexity_score: int = 5,
    **kwargs: Any,
) -> SubProblem:
    """Create a test sub-problem with sensible defaults.

    Args:
        id: Sub-problem ID (default: "sp_test_001")
        goal: Sub-problem goal (default: "Test sub-problem goal")
        context: Sub-problem context (default: "Test sub-problem context")
        complexity_score: Complexity score 1-10 (default: 5)
        **kwargs: Additional keyword arguments passed to SubProblem constructor

    Returns:
        SubProblem instance with provided or default values
    """
    return SubProblem(
        id=id,
        goal=goal,
        context=context,
        complexity_score=complexity_score,
        dependencies=kwargs.get("dependencies", []),
        **{k: v for k, v in kwargs.items() if k != "dependencies"},
    )


def create_test_contribution(
    persona_code: str = "test_expert",
    persona_name: str = "Test Expert",
    round_number: int = 1,
    content: str | None = None,
    **kwargs: Any,
) -> ContributionMessage:
    """Create a test contribution with sensible defaults.

    Args:
        persona_code: Persona code (default: "test_expert")
        persona_name: Persona display name (default: "Test Expert")
        round_number: Round number (default: 1)
        content: Contribution content (default: generated from persona_name)
        **kwargs: Additional keyword arguments passed to ContributionMessage constructor

    Returns:
        ContributionMessage instance with provided or default values
    """
    if content is None:
        content = f"Contribution from {persona_name} in round {round_number}"

    return ContributionMessage(
        persona_code=persona_code,
        persona_name=persona_name,
        round_number=round_number,
        content=content,
        thinking=kwargs.get("thinking", f"Thinking from {persona_name}..."),
        token_count=kwargs.get("token_count", 50),
        cost=kwargs.get("cost", 0.001),
        timestamp=kwargs.get("timestamp", datetime.now()),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["thinking", "token_count", "cost", "timestamp"]
        },
    )


def create_test_metrics(
    total_cost: float = 0.0,
    total_tokens: int = 0,
    phase_costs: dict[str, float] | None = None,
    **kwargs: Any,
) -> DeliberationMetrics:
    """Create test metrics with sensible defaults.

    Args:
        total_cost: Total cost (default: 0.0)
        total_tokens: Total tokens used (default: 0)
        phase_costs: Dictionary of phase names to costs (default: empty dict)
        **kwargs: Additional keyword arguments passed to DeliberationMetrics constructor

    Returns:
        DeliberationMetrics instance with provided or default values
    """
    if phase_costs is None:
        phase_costs = {}

    return DeliberationMetrics(
        total_cost=total_cost,
        total_tokens=total_tokens,
        phase_costs=phase_costs,
        convergence_score=kwargs.get("convergence_score"),
        novelty_score=kwargs.get("novelty_score"),
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["convergence_score", "novelty_score", "start_time", "end_time"]
        },
    )


def create_test_contributions_batch(
    persona_codes: list[str],
    round_number: int = 1,
    content_template: str = "Contribution from {persona_name}",
) -> list[ContributionMessage]:
    """Create a batch of test contributions for multiple personas.

    Args:
        persona_codes: List of persona codes to create contributions for
        round_number: Round number for all contributions (default: 1)
        content_template: Template for content, can use {persona_name} placeholder

    Returns:
        List of ContributionMessage instances
    """
    contributions = []
    for code in persona_codes:
        # Convert code to display name (capitalize and replace underscores)
        display_name = code.replace("_", " ").title()
        content = content_template.format(persona_name=display_name)

        contributions.append(
            create_test_contribution(
                persona_code=code,
                persona_name=display_name,
                round_number=round_number,
                content=content,
            )
        )

    return contributions
