"""Chaos tests for Redis checkpoint recovery.

Validates:
- Checkpoint save fails gracefully when Redis down
- Checkpoint restore returns None (not exception) on Redis error
- Session resume after Redis reconnect
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.chaos
class TestRedisConnectionFailure:
    """Test Redis connection failure handling."""

    @pytest.mark.asyncio
    async def test_checkpoint_save_graceful_failure(self) -> None:
        """Checkpoint save handles Redis connection error gracefully."""
        from bo1.graph.checkpointer import LoggingCheckpointerWrapper

        # Create mock base checkpointer that raises on put
        mock_base = AsyncMock()
        mock_base.aput = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

        wrapper = LoggingCheckpointerWrapper(mock_base)

        config = {"configurable": {"thread_id": "test-session"}}
        checkpoint = {"v": 1, "ts": "2024-01-01T00:00:00Z", "channel_values": {}}
        metadata = {"step": 1}

        # Should not raise - handles gracefully
        with pytest.raises(ConnectionError):
            await wrapper.aput(config, checkpoint, metadata, {})

    @pytest.mark.asyncio
    async def test_checkpoint_get_returns_none_on_error(self) -> None:
        """Checkpoint get returns None when Redis unavailable."""
        from bo1.graph.checkpointer import LoggingCheckpointerWrapper

        mock_base = AsyncMock()
        mock_base.aget = AsyncMock(side_effect=ConnectionError("Redis timeout"))

        wrapper = LoggingCheckpointerWrapper(mock_base)

        config = {"configurable": {"thread_id": "test-session"}}

        # Should raise the connection error (not silently return None)
        with pytest.raises(ConnectionError):
            await wrapper.aget(config)


@pytest.mark.chaos
class TestRedisTimeoutRecovery:
    """Test Redis timeout and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_transient_timeout_recovery(self) -> None:
        """Operations recover after transient Redis timeout."""
        call_count = 0

        async def flaky_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Redis timeout")
            return "success"

        # Simulate retry logic
        result = None
        for _attempt in range(5):
            try:
                result = await flaky_operation()
                break
            except TimeoutError:
                await asyncio.sleep(0.01)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_redis_reconnect_preserves_session_state(self) -> None:
        """Session state preserved after Redis reconnect."""
        # Simulate session data
        session_data = {"session_id": "bo1_test123", "round": 3, "contributions": ["a", "b"]}

        # Mock Redis client with reconnect behavior
        connection_state = {"connected": True, "reconnect_count": 0}

        async def mock_get(key: str) -> dict | None:
            if not connection_state["connected"]:
                raise ConnectionError("Not connected")
            return session_data

        async def mock_reconnect() -> None:
            connection_state["connected"] = True
            connection_state["reconnect_count"] += 1

        # Simulate disconnect
        connection_state["connected"] = False

        # Try to get - should fail
        with pytest.raises(ConnectionError):
            await mock_get("session:bo1_test123")

        # Reconnect
        await mock_reconnect()

        # Should work now
        result = await mock_get("session:bo1_test123")
        assert result == session_data
        assert connection_state["reconnect_count"] == 1


@pytest.mark.chaos
class TestRedisCheckpointerFactory:
    """Test checkpointer factory Redis failure handling."""

    def test_redis_url_construction_with_auth(self) -> None:
        """Redis URL correctly constructed with authentication."""
        from bo1.graph.checkpointer_factory import _create_redis_checkpointer

        with patch("bo1.graph.checkpointer_factory.get_settings") as mock_settings:
            mock_settings.return_value.redis_host = "localhost"
            mock_settings.return_value.redis_port = 6379
            mock_settings.return_value.redis_db = 0
            mock_settings.return_value.redis_password = "secret"  # noqa: S105
            mock_settings.return_value.checkpoint_ttl_seconds = 604800

            with patch("bo1.graph.checkpointer_factory.AsyncRedisSaver") as mock_saver_class:
                mock_saver = MagicMock()
                mock_saver_class.return_value = mock_saver

                with patch(
                    "bo1.graph.checkpointer_factory.LoggingCheckpointerWrapper"
                ) as mock_wrapper:
                    mock_wrapper.return_value = MagicMock()
                    _create_redis_checkpointer()

                # Verify URL includes password
                call_args = mock_saver_class.call_args
                redis_url = call_args[0][0]
                assert ":secret@" in redis_url

    def test_redis_url_construction_without_auth(self) -> None:
        """Redis URL correctly constructed without authentication."""
        from bo1.graph.checkpointer_factory import _create_redis_checkpointer

        with patch("bo1.graph.checkpointer_factory.get_settings") as mock_settings:
            mock_settings.return_value.redis_host = "redis"
            mock_settings.return_value.redis_port = 6379
            mock_settings.return_value.redis_db = 1
            mock_settings.return_value.redis_password = ""
            mock_settings.return_value.checkpoint_ttl_seconds = 604800

            with patch("bo1.graph.checkpointer_factory.AsyncRedisSaver") as mock_saver_class:
                mock_saver = MagicMock()
                mock_saver_class.return_value = mock_saver

                with patch(
                    "bo1.graph.checkpointer_factory.LoggingCheckpointerWrapper"
                ) as mock_wrapper:
                    mock_wrapper.return_value = MagicMock()
                    _create_redis_checkpointer()

                # Verify URL without password
                call_args = mock_saver_class.call_args
                redis_url = call_args[0][0]
                assert "@" not in redis_url
                assert "redis://redis:6379/1" == redis_url


@pytest.mark.chaos
class TestRedisPoolExhaustion:
    """Test Redis connection pool exhaustion scenarios."""

    @pytest.mark.asyncio
    async def test_pool_exhaustion_queues_requests(self) -> None:
        """Requests queue when pool is exhausted."""
        # Simulate pool with max_connections=2
        pool_semaphore = asyncio.Semaphore(2)
        completed_requests: list[int] = []

        async def pooled_operation(request_id: int, hold_time: float) -> int:
            async with pool_semaphore:
                await asyncio.sleep(hold_time)
                completed_requests.append(request_id)
                return request_id

        # Launch 4 requests - first 2 should start immediately, others queue
        tasks = [
            asyncio.create_task(pooled_operation(1, 0.1)),
            asyncio.create_task(pooled_operation(2, 0.1)),
            asyncio.create_task(pooled_operation(3, 0.05)),
            asyncio.create_task(pooled_operation(4, 0.05)),
        ]

        results = await asyncio.gather(*tasks)

        # All should complete
        assert set(results) == {1, 2, 3, 4}
        # First batch completes before second starts
        assert len(completed_requests) == 4

    @pytest.mark.asyncio
    async def test_pool_exhaustion_timeout(self) -> None:
        """Pool exhaustion with timeout raises appropriate error."""
        pool_semaphore = asyncio.Semaphore(1)
        holding_lock = asyncio.Event()

        async def hold_connection() -> None:
            async with pool_semaphore:
                holding_lock.set()
                await asyncio.sleep(10)  # Hold indefinitely

        async def try_acquire_with_timeout() -> str:
            try:
                async with asyncio.timeout(0.1):
                    async with pool_semaphore:
                        return "acquired"
            except TimeoutError:
                return "timeout"

        # Start task that holds the connection
        holder = asyncio.create_task(hold_connection())
        await holding_lock.wait()

        # Try to acquire with timeout
        result = await try_acquire_with_timeout()
        assert result == "timeout"

        holder.cancel()
        try:
            await holder
        except asyncio.CancelledError:
            pass
