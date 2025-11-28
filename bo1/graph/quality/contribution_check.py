"""Lightweight quality check for individual expert contributions.

This module provides fast quality assessment using Haiku to catch shallow
contributions early and provide corrective feedback for subsequent rounds.

Key Features:
- Fast assessment using Haiku 4.5 (~$0.001 per check)
- Evaluates specificity, evidence, and actionability
- Returns structured quality assessment
- Integrates with parallel_round_node for real-time feedback

Architecture:
- Called after each contribution in parallel_round_node
- Results aggregated to provide guidance for next round
- Complements full Judge assessment at convergence
"""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Quality Check Output Schema
# ============================================================================


class QualityCheckResult(BaseModel):
    """Structured output from lightweight quality check.

    This is a simpler, faster version of the full Judge assessment,
    focused on catching shallow contributions early.
    """

    is_shallow: bool = Field(
        ..., description="True if contribution lacks depth (vague, unsupported, or abstract)"
    )
    weak_aspects: list[str] = Field(
        default_factory=list,
        description="List of weak aspects: specificity, evidence, actionability",
    )
    quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall quality score (0-1). Average of 3 aspects."
    )
    feedback: str = Field(
        ..., description="One-sentence feedback for improvement (used in facilitator guidance)"
    )

    # Individual aspect scores for detailed metrics
    specificity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Specificity: 0=vague, 1=concrete with details/numbers"
    )
    evidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Evidence: 0=unsupported claims, 1=cited sources/data"
    )
    actionability_score: float = Field(
        ..., ge=0.0, le=1.0, description="Actionability: 0=abstract theory, 1=concrete next steps"
    )


# ============================================================================
# Quality Check System Prompt
# ============================================================================

