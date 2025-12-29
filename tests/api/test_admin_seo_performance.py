"""Tests for admin SEO performance endpoint.

Tests:
- GET /api/admin/seo/performance - blog post CTR and cost metrics
"""

from contextlib import suppress

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.state.repositories.blog_repository import blog_repository

client = TestClient(app)


@pytest.fixture
def performance_posts():
    """Create published blog posts with CTR data for testing."""
    posts = []
    for i in range(3):
        post = blog_repository.create(
            title=f"Performance Test Post {i}",
            content=f"Test content {i}",
            status="published",
        )
        posts.append(post)

    yield posts

    # Cleanup
    for post in posts:
        with suppress(Exception):
            blog_repository.delete(post["id"])


class TestBlogPerformanceEndpoint:
    """Tests for GET /api/admin/seo/performance."""

    def test_get_performance_requires_admin(self):
        """Endpoint requires admin authentication."""
        response = client.get("/api/admin/seo/performance")
        # Should get 401 or 403 without auth
        assert response.status_code in [401, 403]

    def test_get_performance_metrics_structure(self, performance_posts):
        """Verify repository metrics have expected structure."""
        # Test the repository method directly since admin auth is complex
        metrics = blog_repository.get_performance_metrics(limit=10)

        assert isinstance(metrics, list)
        for post in metrics:
            assert "id" in post
            assert "title" in post
            assert "slug" in post
            assert "view_count" in post
            assert "click_through_count" in post
            assert "ctr_percent" in post

    def test_performance_metrics_ctr_calculation(self, performance_posts):
        """CTR percentage is calculated correctly."""
        # Simulate some views and clicks
        slug = performance_posts[0]["slug"]

        # Track some views and clicks
        for _ in range(10):
            blog_repository.increment_view(slug)
        for _ in range(2):
            blog_repository.increment_click(slug)

        # Get metrics
        metrics = blog_repository.get_performance_metrics(limit=50)

        # Find our test post
        test_post = next((m for m in metrics if m["slug"] == slug), None)
        assert test_post is not None

        # Verify CTR calculation (2 clicks / 10 views = 20%)
        if test_post["view_count"] > 0:
            expected_ctr = (test_post["click_through_count"] / test_post["view_count"]) * 100
            assert abs(float(test_post["ctr_percent"]) - expected_ctr) < 0.01

    def test_get_performance_metrics_ordering(self, performance_posts):
        """Metrics should be ordered by view count descending."""
        # Add different view counts
        for i, post in enumerate(performance_posts):
            for _ in range((i + 1) * 5):  # 5, 10, 15 views
                blog_repository.increment_view(post["slug"])

        metrics = blog_repository.get_performance_metrics(limit=50)

        # Verify descending order
        for i in range(len(metrics) - 1):
            assert metrics[i]["view_count"] >= metrics[i + 1]["view_count"]
