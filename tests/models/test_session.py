"""Tests for Session model roundtrip serialization."""

from datetime import UTC, datetime

from bo1.models import Session, SessionStatus


class TestSessionRoundtrip:
    """Test Session model serialization roundtrips."""

    def test_session_roundtrip_serialization(self, sample_session_dict: dict) -> None:
        """Session → JSON → Session preserves all fields."""
        session = Session(**sample_session_dict)

        # Serialize to JSON
        json_str = session.model_dump_json()

        # Deserialize back
        restored = Session.model_validate_json(json_str)

        assert restored.id == session.id
        assert restored.user_id == session.user_id
        assert restored.problem_statement == session.problem_statement
        assert restored.problem_context == session.problem_context
        assert restored.status == session.status
        assert restored.phase == session.phase
        assert restored.total_cost == session.total_cost
        assert restored.round_number == session.round_number
        assert restored.synthesis_text == session.synthesis_text
        assert restored.final_recommendation == session.final_recommendation

    def test_session_from_db_row_mapping(self, sample_session_dict: dict) -> None:
        """from_db_row() correctly maps all DB columns."""
        session = Session.from_db_row(sample_session_dict)

        assert session.id == sample_session_dict["id"]
        assert session.user_id == sample_session_dict["user_id"]
        assert session.problem_statement == sample_session_dict["problem_statement"]
        assert session.problem_context == sample_session_dict["problem_context"]
        assert session.status == SessionStatus.RUNNING
        assert session.phase == sample_session_dict["phase"]
        assert session.total_cost == sample_session_dict["total_cost"]
        assert session.round_number == sample_session_dict["round_number"]
        assert session.created_at == sample_session_dict["created_at"]
        assert session.updated_at == sample_session_dict["updated_at"]

    def test_session_from_db_row_with_enum_status(self) -> None:
        """from_db_row() handles SessionStatus enum correctly."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": SessionStatus.COMPLETED,  # Already enum
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        session = Session.from_db_row(row)
        assert session.status == SessionStatus.COMPLETED

    def test_session_status_enum_serialization(self) -> None:
        """SessionStatus enum round-trips as string value."""
        for status in SessionStatus:
            session = Session(
                id="bo1_test",
                user_id="u1",
                problem_statement="test",
                status=status,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            # Serialize to dict
            data = session.model_dump()
            assert data["status"] == status.value

            # Serialize to JSON and back
            json_str = session.model_dump_json()
            restored = Session.model_validate_json(json_str)
            assert restored.status == status

    def test_session_optional_fields_null(self) -> None:
        """Optional fields serialize correctly when None, required fields have defaults."""
        session = Session(
            id="bo1_test",
            user_id="u1",
            problem_statement="test",
            status=SessionStatus.CREATED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            # Optional fields default to None, required fields have DB-matching defaults
        )

        data = session.model_dump()
        assert data["problem_context"] is None
        # phase, total_cost, round_number now have defaults matching DB server_default
        assert data["phase"] == "problem_decomposition"
        assert data["total_cost"] == 0.0
        assert data["round_number"] == 0
        assert data["synthesis_text"] is None
        assert data["final_recommendation"] is None

        # Roundtrip
        restored = Session.model_validate_json(session.model_dump_json())
        assert restored.problem_context is None
        assert restored.phase == "problem_decomposition"

    def test_session_termination_fields(self) -> None:
        """Termination fields map correctly from DB row."""
        terminated_at = datetime.now(UTC)
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "completed",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "terminated_at": terminated_at,
            "termination_type": "blocker_identified",
            "termination_reason": "Missing critical data",
            "billable_portion": 0.75,
        }
        session = Session.from_db_row(row)
        assert session.terminated_at == terminated_at
        assert session.termination_type == "blocker_identified"
        assert session.termination_reason == "Missing critical data"
        assert session.billable_portion == 0.75

    def test_session_count_fields(self) -> None:
        """Count fields map correctly from DB row."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "running",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "expert_count": 5,
            "contribution_count": 12,
            "focus_area_count": 3,
            "task_count": 8,
        }
        session = Session.from_db_row(row)
        assert session.expert_count == 5
        assert session.contribution_count == 12
        assert session.focus_area_count == 3
        assert session.task_count == 8

    def test_session_count_fields_default_zero(self) -> None:
        """Count fields default to 0 when not present in row."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "created",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        session = Session.from_db_row(row)
        assert session.expert_count == 0
        assert session.contribution_count == 0
        assert session.focus_area_count == 0
        assert session.task_count == 0

    def test_session_termination_fields_optional(self) -> None:
        """Termination fields default to None when not present."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "running",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        session = Session.from_db_row(row)
        assert session.terminated_at is None
        assert session.termination_type is None
        assert session.termination_reason is None
        assert session.billable_portion is None

    def test_session_from_db_row_with_workspace_id(self) -> None:
        """from_db_row() correctly maps workspace_id from DB column."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "running",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "workspace_id": "ws_abc123",
        }
        session = Session.from_db_row(row)
        assert session.workspace_id == "ws_abc123"

    def test_session_from_db_row_without_workspace_id(self) -> None:
        """from_db_row() defaults workspace_id to None when not present."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "running",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        session = Session.from_db_row(row)
        assert session.workspace_id is None

    def test_session_model_schema_includes_workspace_id(self) -> None:
        """workspace_id field appears in JSON schema."""
        schema = Session.model_json_schema()
        assert "workspace_id" in schema["properties"]
        workspace_field = schema["properties"]["workspace_id"]
        assert workspace_field["description"] == "Workspace UUID (None = personal)"

    def test_session_default_values_match_db(self) -> None:
        """Verify Session defaults match DB server_default values."""
        session = Session(
            id="bo1_test",
            user_id="u1",
            problem_statement="test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # DB defaults (from migrations)
        assert session.phase == "problem_decomposition"
        assert session.total_cost == 0.0
        assert session.round_number == 0
        assert session.expert_count == 0
        assert session.contribution_count == 0
        assert session.focus_area_count == 0
        assert session.task_count == 0

    def test_session_from_db_row_with_counts(self) -> None:
        """from_db_row() correctly maps contribution_count and task_count."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "completed",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "contribution_count": 25,
            "task_count": 10,
        }
        session = Session.from_db_row(row)
        assert session.contribution_count == 25
        assert session.task_count == 10

    def test_session_from_db_row_missing_optional(self) -> None:
        """from_db_row() uses correct defaults when optional fields missing."""
        row = {
            "id": "bo1_test",
            "user_id": "u1",
            "problem_statement": "test",
            "status": "created",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            # All optional/defaulted fields missing
        }
        session = Session.from_db_row(row)
        # Required fields with DB-matching defaults
        assert session.phase == "problem_decomposition"
        assert session.total_cost == 0.0
        assert session.round_number == 0
        # Count fields default to 0
        assert session.contribution_count == 0
        assert session.task_count == 0

    def test_session_model_schema_includes_all_count_fields(self) -> None:
        """All count fields appear in JSON schema."""
        schema = Session.model_json_schema()
        assert "expert_count" in schema["properties"]
        assert "contribution_count" in schema["properties"]
        assert "focus_area_count" in schema["properties"]
        assert "task_count" in schema["properties"]
