"""Tests for contribution summarization metrics and concurrency control."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestSummarizationConcurrencyLimit:
    """Test concurrency limit enforcement via semaphore."""

    @pytest.mark.asyncio
    async def test_concurrency_limit_enforced(self) -> None:
        """Verify semaphore limits concurrent summarization calls."""
        from backend.api.contribution_summarizer import (
            SUMMARIZATION_CONCURRENCY_LIMIT,
            ContributionSummarizer,
        )

        # Track concurrent calls
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_summarize(content: str, persona_name: str) -> dict:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            # Simulate LLM latency
            await asyncio.sleep(0.05)

            async with lock:
                current_concurrent -= 1

            return {"concise": "test"}

        summarizer = ContributionSummarizer(client=AsyncMock())

        with patch.object(summarizer, "summarize", side_effect=mock_summarize):
            # Create more items than concurrency limit
            items = [(f"content {i}", f"persona_{i}") for i in range(10)]
            await summarizer.batch_summarize(items)

        # Max concurrent should not exceed the limit
        assert max_concurrent <= SUMMARIZATION_CONCURRENCY_LIMIT
        # Should have processed all items
        assert current_concurrent == 0


class TestSummarizationMetrics:
    """Test Prometheus metrics for summarization."""

    def test_summarization_duration_metric_exists(self) -> None:
        """Verify summarization duration histogram is registered."""
        from backend.api.metrics import prom_metrics

        assert hasattr(prom_metrics, "summarization_duration")
        # Check it has expected labels
        assert prom_metrics.summarization_duration._labelnames == ("persona_name", "status")

    def test_summarization_batch_metrics_exist(self) -> None:
        """Verify batch metrics are registered."""
        from backend.api.metrics import prom_metrics

        assert hasattr(prom_metrics, "summarization_batch_size")
        assert hasattr(prom_metrics, "summarization_batch_duration")

    def test_record_summarization_duration(self) -> None:
        """Test recording summarization duration metric."""
        from backend.api.metrics import prom_metrics

        # Should not raise
        prom_metrics.record_summarization_duration("test_persona", "success", 1234.5)
        prom_metrics.record_summarization_duration("test_persona", "fallback", 500.0)
        prom_metrics.record_summarization_duration("test_persona", "error", 100.0)

    def test_record_summarization_batch(self) -> None:
        """Test recording batch metrics."""
        from backend.api.metrics import prom_metrics

        # Should not raise
        prom_metrics.record_summarization_batch(batch_size=5, duration_ms=3000.0)


class TestSummarizationInstrumentation:
    """Test that ContributionSummarizer emits metrics."""

    @pytest.mark.asyncio
    async def test_summarization_emits_duration_metric(self) -> None:
        """Verify summarize() records duration metric."""
        from unittest.mock import MagicMock

        from backend.api.contribution_summarizer import ContributionSummarizer

        # Mock the LLM call
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"concise":"test summary"}')]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        summarizer = ContributionSummarizer(client=mock_client)

        with patch("backend.api.metrics.prom_metrics") as mock_prom:
            # Call the method
            await summarizer.summarize("test content", "Test Expert")

            # Verify metric was recorded
            mock_prom.record_summarization_duration.assert_called_once()
            call_args = mock_prom.record_summarization_duration.call_args
            assert call_args[0][0] == "Test Expert"  # persona_name
            assert call_args[0][1] == "success"  # status
            assert call_args[0][2] > 0  # duration_ms

    @pytest.mark.asyncio
    async def test_batch_emits_batch_metrics(self) -> None:
        """Verify batch_summarize() records batch metrics."""
        from backend.api.contribution_summarizer import ContributionSummarizer

        summarizer = ContributionSummarizer(client=AsyncMock())

        async def mock_summarize(content: str, persona_name: str) -> dict:
            return {"concise": "test"}

        with (
            patch.object(summarizer, "summarize", side_effect=mock_summarize),
            patch("backend.api.metrics.prom_metrics") as mock_prom,
        ):
            items = [("content1", "persona1"), ("content2", "persona2")]
            await summarizer.batch_summarize(items)

            # Verify batch metric was recorded
            mock_prom.record_summarization_batch.assert_called_once()
            call_args = mock_prom.record_summarization_batch.call_args
            assert call_args[0][0] == 2  # batch_size
            assert call_args[0][1] > 0  # duration_ms
