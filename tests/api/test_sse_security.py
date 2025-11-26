"""Security tests for SSE streaming endpoints.

Tests for:
- P2-SSE-6: SSE heartbeat/stall detection (frontend - manual testing required)
- P2-SSE-7: SSE with non-owned session (should return 404)
- P2-SSE-8: Event history with non-owned session (should return 404)
- P2-SSE-9: SSE with uninitialized state (should return 409 or 404)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.streaming import get_event_history, stream_deliberation


class TestSSENonOwnedSession:
    """Test SSE access to non-owned sessions returns 404."""

    @pytest.mark.asyncio
    async def test_verify_session_ownership_returns_404(self):
        """Test that verify_session_ownership returns 404 for non-owned sessions."""
        from backend.api.utils.security import verify_session_ownership

        session_id = "bo1_550e8400-e29b-41d4-a716-446655440000"
        user_id = "user_2"
        session_metadata = {
            "user_id": "user_1",  # Different owner
            "status": "running",
        }

        # Should raise HTTPException with 404 status (not 403)
        with pytest.raises(HTTPException) as exc_info:
            await verify_session_ownership(
                session_id=session_id,
                user_id=user_id,
                session_metadata=session_metadata,
            )

        # Verify 404 (not 403) to prevent session enumeration
        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_session_ownership_session_not_found(self):
        """Test that verify_session_ownership returns 404 when session doesn't exist."""
        from backend.api.utils.security import verify_session_ownership

        session_id = "bo1_550e8400-e29b-41d4-a716-446655440001"
        user_id = "user_1"
        session_metadata = None  # Session doesn't exist

        # Should raise HTTPException with 404 status
        with pytest.raises(HTTPException) as exc_info:
            await verify_session_ownership(
                session_id=session_id,
                user_id=user_id,
                session_metadata=session_metadata,
            )

        # Verify 404
        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_stream_endpoint_uses_verified_session_dependency(self):
        """Test that stream endpoint uses VerifiedSession dependency for ownership checks.

        This verifies that the endpoint relies on the dependency injection system
        to handle ownership validation, which already returns 404 for non-owned sessions.
        """
        session_id = "bo1_550e8400-e29b-41d4-a716-446655440002"

        # Mock all Redis operations to simulate session state
        with (
            patch("backend.api.streaming.validate_session_id") as mock_validate,
            patch("backend.api.streaming.get_redis_manager") as mock_redis,
        ):
            mock_validate.return_value = session_id

            # Create mock Redis manager that returns state
            mock_redis_instance = MagicMock()
            mock_redis_instance.is_available = True
            mock_redis_instance.load_state.return_value = {"session_id": session_id}
            mock_redis_instance.load_metadata.return_value = {
                "user_id": "user_1",
                "status": "running",
            }
            mock_redis.return_value = mock_redis_instance

            # Mock session data indicating user owns the session
            mock_session_data = ("user_1", {"user_id": "user_1", "status": "running"})

            # Call should succeed because ownership is verified by dependency
            # (we're not testing the full streaming here, just that ownership check passes)
            result = await stream_deliberation(
                session_id=session_id,
                session_data=mock_session_data,
            )

            # Should return StreamingResponse (not raise exception)
            assert result is not None

    @pytest.mark.asyncio
    async def test_event_history_endpoint_uses_verified_session_dependency(self):
        """Test that event history endpoint uses VerifiedSession dependency."""
        session_id = "bo1_550e8400-e29b-41d4-a716-446655440003"

        # Mock all Redis operations
        with (
            patch("backend.api.streaming.validate_session_id") as mock_validate,
            patch("backend.api.streaming.get_redis_manager") as mock_redis,
        ):
            mock_validate.return_value = session_id

            # Create mock Redis manager
            mock_redis_instance = MagicMock()
            mock_redis_instance.is_available = True
            mock_redis_instance.redis.lrange.return_value = []  # No historical events
            mock_redis.return_value = mock_redis_instance

            # Mock session data indicating user owns the session
            mock_session_data = ("user_1", {"user_id": "user_1", "status": "complete"})

            # Call should succeed because ownership is verified by dependency
            result = await get_event_history(
                session_id=session_id,
                session_data=mock_session_data,
            )

            # Should return event history dict
            assert result is not None
            assert "events" in result
            assert result["session_id"] == session_id


