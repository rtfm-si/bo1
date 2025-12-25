"""Unit tests for backend/api/dependencies.py session dependencies.

Tests the new granular session dependencies:
- get_session_metadata: No auth, just loads metadata
- get_verified_session_admin: Admin auth, no ownership check
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.dependencies import (
    SessionMetadataDict,
    get_session_metadata,
    get_session_metadata_cache,
    get_verified_session_admin,
)


@pytest.fixture
def mock_redis_manager():
    """Create mock Redis manager."""
    manager = MagicMock()
    manager.is_available = True
    manager.load_metadata = MagicMock(
        return_value={
            "user_id": "user-123",
            "status": "running",
            "phase": "deliberation",
            "started_at": "2025-01-01T00:00:00Z",
            "cost": 0.05,
        }
    )
    return manager


@pytest.fixture
def sample_metadata() -> SessionMetadataDict:
    """Sample session metadata."""
    return {
        "user_id": "user-123",
        "status": "running",
        "phase": "deliberation",
        "started_at": "2025-01-01T00:00:00Z",
        "cost": 0.05,
    }


class TestGetSessionMetadata:
    """Tests for get_session_metadata dependency."""

    @pytest.mark.asyncio
    async def test_returns_metadata_for_valid_session(self, mock_redis_manager, sample_metadata):
        """Should return metadata when session exists."""
        # Clear cache before test
        cache = get_session_metadata_cache()
        cache.clear()

        with patch("backend.api.dependencies.validate_session_id", return_value="session-valid"):
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                mock_cache.get_or_load = MagicMock(return_value=sample_metadata)
                mock_cache_fn.return_value = mock_cache

                result = await get_session_metadata(
                    session_id="session-valid",
                    redis_manager=mock_redis_manager,
                )

                assert result["user_id"] == "user-123"
                assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_raises_404_when_session_not_found(self, mock_redis_manager):
        """Should raise 404 when session doesn't exist."""
        with patch("backend.api.dependencies.validate_session_id", return_value="session-missing"):
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                mock_cache.get_or_load = MagicMock(return_value=None)
                mock_cache_fn.return_value = mock_cache

                with pytest.raises(HTTPException) as exc:
                    await get_session_metadata(
                        session_id="session-missing",
                        redis_manager=mock_redis_manager,
                    )

                assert exc.value.status_code == 404
                assert "Session not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_raises_500_when_redis_unavailable(self, mock_redis_manager):
        """Should raise 500 when Redis is unavailable."""
        mock_redis_manager.is_available = False

        with patch("backend.api.dependencies.validate_session_id", return_value="session-id"):
            with pytest.raises(HTTPException) as exc:
                await get_session_metadata(
                    session_id="session-id",
                    redis_manager=mock_redis_manager,
                )

            assert exc.value.status_code == 500
            assert "Redis unavailable" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_uses_cache(self, mock_redis_manager, sample_metadata):
        """Should use session metadata cache."""
        with patch("backend.api.dependencies.validate_session_id", return_value="session-id"):
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                mock_cache.get_or_load = MagicMock(return_value=sample_metadata)
                mock_cache_fn.return_value = mock_cache

                await get_session_metadata(
                    session_id="session-id",
                    redis_manager=mock_redis_manager,
                )

                mock_cache.get_or_load.assert_called_once()


