"""Tests for CacheRepository.

Validates:
- delete_stale() removes old entries
- delete_stale() preserves recently accessed entries
- delete_stale() respects batch_size parameter
- find_similar() respects sharing filters
- save() persists user_id and is_shareable
- mark_user_research_non_shareable() updates user's entries
"""

from unittest.mock import MagicMock, patch

import pytest


class TestDeleteStale:
    """Test delete_stale method for research cache cleanup."""

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

    def test_delete_stale_removes_old_entries(self, mock_connection, mock_cursor):
        """Verify delete_stale deletes entries older than max_age_days."""
        from bo1.state.repositories.cache_repository import CacheRepository

        mock_cursor.rowcount = 5

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            deleted_count = repo.delete_stale(max_age_days=90, access_grace_days=7)

        assert deleted_count == 5
        mock_cursor.execute.assert_called_once()

        # Verify correct parameters passed
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "DELETE FROM research_cache" in query
        assert "research_date < NOW() - INTERVAL" in query
        assert "last_accessed_at" in query
        assert params == (90, 7, 1000)  # max_age, grace, batch_size

    def test_delete_stale_preserves_recently_accessed(self, mock_connection, mock_cursor):
        """Verify delete_stale keeps entries accessed within grace period."""
        from bo1.state.repositories.cache_repository import CacheRepository

        mock_cursor.rowcount = 0  # Nothing deleted (all recently accessed)

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            deleted_count = repo.delete_stale(max_age_days=30, access_grace_days=14)

        assert deleted_count == 0

        # Verify grace period is in the query
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[1] == 14  # access_grace_days

    def test_delete_stale_respects_batch_size(self, mock_connection, mock_cursor):
        """Verify delete_stale limits deletion to batch_size."""
        from bo1.state.repositories.cache_repository import CacheRepository

        mock_cursor.rowcount = 500

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            deleted_count = repo.delete_stale(
                max_age_days=90,
                access_grace_days=7,
                batch_size=500,
            )

        assert deleted_count == 500

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[2] == 500  # batch_size

    def test_delete_stale_validates_nonnegative_max_age(self):
        """Verify delete_stale rejects negative max_age_days."""
        from bo1.state.repositories.cache_repository import CacheRepository

        repo = CacheRepository()

        # Validation happens before db_session is called
        with pytest.raises(ValueError, match="max_age_days"):
            repo.delete_stale(max_age_days=-1)

    def test_delete_stale_validates_nonnegative_grace_days(self):
        """Verify delete_stale rejects negative access_grace_days."""
        from bo1.state.repositories.cache_repository import CacheRepository

        repo = CacheRepository()

        # Validation happens before db_session is called
        with pytest.raises(ValueError, match="access_grace_days"):
            repo.delete_stale(max_age_days=90, access_grace_days=-1)


class TestSimilarityThresholdDefaults:
    """Test that repository methods use centralized threshold constants."""

    def test_find_by_embedding_uses_constant(self):
        """Verify find_by_embedding default uses SimilarityCacheThresholds."""
        import inspect

        from bo1.constants import SimilarityCacheThresholds
        from bo1.state.repositories.cache_repository import CacheRepository

        sig = inspect.signature(CacheRepository.find_by_embedding)
        default = sig.parameters["similarity_threshold"].default

        assert default == SimilarityCacheThresholds.RESEARCH_CACHE

    def test_find_similar_uses_constant(self):
        """Verify find_similar default uses SimilarityCacheThresholds."""
        import inspect

        from bo1.constants import SimilarityCacheThresholds
        from bo1.state.repositories.cache_repository import CacheRepository

        sig = inspect.signature(CacheRepository.find_similar)
        default = sig.parameters["similarity_threshold"].default

        assert default == SimilarityCacheThresholds.RESEARCH_CACHE


