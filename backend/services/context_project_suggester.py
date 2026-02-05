"""Context-based project suggester service.

Analyzes user's business context to suggest strategic projects
aligned with their priorities and objectives.
"""

import json
import logging
from dataclasses import dataclass

from bo1.llm.client import ClaudeClient
from bo1.state.repositories.project_repository import ProjectRepository
from bo1.state.repositories.user_repository import UserRepository
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)

# Lazy-initialized client
_claude_client: ClaudeClient | None = None


def _get_client() -> ClaudeClient:
    """Get or create Claude client."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client


@dataclass
class ContextProjectSuggestion:
    """A suggested project derived from business context.

    Attributes:
        id: Unique identifier for this suggestion (generated)
        name: Suggested project name
        description: Project description
        rationale: Why this project aligns with user's priorities
        category: Project category (strategy/growth/operations/product/marketing)
        priority: Suggested priority (high/medium/low)
    """

    id: str
    name: str
    description: str
    rationale: str
    category: str
    priority: str


# Minimum context fields required to generate suggestions
REQUIRED_CONTEXT_FIELDS = ["primary_objective"]

# Categories for project classification
VALID_CATEGORIES = ["strategy", "growth", "operations", "product", "marketing", "finance"]

CONTEXT_SUGGESTION_PROMPT = """Based on this business context, suggest 2-4 strategic projects that would help achieve the stated objectives.

Business Context:
{context_text}

{existing_projects_section}

For each suggested project:
1. Give it a clear, actionable name (e.g., "Launch Customer Referral Program", "Optimize Pricing Strategy")
2. Write a brief description (2-3 sentences) of what the project aims to achieve
3. Explain the rationale - why this project aligns with the business priorities
4. Assign a category: strategy, growth, operations, product, marketing, or finance
5. Suggest a priority: high, medium, or low

Guidelines:
- Focus on projects that directly support the primary_objective
- Consider the industry context and competitive landscape when applicable
- Suggest practical, achievable projects (not moonshots)
- Avoid duplicating any existing projects the user already has
- Each project should be distinct and actionable
- Prefer projects that leverage the user's value proposition

Respond in JSON format:
{{
    "suggestions": [
        {{
            "name": "Project Name",
            "description": "What this project aims to achieve",
            "rationale": "Why this aligns with priorities",
            "category": "growth",
            "priority": "high"
        }}
    ]
}}

