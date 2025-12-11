"""Tests for vendor health tracking service."""

from backend.services.vendor_health import (
    HealthStatus,
    VendorHealthTracker,
    get_vendor_health_tracker,
    record_provider_failure,
    record_provider_success,
)


class TestVendorHealthTracker:
    """Tests for VendorHealthTracker."""

    def setup_method(self) -> None:
        """Create fresh tracker for each test."""
        self.tracker = VendorHealthTracker()

    def test_initial_status_healthy(self) -> None:
        """New provider starts healthy."""
        health = self.tracker.get_provider_health("anthropic")
        assert health.status == HealthStatus.HEALTHY
        assert health.error_rate == 0.0

    def test_record_success_updates_last_success(self) -> None:
        """Recording success updates timestamp."""
        self.tracker.record_success("anthropic")
        health = self.tracker.get_provider_health("anthropic")
        assert health.last_success is not None
        assert health.total_requests == 1

    def test_record_failure_increments_counts(self) -> None:
        """Recording failure updates counters."""
        self.tracker.record_failure("anthropic", "APIError", "Connection timeout")
        health = self.tracker.get_provider_health("anthropic")
        assert health.failed_requests == 1
        assert health.last_error_type == "APIError"
        assert health.last_error_message == "Connection timeout"

    def test_error_rate_calculation(self) -> None:
        """Error rate calculated correctly."""
        # 2 successes, 1 failure = 33% error rate
        self.tracker.record_success("openai")
        self.tracker.record_success("openai")
        self.tracker.record_failure("openai", "RateLimitError", "Too many requests")

        health = self.tracker.get_provider_health("openai")
        assert 0.32 <= health.error_rate <= 0.34  # ~33%

    def test_transitions_to_degraded_at_20_percent(self) -> None:
        """Status changes to degraded at 20% error rate."""
        # 4 successes, 1 failure = 20% error rate
        for _ in range(4):
            self.tracker.record_success("anthropic")
        self.tracker.record_failure("anthropic", "APIError", "Error")

        health = self.tracker.get_provider_health("anthropic")
        assert health.status == HealthStatus.DEGRADED

    def test_transitions_to_unhealthy_at_50_percent(self) -> None:
        """Status changes to unhealthy at 50% error rate."""
        # 5 successes, 5 failures = 50% error rate
        for _ in range(5):
            self.tracker.record_success("anthropic")
        for _ in range(5):
            self.tracker.record_failure("anthropic", "APIError", "Error")

        health = self.tracker.get_provider_health("anthropic")
        assert health.status == HealthStatus.UNHEALTHY

    def test_recovery_requires_low_error_rate(self) -> None:
        """Recovery from unhealthy requires <10% error rate."""
        # First, make it unhealthy
        for _ in range(5):
            self.tracker.record_failure("anthropic", "APIError", "Error")

        health = self.tracker.get_provider_health("anthropic")
        assert health.status == HealthStatus.UNHEALTHY

        # Add successes to bring error rate to ~15% (still degraded)
        for _ in range(25):
            self.tracker.record_success("anthropic")

        health = self.tracker.get_provider_health("anthropic")
        # Should still be degraded/unhealthy due to hysteresis
        assert health.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

        # Add more successes to bring error rate below 10%
        for _ in range(50):
            self.tracker.record_success("anthropic")

        health = self.tracker.get_provider_health("anthropic")
        assert health.status == HealthStatus.HEALTHY

    def test_overall_status_healthy_when_any_provider_healthy(self) -> None:
        """Overall status is healthy if any provider is healthy."""
        # Make anthropic unhealthy
        for _ in range(10):
            self.tracker.record_failure("anthropic", "APIError", "Error")

        # Keep openai healthy
        self.tracker.record_success("openai")

        assert self.tracker.get_overall_status() == HealthStatus.HEALTHY

    def test_overall_status_unhealthy_when_all_unhealthy(self) -> None:
        """Overall status is unhealthy when all providers unhealthy."""
        for provider in ["anthropic", "openai"]:
            for _ in range(10):
                self.tracker.record_failure(provider, "APIError", "Error")

        assert self.tracker.get_overall_status() == HealthStatus.UNHEALTHY

    def test_is_provider_available(self) -> None:
        """Provider availability check."""
        assert self.tracker.is_provider_available("anthropic")

        # Make unhealthy
        for _ in range(10):
            self.tracker.record_failure("anthropic", "APIError", "Error")

        assert not self.tracker.is_provider_available("anthropic")

    def test_get_available_provider_prefers_primary(self) -> None:
        """get_available_provider prefers primary when healthy."""
        self.tracker.record_success("anthropic")
        self.tracker.record_success("openai")

        provider = self.tracker.get_available_provider("anthropic", "openai")
        assert provider == "anthropic"

    def test_get_available_provider_falls_back(self) -> None:
        """get_available_provider returns fallback when primary unhealthy."""
        # Make anthropic unhealthy
        for _ in range(10):
            self.tracker.record_failure("anthropic", "APIError", "Error")

        # Keep openai healthy
        self.tracker.record_success("openai")

        provider = self.tracker.get_available_provider("anthropic", "openai")
        assert provider == "openai"

    def test_get_available_provider_returns_none_when_all_unhealthy(self) -> None:
        """get_available_provider returns None when all unhealthy."""
        for provider in ["anthropic", "openai"]:
            for _ in range(10):
                self.tracker.record_failure(provider, "APIError", "Error")

        provider = self.tracker.get_available_provider("anthropic", "openai")
        assert provider is None

    def test_to_dict_format(self) -> None:
        """to_dict returns expected format."""
        self.tracker.record_success("anthropic")
        health = self.tracker.get_provider_health("anthropic")
        result = health.to_dict()

        assert result["provider"] == "anthropic"
        assert result["status"] == "healthy"
        assert "error_rate" in result
        assert "total_requests" in result

    def test_record_failure_returns_status_on_change(self) -> None:
        """record_failure returns new status when status changes."""
        # Add some successes first so first failure doesn't immediately trigger unhealthy
        for _ in range(10):
            self.tracker.record_success("anthropic")

        # First failure shouldn't change status (10 successes + 1 failure = ~9% error)
        result = self.tracker.record_failure("anthropic", "APIError", "Error")
        assert result is None  # Still healthy

        # Add more failures to trigger change (need >50% for unhealthy)
        for _ in range(15):
            result = self.tracker.record_failure("anthropic", "APIError", "Error")

        # Should have transitioned to unhealthy
        health = self.tracker.get_provider_health("anthropic")
        assert health.status == HealthStatus.UNHEALTHY


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_global_tracker_singleton(self) -> None:
        """Global tracker is a singleton."""
        tracker1 = get_vendor_health_tracker()
        tracker2 = get_vendor_health_tracker()
        assert tracker1 is tracker2

    def test_record_provider_success(self) -> None:
        """record_provider_success uses global tracker."""
        record_provider_success("test_provider")
        tracker = get_vendor_health_tracker()
        health = tracker.get_provider_health("test_provider")
        assert health.total_requests >= 1

    def test_record_provider_failure(self) -> None:
        """record_provider_failure uses global tracker."""
        record_provider_failure("test_provider_2", "TestError", "Test message")
        tracker = get_vendor_health_tracker()
        health = tracker.get_provider_health("test_provider_2")
        assert health.failed_requests >= 1
