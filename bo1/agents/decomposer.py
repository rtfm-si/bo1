"""Problem decomposition agent.

Breaks complex problems into 1-5 manageable sub-problems with complexity scoring
and dependency mapping.
"""

import json
import logging
from typing import Any

from bo1.config import MODEL_BY_ROLE
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
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

    def __init__(self, broker: PromptBroker | None = None) -> None:
        """Initialize the decomposer agent.

        Args:
            broker: Optional PromptBroker instance. If None, creates a new one.
        """
        self.broker = broker or PromptBroker()
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

        messages = [{"role": "user", "content": clarification_prompt}]
        import asyncio

        response_text, _ = asyncio.run(
            self.broker.client.call(
                model=self.model_name,
                messages=messages,
                system="You are a problem clarification expert. Generate targeted questions to understand the user's problem.",
                cache_system=False,
            )
        )

        # Parse questions
        try:
            questions_data = json.loads(response_text)
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

    async def decompose_problem(
        self,
        problem_description: str,
        context: str = "",
        constraints: list[str] | None = None,
    ) -> LLMResponse:
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
            LLMResponse with:
            - content: JSON string with decomposition (parse with json.loads())
            - token_usage: Detailed token breakdown
            - cost_total: Total cost in USD
            - All other comprehensive metrics

        Examples:
            >>> agent = DecomposerAgent()
            >>> response = await agent.decompose_problem(
            ...     "Should I invest $50K in SEO or paid ads?",
            ...     context="Solo founder, SaaS product, $100K ARR",
            ...     constraints=["Budget: $50K", "Timeline: 6 months"]
            ... )
            >>> decomposition = json.loads(response.content)
            >>> len(decomposition["sub_problems"])
            3
        """
        logger.info(f"Decomposing problem: {problem_description[:100]}...")

        # Compose the decomposition request
        user_message = compose_decomposition_request(
            problem_description=problem_description,
            context=context,
            constraints=constraints,
        )

        # Create prompt request
        request = PromptRequest(
            system=DECOMPOSER_SYSTEM_PROMPT,
            user_message=user_message,
            model=self.model_name,
            prefill="{",  # Ensure JSON response starts with {
            cache_system=False,  # No caching needed for one-off decomposition
            phase="decomposition",
            agent_type="DecomposerAgent",
        )

        # Call LLM via broker (handles retry/rate-limit)
        response = await self.broker.call(request)

        # Validate JSON structure
        try:
            decomposition = json.loads(response.content)

            # Validate structure
            if "sub_problems" not in decomposition:
                raise ValueError("Response missing 'sub_problems' field")

            if "is_atomic" not in decomposition:
                # Infer from number of sub-problems
                decomposition["is_atomic"] = len(decomposition["sub_problems"]) <= 1

            logger.info(
                f"Decomposition complete: {len(decomposition['sub_problems'])} sub-problems, "
                f"atomic={decomposition['is_atomic']} "
                f"({response.summary()})"
            )

            return response

        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse decomposition JSON (this is rare with prefill): {e}. "
                f"Response was: {response.content[:200]}..."
            )
            # Fallback: treat as atomic problem
            # Note: With JSON prefill, this should rarely happen
            fallback = {
                "analysis": "The LLM response could not be parsed as JSON. Treating as an atomic problem that cannot be decomposed further.",
                "is_atomic": True,
                "sub_problems": [
                    {
                        "id": "sp_001",
                        "goal": problem_description,
                        "context": context,
                        "complexity_score": 5,
                        "dependencies": [],
                        "rationale": "Atomic problem - JSON parsing fallback triggered.",
                    }
                ],
            }
            # Update response content with fallback
            response.content = json.dumps(fallback)
            return response
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

    async def identify_information_gaps(
        self,
        problem_description: str,
        sub_problems: list[dict[str, Any]],
        business_context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Identify information gaps that need to be filled before deliberation.

        Categorizes gaps as:
        - INTERNAL: Business data only the user can provide (churn rate, revenue, etc.)
        - EXTERNAL: Publicly researchable information (industry benchmarks, competitor data)

        Each gap is classified as CRITICAL or NICE_TO_HAVE based on impact on deliberation quality.

        Args:
            problem_description: The main problem being addressed
            sub_problems: List of sub-problems from decomposition
            business_context: Optional business context already collected

        Returns:
            LLMResponse with:
            - content: JSON string with information gaps
            - Format: {
                "internal_gaps": [
                    {"question": "...", "priority": "CRITICAL|NICE_TO_HAVE", "reason": "..."}
                ],
                "external_gaps": [
                    {"question": "...", "priority": "CRITICAL|NICE_TO_HAVE", "reason": "..."}
                ]
            }

        Examples:
            >>> agent = DecomposerAgent()
            >>> response = await agent.identify_information_gaps(
            ...     "Should I invest $50K in SEO or paid ads?",
            ...     sub_problems=[...],
            ...     business_context={"business_model": "B2B SaaS"}
            ... )
            >>> gaps = json.loads(response.content)
        """
        logger.info("Identifying information gaps for deliberation")

        # Build context summary
        context_summary = ""
        if business_context:
            context_summary = "Business context already provided:\n"
            for key, value in business_context.items():
                context_summary += f"- {key}: {value}\n"
        else:
            context_summary = "No business context provided yet.\n"

        # Build sub-problems summary
        sub_problems_summary = "Sub-problems to be deliberated:\n"
        for i, sp in enumerate(sub_problems, 1):
            sub_problems_summary += f"{i}. {sp.get('goal', 'Unknown goal')}\n"

        # Create prompt
        user_message = f"""<problem>
{problem_description}
</problem>

<sub_problems>
{sub_problems_summary}
</sub_problems>

<existing_context>
{context_summary}
</existing_context>

<task>
Analyze what information is needed for a high-quality deliberation on this problem.

Identify information gaps in two categories:

1. **INTERNAL gaps**: Business-specific data that only the user can provide
   Examples:
   - Current metrics (revenue, churn rate, customer acquisition cost, etc.)
   - Internal capabilities (team size, technical skills, etc.)
   - Historical performance data
   - Budget constraints
   - Strategic priorities

2. **EXTERNAL gaps**: Information that can be researched from public sources
   Examples:
   - Industry benchmarks (average SaaS churn rate, typical conversion rates, etc.)
   - Market research (market size, growth trends, etc.)
   - Competitor analysis (competitor pricing, features, positioning)
   - Best practices (what successful companies have done)
   - Technical standards or requirements

For each gap:
- Write a clear, specific question
- Classify priority as CRITICAL (essential for good recommendations) or NICE_TO_HAVE (helpful but not essential)
- Explain why this information matters

Respond with JSON in this format:
{{
  "internal_gaps": [
    {{"question": "...", "priority": "CRITICAL", "reason": "..."}}
  ],
  "external_gaps": [
    {{"question": "...", "priority": "NICE_TO_HAVE", "reason": "..."}}
  ]
}}

Be specific and targeted. Only include gaps that would materially improve deliberation quality.
</task>
"""

        # Create prompt request
        request = PromptRequest(
            system="You are an expert at identifying information needs for strategic decision-making. You help ensure deliberations have all necessary context for high-quality recommendations.",
            user_message=user_message,
            model=MODEL_BY_ROLE["decomposer"],  # Use Sonnet for analysis
            prefill="{",  # Ensure JSON response
            cache_system=False,
            phase="information_gap_analysis",
            agent_type="DecomposerAgent",
        )

        # Call LLM
        response = await self.broker.call(request)

        # Validate JSON structure
        try:
            gaps = json.loads(response.content)

            # Validate structure
            if "internal_gaps" not in gaps:
                gaps["internal_gaps"] = []
            if "external_gaps" not in gaps:
                gaps["external_gaps"] = []

            internal_count = len(gaps["internal_gaps"])
            external_count = len(gaps["external_gaps"])

            logger.info(
                f"Information gap analysis complete: {internal_count} internal, "
                f"{external_count} external ({response.summary()})"
            )

            return response

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse information gaps JSON: {e}")
            # Fallback: return empty gaps
            fallback: dict[str, list[dict[str, Any]]] = {"internal_gaps": [], "external_gaps": []}
            response.content = json.dumps(fallback)
            return response
