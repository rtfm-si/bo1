"""Checkpoint logging wrapper for observability.

Wraps LangGraph checkpointers to log:
- put(): checkpoint size (bytes), latency_ms, session_id
- get(): latency_ms, found/not_found, session_id
- errors with full exception context
"""

import logging
import sys
import time
from typing import Any

from bo1.logging import ErrorCode, log_error

logger = logging.getLogger(__name__)


class LoggingCheckpointerWrapper:
    """Wraps a LangGraph checkpointer with operation logging.

    Logs checkpoint operations (put/get) with size, latency, and error details
    for observability without modifying underlying checkpointer behavior.

    Example:
        >>> from langgraph.checkpoint.redis.aio import AsyncRedisSaver
        >>> saver = AsyncRedisSaver(redis_url)
        >>> wrapped = LoggingCheckpointerWrapper(saver)
        >>> graph = create_graph(checkpointer=wrapped)
    """

    def __init__(self, checkpointer: Any) -> None:
        """Initialize wrapper with underlying checkpointer.

        Args:
            checkpointer: LangGraph checkpointer (AsyncRedisSaver, MemorySaver, etc.)
        """
        self._checkpointer = checkpointer

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to wrapped checkpointer."""
        return getattr(self._checkpointer, name)

    async def aput(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Async put with logging.

        Args:
            config: Checkpoint config with thread_id
            checkpoint: Checkpoint data to store
            metadata: Checkpoint metadata
            new_versions: Optional version info

        Returns:
            Result from underlying checkpointer
        """
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        start = time.perf_counter()

        try:
            # Estimate size (rough approximation)
            size_bytes = sys.getsizeof(str(checkpoint))

            result: dict[str, Any] = await self._checkpointer.aput(
                config, checkpoint, metadata, new_versions
            )

            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                f"[CHECKPOINT PUT] session={thread_id}, size_bytes={size_bytes}, "
                f"latency_ms={latency_ms:.2f}"
            )
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log_error(
                logger,
                ErrorCode.GRAPH_CHECKPOINT_ERROR,
                f"[CHECKPOINT PUT ERROR] session={thread_id}, latency_ms={latency_ms:.2f}, "
                f"error={type(e).__name__}: {e}",
                exc_info=True,
                session_id=thread_id,
            )
            raise

    async def aget(self, config: dict[str, Any]) -> dict[str, Any] | None:
        """Async get with logging.

        Args:
            config: Checkpoint config with thread_id

        Returns:
            Checkpoint data or None if not found
        """
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        start = time.perf_counter()

        try:
            result: dict[str, Any] | None = await self._checkpointer.aget(config)

            latency_ms = (time.perf_counter() - start) * 1000
            found = result is not None
            logger.info(
                f"[CHECKPOINT GET] session={thread_id}, found={found}, latency_ms={latency_ms:.2f}"
            )
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log_error(
                logger,
                ErrorCode.GRAPH_CHECKPOINT_ERROR,
                f"[CHECKPOINT GET ERROR] session={thread_id}, latency_ms={latency_ms:.2f}, "
                f"error={type(e).__name__}: {e}",
                exc_info=True,
                session_id=thread_id,
            )
            raise

    async def alist(self, config: dict[str, Any], **kwargs: Any) -> Any:
        """Async list with logging."""
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        start = time.perf_counter()

        try:
            result = await self._checkpointer.alist(config, **kwargs)

            latency_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"[CHECKPOINT LIST] session={thread_id}, latency_ms={latency_ms:.2f}")
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log_error(
                logger,
                ErrorCode.GRAPH_CHECKPOINT_ERROR,
                f"[CHECKPOINT LIST ERROR] session={thread_id}, latency_ms={latency_ms:.2f}, "
                f"error={type(e).__name__}: {e}",
                exc_info=True,
                session_id=thread_id,
            )
            raise

    # Sync versions for compatibility
    def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
        new_versions: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Sync put with logging."""
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        start = time.perf_counter()

        try:
            size_bytes = sys.getsizeof(str(checkpoint))
            result: dict[str, Any] = self._checkpointer.put(
                config, checkpoint, metadata, new_versions
            )

            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                f"[CHECKPOINT PUT] session={thread_id}, size_bytes={size_bytes}, "
                f"latency_ms={latency_ms:.2f}"
            )
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log_error(
                logger,
                ErrorCode.GRAPH_CHECKPOINT_ERROR,
                f"[CHECKPOINT PUT ERROR] session={thread_id}, latency_ms={latency_ms:.2f}, "
                f"error={type(e).__name__}: {e}",
                exc_info=True,
                session_id=thread_id,
            )
            raise

    def get(self, config: dict[str, Any]) -> dict[str, Any] | None:
        """Sync get with logging."""
        thread_id = config.get("configurable", {}).get("thread_id", "unknown")
        start = time.perf_counter()

        try:
            result: dict[str, Any] | None = self._checkpointer.get(config)

            latency_ms = (time.perf_counter() - start) * 1000
            found = result is not None
            logger.info(
                f"[CHECKPOINT GET] session={thread_id}, found={found}, latency_ms={latency_ms:.2f}"
            )
            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log_error(
                logger,
                ErrorCode.GRAPH_CHECKPOINT_ERROR,
                f"[CHECKPOINT GET ERROR] session={thread_id}, latency_ms={latency_ms:.2f}, "
                f"error={type(e).__name__}: {e}",
                exc_info=True,
                session_id=thread_id,
            )
            raise
