"""Option extraction orchestration for Decision Gate.

Extracts 3-5 distinct option cards from expert recommendations
using an LLM call (Haiku for cost efficiency).
"""

import json
import logging
from typing import Any

from bo1.config import get_model_for_role
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.models.option_card import OptionCard
from bo1.models.problem import Constraint
from bo1.models.recommendations import Recommendation
from bo1.prompts.constraints import format_constraints_for_prompt
from bo1.prompts.option_extraction import (
    OPTION_EXTRACTION_SYSTEM_PROMPT,
    OPTION_EXTRACTION_USER_PROMPT,
)

logger = logging.getLogger(__name__)


def _format_recommendations(recommendations: list[Recommendation]) -> str:
    """Format recommendations for LLM input."""
    parts = []
    for i, r in enumerate(recommendations, 1):
        parts.append(
            f"Expert {i}: {r.persona_name} ({r.persona_code})\n"
            f"  Recommendation: {r.recommendation}\n"
            f"  Reasoning: {r.reasoning}\n"
            f"  Confidence: {r.confidence}\n"
            f"  Conditions: {', '.join(r.conditions) if r.conditions else 'None'}"
        )
    return "\n\n".join(parts)


def _format_constraints(constraints: list[Constraint]) -> str:
    """Format constraints for LLM input (option extraction style)."""
    formatted = format_constraints_for_prompt(constraints)
    return formatted if formatted else "No explicit constraints provided."


def _fallback_options(recommendations: list[Recommendation]) -> list[OptionCard]:
    """Create one option per recommendation as fallback."""
    options = []
    for i, r in enumerate(recommendations, 1):
        options.append(
            OptionCard(
                id=f"opt_{i:03d}",
                label=r.recommendation[:60],
                description=r.recommendation,
                supporting_personas=[r.persona_code],
                confidence_range=(r.confidence, r.confidence),
                conditions=r.conditions,
                tradeoffs=[],
                risk_summary=r.risk_assessment or "",
            )
        )
    return options[:5]  # Cap at 5


async def extract_options(
    recommendations: list[Recommendation],
    constraints: list[Constraint] | None = None,
    broker: PromptBroker | None = None,
) -> list[OptionCard]:
    """Extract 3-5 option cards from expert recommendations.

    Args:
        recommendations: Expert recommendations from voting phase
        constraints: Problem constraints for scoring
        broker: PromptBroker instance (created if not provided)

    Returns:
        List of OptionCard objects (3-5 items)
    """
    if not recommendations:
        return []

    if broker is None:
        broker = PromptBroker()

    constraints = constraints or []

    recommendations_formatted = _format_recommendations(recommendations)
    constraints_formatted = _format_constraints(constraints)

    request = PromptRequest(
        system=OPTION_EXTRACTION_SYSTEM_PROMPT,
        user_message=OPTION_EXTRACTION_USER_PROMPT.format(
            recommendations_formatted=recommendations_formatted,
            constraints_formatted=constraints_formatted,
        ),
        model=get_model_for_role("option_extraction"),
        prefill="[",
        max_tokens=4096,
        temperature=0.3,
        phase="voting",
        agent_type="OptionExtractor",
    )

    try:
        response = await broker.call(request)
        raw = response.content.strip()

        # Ensure we have a complete JSON array
        if not raw.startswith("["):
            raw = "[" + raw
        if not raw.endswith("]"):
            # Find last complete object
            last_brace = raw.rfind("}")
            if last_brace > 0:
                raw = raw[: last_brace + 1] + "]"

        options_data: list[dict[str, Any]] = json.loads(raw)

        options = []
        for item in options_data:
            # Normalize confidence_range from list to tuple
            cr = item.get("confidence_range", [0.5, 0.5])
            if isinstance(cr, list) and len(cr) == 2:
                item["confidence_range"] = (cr[0], cr[1])

            options.append(OptionCard(**item))

        logger.info(f"Extracted {len(options)} options from {len(recommendations)} recommendations")
        return options

    except Exception as e:
        logger.warning(f"Option extraction failed, using fallback: {e}")
        return _fallback_options(recommendations)
