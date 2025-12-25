"""Mention resolver service for mentor chat.

Resolves mentions to actual entities and validates user ownership.
"""

import logging
from dataclasses import dataclass, field

from backend.services.mention_parser import Mention, MentionType
from backend.services.mentor_conversation_repo import get_mentor_conversation_repo
from bo1.state.repositories.action_repository import ActionRepository
from bo1.state.repositories.dataset_repository import DatasetRepository
from bo1.state.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)

# Maximum mentions to resolve (prevent context bloat)
MAX_MENTIONS = 5


@dataclass
class ResolvedMeeting:
    """Resolved meeting/session data."""

    id: str
    problem_statement: str
    status: str
    synthesis_summary: str | None = None
    created_at: str | None = None


@dataclass
class ResolvedAction:
    """Resolved action data."""

    id: str
    title: str
    description: str | None
    status: str
    priority: str | None = None
    due_date: str | None = None


@dataclass
class ResolvedDataset:
    """Resolved dataset data."""

    id: str
    name: str
    description: str | None
    row_count: int | None = None
    column_count: int | None = None
    summary: str | None = None


@dataclass
class ResolvedChat:
    """Resolved mentor chat conversation data."""

    id: str
    label: str | None
    persona: str
    created_at: str | None = None
    message_preview: str | None = None


@dataclass
class ResolvedMentions:
    """Container for all resolved mention data."""

    meetings: list[ResolvedMeeting] = field(default_factory=list)
    actions: list[ResolvedAction] = field(default_factory=list)
    datasets: list[ResolvedDataset] = field(default_factory=list)
    chats: list[ResolvedChat] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)  # IDs that couldn't be resolved

    def has_context(self) -> bool:
        """Check if any context was resolved."""
        return bool(self.meetings or self.actions or self.datasets or self.chats)


