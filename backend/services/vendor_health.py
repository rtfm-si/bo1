"""Vendor health tracking service.

Monitors LLM provider health via error pattern analysis.
Detects outages proactively before vendor status pages update.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Vendor health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ErrorRecord:
    """Record of a single error."""

    timestamp: float
    error_type: str
    message: str


@dataclass
class ProviderHealth:
    """Health state for a single provider."""

    provider: str
    status: HealthStatus = HealthStatus.HEALTHY
    error_rate: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    last_success: float | None = None
    last_failure: float | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None
    # Sliding window of recent errors (last 60s)
    recent_errors: deque[ErrorRecord] = field(default_factory=lambda: deque(maxlen=100))
    # Sliding window of recent requests (last 60s)
    recent_requests: deque[float] = field(default_factory=lambda: deque(maxlen=1000))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "provider": self.provider,
            "status": self.status.value,
            "error_rate": round(self.error_rate, 2),
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "last_error_type": self.last_error_type,
            "last_error_message": self.last_error_message,
        }


class VendorHealthTracker:
    """Tracks health of LLM providers.

    Uses sliding window error tracking to detect degradation:
    - >50% error rate in 60s window → unhealthy
    - 20-50% error rate → degraded
    - <20% error rate → healthy
    - Recovery: <10% error rate for 60s → healthy
    """

    # Error rate thresholds
    UNHEALTHY_THRESHOLD = 0.50  # >50% failures
    DEGRADED_THRESHOLD = 0.20  # >20% failures
    RECOVERY_THRESHOLD = 0.10  # <10% to recover
    WINDOW_SECONDS = 60  # Sliding window size

    def __init__(self) -> None:
        """Initialize tracker."""
        self._providers: dict[str, ProviderHealth] = {}
        self._state_change_callbacks: list = []

    def _get_or_create(self, provider: str) -> ProviderHealth:
        """Get or create health state for provider."""
        if provider not in self._providers:
            self._providers[provider] = ProviderHealth(provider=provider)
        return self._providers[provider]

    def _prune_old_records(self, health: ProviderHealth) -> None:
        """Remove records older than window."""
        cutoff = time.time() - self.WINDOW_SECONDS

        # Prune old requests
        while health.recent_requests and health.recent_requests[0] < cutoff:
            health.recent_requests.popleft()

        # Prune old errors
        while health.recent_errors and health.recent_errors[0].timestamp < cutoff:
            health.recent_errors.popleft()

    def _calculate_error_rate(self, health: ProviderHealth) -> float:
        """Calculate error rate in current window."""
        self._prune_old_records(health)
        total = len(health.recent_requests)
        if total == 0:
            return 0.0
        errors = len(health.recent_errors)
        return errors / total

    def _update_status(self, health: ProviderHealth) -> HealthStatus | None:
        """Update provider status based on error rate.

        Returns:
            New status if changed, None otherwise.
        """
        old_status = health.status
        error_rate = self._calculate_error_rate(health)
        health.error_rate = error_rate

        # Determine new status
        if error_rate >= self.UNHEALTHY_THRESHOLD:
            new_status = HealthStatus.UNHEALTHY
        elif error_rate >= self.DEGRADED_THRESHOLD:
            new_status = HealthStatus.DEGRADED
        elif health.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY):
            # Recovery requires lower threshold (hysteresis)
            if error_rate <= self.RECOVERY_THRESHOLD:
                new_status = HealthStatus.HEALTHY
            else:
                new_status = health.status  # Stay in current state
        else:
            new_status = HealthStatus.HEALTHY

        health.status = new_status

        if old_status != new_status:
            logger.warning(
                f"Provider {health.provider} status change: {old_status.value} → {new_status.value} "
                f"(error_rate={error_rate:.1%})"
            )
            return new_status
        return None

    def record_success(self, provider: str) -> None:
        """Record a successful request.

        Args:
            provider: Provider name (e.g., "anthropic", "openai")
        """
        health = self._get_or_create(provider)
        now = time.time()

        health.total_requests += 1
        health.recent_requests.append(now)
        health.last_success = now

        self._update_status(health)

    def record_failure(
        self,
        provider: str,
        error_type: str,
        error_message: str,
    ) -> HealthStatus | None:
        """Record a failed request.

        Args:
            provider: Provider name
            error_type: Exception type name
            error_message: Error message (truncated)

        Returns:
            New status if status changed, None otherwise
        """
        health = self._get_or_create(provider)
        now = time.time()

        health.total_requests += 1
        health.failed_requests += 1
        health.recent_requests.append(now)
        health.recent_errors.append(
            ErrorRecord(
                timestamp=now,
                error_type=error_type,
                message=error_message[:200],
            )
        )
        health.last_failure = now
        health.last_error_type = error_type
        health.last_error_message = error_message[:200]

        return self._update_status(health)

    def get_provider_health(self, provider: str) -> ProviderHealth:
        """Get current health for a provider.

        Args:
            provider: Provider name

        Returns:
            ProviderHealth with current status
        """
        health = self._get_or_create(provider)
        self._prune_old_records(health)
        self._update_status(health)
        return health

    def get_all_health(self) -> dict[str, ProviderHealth]:
        """Get health for all tracked providers.

        Returns:
            Dict of provider name to ProviderHealth
        """
        result = {}
        for provider in self._providers:
            result[provider] = self.get_provider_health(provider)
        return result

    def get_overall_status(self) -> HealthStatus:
        """Get overall LLM provider status.

        Returns:
            HEALTHY if any provider healthy
            DEGRADED if all providers degraded or mixed
            UNHEALTHY if all providers unhealthy
        """
        if not self._providers:
            return HealthStatus.HEALTHY

        all_health = self.get_all_health()
        statuses = [h.status for h in all_health.values()]

        if all(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.DEGRADED

    def is_provider_available(self, provider: str) -> bool:
        """Check if provider is available for requests.

        Args:
            provider: Provider name

        Returns:
            True if provider is healthy or degraded (can accept requests)
        """
        health = self.get_provider_health(provider)
        return health.status != HealthStatus.UNHEALTHY

    def get_available_provider(
        self,
        primary: str = "anthropic",
        fallback: str = "openai",
    ) -> str | None:
        """Get an available provider, preferring primary.

        Args:
            primary: Preferred provider
            fallback: Fallback provider if primary unavailable

        Returns:
            Provider name or None if all unavailable
        """
        if self.is_provider_available(primary):
            return primary
        if self.is_provider_available(fallback):
            logger.warning(f"Primary provider {primary} unavailable, using fallback {fallback}")
            return fallback
        logger.error(f"All LLM providers unavailable ({primary}, {fallback})")
        return None

    def get_recent_errors(self, provider: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent errors for a provider.

        Args:
            provider: Provider name
            limit: Max errors to return

        Returns:
            List of recent error records
        """
        health = self._get_or_create(provider)
        self._prune_old_records(health)

        errors = list(health.recent_errors)[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "error_type": e.error_type,
                "message": e.message,
            }
            for e in errors
        ]


# Global instance
_vendor_health: VendorHealthTracker | None = None


def get_vendor_health_tracker() -> VendorHealthTracker:
    """Get the global vendor health tracker instance."""
    global _vendor_health
    if _vendor_health is None:
        _vendor_health = VendorHealthTracker()
    return _vendor_health


def record_provider_success(provider: str) -> None:
    """Record a successful provider request."""
    get_vendor_health_tracker().record_success(provider)


def record_provider_failure(
    provider: str,
    error_type: str,
    error_message: str,
) -> HealthStatus | None:
    """Record a failed provider request.

    Returns:
        New status if changed (for alerting), None otherwise.
    """
    return get_vendor_health_tracker().record_failure(provider, error_type, error_message)


def get_provider_status(provider: str) -> dict[str, Any]:
    """Get status dict for a provider."""
    return get_vendor_health_tracker().get_provider_health(provider).to_dict()


def get_all_provider_status() -> dict[str, dict[str, Any]]:
    """Get status dict for all providers."""
    return {
        provider: health.to_dict()
        for provider, health in get_vendor_health_tracker().get_all_health().items()
    }


def get_overall_vendor_status() -> str:
    """Get overall vendor status string."""
    return get_vendor_health_tracker().get_overall_status().value
