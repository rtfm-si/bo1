"""Project suggestion service for extracting project ideas from meetings.

Analyzes meeting problem statements and resulting actions to suggest
new projects that could be created from the meeting's outcomes.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from bo1.llm.client import ClaudeClient
from bo1.state.database import db_session
from bo1.state.repositories.session_repository import session_repository
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
class ProjectSuggestion:
    """A suggested project from meeting analysis.

    Attributes:
        name: Suggested project name
        description: Suggested project description
        action_ids: List of action UUIDs that relate to this project
        confidence: Confidence score (0.0-1.0)
        rationale: Why this project was suggested
    """

    name: str
    description: str
    action_ids: list[str]
    confidence: float
    rationale: str


SUGGESTION_PROMPT = """Analyze this meeting's problem statement and resulting actions to suggest potential projects.

A project is a value-delivery container that groups related actions toward a specific goal.

Meeting Problem Statement:
{problem_statement}

Meeting Actions:
{actions_text}

Based on this meeting, suggest 1-3 potential projects. For each project:
1. Give it a clear, actionable name (e.g., "Launch Customer Portal", "Improve Onboarding Flow")
2. Write a brief description of what the project aims to achieve
3. Identify which action IDs should be assigned to this project
4. Rate your confidence (0.0-1.0) that this is a coherent, useful project grouping
5. Explain your rationale briefly

Respond in JSON format:
{{
    "suggestions": [
        {{
            "name": "Project Name",
            "description": "What this project aims to achieve",
            "action_ids": ["action-uuid-1", "action-uuid-2"],
            "confidence": 0.85,
            "rationale": "Why these actions form a coherent project"
        }}
    ]
}}

Rules:
- Only suggest projects if the actions naturally group together
- Each action should only appear in ONE project suggestion
- Minimum confidence for a suggestion is 0.6
- If no clear projects emerge, return {{"suggestions": []}}
- Use the exact action IDs provided, not made-up ones
"""


async def suggest_projects_from_session(
    session_id: str,
    min_confidence: float = 0.6,
) -> list[ProjectSuggestion]:
    """Analyze a session and suggest potential projects.

    Args:
        session_id: Session identifier
        min_confidence: Minimum confidence threshold (default 0.6)

    Returns:
        List of ProjectSuggestion objects
    """
    # Get session data
    session = session_repository.get(session_id)
    if not session:
        logger.warning(f"Session {session_id} not found for project suggestion")
        return []

    problem_statement = session.get("problem_statement", "")

    # Get session actions
    actions = _get_session_actions(session_id)
    if not actions:
        logger.info(f"Session {session_id} has no actions for project suggestion")
        return []

    # Format actions for prompt
    actions_text = _format_actions_for_prompt(actions)

    # Call LLM for analysis
    prompt = SUGGESTION_PROMPT.format(
        problem_statement=problem_statement,
        actions_text=actions_text,
    )

    try:
        client = _get_client()
        response, _ = await client.call(
            model="haiku",  # Use fast model for quick suggestions
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=1500,
        )

        # Parse response
        suggestions = _parse_suggestions(response, actions, min_confidence)
        return suggestions

    except Exception as e:
        logger.error(f"Failed to generate project suggestions: {e}")
        return []


def _get_session_actions(session_id: str) -> list[dict[str, Any]]:
    """Get actions for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of action records
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, description, status, priority, category,
                       what_and_how, success_criteria
                FROM actions
                WHERE source_session_id = %s
                  AND deleted_at IS NULL
                ORDER BY sort_order, created_at
                """,
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def _format_actions_for_prompt(actions: list[dict[str, Any]]) -> str:
    """Format actions as text for the LLM prompt.

    Args:
        actions: List of action records

    Returns:
        Formatted text representation
    """
    lines = []
    for action in actions:
        lines.append(f"Action ID: {action['id']}")
        lines.append(f"  Title: {action['title']}")
        if action.get("description"):
            lines.append(f"  Description: {action['description']}")
        if action.get("what_and_how"):
            lines.append(f"  How: {action['what_and_how'][:200]}...")
        lines.append(f"  Status: {action['status']}")
        lines.append(f"  Priority: {action.get('priority', 'medium')}")
        lines.append(f"  Category: {action.get('category', 'implementation')}")
        lines.append("")
    return "\n".join(lines)


def _parse_suggestions(
    response: str,
    actions: list[dict[str, Any]],
    min_confidence: float,
) -> list[ProjectSuggestion]:
    """Parse LLM response into ProjectSuggestion objects.

    Args:
        response: Raw LLM response text
        actions: Original actions list (for validation)
        min_confidence: Minimum confidence threshold

    Returns:
        List of validated ProjectSuggestion objects
    """
    try:
        data, errors = parse_json_with_fallback(response, context="project_suggester")
        if data is None:
            logger.warning(f"Failed to parse project suggestions: {errors}")
            return []
        raw_suggestions = data.get("suggestions", [])

        # Get valid action IDs for validation
        valid_action_ids = {str(a["id"]) for a in actions}

        suggestions = []
        for raw in raw_suggestions:
            # Validate confidence
            confidence = float(raw.get("confidence", 0))
            if confidence < min_confidence:
                continue

            # Validate action IDs
            action_ids = [aid for aid in raw.get("action_ids", []) if aid in valid_action_ids]
            if not action_ids:
                continue

            suggestions.append(
                ProjectSuggestion(
                    name=raw.get("name", "Untitled Project"),
                    description=raw.get("description", ""),
                    action_ids=action_ids,
                    confidence=confidence,
                    rationale=raw.get("rationale", ""),
                )
            )

        # Sort by confidence (highest first)
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse project suggestions: {e}")
        return []


async def create_project_from_suggestion(
    session_id: str,
    suggestion: ProjectSuggestion,
    user_id: str,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Create a project from a suggestion and assign its actions.

    Args:
        session_id: Source session identifier
        suggestion: ProjectSuggestion to create
        user_id: User creating the project
        workspace_id: Optional workspace for the project

    Returns:
        Created project record
    """
    from bo1.state.repositories.project_repository import project_repository

    # Create project
    project = project_repository.create(
        user_id=user_id,
        name=suggestion.name,
        description=suggestion.description,
    )

    if not project:
        raise ValueError("Failed to create project")

    project_id = str(project["id"])

    # Update workspace_id if provided
    if workspace_id:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE projects SET workspace_id = %s WHERE id = %s",
                    (workspace_id, project_id),
                )

    # Assign actions to project
    for action_id in suggestion.action_ids:
        project_repository.assign_action(
            action_id=action_id,
            project_id=project_id,
            user_id=user_id,
        )

    # Link session to project
    project_repository.link_session(
        project_id=project_id,
        session_id=session_id,
        relationship="created_from",
    )

    # Recalculate progress
    project_repository.recalculate_progress(project_id)

    # Return updated project
    return project_repository.get(project_id) or project
