"""Tests for ContributionMessage model and ContributionStatus enum."""

from datetime import datetime

import pytest

from bo1.models.state import (
    ContributionMessage,
    ContributionStatus,
    DeliberationPhaseType,
)


class TestContributionStatusEnum:
    """Test ContributionStatus enum values."""

    def test_status_values_exist(self) -> None:
        """All expected status values are defined."""
        assert ContributionStatus.IN_FLIGHT.value == "in_flight"
        assert ContributionStatus.COMMITTED.value == "committed"
        assert ContributionStatus.ROLLED_BACK.value == "rolled_back"

    def test_status_enum_count(self) -> None:
        """Exactly 3 status values exist."""
        assert len(ContributionStatus) == 3

    def test_status_from_string(self) -> None:
        """Status enum can be constructed from string value."""
        assert ContributionStatus("in_flight") == ContributionStatus.IN_FLIGHT
        assert ContributionStatus("committed") == ContributionStatus.COMMITTED
        assert ContributionStatus("rolled_back") == ContributionStatus.ROLLED_BACK

    def test_status_invalid_value_raises(self) -> None:
        """Invalid status string raises ValueError."""
        with pytest.raises(ValueError):
            ContributionStatus("invalid_status")


class TestContributionMessageDefaultValues:
    """Test ContributionMessage default values for new fields."""

    def test_user_id_defaults_to_none(self) -> None:
        """user_id defaults to None."""
        msg = ContributionMessage(
            persona_code="ceo",
            persona_name="CEO Expert",
            content="Test content",
            round_number=0,
        )
        assert msg.user_id is None

    def test_status_defaults_to_committed(self) -> None:
        """status defaults to COMMITTED."""
        msg = ContributionMessage(
            persona_code="ceo",
            persona_name="CEO Expert",
            content="Test content",
            round_number=0,
        )
        assert msg.status == ContributionStatus.COMMITTED

    def test_can_set_user_id(self) -> None:
        """user_id can be set explicitly."""
        msg = ContributionMessage(
            persona_code="ceo",
            persona_name="CEO Expert",
            content="Test content",
            round_number=0,
            user_id="user_123",
        )
        assert msg.user_id == "user_123"

    def test_can_set_status(self) -> None:
        """status can be set explicitly."""
        msg = ContributionMessage(
            persona_code="ceo",
            persona_name="CEO Expert",
            content="Test content",
            round_number=0,
            status=ContributionStatus.IN_FLIGHT,
        )
        assert msg.status == ContributionStatus.IN_FLIGHT


class TestFromDbRowWithUserIdAndStatus:
    """Test from_db_row() maps user_id and status correctly."""

    def test_maps_user_id_from_row(self) -> None:
        """user_id is mapped from database row."""
        row = {
            "id": 1,
            "session_id": "bo1_123",
            "user_id": "user_456",
            "status": "committed",
            "persona_code": "ceo",
            "persona_name": "CEO Expert",
            "content": "Test content",
            "round_number": 0,
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.user_id == "user_456"

    def test_maps_status_committed(self) -> None:
        """status is mapped from 'committed' string."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
            "status": "committed",
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.status == ContributionStatus.COMMITTED

    def test_maps_status_in_flight(self) -> None:
        """status is mapped from 'in_flight' string."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
            "status": "in_flight",
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.status == ContributionStatus.IN_FLIGHT

    def test_maps_status_rolled_back(self) -> None:
        """status is mapped from 'rolled_back' string."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
            "status": "rolled_back",
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.status == ContributionStatus.ROLLED_BACK

    def test_missing_user_id_defaults_to_none(self) -> None:
        """Missing user_id in row defaults to None."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.user_id is None

    def test_missing_status_defaults_to_committed(self) -> None:
        """Missing status in row defaults to COMMITTED."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.status == ContributionStatus.COMMITTED

    def test_invalid_status_defaults_to_committed(self) -> None:
        """Invalid status string defaults to COMMITTED."""
        row = {
            "persona_code": "ceo",
            "content": "Test content",
            "round_number": 0,
            "status": "invalid_status",
        }
        msg = ContributionMessage.from_db_row(row)
        assert msg.status == ContributionStatus.COMMITTED

    def test_full_row_mapping(self) -> None:
        """All fields are correctly mapped from complete row."""
        now = datetime.now()
        row = {
            "id": 42,
            "session_id": "bo1_session_abc",
            "user_id": "user_xyz",
            "status": "in_flight",
            "persona_code": "growth_hacker",
            "persona_name": "Zara",
            "content": "Focus on product-led growth",
            "round_number": 2,
            "thinking": "Analyzing options...",
            "phase": "challenge",
            "cost": 0.0025,
            "tokens": 350,
            "model": "claude-sonnet-4-20250514",
            "created_at": now,
        }
        msg = ContributionMessage.from_db_row(row)

        assert msg.id == 42
        assert msg.session_id == "bo1_session_abc"
        assert msg.user_id == "user_xyz"
        assert msg.status == ContributionStatus.IN_FLIGHT
        assert msg.persona_code == "growth_hacker"
        assert msg.persona_name == "Zara"
        assert msg.content == "Focus on product-led growth"
        assert msg.round_number == 2
        assert msg.thinking == "Analyzing options..."
        assert msg.phase == DeliberationPhaseType.CHALLENGE
        assert msg.cost == 0.0025
        assert msg.token_count == 350
        assert msg.model == "claude-sonnet-4-20250514"
        assert msg.timestamp == now


class TestContributionMessageJsonSchema:
    """Test JSON schema includes new fields."""

    def test_schema_includes_user_id(self) -> None:
        """JSON schema includes user_id field."""
        schema = ContributionMessage.model_json_schema()
        assert "user_id" in schema["properties"]

    def test_schema_includes_status(self) -> None:
        """JSON schema includes status field."""
        schema = ContributionMessage.model_json_schema()
        assert "status" in schema["properties"]

    def test_status_field_has_enum_ref(self) -> None:
        """status field references ContributionStatus enum."""
        schema = ContributionMessage.model_json_schema()
        status_prop = schema["properties"]["status"]
        # Should reference $defs/ContributionStatus or have enum values
        assert "$ref" in status_prop or "default" in status_prop
