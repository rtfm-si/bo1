"""Problem decomposition agent.

Breaks complex problems into 1-5 manageable sub-problems with complexity scoring
and dependency mapping.
"""

import json
import logging
from typing import Any

from bo1.config import MODEL_BY_ROLE
from bo1.llm.client import ClaudeClient
from bo1.models.problem import Problem, SubProblem
from bo1.prompts.decomposer_prompts import (
    DECOMPOSER_SYSTEM_PROMPT,
    compose_decomposition_request,
)

logger = logging.getLogger(__name__)


class DecomposerAgent:
    """Agent that decomposes complex problems into sub-problems.

    The decomposer analyzes user input and breaks it into 1-5 manageable
    sub-problems, assigns complexity scores (1-10), and maps dependencies.

    Uses Sonnet 4.5 for complex problem analysis.
    """

    def __init__(self, client: ClaudeClient | None = None) -> None:
        """Initialize the decomposer agent.

        Args:
            client: Optional ClaudeClient instance. If None, creates a new one.
        """
        self.client = client or ClaudeClient()
        self.model_name = MODEL_BY_ROLE["decomposer"]

    def extract_problem_statement(
        self,
        user_input: str,
        interactive: bool = True,
    ) -> tuple[str, str, list[str]]:
        """Extract structured problem statement from user input.

        Optionally asks clarifying questions in an interactive Q&A loop.

        Args:
            user_input: Raw problem description from user
            interactive: If True, ask clarifying questions. If False, use input as-is.

        Returns:
            Tuple of (problem_description, context, constraints)

        Examples:
            >>> agent = DecomposerAgent()
            >>> desc, ctx, constraints = agent.extract_problem_statement(
            ...     "I need to decide on pricing for my SaaS",
            ...     interactive=False
            ... )
        """
        logger.info("Extracting problem statement from user input")

        if not interactive:
            # Non-interactive: just return the input as-is
            return user_input, "", []

        # Interactive mode: ask clarifying questions
        # Phase 1: Generate clarifying questions
        clarification_prompt = f"""You are helping a user articulate their problem clearly.

Problem statement (initial):
{user_input}

Generate 2-4 clarifying questions to help understand:
1. The specific decision or problem they need to solve
2. Their current situation and context
3. Key constraints (budget, time, resources, etc.)
4. What success looks like

Respond with a JSON array of questions:
{{"questions": ["Question 1?", "Question 2?", ...]}}

Keep questions focused and actionable. Avoid generic questions like "Tell me more."
"""

        response = self.client.call(
            model_name=self.model_name,
            system_prompt="You are a problem clarification expert. Generate targeted questions to understand the user's problem.",
            user_message=clarification_prompt,
        )

        # Parse questions
        try:
            questions_data = json.loads(response["content"])
            questions = questions_data.get("questions", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse clarifying questions, skipping Q&A")
            return user_input, "", []

        # Phase 2: Interactive Q&A (simulated for now - will integrate with console UI)
        # TODO: Integrate with bo1/ui/console.py for real user interaction
        logger.info(f"Generated {len(questions)} clarifying questions")
        for i, q in enumerate(questions, 1):
            logger.info(f"Q{i}: {q}")

        # For now, return with minimal structure
        # In full implementation, we'd collect answers and use them to build context
        return user_input, "", []

    def decompose_problem(
        self,
        problem_description: str,
        context: str = "",
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Decompose a problem into sub-problems using LLM.

        Breaks the problem into 1-5 sub-problems with:
        - Clear goals
        - Complexity scores (1-10)
        - Dependency mapping
        - Context for each sub-problem

        Args:
            problem_description: Main problem to decompose
            context: Additional context about the problem
            constraints: List of constraints (budget, time, etc.)

        Returns:
            Dictionary containing:
            - analysis: Brief analysis of the problem
            - is_atomic: Whether problem is atomic (no decomposition needed)
            - sub_problems: List of sub-problem dictionaries

        Examples:
            >>> agent = DecomposerAgent()
            >>> result = agent.decompose_problem(
            ...     "Should I invest $50K in SEO or paid ads?",
            ...     context="Solo founder, SaaS product, $100K ARR",
            ...     constraints=["Budget: $50K", "Timeline: 6 months"]
            ... )
            >>> len(result["sub_problems"])
            3
        """
        logger.info(f"Decomposing problem: {problem_description[:100]}...")

        # Compose the decomposition request
        user_message = compose_decomposition_request(
            problem_description=problem_description,
            context=context,
            constraints=constraints,
        )

        # Call LLM with decomposer system prompt
        response = self.client.call(
            model_name=self.model_name,
            system_prompt=DECOMPOSER_SYSTEM_PROMPT,
            user_message=user_message,
        )

        # Parse JSON response
        try:
            decomposition = json.loads(response["content"])

            # Validate structure
            if "sub_problems" not in decomposition:
                raise ValueError("Response missing 'sub_problems' field")

            if "is_atomic" not in decomposition:
                # Infer from number of sub-problems
                decomposition["is_atomic"] = len(decomposition["sub_problems"]) <= 1

            logger.info(
                f"Decomposition complete: {len(decomposition['sub_problems'])} sub-problems, "
                f"atomic={decomposition['is_atomic']}"
            )

            return decomposition

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decomposition JSON: {e}")
            # Fallback: treat as atomic problem
            return {
                "analysis": "Unable to parse decomposition, treating as atomic problem.",
                "is_atomic": True,
                "sub_problems": [
                    {
                        "id": "sp_001",
                        "goal": problem_description,
                        "context": context,
                        "complexity_score": 5,
                        "dependencies": [],
                        "rationale": "Fallback atomic problem due to parsing error.",
                    }
                ],
            }
        except Exception as e:
            logger.error(f"Error during decomposition: {e}")
            raise

    def create_problem_from_decomposition(
        self,
        title: str,
        problem_description: str,
        context: str,
        decomposition: dict[str, Any],
    ) -> Problem:
        """Create a Problem model from decomposition result.

        Args:
            title: Short title for the problem
            problem_description: Full problem description
            context: Problem context
            decomposition: Result from decompose_problem()

        Returns:
            Problem model instance
        """
        # Convert sub-problem dicts to SubProblem models
        sub_problems = [
            SubProblem(
                id=sp["id"],
                goal=sp["goal"],
                context=sp.get("context", ""),
                complexity_score=sp["complexity_score"],
                dependencies=sp.get("dependencies", []),
            )
            for sp in decomposition.get("sub_problems", [])
        ]

        # Create Problem model
        problem = Problem(
            title=title,
            description=problem_description,
            context=context,
            sub_problems=sub_problems,
        )

        logger.info(f"Created Problem model: {problem.title} with {len(sub_problems)} sub-problems")

        return problem

    def validate_decomposition(self, decomposition: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate decomposition quality.

        Checks:
        - Number of sub-problems (1-5)
        - Complexity scores are in range (1-10)
        - Dependencies reference valid sub-problem IDs
        - Each sub-problem has required fields

        Args:
            decomposition: Decomposition result to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check sub-problems exist
        sub_problems = decomposition.get("sub_problems", [])
        if not sub_problems:
            errors.append("No sub-problems found in decomposition")
            return False, errors

        # Check count (1-5)
        if len(sub_problems) > 5:
            errors.append(f"Too many sub-problems: {len(sub_problems)} (max 5)")

        # Track all IDs for dependency validation
        valid_ids = {sp.get("id") for sp in sub_problems if "id" in sp}

        # Validate each sub-problem
        for i, sp in enumerate(sub_problems, 1):
            prefix = f"Sub-problem {i}"

            # Check required fields
            if "id" not in sp:
                errors.append(f"{prefix}: Missing 'id' field")
            if "goal" not in sp:
                errors.append(f"{prefix}: Missing 'goal' field")
            if "complexity_score" not in sp:
                errors.append(f"{prefix}: Missing 'complexity_score' field")
            else:
                # Validate complexity score range
                score = sp["complexity_score"]
                if not isinstance(score, int) or score < 1 or score > 10:
                    errors.append(f"{prefix}: Complexity score {score} out of range (1-10)")

            # Validate dependencies
            dependencies = sp.get("dependencies", [])
            for dep_id in dependencies:
                if dep_id not in valid_ids:
                    errors.append(f"{prefix}: Invalid dependency '{dep_id}'")

        is_valid = len(errors) == 0
        return is_valid, errors
