"""Persona selection agent.

Recommends optimal personas for a given problem based on domain expertise,
problem complexity, and perspective diversity.

Includes semantic caching to reduce LLM API costs by 40-60%.
"""

import json
from typing import Any

from bo1.agents.base import BaseAgent
from bo1.agents.persona_cache import get_persona_cache
from bo1.config import MODEL_BY_ROLE
from bo1.data import get_active_personas, get_persona_by_code
from bo1.llm.response import LLMResponse
from bo1.models.problem import SubProblem
from bo1.prompts.selector_prompts import SELECTOR_PREFILL, SELECTOR_SYSTEM_PROMPT
from bo1.utils.json_parsing import parse_json_with_fallback
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


def _get_sp_attr(sp: SubProblem | dict[str, Any], attr: str, default: Any = None) -> Any:
    """Safely get attribute from sub_problem (handles both dict and object).

    After checkpoint restoration, SubProblem objects may be deserialized as dicts.
    This helper handles both cases.
    """
    if sp is None:
        return default
    if isinstance(sp, dict):
        return sp.get(attr, default)
    return getattr(sp, attr, default)


class PersonaSelectorAgent(BaseAgent):
    """Agent that recommends personas for deliberation.

    Analyzes the problem domain and complexity to recommend 3-5 expert personas
    that provide comprehensive coverage and diverse perspectives.

    Uses Sonnet 4.5 for complex persona selection analysis.
    """

    def get_default_model(self) -> str:
        """Return default model for persona selector."""
        return MODEL_BY_ROLE["selector"]

    async def recommend_personas(
        self,
        sub_problem: SubProblem,
        problem_context: str = "",
        target_count: int | None = None,
    ) -> LLMResponse:
        """Recommend personas for a given sub-problem with semantic caching.

        Uses LLM to analyze the problem and recommend the specified number of
        expert personas based on domain expertise and perspective diversity.

        Checks semantic cache first - if similar problem found (similarity >0.90),
        returns cached personas to save $0.01-0.02 per call.

        Args:
            sub_problem: The sub-problem to deliberate on
            problem_context: Additional context about the overall problem
            target_count: Target number of experts (3-5, default: adaptive based on complexity)

        Returns:
            LLMResponse with:
            - content: JSON string with recommendation (parse with json.loads())
            - token_usage: Detailed token breakdown
            - cost_total: Total cost in USD (or ~$0.00006 if cache hit)
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
        logger.info(
            f"Recommending personas for sub-problem: {_get_sp_attr(sub_problem, 'id', 'unknown')}"
        )

        # Step 1: Check semantic cache for similar problems
        cache = get_persona_cache()
        cached_personas = await cache.get(sub_problem)

        if cached_personas:
            # CACHE HIT - Return cached personas without LLM call
            # Create synthetic response with cached personas
            cached_recommendation = {
                "analysis": f"[CACHED] Retrieved {len(cached_personas)} cached personas for similar problem (similarity >0.90)",
                "recommended_personas": [
                    {
                        "code": p.code,
                        "name": p.name,
                        "rationale": f"{p.description} (cached selection)",
                    }
                    for p in cached_personas
                ],
                "coverage_summary": f"Cached team of {len(cached_personas)} experts from similar problem analysis.",
            }

            # Create LLMResponse with minimal cost (embedding only, ~$0.00006)
            from bo1.llm.client import TokenUsage
            from bo1.llm.response import LLMResponse

            return LLMResponse(
                content=json.dumps(cached_recommendation),
                token_usage=TokenUsage(
                    input_tokens=0,
                    output_tokens=0,
                    cache_creation_tokens=0,
                    cache_read_tokens=0,
                ),
                model="cached",
                duration_ms=50,  # Fast cache lookup
            )

        # Load available personas
        available_personas = get_active_personas()

        # Build persona catalog summary for LLM
        persona_catalog = self._format_persona_catalog(available_personas)

        # Calculate effective target count (default to 4 if not specified)
        effective_target = target_count if target_count is not None else 4

        # Compose selection request with explicit target count
        user_message = f"""## Problem to Deliberate

**Goal**: {_get_sp_attr(sub_problem, "goal", "")}

**Context**: {_get_sp_attr(sub_problem, "context", "")}

**Complexity Score**: {_get_sp_attr(sub_problem, "complexity_score", 5)}/10

**Additional Problem Context**: {problem_context or "None provided"}

## Available Personas

{persona_catalog}

## Instructions

Analyze this problem and recommend EXACTLY {effective_target} personas from the catalog above.
Ensure domain coverage, perspective diversity, and appropriate expertise depth.

IMPORTANT: Select exactly {effective_target} personas - no more, no less. This count is optimized
for the problem complexity (simpler problems need fewer experts, complex problems need more).

