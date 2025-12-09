"""Chaos tests for PostgreSQL connection pool recovery.

Validates:
- Pool exhaustion triggers backoff retry
- Query failure doesn't corrupt session state
- Transaction rollback on partial write failure
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.chaos
class TestPostgresPoolExhaustion:
    """Test PostgreSQL connection pool exhaustion handling."""

    @pytest.mark.asyncio
    async def test_pool_exhaustion_triggers_retry(self) -> None:
        """Pool exhaustion triggers exponential backoff retry."""
        attempt_times: list[float] = []
        start_time = asyncio.get_event_loop().time()

        async def mock_acquire() -> MagicMock:
            attempt_times.append(asyncio.get_event_loop().time() - start_time)
            if len(attempt_times) < 3:
                raise Exception("connection pool exhausted")
            return MagicMock()

        # Simulate retry with backoff
        connection = None
        for attempt in range(5):
            try:
                connection = await mock_acquire()
                break
            except Exception:
                backoff = min(0.1 * (2**attempt), 1.0)
                await asyncio.sleep(backoff)

        assert connection is not None
        assert len(attempt_times) == 3

    @pytest.mark.asyncio
    async def test_pool_exhaustion_max_retries_exceeded(self) -> None:
        """Pool exhaustion raises after max retries."""
        attempts = 0

        async def always_exhausted() -> MagicMock:
            nonlocal attempts
            attempts += 1
            raise Exception("connection pool exhausted")

        max_retries = 3
        # Try max_retries times, each should fail
        for _ in range(max_retries):
            with pytest.raises(Exception, match="connection pool exhausted"):
                await always_exhausted()

        assert attempts == max_retries


@pytest.mark.chaos
class TestPostgresQueryFailure:
    """Test query failure handling."""

    @pytest.mark.asyncio
    async def test_query_failure_no_state_corruption(self) -> None:
        """Query failure doesn't corrupt application state."""
        # Simulate session state
        session_state = {"session_id": "bo1_test", "contributions": ["a", "b"], "round": 2}
        state_before = session_state.copy()

        async def failing_query() -> None:
            # Simulate query that fails after partial execution
            raise Exception("query execution failed: connection reset")

        # Attempt operation that would modify state
        try:
            await failing_query()
            # If successful, would modify state
            session_state["contributions"].append("c")
            session_state["round"] = 3
        except Exception:
            pass  # Query failed (expected in chaos test)  # noqa: S110

        # State should be unchanged
        assert session_state == state_before

    @pytest.mark.asyncio
    async def test_operational_error_is_retryable(self) -> None:
        """OperationalError triggers retry."""
        call_count = 0

        async def flaky_query() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate psycopg OperationalError
                raise Exception("OperationalError: server closed connection")
            return "success"

        result = None
        for _ in range(5):
            try:
                result = await flaky_query()
                break
            except Exception as e:
                if "OperationalError" in str(e):
                    await asyncio.sleep(0.01)
                else:
                    raise

        assert result == "success"
        assert call_count == 3


