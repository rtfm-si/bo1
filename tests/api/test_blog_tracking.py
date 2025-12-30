"""Tests for blog post view and click tracking endpoints.

Tests:
- POST /api/v1/blog/posts/{slug}/view - track page views
- POST /api/v1/blog/posts/{slug}/click - track CTA clicks
"""

from contextlib import suppress

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.state.repositories.blog_repository import blog_repository

client = TestClient(app)


@pytest.fixture
def published_post():
    """Create a published blog post for testing."""
    post = blog_repository.create(
        title="Test Tracking Post",
        content="This is test content for tracking.",
        excerpt="Test excerpt",
        status="published",
    )
    yield post
    # Cleanup
    with suppress(Exception):
        blog_repository.delete(post["id"])


@pytest.fixture
def draft_post():
    """Create a draft blog post for testing."""
    post = blog_repository.create(
        title="Test Draft Post",
        content="This is draft content.",
        status="draft",
    )
    yield post
    # Cleanup
    with suppress(Exception):
        blog_repository.delete(post["id"])


class TestBlogViewTracking:
    """Tests for view tracking endpoint."""

    def test_track_view_success(self, published_post):
        """Track view increments view count."""
        slug = published_post["slug"]

        # Track view
        response = client.post(f"/api/v1/blog/posts/{slug}/view")
        assert response.status_code == 204

        # Verify increment (get fresh data)
        updated = blog_repository.get_by_slug(slug)
        assert updated is not None
        # View count should be at least 1 (may be higher if other tests ran)
        assert updated.get("view_count", 0) >= 1

    def test_track_view_not_found(self):
        """Track view returns 404 for missing post."""
        response = client.post("/api/v1/blog/posts/nonexistent-post-xyz/view")
        assert response.status_code == 404

    def test_track_view_draft_not_found(self, draft_post):
        """Track view returns 404 for draft posts."""
        slug = draft_post["slug"]
        response = client.post(f"/api/v1/blog/posts/{slug}/view")
        assert response.status_code == 404

    def test_track_view_multiple(self, published_post):
        """Multiple view tracks increment correctly."""
        slug = published_post["slug"]

        # Get initial count
        initial = blog_repository.get_by_slug(slug)
        initial_count = initial.get("view_count", 0) if initial else 0

        # Track multiple views
        for _ in range(3):
            response = client.post(f"/api/v1/blog/posts/{slug}/view")
            assert response.status_code == 204

        # Verify total increment
        updated = blog_repository.get_by_slug(slug)
        assert updated is not None
        assert updated.get("view_count", 0) >= initial_count + 3


class TestBlogClickTracking:
    """Tests for click tracking endpoint."""

    def test_track_click_success(self, published_post):
        """Track click increments click count."""
        slug = published_post["slug"]

        # Track click
        response = client.post(f"/api/v1/blog/posts/{slug}/click")
        assert response.status_code == 204

        # Verify increment
        updated = blog_repository.get_by_slug(slug)
        assert updated is not None
        assert updated.get("click_through_count", 0) >= 1

    def test_track_click_not_found(self):
        """Track click returns 404 for missing post."""
        response = client.post("/api/v1/blog/posts/nonexistent-post-xyz/click")
        assert response.status_code == 404

    def test_track_click_draft_not_found(self, draft_post):
        """Track click returns 404 for draft posts."""
        slug = draft_post["slug"]
        response = client.post(f"/api/v1/blog/posts/{slug}/click")
        assert response.status_code == 404
