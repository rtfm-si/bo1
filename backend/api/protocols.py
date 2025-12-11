"""Protocol definitions for dependency injection in the API layer.

Defines interfaces that decouple API components from concrete implementations,
enabling easier testing and reducing circular dependency risks.
"""

from typing import Any, Protocol


class SessionRepositoryProtocol(Protocol):
    """Protocol for session repository operations used by EventCollector.

    Defines the minimal interface required for session state management
    during deliberation execution. Implementations must provide these methods.
    """

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        ...

    def update_status(
        self,
        session_id: str,
        status: str,
        error_message: str | None = None,
    ) -> bool:
        """Update session status."""
        ...

    def update_phase(self, session_id: str, phase: str) -> bool:
        """Update session phase."""
        ...

    def save_synthesis(self, session_id: str, synthesis_text: str) -> bool:
        """Save synthesis text to session."""
        ...

    def get_events(self, session_id: str) -> list[dict[str, Any]]:
        """Get all events for a session."""
        ...