QUALITY_CHECK_SYSTEM_PROMPT = """<system_role>
You are a contribution quality evaluator for a multi-expert deliberation system.

Your role:
- Quickly assess individual expert contributions for depth and quality
- Identify shallow, vague, or unsupported contributions
- Provide constructive feedback for improvement

You are analytical, fair, and focused on improving deliberation quality.
</system_role>

<evaluation_criteria>
Evaluate contributions on THREE dimensions (each scored 0-1):

1. **Specificity** (vague vs concrete):
   - LOW (0.0-0.3): Generic statements, no specifics ("We should consider risks", "This might work")
   - MEDIUM (0.4-0.7): Some specifics but incomplete ("Target $50K revenue", "3-month timeline")
   - HIGH (0.8-1.0): Concrete details with numbers/names/dates ("Increase MRR from $50K to $75K by Q2 2025 through enterprise upsells in healthcare vertical")

2. **Evidence** (unsupported vs cited):
   - LOW (0.0-0.3): Pure opinions, no backing ("I think this will fail", "Users want this")
   - MEDIUM (0.4-0.7): Some reasoning but no data ("Based on my experience", "Similar to X company")
   - HIGH (0.8-1.0): Cited sources, data, or analysis ("According to 2024 Gartner report", "Our Q3 metrics show 8% churn", "A/B test results: 15% conversion lift")

3. **Actionability** (abstract vs actionable):
   - LOW (0.0-0.3): Pure theory, no next steps ("We need to think about this", "Consider the implications")
   - MEDIUM (0.4-0.7): General direction but vague ("Focus on marketing", "Improve UX")
   - HIGH (0.8-1.0): Specific actions with owners/timeline ("Launch beta to 50 enterprise prospects by Dec 15 via Sarah's sales team", "Hire 2 senior engineers by Q1")

**IMPORTANT**: Be strict. High scores (0.8+) require SPECIFIC, CONCRETE evidence.
</evaluation_criteria>

<examples>
Example 1 - SHALLOW Contribution:
"I think we should be careful about moving too fast. There are risks involved and we need to make sure we consider all stakeholders. Let's take a measured approach and think this through carefully."

Assessment:
- Specificity: 0.2 (no concrete risks named, no timeline, no stakeholders identified)
- Evidence: 0.1 (pure opinion, no data or reasoning)
- Actionability: 0.1 (no specific actions, just "think carefully")
- Quality Score: 0.13
- is_shallow: true
- weak_aspects: ["specificity", "evidence", "actionability"]
- feedback: "Too vague - name specific risks, cite evidence, and propose concrete next steps with timeline."

---

Example 2 - MEDIUM QUALITY Contribution:
"Based on my experience in SaaS, we should focus on enterprise customers. They have higher LTV and lower churn. I recommend we hire a dedicated enterprise sales team."

Assessment:
- Specificity: 0.5 (mentions enterprise, but no target size, timeline, or metrics)
- Evidence: 0.4 (cites experience and general SaaS patterns, but no specific data)
- Actionability: 0.6 (recommends hiring, but no team size, budget, or timeline)
- Quality Score: 0.50
- is_shallow: false (borderline, but acceptable for early rounds)
- weak_aspects: ["specificity", "evidence"]
- feedback: "Good direction - strengthen with specific metrics (target LTV, churn %), team size, and timeline."

---

Example 3 - HIGH QUALITY Contribution:
"I recommend targeting mid-market healthcare companies (100-500 employees). Our Q3 data shows healthcare has 3x higher LTV ($85K vs $28K avg) and 60% lower churn (3.2% vs 8.1%). Action plan: (1) Hire 2 enterprise AEs with healthcare experience by Jan 15 - budget $300K/year; (2) Build HIPAA compliance docs by Dec 1 via legal team; (3) Launch pilot with 10 healthcare prospects from waitlist by Jan 30. Sarah to lead, I'll support on compliance."

Assessment:
- Specificity: 0.95 (specific segment, numbers, dates, owners, budget)
- Evidence: 0.9 (cites Q3 data with specific metrics)
- Actionability: 1.0 (clear 3-step plan with dates, owners, and budget)
- Quality Score: 0.95
- is_shallow: false
- weak_aspects: []
- feedback: "Excellent - specific, data-backed, and actionable with clear ownership and timeline."

---

Example 4 - SHALLOW (Academic/Abstract):
"From a systems thinking perspective, we need to consider the second-order effects of this decision. Complex adaptive systems theory suggests that interventions can have unintended consequences. We should apply scenario planning methodologies to explore multiple futures."

Assessment:
- Specificity: 0.3 (mentions frameworks but no concrete application)
- Evidence: 0.2 (cites theory, but no data or examples)
- Actionability: 0.2 (suggests methodology but no specific scenarios or next steps)
- Quality Score: 0.23
- is_shallow: true
- weak_aspects: ["specificity", "evidence", "actionability"]
- feedback: "Too abstract - apply frameworks to THIS specific decision with concrete scenarios and action items."
</examples>

<output_format>
You MUST respond with ONLY a JSON object matching this schema:

{
  "specificity_score": <float 0-1>,
  "evidence_score": <float 0-1>,
  "actionability_score": <float 0-1>,
  "quality_score": <float 0-1>,
  "is_shallow": <bool>,
  "weak_aspects": [<list of "specificity"|"evidence"|"actionability">],
  "feedback": "<one sentence, max 100 chars>"
}

CRITICAL: Output ONLY valid JSON. No markdown, no prose, no explanations.

Guidelines:
- quality_score = average of 3 aspect scores
- is_shallow = true if quality_score < 0.5
- weak_aspects = list aspects with score < 0.5
- feedback must be actionable and specific (not generic praise/criticism)
</output_format>

<quality_thresholds>
- Shallow threshold: quality_score < 0.5
- Acceptable: quality_score 0.5-0.7
- High quality: quality_score > 0.7

Be strict but fair. The goal is to improve deliberation quality, not block contributions.
</quality_thresholds>
"""


# ============================================================================
# Quality Check Function
# ============================================================================


