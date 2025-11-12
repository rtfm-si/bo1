"""Persona selection agent.

Recommends optimal personas for a given problem based on domain expertise,
problem complexity, and perspective diversity.
"""

import json
import logging
from typing import Any

from bo1.config import MODEL_BY_ROLE
from bo1.data import get_active_personas, get_persona_by_code
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.response import LLMResponse
from bo1.models.problem import SubProblem

logger = logging.getLogger(__name__)


# System prompt for persona selection
SELECTOR_SYSTEM_PROMPT = """You are a persona selection expert for the Board of One deliberation system.

Your role is to recommend 3-5 expert personas for a given problem to ensure:
1. **Domain coverage**: The problem's key domains are represented
2. **Perspective diversity**: Strategic, tactical, technical, and human perspectives
3. **Appropriate expertise depth**: Match persona expertise to problem complexity

## Selection Principles

### Core Coverage (Always Include)
- **Strategic thinker**: For high-level direction and trade-offs
- **Domain expert**: For specific domain knowledge (finance, marketing, tech, etc.)
- **Practical operator**: For execution feasibility and real-world constraints

### Supplementary Roles (Add Based on Problem)
- **Contrarian/skeptic**: For complex or risky decisions
- **User advocate**: For product or customer-facing decisions
- **Technical expert**: For technical implementation questions
- **Financial analyst**: For investment or budget decisions

### Diversity Guidelines
- **Balance perspectives**: Mix strategic + tactical + technical
- **Avoid redundancy**: Don't select multiple personas with identical expertise
- **Match complexity**: Simple problems (3 personas), Complex problems (5 personas)

## Problem Domains

Common problem domains and recommended persona categories:
- **Pricing/Business Model**: finance, marketing, strategy
- **Product Direction**: product, technology, user_research
- **Growth/Marketing**: marketing, growth, finance
- **Technical Decisions**: technology, product, operations
- **Team/Hiring**: leadership, operations, finance
- **Strategic Pivots**: strategy, finance, leadership

## Output Format

Respond with JSON:

```json
{
  "analysis": "Brief analysis of problem domain and key decision factors (2-3 sentences)",
  "recommended_personas": [
    {
      "code": "persona_code",
      "name": "Persona Name",
      "rationale": "Why this persona is essential for this problem (1-2 sentences)"
    }
  ],
  "coverage_summary": "How the selected personas provide comprehensive coverage (1 sentence)"
}
```

## Example

**Problem**: "Should I invest $50K in SEO or paid ads?"
**Complexity**: 6/10

**Output**:
```json
{
  "analysis": "This is a growth investment decision requiring financial analysis, marketing channel expertise, and execution planning. The $50K budget and 6-month timeline create significant constraints.",
  "recommended_personas": [
    {
      "code": "finance_strategist",
      "name": "Maria Santos",
      "rationale": "Will analyze ROI, payback period, and financial constraints to ensure the investment aligns with business metrics."
    },
    {
      "code": "growth_hacker",
      "name": "Zara Morales",
      "rationale": "Brings expertise in evaluating growth channels, understanding funnel metrics, and rapid testing to identify the most scalable option."
    },
    {
      "code": "digital_marketer",
      "name": "Alex Chen",
      "rationale": "Provides tactical execution knowledge for both SEO and paid ads, including realistic timelines and skill requirements."
    },
    {
      "code": "product_strategist",
      "name": "Jordan Kim",
      "rationale": "Will ensure the chosen channel aligns with product positioning and target customer acquisition strategy."
    }
  ],
  "coverage_summary": "This team balances financial rigor (Maria), channel expertise (Zara, Alex), and strategic alignment (Jordan) to provide comprehensive guidance on growth investment."
}
```

## Your Task

When given a problem, analyze it and recommend 3-5 personas from the available persona catalog.
Ensure diversity, domain coverage, and appropriate expertise depth.
"""


