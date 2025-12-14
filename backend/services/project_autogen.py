"""Project autogeneration service for clustering unassigned actions into projects.

Analyzes unassigned actions using LLM to identify coherent groupings
and suggest new projects for user review before creation.
"""

import logging
from dataclasses import dataclass
from typing import Any

from bo1.llm.client import ClaudeClient
from bo1.state.database import db_session
from bo1.state.repositories.project_repository import ProjectRepository

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
class AutogenProjectSuggestion:
    """A suggested project from action clustering.

    Attributes:
        id: Unique identifier for this suggestion (generated)
        name: Suggested project name
        description: Suggested project description
        action_ids: List of action UUIDs that belong to this project
        confidence: Confidence score (0.0-1.0)
        rationale: Why these actions form a coherent project
    """

    id: str
    name: str
    description: str
    action_ids: list[str]
    confidence: float
    rationale: str


# Minimum actions required to trigger autogeneration
MIN_ACTIONS_FOR_AUTOGEN = 3

# Maximum recent actions to analyze (prevents overwhelming the LLM)
MAX_ACTIONS_TO_ANALYZE = 50

CLUSTERING_PROMPT = """Analyze these unassigned actions and cluster them into suggested projects.

A project is a value-delivery container that groups related actions toward a specific goal.

Unassigned Actions:
{actions_text}

Based on these actions, suggest 1-5 potential projects. For each project:
1. Give it a clear, actionable name (e.g., "Launch Customer Portal", "Improve Onboarding Flow")
2. Write a brief description of what the project aims to achieve
3. Identify which action IDs should be grouped into this project
4. Rate your confidence (0.0-1.0) that this is a coherent, useful project grouping
5. Explain your rationale briefly

Guidelines:
- Group actions by shared themes, goals, or outcomes
- Consider action categories, titles, and descriptions when clustering
- Actions from the same meeting source may naturally belong together
- Each action should only appear in ONE project suggestion
- Some actions may not fit any project - leave them unassigned
- Minimum confidence for a suggestion is 0.6
- If actions don't form clear groupings, suggest fewer projects

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

If no clear projects emerge from the actions, return {{"suggestions": []}}.
"""


async def get_autogen_suggestions(
    user_id: str,
    min_confidence: float = 0.6,
) -> list[AutogenProjectSuggestion]:
    """Analyze unassigned actions and suggest project groupings.

    Args:
        user_id: User identifier
        min_confidence: Minimum confidence threshold (default 0.6)

    Returns:
        List of AutogenProjectSuggestion objects
    """
    # Get unassigned actions
    actions = _get_unassigned_actions(user_id)

    if len(actions) < MIN_ACTIONS_FOR_AUTOGEN:
        logger.info(
            f"User {user_id} has {len(actions)} unassigned actions "
            f"(minimum {MIN_ACTIONS_FOR_AUTOGEN} required for autogen)"
        )
        return []

    # Limit to recent actions if too many
    if len(actions) > MAX_ACTIONS_TO_ANALYZE:
        actions = actions[:MAX_ACTIONS_TO_ANALYZE]
        logger.info(f"Limited to {MAX_ACTIONS_TO_ANALYZE} most recent actions for analysis")

    # Format actions for prompt
    actions_text = _format_actions_for_prompt(actions)

    # Call LLM for clustering analysis
    prompt = CLUSTERING_PROMPT.format(actions_text=actions_text)

    try:
        client = _get_client()
        response, _ = await client.call(
            model="haiku",  # Use fast model for quick analysis
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for consistent output
            max_tokens=2000,
        )

        # Parse response
        suggestions = _parse_suggestions(response, actions, min_confidence)
        return suggestions

    except Exception as e:
        logger.error(f"Failed to generate autogen suggestions: {e}")
        return []


