"""Replanning context builder for blocked actions.

Builds comprehensive context for AI-assisted replanning when an action is blocked.
Gathers information about:
- The blocked action details
- Dependencies (what it depends on, what depends on it)
- Project context (if assigned)
- Original session that created the action
- Related actions in the same project
"""

from typing import Any

from bo1.state.repositories.action_repository import action_repository
from bo1.state.repositories.project_repository import project_repository
from bo1.state.repositories.session_repository import session_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


class ReplanningContextBuilder:
    """Builds context for replanning blocked actions."""

    def build_replan_problem_statement(
        self,
        action: dict[str, Any],
        additional_context: str | None = None,
    ) -> str:
        """Build a problem statement for the replanning deliberation.

        The AI needs to understand:
        1. What action was blocked
        2. Why it was blocked
        3. What the original goal was
        4. What dependencies exist
        5. What the user wants to achieve

        Args:
            action: The blocked action details (from action_repository.get)
            additional_context: Optional user-provided context for replanning

        Returns:
            Formatted problem statement for the deliberation
        """
        # Build the problem statement using the template
        parts = []

        # Header
        parts.append("REPLANNING REQUEST: Help Unblock a Stalled Action")
        parts.append("")

        # Original Action Details
        parts.append("## Original Action")
        parts.append(f"**Title:** {action.get('title', 'Unknown')}")
        if action.get("description"):
            parts.append(f"**Description:** {action['description']}")
        if action.get("timeline"):
            parts.append(f"**Timeline:** {action['timeline']}")
        if action.get("priority"):
            parts.append(f"**Priority:** {action['priority'].title()}")
        if action.get("category"):
            parts.append(f"**Category:** {action['category'].replace('_', ' ').title()}")
        parts.append("")

        # What and How (if present)
        if action.get("what_and_how"):
            parts.append("**Implementation Approach:**")
            for item in action["what_and_how"]:
                parts.append(f"- {item}")
            parts.append("")

        # Success Criteria (if present)
        if action.get("success_criteria"):
            parts.append("**Success Criteria:**")
            for item in action["success_criteria"]:
                parts.append(f"- {item}")
            parts.append("")

        # Blocking Status
        parts.append("## Current Status: BLOCKED")
        blocking_reason = action.get("blocking_reason", "No specific reason provided")
        parts.append(f"**Blocking Reason:** {blocking_reason}")
        if action.get("blocked_at"):
            blocked_at = action["blocked_at"]
            if isinstance(blocked_at, str):
                parts.append(f"**Blocked Since:** {blocked_at}")
            else:
                parts.append(f"**Blocked Since:** {blocked_at.isoformat()}")
        parts.append("")

        # User's Additional Context
        if additional_context:
            parts.append("## User's Replanning Request")
            parts.append(additional_context)
            parts.append("")

        # Deliberation Questions
        parts.append("## Questions for the AI Board")
        parts.append(
            "Given this blocked action and its context, please deliberate on the following:"
        )
        parts.append(
            "1. **Alternative Approaches:** What alternative approaches could achieve the original goal?"
        )
        parts.append(
            "2. **Action Modifications:** Should this action be modified, split into smaller tasks, or replaced entirely?"
        )
        parts.append(
            "3. **New Actions:** What new actions might be needed to unblock or work around this?"
        )
        parts.append(
            "4. **Dependency Adjustments:** Do any dependencies need to be adjusted or removed?"
        )
        parts.append(
            "5. **Timeline & Priority:** What are the updated timeline and priority recommendations?"
        )
        parts.append("")
        parts.append(
            "Please provide concrete, actionable recommendations that can be immediately implemented."
        )

        return "\n".join(parts)

    def gather_related_context(
        self,
        action_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Gather all context related to the blocked action.

        Args:
            action_id: ID of the blocked action
            user_id: ID of the user

        Returns:
            Dictionary containing:
            - action: The blocked action details
            - dependencies: What this action depends on
            - dependents: What depends on this action
            - project: Project info (if assigned)
            - original_session: Session that created this action
            - related_actions: Other actions in the same project
        """
        context: dict[str, Any] = {}

        # Get the action details
        action = action_repository.get(action_id)
        if not action:
            raise ValueError(f"Action {action_id} not found")
        # Verify user owns this action
        if action.get("user_id") != user_id:
            raise ValueError(f"Action {action_id} not found")
        context["action"] = action

        # Get dependencies (what this action depends on)
        try:
            deps = action_repository.get_dependencies(action_id)
            context["dependencies"] = deps
        except Exception as e:
            logger.warning(f"Failed to get dependencies for action {action_id}: {e}")
            context["dependencies"] = []

        # Get dependents (what depends on this action)
        try:
            dependents = action_repository.get_dependents(action_id)
            context["dependents"] = dependents
        except Exception as e:
            logger.warning(f"Failed to get dependents for action {action_id}: {e}")
            context["dependents"] = []

        # Get project info if assigned
        project_id = action.get("project_id")
        if project_id:
            try:
                project = project_repository.get(project_id)
                context["project"] = project

                # Get related actions in the same project
                _total, project_actions = project_repository.get_actions(project_id, per_page=20)
                # Filter out the current action
                context["related_actions"] = [
                    a for a in project_actions if a.get("id") != action_id
                ]
            except Exception as e:
                logger.warning(f"Failed to get project info for action {action_id}: {e}")
                context["project"] = None
                context["related_actions"] = []
        else:
            context["project"] = None
            context["related_actions"] = []

        # Get original session info
        source_session_id = action.get("source_session_id")
        if source_session_id:
            try:
                session = session_repository.get(source_session_id)
                if session:
                    context["original_session"] = {
                        "id": session.get("id"),
                        "problem_statement": session.get("problem_statement"),
                        "created_at": session.get("created_at"),
                        "status": session.get("status"),
                    }
                else:
                    context["original_session"] = None
            except Exception as e:
                logger.warning(f"Failed to get original session for action {action_id}: {e}")
                context["original_session"] = None
        else:
            context["original_session"] = None

        return context

    def build_problem_context(
        self,
        related_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the problem_context dict for the replanning session.

        This context is passed to the deliberation as supplementary information.

        Args:
            related_context: Output from gather_related_context()

        Returns:
            Dictionary to be used as problem_context for the session
        """
        problem_context: dict[str, Any] = {
            "is_replanning": True,
            "original_action_id": related_context["action"].get("id"),
            "original_action_title": related_context["action"].get("title"),
        }

        # Add project info
        if related_context.get("project"):
            problem_context["project_id"] = related_context["project"].get("id")
            problem_context["project_name"] = related_context["project"].get("name")

        # Add original session reference
        if related_context.get("original_session"):
            problem_context["original_session_id"] = related_context["original_session"].get("id")
            original_problem = related_context["original_session"].get("problem_statement")
            if original_problem:
                # Truncate if too long
                if len(original_problem) > 500:
                    original_problem = original_problem[:500] + "..."
                problem_context["original_decision"] = original_problem

        # Summarize dependencies
        deps = related_context.get("dependencies", [])
        if deps:
            dep_summary = []
            for dep in deps[:5]:  # Limit to 5
                status = dep.get("status", "unknown")
                title = dep.get("title", "Unknown")
                dep_summary.append(f"- {title} ({status})")
            problem_context["dependencies_summary"] = "\n".join(dep_summary)

        # Summarize dependents (what's waiting on this)
        dependents = related_context.get("dependents", [])
        if dependents:
            dep_summary = []
            for dep in dependents[:5]:  # Limit to 5
                status = dep.get("status", "unknown")
                title = dep.get("title", "Unknown")
                dep_summary.append(f"- {title} ({status})")
            problem_context["blocked_actions_summary"] = "\n".join(dep_summary)

        # Summarize related actions
        related = related_context.get("related_actions", [])
        if related:
            status_counts: dict[str, int] = {}
            for action in related:
                status = action.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            problem_context["project_progress"] = dict(status_counts)

        return problem_context


# Singleton instance
replanning_context_builder = ReplanningContextBuilder()
