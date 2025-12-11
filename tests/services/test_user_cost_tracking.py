"""Tests for user cost tracking service."""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from backend.services.user_cost_tracking import (
    BudgetCheckResult,
    BudgetStatus,
    UserBudgetSettings,
    UserCostPeriod,
    check_budget_status,
    get_current_period_bounds,
    get_default_limit_for_tier,
    get_top_users_by_cost,
    record_session_cost,
)


class TestGetCurrentPeriodBounds:
    """Tests for get_current_period_bounds."""

    def test_returns_first_and_last_of_month(self) -> None:
        """Test period bounds are month start and end."""
        start, end = get_current_period_bounds()

        today = date.today()
        assert start.day == 1
        assert start.month == today.month
        assert start.year == today.year
        assert end.month == today.month
        # End should be last day of month
        assert (end + timedelta(days=1)).day == 1


class TestGetDefaultLimitForTier:
    """Tests for get_default_limit_for_tier."""

    @patch("bo1.config.get_settings")
    def test_free_tier_returns_config_value(self, mock_settings: MagicMock) -> None:
        """Test free tier uses config value."""
        mock_settings.return_value.cost_limit_free_cents = 500
        assert get_default_limit_for_tier("free") == 500

    @patch("bo1.config.get_settings")
    def test_starter_tier_returns_config_value(self, mock_settings: MagicMock) -> None:
        """Test starter tier uses config value."""
        mock_settings.return_value.cost_limit_starter_cents = 2500
        assert get_default_limit_for_tier("starter") == 2500

    @patch("bo1.config.get_settings")
    def test_pro_tier_returns_config_value(self, mock_settings: MagicMock) -> None:
        """Test pro tier uses config value."""
        mock_settings.return_value.cost_limit_pro_cents = 10000
        assert get_default_limit_for_tier("pro") == 10000

    @patch("bo1.config.get_settings")
    def test_none_tier_defaults_to_free(self, mock_settings: MagicMock) -> None:
        """Test None tier defaults to free."""
        mock_settings.return_value.cost_limit_free_cents = 500
        assert get_default_limit_for_tier(None) == 500

    def test_fallback_when_settings_unavailable(self) -> None:
        """Test fallback values when settings fail."""
        with patch(
            "bo1.config.get_settings",
            side_effect=Exception("Settings unavailable"),
        ):
            assert get_default_limit_for_tier("free") == 500
            assert get_default_limit_for_tier("starter") == 2500
            assert get_default_limit_for_tier("pro") == 10000


class TestRecordSessionCost:
    """Tests for record_session_cost."""

    @patch("backend.services.user_cost_tracking.check_budget_status")
    @patch("backend.services.user_cost_tracking.db_session")
    def test_records_cost_and_returns_period(
        self,
        mock_db: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test cost is recorded and period returned."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "user_id": "user123",
            "period_start": date(2025, 12, 1),
            "period_end": date(2025, 12, 31),
            "total_cost_cents": 150,
            "session_count": 3,
        }
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_connection

        mock_check.return_value = BudgetCheckResult(
            user_id="user123",
            status=BudgetStatus.UNDER,
            current_cost_cents=150,
            limit_cents=500,
            percentage_used=30.0,
            should_alert=False,
            should_block=False,
        )

        period, budget_result = record_session_cost("user123", "session456", 50)

        assert period.user_id == "user123"
        assert period.total_cost_cents == 150
        assert period.session_count == 3
        assert budget_result is None  # No alert needed

    @patch("backend.services.user_cost_tracking.check_budget_status")
    @patch("backend.services.user_cost_tracking.db_session")
    def test_returns_budget_result_when_alert_needed(
        self,
        mock_db: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test budget result returned when threshold crossed."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "user_id": "user123",
            "period_start": date(2025, 12, 1),
            "period_end": date(2025, 12, 31),
            "total_cost_cents": 450,
            "session_count": 5,
        }
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_connection

        mock_check.return_value = BudgetCheckResult(
            user_id="user123",
            status=BudgetStatus.WARNING,
            current_cost_cents=450,
            limit_cents=500,
            percentage_used=90.0,
            should_alert=True,  # Alert needed
            should_block=False,
        )

        period, budget_result = record_session_cost("user123", "session456", 50)

        assert budget_result is not None
        assert budget_result.should_alert is True
        assert budget_result.status == BudgetStatus.WARNING


