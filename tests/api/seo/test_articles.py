"""Tests for SEO blog article endpoints.

Validates:
- Pydantic model validation
- Article status values
- Update field validation
"""

from datetime import datetime

import pytest

from backend.api.seo.routes import (
    SeoBlogArticle,
    SeoBlogArticleListResponse,
    SeoBlogArticleUpdate,
)


@pytest.mark.unit
class TestSeoBlogArticleModels:
    """Test SeoBlogArticle Pydantic models."""

    def test_article_valid_fields(self):
        """Valid article should pass validation."""
        article = SeoBlogArticle(
            id=1,
            topic_id=10,
            title="Test Article",
            excerpt="A short excerpt",
            content="# Article Content\n\nThis is the body.",
            meta_title="SEO Title",
            meta_description="SEO description for search engines",
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert article.id == 1
        assert article.topic_id == 10
        assert article.title == "Test Article"
        assert article.status == "draft"

    def test_article_null_topic_id(self):
        """Article without topic_id is valid."""
        article = SeoBlogArticle(
            id=1,
            topic_id=None,
            title="Standalone Article",
            excerpt=None,
            content="Content here",
            meta_title=None,
            meta_description=None,
            status="published",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert article.topic_id is None
        assert article.status == "published"

    def test_article_null_optional_fields(self):
        """Article with null optional fields is valid."""
        article = SeoBlogArticle(
            id=1,
            topic_id=None,
            title="Minimal Article",
            excerpt=None,
            content="Content",
            meta_title=None,
            meta_description=None,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert article.excerpt is None
        assert article.meta_title is None
        assert article.meta_description is None


@pytest.mark.unit
class TestSeoBlogArticleUpdate:
    """Test SeoBlogArticleUpdate Pydantic models."""

    def test_update_title(self):
        """Title update should be valid."""
        req = SeoBlogArticleUpdate(title="New Title")
        assert req.title == "New Title"
        assert req.content is None
        assert req.status is None

    def test_update_content(self):
        """Content update should be valid."""
        req = SeoBlogArticleUpdate(content="Updated content here")
        assert req.content == "Updated content here"

    def test_update_status_draft(self):
        """Draft status should be valid."""
        req = SeoBlogArticleUpdate(status="draft")
        assert req.status == "draft"

    def test_update_status_published(self):
        """Published status should be valid."""
        req = SeoBlogArticleUpdate(status="published")
        assert req.status == "published"

    def test_update_multiple_fields(self):
        """Multiple field updates should be valid."""
        req = SeoBlogArticleUpdate(
            title="New Title",
            excerpt="New excerpt",
            content="New content",
            meta_title="New SEO Title",
            meta_description="New SEO description",
            status="published",
        )
        assert req.title == "New Title"
        assert req.excerpt == "New excerpt"
        assert req.content == "New content"
        assert req.meta_title == "New SEO Title"
        assert req.meta_description == "New SEO description"
        assert req.status == "published"

    def test_update_empty(self):
        """Empty update is valid (no changes)."""
        req = SeoBlogArticleUpdate()
        assert req.title is None
        assert req.content is None
        assert req.status is None

    def test_update_long_title(self):
        """Title at max length should be valid."""
        long_title = "a" * 255
        req = SeoBlogArticleUpdate(title=long_title)
        assert len(req.title) == 255

    def test_update_too_long_title_fails(self):
        """Title over max length should fail."""
        with pytest.raises(ValueError):
            SeoBlogArticleUpdate(title="a" * 256)

    def test_update_long_excerpt(self):
        """Excerpt at max length should be valid."""
        long_excerpt = "a" * 500
        req = SeoBlogArticleUpdate(excerpt=long_excerpt)
        assert len(req.excerpt) == 500

    def test_update_too_long_excerpt_fails(self):
        """Excerpt over max length should fail."""
        with pytest.raises(ValueError):
            SeoBlogArticleUpdate(excerpt="a" * 501)


@pytest.mark.unit
class TestSeoBlogArticleListResponse:
    """Test SeoBlogArticleListResponse model."""

    def test_empty_response(self):
        """Empty article list response is valid."""
        resp = SeoBlogArticleListResponse(
            articles=[],
            total=0,
            remaining_this_month=5,
        )
        assert len(resp.articles) == 0
        assert resp.total == 0
        assert resp.remaining_this_month == 5

    def test_response_with_articles(self):
        """Response with articles is valid."""
        article = SeoBlogArticle(
            id=1,
            topic_id=None,
            title="Test Article",
            excerpt="An excerpt",
            content="Content here",
            meta_title=None,
            meta_description=None,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        resp = SeoBlogArticleListResponse(
            articles=[article],
            total=1,
            remaining_this_month=-1,  # Unlimited
        )
        assert len(resp.articles) == 1
        assert resp.total == 1
        assert resp.remaining_this_month == -1
        assert resp.articles[0].title == "Test Article"

    def test_response_unlimited_remaining(self):
        """Unlimited remaining (-1) is valid."""
        resp = SeoBlogArticleListResponse(
            articles=[],
            total=0,
            remaining_this_month=-1,
        )
        assert resp.remaining_this_month == -1

    def test_response_zero_remaining(self):
        """Zero remaining is valid."""
        resp = SeoBlogArticleListResponse(
            articles=[],
            total=0,
            remaining_this_month=0,
        )
        assert resp.remaining_this_month == 0
