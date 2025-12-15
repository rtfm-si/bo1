"""Embedding batcher for batching multiple embedding requests into single API calls.

Groups embedding requests and flushes when:
- Batch size reaches threshold (default: 5)
- Timeout expires (default: 60s)

This reduces API calls and costs by batching multiple texts into single Voyage API call.
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from bo1.constants import EmbeddingsConfig

logger = logging.getLogger(__name__)


@dataclass
class PendingEmbedding:
    """A pending embedding request in the batch queue."""

    text: str
    future: asyncio.Future[list[float]]
    callback: Callable[[list[float]], Any] | None = None


@dataclass
class EmbeddingBatcher:
    """Batches embedding requests for efficient API usage.

    Accumulates embedding requests and flushes them as a single batch when either:
    - The batch reaches batch_size texts
    - The timeout expires (to avoid indefinite waiting)

    Deduplication: Identical texts within the same batch window share a single
    embedding result, reducing API costs when the same text is requested multiple times.

    Example:
        >>> batcher = EmbeddingBatcher(batch_size=5, timeout_seconds=60)
        >>> embedding = await batcher.add("Focus on user experience")
        >>> # Embedding returned after batch flushes (size or timeout)
    """

    batch_size: int = EmbeddingsConfig.BATCH_SIZE
    timeout_seconds: float = EmbeddingsConfig.BATCH_TIMEOUT_SECONDS
    model: str = "voyage-3"
    input_type: str | None = "document"

    _queue: list[PendingEmbedding] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _timeout_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _flush_count: int = field(default=0)
    _total_texts: int = field(default=0)
    _recent_requests: deque[float] = field(default_factory=deque)
    _traffic_window_seconds: float = EmbeddingsConfig.TRAFFIC_WINDOW_SECONDS
    _current_timeout: float = field(default=EmbeddingsConfig.BATCH_TIMEOUT_HIGH_TRAFFIC)
    # Deduplication tracking
    _pending_by_text: dict[int, PendingEmbedding] = field(default_factory=dict)
    _dedup_hits: int = field(default=0)
    _unique_texts: int = field(default=0)

    async def add(self, text: str) -> list[float]:
        """Add text to batch queue and return embedding when batch flushes.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector (1024 dimensions for voyage-3)

        Raises:
            Exception: If embedding generation fails
        """
        existing_future: asyncio.Future[list[float]] | None = None

        async with self._lock:
            # Track request timestamp for traffic measurement
            self._recent_requests.append(time.monotonic())

            # Check for duplicate text already pending
            text_hash = hash(text)
            if text_hash in self._pending_by_text:
                # Share the existing future - both requesters get same result
                existing = self._pending_by_text[text_hash]
                self._dedup_hits += 1
                logger.debug(f"Dedup hit: sharing future for text hash {text_hash}")
                existing_future = existing.future
            else:
                # New unique text
                loop = asyncio.get_running_loop()
                future: asyncio.Future[list[float]] = loop.create_future()
                pending = PendingEmbedding(text=text, future=future)
                self._queue.append(pending)
                self._pending_by_text[text_hash] = pending
                existing_future = future

                # Start timeout task if this is first item in new batch
                if len(self._queue) == 1:
                    self._start_timeout()

                # Flush if batch is full
                if len(self._queue) >= self.batch_size:
                    await self._flush("size")

        # Wait for result (outside lock)
        return await existing_future

    def _calculate_timeout(self) -> float:
        """Calculate adaptive timeout based on recent traffic.

        Returns:
            Timeout in seconds: 10s for low traffic, 60s for high traffic
        """
        now = time.monotonic()
        cutoff = now - self._traffic_window_seconds

        # Remove stale timestamps
        while self._recent_requests and self._recent_requests[0] < cutoff:
            self._recent_requests.popleft()

        # Calculate requests per second
        request_count = len(self._recent_requests)
        rps = (
            request_count / self._traffic_window_seconds if self._traffic_window_seconds > 0 else 0
        )

        # Select timeout based on traffic rate
        if rps < EmbeddingsConfig.TRAFFIC_THRESHOLD_RPS:
            timeout = EmbeddingsConfig.BATCH_TIMEOUT_LOW_TRAFFIC
        else:
            timeout = EmbeddingsConfig.BATCH_TIMEOUT_HIGH_TRAFFIC

        self._current_timeout = timeout
        logger.debug(f"Adaptive timeout: {timeout}s (rps={rps:.2f}, count={request_count})")
        return timeout

    def _start_timeout(self) -> None:
        """Start background timeout task for partial batch flush."""
        if self._timeout_task is not None:
            self._timeout_task.cancel()

        timeout = self._calculate_timeout()

        async def timeout_flush() -> None:
            await asyncio.sleep(timeout)
            async with self._lock:
                if self._queue:
                    await self._flush("timeout")

        self._timeout_task = asyncio.create_task(timeout_flush())

    async def _flush(self, reason: str) -> None:
        """Flush pending batch and distribute results.

        Args:
            reason: Why flush triggered ("size" or "timeout")
        """
        if not self._queue:
            return

        # Cancel timeout task
        if self._timeout_task is not None:
            self._timeout_task.cancel()
            self._timeout_task = None

        # Extract batch
        batch = self._queue[:]
        self._queue.clear()
        self._pending_by_text.clear()

        texts = [p.text for p in batch]
        self._flush_count += 1
        self._total_texts += len(texts)
        self._unique_texts += len(texts)

        logger.info(
            f"Embedding batch flush: {len(texts)} unique texts, reason={reason}, "
            f"total_flushes={self._flush_count}, dedup_hits={self._dedup_hits}"
        )

        try:
            from bo1.llm.embeddings import generate_embeddings_batch

            embeddings = generate_embeddings_batch(
                texts, model=self.model, input_type=self.input_type
            )

            # Distribute results to futures
            for pending, embedding in zip(batch, embeddings, strict=True):
                if not pending.future.done():
                    pending.future.set_result(embedding)
                if pending.callback:
                    try:
                        pending.callback(embedding)
                    except Exception as cb_err:
                        logger.warning(f"Embedding callback error: {cb_err}")

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Propagate error to all waiting futures
            for pending in batch:
                if not pending.future.done():
                    pending.future.set_exception(e)

    async def flush_pending(self) -> None:
        """Force flush any pending items. Call on shutdown."""
        async with self._lock:
            if self._queue:
                await self._flush("shutdown")

    @property
    def pending_count(self) -> int:
        """Number of texts waiting in queue."""
        return len(self._queue)

    @property
    def stats(self) -> dict[str, int | float]:
        """Batch statistics for monitoring."""
        # Calculate current traffic rate
        now = time.monotonic()
        cutoff = now - self._traffic_window_seconds
        recent_count = sum(1 for ts in self._recent_requests if ts >= cutoff)
        traffic_rps = (
            recent_count / self._traffic_window_seconds if self._traffic_window_seconds > 0 else 0
        )

        # Calculate dedup ratio (hits / total requests)
        total_requests = self._unique_texts + self._dedup_hits
        dedup_ratio = self._dedup_hits / total_requests if total_requests > 0 else 0.0

        return {
            "flush_count": self._flush_count,
            "total_texts": self._total_texts,
            "pending": len(self._queue),
            "batch_size": self.batch_size,
            "current_timeout": self._current_timeout,
            "traffic_rps": round(traffic_rps, 3),
            "dedup_hits": self._dedup_hits,
            "unique_texts": self._unique_texts,
            "dedup_ratio": round(dedup_ratio, 3),
        }


# Global default batcher instance
_default_batcher: EmbeddingBatcher | None = None


def get_default_batcher() -> EmbeddingBatcher:
    """Get or create the default global batcher instance."""
    global _default_batcher
    if _default_batcher is None:
        _default_batcher = EmbeddingBatcher()
    return _default_batcher


async def shutdown_batcher() -> None:
    """Flush and shutdown the default batcher. Call on app shutdown."""
    global _default_batcher
    if _default_batcher is not None:
        await _default_batcher.flush_pending()
        logger.info(f"Embedding batcher shutdown: {_default_batcher.stats}")
        _default_batcher = None
