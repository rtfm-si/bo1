"""Unit tests for embedding batcher."""

import asyncio
import time
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


class TestAdaptiveTimeout:
    """Tests for adaptive timeout feature."""

    def test_low_traffic_uses_short_timeout(self):
        """Zero recent requests should use 10s timeout."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        timeout = batcher._calculate_timeout()

        assert timeout == EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC
        assert timeout == 10.0

    def test_high_traffic_uses_long_timeout(self):
        """High traffic (>=0.5 RPS) should use 60s timeout."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # Simulate 30 requests in 60s window = 0.5 RPS
        now = time.monotonic()
        for i in range(30):
            batcher._recent_requests.append(now - i)

        timeout = batcher._calculate_timeout()

        assert timeout == EmbeddingsConfig.BATCH_TIMEOUT_HIGH_TRAFFIC
        assert timeout == 60.0

    def test_boundary_at_threshold(self):
        """Exactly at threshold (0.5 RPS) should use high traffic timeout."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # Exactly 30 requests in 60s = 0.5 RPS (at threshold)
        now = time.monotonic()
        for i in range(30):
            batcher._recent_requests.append(now - i)

        timeout = batcher._calculate_timeout()

        # At threshold, should use high-traffic timeout
        assert timeout == EmbeddingsConfig.BATCH_TIMEOUT_HIGH_TRAFFIC

    def test_below_threshold_uses_low_timeout(self):
        """Just below threshold should use low traffic timeout."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # 29 requests in 60s = 0.483 RPS (below 0.5 threshold)
        now = time.monotonic()
        for i in range(29):
            batcher._recent_requests.append(now - i)

        timeout = batcher._calculate_timeout()

        assert timeout == EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC

    def test_timeout_changes_with_traffic_pattern(self):
        """Timeout should change as traffic pattern shifts."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # Start with no traffic - low timeout
        timeout1 = batcher._calculate_timeout()
        assert timeout1 == EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC

        # Add high traffic
        now = time.monotonic()
        for i in range(50):
            batcher._recent_requests.append(now - i * 0.5)

        timeout2 = batcher._calculate_timeout()
        assert timeout2 == EmbeddingsConfig.BATCH_TIMEOUT_HIGH_TRAFFIC

    def test_window_sliding_removes_old_requests(self):
        """Old requests outside window should be removed."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        now = time.monotonic()

        # Add old requests (outside 60s window)
        for i in range(50):
            batcher._recent_requests.append(now - 100 - i)

        # Should have 50 stale requests
        assert len(batcher._recent_requests) == 50

        # Calculate timeout - should clean up stale and return low-traffic
        timeout = batcher._calculate_timeout()

        assert timeout == EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC
        assert len(batcher._recent_requests) == 0  # All cleaned up

    def test_stats_includes_adaptive_fields(self):
        """Stats should include current_timeout and traffic_rps."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # Prime the timeout calculation
        batcher._calculate_timeout()

        stats = batcher.stats

        assert "current_timeout" in stats
        assert "traffic_rps" in stats
        assert stats["current_timeout"] == EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC
        assert stats["traffic_rps"] == 0.0

    @pytest.mark.asyncio
    async def test_adaptive_timeout_used_in_flush(
        self,
    ):
        """Timeout task should use adaptive timeout."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock:
            mock.return_value = [[0.1] * 1024]

            # Low traffic - should use 10s timeout
            # We can't easily test the actual timing, but we verify
            # the current_timeout is set correctly
            task = asyncio.create_task(batcher.add("Test text"))

            # Allow task to start
            await asyncio.sleep(0.01)

            # Should have set low-traffic timeout
            assert batcher._current_timeout == EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC

            # Force flush to complete test
            await batcher.flush_pending()
            await task


