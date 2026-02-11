"""Tests for apply_metric_suggestion endpoint timestamp and history tracking.

Verifies:
- Applying a metric suggestion saves benchmark timestamp
- Applying a metric suggestion appends to benchmark history
- Source metadata is recorded in history entry
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


class TestApplyMetricSuggestionTimestamps:
    """Tests for apply_metric_suggestion timestamp recording."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        repo = MagicMock()
        return repo

    @pytest.mark.asyncio
    async def test_saves_timestamp_when_applying_suggestion(self, mock_user_repository):
        """Applying a metric suggestion records benchmark timestamp."""
        from backend.api.context.models import ApplyMetricSuggestionRequest
        from backend.api.context.routes import apply_metric_suggestion

        # Initial context with no revenue
        mock_user_repository.get_context.return_value = {"business_model": "SaaS"}

        request = ApplyMetricSuggestionRequest(
            field="revenue",
            value="50000",
            source_question="What's your MRR?",
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.metrics_routes.user_repository", mock_user_repository):
            await apply_metric_suggestion(request, user=mock_user)

        # Check save was called
        assert mock_user_repository.save_context.called
        saved_context = mock_user_repository.save_context.call_args[0][1]

        # Should have timestamp for revenue
        assert "benchmark_timestamps" in saved_context
        assert "revenue" in saved_context["benchmark_timestamps"]

        # Timestamp should be recent
        ts_str = saved_context["benchmark_timestamps"]["revenue"]
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        assert ts.date() == datetime.now(UTC).date()

    @pytest.mark.asyncio
    async def test_saves_timestamp_when_updating_existing_value(self, mock_user_repository):
        """Updating an existing metric records new timestamp."""
        from backend.api.context.models import ApplyMetricSuggestionRequest
        from backend.api.context.routes import apply_metric_suggestion

        old_timestamp = "2025-01-01T12:00:00+00:00"
        mock_user_repository.get_context.return_value = {
            "revenue": "30000",
            "benchmark_timestamps": {"revenue": old_timestamp},
        }

        request = ApplyMetricSuggestionRequest(
            field="revenue",
            value="50000",  # Updated value
            source_question="What's your MRR?",
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.metrics_routes.user_repository", mock_user_repository):
            await apply_metric_suggestion(request, user=mock_user)

        saved_context = mock_user_repository.save_context.call_args[0][1]

        # Timestamp should be updated (not the old one)
        assert saved_context["benchmark_timestamps"]["revenue"] != old_timestamp


class TestApplyMetricSuggestionHistory:
    """Tests for apply_metric_suggestion history appending."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        repo = MagicMock()
        return repo

    @pytest.mark.asyncio
    async def test_appends_history_when_applying_suggestion(self, mock_user_repository):
        """Applying a metric suggestion appends to benchmark history."""
        from backend.api.context.models import ApplyMetricSuggestionRequest
        from backend.api.context.routes import apply_metric_suggestion

        mock_user_repository.get_context.return_value = {"business_model": "SaaS"}

        request = ApplyMetricSuggestionRequest(
            field="revenue",
            value="50000",
            source_question="What's your MRR?",
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.metrics_routes.user_repository", mock_user_repository):
            await apply_metric_suggestion(request, user=mock_user)

        saved_context = mock_user_repository.save_context.call_args[0][1]

        # Should have history for revenue
        assert "benchmark_history" in saved_context
        assert "revenue" in saved_context["benchmark_history"]
        assert len(saved_context["benchmark_history"]["revenue"]) == 1

        entry = saved_context["benchmark_history"]["revenue"][0]
        assert entry["value"] == "50000"
        assert entry["date"] == datetime.now(UTC).strftime("%Y-%m-%d")

    @pytest.mark.asyncio
    async def test_appends_to_existing_history(self, mock_user_repository):
        """Applying a suggestion appends to existing history entries."""
        from backend.api.context.models import ApplyMetricSuggestionRequest
        from backend.api.context.routes import apply_metric_suggestion

        existing_history = {
            "revenue": [{"value": "30000", "date": "2025-01-01"}],
        }
        mock_user_repository.get_context.return_value = {
            "revenue": "30000",
            "benchmark_history": existing_history,
            "benchmark_timestamps": {"revenue": "2025-01-01T12:00:00+00:00"},
        }

        request = ApplyMetricSuggestionRequest(
            field="revenue",
            value="50000",  # New value
            source_question="Updated MRR?",
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.metrics_routes.user_repository", mock_user_repository):
            await apply_metric_suggestion(request, user=mock_user)

        saved_context = mock_user_repository.save_context.call_args[0][1]

        # Should have 2 entries now
        assert len(saved_context["benchmark_history"]["revenue"]) == 2
        # Newest entry is first
        assert saved_context["benchmark_history"]["revenue"][0]["value"] == "50000"
        # Old entry is second
        assert saved_context["benchmark_history"]["revenue"][1]["value"] == "30000"

    @pytest.mark.asyncio
    async def test_history_includes_source_metadata(self, mock_user_repository):
        """History entry includes source and source_question metadata."""
        from backend.api.context.models import ApplyMetricSuggestionRequest
        from backend.api.context.routes import apply_metric_suggestion

        mock_user_repository.get_context.return_value = {}

        request = ApplyMetricSuggestionRequest(
            field="revenue",
            value="50000",
            source_question="What's your monthly recurring revenue?",
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.metrics_routes.user_repository", mock_user_repository):
            await apply_metric_suggestion(request, user=mock_user)

        saved_context = mock_user_repository.save_context.call_args[0][1]

        entry = saved_context["benchmark_history"]["revenue"][0]
        assert entry["source"] == "insight_suggestion"
        assert entry["source_question"] == "What's your monthly recurring revenue?"

    @pytest.mark.asyncio
    async def test_source_question_truncated_to_200_chars(self, mock_user_repository):
        """Long source questions are truncated to 200 characters."""
        from backend.api.context.models import ApplyMetricSuggestionRequest
        from backend.api.context.routes import apply_metric_suggestion

        mock_user_repository.get_context.return_value = {}

        long_question = "A" * 300  # 300 characters

        request = ApplyMetricSuggestionRequest(
            field="revenue",
            value="50000",
            source_question=long_question,
        )

        mock_user = {"user_id": "user-123"}

        with patch("backend.api.context.metrics_routes.user_repository", mock_user_repository):
            await apply_metric_suggestion(request, user=mock_user)

        saved_context = mock_user_repository.save_context.call_args[0][1]

        entry = saved_context["benchmark_history"]["revenue"][0]
        assert len(entry["source_question"]) == 200