class MentionResolver:
    """Resolves mentions to actual entity data."""

    def __init__(self) -> None:
        """Initialize resolver with repository dependencies."""
        self._session_repo = SessionRepository()
        self._action_repo = ActionRepository()
        self._dataset_repo = DatasetRepository()
        self._mentor_repo = get_mentor_conversation_repo()

    def resolve(self, user_id: str, mentions: list[Mention]) -> ResolvedMentions:
        """Resolve mentions to entity data.

        Validates user ownership - only returns entities owned by the user.
        Limits to MAX_MENTIONS to prevent context bloat.

        Args:
            user_id: User making the request
            mentions: List of parsed mentions

        Returns:
            ResolvedMentions with entity data
        """
        result = ResolvedMentions()

        # Limit mentions
        mentions = mentions[:MAX_MENTIONS]

        for mention in mentions:
            try:
                if mention.type == MentionType.MEETING:
                    resolved = self._resolve_meeting(user_id, mention.id)
                    if resolved:
                        result.meetings.append(resolved)
                    else:
                        result.not_found.append(f"meeting:{mention.id}")

                elif mention.type == MentionType.ACTION:
                    resolved = self._resolve_action(user_id, mention.id)
                    if resolved:
                        result.actions.append(resolved)
                    else:
                        result.not_found.append(f"action:{mention.id}")

                elif mention.type == MentionType.DATASET:
                    resolved = self._resolve_dataset(user_id, mention.id)
                    if resolved:
                        result.datasets.append(resolved)
                    else:
                        result.not_found.append(f"dataset:{mention.id}")

                elif mention.type == MentionType.CHAT:
                    resolved = self._resolve_chat(user_id, mention.id)
                    if resolved:
                        result.chats.append(resolved)
                    else:
                        result.not_found.append(f"chat:{mention.id}")

            except Exception as e:
                logger.warning(f"Error resolving mention {mention.type}:{mention.id}: {e}")
                result.not_found.append(f"{mention.type.value}:{mention.id}")

        return result

    def _resolve_meeting(self, user_id: str, session_id: str) -> ResolvedMeeting | None:
        """Resolve a meeting/session mention."""
        session = self._session_repo.get(session_id)
        if not session:
            return None

        # Security: validate ownership
        if session.get("user_id") != user_id:
            logger.warning(
                f"User {user_id} attempted to access session {session_id} owned by another user"
            )
            return None

        # Extract synthesis summary if available
        synthesis_summary = None
        if session.get("synthesis_text"):
            synthesis = session["synthesis_text"]
            if isinstance(synthesis, dict):
                synthesis_summary = synthesis.get("executive_summary", "")[:500]
            elif isinstance(synthesis, str):
                synthesis_summary = synthesis[:500]

        return ResolvedMeeting(
            id=str(session["id"]),
            problem_statement=session.get("problem_statement", "")[:300],
            status=session.get("status", "unknown"),
            synthesis_summary=synthesis_summary,
            created_at=str(session.get("created_at", ""))[:10]
            if session.get("created_at")
            else None,
        )

    def _resolve_action(self, user_id: str, action_id: str) -> ResolvedAction | None:
        """Resolve an action mention."""
        action = self._action_repo.get(action_id)
        if not action:
            return None

        # Security: validate ownership
        if action.get("user_id") != user_id:
            logger.warning(
                f"User {user_id} attempted to access action {action_id} owned by another user"
            )
            return None

        # Get due date (prefer target, fall back to estimated)
        due_date = action.get("target_end_date") or action.get("estimated_end_date")
        if due_date:
            due_date = str(due_date)[:10]

        return ResolvedAction(
            id=str(action["id"]),
            title=action.get("title", "Untitled"),
            description=action.get("description", "")[:300] if action.get("description") else None,
            status=action.get("status", "unknown"),
            priority=action.get("priority"),
            due_date=due_date,
        )

    def _resolve_dataset(self, user_id: str, dataset_id: str) -> ResolvedDataset | None:
        """Resolve a dataset mention."""
        dataset = self._dataset_repo.get_by_id(dataset_id, user_id)
        if not dataset:
            return None

        # get_by_id already validates ownership via user_id parameter

        # Get summary from profiles if available
        summary = None
        profiles = self._dataset_repo.get_profiles(dataset_id)
        if profiles:
            # Get the latest profile with a summary
            for profile in profiles:
                if profile.get("summary"):
                    summary = profile["summary"][:300]
                    break

        return ResolvedDataset(
            id=str(dataset["id"]),
            name=dataset.get("name", "Unnamed"),
            description=dataset.get("description", "")[:200]
            if dataset.get("description")
            else None,
            row_count=dataset.get("row_count"),
            column_count=dataset.get("column_count"),
            summary=summary,
        )

    def _resolve_chat(self, user_id: str, conversation_id: str) -> ResolvedChat | None:
        """Resolve a mentor chat conversation mention."""
        conversation = self._mentor_repo.get(conversation_id, user_id)
        if not conversation:
            return None

        # get() already validates ownership via user_id parameter

        # Get a preview of recent messages (last 2-3 exchanges)
        messages = conversation.get("messages", [])
        message_preview = None
        if messages:
            # Get last few messages for context
            recent = messages[-6:]  # Up to 3 exchanges (user + assistant)
            previews = []
            for msg in recent:
                role = msg.get("role", "")
                content = msg.get("content", "")[:100]
                if role == "user":
                    previews.append(f"User: {content}")
                elif role == "assistant":
                    previews.append(f"Mentor: {content}")
            message_preview = " | ".join(previews)[:300] if previews else None

        return ResolvedChat(
            id=str(conversation["id"]),
            label=conversation.get("label"),
            persona=conversation.get("persona", "general"),
            created_at=str(conversation.get("created_at", ""))[:10]
            if conversation.get("created_at")
            else None,
            message_preview=message_preview,
        )


# Singleton instance
_resolver: MentionResolver | None = None


def get_mention_resolver() -> MentionResolver:
    """Get singleton mention resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = MentionResolver()
    return _resolver
