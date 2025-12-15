"""Tests for CacheRepository delete_stale method.

Validates:
- delete_stale() removes old entries
- delete_stale() preserves recently accessed entries
- delete_stale() respects batch_size parameter
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
