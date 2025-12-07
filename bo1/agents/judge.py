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
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from bo1.graph.meeting_config import CRITICAL_ASPECTS
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.models.state import AspectCoverage
from bo1.prompts.judge_prompts import JUDGE_PREFILL, JUDGE_SYSTEM_PROMPT

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

    @field_validator("next_round_focus_prompts", mode="before")
    @classmethod
    def normalize_focus_prompts(cls, v: list[Any]) -> list[str]:
        """Normalize focus prompts to strings.

        LLM sometimes returns dicts with 'aspect' and 'prompt' fields instead of strings.
        This validator converts both formats to a list of strings.
        """
        if not v:
            return []

        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Handle dict format: {'aspect': '...', 'prompt': '...'}
                prompt = item.get("prompt", "")
                aspect = item.get("aspect", "")
                if prompt:
                    result.append(f"[{aspect}] {prompt}" if aspect else prompt)
                elif aspect:
                    result.append(aspect)
            else:
                # Fallback: convert to string
                result.append(str(item))
        return result


# ============================================================================
# JSON Repair Utilities
# ============================================================================

MAX_JSON_REPAIR_ATTEMPTS = 1  # Number of LLM retries after JSON repair fails


def _repair_json(raw_text: str) -> str:
    """Attempt to repair common JSON issues from LLM output.

    Fixes:
    - Trailing commas before closing brackets
    - Missing closing brackets/braces
    - Unescaped newlines in strings
    - Truncated JSON (attempts to close open structures)

    Args:
        raw_text: Raw JSON string from LLM

    Returns:
        Repaired JSON string (may still be invalid)
    """
    text = raw_text.strip()

    # Remove trailing commas before closing brackets
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    # Count brackets to detect truncation
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    # Attempt to close truncated JSON
    if open_braces > 0 or open_brackets > 0:
        # Add missing closing brackets
        text += "]" * max(0, open_brackets)
        text += "}" * max(0, open_braces)

    # Fix common unescaped characters in strings
    # Replace literal newlines inside strings (between quotes)
    # This is a simple heuristic - may not catch all cases
    text = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*$)', "\\n", text)

    return text


def _extract_json_from_text(raw_text: str) -> str:
    """Extract JSON object from text that may contain markdown or prose.

    Args:
        raw_text: Raw text that may contain JSON embedded in markdown

    Returns:
        Extracted JSON string
    """
    text = raw_text.strip()

    # If it starts with {, assume it's already JSON
    if text.startswith("{"):
        return text

    # Look for JSON in markdown code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Look for a JSON object anywhere in the text
    brace_start = text.find("{")
    if brace_start != -1:
        # Find matching closing brace
        depth = 0
        for i, char in enumerate(text[brace_start:]):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_start : brace_start + i + 1]
        # If no matching brace found, return from first brace to end
        return text[brace_start:]

    return text


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

    broker = PromptBroker()
    response_text = ""
    last_error: json.JSONDecodeError | Exception | None = None

    for attempt in range(MAX_JSON_REPAIR_ATTEMPTS + 1):
        try:
            # Call LLM (use Haiku 4.5 for cost efficiency)
            request = PromptRequest(
                system=JUDGE_SYSTEM_PROMPT,
                user_message=user_prompt,
                prefill=JUDGE_PREFILL,  # Force JSON output format
                model=config.get("model", "haiku") if config else "haiku",
                temperature=config.get("temperature", 0.0) if config else 0.0,
                max_tokens=config.get("max_tokens", 4096) if config else 4096,
                phase="judge",
                cache_system=True,  # Enable prompt caching (system prompt = static evaluation framework)
            )

            response = await broker.call(request)
            response_text = response.content

            # Step 1: Extract JSON from any surrounding text
            extracted_json = _extract_json_from_text(response_text)

            # Step 2: Try parsing raw extracted JSON
            try:
                judge_output_dict = json.loads(extracted_json)
            except json.JSONDecodeError:
                # Step 3: Try repairing JSON
                repaired_json = _repair_json(extracted_json)
                logger.info(f"Judge JSON repair attempt {attempt + 1}: trying repaired JSON")
                judge_output_dict = json.loads(repaired_json)

            # Convert to Pydantic model
            judge_output = JudgeOutput(**judge_output_dict)

            logger.info(
                f"Judge assessment complete - Exploration: {judge_output.exploration_score:.2f}, "
                f"Status: {judge_output.status}, Missing: {judge_output.missing_critical_aspects}"
            )

            return judge_output

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                f"Judge JSON parse failed (attempt {attempt + 1}/{MAX_JSON_REPAIR_ATTEMPTS + 1}): {e}"
            )
            if attempt < MAX_JSON_REPAIR_ATTEMPTS:
                # Retry with stronger enforcement in prompt
                user_prompt = f"""<CRITICAL>
Your previous response was not valid JSON. You MUST output ONLY valid JSON with no markdown, no prose, no explanations.
The JSON must be parseable by json.loads() directly.
</CRITICAL>

{user_prompt}"""
                logger.info("Retrying Judge with stricter JSON enforcement")
                continue
            # Final attempt failed, fall through to heuristic

        except Exception as e:
            last_error = e
            logger.error(f"Judge Agent error (attempt {attempt + 1}): {e}")
            if attempt < MAX_JSON_REPAIR_ATTEMPTS:
                continue
            # Final attempt failed, fall through to heuristic

    # All attempts failed, use heuristic fallback
    logger.error(
        f"Judge JSON parsing failed after {MAX_JSON_REPAIR_ATTEMPTS + 1} attempts: {last_error}"
    )
    logger.error(
        f"Raw response: {response_text[:500]}..."
        if len(response_text) > 500
        else f"Raw response: {response_text}"
    )
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
