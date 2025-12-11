"""Tests for internal service monitoring."""

import pytest

from backend.services.service_monitor import (
    ServiceMonitor,
    ServiceStatus,
    get_service_monitor,
    get_system_status,
    record_service_success,
)


class TestServiceMonitor:
    """Tests for ServiceMonitor."""

    def setup_method(self) -> None:
        """Create fresh monitor for each test."""
        self.monitor = ServiceMonitor()

    def test_initial_services_operational(self) -> None:
        """Services start operational."""
        health = self.monitor.get_service_health("postgres")
        assert health.status == ServiceStatus.OPERATIONAL

    def test_record_success_updates_metrics(self) -> None:
        """Recording success updates latency and timestamp."""
        self.monitor.record_success("postgres", latency_ms=50.0)
        health = self.monitor.get_service_health("postgres")
        assert health.last_check is not None
        assert len(health.recent_latencies) == 1

    @pytest.mark.asyncio
    async def test_record_failure_updates_metrics(self) -> None:
        """Recording failure updates error count."""
        await self.monitor.record_failure("redis", "Connection refused")
        health = self.monitor.get_service_health("redis")
        assert len(health.recent_errors) == 1
        assert health.last_error == "Connection refused"

    def test_error_rate_calculation(self) -> None:
        """Error rate calculated correctly."""
        import time

        # 2 successes, 1 failure = 33% error rate
        self.monitor.record_success("postgres")
        self.monitor.record_success("postgres")
        # Use sync method for testing (record_failure is async)
        health = self.monitor._get_service("postgres")
        # Add error with current timestamp so it's in the window
        health.recent_errors.append((time.time(), "Error"))
        # Need to also add to successes to count as a request
        health.recent_successes.append(time.time())
        self.monitor._update_status(health)

        health = self.monitor.get_service_health("postgres")
        # 3 total requests (2 successes + 1 that had error), 1 error = 33%
        assert 0.24 <= health.error_rate <= 0.34  # ~25-33%

    @pytest.mark.asyncio
    async def test_high_error_rate_triggers_degraded(self) -> None:
        """High error rate transitions to degraded."""
        # 4 successes, 2 failures = 33% > 20% threshold
        for _ in range(4):
            self.monitor.record_success("postgres")
        for _ in range(2):
            await self.monitor.record_failure("postgres", "Connection timeout")

        health = self.monitor.get_service_health("postgres")
        assert health.status == ServiceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_very_high_error_rate_triggers_outage(self) -> None:
        """Very high error rate transitions to outage."""
        # 5 failures, 5 successes = 50% error rate
        for _ in range(5):
            self.monitor.record_success("redis")
        for _ in range(5):
            await self.monitor.record_failure("redis", "Connection refused")

        health = self.monitor.get_service_health("redis")
        assert health.status == ServiceStatus.OUTAGE

    def test_latency_percentiles(self) -> None:
        """Latency percentiles calculated correctly."""
        # Add varied latencies
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for lat in latencies:
            self.monitor.record_success("postgres", latency_ms=float(lat))

        health = self.monitor.get_service_health("postgres")
        assert health.latency_p50 is not None
        assert health.latency_p95 is not None
        # p50 should be around 50, p95 around 95
        assert 45 <= health.latency_p50 <= 60
        assert 90 <= health.latency_p95 <= 100

    def test_overall_status_operational_when_all_ok(self) -> None:
        """Overall status operational when all critical services ok."""
        self.monitor.record_success("postgres")
        self.monitor.record_success("redis")
        self.monitor.record_success("anthropic")

        assert self.monitor.get_overall_status() == ServiceStatus.OPERATIONAL

    @pytest.mark.asyncio
    async def test_overall_status_degraded_when_critical_degraded(self) -> None:
        """Overall status degraded when critical service degraded."""
        # Make postgres degraded
        for _ in range(4):
            self.monitor.record_success("postgres")
        for _ in range(2):
            await self.monitor.record_failure("postgres", "Error")

        assert self.monitor.get_overall_status() == ServiceStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_overall_status_outage_when_critical_outage(self) -> None:
        """Overall status outage when critical service has outage."""
        # Make postgres outage
        for _ in range(5):
            self.monitor.record_success("postgres")
        for _ in range(5):
            await self.monitor.record_failure("postgres", "Error")

        assert self.monitor.get_overall_status() == ServiceStatus.OUTAGE

    def test_non_critical_service_doesnt_affect_overall(self) -> None:
        """Non-critical service outage doesn't cause overall outage."""
        # Make spaces (non-critical) have issues
        health = self.monitor._get_service("spaces")
        for _ in range(10):
            health.recent_errors.append((1.0, "Error"))
        self.monitor._update_status(health)

        # Overall should still be operational if critical services ok
        self.monitor.record_success("postgres")
        self.monitor.record_success("redis")
        assert self.monitor.get_overall_status() == ServiceStatus.OPERATIONAL

    def test_status_message_none_when_operational(self) -> None:
        """No status message when operational."""
        self.monitor.record_success("postgres")
        assert self.monitor.get_status_message() is None

    @pytest.mark.asyncio
    async def test_status_message_present_when_degraded(self) -> None:
        """Status message present when degraded."""
        for _ in range(4):
            self.monitor.record_success("postgres")
        for _ in range(2):
            await self.monitor.record_failure("postgres", "Error")

        message = self.monitor.get_status_message()
        assert message is not None
        assert "slow" in message.lower() or "unavailable" in message.lower()

    @pytest.mark.asyncio
    async def test_incidents_recorded_on_status_change(self) -> None:
        """Incidents recorded when status changes."""
        # Cause a status change
        for _ in range(5):
            self.monitor.record_success("postgres")
        for _ in range(5):
            await self.monitor.record_failure("postgres", "Error")

        incidents = self.monitor.get_recent_incidents(24)
        # Should have at least one incident from the status change
        assert len(incidents) >= 1
        assert incidents[-1]["service"] == "postgres"

    def test_anomaly_detection_triggers_degraded(self) -> None:
        """Anomaly detection (3x baseline error rate) triggers degraded."""
        import time

        # Set low baseline so we can trigger anomaly with smaller sample
        health = self.monitor._get_service("postgres")
        health.baseline_error_rate = 0.01  # 1% baseline

        now = time.time()
        # 90 successes, 10 failures = 10% error rate = 10x baseline (> 3x threshold)
        for i in range(90):
            health.recent_successes.append(now + i * 0.001)
        for i in range(10):
            health.recent_errors.append((now + 90 * 0.001 + i * 0.001, "Error"))

        self.monitor._update_status(health)
        # 10% error rate is > 3x baseline of 1% = anomaly -> degraded
        assert health.status == ServiceStatus.DEGRADED

    def test_get_all_health(self) -> None:
        """get_all_health returns all tracked services."""
        self.monitor.record_success("postgres")
        self.monitor.record_success("redis")

        all_health = self.monitor.get_all_health()
        assert "postgres" in all_health
        assert "redis" in all_health

    def test_service_to_dict_format(self) -> None:
        """Service to_dict returns expected format."""
        self.monitor.record_success("postgres", latency_ms=25.0)
        health = self.monitor.get_service_health("postgres")
        result = health.to_dict()

        assert result["name"] == "postgres"
        assert result["status"] == "operational"
        assert "error_rate" in result
        assert "is_critical" in result


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_global_monitor_singleton(self) -> None:
        """Global monitor is a singleton."""
        monitor1 = get_service_monitor()
        monitor2 = get_service_monitor()
        assert monitor1 is monitor2

    def test_get_system_status_format(self) -> None:
        """get_system_status returns expected format."""
        status = get_system_status()
        assert "status" in status
        assert "message" in status
        assert "services" in status
        assert status["status"] in ("operational", "degraded", "outage")

    def test_record_service_success_uses_global(self) -> None:
        """record_service_success uses global monitor."""
        record_service_success("test_service", latency_ms=10.0)
        monitor = get_service_monitor()
        health = monitor.get_service_health("test_service")
        assert health.last_check is not None