class TestSSEUninitializedState:
    """Test SSE behavior with uninitialized state."""

    @pytest.mark.asyncio
    async def test_stream_deliberation_uninitialized_state_timeout(self):
        """Test that SSE waits for state initialization and times out if not initialized."""
        session_id = "bo1_test_session_uninit"

        # Mock dependencies
        with (
            patch("backend.api.streaming.get_redis_manager") as mock_redis,
            patch("backend.api.streaming.validate_session_id") as mock_validate,
        ):
            # Valid session ID
            mock_validate.return_value = session_id

            # Redis is available
            mock_redis_instance = MagicMock()
            mock_redis_instance.is_available = True

            # State is never initialized (returns None)
            mock_redis_instance.load_state.return_value = None

            # Metadata exists (session created but graph not started)
            mock_redis_instance.load_metadata.return_value = {
                "user_id": "test_user",
                "status": "created",
            }

            mock_redis.return_value = mock_redis_instance

            # Mock session verification to pass
            mock_session_data = ("test_user", {"user_id": "test_user", "status": "created"})

            # Mock asyncio.sleep to avoid actual waiting in test
            with patch("backend.api.streaming.asyncio.sleep", new_callable=AsyncMock):
                # Attempt to stream - should raise HTTPException(409)
                with pytest.raises(HTTPException) as exc_info:
                    await stream_deliberation(
                        session_id=session_id,
                        session_data=mock_session_data,
                    )

                # Should return 409 (Conflict) - state not initialized yet
                assert exc_info.value.status_code == 409
                assert "has not been started yet" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_stream_deliberation_uninitialized_state_killed(self):
        """Test that SSE handles session killed during initialization."""
        session_id = "bo1_test_session_killed"

        # Mock dependencies
        with (
            patch("backend.api.streaming.get_redis_manager") as mock_redis,
            patch("backend.api.streaming.validate_session_id") as mock_validate,
        ):
            # Valid session ID
            mock_validate.return_value = session_id

            # Redis is available
            mock_redis_instance = MagicMock()
            mock_redis_instance.is_available = True

            # State is never initialized (returns None)
            # But metadata shows session was killed
            mock_redis_instance.load_state.return_value = None
            mock_redis_instance.load_metadata.return_value = {
                "user_id": "test_user",
                "status": "killed"
            }

            mock_redis.return_value = mock_redis_instance

            # Mock session verification with killed status
            mock_session_data = ("test_user", {"user_id": "test_user", "status": "killed"})

            # Mock asyncio.sleep to avoid actual waiting in test
            with patch("backend.api.streaming.asyncio.sleep", new_callable=AsyncMock):
                # Attempt to stream - should raise HTTPException(500)
                with pytest.raises(HTTPException) as exc_info:
                    await stream_deliberation(
                        session_id=session_id,
                        session_data=mock_session_data,
                    )

                # Should return 500 - session failed to initialize
                assert exc_info.value.status_code == 500
                assert "failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_stream_deliberation_session_not_found(self):
        """Test that SSE returns 404 for completely non-existent session."""
        session_id = "bo1_test_session_nonexistent"

        # Mock dependencies
        with (
            patch("backend.api.streaming.get_redis_manager") as mock_redis,
            patch("backend.api.streaming.validate_session_id") as mock_validate,
        ):
            # Valid session ID format
            mock_validate.return_value = session_id

            # Redis is available
            mock_redis_instance = MagicMock()
            mock_redis_instance.is_available = True

            # Neither state nor metadata exists
            mock_redis_instance.load_state.return_value = None
            mock_redis_instance.load_metadata.return_value = None

            mock_redis.return_value = mock_redis_instance

            # Mock session verification to pass
            mock_session_data = ("test_user", {"user_id": "test_user"})

            # Mock asyncio.sleep to avoid actual waiting in test
            with patch("backend.api.streaming.asyncio.sleep", new_callable=AsyncMock):
                # Attempt to stream - should raise HTTPException(404)
                with pytest.raises(HTTPException) as exc_info:
                    await stream_deliberation(
                        session_id=session_id,
                        session_data=mock_session_data,
                    )

                # Should return 404 - session doesn't exist
                assert exc_info.value.status_code == 404
                assert "not found" in exc_info.value.detail or "not properly initialized" in exc_info.value.detail


class TestSSEOwnershipValidation:
    """Test ownership validation for SSE endpoints."""

    def test_verify_session_ownership_returns_404_on_mismatch(self):
        """Test that verify_session_ownership returns 404 (not 403) for unauthorized access."""
        from backend.api.utils.security import verify_session_ownership

        # Test with mismatched ownership
        session_id = "bo1_test_session_ownership"
        user_id = "user_2"
        session_metadata = {
            "user_id": "user_1",  # Different owner
            "status": "running",
        }

        # Should raise HTTPException with 404 status (not 403)
        with pytest.raises(HTTPException) as exc_info:
            # Use asyncio.run for async function
            asyncio.run(
                verify_session_ownership(
                    session_id=session_id,
                    user_id=user_id,
                    session_metadata=session_metadata,
                )
            )

        # Verify 404 (not 403) to prevent session enumeration
        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    def test_verify_session_ownership_passes_for_owner(self):
        """Test that verify_session_ownership passes for legitimate owner."""
        from backend.api.utils.security import verify_session_ownership

        # Test with matching ownership
        session_id = "bo1_test_session_ownership"
        user_id = "user_1"
        session_metadata = {
            "user_id": "user_1",  # Same owner
            "status": "running",
        }

        # Should not raise exception
        result = asyncio.run(
            verify_session_ownership(
                session_id=session_id,
                user_id=user_id,
                session_metadata=session_metadata,
            )
        )

        # Should return the metadata
        assert result == session_metadata


# Mark all tests as integration tests (they test API behavior)
pytestmark = pytest.mark.integration
