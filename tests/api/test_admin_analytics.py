"""Tests for admin cost analytics endpoints.

Tests the endpoint logic and admin authorization checks.
"""

from datetime import date

import pytest
from fastapi import HTTPException

from backend.api.models import (
    CostSummaryResponse,
    DailyCostItem,
    DailyCostsResponse,
    UserCostItem,
    UserCostsResponse,
)
from backend.api.utils.auth_helpers import is_admin, require_admin_role
from backend.services.analytics import CostSummary, DailyCost, UserCost


@pytest.mark.unit
class TestAdminAuthorization:
    """Tests for admin authorization checks."""

    def test_is_admin_returns_true_for_admin(self) -> None:
        """Test is_admin returns True for admin user."""
        admin_user = {"user_id": "admin-123", "is_admin": True}
        assert is_admin(admin_user) is True

    def test_is_admin_returns_false_for_non_admin(self) -> None:
        """Test is_admin returns False for regular user."""
        regular_user = {"user_id": "user-456", "is_admin": False}
        assert is_admin(regular_user) is False

    def test_is_admin_returns_false_for_missing_flag(self) -> None:
        """Test is_admin returns False when is_admin not present."""
        user = {"user_id": "user-789"}
        assert is_admin(user) is False

    def test_require_admin_role_raises_for_non_admin(self) -> None:
        """Test require_admin_role raises 403 for non-admin."""
        regular_user = {"user_id": "user-456", "is_admin": False}

        with pytest.raises(HTTPException) as exc_info:
            require_admin_role(regular_user)

        assert exc_info.value.status_code == 403

    def test_require_admin_role_raises_for_none_user(self) -> None:
        """Test require_admin_role raises 401 for None user."""
        with pytest.raises(HTTPException) as exc_info:
            require_admin_role(None)

        assert exc_info.value.status_code == 401


@pytest.mark.unit
class TestCostSummaryResponse:
    """Tests for CostSummaryResponse model."""

    def test_from_cost_summary(self) -> None:
        """Test creating response from service model."""
        summary = CostSummary(
            today=10.0,
            this_week=30.0,
            this_month=60.0,
            all_time=100.0,
            session_count_today=5,
            session_count_week=15,
            session_count_month=30,
            session_count_total=50,
        )

        response = CostSummaryResponse(
            today=summary.today,
            this_week=summary.this_week,
            this_month=summary.this_month,
            all_time=summary.all_time,
            session_count_today=summary.session_count_today,
            session_count_week=summary.session_count_week,
            session_count_month=summary.session_count_month,
            session_count_total=summary.session_count_total,
        )

        assert response.today == 10.0
        assert response.all_time == 100.0
        assert response.session_count_total == 50


@pytest.mark.unit
class TestUserCostsResponse:
    """Tests for UserCostsResponse model."""

    def test_from_user_costs(self) -> None:
        """Test creating response from service models."""
        users = [
            UserCost(user_id="u1", email="a@test.com", total_cost=50.0, session_count=10),
            UserCost(user_id="u2", email="b@test.com", total_cost=30.0, session_count=5),
        ]

        response = UserCostsResponse(
            users=[
                UserCostItem(
                    user_id=u.user_id,
                    email=u.email,
                    total_cost=u.total_cost,
                    session_count=u.session_count,
                )
                for u in users
            ],
            total=3,
            limit=50,
            offset=0,
        )

        assert len(response.users) == 2
        assert response.users[0].user_id == "u1"
        assert response.total == 3


@pytest.mark.unit
class TestDailyCostsResponse:
    """Tests for DailyCostsResponse model."""

    def test_from_daily_costs(self) -> None:
        """Test creating response from service models."""
        daily = [
            DailyCost(date=date(2025, 1, 1), total_cost=10.0, session_count=5),
            DailyCost(date=date(2025, 1, 2), total_cost=15.0, session_count=7),
        ]

        response = DailyCostsResponse(
            days=[
                DailyCostItem(
                    date=d.date.isoformat(),
                    total_cost=d.total_cost,
                    session_count=d.session_count,
                )
                for d in daily
            ],
            start_date="2025-01-01",
            end_date="2025-01-02",
        )

        assert len(response.days) == 2
        assert response.days[0].date == "2025-01-01"
        assert response.days[0].total_cost == 10.0
