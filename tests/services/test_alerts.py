"""Tests for alert service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.alerts import (
    alert_cost_anomaly,
    alert_kill_all_sessions,
    alert_runaway_session,
    alert_runaway_sessions_batch,
    alert_session_killed,
)
from backend.services.monitoring import RunawaySessionResult


@pytest.fixture
def sample_runaway_result() -> RunawaySessionResult:
    """Create a sample RunawaySessionResult for testing."""
    return RunawaySessionResult(
        session_id="test-session-123",
        user_id="user-1",
        reason="cost",
        duration_minutes=15.5,
        cost_usd=8.75,
        last_event_minutes_ago=2.0,
        started_at=datetime.now(UTC),
    )


class TestAlertRunawaySession:
    """Tests for alert_runaway_session function."""

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.notify_database_alert")
    async def test_sends_alert_when_topic_configured(
        self,
        mock_notify: AsyncMock,
        mock_get_topic: MagicMock,
        sample_runaway_result: RunawaySessionResult,
    ) -> None:
        """Test alert is sent when topic is configured."""
        mock_get_topic.return_value = "test-alerts"
        mock_notify.return_value = True

        result = await alert_runaway_session(sample_runaway_result)

        assert result is True
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "Runaway Session" in call_args.kwargs["title"]
        assert "cost" in call_args.kwargs["title"]

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    async def test_skips_alert_when_no_topic(
        self,
        mock_get_topic: MagicMock,
        sample_runaway_result: RunawaySessionResult,
    ) -> None:
        """Test alert is skipped when no topic configured."""
        mock_get_topic.return_value = ""

        result = await alert_runaway_session(sample_runaway_result)

        assert result is False


class TestAlertRunawaySessionsBatch:
    """Tests for alert_runaway_sessions_batch function."""

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    async def test_returns_true_for_empty_list(
        self,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test returns True for empty list (nothing to alert)."""
        mock_get_topic.return_value = "test-alerts"

        result = await alert_runaway_sessions_batch([])

        assert result is True

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.alert_runaway_session")
    async def test_single_result_delegates_to_single_alert(
        self,
        mock_single_alert: AsyncMock,
        mock_get_topic: MagicMock,
        sample_runaway_result: RunawaySessionResult,
    ) -> None:
        """Test single result calls single alert function."""
        mock_get_topic.return_value = "test-alerts"
        mock_single_alert.return_value = True

        result = await alert_runaway_sessions_batch([sample_runaway_result])

        assert result is True
        mock_single_alert.assert_called_once_with(sample_runaway_result)

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.notify_database_alert")
    async def test_batch_alert_for_multiple_results(
        self,
        mock_notify: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test batch alert is sent for multiple results."""
        mock_get_topic.return_value = "test-alerts"
        mock_notify.return_value = True

        results = [
            RunawaySessionResult(
                session_id=f"session-{i}",
                user_id=f"user-{i}",
                reason="cost",
                duration_minutes=10.0,
                cost_usd=6.0,
                last_event_minutes_ago=1.0,
                started_at=datetime.now(UTC),
            )
            for i in range(3)
        ]

        result = await alert_runaway_sessions_batch(results)

        assert result is True
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "3 Runaway Sessions" in call_args.kwargs["title"]

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.notify_database_alert")
    async def test_critical_priority_for_many_runaways(
        self,
        mock_notify: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test critical priority is used when > 3 runaways."""
        mock_get_topic.return_value = "test-alerts"
        mock_notify.return_value = True

        results = [
            RunawaySessionResult(
                session_id=f"session-{i}",
                user_id=f"user-{i}",
                reason="cost",
                duration_minutes=10.0,
                cost_usd=6.0,
                last_event_minutes_ago=1.0,
                started_at=datetime.now(UTC),
            )
            for i in range(5)
        ]

        await alert_runaway_sessions_batch(results)

        call_args = mock_notify.call_args
        assert call_args.kwargs["alert_type"] == "critical"


class TestAlertSessionKilled:
    """Tests for alert_session_killed function."""

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    async def test_sends_kill_alert(
        self,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test kill alert is sent with correct details."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True

        result = await alert_session_killed(
            session_id="session-123",
            killed_by="admin-user",
            reason="cost_exceeded",
            cost=5.50,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Session Killed" in call_args.kwargs["title"]
        assert "$5.50" in call_args.kwargs["message"]

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    async def test_high_priority_for_system_kills(
        self,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test high priority is used for system kills."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True

        await alert_session_killed(
            session_id="session-123",
            killed_by="system",
            reason="runaway_cost",
        )

        call_args = mock_send.call_args
        assert call_args.kwargs["priority"] == "high"


class TestAlertKillAllSessions:
    """Tests for alert_kill_all_sessions function."""

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    async def test_sends_urgent_kill_all_alert(
        self,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test kill-all alert is sent with urgent priority."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True

        result = await alert_kill_all_sessions(
            killed_count=5,
            killed_by="admin-user",
            reason="system_maintenance",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "EMERGENCY" in call_args.kwargs["title"]
        assert call_args.kwargs["priority"] == "urgent"
        assert "5 sessions" in call_args.kwargs["message"]


class TestCostAnomalyAlert:
    """Tests for alert_cost_anomaly function."""

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    @patch("backend.services.alerts.log_alert")
    async def test_sends_alert_for_negative_cost(
        self,
        mock_log_alert: AsyncMock,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test alert is sent with urgent priority for negative cost."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True
        mock_log_alert.return_value = None

        result = await alert_cost_anomaly(
            anomaly_type="negative_cost",
            session_id="session-123456789abc",
            cost=-0.50,
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "CRITICAL" in call_args.kwargs["title"]
        assert "Negative Cost" in call_args.kwargs["title"]
        assert call_args.kwargs["priority"] == "urgent"
        assert "rotating_light" in call_args.kwargs["tags"]
        assert "moneybag" in call_args.kwargs["tags"]

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    @patch("backend.services.alerts.log_alert")
    async def test_sends_alert_for_high_single_call(
        self,
        mock_log_alert: AsyncMock,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test alert is sent with high priority for high single call cost."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True
        mock_log_alert.return_value = None

        result = await alert_cost_anomaly(
            anomaly_type="high_single_call",
            session_id="session-123456789abc",
            cost=1.50,
            model="claude-opus-4-20250514",
            provider="anthropic",
            input_tokens=50000,
            output_tokens=2000,
            threshold=0.50,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "High Single Call Cost" in call_args.kwargs["title"]
        assert call_args.kwargs["priority"] == "high"
        assert "$1.5000" in call_args.kwargs["message"]
        assert "$0.50" in call_args.kwargs["message"]  # threshold
        assert "50,000" in call_args.kwargs["message"]  # input tokens formatted

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    @patch("backend.services.alerts.log_alert")
    async def test_sends_alert_for_high_session_total(
        self,
        mock_log_alert: AsyncMock,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test alert is sent with high priority for high session total."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True
        mock_log_alert.return_value = None

        result = await alert_cost_anomaly(
            anomaly_type="high_session_total",
            session_id="session-123456789abc",
            cost=8.50,
            threshold=5.00,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "High Session Total Cost" in call_args.kwargs["title"]
        assert call_args.kwargs["priority"] == "high"

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    async def test_skips_alert_when_no_topic(
        self,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test alert is skipped when no topic configured."""
        mock_get_topic.return_value = ""

        result = await alert_cost_anomaly(
            anomaly_type="high_single_call",
            session_id="session-123",
            cost=1.00,
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    @patch("backend.services.alerts.log_alert")
    async def test_logs_alert_to_database(
        self,
        mock_log_alert: AsyncMock,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test alert is logged to database with correct metadata."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True
        mock_log_alert.return_value = None

        await alert_cost_anomaly(
            anomaly_type="high_single_call",
            session_id="session-123",
            cost=1.50,
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            input_tokens=10000,
            output_tokens=500,
            threshold=0.50,
        )

        mock_log_alert.assert_called_once()
        call_args = mock_log_alert.call_args
        assert call_args.kwargs["alert_type"] == "cost_anomaly"
        assert call_args.kwargs["severity"] == "high"
        metadata = call_args.kwargs["metadata"]
        assert metadata["anomaly_type"] == "high_single_call"
        assert metadata["session_id"] == "session-123"
        assert metadata["cost"] == 1.50
        assert metadata["threshold"] == 0.50

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    @patch("backend.services.alerts.log_alert")
    async def test_handles_missing_optional_fields(
        self,
        mock_log_alert: AsyncMock,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test alert works with minimal required fields."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True
        mock_log_alert.return_value = None

        result = await alert_cost_anomaly(
            anomaly_type="high_single_call",
            cost=1.00,
        )

        assert result is True
        call_args = mock_send.call_args
        # Session should show N/A when not provided
        assert "N/A" in call_args.kwargs["message"]

    @pytest.mark.asyncio
    @patch("backend.services.alerts._get_ntfy_alerts_topic")
    @patch("backend.services.alerts.send_ntfy_alert")
    @patch("backend.services.alerts.log_alert")
    async def test_unknown_anomaly_type_uses_default_priority(
        self,
        mock_log_alert: AsyncMock,
        mock_send: AsyncMock,
        mock_get_topic: MagicMock,
    ) -> None:
        """Test unknown anomaly types use default priority."""
        mock_get_topic.return_value = "test-alerts"
        mock_send.return_value = True
        mock_log_alert.return_value = None

        await alert_cost_anomaly(
            anomaly_type="unknown_anomaly",
            cost=1.00,
        )

        call_args = mock_send.call_args
        assert call_args.kwargs["priority"] == "default"
        assert "unknown_anomaly" in call_args.kwargs["title"]
