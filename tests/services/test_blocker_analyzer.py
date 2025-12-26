"""Tests for blocker analyzer service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.blocker_analyzer import (
    BlockerAnalyzer,
    EffortLevel,
    UnblockSuggestion,
    get_blocker_analyzer,
)


class TestUnblockSuggestion:
    """Tests for UnblockSuggestion dataclass."""

    def test_to_dict_low_effort(self):
        """to_dict should include effort level as string."""
        suggestion = UnblockSuggestion(
            approach="Break into smaller tasks",
            rationale="Smaller tasks are easier to complete",
            effort_level=EffortLevel.LOW,
        )
        result = suggestion.to_dict()
        assert result == {
            "approach": "Break into smaller tasks",
            "rationale": "Smaller tasks are easier to complete",
            "effort_level": "low",
        }

    def test_to_dict_high_effort(self):
        """High effort level should serialize correctly."""
        suggestion = UnblockSuggestion(
            approach="Redesign the architecture",
            rationale="Need to rethink the approach",
            effort_level=EffortLevel.HIGH,
        )
        result = suggestion.to_dict()
        assert result["effort_level"] == "high"


class TestBlockerAnalyzerFallback:
    """Tests for fallback suggestion generation."""

    def test_fallback_returns_three_suggestions(self):
        """Fallback should return exactly 3 generic suggestions."""
        analyzer = BlockerAnalyzer()
        result = analyzer._fallback_suggestions(None)
        assert len(result) == 3
        assert all(isinstance(s, UnblockSuggestion) for s in result)

    def test_fallback_includes_varied_effort_levels(self):
        """Fallback suggestions should include different effort levels."""
        analyzer = BlockerAnalyzer()
        result = analyzer._fallback_suggestions("External blocker")
        effort_levels = {s.effort_level for s in result}
        # Should have at least low and medium
        assert EffortLevel.LOW in effort_levels
        assert EffortLevel.MEDIUM in effort_levels


class TestBlockerAnalyzerParsing:
    """Tests for LLM response parsing."""

    def test_parse_valid_json(self):
        """Valid JSON array should be parsed correctly."""
        analyzer = BlockerAnalyzer()
        response = json.dumps(
            [
                {"approach": "Do X", "rationale": "Because Y", "effort_level": "low"},
                {"approach": "Try Z", "rationale": "Might help", "effort_level": "high"},
            ]
        )
        result = analyzer._parse_suggestions(response)
        assert len(result) == 2
        assert result[0].approach == "Do X"
        assert result[0].effort_level == EffortLevel.LOW
        assert result[1].effort_level == EffortLevel.HIGH

    def test_parse_json_with_markdown_wrapper(self):
        """JSON wrapped in markdown code block should be parsed."""
        analyzer = BlockerAnalyzer()
        response = """```json
[
    {"approach": "Test approach", "rationale": "Test reason", "effort_level": "medium"}
]
```"""
        result = analyzer._parse_suggestions(response)
        assert len(result) == 1
        assert result[0].approach == "Test approach"
        assert result[0].effort_level == EffortLevel.MEDIUM

    def test_parse_invalid_json_returns_fallback(self):
        """Invalid JSON should return fallback suggestions."""
        analyzer = BlockerAnalyzer()
        result = analyzer._parse_suggestions("Not valid JSON at all")
        assert len(result) == 3  # Fallback count

    def test_parse_empty_array_returns_fallback(self):
        """Empty array should return fallback suggestions."""
        analyzer = BlockerAnalyzer()
        result = analyzer._parse_suggestions("[]")
        assert len(result) == 3  # Fallback count

    def test_parse_limits_to_max_suggestions(self):
        """Response with more than 5 suggestions should be capped."""
        analyzer = BlockerAnalyzer()
        suggestions = [
            {"approach": f"Approach {i}", "rationale": f"Reason {i}", "effort_level": "low"}
            for i in range(10)
        ]
        result = analyzer._parse_suggestions(json.dumps(suggestions))
        assert len(result) == 5  # MAX_SUGGESTIONS

    def test_parse_unknown_effort_level_defaults_to_medium(self):
        """Unknown effort level should default to medium."""
        analyzer = BlockerAnalyzer()
        response = json.dumps(
            [{"approach": "Test", "rationale": "Test", "effort_level": "extreme"}]
        )
        result = analyzer._parse_suggestions(response)
        assert result[0].effort_level == EffortLevel.MEDIUM

    def test_parse_truncates_long_approach(self):
        """Long approach text should be truncated to 500 chars."""
        analyzer = BlockerAnalyzer()
        long_approach = "x" * 600
        response = json.dumps(
            [{"approach": long_approach, "rationale": "Short", "effort_level": "low"}]
        )
        result = analyzer._parse_suggestions(response)
        assert len(result[0].approach) == 500

    def test_parse_truncates_long_rationale(self):
        """Long rationale text should be truncated to 500 chars."""
        analyzer = BlockerAnalyzer()
        long_rationale = "y" * 600
        response = json.dumps(
            [{"approach": "Short", "rationale": long_rationale, "effort_level": "low"}]
        )
        result = analyzer._parse_suggestions(response)
        assert len(result[0].rationale) == 500


class TestBlockerAnalyzerLLMCall:
    """Tests for suggest_unblock_paths with mocked LLM."""

    @pytest.mark.asyncio
    async def test_suggest_unblock_paths_success(self):
        """Successful LLM call should return parsed suggestions."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {"approach": "Try A", "rationale": "Reason A", "effort_level": "low"},
                {"approach": "Try B", "rationale": "Reason B", "effort_level": "medium"},
                {"approach": "Try C", "rationale": "Reason C", "effort_level": "high"},
            ]
        )

        with patch("backend.services.blocker_analyzer.PromptBroker") as mock_broker:
            broker_instance = mock_broker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            analyzer = BlockerAnalyzer()
            result = await analyzer.suggest_unblock_paths(
                title="Implement feature X",
                description="Build the new feature",
                blocking_reason="Waiting on API docs",
            )

            assert len(result) == 3
            assert result[0].approach == "Try A"
            broker_instance.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_suggest_unblock_paths_with_project_context(self):
        """Project name should be included in prompt."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {"approach": "Test", "rationale": "Test", "effort_level": "low"},
            ]
        )

        with patch("backend.services.blocker_analyzer.PromptBroker") as mock_broker:
            broker_instance = mock_broker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            analyzer = BlockerAnalyzer()
            await analyzer.suggest_unblock_paths(
                title="Task",
                project_name="Project Alpha",
            )

            # Verify the call was made with project context
            call_args = broker_instance.call.call_args
            request = call_args[0][0]
            assert "Project Alpha" in request.user_message

    @pytest.mark.asyncio
    async def test_suggest_unblock_paths_llm_failure_returns_fallback(self):
        """LLM failure should return fallback suggestions."""
        with patch("backend.services.blocker_analyzer.PromptBroker") as mock_broker:
            broker_instance = mock_broker.return_value
            broker_instance.call = AsyncMock(side_effect=Exception("API error"))

            analyzer = BlockerAnalyzer()
            result = await analyzer.suggest_unblock_paths(
                title="Blocked task",
                blocking_reason="Something went wrong",
            )

            # Should get fallback suggestions
            assert len(result) == 3
            assert all(isinstance(s, UnblockSuggestion) for s in result)

    @pytest.mark.asyncio
    async def test_suggest_unblock_paths_uses_haiku_model(self):
        """Should use Haiku model for cost efficiency."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {"approach": "Test", "rationale": "Test", "effort_level": "low"},
            ]
        )

        with patch("backend.services.blocker_analyzer.PromptBroker") as mock_broker:
            broker_instance = mock_broker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            analyzer = BlockerAnalyzer()
            await analyzer.suggest_unblock_paths(title="Task")

            call_args = broker_instance.call.call_args
            request = call_args[0][0]
            assert request.model == "haiku"


class TestGetBlockerAnalyzer:
    """Tests for singleton accessor."""

    def test_get_blocker_analyzer_returns_instance(self):
        """Should return a BlockerAnalyzer instance."""
        result = get_blocker_analyzer()
        assert isinstance(result, BlockerAnalyzer)

    def test_get_blocker_analyzer_singleton(self):
        """Should return the same instance on repeated calls."""
        result1 = get_blocker_analyzer()
        result2 = get_blocker_analyzer()
        assert result1 is result2
