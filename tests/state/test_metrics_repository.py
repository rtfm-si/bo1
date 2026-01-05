"""Unit tests for metrics_repository.

Tests:
- set_metric_relevance method
- get_business_metrics with include_irrelevant flag
"""

from unittest.mock import patch


class TestMetricsRepositoryRelevance:
    """Tests for metric relevance functionality."""

    def test_set_metric_relevance_predefined(self):
        """Test setting relevance on predefined metric."""
        from bo1.state.repositories.metrics_repository import MetricsRepository

        repo = MetricsRepository()

        # Mock the internal methods
        existing_metric = {
            "id": 1,
            "user_id": "user123",
            "metric_key": "mrr",
            "is_predefined": True,
            "is_relevant": True,
        }
        updated_metric = {**existing_metric, "is_relevant": False}

        with patch.object(repo, "get_user_metric", return_value=existing_metric):
            with patch.object(repo, "_execute_one", return_value=updated_metric) as mock_exec:
                result = repo.set_metric_relevance("user123", "mrr", False)

                assert result is not None
                assert result["is_relevant"] is False
                mock_exec.assert_called_once()
                call_args = mock_exec.call_args
                assert "is_relevant = %s" in call_args[0][0]
                assert call_args[0][1][0] is False  # is_relevant param

    def test_set_metric_relevance_not_found(self):
        """Test setting relevance on non-existent metric."""
        from bo1.state.repositories.metrics_repository import MetricsRepository

        repo = MetricsRepository()

        with patch.object(repo, "get_user_metric", return_value=None):
            result = repo.set_metric_relevance("user123", "nonexistent", False)
            assert result is None

    def test_set_metric_relevance_custom_metric_rejected(self):
        """Test setting relevance on custom metric returns None."""
        from bo1.state.repositories.metrics_repository import MetricsRepository

        repo = MetricsRepository()

        custom_metric = {
            "id": 1,
            "user_id": "user123",
            "metric_key": "custom_metric",
            "is_predefined": False,  # Custom metric
            "is_relevant": True,
        }

        with patch.object(repo, "get_user_metric", return_value=custom_metric):
            result = repo.set_metric_relevance("user123", "custom_metric", False)
            assert result is None

    def test_get_business_metrics_excludes_irrelevant_by_default(self):
        """Test get_business_metrics excludes irrelevant metrics by default."""
        from bo1.state.repositories.metrics_repository import MetricsRepository

        repo = MetricsRepository()

        with patch.object(repo, "_execute_query") as mock_exec:
            repo.get_business_metrics("user123")

            call_args = mock_exec.call_args[0][0]
            assert "is_relevant = TRUE" in call_args

    def test_get_business_metrics_includes_irrelevant_when_requested(self):
        """Test get_business_metrics includes irrelevant when flag is True."""
        from bo1.state.repositories.metrics_repository import MetricsRepository

        repo = MetricsRepository()

        with patch.object(repo, "_execute_query") as mock_exec:
            repo.get_business_metrics("user123", include_irrelevant=True)

            call_args = mock_exec.call_args[0][0]
            # Should NOT have is_relevant filter when including irrelevant
            assert "is_relevant = TRUE" not in call_args
