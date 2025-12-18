"""Internal service monitoring.

Tracks health of all external dependencies:
- LLM providers (via vendor_health)
- Redis
- PostgreSQL
- DO Spaces
- Resend (email)

Provides anomaly detection and preemptive alerting.
"""

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service status levels."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"


@dataclass
class ServiceHealth:
    """Health state for a service."""

    name: str
    status: ServiceStatus = ServiceStatus.OPERATIONAL
    error_rate: float = 0.0
    latency_p50: float | None = None
    latency_p95: float | None = None
    last_check: float | None = None
    last_error: str | None = None
    is_critical: bool = True  # Critical services affect overall status
    # Sliding window (5 min)
    recent_latencies: deque[float] = field(default_factory=lambda: deque(maxlen=500))
    recent_errors: deque[tuple[float, str]] = field(default_factory=lambda: deque(maxlen=100))
    recent_successes: deque[float] = field(default_factory=lambda: deque(maxlen=500))
    # Baseline for anomaly detection
    baseline_error_rate: float = 0.01  # 1% baseline
    baseline_latency_p95: float = 1000.0  # 1s baseline

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict."""
        return {
            "name": self.name,
            "status": self.status.value,
            "error_rate": round(self.error_rate, 4),
            "latency_p50_ms": round(self.latency_p50, 1) if self.latency_p50 else None,
            "latency_p95_ms": round(self.latency_p95, 1) if self.latency_p95 else None,
            "last_check": self.last_check,
            "last_error": self.last_error,
            "is_critical": self.is_critical,
        }


class ServiceMonitor:
    """Monitors all external service dependencies.

    Features:
    - Sliding window error tracking (5 min)
    - Latency percentile calculation
    - Anomaly detection (3x baseline = alert)
    - Preemptive alerting before vendor status pages
    """

    WINDOW_SECONDS = 300  # 5 minute window
    ANOMALY_MULTIPLIER = 3.0  # 3x baseline = anomaly

    # Services to monitor
    SERVICES = {
        "anthropic": {"critical": True, "baseline_error_rate": 0.02},
        "openai": {"critical": True, "baseline_error_rate": 0.02},
        "voyage": {"critical": False, "baseline_error_rate": 0.02},
        "brave": {"critical": False, "baseline_error_rate": 0.05},
        "postgres": {"critical": True, "baseline_error_rate": 0.001},
        "redis": {"critical": True, "baseline_error_rate": 0.001},
        "spaces": {"critical": False, "baseline_error_rate": 0.01},
        "resend": {"critical": False, "baseline_error_rate": 0.05},
    }

    def __init__(self) -> None:
        """Initialize monitor."""
        self._services: dict[str, ServiceHealth] = {}
        self._incidents: deque[dict[str, Any]] = deque(maxlen=100)  # Last 24h incidents
        self._alert_callback: Any = None

        # Initialize all services
        for name, config in self.SERVICES.items():
            self._services[name] = ServiceHealth(
                name=name,
                is_critical=config["critical"],
                baseline_error_rate=config["baseline_error_rate"],
            )

    def set_alert_callback(self, callback: Any) -> None:
        """Set callback for alerts.

        Args:
            callback: Async function(service_name, old_status, new_status, details)
        """
        self._alert_callback = callback

    def _get_service(self, name: str) -> ServiceHealth:
        """Get or create service health."""
        if name not in self._services:
            self._services[name] = ServiceHealth(name=name)
        return self._services[name]

    def _prune_window(self, service: ServiceHealth) -> None:
        """Remove records older than window."""
        cutoff = time.time() - self.WINDOW_SECONDS

        while service.recent_successes and service.recent_successes[0] < cutoff:
            service.recent_successes.popleft()
        while service.recent_errors and service.recent_errors[0][0] < cutoff:
            service.recent_errors.popleft()
        while service.recent_latencies and len(service.recent_latencies) > 0:
            # Latencies don't have timestamps, keep last N
            break

    def _calculate_percentile(self, values: list[float], percentile: float) -> float | None:
        """Calculate percentile from values."""
        if not values:
            return None
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        idx = min(idx, len(sorted_values) - 1)
        return sorted_values[idx]

    def _calculate_error_rate(self, service: ServiceHealth) -> float:
        """Calculate error rate in current window."""
        total = len(service.recent_successes) + len(service.recent_errors)
        if total == 0:
            return 0.0
        return len(service.recent_errors) / total

    def _update_status(self, service: ServiceHealth) -> ServiceStatus | None:
        """Update service status based on metrics.

        Returns:
            New status if changed, None otherwise.
        """
        self._prune_window(service)
        old_status = service.status

        # Calculate metrics
        service.error_rate = self._calculate_error_rate(service)
        latencies = list(service.recent_latencies)
        service.latency_p50 = self._calculate_percentile(latencies, 50)
        service.latency_p95 = self._calculate_percentile(latencies, 95)

        # Determine status
        is_anomaly = service.error_rate >= (service.baseline_error_rate * self.ANOMALY_MULTIPLIER)
        is_high_latency = service.latency_p95 is not None and service.latency_p95 >= (
            service.baseline_latency_p95 * self.ANOMALY_MULTIPLIER
        )

        if service.error_rate >= 0.50:
            new_status = ServiceStatus.OUTAGE
        elif service.error_rate >= 0.20 or is_anomaly or is_high_latency:
            new_status = ServiceStatus.DEGRADED
        else:
            new_status = ServiceStatus.OPERATIONAL

        service.status = new_status

        if old_status != new_status:
            logger.warning(
                f"Service {service.name} status change: {old_status.value} → {new_status.value} "
                f"(error_rate={service.error_rate:.1%}, p95={service.latency_p95}ms)"
            )
            # Record incident
            self._incidents.append(
                {
                    "service": service.name,
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "timestamp": time.time(),
                    "error_rate": service.error_rate,
                    "latency_p95": service.latency_p95,
                }
            )
            return new_status
        return None

    def record_success(self, service_name: str, latency_ms: float | None = None) -> None:
        """Record successful service call.

        Args:
            service_name: Service identifier
            latency_ms: Request latency in milliseconds
        """
        service = self._get_service(service_name)
        now = time.time()
        service.recent_successes.append(now)
        service.last_check = now
        if latency_ms is not None:
            service.recent_latencies.append(latency_ms)
        self._update_status(service)

    async def record_failure(
        self,
        service_name: str,
        error_message: str,
        latency_ms: float | None = None,
    ) -> ServiceStatus | None:
        """Record failed service call.

        Args:
            service_name: Service identifier
            error_message: Error description
            latency_ms: Request latency

        Returns:
            New status if changed (for alerting)
        """
        service = self._get_service(service_name)
        now = time.time()
        service.recent_errors.append((now, error_message[:200]))
        service.last_check = now
        service.last_error = error_message[:200]
        if latency_ms is not None:
            service.recent_latencies.append(latency_ms)

        new_status = self._update_status(service)

        # Fire alert callback if status changed
        if new_status and self._alert_callback:
            try:
                await self._alert_callback(
                    service_name,
                    service.status.value,
                    {
                        "error_rate": service.error_rate,
                        "latency_p95": service.latency_p95,
                        "last_error": service.last_error,
                    },
                )
            except Exception as e:
                logger.exception(f"Alert callback failed: {e}")

        return new_status

    def get_service_health(self, service_name: str) -> ServiceHealth:
        """Get current health for a service."""
        service = self._get_service(service_name)
        self._prune_window(service)
        self._update_status(service)
        return service

    def get_all_health(self) -> dict[str, ServiceHealth]:
        """Get health for all services."""
        return {name: self.get_service_health(name) for name in self._services}

    def get_overall_status(self) -> ServiceStatus:
        """Get overall system status.

        Based on critical services only.
        """
        all_health = self.get_all_health()
        critical = [h for h in all_health.values() if h.is_critical]

        if not critical:
            return ServiceStatus.OPERATIONAL

        if any(h.status == ServiceStatus.OUTAGE for h in critical):
            return ServiceStatus.OUTAGE
        if any(h.status == ServiceStatus.DEGRADED for h in critical):
            return ServiceStatus.DEGRADED
        return ServiceStatus.OPERATIONAL

    def get_status_message(self) -> str | None:
        """Get user-friendly status message if not operational."""
        status = self.get_overall_status()
        if status == ServiceStatus.OPERATIONAL:
            return None

        if status == ServiceStatus.OUTAGE:
            return "Some services are currently unavailable. We're working to restore them."
        return "Some features may be slow or unavailable. We're working on it."

    def get_recent_incidents(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get incidents from last N hours."""
        cutoff = time.time() - (hours * 3600)
        return [i for i in self._incidents if i["timestamp"] >= cutoff]

    async def check_redis(self) -> bool:
        """Health check Redis."""
        try:
            import redis.asyncio as aioredis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            client = aioredis.from_url(redis_url, socket_timeout=5)
            start = time.time()
            await client.ping()
            latency = (time.time() - start) * 1000
            await client.aclose()
            self.record_success("redis", latency)
            return True
        except Exception as e:
            await self.record_failure("redis", str(e))
            return False

    async def check_postgres(self) -> bool:
        """Health check PostgreSQL."""
        try:
            import psycopg2

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                await self.record_failure("postgres", "DATABASE_URL not set")
                return False

            start = time.time()
            conn = psycopg2.connect(database_url, connect_timeout=5)
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            latency = (time.time() - start) * 1000
            self.record_success("postgres", latency)
            return True
        except Exception as e:
            await self.record_failure("postgres", str(e))
            return False

    async def run_health_checks(self) -> dict[str, bool]:
        """Run health checks on all infrastructure services."""
        results = await asyncio.gather(
            self.check_redis(),
            self.check_postgres(),
            return_exceptions=True,
        )
        return {
            "redis": results[0] if not isinstance(results[0], Exception) else False,
            "postgres": results[1] if not isinstance(results[1], Exception) else False,
        }


