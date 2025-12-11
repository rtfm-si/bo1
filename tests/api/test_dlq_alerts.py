"""Unit tests for DLQ monitoring alerts.

Tests check_dlq_alerts thresholds and Prometheus metrics.
"""

import logging

import pytest

from backend.api.event_publisher import (
    DLQ_ALERT_THRESHOLD,
    DLQ_CRITICAL_THRESHOLD,
    check_dlq_alerts,
)
from backend.api.metrics import prom_metrics


class TestCheckDlqAlerts:
    """Tests for check_dlq_alerts function."""

    def test_no_alert_below_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """No alert logged when DLQ depth below warning threshold."""
        with caplog.at_level(logging.WARNING):
            check_dlq_alerts(DLQ_ALERT_THRESHOLD - 1)

        assert "[DLQ_ALERT]" not in caplog.text

    def test_no_alert_at_zero(self, caplog: pytest.LogCaptureFixture) -> None:
        """No alert logged when DLQ is empty."""
        with caplog.at_level(logging.WARNING):
            check_dlq_alerts(0)

        assert "[DLQ_ALERT]" not in caplog.text

    def test_warning_at_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """Warning logged when DLQ depth equals warning threshold."""
        with caplog.at_level(logging.WARNING):
            check_dlq_alerts(DLQ_ALERT_THRESHOLD)

        assert "[DLQ_ALERT] Warning" in caplog.text
        assert str(DLQ_ALERT_THRESHOLD) in caplog.text

    def test_warning_above_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """Warning logged when DLQ depth above warning but below critical."""
        depth = DLQ_ALERT_THRESHOLD + 5
        with caplog.at_level(logging.WARNING):
            check_dlq_alerts(depth)

        assert "[DLQ_ALERT] Warning" in caplog.text
        assert str(depth) in caplog.text

    def test_critical_at_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """Error logged when DLQ depth equals critical threshold."""
        with caplog.at_level(logging.ERROR):
            check_dlq_alerts(DLQ_CRITICAL_THRESHOLD)

        assert "[DLQ_ALERT] Critical" in caplog.text
        assert str(DLQ_CRITICAL_THRESHOLD) in caplog.text

    def test_critical_above_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """Error logged when DLQ depth above critical threshold."""
        depth = DLQ_CRITICAL_THRESHOLD + 100
        with caplog.at_level(logging.ERROR):
            check_dlq_alerts(depth)

        assert "[DLQ_ALERT] Critical" in caplog.text
        assert str(depth) in caplog.text

    def test_negative_depth_no_alert(self, caplog: pytest.LogCaptureFixture) -> None:
        """No alert logged when depth is negative (error retrieving)."""
        with caplog.at_level(logging.WARNING):
            check_dlq_alerts(-1)

        assert "[DLQ_ALERT]" not in caplog.text


class TestDlqMetrics:
    """Tests for DLQ Prometheus metrics."""

    def test_update_queue_metrics(self) -> None:
        """Metrics are updated correctly."""
        prom_metrics.update_queue_metrics(dlq_depth=25, retry_queue_depth=100)

        # Verify gauges are set (Prometheus gauges expose _value for testing)
        assert prom_metrics.event_dlq_depth._value._value == 25
        assert prom_metrics.event_retry_queue_depth._value._value == 100

    def test_update_queue_metrics_zero(self) -> None:
        """Metrics can be set to zero."""
        prom_metrics.update_queue_metrics(dlq_depth=0, retry_queue_depth=0)

        assert prom_metrics.event_dlq_depth._value._value == 0
        assert prom_metrics.event_retry_queue_depth._value._value == 0


class TestThresholdValues:
    """Tests for threshold constant values."""

    def test_warning_threshold_reasonable(self) -> None:
        """Warning threshold is a reasonable positive value."""
        assert DLQ_ALERT_THRESHOLD > 0
        assert DLQ_ALERT_THRESHOLD < DLQ_CRITICAL_THRESHOLD

    def test_critical_threshold_reasonable(self) -> None:
        """Critical threshold is higher than warning."""
        assert DLQ_CRITICAL_THRESHOLD > DLQ_ALERT_THRESHOLD
        assert DLQ_CRITICAL_THRESHOLD > 0
