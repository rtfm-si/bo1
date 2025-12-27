"""Tests for meeting bundle purchase and credit management.

Tests the one-time meeting bundle purchase flow:
- Bundle config in PlanConfig
- Purchase bundle endpoint
- Credit crediting via webhook
- Credit decrement on session creation
"""

from unittest.mock import MagicMock, patch

from bo1.billing.config import PlanConfig


class TestMeetingBundleConfig:
    """Tests for meeting bundle configuration."""

    def test_get_meeting_bundle_valid(self):
        """Test getting valid bundle sizes."""
        for size in [1, 3, 5, 9]:
            bundle = PlanConfig.get_meeting_bundle(size)
            assert bundle is not None
            assert bundle.meetings == size
            assert bundle.price_cents > 0

    def test_get_meeting_bundle_invalid(self):
        """Test invalid bundle sizes return None."""
        assert PlanConfig.get_meeting_bundle(0) is None
        assert PlanConfig.get_meeting_bundle(2) is None
        assert PlanConfig.get_meeting_bundle(10) is None
        assert PlanConfig.get_meeting_bundle(-1) is None

    def test_get_all_bundles(self):
        """Test getting all bundles sorted by size."""
        bundles = PlanConfig.get_all_bundles()
        assert len(bundles) == 4
        assert bundles[0].meetings == 1
        assert bundles[1].meetings == 3
        assert bundles[2].meetings == 5
        assert bundles[3].meetings == 9

    def test_bundle_pricing(self):
        """Test bundle prices are correct."""
        bundle_1 = PlanConfig.get_meeting_bundle(1)
        bundle_5 = PlanConfig.get_meeting_bundle(5)
        bundle_9 = PlanConfig.get_meeting_bundle(9)

        assert bundle_1 is not None
        assert bundle_5 is not None
        assert bundle_9 is not None

        assert bundle_1.price_cents == 1000  # £10
        assert bundle_5.price_cents == 5000  # £50
        assert bundle_9.price_cents == 9000  # £90

    @patch.dict("os.environ", {"STRIPE_PRICE_BUNDLE_5": "price_test_123"})
    def test_get_meetings_for_price_id_match(self):
        """Test price ID lookup returns correct meetings."""
        meetings = PlanConfig.get_meetings_for_price_id("price_test_123")
        assert meetings == 5

    def test_get_meetings_for_price_id_no_match(self):
        """Test price ID lookup returns None for unknown ID."""
        meetings = PlanConfig.get_meetings_for_price_id("price_unknown")
        assert meetings is None


class TestMeetingCreditsDecrement:
    """Tests for meeting credit decrement logic."""

    def test_decrement_credit_reduces_count(self):
        """Test that decrementing credits reduces the count."""
        from backend.api.middleware.tier_limits import _decrement_meeting_credit

        # Mock db_session to simulate credit decrement
        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (4,)  # 4 credits remaining after decrement
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            result = _decrement_meeting_credit("test-user-id")

            assert result == 4
            # Verify the UPDATE query was executed
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "UPDATE users" in call_args[0][0]
            assert "meeting_credits = meeting_credits - 1" in call_args[0][0]

    def test_get_meeting_credits(self):
        """Test getting user's meeting credits."""
        from backend.api.middleware.tier_limits import _get_meeting_credits

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (5,)
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            result = _get_meeting_credits("test-user-id")

            assert result == 5


class TestMeetingLimitResult:
    """Tests for MeetingLimitResult with meeting credits."""

    def test_meeting_limit_result_with_credit(self):
        """Test MeetingLimitResult captures meeting credit usage."""
        from datetime import datetime

        from backend.api.middleware.tier_limits import MeetingLimitResult
        from backend.services.usage_tracking import UsageResult

        result = MeetingLimitResult(
            usage=UsageResult(
                allowed=False,
                current=3,
                limit=3,
                remaining=0,
                reset_at=datetime.now(),
            ),
            uses_meeting_credit=True,
            meeting_credits_remaining=4,
        )

        assert result.uses_meeting_credit is True
        assert result.meeting_credits_remaining == 4
        assert result.uses_promo_credit is False

    def test_meeting_limit_result_default_values(self):
        """Test MeetingLimitResult defaults."""
        from backend.api.middleware.tier_limits import MeetingLimitResult
        from backend.services.usage_tracking import UsageResult

        result = MeetingLimitResult(
            usage=UsageResult(
                allowed=True,
                current=1,
                limit=3,
                remaining=2,
                reset_at=None,
            ),
        )

        assert result.uses_meeting_credit is False
        assert result.meeting_credits_remaining == 0
        assert result.uses_promo_credit is False
