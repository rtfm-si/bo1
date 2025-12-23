"""Tests for Project model roundtrip serialization."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from bo1.models import Project, ProjectStatus


class TestProjectRoundtrip:
    """Test Project model serialization roundtrips."""

    @pytest.fixture
    def sample_project_dict(self) -> dict:
        """Realistic Project data matching DB schema."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "user_test_123",
            "name": "Q1 Marketing Campaign",
            "description": "Launch new product marketing initiative",
            "status": "active",
            "target_start_date": date(2025, 1, 1),
            "target_end_date": date(2025, 3, 31),
            "estimated_start_date": date(2025, 1, 5),
            "estimated_end_date": date(2025, 3, 25),
            "actual_start_date": datetime(2025, 1, 5, 9, 0, 0, tzinfo=UTC),
            "actual_end_date": None,
            "progress_percent": 45,
            "total_actions": 20,
            "completed_actions": 9,
            "color": "#3B82F6",
            "icon": "rocket",
            "workspace_id": "456e7890-e89b-12d3-a456-426614174000",
            "version": 1,
            "source_project_id": None,
            "created_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2025, 1, 20, 14, 30, 0, tzinfo=UTC),
        }

    def test_project_roundtrip_serialization(self, sample_project_dict: dict) -> None:
        """Project -> JSON -> Project preserves all fields."""
        project = Project.from_db_row(sample_project_dict)

        json_str = project.model_dump_json()
        restored = Project.model_validate_json(json_str)

        assert restored.id == project.id
        assert restored.user_id == project.user_id
        assert restored.name == project.name
        assert restored.description == project.description
        assert restored.status == project.status
        assert restored.progress_percent == project.progress_percent
        assert restored.total_actions == project.total_actions
        assert restored.completed_actions == project.completed_actions

    def test_project_from_db_row_mapping(self, sample_project_dict: dict) -> None:
        """from_db_row() correctly maps all DB columns."""
        project = Project.from_db_row(sample_project_dict)

        assert project.id == sample_project_dict["id"]
        assert project.user_id == sample_project_dict["user_id"]
        assert project.name == sample_project_dict["name"]
        assert project.description == sample_project_dict["description"]
        assert project.status == ProjectStatus.ACTIVE
        assert project.progress_percent == 45
        assert project.total_actions == 20
        assert project.completed_actions == 9

    def test_project_from_db_row_with_enum_status(self) -> None:
        """from_db_row() handles ProjectStatus enum correctly."""
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "name": "Test Project",
            "status": ProjectStatus.COMPLETED,  # Already enum
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        project = Project.from_db_row(row)
        assert project.status == ProjectStatus.COMPLETED

    def test_project_status_enum_values(self) -> None:
        """ProjectStatus enum has all expected values."""
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.PAUSED.value == "paused"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.ARCHIVED.value == "archived"

    def test_project_progress_percent_bounds(self) -> None:
        """Progress percent validates 0-100 range."""
        # Valid progress
        project = Project(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            name="Test",
            progress_percent=50,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert project.progress_percent == 50

        # Invalid progress (too high)
        with pytest.raises(ValueError):
            Project(
                id="123e4567-e89b-12d3-a456-426614174000",
                user_id="u1",
                name="Test",
                progress_percent=101,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        # Invalid progress (negative)
        with pytest.raises(ValueError):
            Project(
                id="123e4567-e89b-12d3-a456-426614174000",
                user_id="u1",
                name="Test",
                progress_percent=-1,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

    def test_project_version_defaults(self) -> None:
        """Version defaults to 1."""
        project = Project(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            name="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert project.version == 1
        assert project.source_project_id is None

    def test_project_optional_fields_none_safe(self) -> None:
        """Optional fields handle None correctly."""
        project = Project(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            name="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert project.description is None
        assert project.target_start_date is None
        assert project.target_end_date is None
        assert project.actual_start_date is None
        assert project.actual_end_date is None
        assert project.color is None
        assert project.icon is None
        assert project.workspace_id is None
        assert project.source_project_id is None

    def test_project_from_db_row_uuid_handling(self) -> None:
        """from_db_row() handles UUID objects correctly."""
        row = {
            "id": UUID("123e4567-e89b-12d3-a456-426614174000"),
            "user_id": "u1",
            "name": "Test",
            "workspace_id": UUID("456e7890-e89b-12d3-a456-426614174000"),
            "source_project_id": UUID("789e0123-e89b-12d3-a456-426614174000"),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        project = Project.from_db_row(row)
        assert project.id == "123e4567-e89b-12d3-a456-426614174000"
        assert project.workspace_id == "456e7890-e89b-12d3-a456-426614174000"
        assert project.source_project_id == "789e0123-e89b-12d3-a456-426614174000"

    def test_project_versioning_fields(self) -> None:
        """Versioning fields map correctly."""
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "name": "Test v2",
            "version": 2,
            "source_project_id": "456e7890-e89b-12d3-a456-426614174000",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        project = Project.from_db_row(row)
        assert project.version == 2
        assert project.source_project_id == "456e7890-e89b-12d3-a456-426614174000"

    def test_project_date_fields_mapping(self) -> None:
        """Date and datetime fields map correctly."""
        target_start = date(2025, 1, 1)
        target_end = date(2025, 3, 31)
        actual_start = datetime(2025, 1, 5, 9, 0, 0, tzinfo=UTC)

        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "name": "Test",
            "target_start_date": target_start,
            "target_end_date": target_end,
            "actual_start_date": actual_start,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        project = Project.from_db_row(row)
        assert project.target_start_date == target_start
        assert project.target_end_date == target_end
        assert project.actual_start_date == actual_start

    def test_project_defaults_match_db(self) -> None:
        """Verify Project defaults match DB server_default values."""
        project = Project(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            name="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # DB defaults
        assert project.status == ProjectStatus.ACTIVE
        assert project.progress_percent == 0
        assert project.total_actions == 0
        assert project.completed_actions == 0
        assert project.version == 1

    def test_project_visual_customization(self) -> None:
        """Visual customization fields map correctly."""
        project = Project(
            id="123e4567-e89b-12d3-a456-426614174000",
            user_id="u1",
            name="Test",
            color="#FF5733",
            icon="star",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert project.color == "#FF5733"
        assert project.icon == "star"

    def test_project_action_counts(self) -> None:
        """Action count fields map correctly."""
        row = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "u1",
            "name": "Test",
            "total_actions": 15,
            "completed_actions": 7,
            "progress_percent": 47,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        project = Project.from_db_row(row)
        assert project.total_actions == 15
        assert project.completed_actions == 7
        assert project.progress_percent == 47
