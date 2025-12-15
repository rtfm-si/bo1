"""Auto-generate projects from completed actions.

When an action is marked as completed, this service can automatically
create a project if one doesn't already exist with a similar title.
Uses title similarity matching to deduplicate against existing projects.
"""

import logging
import re
from difflib import SequenceMatcher
from typing import Any

from bo1.state.repositories.action_repository import action_repository
from bo1.state.repositories.project_repository import project_repository

logger = logging.getLogger(__name__)

# Threshold for title similarity (0.8 = 80% similar)
SIMILARITY_THRESHOLD = 0.8

# Common action verb prefixes to strip for project names
ACTION_VERB_PREFIXES = [
    "implement",
    "create",
    "build",
    "develop",
    "add",
    "setup",
    "configure",
    "deploy",
    "design",
    "integrate",
    "complete",
    "finish",
    "write",
    "update",
    "fix",
    "refactor",
    "migrate",
    "upgrade",
    "optimize",
    "review",
    "test",
    "document",
]


def normalize_title(title: str) -> str:
    """Normalize a title for comparison.

    Removes common action verbs, punctuation, and normalizes whitespace.

    Args:
        title: Original title

    Returns:
        Normalized title for comparison
    """
    if not title:
        return ""

    # Lowercase
    normalized = title.lower().strip()

    # Remove common action verb prefixes
    for verb in ACTION_VERB_PREFIXES:
        pattern = rf"^{verb}\s+"
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

    # Remove punctuation except hyphens and underscores
    normalized = re.sub(r"[^\w\s\-_]", "", normalized)

    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def calculate_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles.

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity score between 0.0 and 1.0
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    if not norm1 or not norm2:
        return 0.0

    return SequenceMatcher(None, norm1, norm2).ratio()


def extract_project_title(action_title: str) -> str:
    """Extract a project title from an action title.

    Strips common action verbs to get a cleaner project name.

    Args:
        action_title: Original action title

    Returns:
        Cleaned project title
    """
    if not action_title:
        return "Untitled Project"

    title = action_title.strip()

    # Strip common action verb prefixes (keep original case)
    for verb in ACTION_VERB_PREFIXES:
        pattern = rf"^{verb}\s+"
        if re.match(pattern, title, flags=re.IGNORECASE):
            title = re.sub(pattern, "", title, count=1, flags=re.IGNORECASE)
            break

    # Title case the result if it's all lowercase
    if title == title.lower():
        title = title.title()

    return title.strip() or "Untitled Project"


def find_similar_project(
    user_id: str,
    title: str,
    threshold: float = SIMILARITY_THRESHOLD,
) -> dict[str, Any] | None:
    """Find an existing project with a similar title.

    Args:
        user_id: User who owns the projects
        title: Title to match against
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        Matching project record or None if no match
    """
    # Get user's projects
    _, projects = project_repository.get_by_user(user_id, per_page=500)

    best_match = None
    best_score = 0.0

    for project in projects:
        project_name = project.get("name", "")
        score = calculate_similarity(title, project_name)

        if score >= threshold and score > best_score:
            best_match = project
            best_score = score

    if best_match:
        logger.debug(
            f"Found similar project '{best_match.get('name')}' "
            f"for title '{title}' (similarity: {best_score:.2f})"
        )

    return best_match


def is_action_project_worthy(action: dict[str, Any]) -> bool:
    """Determine if an action should trigger project generation.

    Filters out tactical/narrow actions that shouldn't become projects.

    Args:
        action: Action record

    Returns:
        True if action should trigger project generation
    """
    title = action.get("title", "")
    description = action.get("description", "")

    # Too short titles are likely tactical
    if len(title) < 15:
        return False

    # Actions with dependencies are more strategic
    # (This could be enhanced to check action_dependencies table)

    # Exclude certain tactical categories
    tactical_keywords = [
        "fix bug",
        "quick fix",
        "hotfix",
        "patch",
        "typo",
        "cleanup",
        "minor",
        "small",
    ]
    title_lower = title.lower()
    for keyword in tactical_keywords:
        if keyword in title_lower:
            return False

    # Long descriptions suggest more strategic work
    if len(description) > 100:
        return True

    # Has success criteria suggests planned work
    if action.get("success_criteria"):
        return True

    # Has what_and_how suggests detailed planning
    if action.get("what_and_how"):
        return True

    # Default: generate project for non-trivial titles
    return len(title) >= 20


def generate_project_from_action(
    action_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """Generate a project from a completed action.

    Checks for similar existing projects and either:
    1. Links the action to an existing similar project, or
    2. Creates a new project and links the action

    Args:
        action_id: Action UUID
        user_id: User ID (for verification and project creation)

    Returns:
        Created or matched project record, or None if not generated
    """
    # Get action
    action = action_repository.get(action_id)
    if not action:
        logger.warning(f"Action {action_id} not found for project generation")
        return None

    # Verify ownership
    if action.get("user_id") != user_id:
        logger.warning(f"Action {action_id} does not belong to user {user_id}")
        return None

    # Check if action already has a project
    if action.get("project_id"):
        logger.debug(f"Action {action_id} already assigned to project {action.get('project_id')}")
        return None

    # Check if action is project-worthy
    if not is_action_project_worthy(action):
        logger.debug(f"Action {action_id} is not project-worthy, skipping")
        return None

    action_title = action.get("title", "")
    project_title = extract_project_title(action_title)

    # Check for similar existing projects
    existing = find_similar_project(user_id, project_title)

    if existing:
        # Link action to existing project
        project_id = str(existing["id"])
        logger.info(f"Linking action {action_id} to existing project '{existing.get('name')}'")

        project_repository.assign_action(action_id, project_id, user_id)
        project_repository.recalculate_progress(project_id)

        return existing

    # Create new project
    logger.info(f"Creating new project '{project_title}' from action {action_id}")

    project = project_repository.create(
        user_id=user_id,
        name=project_title,
        description=action.get("description", ""),
        status="active",
    )

    if not project:
        logger.error(f"Failed to create project for action {action_id}")
        return None

    project_id = str(project["id"])

    # Link action to new project
    project_repository.assign_action(action_id, project_id, user_id)

    # Link session to project if action has a source session
    session_id = action.get("source_session_id")
    if session_id:
        project_repository.link_session(
            project_id=project_id,
            session_id=session_id,
            relationship="created_from",
        )

    # Recalculate progress
    project_repository.recalculate_progress(project_id)

    return project


async def maybe_generate_project(action_id: str, user_id: str) -> dict[str, Any] | None:
    """Async wrapper for project generation.

    Called from action completion handlers. Non-blocking - errors are logged
    but don't affect the action completion.

    Args:
        action_id: Action UUID
        user_id: User ID

    Returns:
        Created/matched project or None
    """
    from bo1.config import get_settings

    settings = get_settings()

    # Check if auto-generation is enabled
    if not getattr(settings, "auto_generate_projects", True):
        logger.debug("Auto-generate projects is disabled")
        return None

    try:
        return generate_project_from_action(action_id, user_id)
    except Exception as e:
        logger.error(f"Failed to auto-generate project for action {action_id}: {e}")
        return None
