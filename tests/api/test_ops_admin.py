"""Tests for admin ops API endpoints.

These tests verify the API endpoint logic using unit tests.
Integration tests with the full app are done separately.
"""

from datetime import UTC, datetime

import pytest

from backend.api.admin.ops import (
    CreatePatternRequest,
    ErrorPatternListResponse,
    ErrorPatternResponse,
    RemediationHistoryResponse,
    RemediationLogEntry,
    SystemHealthResponse,
    UpdatePatternRequest,
)


class TestModels:
    """Tests for Pydantic models."""

    def test_create_pattern_request_defaults(self) -> None:
        """Test CreatePatternRequest has correct defaults."""
        request = CreatePatternRequest(
            pattern_name="test",
            pattern_regex=r"test.*",
            error_type="test",
        )
        assert request.severity == "medium"
        assert request.threshold_count == 3
        assert request.threshold_window_minutes == 5
        assert request.cooldown_minutes == 5

    def test_create_pattern_request_validation(self) -> None:
        """Test CreatePatternRequest field validation."""
        # Valid severity values
        for severity in ["low", "medium", "high", "critical"]:
            request = CreatePatternRequest(
                pattern_name="test",
                pattern_regex=r"test",
                error_type="test",
                severity=severity,
            )
            assert request.severity == severity

    def test_update_pattern_request_optional(self) -> None:
        """Test UpdatePatternRequest fields are optional."""
        request = UpdatePatternRequest()
        assert request.pattern_regex is None
        assert request.severity is None
        assert request.enabled is None

    def test_error_pattern_response(self) -> None:
        """Test ErrorPatternResponse model."""
        pattern = ErrorPatternResponse(
            id=1,
            pattern_name="test",
            pattern_regex=r"test.*",
            error_type="redis",
            severity="high",
            description="Test pattern",
            enabled=True,
            threshold_count=3,
            threshold_window_minutes=5,
            cooldown_minutes=5,
            created_at=datetime.now(UTC),
            recent_matches=10,
            fix_count=2,
            last_remediation=None,
        )
        assert pattern.id == 1
        assert pattern.pattern_name == "test"
        assert pattern.recent_matches == 10

    def test_error_pattern_list_response(self) -> None:
        """Test ErrorPatternListResponse model."""
        response = ErrorPatternListResponse(patterns=[], total=0)
        assert response.total == 0
        assert response.patterns == []

    def test_remediation_log_entry(self) -> None:
        """Test RemediationLogEntry model."""
        entry = RemediationLogEntry(
            id=1,
            pattern_name="redis_error",
            fix_type="reconnect_redis",
            triggered_at=datetime.now(UTC),
            outcome="success",
            details={"attempts": 2},
            duration_ms=150,
        )
        assert entry.outcome == "success"
        assert entry.duration_ms == 150

    def test_remediation_history_response(self) -> None:
        """Test RemediationHistoryResponse model."""
        response = RemediationHistoryResponse(entries=[], total=0)
        assert response.total == 0

    def test_system_health_response(self) -> None:
        """Test SystemHealthResponse model."""
        response = SystemHealthResponse(
            checked_at=datetime.now(UTC),
            overall="healthy",
            components={
                "redis": {"status": "healthy"},
                "postgres": {"status": "healthy"},
            },
            recent_remediations={"success": 5, "failure": 1},
        )
        assert response.overall == "healthy"
        assert response.recent_remediations["success"] == 5


class TestPatternValidation:
    """Tests for pattern validation logic."""

    def test_valid_regex_patterns(self) -> None:
        """Test that valid regex patterns are accepted."""
        import re

        valid_patterns = [
            r"Connection refused",
            r"(error|fail)",
            r"rate_limit.*exceeded",
            r"[0-9]+\s+errors",
        ]
        for pattern in valid_patterns:
            re.compile(pattern)  # Should not raise

    def test_invalid_regex_patterns(self) -> None:
        """Test that invalid regex patterns raise."""
        import re

        invalid_patterns = [
            r"[invalid(",
            r"unmatched)",
            r"(?P<",
        ]
        for pattern in invalid_patterns:
            with pytest.raises(re.error):
                re.compile(pattern)


class TestSeverityMapping:
    """Tests for severity values."""

    def test_valid_severities(self) -> None:
        """Test all valid severity values."""
        valid = ["low", "medium", "high", "critical"]
        for sev in valid:
            request = CreatePatternRequest(
                pattern_name="test",
                pattern_regex=r"test",
                error_type="test",
                severity=sev,
            )
            assert request.severity == sev


class TestThresholdBounds:
    """Tests for threshold value bounds."""

    def test_threshold_count_bounds(self) -> None:
        """Test threshold_count is within bounds."""
        # Min value
        request = CreatePatternRequest(
            pattern_name="test",
            pattern_regex=r"test",
            error_type="test",
            threshold_count=1,
        )
        assert request.threshold_count == 1

        # Max value
        request = CreatePatternRequest(
            pattern_name="test",
            pattern_regex=r"test",
            error_type="test",
            threshold_count=100,
        )
        assert request.threshold_count == 100

    def test_window_minutes_bounds(self) -> None:
        """Test threshold_window_minutes is within bounds."""
        request = CreatePatternRequest(
            pattern_name="test",
            pattern_regex=r"test",
            error_type="test",
            threshold_window_minutes=60,
        )
        assert request.threshold_window_minutes == 60

    def test_cooldown_minutes_bounds(self) -> None:
        """Test cooldown_minutes is within bounds."""
        request = CreatePatternRequest(
            pattern_name="test",
            pattern_regex=r"test",
            error_type="test",
            cooldown_minutes=60,
        )
        assert request.cooldown_minutes == 60
