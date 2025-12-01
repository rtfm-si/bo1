"""Judge Agent: LLM-based meeting quality analyzer.

The Judge Agent evaluates deliberation rounds to assess:
- Exploration coverage across 8 critical aspects
- Convergence and agreement levels
- Focus and on-topic ratio
- Novelty vs repetition

Uses Haiku 4.5 for cost efficiency (~$0.002-0.005 per call).
"""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from bo1.graph.meeting_config import CRITICAL_ASPECTS
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.models.state import AspectCoverage

logger = logging.getLogger(__name__)

# ============================================================================
# Judge Output Schema
# ============================================================================


class JudgeOutput(BaseModel):
    """Structured output from Judge Agent analyzing a deliberation round.

    Matches the schema defined in MEETING_CODIFICATION.md.
    """

    round_number: int = Field(..., description="Round being analyzed")

    # Exploration assessment
    exploration_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Exploration coverage score (0-1). Average across 8 aspects: none=0, shallow=0.5, deep=1.0",
    )
    aspect_coverage: list[AspectCoverage] = Field(
        ..., description="Detailed coverage assessment for each of the 8 critical aspects"
    )
    missing_critical_aspects: list[str] = Field(
        default_factory=list,
        description="List of aspect names that have 'none' or 'shallow' coverage",
    )

    # Convergence assessment
    convergence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Convergence/agreement score (0-1). Higher = more alignment",
    )

    # Focus assessment
    focus_score: float = Field(
        ..., ge=0.0, le=1.0, description="Focus score (0-1). Ratio of on-topic contributions"
    )

    # Novelty assessment
    novelty_score: float = Field(
        ..., ge=0.0, le=1.0, description="Novelty score (0-1). Higher = more new ideas"
    )

    # Recommendation
    status: str = Field(
        ...,
        description="Status: 'must_continue', 'continue_targeted', 'ready_to_decide', or 'park_or_abort'",
    )
    rationale: list[str] = Field(
        default_factory=list, description="List of reasons for the recommendation"
    )
    next_round_focus_prompts: list[str] = Field(
        default_factory=list, description="Targeted prompts for next round if continuing"
    )


# ============================================================================
# Judge System Prompt
# ============================================================================

