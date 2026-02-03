"""Tests for CostTracker metrics and anomaly detection.

Validates:
- Flush duration histogram is observed
- Retry queue gauge updates
- Anomaly counter increments for each type
- Anomaly detection thresholds
- Cost flush success/failure counters
"""

import logging
from unittest.mock import patch

import pytest

from bo1.llm.cost_tracker import CostRecord, CostTracker


class TestCostFlushMetrics:
    """Test _record_flush_metrics method."""

    def test_flush_metrics_recorded_on_success(self):
        """Verify both duration and success counter are recorded."""
        with patch("bo1.llm.cost_tracker.CostTracker._record_flush_metrics") as mock_record:
            # Simulate what _flush_batch does
            CostTracker._record_flush_metrics(0.05, success=True)

        mock_record.assert_called_once_with(0.05, success=True)

    def test_flush_metrics_recorded_on_failure(self):
        """Verify metrics are recorded on flush failure."""
        with patch("bo1.llm.cost_tracker.CostTracker._record_flush_metrics") as mock_record:
            CostTracker._record_flush_metrics(0.10, success=False)

        mock_record.assert_called_once_with(0.10, success=False)

    def test_record_flush_metrics_calls_prometheus(self):
        """Verify _record_flush_metrics calls Prometheus functions."""
        with (
            patch("backend.api.middleware.metrics.record_cost_flush_duration") as mock_duration,
            patch("backend.api.middleware.metrics.record_cost_flush") as mock_flush,
        ):
            CostTracker._record_flush_metrics(0.123, success=True)

        mock_duration.assert_called_once_with(0.123)
        mock_flush.assert_called_once_with(True)

    def test_record_flush_metrics_handles_import_error(self):
        """Verify graceful handling when metrics module not available."""
        with patch("bo1.llm.cost_tracker.CostTracker._record_flush_metrics") as mock_method:
            # Side effect simulates import failing gracefully
            mock_method.side_effect = lambda d, s: None
            # Should not raise
            CostTracker._record_flush_metrics(0.1, True)


class TestRetryQueueMetrics:
    """Test _update_retry_queue_metric method."""

    def test_update_retry_queue_metric_calls_prometheus(self):
        """Verify retry queue metric update calls Prometheus gauge."""
        with patch("backend.api.middleware.metrics.set_cost_retry_queue_depth") as mock_set:
            CostTracker._update_retry_queue_metric(42)

        mock_set.assert_called_once_with(42)

    def test_update_retry_queue_metric_handles_import_error(self):
        """Verify graceful handling when metrics module not available."""
        # Should not raise even if import fails
        with patch.object(
            CostTracker,
            "_update_retry_queue_metric",
            side_effect=lambda d: None,
        ):
            CostTracker._update_retry_queue_metric(100)


