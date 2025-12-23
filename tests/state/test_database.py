"""Tests for database.py statement_timeout functionality.

Tests:
- SET LOCAL statement_timeout executed when parameter provided
- Timeout triggers QueryCanceled (SQLSTATE 57014)
- Timeout value correctly set from env var
- db_session_batch() uses default timeout
- _record_statement_timeout() increments metric
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestStatementTimeoutConfig:
    """Tests for StatementTimeoutConfig in constants.py."""

    def test_default_timeout_constant(self):
        """Default timeout should be 30 seconds (30000ms)."""
        from bo1.constants import StatementTimeoutConfig

        assert StatementTimeoutConfig.DEFAULT_TIMEOUT_MS == 30000

    def test_interactive_timeout_constant(self):
        """Interactive timeout should be 5 seconds (5000ms)."""
        from bo1.constants import StatementTimeoutConfig

        assert StatementTimeoutConfig.INTERACTIVE_TIMEOUT_MS == 5000

    def test_get_default_timeout_returns_constant(self):
        """get_default_timeout() returns constant when no env var."""
        from bo1.constants import StatementTimeoutConfig

        # Clear env var if set
        env_backup = os.environ.pop("DB_STATEMENT_TIMEOUT_MS", None)
        try:
            result = StatementTimeoutConfig.get_default_timeout()
            assert result == 30000
        finally:
            if env_backup:
                os.environ["DB_STATEMENT_TIMEOUT_MS"] = env_backup

    def test_get_default_timeout_from_env(self):
        """get_default_timeout() reads from env var when set."""
        from bo1.constants import StatementTimeoutConfig

        env_backup = os.environ.get("DB_STATEMENT_TIMEOUT_MS")
        try:
            os.environ["DB_STATEMENT_TIMEOUT_MS"] = "60000"
            # Force module reload to pick up env var
            result = StatementTimeoutConfig.get_default_timeout()
            assert result == 60000
        finally:
            if env_backup:
                os.environ["DB_STATEMENT_TIMEOUT_MS"] = env_backup
            else:
                os.environ.pop("DB_STATEMENT_TIMEOUT_MS", None)

    def test_get_interactive_timeout_returns_constant(self):
        """get_interactive_timeout() returns constant when no env var."""
        from bo1.constants import StatementTimeoutConfig

        env_backup = os.environ.pop("DB_INTERACTIVE_TIMEOUT_MS", None)
        try:
            result = StatementTimeoutConfig.get_interactive_timeout()
            assert result == 5000
        finally:
            if env_backup:
                os.environ["DB_INTERACTIVE_TIMEOUT_MS"] = env_backup

    def test_get_interactive_timeout_from_env(self):
        """get_interactive_timeout() reads from env var when set."""
        from bo1.constants import StatementTimeoutConfig

        env_backup = os.environ.get("DB_INTERACTIVE_TIMEOUT_MS")
        try:
            os.environ["DB_INTERACTIVE_TIMEOUT_MS"] = "10000"
            result = StatementTimeoutConfig.get_interactive_timeout()
            assert result == 10000
        finally:
            if env_backup:
                os.environ["DB_INTERACTIVE_TIMEOUT_MS"] = env_backup
            else:
                os.environ.pop("DB_INTERACTIVE_TIMEOUT_MS", None)


class TestDbSessionStatementTimeout:
    """Tests for db_session() statement_timeout_ms parameter."""

    @patch("bo1.state.database.get_connection_pool")
    @patch("bo1.state.pool_degradation.get_degradation_manager")
    def test_set_local_executed_when_timeout_provided(self, mock_manager, mock_get_pool):
        """SET LOCAL statement_timeout executed when statement_timeout_ms is provided."""
        from bo1.state.database import db_session

        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        mock_mgr = MagicMock()
        mock_mgr.should_shed_load.return_value = False
        mock_mgr.is_degraded.return_value = False
        mock_manager.return_value = mock_mgr

        # Execute with statement_timeout_ms
        with db_session(statement_timeout_ms=5000):
            pass

        # Verify SET LOCAL was called with correct value
        calls = mock_cursor.execute.call_args_list
        timeout_calls = [c for c in calls if "statement_timeout" in str(c)]
        assert len(timeout_calls) == 1
        assert timeout_calls[0][0][0] == "SET LOCAL statement_timeout = %s"
        assert timeout_calls[0][0][1] == (5000,)

    @patch("bo1.state.database.get_connection_pool")
    @patch("bo1.state.pool_degradation.get_degradation_manager")
    def test_no_set_local_when_timeout_none(self, mock_manager, mock_get_pool):
        """SET LOCAL statement_timeout not executed when statement_timeout_ms is None."""
        from bo1.state.database import db_session

        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        mock_mgr = MagicMock()
        mock_mgr.should_shed_load.return_value = False
        mock_mgr.is_degraded.return_value = False
        mock_manager.return_value = mock_mgr

        # Execute without statement_timeout_ms
        with db_session():
            pass

        # Verify SET LOCAL statement_timeout was NOT called
        calls = mock_cursor.execute.call_args_list
        timeout_calls = [c for c in calls if "statement_timeout" in str(c)]
        assert len(timeout_calls) == 0

    @patch("bo1.state.database.get_connection_pool")
    @patch("bo1.state.pool_degradation.get_degradation_manager")
    def test_rls_and_timeout_both_set(self, mock_manager, mock_get_pool):
        """Both RLS context and statement_timeout can be set together."""
        from bo1.state.database import db_session

        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        mock_mgr = MagicMock()
        mock_mgr.should_shed_load.return_value = False
        mock_mgr.is_degraded.return_value = False
        mock_manager.return_value = mock_mgr

        # Execute with both user_id and statement_timeout_ms
        with db_session(user_id="user-123", statement_timeout_ms=10000):
            pass

        # Verify both SET LOCAL calls were made
        calls = mock_cursor.execute.call_args_list
        rls_calls = [c for c in calls if "current_user_id" in str(c)]
        timeout_calls = [c for c in calls if "statement_timeout" in str(c)]

        assert len(rls_calls) == 1
        assert len(timeout_calls) == 1

        # RLS should be set before timeout (order matters for isolation)
        rls_index = next(i for i, c in enumerate(calls) if "current_user_id" in str(c))
        timeout_index = next(i for i, c in enumerate(calls) if "statement_timeout" in str(c))
        assert rls_index < timeout_index

    @patch("bo1.state.database._record_statement_timeout")
    @patch("bo1.state.database.get_connection_pool")
    @patch("bo1.state.pool_degradation.get_degradation_manager")
    def test_query_canceled_records_metric(self, mock_manager, mock_get_pool, mock_record):
        """QueryCanceled (SQLSTATE 57014) increments metric."""
        from bo1.state.database import db_session

        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        mock_mgr = MagicMock()
        mock_mgr.should_shed_load.return_value = False
        mock_mgr.is_degraded.return_value = False
        mock_manager.return_value = mock_mgr

        # Create custom exception with pgcode attribute for testing
        # (psycopg2.OperationalError has readonly pgcode)
        class QueryCanceledError(Exception):
            pgcode = "57014"

        # Make the context manager body raise the error
        with pytest.raises(QueryCanceledError):
            with db_session(statement_timeout_ms=100):
                raise QueryCanceledError("canceling statement due to statement timeout")

        # Verify metric was recorded
        mock_record.assert_called_once()


class TestDbSessionBatch:
    """Tests for db_session_batch() convenience wrapper."""

    @patch("bo1.state.database.db_session")
    def test_uses_default_timeout(self, mock_db_session):
        """db_session_batch() calls db_session with default timeout."""
        from bo1.constants import StatementTimeoutConfig
        from bo1.state.database import db_session_batch

        mock_db_session.return_value.__enter__ = MagicMock()
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        with db_session_batch():
            pass

        mock_db_session.assert_called_once()
        call_kwargs = mock_db_session.call_args.kwargs
        assert call_kwargs["statement_timeout_ms"] == StatementTimeoutConfig.get_default_timeout()

    @patch("bo1.state.database.db_session")
    def test_defaults_to_allow_degraded_true(self, mock_db_session):
        """db_session_batch() defaults to allow_degraded=True."""
        from bo1.state.database import db_session_batch

        mock_db_session.return_value.__enter__ = MagicMock()
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        with db_session_batch():
            pass

        call_kwargs = mock_db_session.call_args.kwargs
        assert call_kwargs["allow_degraded"] is True

    @patch("bo1.state.database.db_session")
    def test_passes_user_id(self, mock_db_session):
        """db_session_batch() passes user_id parameter."""
        from bo1.state.database import db_session_batch

        mock_db_session.return_value.__enter__ = MagicMock()
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        with db_session_batch(user_id="test-user"):
            pass

        call_kwargs = mock_db_session.call_args.kwargs
        assert call_kwargs["user_id"] == "test-user"


class TestRecordStatementTimeout:
    """Tests for _record_statement_timeout() helper."""

    @patch("backend.api.middleware.metrics.bo1_db_statement_timeout_total")
    def test_increments_counter(self, mock_counter):
        """_record_statement_timeout() increments Prometheus counter."""
        from bo1.state.database import _record_statement_timeout

        _record_statement_timeout()
        mock_counter.inc.assert_called_once()

    def test_handles_import_error_gracefully(self):
        """_record_statement_timeout() handles missing metrics gracefully."""
        from bo1.state.database import _record_statement_timeout

        # Patch the import to fail
        with patch.dict("sys.modules", {"backend.api.middleware.metrics": None}):
            # Should not raise even if import fails
            _record_statement_timeout()


class TestExecuteQueryStatementTimeout:
    """Tests for execute_query() statement_timeout_ms parameter."""

    @patch("backend.api.utils.db_helpers.db_session")
    def test_passes_timeout_to_db_session(self, mock_db_session):
        """execute_query() passes statement_timeout_ms to db_session."""
        from backend.api.utils.db_helpers import execute_query

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        execute_query("SELECT 1", fetch="all", statement_timeout_ms=15000)

        mock_db_session.assert_called_once()
        call_kwargs = mock_db_session.call_args.kwargs
        assert call_kwargs["statement_timeout_ms"] == 15000

    @patch("backend.api.utils.db_helpers.db_session")
    def test_timeout_none_by_default(self, mock_db_session):
        """execute_query() defaults statement_timeout_ms to None."""
        from backend.api.utils.db_helpers import execute_query

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        execute_query("SELECT 1", fetch="all")

        call_kwargs = mock_db_session.call_args.kwargs
        assert call_kwargs["statement_timeout_ms"] is None