Provide your recommendation as JSON following the format in your system prompt.
"""

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=SELECTOR_SYSTEM_PROMPT,
            user_message=user_message,
            phase="selection",
            prefill=SELECTOR_PREFILL,
            cache_system=False,
        )

        # Validate JSON structure with robust parsing
        try:
            # Use parse_json_with_fallback for resilient JSON parsing
            # This handles extra text after JSON, markdown code blocks, etc.
            recommendation, parse_errors = parse_json_with_fallback(
                content=response.content,
                context="persona selection",
                logger=logger,
            )

            if recommendation is None:
                raise json.JSONDecodeError(
                    f"All parsing strategies failed: {parse_errors}",
                    response.content,
                    0,
                )

            # Validate structure
            if "recommended_personas" not in recommendation:
                raise ValueError("Response missing 'recommended_personas' field")

            persona_codes = [p["code"] for p in recommendation["recommended_personas"]]
            logger.info(
                f"Recommended {len(persona_codes)} personas: {', '.join(persona_codes)} "
                f"({response.summary()})"
            )

            # Step 2: Validate for domain overlap and filter duplicates
            # Convert persona codes to PersonaProfile objects
            from bo1.models.persona import PersonaProfile

            selected_personas = []
            seen_domains: set[str] = set()

            for code in persona_codes:
                persona_dict = get_persona_by_code(code)
                if persona_dict:
                    persona = PersonaProfile.model_validate(persona_dict)

                    # Check for domain overlap
                    # Parse domain_expertise (PostgreSQL array format: "{domain1,domain2}")
                    domain_str = persona_dict.get("domain_expertise", "")
                    if isinstance(domain_str, str):
                        # Remove curly braces and split by comma
                        domain_str = domain_str.strip("{}")
                        persona_domains = {d.strip() for d in domain_str.split(",") if d.strip()}
                    else:
                        persona_domains = set()

                    # If there's significant overlap (>50% of domains), skip this persona
                    if seen_domains and persona_domains:
                        overlap = len(persona_domains & seen_domains)
                        overlap_ratio = overlap / len(persona_domains) if persona_domains else 0

                        if overlap_ratio > 0.5:
                            logger.warning(
                                f"Skipping {code} ({persona_dict.get('name')}) due to domain overlap: "
                                f"{overlap}/{len(persona_domains)} domains already covered. "
                                f"Domains: {persona_domains}, Seen: {seen_domains}"
                            )
                            continue

                    selected_personas.append(persona)
                    seen_domains.update(persona_domains)

            # Log if count doesn't match target (for observability)
            if len(selected_personas) != effective_target:
                logger.info(
                    f"Expert count mismatch: target={effective_target}, selected={len(selected_personas)} "
                    f"(before={len(persona_codes)}, after domain filtering)"
                )

            # Ensure we have at least min(2, target) personas (in case filtering was too aggressive)
            min_required = min(2, effective_target)
            if len(selected_personas) < min_required and len(persona_codes) >= min_required:
                logger.warning(
                    f"Domain overlap filtering reduced selection to {len(selected_personas)} personas. "
                    f"Reverting to original selection."
                )
                selected_personas = []
                for code in persona_codes:
                    persona_dict = get_persona_by_code(code)
                    if persona_dict:
                        selected_personas.append(PersonaProfile.model_validate(persona_dict))

            # Store in cache (async, don't block on errors)
            try:
                await cache.set(sub_problem, selected_personas)
            except Exception as e:
                logger.warning(f"Failed to cache persona selection: {e}")

            # Update response content to reflect filtered personas
            # This ensures nodes.py uses the filtered list, not the original LLM recommendation
            filtered_recommendation = recommendation.copy()
            filtered_recommendation["recommended_personas"] = [
                {
                    "code": p.code,
                    "name": p.name,
                    "rationale": next(
                        (
                            rec["rationale"]
                            for rec in recommendation["recommended_personas"]
                            if rec["code"] == p.code
                        ),
                        f"Selected for expertise in {persona_dict.get('domain_expertise', '')}",
                    ),
                }
                for p in selected_personas
                # Get persona_dict for each selected persona
                if (persona_dict := get_persona_by_code(p.code))
            ]
            response.content = json.dumps(filtered_recommendation)

            logger.info(
                f"Final selection after filtering: {len(selected_personas)} personas: "
                f"{', '.join(p.code for p in selected_personas)}"
            )

            return response

        except json.JSONDecodeError as e:
            logger.error(
                f"⚠️ FALLBACK: Failed to parse persona selection JSON (rare with prefill). "
                f"Using default persona recommendation. "
                f"Error: {e}. Response: {response.content[:200]}..."
            )
            # Fallback: use default personas
            fallback = self._get_default_recommendation()
            logger.warning(
                f"⚠️ FALLBACK: Default personas selected: "
                f"{[r['code'] for r in fallback['recommended_personas']]}"
            )
            # Update response content with fallback
            response.content = json.dumps(fallback)
            return response
        except Exception as e:
            logger.error(
                f"⚠️ FALLBACK: Unexpected error during persona selection. Re-raising exception. "
                f"Error: {e}"
            )
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
        Uses persona codes that exist in bo1/data/personas.json.
        """
        logger.warning("Using default persona recommendation due to parsing error")
        return {
            "analysis": "Using default persona set due to recommendation error.",
            "recommended_personas": [
                {
                    "code": "product_manager",  # Exists in personas.json
                    "name": "Priya Desai",
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
