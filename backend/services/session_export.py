"""Session export service for JSON and Markdown formats.

Provides:
- SessionExporter class for exporting sessions to JSON and Markdown
- Serialization of session metadata, events, conclusions, and actions
- Permission checking (session ownership)
"""

from datetime import UTC, datetime
from typing import Any

from bo1.utils.logging import get_logger

logger = get_logger(__name__)


class SessionExporter:
    """Export session data to JSON and Markdown formats."""

    def __init__(self) -> None:
        """Initialize exporter (uses repository for database access)."""
        pass

    async def export_to_json(self, session_id: str, user_id: str) -> dict[str, Any]:
        """Export session to JSON format.

        Includes: metadata, all events, conclusions, actions.

        Args:
            session_id: Session UUID
            user_id: User UUID (for permission check)

        Returns:
            Dictionary with session data

        Raises:
            ValueError: If session not found or user lacks permission
        """
        # Import here to avoid circular dependencies
        from bo1.state.repositories.session_repository import session_repository

        session_data = session_repository.get_session_by_id(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        if session_data.get("user_id") != user_id:
            raise ValueError("User does not own this session")

        # Build export
        export = {
            "metadata": {
                "session_id": session_data.get("id"),
                "problem_statement": session_data.get("problem_statement"),
                "problem_context": session_data.get("problem_context"),
                "status": session_data.get("status"),
                "created_at": session_data.get("created_at"),
                "completed_at": session_data.get("completed_at"),
            },
            "conclusion": session_data.get("conclusion"),
            "synthesis": session_data.get("synthesis"),
            "actions": [],
        }

        return export

    async def export_to_markdown(self, session_id: str, user_id: str) -> str:
        """Export session to human-readable Markdown format.

        Includes: summary, synthesis, actions.

        Args:
            session_id: Session UUID
            user_id: User UUID (for permission check)

        Returns:
            Markdown-formatted report

        Raises:
            ValueError: If session not found or user lacks permission
        """
        # Import here to avoid circular dependencies
        from bo1.state.repositories.session_repository import session_repository

        session_data = session_repository.get_session_by_id(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        if session_data.get("user_id") != user_id:
            raise ValueError("User does not own this session")

        md = []
        md.append("# Deliberation Report\n")

        # Header
        md.append(f"## Problem Statement\n{session_data.get('problem_statement')}\n")

        problem_context = session_data.get("problem_context")
        if problem_context:
            md.append("## Context\n")
            if isinstance(problem_context, dict):
                for key, value in problem_context.items():
                    md.append(f"- **{key}**: {value}")
            md.append("")

        # Synthesis & Conclusion
        synthesis = session_data.get("synthesis")
        if synthesis:
            md.append("## Synthesis\n")
            # Strip JSON footer if present
            synthesis_text = synthesis
            if isinstance(synthesis_text, str) and "\n```json" in synthesis_text:
                synthesis_text = synthesis_text.split("\n```json")[0]
            md.append(f"{synthesis_text}\n")

        conclusion = session_data.get("conclusion")
        if conclusion:
            md.append("## Conclusion\n")
            md.append(f"{conclusion}\n")

        # Footer
        md.append(f"---\n_Generated {datetime.now(UTC).isoformat()}_\n")

        return "\n".join(md)
