"""Unit tests for embedding batcher."""

import asyncio
from unittest.mock import patch

import pytest

from bo1.constants import EmbeddingsConfig
from bo1.llm.embedding_batcher import EmbeddingBatcher, get_default_batcher, shutdown_batcher


class TestEmbeddingBatcher:
    """Tests for EmbeddingBatcher class."""

    @pytest.fixture
    def mock_generate_batch(self):
        """Mock generate_embeddings_batch to return fake embeddings."""
        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock:
            # Return 1024-dim vectors for each text
            mock.side_effect = lambda texts, **kwargs: [[0.1] * 1024 for _ in texts]
            yield mock

    @pytest.mark.asyncio
    async def test_batch_flushes_at_size_threshold(self, mock_generate_batch):
        """Batch should flush when batch_size is reached."""
        batcher = EmbeddingBatcher(batch_size=3, timeout_seconds=60)

        # Add texts concurrently
        tasks = [asyncio.create_task(batcher.add(f"Text {i}")) for i in range(3)]

        # Wait for all to complete
        embeddings = await asyncio.gather(*tasks)

        # Should have called batch API once with all 3 texts
        assert mock_generate_batch.call_count == 1
        call_args = mock_generate_batch.call_args
        assert len(call_args[0][0]) == 3  # 3 texts in batch

        # All embeddings returned
        assert len(embeddings) == 3
        assert all(len(e) == 1024 for e in embeddings)

    @pytest.mark.asyncio
    async def test_batch_flushes_on_timeout(self, mock_generate_batch):
        """Batch should flush when timeout expires with partial batch."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=0.1)

        # Add only 2 texts (below batch_size)
        task1 = asyncio.create_task(batcher.add("Text 1"))
        task2 = asyncio.create_task(batcher.add("Text 2"))

        # Wait for timeout flush
        embeddings = await asyncio.gather(task1, task2)

        # Should have called batch API with 2 texts after timeout
        assert mock_generate_batch.call_count == 1
        call_args = mock_generate_batch.call_args
        assert len(call_args[0][0]) == 2

        assert len(embeddings) == 2

    @pytest.mark.asyncio
    async def test_error_propagates_to_all_futures(self):
        """API error should propagate to all waiting futures."""
        batcher = EmbeddingBatcher(batch_size=2, timeout_seconds=60)

        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock:
            mock.side_effect = Exception("API Error")

            task1 = asyncio.create_task(batcher.add("Text 1"))
            task2 = asyncio.create_task(batcher.add("Text 2"))

            # Both should raise the same exception
            with pytest.raises(Exception, match="API Error"):
                await task1

            with pytest.raises(Exception, match="API Error"):
                await task2

    @pytest.mark.asyncio
    async def test_flush_pending_on_shutdown(self):
        """flush_pending should force flush remaining items."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock_batch:
            mock_batch.return_value = [[0.1] * 1024]

            # Add one item (won't trigger size flush)
            task = asyncio.create_task(batcher.add("Single text"))

            # Allow task to be scheduled
            await asyncio.sleep(0.01)

            # Force flush
            await batcher.flush_pending()

            embedding = await task

            assert mock_batch.call_count == 1
            assert len(embedding) == 1024

    @pytest.mark.asyncio
    async def test_stats_tracking(self, mock_generate_batch):
        """Stats should track flush count and total texts."""
        batcher = EmbeddingBatcher(batch_size=2, timeout_seconds=60)

        # First batch
        await asyncio.gather(
            batcher.add("Text 1"),
            batcher.add("Text 2"),
        )

        # Second batch
        await asyncio.gather(
            batcher.add("Text 3"),
            batcher.add("Text 4"),
        )

        stats = batcher.stats
        assert stats["flush_count"] == 2
        assert stats["total_texts"] == 4
        assert stats["pending"] == 0
        assert stats["batch_size"] == 2

    @pytest.mark.asyncio
    async def test_empty_queue_flush_is_noop(self):
        """Flushing empty queue should not call API."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock_batch:
            await batcher.flush_pending()
            mock_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_adds_are_safe(self, mock_generate_batch):
        """Multiple concurrent adds should be handled safely."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # Fire many concurrent adds
        tasks = [asyncio.create_task(batcher.add(f"Text {i}")) for i in range(10)]

        embeddings = await asyncio.gather(*tasks)

        # All 10 should complete
        assert len(embeddings) == 10
        assert all(len(e) == 1024 for e in embeddings)

        # Should have called batch API twice (5 + 5)
        assert mock_generate_batch.call_count == 2

    def test_default_config_from_constants(self):
        """Batcher should use constants for default config."""
        batcher = EmbeddingBatcher()

        assert batcher.batch_size == EmbeddingsConfig.BATCH_SIZE
        assert batcher.timeout_seconds == EmbeddingsConfig.BATCH_TIMEOUT_SECONDS


class TestDefaultBatcher:
    """Tests for global batcher singleton."""

    @pytest.mark.asyncio
    async def test_get_default_batcher_returns_singleton(self):
        """get_default_batcher should return same instance."""
        # Reset singleton
        await shutdown_batcher()

        batcher1 = get_default_batcher()
        batcher2 = get_default_batcher()

        assert batcher1 is batcher2

        # Cleanup
        await shutdown_batcher()

    @pytest.mark.asyncio
    async def test_shutdown_flushes_and_clears(self):
        """shutdown_batcher should flush pending and clear singleton."""
        # Reset
        await shutdown_batcher()

        batcher = get_default_batcher()

        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock:
            mock.return_value = [[0.1] * 1024]

            # Add item but don't wait
            task = asyncio.create_task(batcher.add("Test"))
            await asyncio.sleep(0.01)

            # Shutdown should flush
            await shutdown_batcher()

            # Task should complete
            await task

            mock.assert_called_once()