# Global instance
_service_monitor: ServiceMonitor | None = None


def get_service_monitor() -> ServiceMonitor:
    """Get the global service monitor instance."""
    global _service_monitor
    if _service_monitor is None:
        _service_monitor = ServiceMonitor()
    return _service_monitor


def record_service_success(service: str, latency_ms: float | None = None) -> None:
    """Record successful service call."""
    get_service_monitor().record_success(service, latency_ms)


async def record_service_failure(
    service: str,
    error_message: str,
    latency_ms: float | None = None,
) -> ServiceStatus | None:
    """Record failed service call."""
    return await get_service_monitor().record_failure(service, error_message, latency_ms)


def get_system_status() -> dict[str, Any]:
    """Get overall system status for public API."""
    monitor = get_service_monitor()
    status = monitor.get_overall_status()
    message = monitor.get_status_message()
    all_health = monitor.get_all_health()

    return {
        "status": status.value,
        "message": message,
        "services": [h.to_dict() for h in all_health.values()],
    }


def get_detailed_status() -> dict[str, Any]:
    """Get detailed status for admin API."""
    monitor = get_service_monitor()
    all_health = monitor.get_all_health()
    incidents = monitor.get_recent_incidents(24)

    return {
        "status": monitor.get_overall_status().value,
        "message": monitor.get_status_message(),
        "services": {name: h.to_dict() for name, h in all_health.items()},
        "incidents_24h": incidents,
    }
