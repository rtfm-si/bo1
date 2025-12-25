"""Tests for action unblock suggestions feature.

Tests cover:
1. Pydantic model validation for API responses
2. Blocker analyzer is tested in tests/services/test_blocker_analyzer.py
3. Rate limiting is tested in tests/security/test_rate_limiting.py

Note: Direct endpoint handler tests are skipped due to rate limiter complexity.
The endpoint logic is validated through:
- Unit tests for the blocker analyzer service
- Model validation tests below
- Manual integration testing
"""

import pytest

from backend.services.blocker_analyzer import EffortLevel, UnblockSuggestion


class TestUnblockSuggestionModel:
    """Test Pydantic models for API response."""

    def test_unblock_suggestion_model_validation(self):
        """UnblockSuggestionModel should validate effort_level pattern."""
        from backend.api.models import UnblockSuggestionModel

        # Valid effort levels
        model = UnblockSuggestionModel(
            approach="Test approach",
            rationale="Test rationale",
            effort_level="low",
        )
        assert model.effort_level == "low"

        model = UnblockSuggestionModel(
            approach="Test",
            rationale="Test",
            effort_level="medium",
        )
        assert model.effort_level == "medium"

        model = UnblockSuggestionModel(
            approach="Test",
            rationale="Test",
            effort_level="high",
        )
        assert model.effort_level == "high"

    def test_unblock_suggestion_model_rejects_invalid_effort(self):
        """Invalid effort_level should be rejected."""
        from pydantic import ValidationError

        from backend.api.models import UnblockSuggestionModel

        with pytest.raises(ValidationError):
            UnblockSuggestionModel(
                approach="Test",
                rationale="Test",
                effort_level="extreme",  # Invalid
            )

    def test_unblock_paths_response_validation(self):
        """UnblockPathsResponse should validate suggestions list."""
        from backend.api.models import UnblockPathsResponse, UnblockSuggestionModel

        response = UnblockPathsResponse(
            action_id="test-uuid-123",
            suggestions=[
                UnblockSuggestionModel(
                    approach="Approach 1",
                    rationale="Rationale 1",
                    effort_level="low",
                ),
                UnblockSuggestionModel(
                    approach="Approach 2",
                    rationale="Rationale 2",
                    effort_level="high",
                ),
            ],
        )

        assert response.action_id == "test-uuid-123"
        assert len(response.suggestions) == 2

    def test_unblock_paths_response_requires_at_least_one_suggestion(self):
        """Response should require at least one suggestion."""
        from pydantic import ValidationError

        from backend.api.models import UnblockPathsResponse

        with pytest.raises(ValidationError):
            UnblockPathsResponse(
                action_id="test-uuid",
                suggestions=[],  # Empty list should fail
            )

    def test_unblock_paths_response_limits_to_five_suggestions(self):
        """Response should accept max 5 suggestions."""
        from pydantic import ValidationError

        from backend.api.models import UnblockPathsResponse, UnblockSuggestionModel

        suggestions = [
            UnblockSuggestionModel(
                approach=f"Approach {i}",
                rationale=f"Rationale {i}",
                effort_level="low",
            )
            for i in range(6)
        ]

        with pytest.raises(ValidationError):
            UnblockPathsResponse(
                action_id="test-uuid",
                suggestions=suggestions,  # 6 items should fail
            )


class TestBlockerAnalyzerDataclassSerialization:
    """Test UnblockSuggestion dataclass serialization."""

    def test_unblock_suggestion_to_dict(self):
        """to_dict should serialize correctly."""
        suggestion = UnblockSuggestion(
            approach="Break into smaller tasks",
            rationale="Makes progress more achievable",
            effort_level=EffortLevel.LOW,
        )
        result = suggestion.to_dict()

        assert result == {
            "approach": "Break into smaller tasks",
            "rationale": "Makes progress more achievable",
            "effort_level": "low",
        }

    def test_effort_level_enum_values(self):
        """EffortLevel enum should have correct string values."""
        assert EffortLevel.LOW.value == "low"
        assert EffortLevel.MEDIUM.value == "medium"
        assert EffortLevel.HIGH.value == "high"
