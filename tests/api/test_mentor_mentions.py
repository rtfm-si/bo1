"""Tests for mentor mention search functionality."""

from unittest.mock import patch

from backend.services.mention_parser import Mention, MentionType
from backend.services.mention_resolver import (
    MentionResolver,
    ResolvedAction,
    ResolvedMeeting,
    ResolvedMentions,
)


class TestMentionResolver:
    """Tests for MentionResolver service."""

    def test_resolve_empty_mentions(self):
        """Empty mentions list returns empty results."""
        resolver = MentionResolver()
        result = resolver.resolve("user-123", [])

        assert len(result.meetings) == 0
        assert len(result.actions) == 0
        assert len(result.datasets) == 0
        assert not result.has_context()

    @patch("bo1.state.repositories.session_repository.SessionRepository.get")
    def test_resolve_meeting_validates_ownership(self, mock_get):
        """Meeting resolution validates user ownership."""
        mock_get.return_value = {
            "id": "session-123",
            "user_id": "other-user",  # Different user
            "problem_statement": "Test problem",
            "status": "completed",
        }

        resolver = MentionResolver()
        mentions = [
            Mention(type=MentionType.MEETING, id="session-123", raw_text="@meeting:session-123")
        ]
        result = resolver.resolve("user-123", mentions)

        # Should not include session owned by another user
        assert len(result.meetings) == 0
        assert "meeting:session-123" in result.not_found

    @patch("bo1.state.repositories.session_repository.SessionRepository.get")
    def test_resolve_meeting_success(self, mock_get):
        """Meeting resolution returns data for owned sessions."""
        mock_get.return_value = {
            "id": "session-123",
            "user_id": "user-123",  # Same user
            "problem_statement": "Marketing strategy decision",
            "status": "completed",
            "synthesis_text": {"executive_summary": "We should focus on digital marketing."},
            "created_at": "2024-01-15",
        }

        resolver = MentionResolver()
        mentions = [
            Mention(type=MentionType.MEETING, id="session-123", raw_text="@meeting:session-123")
        ]
        result = resolver.resolve("user-123", mentions)

        assert len(result.meetings) == 1
        assert result.meetings[0].id == "session-123"
        assert result.meetings[0].problem_statement == "Marketing strategy decision"
        assert result.meetings[0].status == "completed"
        assert "digital marketing" in result.meetings[0].synthesis_summary

    @patch("bo1.state.repositories.action_repository.ActionRepository.get")
    def test_resolve_action_validates_ownership(self, mock_get):
        """Action resolution validates user ownership."""
        mock_get.return_value = {
            "id": "action-123",
            "user_id": "other-user",  # Different user
            "title": "Test action",
            "status": "todo",
        }

        resolver = MentionResolver()
        mentions = [
            Mention(type=MentionType.ACTION, id="action-123", raw_text="@action:action-123")
        ]
        result = resolver.resolve("user-123", mentions)

        assert len(result.actions) == 0
        assert "action:action-123" in result.not_found

    @patch("bo1.state.repositories.action_repository.ActionRepository.get")
    def test_resolve_action_success(self, mock_get):
        """Action resolution returns data for owned actions."""
        mock_get.return_value = {
            "id": "action-123",
            "user_id": "user-123",
            "title": "Review marketing proposal",
            "description": "Review the Q4 marketing proposal and provide feedback",
            "status": "in_progress",
            "priority": "high",
            "target_end_date": "2024-01-20",
        }

        resolver = MentionResolver()
        mentions = [
            Mention(type=MentionType.ACTION, id="action-123", raw_text="@action:action-123")
        ]
        result = resolver.resolve("user-123", mentions)

        assert len(result.actions) == 1
        assert result.actions[0].id == "action-123"
        assert result.actions[0].title == "Review marketing proposal"
        assert result.actions[0].status == "in_progress"
        assert result.actions[0].priority == "high"

    @patch("bo1.state.repositories.dataset_repository.DatasetRepository.get_profiles")
    @patch("bo1.state.repositories.dataset_repository.DatasetRepository.get_by_id")
    def test_resolve_dataset_success(self, mock_get_by_id, mock_get_profiles):
        """Dataset resolution returns data for owned datasets."""
        mock_get_by_id.return_value = {
            "id": "dataset-123",
            "user_id": "user-123",
            "name": "Q4 Sales Data",
            "description": "Sales data for Q4 2024",
            "row_count": 1000,
            "column_count": 15,
        }
        mock_get_profiles.return_value = [
            {"summary": "Monthly sales data showing strong growth in December."}
        ]

        resolver = MentionResolver()
        mentions = [
            Mention(type=MentionType.DATASET, id="dataset-123", raw_text="@dataset:dataset-123")
        ]
        result = resolver.resolve("user-123", mentions)

        assert len(result.datasets) == 1
        assert result.datasets[0].id == "dataset-123"
        assert result.datasets[0].name == "Q4 Sales Data"
        assert result.datasets[0].row_count == 1000
        assert "growth" in result.datasets[0].summary

    @patch("bo1.state.repositories.session_repository.SessionRepository.get")
    def test_resolve_limits_mentions(self, mock_get):
        """Resolution limits to MAX_MENTIONS to prevent context bloat."""
        from backend.services.mention_resolver import MAX_MENTIONS

        mock_get.return_value = None  # All not found

        resolver = MentionResolver()

        # Create more than MAX_MENTIONS
        mentions = [
            Mention(type=MentionType.MEETING, id=f"session-{i}", raw_text=f"@meeting:session-{i}")
            for i in range(MAX_MENTIONS + 5)
        ]
        result = resolver.resolve("user-123", mentions)

        # Should only process MAX_MENTIONS
        assert len(result.not_found) == MAX_MENTIONS

    @patch("bo1.state.repositories.action_repository.ActionRepository.get")
    @patch("bo1.state.repositories.session_repository.SessionRepository.get")
    def test_resolve_multiple_types(self, mock_session_get, mock_action_get):
        """Resolution handles multiple mention types in one call."""
        mock_session_get.return_value = {
            "id": "session-123",
            "user_id": "user-123",
            "problem_statement": "Test meeting",
            "status": "completed",
        }

        mock_action_get.return_value = {
            "id": "action-123",
            "user_id": "user-123",
            "title": "Test action",
            "status": "todo",
        }

        resolver = MentionResolver()
        mentions = [
            Mention(type=MentionType.MEETING, id="session-123", raw_text="@meeting:session-123"),
            Mention(type=MentionType.ACTION, id="action-123", raw_text="@action:action-123"),
        ]
        result = resolver.resolve("user-123", mentions)

        assert len(result.meetings) == 1
        assert len(result.actions) == 1
        assert result.has_context()