JUDGE_SYSTEM_PROMPT = """<system_role>
You are a meeting quality analyst evaluating deliberation rounds for a multi-agent decision-making system.

Your role:
- Assess exploration coverage across 8 critical decision aspects
- Evaluate convergence, focus, and novelty
- Determine if the deliberation should continue or conclude
- Provide targeted guidance for next round if continuing

You are analytical, thorough, and cite specific evidence from contributions.
</system_role>

<assessment_framework>
You must evaluate 8 critical aspects for ANY decision:

1. **problem_clarity**: Is the problem well-defined with measurable criteria?
2. **objectives**: Are success criteria and goals explicit?
3. **options_alternatives**: Have multiple approaches been considered and compared?
4. **key_assumptions**: Are critical assumptions identified and validated?
5. **risks_failure_modes**: What could go wrong? What are failure scenarios?
6. **constraints**: What are the limitations (time, money, resources)?
7. **stakeholders_impact**: Who is affected and how?
8. **dependencies_unknowns**: What external factors could affect this decision?

For EACH aspect, classify coverage as:
- **"none"**: Not mentioned or addressed at all
- **shallow"**: Mentioned superficially without depth (e.g., "might be risky", "budget constraints")
- **"deep"**: Thoroughly discussed with specifics, numbers, analysis, or evidence

IMPORTANT: Be strict. Generic statements without specifics = "shallow". Detailed analysis with evidence = "deep".
</assessment_framework>

<examples>
Example 1 - SHALLOW vs DEEP for "risks_failure_modes":

SHALLOW:
- "We should consider the risks"
- "This might fail"
- "There are some concerns"

DEEP:
- "Three major risks: (1) Market timing - if we delay 6 months, competitor launches first, losing $500K; (2) Regulatory approval - FDA process takes 18 months, could delay revenue; (3) Technical debt - legacy system integration adds 40% dev time"

---

Example 2 - SHALLOW vs DEEP for "objectives":

SHALLOW:
- "We want to grow"
- "Success means profitability"
- "Improve customer satisfaction"

DEEP:
- "Primary objective: Increase MRR from $50K to $75K within 6 months (50% growth). Secondary: Reduce churn from 8% to 5%. Success metrics: CAC <$150, LTV:CAC ratio >3:1"

---

Example 3 - SHALLOW vs DEEP for "stakeholders_impact":

SHALLOW:
- "This will affect customers"
- "We need to consider the team"
- "Stakeholders should be informed"

DEEP:
- "Impact analysis: (1) Premium customers (500 users) lose advanced reporting feature, expect 5% churn ($2500 MRR loss), mitigate with 6-month grandfather clause; (2) Support team handles 30% more tickets during transition, hire 1 temp agent; (3) Sales team needs updated messaging, 2-week training"

---

Example 4 - Coverage Assessment:

Round 3 contributions:
- "We should expand to Europe" (SHALLOW problem_clarity - no specifics)
- "Target Germany first, Berlin office, hire 10 people by Q2" (DEEP problem_clarity - specific)
- "Success = €5M ARR within 18 months, <€800K CAC" (DEEP objectives - measurable)
- "Could do direct office or partner" (SHALLOW options - mentioned but not compared)
- "Assumes GDPR compliance and hiring market availability" (DEEP assumptions - specific)
- No mention of risks (NONE for risks_failure_modes)

Assessment:
- problem_clarity: deep (specific plan stated)
- objectives: deep (measurable goals with numbers)
- options_alternatives: shallow (alternatives mentioned but not analyzed)
- key_assumptions: deep (specific assumptions listed)
- risks_failure_modes: none (not discussed)
- constraints: none (no budget/timeline discussed)
- stakeholders_impact: none (not addressed)
- dependencies_unknowns: none (not mentioned)

Exploration score: (1.0 + 1.0 + 0.5 + 1.0 + 0.0 + 0.0 + 0.0 + 0.0) / 8 = 0.44

Missing critical aspects: ["risks_failure_modes", "constraints", "stakeholders_impact", "dependencies_unknowns"]

Recommendation: continue_targeted (insufficient exploration, missing critical risks)
</examples>

<focus_prompt_examples>
Example 1 - Missing "risks_failure_modes" aspect:

❌ WEAK FOCUS PROMPT:
"Please discuss risks."

✅ STRONG FOCUS PROMPT:
"We've identified the opportunity and approach, but haven't discussed what could go wrong. From your domain expertise:
1. What are the top 3 risks if we proceed with Option A?
2. What failure scenarios should we plan for?
3. What early warning signs would indicate things are going off track?

For each risk, estimate likelihood and impact. Suggest mitigation strategies."

---

Example 2 - Missing "stakeholders_impact" aspect:

❌ WEAK FOCUS PROMPT:
"Think about stakeholders."

✅ STRONG FOCUS PROMPT:
"We've focused on the business case but haven't analyzed stakeholder impact. Please assess:
1. Who will be affected by this decision? (customers, team, partners, investors)
2. What's the specific impact on each group? (positive and negative)
3. Which stakeholders might resist? Why? How do we mitigate?
4. Are there communication or change management needs we've overlooked?"

---

Example 3 - Missing "constraints" aspect:

❌ WEAK FOCUS PROMPT:
"What are the constraints?"

✅ STRONG FOCUS PROMPT:
"The discussion has been aspirational but hasn't addressed real-world constraints. From your perspective:
1. What are the hard constraints? (budget, timeline, resources, regulations)
2. What trade-offs do these constraints force? (e.g., if budget is fixed, what's deprioritized?)
3. Are there deal-breakers? (constraints that would kill the project)
4. How do we maximize impact within these constraints?"
</focus_prompt_examples>

<thinking_process>
Before your assessment:
1. Review all contributions in this round carefully
2. For each of the 8 aspects, find evidence in contributions
3. Classify each aspect as none/shallow/deep based on examples above
4. Calculate exploration score: sum(0.0=none, 0.5=shallow, 1.0=deep) / 8
5. Identify missing critical aspects (none or shallow coverage)
6. Assess convergence: Are experts agreeing or disagreeing?
7. Assess focus: Are contributions on-topic or drifting?
8. Assess novelty: Are new ideas emerging or repeating?
9. Determine status and next steps based on completeness
</thinking_process>

<output_format>
You MUST respond with a JSON object matching this schema:

{
  "round_number": <int>,
  "exploration_score": <float 0-1>,
  "aspect_coverage": [
    {
      "name": "<aspect_name>",
      "level": "none|shallow|deep",
      "notes": "<specific evidence from contributions>"
    },
    ... (all 8 aspects)
  ],
  "missing_critical_aspects": [<list of aspect names with none/shallow>],
  "convergence_score": <float 0-1>,
  "focus_score": <float 0-1>,
  "novelty_score": <float 0-1>,
  "status": "must_continue|continue_targeted|ready_to_decide|park_or_abort",
  "rationale": [<list of reasons for status>],
  "next_round_focus_prompts": [<targeted prompts for missing aspects>]
}

CRITICAL: Output ONLY valid JSON. No markdown, no prose, no explanations outside the JSON.
</output_format>

<quality_standards>
High-quality deliberations require:
- Exploration score ≥ 0.60 (at least 5/8 aspects discussed)
- Risks MUST be addressed (cannot end with risks at "none")
- Objectives MUST be clear (cannot end with objectives at "none")
- Convergence + Exploration together (not just early agreement)

Status guidelines:
- "must_continue": Exploration < 0.50 or critical aspects missing (risks, objectives)
- "continue_targeted": Exploration 0.50-0.70 and missing some aspects
- "ready_to_decide": Exploration ≥ 0.70, convergence high, novelty low
- "park_or_abort": Stalled debate (no progress, low novelty, no convergence improvement)
</quality_standards>
"""