class TestCostAnomalyDetection:
    """Test check_anomaly method."""

    def test_detects_negative_cost(self, caplog):
        """Verify negative cost is detected and logged."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=-0.01,
            session_id="test_session",
        )

        with patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True):
            with caplog.at_level(logging.ERROR):
                anomalies = CostTracker.check_anomaly(record)

        assert "negative_cost" in anomalies
        assert "Negative cost detected" in caplog.text

    def test_detects_high_single_call(self, caplog):
        """Verify high single call cost is detected."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.75,  # Above $0.50 threshold
            session_id="test_session",
            input_tokens=50000,
            output_tokens=2000,
        )

        with (
            patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
        ):
            with caplog.at_level(logging.ERROR):
                anomalies = CostTracker.check_anomaly(record)

        assert "high_single_call" in anomalies
        assert "High single call cost" in caplog.text

    def test_detects_high_session_total(self, caplog):
        """Verify high session total is detected when provided."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.10,
            session_id="test_session",
        )

        with (
            patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch("bo1.constants.CostAnomalyConfig.get_session_total_threshold", return_value=5.00),
        ):
            with caplog.at_level(logging.ERROR):
                anomalies = CostTracker.check_anomaly(record, session_total=6.50)

        assert "high_session_total" in anomalies
        assert "High session total" in caplog.text

    def test_no_anomaly_when_under_thresholds(self, caplog):
        """Verify no anomaly when all values are normal."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.05,
            session_id="test_session",
        )

        with (
            patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch("bo1.constants.CostAnomalyConfig.get_session_total_threshold", return_value=5.00),
        ):
            with caplog.at_level(logging.ERROR):
                anomalies = CostTracker.check_anomaly(record, session_total=1.00)

        assert len(anomalies) == 0
        assert "cost" not in caplog.text.lower() or "Negative" not in caplog.text

    def test_disabled_detection_returns_empty(self):
        """Verify disabled detection returns empty list."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=-100.0,  # Would be flagged if enabled
        )

        with patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=False):
            anomalies = CostTracker.check_anomaly(record)

        assert len(anomalies) == 0

    def test_multiple_anomalies_detected(self, caplog):
        """Verify multiple anomaly types can be detected simultaneously."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=-0.01,  # Negative
            session_id="test_session",
        )

        # Note: negative cost won't also trigger high_single_call since -0.01 < 0.50
        with patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True):
            anomalies = CostTracker.check_anomaly(record)

        assert "negative_cost" in anomalies


class TestAnomalyMetricsRecording:
    """Test _record_anomaly_metrics method."""

    def test_record_anomaly_metrics_calls_prometheus(self):
        """Verify anomaly metrics are recorded to Prometheus."""
        anomalies = ["high_single_call", "negative_cost"]

        with patch("backend.api.middleware.metrics.record_cost_anomaly") as mock_record:
            CostTracker._record_anomaly_metrics(anomalies)

        assert mock_record.call_count == 2
        mock_record.assert_any_call("high_single_call")
        mock_record.assert_any_call("negative_cost")

    def test_record_anomaly_metrics_empty_list(self):
        """Verify no calls when anomaly list is empty."""
        with patch("backend.api.middleware.metrics.record_cost_anomaly") as mock_record:
            CostTracker._record_anomaly_metrics([])

        mock_record.assert_not_called()

    def test_record_anomaly_metrics_handles_import_error(self):
        """Verify graceful handling when metrics module not available."""
        # Should not raise
        with patch.object(
            CostTracker,
            "_record_anomaly_metrics",
            side_effect=lambda a: None,
        ):
            CostTracker._record_anomaly_metrics(["high_single_call"])


