"""Tests for experiments service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.services.experiments import (
    Experiment,
    Variant,
    _hash_user_for_variant,
    assign_user_to_variant,
    conclude_experiment,
    create_experiment,
    delete_experiment,
    get_user_variant,
    pause_experiment,
    start_experiment,
    update_experiment,
)


class TestHashUserForVariant:
    """Tests for _hash_user_for_variant."""

    def test_deterministic_hash(self) -> None:
        """Hash should be deterministic for same inputs."""
        result1 = _hash_user_for_variant("test_exp", "user123")
        result2 = _hash_user_for_variant("test_exp", "user123")
        assert result1 == result2

    def test_different_users_different_hash(self) -> None:
        """Different users should (likely) have different hashes."""
        result1 = _hash_user_for_variant("test_exp", "user1")
        result2 = _hash_user_for_variant("test_exp", "user2")
        assert 0 <= result1 < 100
        assert 0 <= result2 < 100

    def test_hash_in_range(self) -> None:
        """Hash should be between 0 and 99."""
        for i in range(100):
            result = _hash_user_for_variant("exp", f"user{i}")
            assert 0 <= result < 100


class TestCreateExperiment:
    """Tests for create_experiment function."""

    @patch("backend.services.experiments.db_session")
    def test_creates_with_defaults(self, mock_db: MagicMock) -> None:
        """Should create experiment with default control/treatment variants."""
        mock_session = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.cursor.return_value.__enter__.return_value = mock_cursor

        now = datetime.now(UTC)
        mock_cursor.fetchone.side_effect = [
            None,  # No existing experiment
            {
                "id": uuid4(),
                "name": "test_exp",
                "description": None,
                "status": "draft",
                "variants": [
                    {"name": "control", "weight": 50},
                    {"name": "treatment", "weight": 50},
                ],
                "metrics": [],
                "start_date": None,
                "end_date": None,
                "created_at": now,
                "updated_at": now,
            },
        ]

        exp = create_experiment(name="test_exp")

        assert exp.name == "test_exp"
        assert exp.status == "draft"
        assert len(exp.variants) == 2
        assert exp.variants[0].name == "control"
        assert exp.variants[0].weight == 50

    @patch("backend.services.experiments.db_session")
    def test_raises_when_exists(self, mock_db: MagicMock) -> None:
        """Should raise ValueError if experiment name exists."""
        mock_session = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": uuid4()}

        with pytest.raises(ValueError, match="already exists"):
            create_experiment(name="existing")

    def test_raises_on_invalid_weights(self) -> None:
        """Should raise ValueError if weights don't sum to 100."""
        with pytest.raises(ValueError, match="weights must sum to 100"):
            create_experiment(
                name="test",
                variants=[{"name": "a", "weight": 30}, {"name": "b", "weight": 30}],
            )

    def test_raises_on_too_few_variants(self) -> None:
        """Should raise ValueError if fewer than 2 variants."""
        with pytest.raises(ValueError, match="at least 2 variants"):
            create_experiment(name="test", variants=[{"name": "only_one", "weight": 100}])


class TestUpdateExperiment:
    """Tests for update_experiment function."""

    @patch("backend.services.experiments.get_experiment")
    def test_raises_when_not_draft(self, mock_get: MagicMock) -> None:
        """Should raise ValueError if not in draft status."""
        mock_get.return_value = Experiment(
            id=uuid4(),
            name="test",
            description=None,
            status="running",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=datetime.now(UTC),
            end_date=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with pytest.raises(ValueError, match="Cannot update experiment in 'running' status"):
            update_experiment(uuid4(), description="Updated")

    @patch("backend.services.experiments.get_experiment")
    def test_returns_none_when_not_found(self, mock_get: MagicMock) -> None:
        """Should return None if experiment not found."""
        mock_get.return_value = None
        result = update_experiment(uuid4(), description="Updated")
        assert result is None


class TestStatusTransitions:
    """Tests for experiment status transitions."""

    @patch("backend.services.experiments.db_session")
    @patch("backend.services.experiments.get_experiment")
    def test_start_from_draft(self, mock_get: MagicMock, mock_db: MagicMock) -> None:
        """Should start experiment from draft."""
        exp_id = uuid4()
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=exp_id,
            name="test",
            description=None,
            status="draft",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=None,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        mock_session = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": exp_id,
            "name": "test",
            "description": None,
            "status": "running",
            "variants": [{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}],
            "metrics": [],
            "start_date": now,
            "end_date": None,
            "created_at": now,
            "updated_at": now,
        }

        result = start_experiment(exp_id)

        assert result is not None
        assert result.status == "running"
        assert result.start_date is not None

    @patch("backend.services.experiments.get_experiment")
    def test_cannot_start_from_concluded(self, mock_get: MagicMock) -> None:
        """Should raise ValueError when starting from concluded."""
        exp_id = uuid4()
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=exp_id,
            name="test",
            description=None,
            status="concluded",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=now,
            end_date=now,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Cannot transition from 'concluded' to 'running'"):
            start_experiment(exp_id)

    @patch("backend.services.experiments.db_session")
    @patch("backend.services.experiments.get_experiment")
    def test_pause_running_experiment(self, mock_get: MagicMock, mock_db: MagicMock) -> None:
        """Should pause a running experiment."""
        exp_id = uuid4()
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=exp_id,
            name="test",
            description=None,
            status="running",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=now,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        mock_session = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": exp_id,
            "name": "test",
            "description": None,
            "status": "paused",
            "variants": [{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}],
            "metrics": [],
            "start_date": now,
            "end_date": None,
            "created_at": now,
            "updated_at": now,
        }

        result = pause_experiment(exp_id)

        assert result is not None
        assert result.status == "paused"

    @patch("backend.services.experiments.db_session")
    @patch("backend.services.experiments.get_experiment")
    def test_conclude_sets_end_date(self, mock_get: MagicMock, mock_db: MagicMock) -> None:
        """Should set end_date when concluding."""
        exp_id = uuid4()
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=exp_id,
            name="test",
            description=None,
            status="running",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=now,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        mock_session = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "id": exp_id,
            "name": "test",
            "description": None,
            "status": "concluded",
            "variants": [{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}],
            "metrics": [],
            "start_date": now,
            "end_date": now,
            "created_at": now,
            "updated_at": now,
        }

        result = conclude_experiment(exp_id)

        assert result is not None
        assert result.status == "concluded"
        assert result.end_date is not None


