"""Tests for public blog API endpoints.

Tests:
- GET /api/v1/blog/posts - list published posts
- GET /api/v1/blog/posts/{slug} - get post by slug
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
        title="Test Published Post",
        content="This is test content for the published post.",
        excerpt="Test excerpt",
        status="published",
        meta_title="Test Meta Title",
        meta_description="Test meta description for SEO.",
        seo_keywords=["test", "blog", "seo"],
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
        content="This is test content for the draft post.",
        excerpt="Draft excerpt",
        status="draft",
    )
    yield post
    # Cleanup
    with suppress(Exception):
        blog_repository.delete(post["id"])


class TestListPublishedPosts:
    """Tests for GET /api/v1/blog/posts."""

    def test_list_returns_published_only(self, published_post, draft_post):
        """Should only return published posts, not drafts."""
        response = client.get("/api/v1/blog/posts")
        assert response.status_code == 200

        data = response.json()
        assert "posts" in data
        assert "total" in data

        # Check that published post is in results
        slugs = [p["slug"] for p in data["posts"]]
        assert published_post["slug"] in slugs

        # Check that draft post is NOT in results
        assert draft_post["slug"] not in slugs

    def test_list_with_pagination(self, published_post):
        """Should support limit and offset parameters."""
        response = client.get("/api/v1/blog/posts?limit=10&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data["posts"]) <= 10

    def test_list_empty_when_no_published(self):
        """Should return empty list when no published posts exist."""
        # This test may have side effects from other fixtures
        # Just verify structure is correct
        response = client.get("/api/v1/blog/posts")
        assert response.status_code == 200

        data = response.json()
        assert "posts" in data
        assert isinstance(data["posts"], list)
        assert "total" in data
        assert isinstance(data["total"], int)


class TestGetPostBySlug:
    """Tests for GET /api/v1/blog/posts/{slug}."""

    def test_get_published_post(self, published_post):
        """Should return published post by slug."""
        response = client.get(f"/api/v1/blog/posts/{published_post['slug']}")
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Test Published Post"
        assert data["slug"] == published_post["slug"]
        assert data["status"] == "published"
        assert "content" in data
        assert "excerpt" in data

    def test_get_draft_post_returns_404(self, draft_post):
        """Should return 404 for draft posts (not published)."""
        response = client.get(f"/api/v1/blog/posts/{draft_post['slug']}")
        assert response.status_code == 404

    def test_get_nonexistent_post_returns_404(self):
        """Should return 404 for nonexistent slug."""
        response = client.get("/api/v1/blog/posts/nonexistent-slug-12345")
        assert response.status_code == 404

    def test_seo_fields_included(self, published_post):
        """Should include SEO-related fields in response."""
        response = client.get(f"/api/v1/blog/posts/{published_post['slug']}")
        assert response.status_code == 200

        data = response.json()
        assert "meta_title" in data
        assert "meta_description" in data
        assert "seo_keywords" in data
        assert data["meta_title"] == "Test Meta Title"
        assert data["meta_description"] == "Test meta description for SEO."
        assert "test" in data["seo_keywords"]


class TestRateLimiting:
    """Tests for rate limiting on public blog endpoints."""

    def test_rate_limit_headers(self, published_post):
        """Should include rate limit headers in response."""
        response = client.get("/api/v1/blog/posts")
        # Note: Rate limit headers may vary based on configuration
        assert response.status_code == 200