async def quick_quality_check(
    contribution: str,
    problem_context: str,
    persona_name: str = "Unknown",
    config: dict[str, Any] | None = None,
) -> tuple[QualityCheckResult, Any | None]:
    """Fast quality check using Haiku for individual contribution.

    This function provides lightweight quality assessment to catch shallow
    contributions early and provide corrective feedback.

    Args:
        contribution: The expert contribution text to evaluate
        problem_context: Brief context about the problem being solved
        persona_name: Name of the persona who made the contribution (for logging)
        config: Optional LLM config (temperature, model, etc.)

    Returns:
        Tuple of (QualityCheckResult, LLMResponse) for cost tracking
        LLMResponse is None if heuristic fallback was used

    Raises:
        ValueError: If LLM call fails or output cannot be parsed
        Exception: For other unexpected errors (falls back to heuristic)

    Example:
        >>> contribution = "We should think about the risks."
        >>> problem = "Should we expand to Europe?"
        >>> result, llm_response = await quick_quality_check(contribution, problem)
        >>> print(f"Shallow: {result.is_shallow}, Score: {result.quality_score:.2f}")
        >>> print(f"Feedback: {result.feedback}")
        Shallow: True, Score: 0.15
        Feedback: Too vague - name specific risks with evidence and timeline.
    """
    from bo1.llm.broker import PromptBroker, PromptRequest

    logger.debug(f"Quick quality check for contribution from {persona_name}")

    # Build user prompt
    user_prompt = f"""<problem_context>
{problem_context}
</problem_context>

<contribution_to_evaluate>
{contribution}
</contribution_to_evaluate>

<task>
Evaluate the contribution above for quality. Output JSON matching the schema in <output_format>.

Remember:
- Be strict with high scores (0.8+) - require specific evidence, numbers, concrete actions
- quality_score = average of 3 aspects
- is_shallow = true if quality_score < 0.5
- weak_aspects = aspects with score < 0.5
- feedback must be actionable (not generic)
</task>
"""

    try:
        # Call LLM (use Haiku 4.5 for speed and cost efficiency)
        broker = PromptBroker()
        request = PromptRequest(
            system=QUALITY_CHECK_SYSTEM_PROMPT,
            user_message=user_prompt,
            model=config.get("model", "haiku") if config else "haiku",
            temperature=config.get("temperature", 0.0) if config else 0.0,
            max_tokens=config.get("max_tokens", 500) if config else 500,
            phase="quality_check",
        )

        response = await broker.call(request)

        # Parse JSON response
        response_text = response.content
        result_dict = json.loads(response_text)

        # Convert to Pydantic model
        result = QualityCheckResult(**result_dict)

        logger.debug(
            f"Quality check for {persona_name}: Score={result.quality_score:.2f}, "
            f"Shallow={result.is_shallow}, Weak={result.weak_aspects}"
        )

        return result, response

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse quality check output as JSON: {e}")
        logger.error(f"Raw response: {response_text if 'response_text' in locals() else 'N/A'}")
        # Fall back to heuristic
        return _quality_check_heuristic(contribution, persona_name), None

    except Exception as e:
        logger.error(f"Quality check failed: {e}, falling back to heuristic")
        return _quality_check_heuristic(contribution, persona_name), None