class TestDeduplication:
    """Tests for embedding request deduplication."""

    @pytest.fixture
    def mock_generate_batch(self):
        """Mock generate_embeddings_batch to return fake embeddings."""
        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock:
            # Return unique 1024-dim vectors for each text (based on index)
            mock.side_effect = lambda texts, **kwargs: [
                [float(i) / 1000] * 1024 for i in range(len(texts))
            ]
            yield mock

    @pytest.mark.asyncio
    async def test_duplicate_texts_call_api_once(self, mock_generate_batch):
        """Duplicate texts in batch should only call API once per unique text."""
        batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)

        # Add same text 3 times
        tasks = [
            asyncio.create_task(batcher.add("Same text")),
            asyncio.create_task(batcher.add("Same text")),
            asyncio.create_task(batcher.add("Same text")),
        ]

        # Force flush
        await asyncio.sleep(0.01)
        await batcher.flush_pending()

        embeddings = await asyncio.gather(*tasks)

        # Should call API only once with 1 unique text
        assert mock_generate_batch.call_count == 1
        call_args = mock_generate_batch.call_args
        assert len(call_args[0][0]) == 1  # Only 1 unique text sent to API

        # All 3 requesters get same embedding
        assert len(embeddings) == 3
        assert embeddings[0] == embeddings[1] == embeddings[2]

    @pytest.mark.asyncio
    async def test_all_duplicate_requesters_receive_same_embedding(self, mock_generate_batch):
        """All requesters of same text should receive identical embedding."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        # Add duplicates
        task1 = asyncio.create_task(batcher.add("Duplicate"))
        task2 = asyncio.create_task(batcher.add("Duplicate"))
        task3 = asyncio.create_task(batcher.add("Unique text"))
        task4 = asyncio.create_task(batcher.add("Duplicate"))

        await asyncio.sleep(0.01)
        await batcher.flush_pending()

        results = await asyncio.gather(task1, task2, task3, task4)

        # Duplicates get same embedding
        assert results[0] == results[1] == results[3]
        # Unique text gets different embedding
        assert results[2] != results[0]

    @pytest.mark.asyncio
    async def test_dedup_hits_counter_increments(self, mock_generate_batch):
        """dedup_hits counter should increment for each duplicate request."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        # Add 3 duplicates + 2 unique = 2 dedup hits
        tasks = [
            asyncio.create_task(batcher.add("Dup")),
            asyncio.create_task(batcher.add("Dup")),  # hit 1
            asyncio.create_task(batcher.add("Dup")),  # hit 2
            asyncio.create_task(batcher.add("Unique1")),
            asyncio.create_task(batcher.add("Unique2")),
        ]

        await asyncio.sleep(0.01)
        await batcher.flush_pending()
        await asyncio.gather(*tasks)

        stats = batcher.stats
        assert stats["dedup_hits"] == 2
        assert stats["unique_texts"] == 3

    @pytest.mark.asyncio
    async def test_dedup_ratio_calculation(self, mock_generate_batch):
        """dedup_ratio should be hits / total requests."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        # 4 requests: 2 unique, 2 duplicates = 50% dedup ratio
        tasks = [
            asyncio.create_task(batcher.add("A")),
            asyncio.create_task(batcher.add("A")),  # dup
            asyncio.create_task(batcher.add("B")),
            asyncio.create_task(batcher.add("B")),  # dup
        ]

        await asyncio.sleep(0.01)
        await batcher.flush_pending()
        await asyncio.gather(*tasks)

        stats = batcher.stats
        # 2 hits / (2 unique + 2 hits) = 0.5
        assert stats["dedup_ratio"] == 0.5

    @pytest.mark.asyncio
    async def test_concurrent_identical_requests_share_future(self, mock_generate_batch):
        """Concurrent identical requests should all resolve with same result."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        # Fire many concurrent identical requests
        tasks = [asyncio.create_task(batcher.add("Concurrent text")) for _ in range(10)]

        await asyncio.sleep(0.01)
        await batcher.flush_pending()

        embeddings = await asyncio.gather(*tasks)

        # All should get same embedding
        assert all(e == embeddings[0] for e in embeddings)
        # Only 1 API call
        assert mock_generate_batch.call_count == 1

    @pytest.mark.asyncio
    async def test_error_propagates_to_duplicate_requesters(self):
        """API error should propagate to all requesters including duplicates."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        with patch("bo1.llm.embeddings.generate_embeddings_batch") as mock:
            mock.side_effect = Exception("API Error")

            task1 = asyncio.create_task(batcher.add("Text"))
            task2 = asyncio.create_task(batcher.add("Text"))  # dup
            task3 = asyncio.create_task(batcher.add("Other"))

            await asyncio.sleep(0.01)
            await batcher.flush_pending()

            # All should get the error
            with pytest.raises(Exception, match="API Error"):
                await task1
            with pytest.raises(Exception, match="API Error"):
                await task2
            with pytest.raises(Exception, match="API Error"):
                await task3

    @pytest.mark.asyncio
    async def test_mixed_unique_and_duplicate_batch(self, mock_generate_batch):
        """Batch with mix of unique and duplicate texts works correctly."""
        batcher = EmbeddingBatcher(batch_size=10, timeout_seconds=60)

        tasks = [
            asyncio.create_task(batcher.add("A")),
            asyncio.create_task(batcher.add("B")),
            asyncio.create_task(batcher.add("A")),  # dup
            asyncio.create_task(batcher.add("C")),
            asyncio.create_task(batcher.add("B")),  # dup
            asyncio.create_task(batcher.add("D")),
        ]

        await asyncio.sleep(0.01)
        await batcher.flush_pending()

        embeddings = await asyncio.gather(*tasks)

        # API called with only unique texts
        call_args = mock_generate_batch.call_args
        assert len(call_args[0][0]) == 4  # A, B, C, D

        # Verify duplicates match originals
        assert embeddings[0] == embeddings[2]  # A
        assert embeddings[1] == embeddings[4]  # B


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
