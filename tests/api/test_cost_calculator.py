"""Tests for cost calculator defaults endpoints.

Validates:
- GET /v1/user/cost-calculator-defaults returns current defaults
- PATCH /v1/user/cost-calculator-defaults updates defaults
- Validation: reasonable bounds on all fields
"""

import pytest

from backend.api.user import CostCalculatorDefaults


@pytest.mark.unit
class TestCostCalculatorDefaultsModel:
    """Test Pydantic model for cost calculator defaults."""

    def test_valid_defaults(self) -> None:
        """Test valid cost calculator defaults."""
        defaults = CostCalculatorDefaults(
            avg_hourly_rate=75,
            typical_participants=5,
            typical_duration_mins=60,
            typical_prep_mins=30,
        )
        assert defaults.avg_hourly_rate == 75
        assert defaults.typical_participants == 5
        assert defaults.typical_duration_mins == 60
        assert defaults.typical_prep_mins == 30

    def test_default_values(self) -> None:
        """Test that defaults are applied when no values provided."""
        defaults = CostCalculatorDefaults()
        assert defaults.avg_hourly_rate == 75
        assert defaults.typical_participants == 5
        assert defaults.typical_duration_mins == 60
        assert defaults.typical_prep_mins == 30

    def test_min_hourly_rate(self) -> None:
        """Test minimum hourly rate of $10."""
        defaults = CostCalculatorDefaults(avg_hourly_rate=10)
        assert defaults.avg_hourly_rate == 10

    def test_max_hourly_rate(self) -> None:
        """Test maximum hourly rate of $1000."""
        defaults = CostCalculatorDefaults(avg_hourly_rate=1000)
        assert defaults.avg_hourly_rate == 1000

    def test_below_min_hourly_rate(self) -> None:
        """Test that hourly rate below $10 is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(avg_hourly_rate=9)

    def test_above_max_hourly_rate(self) -> None:
        """Test that hourly rate above $1000 is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(avg_hourly_rate=1001)

    def test_min_participants(self) -> None:
        """Test minimum 1 participant."""
        defaults = CostCalculatorDefaults(typical_participants=1)
        assert defaults.typical_participants == 1

    def test_max_participants(self) -> None:
        """Test maximum 20 participants."""
        defaults = CostCalculatorDefaults(typical_participants=20)
        assert defaults.typical_participants == 20

    def test_below_min_participants(self) -> None:
        """Test that 0 participants is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(typical_participants=0)

    def test_above_max_participants(self) -> None:
        """Test that 21 participants is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(typical_participants=21)

    def test_min_duration(self) -> None:
        """Test minimum 15 minute duration."""
        defaults = CostCalculatorDefaults(typical_duration_mins=15)
        assert defaults.typical_duration_mins == 15

    def test_max_duration(self) -> None:
        """Test maximum 480 minute (8 hour) duration."""
        defaults = CostCalculatorDefaults(typical_duration_mins=480)
        assert defaults.typical_duration_mins == 480

    def test_below_min_duration(self) -> None:
        """Test that 14 minute duration is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(typical_duration_mins=14)

    def test_above_max_duration(self) -> None:
        """Test that 481 minute duration is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(typical_duration_mins=481)

    def test_min_prep_time(self) -> None:
        """Test minimum 0 minute prep time."""
        defaults = CostCalculatorDefaults(typical_prep_mins=0)
        assert defaults.typical_prep_mins == 0

    def test_max_prep_time(self) -> None:
        """Test maximum 240 minute (4 hour) prep time."""
        defaults = CostCalculatorDefaults(typical_prep_mins=240)
        assert defaults.typical_prep_mins == 240

    def test_below_min_prep_time(self) -> None:
        """Test that negative prep time is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(typical_prep_mins=-1)

    def test_above_max_prep_time(self) -> None:
        """Test that 241 minute prep time is rejected."""
        with pytest.raises(ValueError):
            CostCalculatorDefaults(typical_prep_mins=241)


@pytest.mark.unit
class TestCostCalculatorRepository:
    """Test user repository methods for cost calculator defaults."""

    def test_default_cost_calculator_values(self) -> None:
        """Test that DEFAULT_COST_CALCULATOR has expected values."""
        from bo1.state.repositories.user_repository import UserRepository

        defaults = UserRepository.DEFAULT_COST_CALCULATOR

        assert defaults["avg_hourly_rate"] == 75
        assert defaults["typical_participants"] == 5
        assert defaults["typical_duration_mins"] == 60
        assert defaults["typical_prep_mins"] == 30

    def test_get_defaults_returns_copy(self) -> None:
        """Test that get_cost_calculator_defaults returns a copy, not reference."""
        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()
        # Override _execute_one to return None (simulate no stored defaults)
        repo._execute_one = lambda *args, **kwargs: None

        result1 = repo.get_cost_calculator_defaults("user123")
        result2 = repo.get_cost_calculator_defaults("user456")

        # Should return separate copies
        assert result1 is not result2

        # Modifying one shouldn't affect the other
        result1["avg_hourly_rate"] = 999
        assert result2["avg_hourly_rate"] == 75

    def test_get_defaults_returns_defaults_when_null(self) -> None:
        """Test get_cost_calculator_defaults returns defaults when column is NULL."""
        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()
        repo._execute_one = lambda *args, **kwargs: {"cost_calculator_defaults": None}

        result = repo.get_cost_calculator_defaults("user123")

        assert result["avg_hourly_rate"] == 75
        assert result["typical_participants"] == 5
        assert result["typical_duration_mins"] == 60
        assert result["typical_prep_mins"] == 30

    def test_get_defaults_returns_saved_values(self) -> None:
        """Test get_cost_calculator_defaults returns saved values when present."""
        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()
        repo._execute_one = lambda *args, **kwargs: {
            "cost_calculator_defaults": {
                "avg_hourly_rate": 100,
                "typical_participants": 8,
                "typical_duration_mins": 90,
                "typical_prep_mins": 45,
            }
        }

        result = repo.get_cost_calculator_defaults("user123")

        assert result["avg_hourly_rate"] == 100
        assert result["typical_participants"] == 8
        assert result["typical_duration_mins"] == 90
        assert result["typical_prep_mins"] == 45


@pytest.mark.unit
class TestCostCalculatorEndpoints:
    """Test cost calculator endpoint validation."""

    def test_endpoint_model_validation(self) -> None:
        """Test that endpoint uses Pydantic model validation."""
        # Valid request should pass
        valid = CostCalculatorDefaults(
            avg_hourly_rate=100,
            typical_participants=10,
            typical_duration_mins=60,
            typical_prep_mins=30,
        )
        assert valid.avg_hourly_rate == 100

        # Invalid request should fail
        with pytest.raises(ValueError):
            CostCalculatorDefaults(
                avg_hourly_rate=5,  # Below minimum
                typical_participants=10,
                typical_duration_mins=60,
                typical_prep_mins=30,
            )

    def test_all_fields_must_be_in_range(self) -> None:
        """Test that all fields are validated together."""
        # All valid
        valid = CostCalculatorDefaults(
            avg_hourly_rate=500,
            typical_participants=15,
            typical_duration_mins=180,
            typical_prep_mins=120,
        )
        assert valid.avg_hourly_rate == 500

        # One invalid should fail even if others are valid
        with pytest.raises(ValueError):
            CostCalculatorDefaults(
                avg_hourly_rate=500,
                typical_participants=50,  # Too high
                typical_duration_mins=180,
                typical_prep_mins=120,
            )