class TestMentionContextFormatting:
    """Tests for formatting resolved mentions into prompt context."""

    def test_format_mentioned_context_empty(self):
        """Empty resolved mentions returns empty string."""
        from bo1.prompts.mentor import format_mentioned_context

        resolved = ResolvedMentions()
        result = format_mentioned_context(resolved)

        assert result == ""

    def test_format_mentioned_context_with_meeting(self):
        """Format includes meeting details."""
        from bo1.prompts.mentor import format_mentioned_context

        resolved = ResolvedMentions(
            meetings=[
                ResolvedMeeting(
                    id="session-123",
                    problem_statement="Marketing strategy",
                    status="completed",
                    synthesis_summary="Focus on digital marketing",
                    created_at="2024-01-15",
                )
            ]
        )
        result = format_mentioned_context(resolved)

        assert "<mentioned_context>" in result
        assert "<referenced_meetings>" in result
        assert "Marketing strategy" in result
        assert "digital marketing" in result
        assert "completed" in result

    def test_format_mentioned_context_with_action(self):
        """Format includes action details."""
        from bo1.prompts.mentor import format_mentioned_context

        resolved = ResolvedMentions(
            actions=[
                ResolvedAction(
                    id="action-123",
                    title="Review proposal",
                    description="Review the Q4 proposal",
                    status="in_progress",
                    priority="high",
                    due_date="2024-01-20",
                )
            ]
        )
        result = format_mentioned_context(resolved)

        assert "<referenced_actions>" in result
        assert "Review proposal" in result
        assert "in_progress" in result
        assert "high" in result

    def test_format_mentioned_context_with_not_found(self):
        """Format includes not found mentions."""
        from bo1.prompts.mentor import format_mentioned_context

        resolved = ResolvedMentions(
            meetings=[ResolvedMeeting(id="1", problem_statement="Test", status="completed")],
            not_found=["meeting:invalid-123", "action:invalid-456"],
        )
        result = format_mentioned_context(resolved)

        assert "<not_found>" in result
        assert "meeting:invalid-123" in result


class TestBuildMentorPromptWithMentions:
    """Tests for build_mentor_prompt with mentioned_context."""

    def test_build_prompt_with_mentioned_context(self):
        """Prompt builder includes mentioned context."""
        from bo1.prompts.mentor import build_mentor_prompt

        result = build_mentor_prompt(
            question="What should I focus on?",
            business_context="<business_context>Test</business_context>",
            mentioned_context="<mentioned_context>Referenced data</mentioned_context>",
        )

        # Both contexts should be present
        assert "<business_context>Test</business_context>" in result
        assert "<mentioned_context>Referenced data</mentioned_context>" in result
        assert "<question>What should I focus on?</question>" in result

    def test_build_prompt_mentioned_context_before_question(self):
        """Mentioned context appears before the question."""
        from bo1.prompts.mentor import build_mentor_prompt

        result = build_mentor_prompt(
            question="My question",
            mentioned_context="<mentioned_context>Test</mentioned_context>",
        )

        mentioned_idx = result.index("<mentioned_context>")
        question_idx = result.index("<question>")
        assert mentioned_idx < question_idx
