"""Tests for action failure detector service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from backend.services.action_failure_detector import (
    ActionFailureDetector,
    get_action_failure_detector,
)


@pytest.fixture
def detector():
    """Create a fresh detector instance."""
    return ActionFailureDetector()


class TestFailureRateCalculation:
    """Tests for failure rate calculation."""

    def test_zero_failure_rate_no_actions(self, detector):
        """Test 0% failure rate when no actions exist."""
        with patch.object(detector, "_get_failed_actions", return_value=[]):
            with patch.object(detector, "_get_total_action_count", return_value=0):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.failure_rate == 0.0
        assert summary.total_actions == 0
        assert summary.failed_actions == 0
        assert summary.patterns == []

    def test_zero_failure_rate_all_completed(self, detector):
        """Test 0% failure rate when all actions completed."""
        with patch.object(detector, "_get_failed_actions", return_value=[]):
            with patch.object(detector, "_get_total_action_count", return_value=10):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.failure_rate == 0.0
        assert summary.total_actions == 10
        assert summary.failed_actions == 0

    def test_fifty_percent_failure_rate(self, detector):
        """Test 50% failure rate calculation."""
        failed_actions = [
            {
                "id": f"action-{i}",
                "title": f"Failed Action {i}",
                "project_id": None,
                "project_name": None,
                "status": "cancelled",
                "priority": "medium",
                "cancellation_reason": "Too complex",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "scope_creep",
                "tags": [],
            }
            for i in range(5)
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=10):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.failure_rate == 0.5
        assert summary.total_actions == 10
        assert summary.failed_actions == 5

    def test_hundred_percent_failure_rate(self, detector):
        """Test 100% failure rate calculation."""
        failed_actions = [
            {
                "id": f"action-{i}",
                "title": f"Failed Action {i}",
                "project_id": None,
                "project_name": None,
                "status": "cancelled",
                "priority": "high",
                "cancellation_reason": "Blocked",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "blocker",
                "tags": [],
            }
            for i in range(5)
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=5):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.failure_rate == 1.0
        assert summary.total_actions == 5
        assert summary.failed_actions == 5


class TestTimeWindowFiltering:
    """Tests for time window filtering."""

    def test_seven_day_window(self, detector):
        """Test 7-day window filtering."""
        # The cutoff calculation happens in detect_failure_patterns
        with patch.object(detector, "_get_failed_actions") as mock_get_failed:
            with patch.object(detector, "_get_total_action_count") as mock_get_total:
                mock_get_failed.return_value = []
                mock_get_total.return_value = 0

                detector.detect_failure_patterns("user-1", days=7)

                # Verify the cutoff was calculated for 7 days ago
                call_args = mock_get_failed.call_args
                user_id, cutoff = call_args[0]
                expected_cutoff = datetime.now(UTC) - timedelta(days=7)

                # Check within 1 second tolerance
                assert abs((cutoff - expected_cutoff).total_seconds()) < 1

    def test_thirty_day_window(self, detector):
        """Test 30-day window filtering (default)."""
        with patch.object(detector, "_get_failed_actions") as mock_get_failed:
            with patch.object(detector, "_get_total_action_count") as mock_get_total:
                mock_get_failed.return_value = []
                mock_get_total.return_value = 0

                detector.detect_failure_patterns("user-1", days=30)

                call_args = mock_get_failed.call_args
                user_id, cutoff = call_args[0]
                expected_cutoff = datetime.now(UTC) - timedelta(days=30)

                assert abs((cutoff - expected_cutoff).total_seconds()) < 1


class TestPatternGroupingByProject:
    """Tests for grouping patterns by project."""

    def test_group_by_project(self, detector):
        """Test patterns grouped by project name."""
        failed_actions = [
            {
                "id": "action-1",
                "title": "Failed Action 1",
                "project_id": "proj-1",
                "project_name": "Project Alpha",
                "status": "cancelled",
                "priority": "medium",
                "cancellation_reason": "Too complex",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "scope_creep",
                "tags": [],
            },
            {
                "id": "action-2",
                "title": "Failed Action 2",
                "project_id": "proj-1",
                "project_name": "Project Alpha",
                "status": "cancelled",
                "priority": "medium",
                "cancellation_reason": "Resource unavailable",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "blocker",
                "tags": [],
            },
            {
                "id": "action-3",
                "title": "Failed Action 3",
                "project_id": "proj-2",
                "project_name": "Project Beta",
                "status": "cancelled",
                "priority": "high",
                "cancellation_reason": "Dependency issue",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "dependency",
                "tags": [],
            },
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=10):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.by_project["Project Alpha"] == 2
        assert summary.by_project["Project Beta"] == 1

    def test_group_no_project(self, detector):
        """Test patterns with no project assigned."""
        failed_actions = [
            {
                "id": "action-1",
                "title": "Orphan Action",
                "project_id": None,
                "project_name": None,
                "status": "cancelled",
                "priority": "low",
                "cancellation_reason": "Changed priorities",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "unknown",
                "tags": [],
            },
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=5):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.by_project["No Project"] == 1


class TestPatternGroupingByCategory:
    """Tests for grouping patterns by failure category."""

    def test_group_by_category(self, detector):
        """Test patterns grouped by failure category."""
        failed_actions = [
            {
                "id": "action-1",
                "title": "Blocked action",
                "project_id": None,
                "project_name": None,
                "status": "blocked",
                "priority": "medium",
                "cancellation_reason": None,
                "cancelled_at": None,
                "blocking_reason": "Waiting for API",
                "blocked_at": datetime.now(UTC),
                "failure_reason_category": "blocker",
                "tags": [],
            },
            {
                "id": "action-2",
                "title": "Scope creep",
                "project_id": None,
                "project_name": None,
                "status": "cancelled",
                "priority": "medium",
                "cancellation_reason": "Grew too large",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "scope_creep",
                "tags": [],
            },
            {
                "id": "action-3",
                "title": "Dependency fail",
                "project_id": None,
                "project_name": None,
                "status": "cancelled",
                "priority": "medium",
                "cancellation_reason": "Upstream cancelled",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "dependency",
                "tags": [],
            },
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=10):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.by_category["blocker"] == 1
        assert summary.by_category["scope_creep"] == 1
        assert summary.by_category["dependency"] == 1

    def test_unknown_category_fallback(self, detector):
        """Test fallback to 'unknown' when category is None."""
        failed_actions = [
            {
                "id": "action-1",
                "title": "Mystery failure",
                "project_id": None,
                "project_name": None,
                "status": "cancelled",
                "priority": "medium",
                "cancellation_reason": "Just didn't work",
                "cancelled_at": datetime.now(UTC),
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": None,
                "tags": [],
            },
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=5):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert summary.by_category["unknown"] == 1


class TestEmptyAndEdgeCases:
    """Tests for empty and edge cases."""

    def test_empty_user_no_actions(self, detector):
        """Test user with no actions returns empty patterns."""
        with patch.object(detector, "_get_failed_actions", return_value=[]):
            with patch.object(detector, "_get_total_action_count", return_value=0):
                summary = detector.detect_failure_patterns("new-user", days=30)

        assert summary.patterns == []
        assert summary.failure_rate == 0.0
        assert summary.by_project == {}
        assert summary.by_category == {}

    def test_min_failures_parameter(self, detector):
        """Test min_failures parameter is passed correctly."""
        with patch.object(detector, "_get_failed_actions", return_value=[]):
            with patch.object(detector, "_get_total_action_count", return_value=0):
                summary = detector.detect_failure_patterns("user-1", days=30, min_failures=5)

        # min_failures doesn't affect detection, only API filtering
        assert summary.failed_actions == 0

    def test_period_days_in_summary(self, detector):
        """Test period_days is correctly set in summary."""
        with patch.object(detector, "_get_failed_actions", return_value=[]):
            with patch.object(detector, "_get_total_action_count", return_value=0):
                summary = detector.detect_failure_patterns("user-1", days=45)

        assert summary.period_days == 45


class TestPatternDataExtraction:
    """Tests for correct extraction of pattern data."""

    def test_cancelled_action_pattern(self, detector):
        """Test cancelled action creates correct pattern."""
        cancelled_at = datetime.now(UTC)
        failed_actions = [
            {
                "id": "action-123",
                "title": "Build feature X",
                "project_id": "proj-abc",
                "project_name": "Core Product",
                "status": "cancelled",
                "priority": "high",
                "cancellation_reason": "Requirements changed",
                "cancelled_at": cancelled_at,
                "blocking_reason": None,
                "blocked_at": None,
                "failure_reason_category": "scope_creep",
                "tags": ["backend", "api"],
            },
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=5):
                summary = detector.detect_failure_patterns("user-1", days=30)

        assert len(summary.patterns) == 1
        pattern = summary.patterns[0]
        assert pattern.action_id == "action-123"
        assert pattern.title == "Build feature X"
        assert pattern.project_name == "Core Product"
        assert pattern.status == "cancelled"
        assert pattern.priority == "high"
        assert pattern.failure_reason == "Requirements changed"
        assert pattern.failure_category == "scope_creep"
        assert pattern.tags == ["backend", "api"]

    def test_blocked_action_pattern(self, detector):
        """Test blocked action creates correct pattern."""
        blocked_at = datetime.now(UTC)
        failed_actions = [
            {
                "id": "action-456",
                "title": "Deploy to prod",
                "project_id": None,
                "project_name": None,
                "status": "blocked",
                "priority": "critical",
                "cancellation_reason": None,
                "cancelled_at": None,
                "blocking_reason": "CI/CD pipeline broken",
                "blocked_at": blocked_at,
                "failure_reason_category": "blocker",
                "tags": [],
            },
        ]

        with patch.object(detector, "_get_failed_actions", return_value=failed_actions):
            with patch.object(detector, "_get_total_action_count", return_value=3):
                summary = detector.detect_failure_patterns("user-1", days=30)

        pattern = summary.patterns[0]
        assert pattern.status == "blocked"
        assert pattern.failure_reason == "CI/CD pipeline broken"


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_detector_returns_same_instance(self):
        """Test singleton returns same instance."""
        detector1 = get_action_failure_detector()
        detector2 = get_action_failure_detector()
        assert detector1 is detector2

    def test_detector_is_correct_type(self):
        """Test singleton returns correct type."""
        detector = get_action_failure_detector()
        assert isinstance(detector, ActionFailureDetector)