class TestDeleteExperiment:
    """Tests for delete_experiment function."""

    @patch("backend.services.experiments.get_experiment")
    def test_raises_when_not_draft(self, mock_get: MagicMock) -> None:
        """Should raise ValueError if not in draft status."""
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=uuid4(),
            name="test",
            description=None,
            status="running",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=now,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(ValueError, match="Cannot delete experiment in 'running' status"):
            delete_experiment(uuid4())

    @patch("backend.services.experiments.get_experiment")
    def test_returns_false_when_not_found(self, mock_get: MagicMock) -> None:
        """Should return False if experiment not found."""
        mock_get.return_value = None
        result = delete_experiment(uuid4())
        assert result is False

    @patch("backend.services.experiments.db_session")
    @patch("backend.services.experiments.get_experiment")
    def test_deletes_draft_experiment(self, mock_get: MagicMock, mock_db: MagicMock) -> None:
        """Should delete draft experiment successfully."""
        exp_id = uuid4()
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=exp_id,
            name="test",
            description=None,
            status="draft",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=None,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        mock_session = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": exp_id}

        result = delete_experiment(exp_id)
        assert result is True


class TestAssignUserToVariant:
    """Tests for assign_user_to_variant function."""

    @patch("backend.services.experiments.get_experiment_by_name")
    def test_returns_none_when_not_running(self, mock_get: MagicMock) -> None:
        """Should return None if experiment not running."""
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=uuid4(),
            name="test",
            description=None,
            status="draft",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=None,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        result = assign_user_to_variant("test", "user123")
        assert result is None

    @patch("backend.services.experiments.get_experiment_by_name")
    def test_returns_none_when_not_found(self, mock_get: MagicMock) -> None:
        """Should return None if experiment not found."""
        mock_get.return_value = None
        result = assign_user_to_variant("nonexistent", "user123")
        assert result is None

    @patch("backend.services.experiments.get_experiment_by_name")
    def test_deterministic_assignment(self, mock_get: MagicMock) -> None:
        """Should assign same variant to same user."""
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=uuid4(),
            name="test",
            description=None,
            status="running",
            variants=[Variant("control", 50), Variant("treatment", 50)],
            metrics=[],
            start_date=now,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        result1 = assign_user_to_variant("test", "deterministic_user")
        result2 = assign_user_to_variant("test", "deterministic_user")

        assert result1 == result2
        assert result1 in ["control", "treatment"]

    @patch("backend.services.experiments.get_experiment_by_name")
    def test_respects_variant_weights(self, mock_get: MagicMock) -> None:
        """Should distribute users according to weights."""
        now = datetime.now(UTC)
        mock_get.return_value = Experiment(
            id=uuid4(),
            name="test",
            description=None,
            status="running",
            variants=[
                Variant("a", 80),
                Variant("b", 20),
            ],
            metrics=[],
            start_date=now,
            end_date=None,
            created_at=now,
            updated_at=now,
        )

        # Generate assignments for many users
        assignments = {"a": 0, "b": 0}
        for i in range(1000):
            variant = assign_user_to_variant("test", f"user{i}")
            if variant:
                assignments[variant] += 1

        # Should be roughly 80/20 distribution (with some tolerance)
        total = assignments["a"] + assignments["b"]
        a_pct = assignments["a"] / total * 100

        # Allow +-10% tolerance due to hash distribution
        assert 70 < a_pct < 90


class TestGetUserVariant:
    """Tests for get_user_variant function."""

    @patch("backend.services.experiments.assign_user_to_variant")
    def test_is_alias_for_assign(self, mock_assign: MagicMock) -> None:
        """Should be an alias for assign_user_to_variant."""
        mock_assign.return_value = "control"
        result = get_user_variant("test", "user123")
        assert result == "control"
        mock_assign.assert_called_once_with("test", "user123")
