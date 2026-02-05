"""Blocker analyzer service using Claude Haiku.

Suggests unblock paths for blocked actions using fast, cheap LLM calls.
Cost: ~$0.0005/request (1K input + 500 output tokens at Haiku rates)

Provides:
- 3-5 actionable suggestions per blocked action
- Effort estimation (low/medium/high)
- Rationale for each approach
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.prompts.blocker import BLOCKER_SYSTEM_PROMPT, build_blocker_prompt
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)


class EffortLevel(str, Enum):
    """Effort required to implement a suggestion."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class UnblockSuggestion:
    """A single suggestion for unblocking an action."""

    approach: str
    rationale: str
    effort_level: EffortLevel

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "approach": self.approach,
            "rationale": self.rationale,
            "effort_level": self.effort_level.value,
        }


class BlockerAnalyzer:
    """Analyzes blocked actions and suggests unblock paths."""

    MAX_SUGGESTIONS = 5

    def __init__(self) -> None:
        """Initialize analyzer with lazy broker."""
        self._broker: PromptBroker | None = None

    def _get_broker(self) -> PromptBroker:
        """Lazy-initialize prompt broker."""
        if self._broker is None:
            self._broker = PromptBroker()
        return self._broker

    async def suggest_unblock_paths(
        self,
        title: str,
        description: str | None = None,
        blocking_reason: str | None = None,
        project_name: str | None = None,
    ) -> list[UnblockSuggestion]:
        """Generate unblock suggestions for a blocked action.

        Args:
            title: Action title
            description: Optional action description
            blocking_reason: Why the action is blocked
            project_name: Optional project name for context

        Returns:
            List of 3-5 UnblockSuggestion objects
        """
        user_prompt = build_blocker_prompt(
            title=title,
            description=description,
            blocking_reason=blocking_reason,
            project_name=project_name,
        )

        try:
            broker = self._get_broker()
            request = PromptRequest(
                system=BLOCKER_SYSTEM_PROMPT,
                user_message=user_prompt,
                model="haiku",
                max_tokens=1000,
                temperature=0.7,  # Some creativity for varied suggestions
                agent_type="BlockerAnalyzer",
                prompt_type="blocker_analysis",
            )

            response = await broker.call(request)
            return self._parse_suggestions(response.text)

        except Exception as e:
            logger.warning(f"Blocker analysis failed: {e}")
            return self._fallback_suggestions(blocking_reason)

    def _parse_suggestions(self, response_text: str) -> list[UnblockSuggestion]:
        """Parse LLM response into UnblockSuggestion objects.

        Args:
            response_text: Raw LLM response (expected JSON array)

        Returns:
            List of parsed suggestions, max 5
        """
        try:
            data, errors = parse_json_with_fallback(response_text, context="blocker_analyzer")
            if data is None:
                logger.warning(f"Failed to parse blocker suggestions: {errors}")
                return self._fallback_suggestions(None)
            if not isinstance(data, list):
                raise ValueError("Expected JSON array")

            suggestions = []
            for item in data[: self.MAX_SUGGESTIONS]:
                effort_str = item.get("effort_level", "medium").lower()
                try:
                    effort = EffortLevel(effort_str)
                except ValueError:
                    effort = EffortLevel.MEDIUM

                suggestions.append(
                    UnblockSuggestion(
                        approach=str(item.get("approach", ""))[:500],
                        rationale=str(item.get("rationale", ""))[:500],
                        effort_level=effort,
                    )
                )

            return suggestions if suggestions else self._fallback_suggestions(None)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse blocker suggestions: {e}")
            return self._fallback_suggestions(None)

    def _fallback_suggestions(self, blocking_reason: str | None) -> list[UnblockSuggestion]:
        """Return generic fallback suggestions when LLM fails.

        Args:
            blocking_reason: Original blocking reason for context

        Returns:
            List of 3 generic suggestions
        """
        return [
            UnblockSuggestion(
                approach="Break into smaller sub-tasks",
                rationale="Large tasks often get blocked because they're overwhelming. Identify the smallest next step.",
                effort_level=EffortLevel.LOW,
            ),
            UnblockSuggestion(
                approach="Identify and remove the dependency",
                rationale="If blocked on someone or something, directly address that dependency or find an alternative path.",
                effort_level=EffortLevel.MEDIUM,
            ),
            UnblockSuggestion(
                approach="Time-box and just start",
                rationale="Set a 25-minute timer and commit to making any progress. Starting often reveals the path forward.",
                effort_level=EffortLevel.LOW,
            ),
        ]


# Module-level singleton
_analyzer: BlockerAnalyzer | None = None


def get_blocker_analyzer() -> BlockerAnalyzer:
    """Get or create the blocker analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = BlockerAnalyzer()
    return _analyzer


async def escalate_blocked_action(
    action_id: str,
    user_id: str,
    include_suggestions: bool = True,
) -> dict:
    """Create a meeting session to resolve a blocked action.

    Args:
        action_id: UUID of the blocked action
        user_id: UUID of the user
        include_suggestions: Whether to include unblock suggestions in context

    Returns:
        Dict with session_id and redirect_url

    Raises:
        ValueError: If action not found, not blocked, or not owned by user
    """
    from backend.api.dependencies import get_redis_manager
    from bo1.state.repositories.action_repository import action_repository
    from bo1.state.repositories.project_repository import ProjectRepository
    from bo1.state.repositories.session_repository import SessionRepository

    # Fetch action with ownership check
    action = action_repository.get(action_id)
    if not action:
        raise ValueError("Action not found")
    if action.get("user_id") != user_id:
        raise ValueError("Not authorized")
    if action.get("status") != "blocked":
        raise ValueError("Action is not blocked")

    # Get project name if linked
    project_name = None
    project_id = action.get("project_id")
    if project_id:
        project_repo = ProjectRepository()
        project = project_repo.get(project_id)
        if project:
            project_name = project.get("name")

    # Build problem statement (truncate title to 200 chars)
    title = action.get("title", "Unknown action")[:200]
    problem_statement = f"How can we unblock: {title}?"

    # Build context
    context = {
        "action_id": action_id,
        "action_title": action.get("title"),
        "action_description": action.get("description"),
        "blocking_reason": action.get("blocking_reason"),
        "blocked_at": action.get("blocked_at").isoformat() if action.get("blocked_at") else None,
    }

    if project_name:
        context["project_name"] = project_name

    # Get unblock suggestions if requested
    if include_suggestions:
        analyzer = get_blocker_analyzer()
        suggestions = await analyzer.suggest_unblock_paths(
            title=action.get("title", ""),
            description=action.get("description"),
            blocking_reason=action.get("blocking_reason"),
            project_name=project_name,
        )
        context["prior_suggestions"] = [s.to_dict() for s in suggestions]

    # Create session
    redis_manager = get_redis_manager()
    if not redis_manager.is_available:
        raise ValueError("Service temporarily unavailable")

    session_id = redis_manager.create_session()
    session_repo = SessionRepository()

    session = session_repo.create(
        session_id=session_id,
        user_id=user_id,
        problem_statement=problem_statement,
        problem_context=context,
    )

    if not session:
        raise ValueError("Failed to create session")

    return {
        "session_id": session_id,
        "redirect_url": f"/meetings/{session_id}",
    }