class TestGetVerifiedSessionAdmin:
    """Tests for get_verified_session_admin dependency."""

    @pytest.mark.asyncio
    async def test_returns_metadata_for_admin(self, mock_redis_manager, sample_metadata):
        """Should return metadata when admin is authenticated."""
        with patch("backend.api.dependencies.validate_session_id", return_value="session-valid"):
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                mock_cache.get_or_load = MagicMock(return_value=sample_metadata)
                mock_cache_fn.return_value = mock_cache

                result = await get_verified_session_admin(
                    session_id="session-valid",
                    _admin="admin-key",
                    redis_manager=mock_redis_manager,
                )

                assert result["user_id"] == "user-123"
                assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_admin_can_access_any_user_session(self, mock_redis_manager):
        """Admin should be able to access sessions belonging to any user."""
        other_user_metadata = {
            "user_id": "other-user-456",
            "status": "running",
        }

        with patch("backend.api.dependencies.validate_session_id", return_value="session-id"):
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                mock_cache.get_or_load = MagicMock(return_value=other_user_metadata)
                mock_cache_fn.return_value = mock_cache

                # Admin should be able to access another user's session
                result = await get_verified_session_admin(
                    session_id="session-id",
                    _admin="admin-key",
                    redis_manager=mock_redis_manager,
                )

                # No ownership check - admin gets the metadata
                assert result["user_id"] == "other-user-456"

    @pytest.mark.asyncio
    async def test_raises_404_when_session_not_found(self, mock_redis_manager):
        """Should raise 404 when session doesn't exist."""
        with patch("backend.api.dependencies.validate_session_id", return_value="session-missing"):
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                mock_cache.get_or_load = MagicMock(return_value=None)
                mock_cache_fn.return_value = mock_cache

                with pytest.raises(HTTPException) as exc:
                    await get_verified_session_admin(
                        session_id="session-missing",
                        _admin="admin-key",
                        redis_manager=mock_redis_manager,
                    )

                assert exc.value.status_code == 404
                assert "Session not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_raises_500_when_redis_unavailable(self, mock_redis_manager):
        """Should raise 500 when Redis is unavailable."""
        mock_redis_manager.is_available = False

        with patch("backend.api.dependencies.validate_session_id", return_value="session-id"):
            with pytest.raises(HTTPException) as exc:
                await get_verified_session_admin(
                    session_id="session-id",
                    _admin="admin-key",
                    redis_manager=mock_redis_manager,
                )

            assert exc.value.status_code == 500
            assert "Redis unavailable" in str(exc.value.detail)


class TestSessionMetadataCache:
    """Tests for cache integration with dependencies."""

    @pytest.mark.asyncio
    async def test_cache_is_used_on_repeated_calls(self, mock_redis_manager, sample_metadata):
        """Cache should be used on repeated calls."""
        cache = get_session_metadata_cache()
        cache.clear()

        with patch("backend.api.dependencies.validate_session_id", return_value="session-cached"):
            # First call - cache miss, loads from Redis
            with patch("backend.api.dependencies.get_session_metadata_cache") as mock_cache_fn:
                mock_cache = MagicMock()
                call_count = [0]

                def get_or_load_impl(session_id, loader_fn):
                    call_count[0] += 1
                    return sample_metadata

                mock_cache.get_or_load = MagicMock(side_effect=get_or_load_impl)
                mock_cache_fn.return_value = mock_cache

                result1 = await get_session_metadata(
                    session_id="session-cached",
                    redis_manager=mock_redis_manager,
                )
                result2 = await get_session_metadata(
                    session_id="session-cached",
                    redis_manager=mock_redis_manager,
                )

                assert result1["user_id"] == "user-123"
                assert result2["user_id"] == "user-123"
                # Cache was used both times
                assert call_count[0] == 2


class TestSessionMetadataDict:
    """Tests for SessionMetadataDict TypedDict."""

    def test_all_fields_optional(self):
        """All fields should be optional (TypedDict with total=False)."""
        # Empty dict should be valid
        empty: SessionMetadataDict = {}
        assert empty == {}

        # Partial dict should be valid
        partial: SessionMetadataDict = {"user_id": "user-123", "status": "running"}
        assert partial["user_id"] == "user-123"

        # Full dict should be valid
        full: SessionMetadataDict = {
            "user_id": "user-123",
            "status": "running",
            "phase": "deliberation",
            "started_at": "2025-01-01T00:00:00Z",
            "cost": 0.05,
            "round_number": 2,
            "expert_count": 5,
            "contribution_count": 10,
            "focus_area_count": 3,
            "task_count": 5,
            "workspace_id": "ws-123",
        }
        assert full["expert_count"] == 5