class TestCheckBudgetStatus:
    """Tests for check_budget_status."""

    @patch("backend.services.user_cost_tracking.get_user_budget_settings")
    @patch("backend.services.user_cost_tracking.get_user_period_cost")
    def test_under_budget_status(
        self,
        mock_period: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test under budget returns correct status."""
        mock_period.return_value = UserCostPeriod(
            user_id="user123",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_cost_cents=100,
            session_count=2,
        )
        mock_settings.return_value = UserBudgetSettings(
            user_id="user123",
            monthly_cost_limit_cents=500,
            alert_threshold_pct=80,
            hard_limit_enabled=False,
            alert_sent_at=None,
        )

        result = check_budget_status("user123")

        assert result.status == BudgetStatus.UNDER
        assert result.percentage_used == 20.0
        assert result.should_alert is False
        assert result.should_block is False

    @patch("backend.services.user_cost_tracking.get_user_budget_settings")
    @patch("backend.services.user_cost_tracking.get_user_period_cost")
    def test_warning_status_triggers_alert(
        self,
        mock_period: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test warning status triggers alert."""
        mock_period.return_value = UserCostPeriod(
            user_id="user123",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_cost_cents=450,
            session_count=5,
        )
        mock_settings.return_value = UserBudgetSettings(
            user_id="user123",
            monthly_cost_limit_cents=500,
            alert_threshold_pct=80,
            hard_limit_enabled=False,
            alert_sent_at=None,
        )

        result = check_budget_status("user123")

        assert result.status == BudgetStatus.WARNING
        assert result.percentage_used == 90.0
        assert result.should_alert is True
        assert result.should_block is False

    @patch("backend.services.user_cost_tracking.get_user_budget_settings")
    @patch("backend.services.user_cost_tracking.get_user_period_cost")
    def test_exceeded_with_hard_limit_blocks(
        self,
        mock_period: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test exceeded + hard limit triggers block."""
        mock_period.return_value = UserCostPeriod(
            user_id="user123",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_cost_cents=600,
            session_count=7,
        )
        mock_settings.return_value = UserBudgetSettings(
            user_id="user123",
            monthly_cost_limit_cents=500,
            alert_threshold_pct=80,
            hard_limit_enabled=True,
            alert_sent_at=None,
        )

        result = check_budget_status("user123")

        assert result.status == BudgetStatus.EXCEEDED
        assert result.percentage_used == 120.0
        assert result.should_alert is True
        assert result.should_block is True

    @patch("backend.services.user_cost_tracking.get_user_budget_settings")
    @patch("backend.services.user_cost_tracking.get_user_period_cost")
    def test_no_limit_returns_under_status(
        self,
        mock_period: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test no limit configured returns under status."""
        mock_period.return_value = UserCostPeriod(
            user_id="user123",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_cost_cents=10000,
            session_count=50,
        )
        mock_settings.return_value = None  # No settings configured

        result = check_budget_status("user123")

        assert result.status == BudgetStatus.UNDER
        assert result.limit_cents is None
        assert result.percentage_used is None
        assert result.should_alert is False
        assert result.should_block is False

    @patch("backend.services.user_cost_tracking.get_user_budget_settings")
    @patch("backend.services.user_cost_tracking.get_user_period_cost")
    def test_already_alerted_does_not_alert_again(
        self,
        mock_period: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test no alert if already alerted this period."""
        mock_period.return_value = UserCostPeriod(
            user_id="user123",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_cost_cents=450,
            session_count=5,
        )
        # Alert was sent today (within current period)
        mock_settings.return_value = UserBudgetSettings(
            user_id="user123",
            monthly_cost_limit_cents=500,
            alert_threshold_pct=80,
            hard_limit_enabled=False,
            alert_sent_at=datetime.now(),
        )

        result = check_budget_status("user123")

        assert result.status == BudgetStatus.WARNING
        assert result.should_alert is False  # Already alerted


class TestGetTopUsersByCost:
    """Tests for get_top_users_by_cost."""

    @patch("backend.services.user_cost_tracking.db_session")
    def test_returns_users_sorted_by_cost(self, mock_db: MagicMock) -> None:
        """Test users returned sorted by cost descending."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "user_id": "user1",
                "period_start": date(2025, 12, 1),
                "period_end": date(2025, 12, 31),
                "total_cost_cents": 1000,
                "session_count": 10,
            },
            {
                "user_id": "user2",
                "period_start": date(2025, 12, 1),
                "period_end": date(2025, 12, 31),
                "total_cost_cents": 500,
                "session_count": 5,
            },
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_connection

        users = get_top_users_by_cost(limit=10)

        assert len(users) == 2
        assert users[0].user_id == "user1"
        assert users[0].total_cost_cents == 1000
        assert users[1].user_id == "user2"
