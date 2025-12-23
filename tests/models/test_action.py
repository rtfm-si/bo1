"""Tests for Action model roundtrip serialization."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from bo1.models import Action, ActionCategory, ActionPriority, ActionStatus
from bo1.models.action import FailureReasonCategory


class TestActionRoundtrip:
    """Test Action model serialization roundtrips."""

    @pytest.fixture
    def sample_action_dict(self) -> dict:
        """Realistic Action data matching DB schema."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "user_test_123",
            "source_session_id": "bo1_abc123",
            "title": "Implement user authentication",
            "description": "Add OAuth login flow with Google and GitHub providers",
            "what_and_how": [
                "Configure OAuth providers",
                "Add login UI",
                "Set up session management",
            ],
            "success_criteria": [
                "Users can log in with Google",
                "Session persists across page reloads",
            ],
            "kill_criteria": ["Budget exceeds $5000", "Timeline extends past Q1"],
            "status": "in_progress",
            "priority": "high",
            "category": "implementation",
            "sort_order": 1,
            "confidence": Decimal("0.85"),
            "source_section": "recommendations",
            "sub_problem_index": 0,
            "timeline": "2 weeks",
            "estimated_duration_days": 10,
            "target_start_date": date(2025, 1, 15),
            "target_end_date": date(2025, 1, 29),
            "estimated_start_date": date(2025, 1, 15),
            "estimated_end_date": date(2025, 1, 25),
            "actual_start_date": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            "actual_end_date": None,
            "blocking_reason": None,
            "blocked_at": None,
            "auto_unblock": False,
            "project_id": "456e7890-e89b-12d3-a456-426614174000",
            "replan_session_id": None,
            "replan_requested_at": None,
            "replanning_reason": None,
            "failure_reason_category": None,
            "replan_suggested_at": None,
            "replan_session_created_id": None,
            "closure_reason": None,
            "replanned_from_id": None,
            "deleted_at": None,
            "created_at": datetime(2025, 1, 10, 9, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2025, 1, 15, 11, 30, 0, tzinfo=UTC),
        }

    def test_action_roundtrip_serialization(self, sample_action_dict: dict) -> None:
        """Action -> JSON -> Action preserves all fields."""
        action = Action.from_db_row(sample_action_dict)

        json_str = action.model_dump_json()
        restored = Action.model_validate_json(json_str)

        assert restored.id == action.id
        assert restored.user_id == action.user_id
        assert restored.source_session_id == action.source_session_id
        assert restored.title == action.title
        assert restored.description == action.description
        assert restored.what_and_how == action.what_and_how
        assert restored.success_criteria == action.success_criteria
        assert restored.kill_criteria == action.kill_criteria
        assert restored.status == action.status
        assert restored.priority == action.priority
        assert restored.category == action.category

    def test_action_from_db_row_mapping(self, sample_action_dict: dict) -> None:
        """from_db_row() correctly maps all DB columns."""
        action = Action.from_db_row(sample_action_dict)

        assert action.id == sample_action_dict["id"]
        assert action.user_id == sample_action_dict["user_id"]
        assert action.source_session_id == sample_action_dict["source_session_id"]
        assert action.title == sample_action_dict["title"]
        assert action.description == sample_action_dict["description"]
        assert action.status == ActionStatus.IN_PROGRESS
        assert action.priority == ActionPriority.HIGH
        assert action.category == ActionCategory.IMPLEMENTATION

    def test_action_from_db_row_with_enum_status(self) -> None:
        """from_db_row() handles ActionStatus enum correctly."""
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "source_session_id": "bo1_test",
            "title": "Test action",
            "description": "Test description",
            "status": ActionStatus.DONE,  # Already enum
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        action = Action.from_db_row(row)
        assert action.status == ActionStatus.DONE

    def test_action_status_enum_values(self) -> None:
        """ActionStatus enum has all expected values."""
        assert ActionStatus.TODO.value == "todo"
        assert ActionStatus.IN_PROGRESS.value == "in_progress"
        assert ActionStatus.BLOCKED.value == "blocked"
        assert ActionStatus.IN_REVIEW.value == "in_review"
        assert ActionStatus.DONE.value == "done"
        assert ActionStatus.CANCELLED.value == "cancelled"

    def test_action_priority_enum_values(self) -> None:
        """ActionPriority enum has all expected values."""
        assert ActionPriority.HIGH.value == "high"
        assert ActionPriority.MEDIUM.value == "medium"
        assert ActionPriority.LOW.value == "low"

    def test_action_category_enum_values(self) -> None:
        """ActionCategory enum has all expected values."""
        assert ActionCategory.IMPLEMENTATION.value == "implementation"
        assert ActionCategory.RESEARCH.value == "research"
        assert ActionCategory.DECISION.value == "decision"
        assert ActionCategory.COMMUNICATION.value == "communication"

    def test_action_optional_fields_none_safe(self) -> None:
        """Optional fields handle None correctly."""
        action = Action(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            source_session_id="bo1_test",
            title="Test",
            description="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert action.project_id is None
        assert action.blocking_reason is None
        assert action.target_start_date is None
        assert action.actual_start_date is None
        assert action.replan_session_id is None
        assert action.closure_reason is None
        assert action.deleted_at is None

    def test_action_confidence_range(self) -> None:
        """Confidence field validates range 0.0-1.0."""
        # Valid confidence
        action = Action(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            source_session_id="bo1_test",
            title="Test",
            description="Test",
            confidence=Decimal("0.85"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert action.confidence == Decimal("0.85")

        # Invalid confidence (too high)
        with pytest.raises(ValueError):
            Action(
                id="123e4567-e89b-12d3-a456-426614174000",
                user_id="u1",
                source_session_id="bo1_test",
                title="Test",
                description="Test",
                confidence=Decimal("1.5"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

    def test_action_array_fields_none_to_empty_list(self) -> None:
        """Array fields convert None to empty list."""
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "source_session_id": "bo1_test",
            "title": "Test",
            "description": "Test",
            "what_and_how": None,
            "success_criteria": None,
            "kill_criteria": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        action = Action.from_db_row(row)
        assert action.what_and_how == []
        assert action.success_criteria == []
        assert action.kill_criteria == []

    def test_action_from_db_row_uuid_handling(self) -> None:
        """from_db_row() handles UUID objects correctly."""
        row = {
            "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
            "user_id": "u1",
            "source_session_id": "bo1_test",
            "title": "Test",
            "description": "Test",
            "project_id": UUID("456e7890-e89b-12d3-a456-426614174000"),
            "replanned_from_id": UUID("789e0123-e89b-12d3-a456-426614174000"),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        action = Action.from_db_row(row)
        assert action.id == "123e4567-e89b-12d3-a456-426614174000"
        assert action.project_id == "456e7890-e89b-12d3-a456-426614174000"
        assert action.replanned_from_id == "789e0123-e89b-12d3-a456-426614174000"

    def test_action_blocked_status_with_reason(self) -> None:
        """Blocked action has blocking_reason and blocked_at."""
        blocked_at = datetime.now(UTC)
        action = Action(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            source_session_id="bo1_test",
            title="Test",
            description="Test",
            status=ActionStatus.BLOCKED,
            blocking_reason="Waiting for API access",
            blocked_at=blocked_at,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert action.status == ActionStatus.BLOCKED
        assert action.blocking_reason == "Waiting for API access"
        assert action.blocked_at == blocked_at

    def test_action_replanning_fields(self) -> None:
        """Replanning fields map correctly."""
        replan_requested_at = datetime.now(UTC)
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "source_session_id": "bo1_test",
            "title": "Test",
            "description": "Test",
            "replan_session_id": "bo1_replan_123",
            "replan_requested_at": replan_requested_at,
            "replanning_reason": "Scope changed significantly",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        action = Action.from_db_row(row)
        assert action.replan_session_id == "bo1_replan_123"
        assert action.replan_requested_at == replan_requested_at
        assert action.replanning_reason == "Scope changed significantly"

    def test_action_failure_reason_category_enum(self) -> None:
        """FailureReasonCategory enum maps correctly."""
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "source_session_id": "bo1_test",
            "title": "Test",
            "description": "Test",
            "failure_reason_category": "blocker",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        action = Action.from_db_row(row)
        assert action.failure_reason_category == FailureReasonCategory.BLOCKER

    def test_action_date_fields_mapping(self) -> None:
        """Date and datetime fields map correctly."""
        target_start = date(2025, 1, 15)
        target_end = date(2025, 1, 29)
        actual_start = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)

        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "source_session_id": "bo1_test",
            "title": "Test",
            "description": "Test",
            "target_start_date": target_start,
            "target_end_date": target_end,
            "actual_start_date": actual_start,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        action = Action.from_db_row(row)
        assert action.target_start_date == target_start
        assert action.target_end_date == target_end
        assert action.actual_start_date == actual_start

    def test_action_defaults_match_db(self) -> None:
        """Verify Action defaults match DB server_default values."""
        action = Action(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            source_session_id="bo1_test",
            title="Test",
            description="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # DB defaults
        assert action.status == ActionStatus.TODO
        assert action.priority == ActionPriority.MEDIUM
        assert action.category == ActionCategory.IMPLEMENTATION
        assert action.sort_order == 0
        assert action.confidence == Decimal("0.0")
        assert action.auto_unblock is False
        assert action.what_and_how == []
        assert action.success_criteria == []
        assert action.kill_criteria == []