# ============================================================================
# Judge Agent Functions
# ============================================================================


async def judge_round(
    contributions: list[Any],
    problem_statement: str,
    round_number: int,
    config: dict[str, Any] | None = None,
) -> JudgeOutput:
    """Analyze a deliberation round using the Judge Agent.

    Args:
        contributions: List of ContributionMessage objects from this round
        problem_statement: The problem being deliberated
        round_number: Current round number
        config: Optional LLM config (temperature, model, etc.)

    Returns:
        JudgeOutput with quality assessment

    Raises:
        ValueError: If LLM call fails or output cannot be parsed
        Exception: For other unexpected errors (falls back to heuristic)

    Example:
        >>> contributions = state.get_contributions_for_round(3)
        >>> problem = state.problem.description
        >>> output = await judge_round(contributions, problem, round_number=3)
        >>> print(f"Exploration: {output.exploration_score:.2f}")
        >>> print(f"Missing aspects: {output.missing_critical_aspects}")
    """
    logger.info(f"Judge analyzing round {round_number} with {len(contributions)} contributions")

    # Format contributions for prompt
    formatted_contributions = _format_contributions_for_prompt(contributions)

    # Build user prompt
    user_prompt = f"""<problem_statement>
{problem_statement}
</problem_statement>

<round_number>{round_number}</round_number>

<contributions_this_round>
{formatted_contributions}
</contributions_this_round>

<task>
Analyze the contributions above and assess meeting quality. Output JSON matching the schema provided in <output_format>.

Remember:
- Be strict with "deep" classification - require specific evidence, numbers, analysis
- Calculate exploration_score = average(aspect scores) where none=0, shallow=0.5, deep=1.0
- Cite specific evidence in notes field for each aspect
- Provide targeted focus prompts for missing aspects
</task>
"""

    try:
        # Call LLM (use Haiku 4.5 for cost efficiency)
        broker = PromptBroker()
        request = PromptRequest(
            system=JUDGE_SYSTEM_PROMPT,
            user_message=user_prompt,
            prefill="{",  # Force JSON output format
            model=config.get("model", "haiku") if config else "haiku",
            temperature=config.get("temperature", 0.0) if config else 0.0,
            max_tokens=config.get("max_tokens", 2000) if config else 2000,
            phase="judge",
            cache_system=True,  # TASK 1 FIX: Enable prompt caching (system prompt = static evaluation framework)
        )

        response = await broker.call(request)

        # Parse JSON response
        response_text = response.content
        judge_output_dict = json.loads(response_text)

        # Convert to Pydantic model
        judge_output = JudgeOutput(**judge_output_dict)

        logger.info(
            f"Judge assessment complete - Exploration: {judge_output.exploration_score:.2f}, "
            f"Status: {judge_output.status}, Missing: {judge_output.missing_critical_aspects}"
        )

        return judge_output

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Judge output as JSON: {e}")
        logger.error(f"Raw response: {response_text if 'response_text' in locals() else 'N/A'}")
        # Fall back to heuristic
        return _judge_round_heuristic(contributions, problem_statement, round_number)

    except Exception as e:
        logger.error(f"Judge Agent failed: {e}, falling back to heuristic")
        return _judge_round_heuristic(contributions, problem_statement, round_number)