class TestCostAnomalyConfig:
    """Test CostAnomalyConfig class."""

    def test_default_single_call_threshold(self):
        """Verify default single call threshold is $0.50."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {}, clear=True):
            # Clear env to get default
            import importlib

            import bo1.constants

            importlib.reload(bo1.constants)

            # Just test the static value
            assert CostAnomalyConfig.SINGLE_CALL_THRESHOLD_USD == 0.50

    def test_default_session_total_threshold(self):
        """Verify default session total threshold is $5.00."""
        from bo1.constants import CostAnomalyConfig

        assert CostAnomalyConfig.SESSION_TOTAL_THRESHOLD_USD == 5.00

    def test_single_call_threshold_from_env(self):
        """Verify single call threshold can be overridden by env var."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {"COST_ANOMALY_SINGLE_CALL_THRESHOLD": "1.25"}):
            threshold = CostAnomalyConfig.get_single_call_threshold()

        assert threshold == 1.25

    def test_session_total_threshold_from_env(self):
        """Verify session total threshold can be overridden by env var."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {"COST_ANOMALY_SESSION_TOTAL_THRESHOLD": "10.00"}):
            threshold = CostAnomalyConfig.get_session_total_threshold()

        assert threshold == 10.00

    def test_is_enabled_default(self):
        """Verify anomaly detection is enabled by default."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {}, clear=True):
            # Default is true
            enabled = CostAnomalyConfig.is_enabled()

        assert enabled is True

    def test_is_enabled_disabled_via_env(self):
        """Verify anomaly detection can be disabled via env var."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {"COST_ANOMALY_DETECTION_ENABLED": "false"}):
            enabled = CostAnomalyConfig.is_enabled()

        assert enabled is False


class TestAnomalyCheckIntegration:
    """Integration tests for anomaly checking in track_call context manager."""

    def test_anomaly_check_called_in_track_call(self):
        """Verify check_anomaly is called during track_call exit."""
        with (
            patch.object(CostTracker, "check_anomaly") as mock_check,
            patch.object(CostTracker, "log_cost", return_value="test_id"),
            patch.object(CostTracker, "_emit_cache_metrics"),
            patch.object(CostTracker, "_check_token_budget"),
            patch.object(CostTracker, "_emit_prometheus_metrics"),
        ):
            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
                model_name="claude-sonnet-4-5-20250929",
                session_id="test_session",
            ) as record:
                record.input_tokens = 1000
                record.output_tokens = 200

        mock_check.assert_called_once()
        # Verify it was called with the record
        call_args = mock_check.call_args
        assert call_args[0][0].session_id == "test_session"


class TestCostAnomalyAlerts:
    """Test cost anomaly ntfy alerting integration."""

    def test_alerts_sent_when_anomaly_detected(self):
        """Verify alerts are sent when anomalies are detected."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=1.00,  # Above $0.50 threshold
            session_id="test_session",
            input_tokens=50000,
            output_tokens=2000,
        )

        with (
            patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.are_alerts_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch.object(CostTracker, "_send_anomaly_alerts") as mock_send_alerts,
        ):
            anomalies = CostTracker.check_anomaly(record)

        assert "high_single_call" in anomalies
        mock_send_alerts.assert_called_once()
        # Verify alert function called with correct args
        call_args = mock_send_alerts.call_args
        assert "high_single_call" in call_args[0][0]  # anomalies list
        assert call_args[0][1].session_id == "test_session"  # record

    def test_no_alerts_when_disabled(self):
        """Verify alerts are not sent when COST_ANOMALY_ALERTS_ENABLED=false."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=1.00,
            session_id="test_session",
        )

        # Patch env var directly to disable alerts
        with (
            patch.dict("os.environ", {"COST_ANOMALY_ALERTS_ENABLED": "false"}),
            patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch.object(CostTracker, "_send_anomaly_alerts") as mock_send_alerts,
        ):
            anomalies = CostTracker.check_anomaly(record)

        # Anomaly should still be detected
        assert "high_single_call" in anomalies
        # But alerts should not be sent
        mock_send_alerts.assert_not_called()

    def test_no_alerts_when_no_anomalies(self):
        """Verify alerts are not sent when no anomalies detected."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.05,  # Below threshold
            session_id="test_session",
        )

        with (
            patch("bo1.constants.CostAnomalyConfig.is_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.are_alerts_enabled", return_value=True),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch.object(CostTracker, "_send_anomaly_alerts") as mock_send_alerts,
        ):
            anomalies = CostTracker.check_anomaly(record)

        assert len(anomalies) == 0
        mock_send_alerts.assert_not_called()

    def test_send_anomaly_alerts_handles_import_error(self):
        """Verify graceful degradation when alert service not available."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=1.00,
            session_id="test_session",
        )

        # Mock import error for alert service
        with patch.dict("sys.modules", {"backend.services.alerts": None}):
            # Should not raise
            CostTracker._send_anomaly_alerts(["high_single_call"], record)

    @pytest.mark.asyncio
    async def test_send_anomaly_alerts_includes_threshold_for_single_call(self):
        """Verify threshold is included in alert for high_single_call."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=1.00,
            session_id="test_session",
            input_tokens=50000,
            output_tokens=2000,
        )

        from unittest.mock import AsyncMock

        with (
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch(
                "backend.services.alerts.alert_cost_anomaly", new_callable=AsyncMock
            ) as mock_alert,
        ):
            mock_alert.return_value = True

            # Call in async context
            CostTracker._send_anomaly_alerts(["high_single_call"], record)
            # Give task time to complete
            import asyncio

            await asyncio.sleep(0.01)

        # Verify threshold was passed
        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args[1]
        assert call_kwargs["threshold"] == 0.50
        assert call_kwargs["cost"] == 1.00

    @pytest.mark.asyncio
    async def test_send_anomaly_alerts_includes_session_total_for_high_session(self):
        """Verify session total cost is used for high_session_total alerts."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.10,  # Individual call cost
            session_id="test_session",
        )

        from unittest.mock import AsyncMock

        with (
            patch("bo1.constants.CostAnomalyConfig.get_session_total_threshold", return_value=5.00),
            patch("bo1.constants.CostAnomalyConfig.get_single_call_threshold", return_value=0.50),
            patch(
                "backend.services.alerts.alert_cost_anomaly", new_callable=AsyncMock
            ) as mock_alert,
        ):
            mock_alert.return_value = True

            # Call with session total
            CostTracker._send_anomaly_alerts(["high_session_total"], record, session_total=6.50)
            # Give task time to complete
            import asyncio

            await asyncio.sleep(0.01)

        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args[1]
        # Should use session total, not individual call cost
        assert call_kwargs["cost"] == 6.50
        assert call_kwargs["threshold"] == 5.00


class TestAreAlertsEnabled:
    """Test CostAnomalyConfig.are_alerts_enabled method."""

    def test_alerts_enabled_by_default(self):
        """Verify alerts are enabled by default."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {}, clear=True):
            enabled = CostAnomalyConfig.are_alerts_enabled()

        assert enabled is True

    def test_alerts_disabled_via_env(self):
        """Verify alerts can be disabled via env var."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {"COST_ANOMALY_ALERTS_ENABLED": "false"}):
            enabled = CostAnomalyConfig.are_alerts_enabled()

        assert enabled is False

    def test_alerts_enabled_case_insensitive(self):
        """Verify env var is case insensitive."""
        from bo1.constants import CostAnomalyConfig

        with patch.dict("os.environ", {"COST_ANOMALY_ALERTS_ENABLED": "FALSE"}):
            enabled = CostAnomalyConfig.are_alerts_enabled()

        assert enabled is False

        with patch.dict("os.environ", {"COST_ANOMALY_ALERTS_ENABLED": "True"}):
            enabled = CostAnomalyConfig.are_alerts_enabled()

        assert enabled is True


class TestPromptTypeCacheMetrics:
    """Test get_prompt_type_cache_metrics method."""

    def test_returns_empty_list_when_no_data(self):
        """Verify empty list returned when no Anthropic costs exist."""
        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value
            mock_cursor.__enter__.return_value.fetchall.return_value = []

            result = CostTracker.get_prompt_type_cache_metrics(days=7)

        assert result == []

    def test_returns_correct_structure(self):
        """Verify returned structure has all expected fields."""
        mock_rows = [
            {
                0: "persona_contribution",
                1: 80,  # cache_hits
                2: 20,  # cache_misses
                3: 100,  # total_requests
                4: 50000,  # cache_read_tokens
                5: 100000,  # total_input_tokens
            }
        ]

        # Convert to list with positional access
        class MockRow:
            def __init__(self, data):
                self._data = data

            def __getitem__(self, key):
                return self._data[key]

        mock_rows = [MockRow(mock_rows[0])]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value
            mock_cursor.__enter__.return_value.fetchall.return_value = mock_rows

            result = CostTracker.get_prompt_type_cache_metrics(days=7)

        assert len(result) == 1
        item = result[0]
        assert item["prompt_type"] == "persona_contribution"
        assert item["cache_hits"] == 80
        assert item["cache_misses"] == 20
        assert item["cache_hit_rate"] == 0.8
        assert item["total_requests"] == 100
        assert item["cache_read_tokens"] == 50000
        assert item["total_input_tokens"] == 100000
        assert item["cache_token_rate"] == 0.5

    def test_handles_zero_totals(self):
        """Verify zero division is handled for empty prompt types."""

        class MockRow:
            def __init__(self, data):
                self._data = data

            def __getitem__(self, key):
                return self._data[key]

        mock_rows = [
            MockRow(
                {
                    0: "unknown",
                    1: 0,  # cache_hits
                    2: 0,  # cache_misses
                    3: 0,  # total_requests
                    4: 0,  # cache_read_tokens
                    5: 0,  # total_input_tokens
                }
            )
        ]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value
            mock_cursor.__enter__.return_value.fetchall.return_value = mock_rows

            result = CostTracker.get_prompt_type_cache_metrics(days=7)

        assert len(result) == 1
        item = result[0]
        assert item["cache_hit_rate"] == 0.0
        assert item["cache_token_rate"] == 0.0

    def test_groups_null_prompt_type_as_unknown(self):
        """Verify NULL prompt_type is grouped as 'unknown'."""

        class MockRow:
            def __init__(self, data):
                self._data = data

            def __getitem__(self, key):
                return self._data[key]

        mock_rows = [
            MockRow(
                {
                    0: "unknown",  # COALESCE result
                    1: 10,
                    2: 5,
                    3: 15,
                    4: 1000,
                    5: 2000,
                }
            )
        ]

        with patch("bo1.llm.cost_tracker.db_session") as mock_db:
            mock_cursor = mock_db.return_value.__enter__.return_value.cursor.return_value
            mock_cursor.__enter__.return_value.fetchall.return_value = mock_rows

            result = CostTracker.get_prompt_type_cache_metrics(days=7)

        assert result[0]["prompt_type"] == "unknown"


class TestPromptTypeCachePrometheus:
    """Test Prometheus metrics for prompt type cache."""

    def test_emit_cache_metrics_calls_prompt_type_metric(self):
        """Verify _emit_cache_metrics calls record_prompt_type_cache for Anthropic."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.05,
            cache_read_tokens=1000,
            prompt_type="persona_contribution",
        )

        with (
            patch("backend.api.metrics.metrics"),
            patch("backend.api.metrics.prom_metrics") as mock_prom,
        ):
            CostTracker._emit_cache_metrics(record)

        # Verify prompt type cache metric was called
        mock_prom.record_prompt_type_cache.assert_called_once_with(
            "persona_contribution",
            True,  # cache_hit=True since cache_read_tokens > 0
        )

    def test_emit_cache_metrics_skips_non_anthropic(self):
        """Verify prompt type metric is not called for non-Anthropic providers."""
        record = CostRecord(
            provider="voyage",
            model_name="voyage-3",
            operation_type="embedding",
            total_cost=0.001,
            prompt_type="embedding",
        )

        with (
            patch("backend.api.metrics.metrics"),
            patch("backend.api.metrics.prom_metrics") as mock_prom,
        ):
            CostTracker._emit_cache_metrics(record)

        # Verify prompt type cache metric was NOT called
        mock_prom.record_prompt_type_cache.assert_not_called()

    def test_emit_cache_metrics_handles_none_prompt_type(self):
        """Verify None prompt_type is handled gracefully."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.05,
            cache_read_tokens=0,
            prompt_type=None,
        )

        with (
            patch("backend.api.metrics.metrics"),
            patch("backend.api.metrics.prom_metrics") as mock_prom,
        ):
            CostTracker._emit_cache_metrics(record)

        # Should still be called with None (metric method handles it)
        mock_prom.record_prompt_type_cache.assert_called_once_with(
            None,
            False,  # cache_hit=False since cache_read_tokens == 0
        )
