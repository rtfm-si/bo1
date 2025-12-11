"""Tests for admin feature flag endpoints and authorization."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.api.admin.feature_flags import (
    CreateFeatureFlagRequest,
    FeatureFlagItem,
    FeatureFlagListResponse,
    SetUserOverrideRequest,
    UpdateFeatureFlagRequest,
    UserOverrideResponse,
    _flag_to_item,
)
from backend.services.feature_flags import FeatureFlag


@pytest.mark.unit
class TestFeatureFlagItem:
    """Tests for FeatureFlagItem model."""

    def test_from_service_model(self) -> None:
        """Test creating response from service model."""
        now = datetime.now(UTC)
        flag = FeatureFlag(
            id=uuid4(),
            name="test_flag",
            description="A test flag",
            enabled=True,
            rollout_pct=50,
            tiers=["pro", "starter"],
            created_at=now,
            updated_at=now,
        )

        item = _flag_to_item(flag)

        assert item.name == "test_flag"
        assert item.description == "A test flag"
        assert item.enabled is True
        assert item.rollout_pct == 50
        assert item.tiers == ["pro", "starter"]


@pytest.mark.unit
class TestFeatureFlagListResponse:
    """Tests for FeatureFlagListResponse model."""

    def test_structure(self) -> None:
        """Test response structure."""
        response = FeatureFlagListResponse(
            flags=[
                FeatureFlagItem(
                    id=str(uuid4()),
                    name="flag1",
                    description=None,
                    enabled=True,
                    rollout_pct=100,
                    tiers=[],
                    created_at=datetime.now(UTC).isoformat(),
                    updated_at=datetime.now(UTC).isoformat(),
                ),
            ],
            count=1,
        )

        assert len(response.flags) == 1
        assert response.count == 1


@pytest.mark.unit
class TestCreateFeatureFlagRequest:
    """Tests for CreateFeatureFlagRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request."""
        request = CreateFeatureFlagRequest(
            name="new_flag",
            description="Description",
            enabled=True,
            rollout_pct=75,
            tiers=["pro"],
        )

        assert request.name == "new_flag"
        assert request.enabled is True
        assert request.rollout_pct == 75

    def test_defaults(self) -> None:
        """Test default values."""
        request = CreateFeatureFlagRequest(name="minimal")

        assert request.enabled is False
        assert request.rollout_pct == 100
        assert request.tiers == []

    def test_rollout_pct_validation(self) -> None:
        """Test rollout percentage validation."""
        # Valid values
        CreateFeatureFlagRequest(name="test", rollout_pct=0)
        CreateFeatureFlagRequest(name="test", rollout_pct=100)

        # Invalid values
        with pytest.raises(ValueError):
            CreateFeatureFlagRequest(name="test", rollout_pct=-1)
        with pytest.raises(ValueError):
            CreateFeatureFlagRequest(name="test", rollout_pct=101)


@pytest.mark.unit
class TestUpdateFeatureFlagRequest:
    """Tests for UpdateFeatureFlagRequest model."""

    def test_partial_update(self) -> None:
        """Test partial update request."""
        request = UpdateFeatureFlagRequest(enabled=True)

        assert request.enabled is True
        assert request.description is None
        assert request.rollout_pct is None
        assert request.tiers is None


@pytest.mark.unit
class TestSetUserOverrideRequest:
    """Tests for SetUserOverrideRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request."""
        request = SetUserOverrideRequest(user_id="user123", enabled=True)

        assert request.user_id == "user123"
        assert request.enabled is True


@pytest.mark.unit
class TestUserOverrideResponse:
    """Tests for UserOverrideResponse model."""

    def test_structure(self) -> None:
        """Test response structure."""
        response = UserOverrideResponse(
            flag_name="test_flag",
            user_id="user123",
            enabled=True,
        )

        assert response.flag_name == "test_flag"
        assert response.user_id == "user123"
        assert response.enabled is True


@pytest.mark.unit
class TestAdminAuthorizationCheck:
    """Tests for admin authorization on endpoints."""

    @patch("backend.api.admin.feature_flags.ff.get_all_flags")
    @patch("backend.api.utils.auth_helpers.is_admin")
    def test_non_admin_gets_403(self, mock_is_admin: MagicMock, mock_get_all: MagicMock) -> None:
        """Non-admin users should get 403."""
        mock_is_admin.return_value = False

        from fastapi import HTTPException

        from backend.api.utils.auth_helpers import require_admin_role

        current_user = {"user_id": "user123", "is_admin": False}

        with pytest.raises(HTTPException) as exc_info:
            require_admin_role(current_user)

        assert exc_info.value.status_code == 403

    @patch("backend.api.utils.auth_helpers.is_admin")
    def test_admin_passes(self, mock_is_admin: MagicMock) -> None:
        """Admin users should pass."""
        mock_is_admin.return_value = True

        from backend.api.utils.auth_helpers import require_admin_role

        current_user = {"user_id": "admin123", "is_admin": True}

        # Should not raise
        require_admin_role(current_user)
