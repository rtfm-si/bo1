"""Performance threshold configuration for early warning detection.

Defines default thresholds and provides database-backed runtime adjustment.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class ThresholdConfig:
    """Performance threshold configuration."""

    metric_name: str
    warn_value: float
    critical_value: float
    window_minutes: int = 5
    enabled: bool = True
    description: str = ""
    unit: str = ""  # e.g., "ms", "%", "count"


# Default threshold configurations
DEFAULT_THRESHOLDS: dict[str, ThresholdConfig] = {
    "api_response_time_ms": ThresholdConfig(
        metric_name="api_response_time_ms",
        warn_value=2000,  # 2 seconds
        critical_value=5000,  # 5 seconds
        description="API endpoint response time (p95)",
        unit="ms",
    ),
    "llm_response_time_ms": ThresholdConfig(
        metric_name="llm_response_time_ms",
        warn_value=30000,  # 30 seconds
        critical_value=60000,  # 60 seconds
        description="LLM API response time (p95)",
        unit="ms",
    ),
    "error_rate_percent": ThresholdConfig(
        metric_name="error_rate_percent",
        warn_value=5.0,  # 5%
        critical_value=10.0,  # 10%
        description="Error rate as percentage of requests",
        unit="%",
    ),
    "queue_depth": ThresholdConfig(
        metric_name="queue_depth",
        warn_value=100,
        critical_value=500,
        description="Number of items in processing queue",
        unit="count",
    ),
    "db_pool_usage_percent": ThresholdConfig(
        metric_name="db_pool_usage_percent",
        warn_value=80.0,  # 80%
        critical_value=95.0,  # 95%
        description="Database connection pool utilization",
        unit="%",
    ),
}


@dataclass
class PerformanceThreshold:
    """Database performance threshold record."""

    id: int
    metric_name: str
    warn_value: float
    critical_value: float
    window_minutes: int
    enabled: bool
    description: str | None
    unit: str | None
    created_at: datetime
    updated_at: datetime


class ThresholdService:
    """Service for managing performance thresholds.

    Provides database-backed storage with in-memory defaults.
    """

    def __init__(self) -> None:
        """Initialize threshold service."""
        self._cache: dict[str, PerformanceThreshold] = {}
        self._cache_loaded_at: float = 0
        self._cache_ttl_seconds: int = 60

    def get_threshold(self, metric_name: str) -> ThresholdConfig:
        """Get threshold config for a metric.

        Checks database first, falls back to defaults.

        Args:
            metric_name: Name of the metric

        Returns:
            ThresholdConfig for the metric
        """
        # Try database first
        db_threshold = self._get_from_db(metric_name)
        if db_threshold:
            return ThresholdConfig(
                metric_name=db_threshold.metric_name,
                warn_value=db_threshold.warn_value,
                critical_value=db_threshold.critical_value,
                window_minutes=db_threshold.window_minutes,
                enabled=db_threshold.enabled,
                description=db_threshold.description or "",
                unit=db_threshold.unit or "",
            )

        # Fall back to defaults
        if metric_name in DEFAULT_THRESHOLDS:
            return DEFAULT_THRESHOLDS[metric_name]

        # Return a generic threshold for unknown metrics
        return ThresholdConfig(
            metric_name=metric_name,
            warn_value=0,
            critical_value=0,
            enabled=False,
            description="Unknown metric (no threshold defined)",
        )

    def get_all_thresholds(self) -> list[ThresholdConfig]:
        """Get all configured thresholds.

        Returns:
            List of all threshold configs (db + defaults)
        """
        result: dict[str, ThresholdConfig] = {}

        # Start with defaults
        for name, config in DEFAULT_THRESHOLDS.items():
            result[name] = config

        # Overlay database values
        db_thresholds = self._get_all_from_db()
        for threshold in db_thresholds:
            result[threshold.metric_name] = ThresholdConfig(
                metric_name=threshold.metric_name,
                warn_value=threshold.warn_value,
                critical_value=threshold.critical_value,
                window_minutes=threshold.window_minutes,
                enabled=threshold.enabled,
                description=threshold.description or "",
                unit=threshold.unit or "",
            )

        return list(result.values())

    def update_threshold(
        self,
        metric_name: str,
        warn_value: float | None = None,
        critical_value: float | None = None,
        window_minutes: int | None = None,
        enabled: bool | None = None,
    ) -> ThresholdConfig | None:
        """Update or create a threshold in the database.

        Args:
            metric_name: Metric name
            warn_value: Warning threshold (optional)
            critical_value: Critical threshold (optional)
            window_minutes: Window size (optional)
            enabled: Whether threshold is enabled (optional)

        Returns:
            Updated ThresholdConfig or None on failure
        """
        try:
            with db_session() as session:
                # Check if exists
                result = session.execute(
                    """
                    SELECT id, metric_name, warn_value, critical_value, window_minutes,
                           enabled, description, unit, created_at, updated_at
                    FROM performance_thresholds
                    WHERE metric_name = :name
                    """,
                    {"name": metric_name},
                )
                row = result.fetchone()

                now = datetime.now(UTC)

                if row:
                    # Update existing
                    updates = []
                    params: dict[str, Any] = {"name": metric_name, "now": now}

                    if warn_value is not None:
                        updates.append("warn_value = :warn")
                        params["warn"] = warn_value
                    if critical_value is not None:
                        updates.append("critical_value = :critical")
                        params["critical"] = critical_value
                    if window_minutes is not None:
                        updates.append("window_minutes = :window")
                        params["window"] = window_minutes
                    if enabled is not None:
                        updates.append("enabled = :enabled")
                        params["enabled"] = enabled

                    if updates:
                        updates.append("updated_at = :now")
                        session.execute(
                            f"""
                            UPDATE performance_thresholds
                            SET {", ".join(updates)}
                            WHERE metric_name = :name
                            """,
                            params,
                        )
                        session.commit()
                else:
                    # Get defaults for missing values
                    defaults = DEFAULT_THRESHOLDS.get(
                        metric_name,
                        ThresholdConfig(metric_name=metric_name, warn_value=0, critical_value=0),
                    )

                    session.execute(
                        """
                        INSERT INTO performance_thresholds
                        (metric_name, warn_value, critical_value, window_minutes, enabled, description, unit, created_at, updated_at)
                        VALUES (:name, :warn, :critical, :window, :enabled, :desc, :unit, :now, :now)
                        """,
                        {
                            "name": metric_name,
                            "warn": warn_value if warn_value is not None else defaults.warn_value,
                            "critical": critical_value
                            if critical_value is not None
                            else defaults.critical_value,
                            "window": window_minutes
                            if window_minutes is not None
                            else defaults.window_minutes,
                            "enabled": enabled if enabled is not None else defaults.enabled,
                            "desc": defaults.description,
                            "unit": defaults.unit,
                            "now": now,
                        },
                    )
                    session.commit()

                # Clear cache
                self._cache_loaded_at = 0

                return self.get_threshold(metric_name)

        except Exception as e:
            logger.error(f"Failed to update threshold for {metric_name}: {e}")
            return None

    def _get_from_db(self, metric_name: str) -> PerformanceThreshold | None:
        """Get threshold from database."""
        try:
            with db_session() as session:
                result = session.execute(
                    """
                    SELECT id, metric_name, warn_value, critical_value, window_minutes,
                           enabled, description, unit, created_at, updated_at
                    FROM performance_thresholds
                    WHERE metric_name = :name AND enabled = true
                    """,
                    {"name": metric_name},
                )
                row = result.fetchone()
                if row:
                    return PerformanceThreshold(
                        id=row[0],
                        metric_name=row[1],
                        warn_value=row[2],
                        critical_value=row[3],
                        window_minutes=row[4],
                        enabled=row[5],
                        description=row[6],
                        unit=row[7],
                        created_at=row[8],
                        updated_at=row[9],
                    )
                return None
        except Exception as e:
            logger.warning(f"Failed to get threshold from DB for {metric_name}: {e}")
            return None

    def _get_all_from_db(self) -> list[PerformanceThreshold]:
        """Get all thresholds from database."""
        try:
            with db_session() as session:
                result = session.execute(
                    """
                    SELECT id, metric_name, warn_value, critical_value, window_minutes,
                           enabled, description, unit, created_at, updated_at
                    FROM performance_thresholds
                    """
                )
                thresholds = []
                for row in result.fetchall():
                    thresholds.append(
                        PerformanceThreshold(
                            id=row[0],
                            metric_name=row[1],
                            warn_value=row[2],
                            critical_value=row[3],
                            window_minutes=row[4],
                            enabled=row[5],
                            description=row[6],
                            unit=row[7],
                            created_at=row[8],
                            updated_at=row[9],
                        )
                    )
                return thresholds
        except Exception as e:
            logger.warning(f"Failed to get thresholds from DB: {e}")
            return []

    def check_threshold(self, metric_name: str, value: float) -> tuple[str, bool]:
        """Check if a value exceeds thresholds.

        Args:
            metric_name: Metric name
            value: Value to check

        Returns:
            Tuple of (severity, exceeded) where severity is "none", "warn", or "critical"
        """
        config = self.get_threshold(metric_name)

        if not config.enabled:
            return "none", False

        if value >= config.critical_value:
            return "critical", True
        elif value >= config.warn_value:
            return "warn", True
        else:
            return "none", False


# Module-level singleton
_service: ThresholdService | None = None


def get_threshold_service() -> ThresholdService:
    """Get threshold service singleton."""
    global _service
    if _service is None:
        _service = ThresholdService()
    return _service