def _quality_check_heuristic(
    contribution: str, persona_name: str = "Unknown"
) -> QualityCheckResult:
    """Heuristic fallback for quality check when LLM fails.

    Uses simple keyword and length-based rules. Less accurate than LLM but
    provides a reasonable fallback.

    Args:
        contribution: The contribution text to evaluate
        persona_name: Name of persona (for logging)

    Returns:
        QualityCheckResult with heuristic assessment
    """
    logger.warning(f"Using heuristic quality check for {persona_name} (LLM fallback)")

    text_lower = contribution.lower()

    # Specificity heuristic: Look for numbers, dates, names, specific terms
    specificity_indicators = [
        r"\d+%",  # Percentages
        r"\$\d+",  # Dollar amounts
        r"\d{4}",  # Years
        r"q[1-4]",  # Quarters
        r"january|february|march|april|may|june|july|august|september|october|november|december",
        r"by [a-z]+ \d+",  # "by Jan 15"
    ]

    import re

    specificity_count = sum(
        1 for pattern in specificity_indicators if re.search(pattern, text_lower)
    )
    specificity_score = min(1.0, specificity_count * 0.25)  # 0.25 per indicator, max 1.0

    # Evidence heuristic: Look for data references, citations
    evidence_indicators = [
        "data",
        "study",
        "research",
        "report",
        "metrics",
        "analysis",
        "according to",
        "shows that",
        "found that",
        "survey",
    ]
    evidence_count = sum(1 for word in evidence_indicators if word in text_lower)
    evidence_score = min(1.0, evidence_count * 0.2)  # 0.2 per indicator, max 1.0

    # Actionability heuristic: Look for action verbs, concrete steps
    action_indicators = [
        "recommend",
        "propose",
        "hire",
        "launch",
        "build",
        "create",
        "implement",
        "deploy",
        "execute",
        "step 1",
        "step 2",
        "action",
        "plan:",
    ]
    action_count = sum(1 for word in action_indicators if word in text_lower)
    actionability_score = min(1.0, action_count * 0.2)  # 0.2 per indicator, max 1.0

    # Penalize very short contributions
    word_count = len(contribution.split())
    if word_count < 30:
        specificity_score *= 0.5
        evidence_score *= 0.5
        actionability_score *= 0.5

    # Calculate overall quality
    quality_score = (specificity_score + evidence_score + actionability_score) / 3.0
    is_shallow = quality_score < 0.5

    # Determine weak aspects
    weak_aspects = []
    if specificity_score < 0.5:
        weak_aspects.append("specificity")
    if evidence_score < 0.5:
        weak_aspects.append("evidence")
    if actionability_score < 0.5:
        weak_aspects.append("actionability")

    # Generate feedback
    if is_shallow:
        feedback = "Add concrete details, evidence, and actionable next steps (heuristic check)"
    else:
        feedback = f"Good contribution - consider adding more {', '.join(weak_aspects) if weak_aspects else 'depth'} (heuristic)"

    return QualityCheckResult(
        specificity_score=specificity_score,
        evidence_score=evidence_score,
        actionability_score=actionability_score,
        quality_score=quality_score,
        is_shallow=is_shallow,
        weak_aspects=weak_aspects,
        feedback=feedback,
    )


# ============================================================================
# Batch Quality Check (for parallel rounds)
# ============================================================================


async def check_contributions_quality(
    contributions: list[Any],  # list[ContributionMessage]
    problem_context: str,
    config: dict[str, Any] | None = None,
) -> tuple[list[QualityCheckResult], list[Any]]:
    """Check quality for multiple contributions in parallel.

    This is the main entry point for parallel_round_node integration.

    Args:
        contributions: List of ContributionMessage objects
        problem_context: Brief problem description for context
        config: Optional LLM config

    Returns:
        Tuple of (quality_results, llm_responses) for cost tracking
        - quality_results: List of QualityCheckResult objects (same order as input)
        - llm_responses: List of LLMResponse objects (None for heuristic fallbacks)

    Example:
        >>> contributions = [contrib1, contrib2, contrib3]
        >>> problem = "Should we expand to Europe?"
        >>> results, responses = await check_contributions_quality(contributions, problem)
        >>> shallow_count = sum(1 for r in results if r.is_shallow)
        >>> print(f"{shallow_count}/{len(results)} contributions are shallow")
    """
    import asyncio

    if not contributions:
        return [], []

    # Create quality check tasks for all contributions
    tasks = []
    for contrib in contributions:
        contrib_text = contrib.content if hasattr(contrib, "content") else str(contrib)
        persona_name = getattr(contrib, "persona_name", "Unknown")

        task = quick_quality_check(
            contribution=contrib_text,
            problem_context=problem_context,
            persona_name=persona_name,
            config=config,
        )
        tasks.append(task)

    # Run all quality checks in parallel
    # Each task returns (QualityCheckResult, LLMResponse | None)
    results_with_responses = await asyncio.gather(*tasks)

    # Separate results and responses
    quality_results = [r[0] for r in results_with_responses]
    llm_responses = [r[1] for r in results_with_responses]

    # Log summary
    shallow_count = sum(1 for r in quality_results if r.is_shallow)
    avg_quality = sum(r.quality_score for r in quality_results) / len(quality_results)

    logger.info(
        f"Quality check complete: {shallow_count}/{len(quality_results)} shallow, "
        f"avg quality: {avg_quality:.2f}"
    )

    return quality_results, llm_responses