def _format_contributions_for_prompt(contributions: list[Any]) -> str:
    """Format contributions for judge prompt.

    Args:
        contributions: List of ContributionMessage objects

    Returns:
        Formatted string with contributions
    """
    lines = []
    for i, contrib in enumerate(contributions, 1):
        persona_name = getattr(contrib, "persona_name", "Unknown")
        content = getattr(contrib, "content", str(contrib))
        lines.append(f"--- Contribution {i}: {persona_name} ---")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def _judge_round_heuristic(
    contributions: list[Any], problem_statement: str, round_number: int
) -> JudgeOutput:
    """Heuristic fallback for judge_round when LLM fails.

    Uses keyword matching and simple rules. Less accurate than LLM but provides
    a reasonable fallback.

    Args:
        contributions: List of ContributionMessage objects
        problem_statement: The problem being deliberated
        round_number: Current round number

    Returns:
        JudgeOutput with heuristic assessment
    """
    logger.warning("Using heuristic judge (LLM fallback)")

    # Combine all contribution text
    all_text = " ".join([getattr(c, "content", str(c)).lower() for c in contributions])

    # Heuristic aspect detection using keywords
    aspect_keywords = {
        "problem_clarity": ["problem is", "we need to", "goal is", "objective is"],
        "objectives": ["success", "target", "metric", "achieve", "goal"],
        "options_alternatives": ["option", "alternative", "could also", "instead", "or we could"],
        "key_assumptions": ["assume", "assumption", "if", "provided that", "given that"],
        "risks_failure_modes": ["risk", "fail", "could go wrong", "danger", "threat", "concern"],
        "constraints": ["budget", "time", "resource", "limitation", "can't", "cannot"],
        "stakeholders_impact": ["stakeholder", "customer", "team", "user", "affect", "impact"],
        "dependencies_unknowns": ["depend", "unknown", "unclear", "need to know", "blocker"],
    }

    aspect_coverage = []
    deep_count = 0
    shallow_count = 0
    none_count = 0

    for aspect in CRITICAL_ASPECTS:
        keywords = aspect_keywords.get(aspect, [])
        matches = sum(1 for keyword in keywords if keyword in all_text)

        if matches >= 3:
            level = "deep"
            deep_count += 1
            notes = f"Found {matches} mentions with keyword matching (heuristic)"
        elif matches >= 1:
            level = "shallow"
            shallow_count += 1
            notes = f"Found {matches} mentions (heuristic)"
        else:
            level = "none"
            none_count += 1
            notes = "Not mentioned (heuristic)"

        aspect_coverage.append(AspectCoverage(name=aspect, level=level, notes=notes))

    # Calculate exploration score
    exploration_score = (deep_count * 1.0 + shallow_count * 0.5) / 8.0

    # Find missing aspects
    missing_critical_aspects = [a.name for a in aspect_coverage if a.level in ["none", "shallow"]]

    # Heuristic convergence (count agreement words)
    agreement_words = ["agree", "yes", "correct", "exactly", "support"]
    convergence_score = min(1.0, sum(1 for word in agreement_words if word in all_text) / 10.0)

    # Heuristic focus (assume on-topic unless drift keywords)
    drift_words = ["off topic", "tangent", "unrelated", "different subject"]
    focus_score = 0.8 if not any(word in all_text for word in drift_words) else 0.5

    # Heuristic novelty (assume moderate novelty)
    novelty_score = 0.5

    # Determine status
    if exploration_score < 0.5:
        status = "must_continue"
        rationale = ["Exploration score too low (heuristic)"]
    elif exploration_score < 0.7:
        status = "continue_targeted"
        rationale = ["Missing some aspects (heuristic)"]
    else:
        status = "ready_to_decide"
        rationale = ["Sufficient exploration (heuristic)"]

    # Generate focus prompts for missing aspects
    next_round_focus_prompts = []
    for aspect in missing_critical_aspects[:3]:  # Top 3
        prompt_templates = {
            "risks_failure_modes": "What are the top 3 risks if we proceed? What could go wrong?",
            "stakeholders_impact": "Who will be affected by this decision? How will they be impacted?",
            "options_alternatives": "What alternative approaches should we consider?",
            "constraints": "What are the specific constraints (budget, time, resources)?",
            "dependencies_unknowns": "What dependencies or unknowns could block this?",
        }
        if aspect in prompt_templates:
            next_round_focus_prompts.append(prompt_templates[aspect])

    return JudgeOutput(
        round_number=round_number,
        exploration_score=exploration_score,
        aspect_coverage=aspect_coverage,
        missing_critical_aspects=missing_critical_aspects,
        convergence_score=convergence_score,
        focus_score=focus_score,
        novelty_score=novelty_score,
        status=status,
        rationale=rationale,
        next_round_focus_prompts=next_round_focus_prompts,
    )


# ============================================================================
# Prompt Composition Helper
# ============================================================================


def compose_judge_prompt_with_context(
    contributions: list[Any],
    problem_statement: str,
    round_number: int,
    previous_round_summaries: list[str] | None = None,
) -> str:
    """Compose judge prompt with hierarchical context (for caching optimization).

    Args:
        contributions: List of ContributionMessage objects from current round
        problem_statement: The problem being deliberated
        round_number: Current round number
        previous_round_summaries: Summaries of earlier rounds (for context, cached)

    Returns:
        Formatted prompt with cached context
    """
    # Cached portion: problem + previous summaries
    cached_context = f"""<problem_statement>
{problem_statement}
</problem_statement>

<previous_rounds_summary>
{chr(10).join(previous_round_summaries) if previous_round_summaries else "No previous rounds"}
</previous_rounds_summary>
"""

    # Uncached portion: current round contributions
    formatted_contributions = _format_contributions_for_prompt(contributions)

    user_prompt = f"""{cached_context}

<round_number>{round_number}</round_number>

<contributions_this_round>
{formatted_contributions}
</contributions_this_round>

<task>
Analyze the contributions above and assess meeting quality. Output JSON matching the schema provided in <output_format>.
</task>
"""

    return user_prompt
