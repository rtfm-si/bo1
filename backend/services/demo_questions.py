"""Demo question generator service.

Generates personalized business questions based on user's context.
Uses LLM to create relevant, actionable questions for new users.
"""

import json
import logging
from typing import Any

import redis
from pydantic import BaseModel, Field

from bo1.config import get_settings
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

# Redis cache TTL for demo questions (7 days)
DEMO_QUESTIONS_TTL = 604800


class DemoQuestion(BaseModel):
    """A suggested demo question for onboarding."""

    question: str = Field(..., description="The question text")
    category: str = Field(
        ..., description="Category: strategy, growth, operations, product, finance"
    )
    relevance: str = Field(..., description="Why this question is relevant to the user's business")


class DemoQuestionsResponse(BaseModel):
    """Response containing generated demo questions."""

    questions: list[DemoQuestion] = Field(default_factory=list)
    generated: bool = Field(False, description="Whether questions were freshly generated")
    cached: bool = Field(False, description="Whether questions came from cache")


def _get_redis_client() -> redis.Redis:  # type: ignore[type-arg]
    """Get Redis client for caching."""
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def _cache_key(user_id: str) -> str:
    """Generate cache key for user's demo questions."""
    return f"demo_questions:{user_id}"


def _get_cached_questions(user_id: str) -> list[DemoQuestion] | None:
    """Get cached demo questions for user."""
    try:
        client = _get_redis_client()
        cached = client.get(_cache_key(user_id))
        if cached:
            data = json.loads(cached)
            return [DemoQuestion(**q) for q in data]
        return None
    except Exception as e:
        logger.warning(f"Failed to get cached questions: {e}")
        return None


def _cache_questions(user_id: str, questions: list[DemoQuestion]) -> None:
    """Cache demo questions for user."""
    try:
        client = _get_redis_client()
        data = json.dumps([q.model_dump() for q in questions])
        client.setex(_cache_key(user_id), DEMO_QUESTIONS_TTL, data)
    except Exception as e:
        logger.warning(f"Failed to cache questions: {e}")


def _build_context_summary(context: dict[str, Any]) -> str:
    """Build a summary of user's business context for the prompt."""
    parts = []

    if context.get("business_model"):
        parts.append(f"Business model: {context['business_model']}")

    if context.get("target_market"):
        parts.append(f"Target market: {context['target_market']}")

    if context.get("product_description"):
        parts.append(f"Product/service: {context['product_description']}")

    if context.get("company_name"):
        parts.append(f"Company: {context['company_name']}")

    if context.get("stage"):
        parts.append(f"Business stage: {context['stage']}")

    if context.get("industry"):
        parts.append(f"Industry: {context['industry']}")

    if context.get("revenue"):
        parts.append(f"Revenue: ${context['revenue']:,.0f}")

    if context.get("customers"):
        parts.append(f"Customers: {context['customers']}")

    if context.get("growth_rate"):
        parts.append(f"Growth rate: {context['growth_rate']}%")

    if context.get("competitors"):
        comps = context["competitors"]
        if isinstance(comps, list):
            parts.append(f"Competitors: {', '.join(comps[:5])}")

    if context.get("challenges"):
        challenges = context["challenges"]
        if isinstance(challenges, list):
            parts.append(f"Key challenges: {', '.join(challenges[:3])}")

    return "\n".join(parts) if parts else "No business context provided."


DEMO_QUESTIONS_PROMPT = """You are helping a new user of Board of One, an AI-powered decision support platform.

Based on the user's business context below, generate 5 relevant business questions they could explore in their first meeting. These should be:
1. Strategic questions relevant to their specific business situation
2. Actionable - questions that lead to concrete decisions
3. Diverse - covering different aspects (strategy, growth, operations, product, finance)
4. Appropriate for their business stage and size

<business_context>
{context_summary}
</business_context>

Return a JSON array with exactly 5 questions. Each question object should have:
- "question": The question text (1-2 sentences, clear and specific)
- "category": One of "strategy", "growth", "operations", "product", "finance"
- "relevance": Brief explanation of why this question matters for their business (1 sentence)

Example format:
[
  {{"question": "Should we expand to the European market this year?", "category": "growth", "relevance": "Given your growth rate and product maturity, international expansion could be timely."}}
]

Respond with ONLY the JSON array, no other text."""

FALLBACK_QUESTIONS = [
    DemoQuestion(
        question="What should be our top 3 strategic priorities for the next quarter?",
        category="strategy",
        relevance="Helps focus resources and align team efforts on what matters most.",
    ),
    DemoQuestion(
        question="How should we prioritize our product roadmap for maximum customer impact?",
        category="product",
        relevance="Ensures development efforts align with customer needs and business goals.",
    ),
    DemoQuestion(
        question="What's the best approach to improve our customer retention rate?",
        category="growth",
        relevance="Retention is often more cost-effective than acquisition for sustainable growth.",
    ),
    DemoQuestion(
        question="Should we hire more team members now or wait until next funding round?",
        category="operations",
        relevance="Timing hiring decisions right affects runway and team productivity.",
    ),
    DemoQuestion(
        question="How should we allocate our marketing budget across channels?",
        category="finance",
        relevance="Optimizing marketing spend is crucial for efficient customer acquisition.",
    ),
]


async def generate_demo_questions(
    user_id: str,
    context: dict[str, Any] | None = None,
    force_refresh: bool = False,
) -> DemoQuestionsResponse:
    """Generate demo questions for a user based on their business context.

    Args:
        user_id: User ID to generate questions for
        context: User's business context (optional, uses generic if not provided)
        force_refresh: If True, skip cache and regenerate

    Returns:
        DemoQuestionsResponse with questions
    """
    # Check cache first (unless force_refresh)
    if not force_refresh:
        cached = _get_cached_questions(user_id)
        if cached:
            return DemoQuestionsResponse(questions=cached, generated=False, cached=True)

    # If no context provided, return fallback questions
    if not context or not any(context.values()):
        return DemoQuestionsResponse(questions=FALLBACK_QUESTIONS, generated=False, cached=False)

    # Generate questions using LLM
    try:
        context_summary = _build_context_summary(context)
        prompt = DEMO_QUESTIONS_PROMPT.format(context_summary=context_summary)

        broker = PromptBroker(cost_tracker=CostTracker())
        request = PromptRequest(
            system="You are a business strategy assistant helping users explore important decisions.",
            user_message=prompt,
            model="fast",  # Use fast tier (Haiku) to minimize cost
            max_tokens=1500,
            phase="onboarding",
        )

        response = await broker.call(request)

        # Parse response
        try:
            # Clean response (remove markdown code blocks if present)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()

            questions_data = json.loads(content)
            questions = [DemoQuestion(**q) for q in questions_data[:5]]

            # Cache the generated questions
            _cache_questions(user_id, questions)

            return DemoQuestionsResponse(questions=questions, generated=True, cached=False)

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return DemoQuestionsResponse(
                questions=FALLBACK_QUESTIONS, generated=False, cached=False
            )

    except Exception as e:
        logger.error(f"Failed to generate demo questions: {e}")
        return DemoQuestionsResponse(questions=FALLBACK_QUESTIONS, generated=False, cached=False)


def clear_cached_questions(user_id: str) -> bool:
    """Clear cached demo questions for a user.

    Args:
        user_id: User ID to clear cache for

    Returns:
        True if cache was cleared, False otherwise
    """
    try:
        client = _get_redis_client()
        client.delete(_cache_key(user_id))
        return True
    except Exception as e:
        logger.warning(f"Failed to clear cached questions: {e}")
        return False