If the business context is too sparse to make meaningful suggestions, return {{"suggestions": [], "reason": "Insufficient context"}}.
"""


async def suggest_from_context(user_id: str) -> list[ContextProjectSuggestion]:
    """Generate project suggestions from user's business context.

    Args:
        user_id: User identifier

    Returns:
        List of ContextProjectSuggestion objects
    """
    # Get user's business context
    user_repo = UserRepository()
    context = user_repo.get_context(user_id)

    if not context:
        logger.info(f"User {user_id} has no business context")
        return []

    # Check for minimum required fields
    if not context.get("primary_objective"):
        logger.info(f"User {user_id} missing primary_objective - insufficient context")
        return []

    # Format context for prompt
    context_text = _format_context_for_prompt(context)

    # Get existing projects to avoid duplication
    project_repo = ProjectRepository()
    _, existing_projects = project_repo.get_by_user(user_id=user_id, page=1, per_page=50)
    existing_projects_section = _format_existing_projects(existing_projects)

    # Call LLM
    prompt = CONTEXT_SUGGESTION_PROMPT.format(
        context_text=context_text,
        existing_projects_section=existing_projects_section,
    )

    try:
        client = _get_client()
        response, _ = await client.call(
            model="haiku",  # Fast model for quick suggestions
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,  # Some creativity for diverse suggestions
            max_tokens=1500,
        )

        suggestions = _parse_suggestions(response, existing_projects)
        return suggestions

    except Exception as e:
        logger.error(f"Failed to generate context suggestions: {e}")
        return []


def _format_context_for_prompt(context: dict) -> str:
    """Format business context fields for the LLM prompt.

    Args:
        context: User's business context dictionary

    Returns:
        Formatted text representation
    """
    lines = []

    # Core fields
    if context.get("primary_objective"):
        lines.append(f"Primary Objective: {context['primary_objective']}")

    if context.get("main_value_proposition"):
        lines.append(f"Value Proposition: {context['main_value_proposition']}")

    if context.get("industry"):
        lines.append(f"Industry: {context['industry']}")

    if context.get("business_model"):
        lines.append(f"Business Model: {context['business_model']}")

    if context.get("business_stage"):
        lines.append(f"Business Stage: {context['business_stage']}")

    # Target market
    if context.get("target_market"):
        lines.append(f"Target Market: {context['target_market']}")

    if context.get("ideal_customer_profile"):
        lines.append(f"Ideal Customer: {context['ideal_customer_profile']}")

    # Competition
    competitors = context.get("competitors") or context.get("detected_competitors")
    if competitors:
        if isinstance(competitors, list):
            lines.append(f"Competitors: {', '.join(competitors[:5])}")
        else:
            lines.append(f"Competitors: {competitors}")

    # Scale indicators
    if context.get("revenue_stage"):
        lines.append(f"Revenue Stage: {context['revenue_stage']}")

    if context.get("team_size"):
        lines.append(f"Team Size: {context['team_size']}")

    # Constraints
    if context.get("budget_constraints"):
        lines.append(f"Budget Constraints: {context['budget_constraints']}")

    if context.get("time_constraints"):
        lines.append(f"Time Constraints: {context['time_constraints']}")

    return "\n".join(lines) if lines else "No context available"


def _format_existing_projects(projects: list[dict]) -> str:
    """Format existing projects for the prompt to avoid duplicates.

    Args:
        projects: List of existing project records

    Returns:
        Formatted section for the prompt
    """
    if not projects:
        return ""

    project_names = [p["name"] for p in projects if p.get("name")]
    if not project_names:
        return ""

    return "\nExisting Projects (DO NOT suggest duplicates):\n- " + "\n- ".join(project_names[:10])


def _parse_suggestions(
    response: str,
    existing_projects: list[dict],
) -> list[ContextProjectSuggestion]:
    """Parse LLM response into ContextProjectSuggestion objects.

    Args:
        response: Raw LLM response text
        existing_projects: Existing projects for duplicate detection

    Returns:
        List of validated ContextProjectSuggestion objects
    """
    import uuid

    try:
        data, errors = parse_json_with_fallback(response, context="context_project_suggester")
        if data is None:
            logger.warning(f"Failed to parse project suggestions: {errors}")
            return []
        raw_suggestions = data.get("suggestions", [])

        # Get existing project names (lowercased) for duplicate check
        existing_names = {p["name"].lower() for p in existing_projects if p.get("name")}

        suggestions = []
        for raw in raw_suggestions:
            name = raw.get("name", "").strip()
            if not name:
                continue

            # Skip if too similar to existing project
            if _is_duplicate(name, existing_names):
                logger.debug(f"Skipping duplicate suggestion: {name}")
                continue

            # Validate and normalize category
            category = raw.get("category", "strategy").lower()
            if category not in VALID_CATEGORIES:
                category = "strategy"

            # Validate priority
            priority = raw.get("priority", "medium").lower()
            if priority not in ["high", "medium", "low"]:
                priority = "medium"

            suggestion_id = str(uuid.uuid4())

            suggestions.append(
                ContextProjectSuggestion(
                    id=suggestion_id,
                    name=name,
                    description=raw.get("description", ""),
                    rationale=raw.get("rationale", ""),
                    category=category,
                    priority=priority,
                )
            )

        return suggestions

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse context suggestions: {e}")
        return []


def _is_duplicate(name: str, existing_names: set[str]) -> bool:
    """Check if a suggestion name is too similar to existing projects.

    Args:
        name: Suggested project name
        existing_names: Set of existing project names (lowercased)

    Returns:
        True if this appears to be a duplicate
    """
    name_lower = name.lower()

    # Exact match
    if name_lower in existing_names:
        return True

    # Check for high word overlap (>60% of words match)
    name_words = set(name_lower.split())
    for existing in existing_names:
        existing_words = set(existing.split())
        if not name_words or not existing_words:
            continue
        overlap = len(name_words & existing_words)
        if overlap / min(len(name_words), len(existing_words)) > 0.6:
            return True

    return False


def get_context_completeness(user_id: str) -> dict:
    """Check how complete the user's business context is.

    Args:
        user_id: User identifier

    Returns:
        Dictionary with completeness score and missing fields
    """
    try:
        user_repo = UserRepository()
        context = user_repo.get_context(user_id)

        if not context:
            return {
                "completeness": 0.0,
                "has_minimum": False,
                "missing_required": REQUIRED_CONTEXT_FIELDS.copy(),
                "missing_recommended": [
                    "main_value_proposition",
                    "industry",
                    "business_model",
                ],
            }

        # Check required fields
        missing_required = [f for f in REQUIRED_CONTEXT_FIELDS if not context.get(f)]

        # Recommended fields for better suggestions
        recommended = [
            "main_value_proposition",
            "industry",
            "business_model",
            "target_market",
            "competitors",
        ]
        missing_recommended = [f for f in recommended if not context.get(f)]

        # Calculate completeness score
        total_fields = len(REQUIRED_CONTEXT_FIELDS) + len(recommended)
        filled_fields = (len(REQUIRED_CONTEXT_FIELDS) - len(missing_required)) + (
            len(recommended) - len(missing_recommended)
        )
        completeness = filled_fields / total_fields if total_fields > 0 else 0.0

        return {
            "completeness": completeness,
            "has_minimum": len(missing_required) == 0,
            "missing_required": missing_required,
            "missing_recommended": missing_recommended,
        }
    except Exception as e:
        logger.error(f"Failed to get context completeness: {e}")
        return {
            "completeness": 0.0,
            "has_minimum": False,
            "missing_required": REQUIRED_CONTEXT_FIELDS.copy(),
            "missing_recommended": [
                "main_value_proposition",
                "industry",
                "business_model",
            ],
        }
