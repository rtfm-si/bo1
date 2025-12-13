"""Tests for automated recovery service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.auto_remediation import (
    AutoRemediation,
    ErrorFix,
    RemediationOutcome,
    RemediationResult,
    RemediationType,
    execute_remediation,
    get_auto_remediation,
)


@pytest.fixture
def sample_fix() -> ErrorFix:
    """Create a sample error fix."""
    return ErrorFix(
        id=1,
        error_pattern_id=1,
        fix_type=RemediationType.RECONNECT_REDIS.value,
        fix_config={"max_retries": 3, "retry_delay_seconds": 1},
        priority=1,
        enabled=True,
        success_count=5,
        failure_count=2,
        last_applied_at=datetime.now(UTC),
    )


@pytest.fixture
def remediation() -> AutoRemediation:
    """Create AutoRemediation instance."""
    return AutoRemediation()


class TestRemediationType:
    """Tests for RemediationType enum."""

    def test_enum_values(self) -> None:
        """Test all expected remediation types exist."""
        assert RemediationType.RECONNECT_REDIS.value == "reconnect_redis"
        assert RemediationType.RELEASE_IDLE_CONNECTIONS.value == "release_idle_connections"
        assert RemediationType.CIRCUIT_BREAK.value == "circuit_break"
        assert RemediationType.RESET_SSE_CONNECTIONS.value == "reset_sse_connections"
        assert RemediationType.CLEAR_CACHES.value == "clear_caches"
        assert RemediationType.KILL_RUNAWAY_SESSIONS.value == "kill_runaway_sessions"
        assert RemediationType.ALERT_ONLY.value == "alert_only"


class TestRemediationOutcome:
    """Tests for RemediationOutcome enum."""

    def test_enum_values(self) -> None:
        """Test all expected outcomes exist."""
        assert RemediationOutcome.SUCCESS.value == "success"
        assert RemediationOutcome.FAILURE.value == "failure"
        assert RemediationOutcome.SKIPPED.value == "skipped"
        assert RemediationOutcome.PARTIAL.value == "partial"


class TestAutoRemediation:
    """Tests for AutoRemediation class."""

    @patch("backend.services.auto_remediation.db_session")
    def test_get_fix_for_pattern(self, mock_db: MagicMock, remediation: AutoRemediation) -> None:
        """Test getting fix for pattern from database."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (
            1,  # id
            1,  # error_pattern_id
            "reconnect_redis",  # fix_type
            {"max_retries": 3},  # fix_config
            1,  # priority
            True,  # enabled
            5,  # success_count
            2,  # failure_count
            None,  # last_applied_at
        )
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )

        fix = remediation.get_fix_for_pattern(1)

        assert fix is not None
        assert fix.id == 1
        assert fix.fix_type == "reconnect_redis"
        assert fix.fix_config == {"max_retries": 3}

    @patch("backend.services.auto_remediation.db_session")
    def test_get_fix_for_pattern_none(
        self, mock_db: MagicMock, remediation: AutoRemediation
    ) -> None:
        """Test getting fix when none configured."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )

        fix = remediation.get_fix_for_pattern(999)

        assert fix is None

    @pytest.mark.asyncio
    async def test_execute_fix_unknown_type(
        self, remediation: AutoRemediation, sample_fix: ErrorFix
    ) -> None:
        """Test executing fix with unknown type."""
        sample_fix.fix_type = "unknown_fix_type"

        result = await remediation.execute_fix(sample_fix)

        assert result.outcome == RemediationOutcome.SKIPPED
        assert "Unknown fix type" in result.message

    @pytest.mark.asyncio
    @patch("backend.services.auto_remediation.AutoRemediation._update_fix_stats")
    async def test_execute_fix_exception(
        self, mock_stats: AsyncMock, remediation: AutoRemediation, sample_fix: ErrorFix
    ) -> None:
        """Test executing fix that raises exception."""
        # Make the handler raise an exception
        remediation._fix_handlers[sample_fix.fix_type] = AsyncMock(
            side_effect=Exception("Test error")
        )

        result = await remediation.execute_fix(sample_fix)

        assert result.outcome == RemediationOutcome.FAILURE
        assert "Test error" in result.message
        mock_stats.assert_called_once_with(sample_fix.id, success=False)

    @pytest.mark.asyncio
    @patch("backend.services.auto_remediation.db_session")
    async def test_log_remediation(self, mock_db: MagicMock, remediation: AutoRemediation) -> None:
        """Test logging remediation to database."""
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )

        result = RemediationResult(
            outcome=RemediationOutcome.SUCCESS,
            fix_type="reconnect_redis",
            duration_ms=100,
            message="Redis reconnected",
            details={"attempts": 2},
        )

        await remediation.log_remediation(1, 1, result, {"extra": "context"})

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO auto_remediation_log" in call_args[0][0]


class TestFixImplementations:
    """Tests for individual fix implementations."""

    @pytest.fixture
    def remediation(self) -> AutoRemediation:
        return AutoRemediation()

    @pytest.mark.asyncio
    @patch("backend.services.auto_remediation.AutoRemediation._update_fix_stats")
    async def test_fix_db_pool_reset(
        self, mock_stats: AsyncMock, remediation: AutoRemediation
    ) -> None:
        """Test database pool reset fix."""
        with patch("backend.services.auto_remediation.db_session") as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1,)
            mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = await remediation._fix_db_pool_reset({"idle_timeout_seconds": 30}, {})

            assert result.outcome == RemediationOutcome.SUCCESS
            assert "Database pool verified" in result.message

    @pytest.mark.asyncio
    async def test_fix_sse_reset(self, remediation: AutoRemediation) -> None:
        """Test SSE connection reset fix."""
        result = await remediation._fix_sse_reset({"max_age_seconds": 300}, {})

        assert result.outcome == RemediationOutcome.SUCCESS
        assert "300" in result.message

    @pytest.mark.asyncio
    async def test_fix_clear_caches_success(self, remediation: AutoRemediation) -> None:
        """Test cache clearing fix."""
        result = await remediation._fix_clear_caches(
            {"caches": ["redis_local", "research_cache"]}, {}
        )

        assert result.outcome == RemediationOutcome.SUCCESS
        assert result.details is not None
        assert len(result.details["cleared"]) == 2

    @pytest.mark.asyncio
    async def test_fix_clear_caches_unknown(self, remediation: AutoRemediation) -> None:
        """Test cache clearing with unknown cache."""
        result = await remediation._fix_clear_caches({"caches": ["unknown_cache"]}, {})

        assert result.outcome == RemediationOutcome.FAILURE
        assert result.details is not None
        assert "unknown_cache" in result.details["failed"]

    @pytest.mark.asyncio
    @patch("backend.services.alerts.alert_service_degraded")
    async def test_fix_alert_only(
        self, mock_alert: AsyncMock, remediation: AutoRemediation
    ) -> None:
        """Test alert-only fix."""
        mock_alert.return_value = True

        result = await remediation._fix_alert_only(
            {"severity": "high", "escalate": True},
            {"pattern_name": "test_pattern", "error_count": 5},
        )

        assert result.outcome == RemediationOutcome.SUCCESS
        mock_alert.assert_called_once()


class TestGlobalFunctions:
    """Tests for module-level helper functions."""

    @patch("backend.services.auto_remediation._auto_remediation", None)
    def test_get_auto_remediation_creates_singleton(self) -> None:
        """Test singleton pattern for global instance."""
        instance1 = get_auto_remediation()
        instance2 = get_auto_remediation()
        assert instance1 is instance2

    @pytest.mark.asyncio
    @patch("backend.services.auto_remediation.get_auto_remediation")
    async def test_execute_remediation_no_fix(self, mock_get: MagicMock) -> None:
        """Test execute_remediation when no fix configured."""
        mock_remediation = MagicMock()
        mock_remediation.get_fix_for_pattern.return_value = None
        mock_get.return_value = mock_remediation

        result = await execute_remediation(999)

        assert result is None

    @pytest.mark.asyncio
    @patch("backend.services.auto_remediation.get_auto_remediation")
    async def test_execute_remediation_with_fix(self, mock_get: MagicMock) -> None:
        """Test execute_remediation executes and logs."""
        mock_fix = ErrorFix(
            id=1,
            error_pattern_id=1,
            fix_type="alert_only",
            fix_config={},
            priority=1,
            enabled=True,
            success_count=0,
            failure_count=0,
            last_applied_at=None,
        )
        mock_result = RemediationResult(
            outcome=RemediationOutcome.SUCCESS,
            fix_type="alert_only",
            duration_ms=10,
            message="Alert sent",
        )

        mock_remediation = MagicMock()
        mock_remediation.get_fix_for_pattern.return_value = mock_fix
        mock_remediation.execute_fix = AsyncMock(return_value=mock_result)
        mock_remediation.log_remediation = AsyncMock()
        mock_get.return_value = mock_remediation

        result = await execute_remediation(1, context={"test": True})

        assert result is not None
        assert result.outcome == RemediationOutcome.SUCCESS
        mock_remediation.execute_fix.assert_called_once()
        mock_remediation.log_remediation.assert_called_once()