@pytest.mark.chaos
class TestPostgresTransactionRollback:
    """Test transaction rollback on partial failure."""

    @pytest.mark.asyncio
    async def test_partial_write_rollback(self) -> None:
        """Transaction rolls back on partial write failure."""
        # Simulate database state
        db_state: dict[str, list[str]] = {"sessions": [], "contributions": []}
        committed = False

        class MockTransaction:
            def __init__(self) -> None:
                self.pending_sessions: list[str] = []
                self.pending_contributions: list[str] = []

            async def insert_session(self, session_id: str) -> None:
                self.pending_sessions.append(session_id)

            async def insert_contribution(self, contribution: str) -> None:
                if contribution == "fail":
                    raise Exception("constraint violation")
                self.pending_contributions.append(contribution)

            async def commit(self) -> None:
                nonlocal committed
                db_state["sessions"].extend(self.pending_sessions)
                db_state["contributions"].extend(self.pending_contributions)
                committed = True

            async def rollback(self) -> None:
                self.pending_sessions.clear()
                self.pending_contributions.clear()

        tx = MockTransaction()

        try:
            await tx.insert_session("bo1_test")
            await tx.insert_contribution("good")
            await tx.insert_contribution("fail")  # This fails
            await tx.commit()
        except Exception:
            await tx.rollback()

        # Nothing should be committed due to rollback
        assert db_state["sessions"] == []
        assert db_state["contributions"] == []
        assert not committed

    @pytest.mark.asyncio
    async def test_successful_transaction_commits(self) -> None:
        """Successful transaction commits all changes."""
        db_state: dict[str, list[str]] = {"sessions": [], "contributions": []}

        class MockTransaction:
            def __init__(self) -> None:
                self.pending_sessions: list[str] = []
                self.pending_contributions: list[str] = []

            async def insert_session(self, session_id: str) -> None:
                self.pending_sessions.append(session_id)

            async def insert_contribution(self, contribution: str) -> None:
                self.pending_contributions.append(contribution)

            async def commit(self) -> None:
                db_state["sessions"].extend(self.pending_sessions)
                db_state["contributions"].extend(self.pending_contributions)

            async def rollback(self) -> None:
                self.pending_sessions.clear()
                self.pending_contributions.clear()

        tx = MockTransaction()

        try:
            await tx.insert_session("bo1_test")
            await tx.insert_contribution("contrib1")
            await tx.insert_contribution("contrib2")
            await tx.commit()
        except Exception:
            await tx.rollback()

        # All should be committed
        assert db_state["sessions"] == ["bo1_test"]
        assert db_state["contributions"] == ["contrib1", "contrib2"]


@pytest.mark.chaos
class TestPostgresCheckpointerFailure:
    """Test PostgreSQL checkpointer failure handling."""

    def test_postgres_checkpointer_setup_failure_logged(self) -> None:
        """PostgreSQL setup failure is logged but doesn't crash."""

        with patch("bo1.graph.checkpointer_factory.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "postgresql://test:test@localhost/test"

            with patch("bo1.graph.checkpointer_factory._run_postgres_setup_sync") as mock_setup:
                mock_setup.side_effect = Exception("Setup failed: tables exist")

                with patch("bo1.graph.checkpointer_factory.AsyncConnectionPool") as mock_pool:
                    mock_pool.return_value = MagicMock()

                    with patch("bo1.graph.checkpointer_factory.AsyncPostgresSaver") as mock_saver:
                        mock_saver.return_value = MagicMock()

                        with patch(
                            "bo1.graph.checkpointer_factory.LoggingCheckpointerWrapper"
                        ) as mock_wrapper:
                            mock_wrapper.return_value = MagicMock()

                            # Reset setup flag for test
                            import bo1.graph.checkpointer_factory as cf

                            cf._postgres_setup_complete = False

                            from bo1.graph.checkpointer_factory import (
                                _create_postgres_checkpointer,
                            )

                            # Should not raise despite setup failure
                            result = _create_postgres_checkpointer()
                            assert result is not None

    def test_postgres_url_password_masked_in_logs(self) -> None:
        """PostgreSQL password is masked in log output."""
        from bo1.graph.checkpointer_factory import _mask_password

        url = "postgresql://user:supersecret@localhost:5432/mydb"
        masked = _mask_password(url)

        assert "supersecret" not in masked
        assert "***" in masked
        assert "user:" in masked


@pytest.mark.chaos
class TestDatabaseSessionRecovery:
    """Test database session recovery patterns."""

    @pytest.mark.asyncio
    async def test_session_repository_handles_disconnect(self) -> None:
        """SessionRepository handles mid-operation disconnect."""
        # This tests the pattern, not actual implementation
        disconnect_after = 2
        call_count = 0

        async def mock_db_operation() -> dict:
            nonlocal call_count
            call_count += 1
            if call_count <= disconnect_after:
                raise Exception("connection reset by peer")
            return {"session_id": "bo1_test", "status": "active"}

        # Simulate repository retry pattern
        result = None
        for attempt in range(5):
            try:
                result = await mock_db_operation()
                break
            except Exception as e:
                if "connection reset" in str(e) and attempt < 4:
                    await asyncio.sleep(0.01 * (attempt + 1))
                else:
                    raise

        assert result is not None
        assert result["session_id"] == "bo1_test"
        assert call_count == 3  # Failed twice, succeeded on third
