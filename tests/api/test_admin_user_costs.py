"""Tests for admin user cost tracking endpoints and authorization."""

from datetime import date

import pytest

from backend.api.models import (
    TopUsersCostResponse,
    UpdateBudgetSettingsRequest,
    UserBudgetSettingsItem,
    UserCostDetailResponse,
    UserCostPeriodItem,
)
from backend.services.user_cost_tracking import (
    UserBudgetSettings,
    UserCostPeriod,
)


@pytest.mark.unit
class TestUserCostPeriodItem:
    """Tests for UserCostPeriodItem model."""

    def test_from_service_model(self) -> None:
        """Test creating response from service model."""
        period = UserCostPeriod(
            user_id="user123",
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 31),
            total_cost_cents=1000,
            session_count=10,
        )

        item = UserCostPeriodItem(
            user_id=period.user_id,
            period_start=period.period_start.isoformat(),
            period_end=period.period_end.isoformat(),
            total_cost_cents=period.total_cost_cents,
            session_count=period.session_count,
        )

        assert item.user_id == "user123"
        assert item.period_start == "2025-12-01"
        assert item.period_end == "2025-12-31"
        assert item.total_cost_cents == 1000
        assert item.session_count == 10


@pytest.mark.unit
class TestUserBudgetSettingsItem:
    """Tests for UserBudgetSettingsItem model."""

    def test_from_service_model(self) -> None:
        """Test creating response from service model."""
        settings = UserBudgetSettings(
            user_id="user123",
            monthly_cost_limit_cents=5000,
            alert_threshold_pct=80,
            hard_limit_enabled=True,
            alert_sent_at=None,
        )

        item = UserBudgetSettingsItem(
            user_id=settings.user_id,
            monthly_cost_limit_cents=settings.monthly_cost_limit_cents,
            alert_threshold_pct=settings.alert_threshold_pct,
            hard_limit_enabled=settings.hard_limit_enabled,
        )

        assert item.user_id == "user123"
        assert item.monthly_cost_limit_cents == 5000
        assert item.alert_threshold_pct == 80
        assert item.hard_limit_enabled is True


@pytest.mark.unit
class TestTopUsersCostResponse:
    """Tests for TopUsersCostResponse model."""

    def test_with_users(self) -> None:
        """Test response with users."""
        users = [
            UserCostPeriodItem(
                user_id="user1",
                period_start="2025-12-01",
                period_end="2025-12-31",
                total_cost_cents=1000,
                session_count=10,
            ),
            UserCostPeriodItem(
                user_id="user2",
                period_start="2025-12-01",
                period_end="2025-12-31",
                total_cost_cents=500,
                session_count=5,
            ),
        ]

        response = TopUsersCostResponse(
            period_start="2025-12-01",
            users=users,
        )

        assert response.period_start == "2025-12-01"
        assert len(response.users) == 2
        assert response.users[0].total_cost_cents == 1000


@pytest.mark.unit
class TestUpdateBudgetSettingsRequest:
    """Tests for UpdateBudgetSettingsRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        request = UpdateBudgetSettingsRequest(
            monthly_cost_limit_cents=2000,
            alert_threshold_pct=90,
            hard_limit_enabled=True,
        )

        assert request.monthly_cost_limit_cents == 2000
        assert request.alert_threshold_pct == 90
        assert request.hard_limit_enabled is True

    def test_partial_update(self) -> None:
        """Test partial update with only some fields."""
        request = UpdateBudgetSettingsRequest(
            monthly_cost_limit_cents=3000,
        )

        assert request.monthly_cost_limit_cents == 3000
        assert request.alert_threshold_pct is None
        assert request.hard_limit_enabled is None

    def test_threshold_validation(self) -> None:
        """Test alert_threshold_pct validation (1-100)."""
        # Valid threshold
        request = UpdateBudgetSettingsRequest(alert_threshold_pct=50)
        assert request.alert_threshold_pct == 50

        # Invalid: too high
        with pytest.raises(ValueError):
            UpdateBudgetSettingsRequest(alert_threshold_pct=150)

        # Invalid: too low
        with pytest.raises(ValueError):
            UpdateBudgetSettingsRequest(alert_threshold_pct=0)


@pytest.mark.unit
class TestUserCostDetailResponse:
    """Tests for UserCostDetailResponse model."""

    def test_full_response(self) -> None:
        """Test full response with all fields."""
        response = UserCostDetailResponse(
            user_id="user123",
            email="test@example.com",
            current_period=UserCostPeriodItem(
                user_id="user123",
                period_start="2025-12-01",
                period_end="2025-12-31",
                total_cost_cents=500,
                session_count=5,
            ),
            budget_settings=UserBudgetSettingsItem(
                user_id="user123",
                monthly_cost_limit_cents=1000,
                alert_threshold_pct=80,
                hard_limit_enabled=False,
            ),
            history=[],
        )

        assert response.user_id == "user123"
        assert response.email == "test@example.com"
        assert response.current_period is not None
        assert response.current_period.total_cost_cents == 500
        assert response.budget_settings is not None
        assert response.budget_settings.monthly_cost_limit_cents == 1000

    def test_minimal_response(self) -> None:
        """Test response with no data."""
        response = UserCostDetailResponse(
            user_id="user123",
            email=None,
            current_period=None,
            budget_settings=None,
            history=[],
        )

        assert response.user_id == "user123"
        assert response.email is None
        assert response.current_period is None
        assert response.budget_settings is None
