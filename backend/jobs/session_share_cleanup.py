"""Background job for cleaning up expired session shares.

Runs daily (or on demand) to:
- Delete expired session_shares records
- Log results to Prometheus metrics
"""

from datetime import UTC, datetime

from bo1.state.database import db_session
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


def cleanup_expired_shares() -> dict[str, int]:
    """Clean up expired session shares.

    Deletes all session_shares records where expires_at < now.

    Returns:
        Dict with cleanup statistics: {deleted_count, error_count}
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Delete expired shares
                cur.execute(
                    """
                    DELETE FROM session_shares
                    WHERE expires_at < NOW()
                    """
                )
                deleted_count = cur.rowcount
                logger.info(f"Cleanup: deleted {deleted_count} expired shares")

                # Log to Prometheus (if available)
                try:
                    from backend.api.middleware.metrics import record_metric

                    record_metric(
                        "bo1_session_shares_cleanup_count",
                        deleted_count,
                        labels={"status": "deleted"},
                    )
                except Exception as e:
                    logger.debug(f"Failed to record cleanup metric: {e}")

                return {
                    "deleted_count": deleted_count,
                    "error_count": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

    except Exception as e:
        logger.error(f"Failed to clean up expired shares: {e}", exc_info=True)
        return {
            "deleted_count": 0,
            "error_count": 1,
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
        }


if __name__ == "__main__":
    # Run cleanup when invoked directly
    result = cleanup_expired_shares()
    logger.info(f"Cleanup result: {result}")
