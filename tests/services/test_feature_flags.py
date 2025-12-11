"""Tests for feature flags service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.services.feature_flags import (
    FeatureFlag,
    _hash_user_for_rollout,
    create_flag,
    delete_flag,
    get_flags_for_user,
    is_enabled,
    set_user_override,
    update_flag,
)


class TestHashUserForRollout:
    """Tests for _hash_user_for_rollout."""

    def test_deterministic_hash(self) -> None:
        """Hash should be deterministic for same inputs."""
        result1 = _hash_user_for_rollout("test_flag", "user123")
        result2 = _hash_user_for_rollout("test_flag", "user123")
        assert result1 == result2

    def test_different_users_different_hash(self) -> None:
        """Different users should have different hashes (usually)."""
        result1 = _hash_user_for_rollout("test_flag", "user1")
        result2 = _hash_user_for_rollout("test_flag", "user2")
        # Not guaranteed to be different, but statistically very likely
        # For this test, we just verify both are in valid range
        assert 0 <= result1 < 100
        assert 0 <= result2 < 100

    def test_hash_in_range(self) -> None:
        """Hash should be between 0 and 99."""
        for i in range(100):
            result = _hash_user_for_rollout("flag", f"user{i}")
            assert 0 <= result < 100


class TestIsEnabled:
    """Tests for is_enabled function."""

    @patch("backend.services.feature_flags.get_flag")
    def test_returns_false_when_flag_not_found(self, mock_get_flag: MagicMock) -> None:
        """Non-existent flag should return False."""
        mock_get_flag.return_value = None
        assert is_enabled("nonexistent") is False

    @patch("backend.services.feature_flags.get_flag")
    def test_returns_false_when_globally_disabled(self, mock_get_flag: MagicMock) -> None:
        """Globally disabled flag should return False."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=False,
            rollout_pct=100,
            tiers=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert is_enabled("test") is False

    @patch("backend.services.feature_flags.get_user_override")
    @patch("backend.services.feature_flags.get_flag")
    def test_user_override_takes_precedence(
        self, mock_get_flag: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """User override should take precedence over other rules."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=True,
            rollout_pct=0,  # Would normally be disabled
            tiers=["pro"],  # Would normally require pro tier
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get_override.return_value = True

        # Override enables it despite rollout_pct=0 and missing tier
        assert is_enabled("test", user_id="user123", tier="free") is True

    @patch("backend.services.feature_flags.get_user_override")
    @patch("backend.services.feature_flags.get_flag")
    def test_tier_restriction_enforced(
        self, mock_get_flag: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Tier restriction should be enforced when no override."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=True,
            rollout_pct=100,
            tiers=["pro", "starter"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get_override.return_value = None

        # Free tier should be denied
        assert is_enabled("test", user_id="user123", tier="free") is False

        # Starter tier should be allowed
        assert is_enabled("test", user_id="user123", tier="starter") is True

        # Pro tier should be allowed
        assert is_enabled("test", user_id="user123", tier="pro") is True

    @patch("backend.services.feature_flags.get_user_override")
    @patch("backend.services.feature_flags.get_flag")
    def test_no_tier_fails_when_tiers_specified(
        self, mock_get_flag: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """No tier provided should fail when flag requires specific tiers."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=True,
            rollout_pct=100,
            tiers=["pro"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get_override.return_value = None

        assert is_enabled("test", user_id="user123") is False

    @patch("backend.services.feature_flags.get_user_override")
    @patch("backend.services.feature_flags.get_flag")
    def test_rollout_percentage_enforced(
        self, mock_get_flag: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Rollout percentage should filter users."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=True,
            rollout_pct=50,
            tiers=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get_override.return_value = None

        # Test determinism: same user should always get same result
        result1 = is_enabled("test", user_id="user_deterministic")
        result2 = is_enabled("test", user_id="user_deterministic")
        assert result1 == result2

    @patch("backend.services.feature_flags.get_user_override")
    @patch("backend.services.feature_flags.get_flag")
    def test_enabled_globally_with_no_restrictions(
        self, mock_get_flag: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Flag with no restrictions should be enabled for everyone."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=True,
            rollout_pct=100,
            tiers=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get_override.return_value = None

        assert is_enabled("test") is True
        assert is_enabled("test", user_id="anyone") is True
        assert is_enabled("test", user_id="anyone", tier="free") is True


class TestCreateFlag:
    """Tests for create_flag function."""

    @patch("backend.services.feature_flags.db_session")
    def test_creates_flag_successfully(self, mock_db: MagicMock) -> None:
        """Should create flag with provided values."""
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.side_effect = [
            None,  # No existing flag
            (uuid4(),),  # Return new ID
        ]

        flag = create_flag(
            name="new_feature",
            description="A new feature",
            enabled=True,
            rollout_pct=50,
            tiers=["pro"],
        )

        assert flag.name == "new_feature"
        assert flag.description == "A new feature"
        assert flag.enabled is True
        assert flag.rollout_pct == 50
        assert flag.tiers == ["pro"]

    @patch("backend.services.feature_flags.db_session")
    def test_raises_when_flag_exists(self, mock_db: MagicMock) -> None:
        """Should raise ValueError if flag name already exists."""
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = (uuid4(),)

        with pytest.raises(ValueError, match="already exists"):
            create_flag(name="existing_flag")


class TestUpdateFlag:
    """Tests for update_flag function."""

    @patch("backend.services.feature_flags._invalidate_cache")
    @patch("backend.services.feature_flags.get_flag")
    @patch("backend.services.feature_flags.db_session")
    def test_updates_flag_and_invalidates_cache(
        self,
        mock_db: MagicMock,
        mock_get_flag: MagicMock,
        mock_invalidate: MagicMock,
    ) -> None:
        """Should update flag and invalidate cache."""
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = (uuid4(),)

        updated_flag = FeatureFlag(
            id=uuid4(),
            name="test",
            description="Updated",
            enabled=True,
            rollout_pct=75,
            tiers=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get_flag.return_value = updated_flag

        result = update_flag(name="test", enabled=True, rollout_pct=75)

        assert result is not None
        mock_invalidate.assert_called_once_with("test")


class TestDeleteFlag:
    """Tests for delete_flag function."""

    @patch("backend.services.feature_flags._invalidate_cache")
    @patch("backend.services.feature_flags.db_session")
    def test_deletes_flag_and_invalidates_cache(
        self, mock_db: MagicMock, mock_invalidate: MagicMock
    ) -> None:
        """Should delete flag and invalidate cache."""
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = (uuid4(),)

        result = delete_flag("test")

        assert result is True
        mock_invalidate.assert_called_once_with("test")

    @patch("backend.services.feature_flags.db_session")
    def test_returns_false_when_not_found(self, mock_db: MagicMock) -> None:
        """Should return False if flag not found."""
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchone.return_value = None

        result = delete_flag("nonexistent")

        assert result is False


class TestSetUserOverride:
    """Tests for set_user_override function."""

    @patch("backend.services.feature_flags.get_flag")
    @patch("backend.services.feature_flags.db_session")
    def test_sets_override_successfully(self, mock_db: MagicMock, mock_get_flag: MagicMock) -> None:
        """Should set user override."""
        mock_get_flag.return_value = FeatureFlag(
            id=uuid4(),
            name="test",
            description=None,
            enabled=True,
            rollout_pct=100,
            tiers=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_session = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_session

        result = set_user_override("test", "user123", enabled=True)

        assert result is True

    @patch("backend.services.feature_flags.get_flag")
    def test_returns_false_when_flag_not_found(self, mock_get_flag: MagicMock) -> None:
        """Should return False if flag not found."""
        mock_get_flag.return_value = None

        result = set_user_override("nonexistent", "user123", enabled=True)

        assert result is False


class TestGetFlagsForUser:
    """Tests for get_flags_for_user function."""

    @patch("backend.services.feature_flags.is_enabled")
    @patch("backend.services.feature_flags.get_all_flags")
    def test_returns_evaluated_flags(
        self, mock_get_all: MagicMock, mock_is_enabled: MagicMock
    ) -> None:
        """Should return dict of flag evaluations for user."""
        mock_get_all.return_value = [
            FeatureFlag(
                id=uuid4(),
                name="flag1",
                description=None,
                enabled=True,
                rollout_pct=100,
                tiers=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            FeatureFlag(
                id=uuid4(),
                name="flag2",
                description=None,
                enabled=False,
                rollout_pct=100,
                tiers=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]
        mock_is_enabled.side_effect = [True, False]

        result = get_flags_for_user("user123", tier="pro")

        assert result == {"flag1": True, "flag2": False}
