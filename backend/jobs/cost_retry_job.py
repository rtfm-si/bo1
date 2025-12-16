"""Cost retry job for processing failed API cost inserts.

Provides:
- process_retry_queue: Process queued cost records from Redis
- run_retry_job: CLI entry point for cron jobs

Polls cost_retry_queue every run and batch inserts to api_costs table.
"""

import json
import logging
from datetime import UTC, datetime

from dateutil.parser import parse as parse_datetime

from bo1.llm.cost_tracker import (
    COST_RETRY_ALERT_THRESHOLD,
    CostTracker,
)
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Job configuration
DEFAULT_BATCH_SIZE = 50
DEFAULT_POLL_INTERVAL_SECONDS = 30


def process_retry_queue(batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, int]:
    """Process queued cost records from Redis retry queue.

    Args:
        batch_size: Max records to process per batch

    Returns:
        Dict with processing statistics
    """
    stats = {
        "processed": 0,
        "failed": 0,
        "sessions_cleared": 0,
        "queue_depth_before": 0,
        "queue_depth_after": 0,
    }

    # Get queue depth before processing
    stats["queue_depth_before"] = CostTracker.get_retry_queue_depth()

    if stats["queue_depth_before"] == 0:
        logger.debug("Cost retry queue is empty, nothing to process")
        return stats

    logger.info(
        f"Processing cost retry queue (depth: {stats['queue_depth_before']}, "
        f"batch_size: {batch_size})"
    )

    # Pop batch from queue
    records = CostTracker.pop_retry_batch(batch_size)
    if not records:
        return stats

    # Group by session for efficient flag clearing
    sessions_with_costs: set[str] = set()

    # Batch insert to database
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                insert_data = []
                for record in records:
                    # Parse created_at from retry record, or use current time as fallback
                    created_at_str = record.get("created_at")
                    if created_at_str:
                        created_at = parse_datetime(created_at_str)
                    else:
                        created_at = datetime.now(UTC)

                    insert_data.append(
                        (
                            record.get("request_id"),
                            created_at,  # Include for conflict resolution
                            record.get("session_id"),
                            record.get("user_id"),
                            record.get("provider"),
                            record.get("model_name"),
                            record.get("operation_type"),
                            None,  # node_name
                            None,  # phase
                            None,  # persona_name
                            None,  # round_number
                            None,  # sub_problem_index
                            record.get("input_tokens", 0),
                            record.get("output_tokens", 0),
                            record.get("cache_creation_tokens", 0),
                            record.get("cache_read_tokens", 0),
                            record.get("cache_read_tokens", 0) > 0,  # cache_hit
                            0.0,  # input_cost (would need recalculation)
                            0.0,  # output_cost
                            0.0,  # cache_write_cost
                            0.0,  # cache_read_cost
                            record.get("total_cost", 0.0),
                            None,  # optimization_type
                            None,  # cost_without_optimization
                            None,  # latency_ms
                            "retry",  # status
                            record.get("error"),  # error_message
                            json.dumps({"retry_source": "cost_retry_job"}),  # metadata
                        )
                    )

                    # Track session for flag clearing
                    if record.get("session_id"):
                        sessions_with_costs.add(record["session_id"])

                # Use ON CONFLICT with composite key (request_id, created_at)
                # to handle idempotent retries on partitioned api_costs table
                cur.executemany(
                    """
                    INSERT INTO api_costs (
                        request_id, created_at, session_id, user_id,
                        provider, model_name, operation_type,
                        node_name, phase, persona_name, round_number, sub_problem_index,
                        input_tokens, output_tokens,
                        cache_creation_tokens, cache_read_tokens, cache_hit,
                        input_cost, output_cost, cache_write_cost, cache_read_cost, total_cost,
                        optimization_type, cost_without_optimization,
                        latency_ms, status, error_message,
                        metadata
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s
                    )
                    ON CONFLICT (request_id, created_at) DO NOTHING
                    """,
                    insert_data,
                )

        stats["processed"] = len(records)
        logger.info(f"Successfully inserted {stats['processed']} retry records")

        # Clear untracked costs flag for affected sessions
        for session_id in sessions_with_costs:
            # Only clear if no more pending costs for this session in queue
            remaining_in_queue = _check_session_in_queue(session_id)
            if not remaining_in_queue:
                if CostTracker.clear_session_untracked_flag(session_id):
                    stats["sessions_cleared"] += 1

    except Exception as e:
        logger.error(f"Failed to insert retry batch: {e}")
        stats["failed"] = len(records)
        # Re-queue failed records (they were already popped)
        for record in records:
            try:
                import redis

                from bo1.config import get_settings

                settings = get_settings()
                redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                redis_client.rpush("cost_retry_queue", json.dumps(record))
            except Exception:
                logger.debug("Failed to re-queue cost record, dropping")

    # Get queue depth after processing
    stats["queue_depth_after"] = CostTracker.get_retry_queue_depth()

    return stats


def _check_session_in_queue(session_id: str) -> bool:
    """Check if session has any remaining records in retry queue.

    Args:
        session_id: Session to check

    Returns:
        True if session has records in queue
    """
    try:
        import redis

        from bo1.config import get_settings

        settings = get_settings()
        redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

        # Scan queue (not efficient but queue should be small)
        all_items = redis_client.lrange("cost_retry_queue", 0, -1)
        for item in all_items:
            record = json.loads(item)
            if record.get("session_id") == session_id:
                return True
        return False
    except Exception:
        return False


def run_retry_job(batch_size: int | None = None) -> dict[str, int]:
    """Run the cost retry job.

    Args:
        batch_size: Override batch size (uses default if None)

    Returns:
        Dict with processing statistics
    """
    size = batch_size if batch_size is not None else DEFAULT_BATCH_SIZE
    logger.info(f"Starting cost retry job (batch_size: {size})")

    stats = process_retry_queue(size)
    stats["run_at"] = datetime.now(UTC).isoformat()

    # Alert if queue is still too deep after processing
    if stats["queue_depth_after"] > COST_RETRY_ALERT_THRESHOLD:
        logger.warning(
            f"Cost retry queue still deep after processing: {stats['queue_depth_after']}"
        )

    logger.info(f"Cost retry job complete: {stats}")
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run cost retry job")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Batch size (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Just show queue status without processing",
    )
    args = parser.parse_args()

    if args.status:
        depth = CostTracker.get_retry_queue_depth()
        print(f"Cost retry queue depth: {depth}")
    else:
        result = run_retry_job(args.batch_size)
        print(f"Retry job result: {result}")