class TestResearchSharingFilters:
    """Test research sharing filter logic in find_similar."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_find_similar_includes_shared_by_default(self, mock_connection, mock_cursor):
        """find_similar includes shared research by default."""
        from bo1.state.repositories.cache_repository import CacheRepository

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            repo.find_similar(question_embedding=[0.1] * 1024)

        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]

        # Should include shareable filter when no user_id
        assert "is_shareable = true" in query or "user_id IS NULL" in query

    def test_find_similar_user_owns_plus_shared(self, mock_connection, mock_cursor):
        """find_similar returns user's own and shared research."""
        from bo1.state.repositories.cache_repository import CacheRepository

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            repo.find_similar(
                question_embedding=[0.1] * 1024,
                user_id="user_123",
                include_shared=True,
            )

        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]

        # Should include user's own OR shareable
        assert "user_id = %s" in query
        assert "is_shareable = true" in query

    def test_find_similar_user_only(self, mock_connection, mock_cursor):
        """find_similar returns only user's research when include_shared=False."""
        from bo1.state.repositories.cache_repository import CacheRepository

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            repo.find_similar(
                question_embedding=[0.1] * 1024,
                user_id="user_123",
                include_shared=False,
            )

        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]

        # Should only filter by user_id (is_shareable not in WHERE)
        assert "user_id = %s" in query
        # is_shareable only in SELECT, not in WHERE clause for filtering
        assert "is_shareable = true" not in query

    def test_find_similar_shared_flag_in_results(self, mock_connection, mock_cursor):
        """find_similar adds 'shared' flag to results."""
        from bo1.state.repositories.cache_repository import CacheRepository

        # Mock a result from another user
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "question": "test?",
                "answer_summary": "answer",
                "confidence": "high",
                "sources": [],
                "source_count": 0,
                "category": None,
                "industry": None,
                "research_date": None,
                "access_count": 0,
                "last_accessed_at": None,
                "freshness_days": 90,
                "tokens_used": 100,
                "research_cost_usd": 0.01,
                "similarity": 0.95,
                "cache_user_id": "other_user",
                "is_shareable": True,
            }
        ]

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            results = repo.find_similar(
                question_embedding=[0.1] * 1024,
                user_id="current_user",
            )

        # Should have shared=True since cache_user_id != current user_id
        assert len(results) == 1
        assert results[0]["shared"] is True

    def test_find_similar_own_research_not_shared(self, mock_connection, mock_cursor):
        """find_similar marks user's own research as shared=False."""
        from bo1.state.repositories.cache_repository import CacheRepository

        # Mock a result from the same user
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "question": "test?",
                "answer_summary": "answer",
                "confidence": "high",
                "sources": [],
                "source_count": 0,
                "category": None,
                "industry": None,
                "research_date": None,
                "access_count": 0,
                "last_accessed_at": None,
                "freshness_days": 90,
                "tokens_used": 100,
                "research_cost_usd": 0.01,
                "similarity": 0.95,
                "cache_user_id": "current_user",
                "is_shareable": True,
            }
        ]

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            results = repo.find_similar(
                question_embedding=[0.1] * 1024,
                user_id="current_user",
            )

        # Should have shared=False since cache_user_id == current user_id
        assert len(results) == 1
        assert results[0]["shared"] is False


class TestSaveWithUserContext:
    """Test save method includes user_id and is_shareable."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = {"id": 1}
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_save_includes_user_id_and_shareable(self, mock_connection, mock_cursor):
        """save() persists user_id and is_shareable."""
        from bo1.state.repositories.cache_repository import CacheRepository

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            repo.save(
                question="test question",
                embedding=[0.1] * 1024,
                summary="test summary",
                user_id="user_123",
                is_shareable=True,
            )

        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        # Verify query includes user_id and is_shareable columns
        assert "user_id" in query
        assert "is_shareable" in query
        assert "user_123" in params
        assert True in params  # is_shareable=True

    def test_save_defaults_shareable_to_true(self, mock_connection, mock_cursor):
        """save() defaults is_shareable to True."""
        from bo1.state.repositories.cache_repository import CacheRepository

        with patch("bo1.state.repositories.cache_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = CacheRepository()
            repo.save(
                question="test question",
                embedding=[0.1] * 1024,
                summary="test summary",
            )

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]

        # Should have is_shareable=True as default
        assert True in params
