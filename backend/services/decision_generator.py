"""Decision page content generator service.

Runs a real deliberation and extracts content for SEO decision pages.
Uses internal sessions for generation.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from bo1.config import resolve_model_alias
from bo1.llm.client import ClaudeClient
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response_parser import extract_json_from_response

logger = logging.getLogger(__name__)

# Use Sonnet for quality (this is public-facing content)
MODEL = "sonnet"


@dataclass
class DecisionContent:
    """Generated decision content."""

    session_id: str | None
    expert_perspectives: list[dict[str, Any]]
    synthesis: str
    faqs: list[dict[str, Any]]
    meta_description: str
    created_at: datetime = field(default_factory=datetime.now)


DECISION_GENERATION_PROMPT = """You are an expert business advisor creating content for a decision framework page.

A founder is facing this decision:
Question: {question}

Founder Context:
- Stage: {stage}
- Constraints: {constraints}
- Situation: {situation}

Generate expert perspectives from 3-4 different viewpoints that would help a founder think through this decision.
Each perspective should:
1. Come from a distinct expert archetype (Growth Operator, Financial Strategist, Risk Analyst, Market Expert, etc.)
2. Provide specific, actionable advice (not generic platitudes)
3. Consider the founder's specific context and constraints
4. Be 2-4 sentences with concrete recommendations

Then synthesize the perspectives into a balanced recommendation (2-3 paragraphs).

Finally, generate 6-8 FAQ questions and answers that founders commonly ask about this decision.

Output as JSON:
{{
    "expert_perspectives": [
        {{
            "persona_name": "Growth Operator",
            "quote": "At your stage with limited runway, speed of iteration beats..."
        }},
        {{
            "persona_name": "Financial Strategist",
            "quote": "Run the numbers: if you're paying contractors £X/hour..."
        }}
    ],
    "synthesis": "Full synthesis text here (2-3 paragraphs)...",
    "faqs": [
        {{
            "question": "How do I evaluate engineers as a non-technical founder?",
            "answer": "Focus on..."
        }}
    ],
    "meta_description": "SEO meta description (150-160 chars) for this decision page"
}}"""


async def generate_decision_content(
    question: str,
    category: str,
    founder_context: dict[str, Any],
) -> DecisionContent:
    """Generate decision page content.

    This creates expert perspectives and synthesis without running a full session.
    For quick content generation without the overhead of a real deliberation.

    Args:
        question: The decision question
        category: Decision category
        founder_context: Dict with stage, constraints, situation

    Returns:
        DecisionContent with generated content

    Raises:
        ValueError: If generation fails
    """
    stage = founder_context.get("stage", "Early stage startup")
    constraints = founder_context.get("constraints", [])
    constraints_str = (
        "\n".join(f"- {c}" for c in constraints) if constraints else "- None specified"
    )
    situation = founder_context.get("situation", "Evaluating options")

    client = ClaudeClient()

    prompt = DECISION_GENERATION_PROMPT.format(
        question=question,
        stage=stage,
        constraints=constraints_str,
        situation=situation,
    )

    # Track cost with internal_seo category
    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias(MODEL),
        prompt_type="decision_generation",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
            prefill="{",
        )
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    try:
        data = extract_json_from_response(response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse decision generation response: {e}")
        raise ValueError("Decision generation returned invalid JSON format") from e

    logger.info(
        f"Generated decision content for: '{question}' "
        f"(tokens: {usage.total_tokens}, cost: ${usage.calculate_cost(MODEL):.4f})"
    )

    return DecisionContent(
        session_id=None,  # No real session for quick generation
        expert_perspectives=data.get("expert_perspectives", []),
        synthesis=data.get("synthesis", ""),
        faqs=data.get("faqs", []),
        meta_description=data.get("meta_description", ""),
    )


async def generate_faqs_for_decision(
    question: str,
    founder_context: dict[str, Any],
    existing_faqs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate additional FAQs for an existing decision.

    Args:
        question: The decision question
        founder_context: Founder context
        existing_faqs: Existing FAQs to avoid duplication

    Returns:
        List of new FAQ dicts
    """
    existing_questions = [f["question"] for f in (existing_faqs or [])]
    existing_str = "\n".join(f"- {q}" for q in existing_questions) if existing_questions else "None"

    faq_prompt = f"""Generate 4-6 additional FAQ questions and answers for this decision page.

Decision Question: {question}
Founder Context: {founder_context}

Existing FAQs (do not duplicate):
{existing_str}

Output as JSON:
{{
    "faqs": [
        {{"question": "...", "answer": "..."}}
    ]
}}"""

    client = ClaudeClient()

    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias("haiku"),  # Use haiku for FAQ generation
        prompt_type="faq_generation",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": faq_prompt}],
            temperature=0.7,
            max_tokens=2048,
            prefill="{",
        )
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    data = extract_json_from_response(response)

    logger.info(f"Generated {len(data.get('faqs', []))} additional FAQs for decision")

    return data.get("faqs", [])
