"""Background worker for retrying failed event persistence.

This worker runs in the background and periodically checks the failed events
queue, retrying persistence to PostgreSQL with exponential backoff.
"""

import asyncio
import logging

import redis

from backend.api.event_publisher import (
    check_dlq_alerts,
    get_dlq_depth,
    get_pending_retries,
    get_queue_depth,
    retry_event,
    update_retry_event,
)
from backend.api.metrics import prom_metrics
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Worker configuration
WORKER_INTERVAL_SECONDS = 30  # Check queue every 30 seconds
BATCH_SIZE = 100  # Process up to 100 events per cycle


class PersistenceWorker:
    """Background worker for retrying failed event persistence.

    Runs as a background task and periodically checks the failed events queue,
    attempting to persist each event to PostgreSQL. Uses exponential backoff
    for retries and moves permanently failed events to a dead letter queue.

    Examples:
        >>> from backend.api.persistence_worker import start_persistence_worker
        >>> worker_task = asyncio.create_task(start_persistence_worker())
    """

    def __init__(self, redis_client: redis.Redis) -> None:  # type: ignore[type-arg]
        """Initialize persistence worker.

        Args:
            redis_client: Redis client instance for queue operations
        """
        self.redis = redis_client
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background worker."""
        if self._running:
            logger.warning("Persistence worker is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🔄 Started persistence retry worker")

    async def stop(self) -> None:
        """Stop the background worker."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped persistence retry worker")

    async def _run_loop(self) -> None:
        """Main worker loop that checks queue and processes retries."""
        logger.info(f"Persistence worker starting (interval: {WORKER_INTERVAL_SECONDS}s)")

        while self._running:
            try:
                await self._process_retry_batch()
            except Exception as e:
                log_error(
                    logger,
                    ErrorCode.DB_WRITE_ERROR,
                    f"Error in persistence worker loop: {e}",
                    exc_info=True,
                )

            # Wait before next cycle
            await asyncio.sleep(WORKER_INTERVAL_SECONDS)

    async def _process_retry_batch(self) -> None:
        """Process a batch of events ready for retry."""
        try:
            # Get queue depths and update metrics
            retry_depth = await get_queue_depth(self.redis)
            dlq_depth = await get_dlq_depth(self.redis)

            # Update Prometheus metrics
            prom_metrics.update_queue_metrics(
                dlq_depth=max(0, dlq_depth),
                retry_queue_depth=max(0, retry_depth),
            )

            # Check DLQ alerts
            check_dlq_alerts(dlq_depth)

            # Get events ready for retry
            pending_events = await get_pending_retries(self.redis, limit=BATCH_SIZE)

            if not pending_events:
                # No events to process
                return

            logger.info(f"Processing {len(pending_events)} failed event(s) for retry")

            # Process each event
            success_count = 0
            failure_count = 0

            for event in pending_events:
                try:
                    # Attempt to retry persistence
                    success = await retry_event(self.redis, event)

                    # Update event status (remove if success, reschedule if failed)
                    await update_retry_event(self.redis, event, success)

                    if success:
                        success_count += 1
                    else:
                        failure_count += 1

                except Exception as e:
                    log_error(
                        logger,
                        ErrorCode.DB_WRITE_ERROR,
                        f"Failed to process retry for event {event.get('event_type')}: {e}",
                        session_id=event.get("session_id"),
                        event_type=event.get("event_type"),
                    )
                    failure_count += 1

            if success_count > 0 or failure_count > 0:
                logger.info(
                    f"Retry batch complete: {success_count} succeeded, {failure_count} failed"
                )

        except Exception as e:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Error processing retry batch: {e}",
                exc_info=True,
            )


# Global worker instance
_worker: PersistenceWorker | None = None


async def start_persistence_worker() -> PersistenceWorker:
    """Start the global persistence worker.

    Returns:
        The started worker instance

    Examples:
        >>> worker = await start_persistence_worker()
    """
    global _worker

    if _worker is not None:
        logger.warning("Persistence worker already started")
        return _worker

    # Initialize Redis client
    redis_manager = RedisManager()
    if not redis_manager.is_available:
        log_error(
            logger,
            ErrorCode.REDIS_READ_ERROR,
            "Redis is not available, cannot start persistence worker",
        )
        raise RuntimeError("Redis is not available")

    # Create and start worker
    _worker = PersistenceWorker(redis_manager.redis)  # type: ignore[arg-type]
    await _worker.start()

    return _worker


async def stop_persistence_worker() -> None:
    """Stop the global persistence worker.

    Examples:
        >>> await stop_persistence_worker()
    """
    global _worker

    if _worker is None:
        return

    await _worker.stop()
    _worker = None


def get_worker() -> PersistenceWorker | None:
    """Get the global worker instance.

    Returns:
        Worker instance if started, None otherwise
    """
    return _worker
