"""Tests for ContributionRepository recommendation operations.

Validates:
- save_recommendation() includes user_id in INSERT
- get_recommendations_by_session() retrieves with full DB fields
- user_id is auto-fetched from session when not provided
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


class TestSaveRecommendationWithUserId:
    """Test save_recommendation includes user_id."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with RealDictCursor-like behavior."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_save_recommendation_with_explicit_user_id(self, mock_connection, mock_cursor):
        """save_recommendation includes user_id when explicitly provided."""
        from bo1.state.repositories.contribution_repository import ContributionRepository

        # Mock return value from INSERT
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "session_id": "bo1_test123",
            "sub_problem_index": 0,
            "persona_code": "strategist",
            "user_id": "user_abc",
            "created_at": datetime.now(),
        }

        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = ContributionRepository()
            result = repo.save_recommendation(
                session_id="bo1_test123",
                persona_code="strategist",
                recommendation="Test recommendation",
                reasoning="Test reasoning",
                confidence=0.85,
                user_id="user_abc",
            )

        assert result["user_id"] == "user_abc"
        assert result["session_id"] == "bo1_test123"
        assert result["sub_problem_index"] == 0

        # Verify execute was called with user_id in the SQL
        execute_calls = mock_cursor.execute.call_args_list
        assert len(execute_calls) == 1  # Only INSERT, no session lookup

        sql, params = execute_calls[0][0]
        assert "user_id" in sql
        assert "user_abc" in params

    def test_save_recommendation_fetches_user_id_from_session(self, mock_connection, mock_cursor):
        """save_recommendation fetches user_id from session when not provided."""
        from bo1.state.repositories.contribution_repository import ContributionRepository

        # First call: fetch user_id from session
        # Second call: INSERT recommendation
        mock_cursor.fetchone.side_effect = [
            {"user_id": "user_from_session"},  # Session lookup
            {  # INSERT result
                "id": 2,
                "session_id": "bo1_test456",
                "sub_problem_index": None,
                "persona_code": "analyst",
                "user_id": "user_from_session",
                "created_at": datetime.now(),
            },
        ]

        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = ContributionRepository()
            result = repo.save_recommendation(
                session_id="bo1_test456",
                persona_code="analyst",
                recommendation="Analysis complete",
                reasoning="Based on data",
                confidence=0.75,
                # No user_id provided - should fetch from session
            )

        assert result["user_id"] == "user_from_session"

        # Verify session lookup was made first
        execute_calls = mock_cursor.execute.call_args_list
        assert len(execute_calls) == 2

        # First call should be session lookup
        first_sql = execute_calls[0][0][0]
        assert "SELECT user_id FROM sessions" in first_sql


class TestGetRecommendationsBySession:
    """Test get_recommendations_by_session method."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_get_recommendations_returns_all_db_fields(self, mock_connection, mock_cursor):
        """get_recommendations_by_session returns full DB-mapped fields."""
        from bo1.state.repositories.contribution_repository import ContributionRepository

        now = datetime.now()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "session_id": "bo1_sess_xyz",
                "sub_problem_index": 0,
                "persona_code": "ceo",
                "persona_name": "CEO",
                "recommendation": "Proceed with merger",
                "reasoning": "Strategic alignment",
                "confidence": Decimal("0.90"),
                "conditions": ["Board approval"],
                "weight": Decimal("1.20"),
                "user_id": "user_123",
                "created_at": now,
            },
            {
                "id": 2,
                "session_id": "bo1_sess_xyz",
                "sub_problem_index": 0,
                "persona_code": "cfo",
                "persona_name": "CFO",
                "recommendation": "Proceed with caution",
                "reasoning": "Financial concerns",
                "confidence": Decimal("0.70"),
                "conditions": ["Due diligence"],
                "weight": Decimal("1.00"),
                "user_id": "user_123",
                "created_at": now,
            },
        ]

        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = ContributionRepository()
            results = repo.get_recommendations_by_session("bo1_sess_xyz", user_id="user_123")

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["session_id"] == "bo1_sess_xyz"
        assert results[0]["sub_problem_index"] == 0
        assert results[0]["user_id"] == "user_123"
        assert results[0]["persona_code"] == "ceo"
        assert results[0]["recommendation"] == "Proceed with merger"

    def test_get_recommendations_filters_by_sub_problem(self, mock_connection, mock_cursor):
        """get_recommendations_by_session filters by sub_problem_index."""
        from bo1.state.repositories.contribution_repository import ContributionRepository

        mock_cursor.fetchall.return_value = []

        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = ContributionRepository()
            repo.get_recommendations_by_session(
                "bo1_sess_xyz", sub_problem_index=1, user_id="user_123"
            )

        # Verify SQL includes sub_problem_index filter
        execute_calls = mock_cursor.execute.call_args_list
        sql, params = execute_calls[0][0]
        assert "sub_problem_index = %s" in sql
        assert 1 in params

    def test_get_recommendations_passes_user_id_to_db_session(self, mock_connection, mock_cursor):
        """get_recommendations_by_session passes user_id to db_session for RLS."""
        from bo1.state.repositories.contribution_repository import ContributionRepository

        mock_cursor.fetchall.return_value = []

        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = ContributionRepository()
            repo.get_recommendations_by_session("bo1_sess_xyz", user_id="rls_user")

        # Verify db_session was called with user_id
        mock_db.assert_called_once_with(user_id="rls_user")