def _get_unassigned_actions(user_id: str) -> list[dict[str, Any]]:
    """Get unassigned actions for a user.

    Args:
        user_id: User identifier

    Returns:
        List of action records without project assignments
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.title, a.description, a.status, a.priority, a.category,
                       a.what_and_how, a.success_criteria, a.source_session_id,
                       s.problem_statement as session_problem
                FROM actions a
                LEFT JOIN sessions s ON a.source_session_id = s.id
                WHERE a.user_id = %s
                  AND a.project_id IS NULL
                  AND a.deleted_at IS NULL
                ORDER BY a.created_at DESC
                LIMIT %s
                """,
                (user_id, MAX_ACTIONS_TO_ANALYZE),
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
            lines.append(f"  Description: {action['description'][:200]}")
        if action.get("what_and_how"):
            lines.append(f"  How: {action['what_and_how'][:150]}...")
        lines.append(f"  Status: {action['status']}")
        lines.append(f"  Priority: {action.get('priority', 'medium')}")
        lines.append(f"  Category: {action.get('category', 'implementation')}")
        if action.get("session_problem"):
            lines.append(f"  Source Meeting: {action['session_problem'][:100]}...")
        lines.append("")
    return "\n".join(lines)


def _parse_suggestions(
    response: str,
    actions: list[dict[str, Any]],
    min_confidence: float,
) -> list[AutogenProjectSuggestion]:
    """Parse LLM response into AutogenProjectSuggestion objects.

    Args:
        response: Raw LLM response text
        actions: Original actions list (for validation)
        min_confidence: Minimum confidence threshold

    Returns:
        List of validated AutogenProjectSuggestion objects
    """
    import json
    import uuid

    try:
        # Extract JSON from response
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]

        data = json.loads(json_str.strip())
        raw_suggestions = data.get("suggestions", [])

        # Get valid action IDs for validation
        valid_action_ids = {str(a["id"]) for a in actions}

        # Track used action IDs to prevent duplicates across suggestions
        used_action_ids: set[str] = set()

        suggestions = []
        for raw in raw_suggestions:
            # Validate confidence
            confidence = float(raw.get("confidence", 0))
            if confidence < min_confidence:
                continue

            # Validate and filter action IDs (no duplicates, only valid IDs)
            action_ids = [
                aid
                for aid in raw.get("action_ids", [])
                if aid in valid_action_ids and aid not in used_action_ids
            ]

            if not action_ids:
                continue

            # Mark these action IDs as used
            used_action_ids.update(action_ids)

            # Generate unique ID for this suggestion
            suggestion_id = str(uuid.uuid4())

            suggestions.append(
                AutogenProjectSuggestion(
                    id=suggestion_id,
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
        logger.error(f"Failed to parse autogen suggestions: {e}")
        return []


def get_unassigned_action_count(user_id: str) -> int:
    """Get count of unassigned actions for a user.

    Args:
        user_id: User identifier

    Returns:
        Number of actions without project assignments
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM actions
                WHERE user_id = %s
                  AND project_id IS NULL
                  AND deleted_at IS NULL
                """,
                (user_id,),
            )
            result = cur.fetchone()
            return result["count"] if result else 0


async def create_projects_from_suggestions(
    suggestions: list[AutogenProjectSuggestion],
    user_id: str,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    """Create projects from selected suggestions and assign actions.

    Args:
        suggestions: List of suggestions to create
        user_id: User creating the projects
        workspace_id: Optional workspace for the projects

    Returns:
        List of created project records
    """
    project_repo = ProjectRepository()
    created_projects = []

    for suggestion in suggestions:
        # Create project
        project = project_repo.create(
            user_id=user_id,
            name=suggestion.name,
            description=suggestion.description,
        )

        if not project:
            logger.error(f"Failed to create project: {suggestion.name}")
            continue

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
            project_repo.assign_action(
                action_id=action_id,
                project_id=project_id,
                user_id=user_id,
            )

        # Recalculate progress
        project_repo.recalculate_progress(project_id)

        # Get updated project
        updated_project = project_repo.get(project_id)
        if updated_project:
            created_projects.append(updated_project)

    return created_projects
