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
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


# System prompt for persona selection
SELECTOR_SYSTEM_PROMPT = """You are a persona selection expert for the Board of One deliberation system.

Your role is to recommend 2-5 expert personas for a given problem to ensure:
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
- **Avoid redundancy**: NEVER select multiple personas with identical or wholly overlapping expertise domains (e.g., don't select both a CFO and a Financial Strategist, or a Marketing Director and a Growth Hacker). Each persona must bring a UNIQUE contribution and perspective.
- **Match complexity**: Simple problems (2-3 personas), Complex problems (4-5 personas)
- **Quality over quantity**: Select the BEST 2-max cap personas with the most relevant expertise. Do NOT populate the board unnecessarily - only include experts who will add distinct, valuable perspectives.

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

---

**Example 2 - Technical Architecture Decision**:

**Problem**: "Should we migrate from monolith to microservices?"
**Complexity**: 8/10
**Context**: Series B SaaS, 50 engineers, experiencing scaling issues

**Output**:
```json
{
  "analysis": "This is a complex technical decision with organizational and financial implications. Requires architecture expertise, team/culture perspective, and long-term cost modeling.",
  "recommended_personas": [
    {
      "code": "cto",
      "name": "Alex Chen",
      "rationale": "Strategic technology decision requiring assessment of architecture patterns, scalability needs, and long-term technical vision. CTO perspective balances technical and business considerations."
    },
    {
      "code": "devops_engineer",
      "name": "Jordan Kim",
      "rationale": "Hands-on expertise in microservices implementation, deployment complexity, and operational overhead. Will provide realistic assessment of infrastructure requirements and team skill gaps."
    },
    {
      "code": "engineering_manager",
      "name": "Sam Taylor",
      "rationale": "Organizational impact perspective: how microservices affect team structure (Conway's Law), onboarding, and development velocity. Critical for assessing cultural/process changes."
    },
    {
      "code": "cfo",
      "name": "Maria Santos",
      "rationale": "Financial modeling of migration costs ($500K-2M estimate), opportunity cost, and long-term maintenance savings. Ensures ROI justification beyond technical elegance."
    }
  ],
  "coverage_summary": "Balances strategic tech vision (CTO), hands-on implementation (DevOps), organizational change (Eng Manager), and financial feasibility (CFO) for comprehensive assessment."
}
```

---

**Example 3 - Hiring Decision**:

**Problem**: "Should I hire a co-founder 12 months into my startup?"
**Complexity**: 7/10
**Context**: Non-technical founder, MVP launched, $200K angel round raised, considering technical co-founder

**Output**:
```json
{
  "analysis": "This is a high-stakes people decision with equity, cultural, and strategic implications. Requires startup experience, equity/legal expertise, and relationship dynamics understanding.",
  "recommended_personas": [
    {
      "code": "startup_founder",
      "name": "Casey Morgan",
      "rationale": "First-hand experience with co-founder dynamics at different startup stages. Can assess timing (12 months in), equity split implications, and whether technical skills justify co-founder title vs early employee."
    },
    {
      "code": "startup_lawyer",
      "name": "Riley Adams",
      "rationale": "Legal structure and equity implications. 12 months in, cap table already set; adding co-founder affects vesting, founder shares, and investor rights. Critical to structure correctly."
    },
    {
      "code": "executive_coach",
      "name": "Morgan Lee",
      "rationale": "Relationship and cultural fit assessment. Co-founder relationships are like marriages - need to evaluate working styles, decision-making compatibility, and conflict resolution before committing."
    },
    {
      "code": "cto",
      "name": "Alex Chen",
      "rationale": "Technical assessment of candidate's skills. Is this person truly co-founder caliber (rare, senior) or strong senior engineer (more common)? Equity/title should match true value."
    }
  ],
  "coverage_summary": "Combines startup experience (Casey), legal/equity guidance (Riley), relationship dynamics (Morgan), and technical assessment (Alex) for comprehensive evaluation."
}
```

---

**Example 4 - BAD SELECTION (Anti-pattern)**:

**Problem**: "Should I invest $50K in SEO or paid ads?"
**Complexity**: 6/10

❌ **WRONG Selection** (Redundant expertise):
```json
{
  "recommended_personas": [
    {"code": "growth_hacker", "name": "Zara", "rationale": "Growth expertise"},
    {"code": "digital_marketer", "name": "Alex", "rationale": "Marketing channels expertise"},
    {"code": "marketing_director", "name": "Sam", "rationale": "Marketing strategy"},
    {"code": "seo_specialist", "name": "Taylor", "rationale": "SEO expertise"},
    {"code": "ppc_specialist", "name": "Jordan", "rationale": "Paid ads expertise"}
  ]
}
```

**Why WRONG**:
- 5 personas with OVERLAPPING expertise (all marketing domain)
- Growth Hacker + Digital Marketer + Marketing Director = redundant high-level marketing perspectives
- SEO Specialist + PPC Specialist = too tactical; experts will just advocate for their specialty
- MISSING financial perspective (ROI, cash flow, payback period)
- MISSING product/strategy perspective (how channel choice affects positioning)
- MISSING execution perspective (solo founder capacity to execute either strategy)

✅ **CORRECT Selection** (Diverse perspectives):
```json
{
  "recommended_personas": [
    {"code": "growth_hacker", "name": "Zara", "rationale": "Channel evaluation expertise, growth metrics, testing frameworks"},
    {"code": "cfo", "name": "Maria", "rationale": "Financial analysis: ROI timeline, cash flow impact, budget optimization"},
    {"code": "product_strategist", "name": "Jordan", "rationale": "Strategic alignment: how channel choice affects product positioning and customer acquisition strategy"},
    {"code": "operations_manager", "name": "Sam", "rationale": "Execution feasibility: solo founder capacity, skill requirements, time allocation"}
  ]
}
```

**Why CORRECT**:
- Diverse domains: Marketing (Zara), Finance (Maria), Strategy (Jordan), Operations (Sam)
- Each persona brings UNIQUE perspective
- Financial + Growth + Strategy + Execution = comprehensive coverage
- 4 personas (not 5) - quality over quantity

## Justification Quality Criteria

STRONG JUSTIFICATION (✅):
- Cites specific problem characteristics: "$50K budget creates constraint...", "12 months into startup affects equity split..."
- Explains WHY this persona's expertise is essential for THIS problem
- Names specific frameworks, methods, or domain knowledge persona will contribute
- Example: "Will analyze ROI using payback period methodology, considering 6-month SEO lag vs immediate paid ads results"

WEAK JUSTIFICATION (❌):
- Generic descriptions: "Good strategic thinker", "Brings valuable perspective"
- Doesn't cite problem specifics
- Could apply to any problem
- Example: "Will provide marketing expertise"

## Your Task

When given a problem, analyze it and recommend 3-5 personas from the available persona catalog.
Ensure diversity, domain coverage, and appropriate expertise depth.
"""


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
    ) -> LLMResponse:
        """Recommend personas for a given sub-problem with semantic caching.

        Uses LLM to analyze the problem and recommend 3-5 expert personas
        based on domain expertise, complexity, and perspective diversity.

        Checks semantic cache first - if similar problem found (similarity >0.90),
        returns cached personas to save $0.01-0.02 per call.

        Args:
            sub_problem: The sub-problem to deliberate on
            problem_context: Additional context about the overall problem

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
        logger.info(f"Recommending personas for sub-problem: {sub_problem.id}")

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

        # Use new helper method instead of manual PromptRequest creation
        response = await self._create_and_call_prompt(
            system=SELECTOR_SYSTEM_PROMPT,
            user_message=user_message,
            phase="selection",
            prefill="{",
            cache_system=False,
        )

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

            # Ensure we have at least 2 personas (in case filtering was too aggressive)
            if len(selected_personas) < 2 and len(persona_codes) >= 2:
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
                f"{[r['code'] for r in fallback['recommendations']]}"
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