class PersonaSelectorAgent:
    """Agent that recommends personas for deliberation.

    Analyzes the problem domain and complexity to recommend 3-5 expert personas
    that provide comprehensive coverage and diverse perspectives.

    Uses Sonnet 4.5 for complex persona selection analysis.
    """

    def __init__(self, broker: PromptBroker | None = None) -> None:
        """Initialize the persona selector agent.

        Args:
            broker: Optional PromptBroker instance. If None, creates a new one.
        """
        self.broker = broker or PromptBroker()
        self.model_name = MODEL_BY_ROLE["selector"]

    async def recommend_personas(
        self,
        sub_problem: SubProblem,
        problem_context: str = "",
    ) -> LLMResponse:
        """Recommend personas for a given sub-problem.

        Uses LLM to analyze the problem and recommend 3-5 expert personas
        based on domain expertise, complexity, and perspective diversity.

        Args:
            sub_problem: The sub-problem to deliberate on
            problem_context: Additional context about the overall problem

        Returns:
            LLMResponse with:
            - content: JSON string with recommendation (parse with json.loads())
            - token_usage: Detailed token breakdown
            - cost_total: Total cost in USD
            - All other comprehensive metrics

        Examples:
            >>> agent = PersonaSelectorAgent()
            >>> response = await agent.recommend_personas(
            ...     sub_problem=SubProblem(
            ...         id="sp_001",
            ...         goal="Should I invest $50K in SEO or paid ads?",
            ...         context="Solo founder, SaaS product, $100K ARR",
            ...         complexity_score=6,
            ...     )
            ... )
            >>> recommendation = json.loads(response.content)
            >>> len(recommendation["recommended_personas"])
            4
        """
        logger.info(f"Recommending personas for sub-problem: {sub_problem.id}")

        # Load available personas
        available_personas = get_active_personas()

        # Build persona catalog summary for LLM
        persona_catalog = self._format_persona_catalog(available_personas)

        # Compose selection request
        user_message = f"""## Problem to Deliberate

**Goal**: {sub_problem.goal}

**Context**: {sub_problem.context}

**Complexity Score**: {sub_problem.complexity_score}/10

**Additional Problem Context**: {problem_context or "None provided"}

## Available Personas

{persona_catalog}

## Instructions

Analyze this problem and recommend 3-5 personas from the catalog above.
Ensure domain coverage, perspective diversity, and appropriate expertise depth.

Provide your recommendation as JSON following the format in your system prompt.
"""

        # Create prompt request
        request = PromptRequest(
            system=SELECTOR_SYSTEM_PROMPT,
            user_message=user_message,
            model=self.model_name,
            prefill="{",  # Ensure JSON response starts with {
            cache_system=False,  # No caching needed for one-off selection
            phase="selection",
            agent_type="PersonaSelectorAgent",
        )

        # Call LLM via broker (handles retry/rate-limit)
        response = await self.broker.call(request)

        # Validate JSON structure
        try:
            recommendation = json.loads(response.content)

            # Validate structure
            if "recommended_personas" not in recommendation:
                raise ValueError("Response missing 'recommended_personas' field")

            persona_codes = [p["code"] for p in recommendation["recommended_personas"]]
            logger.info(
                f"Recommended {len(persona_codes)} personas: {', '.join(persona_codes)} "
                f"({response.summary()})"
            )

            return response

        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse persona selection JSON (rare with prefill): {e}. "
                f"Response was: {response.content[:200]}..."
            )
            # Fallback: use default personas
            fallback = self._get_default_recommendation()
            # Update response content with fallback
            response.content = json.dumps(fallback)
            return response
        except Exception as e:
            logger.error(f"Error during persona selection: {e}")
            raise

    def _format_persona_catalog(self, personas: list[dict[str, Any]]) -> str:
        """Format persona catalog for LLM prompt.

        Args:
            personas: List of persona dictionaries

        Returns:
            Formatted string with persona information
        """
        lines = []
        for p in personas:
            lines.append(
                f"- **{p['code']}** ({p['name']}): {p['description']}"
                f"\n  Category: {p.get('category', 'general')}, "
                f"Expertise: {p.get('domain_expertise', 'general')}"
            )
        return "\n".join(lines)

    def _get_default_recommendation(self) -> dict[str, Any]:
        """Get a default persona recommendation as fallback.

        Returns a safe default set of personas covering key perspectives.
        """
        logger.warning("Using default persona recommendation due to parsing error")
        return {
            "analysis": "Using default persona set due to recommendation error.",
            "recommended_personas": [
                {
                    "code": "product_strategist",
                    "name": "Jordan Kim",
                    "rationale": "Strategic perspective on product decisions",
                },
                {
                    "code": "finance_strategist",
                    "name": "Maria Santos",
                    "rationale": "Financial analysis and budget considerations",
                },
                {
                    "code": "growth_hacker",
                    "name": "Zara Morales",
                    "rationale": "Growth and marketing expertise",
                },
            ],
            "coverage_summary": "Default balanced team with strategic, financial, and growth perspectives.",
        }

    def validate_persona_codes(self, persona_codes: list[str]) -> tuple[bool, list[str]]:
        """Validate that persona codes exist in the catalog.

        Args:
            persona_codes: List of persona codes to validate

        Returns:
            Tuple of (is_valid, list of invalid codes)
        """
        invalid_codes = []

        for code in persona_codes:
            persona = get_persona_by_code(code)
            if persona is None:
                invalid_codes.append(code)

        is_valid = len(invalid_codes) == 0

        if not is_valid:
            logger.warning(f"Invalid persona codes: {', '.join(invalid_codes)}")

        return is_valid, invalid_codes

    def get_personas_by_codes(self, persona_codes: list[str]) -> list[dict[str, Any]]:
        """Get full persona data for a list of codes.

        Args:
            persona_codes: List of persona codes

        Returns:
            List of persona dictionaries (only valid codes)
        """
        personas = []
        for code in persona_codes:
            persona = get_persona_by_code(code)
            if persona:
                personas.append(persona)
            else:
                logger.warning(f"Skipping invalid persona code: {code}")

        logger.info(f"Retrieved {len(personas)} personas from {len(persona_codes)} codes")
        return personas
