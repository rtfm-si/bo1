"""Tests for SEO topics CRUD endpoints.

Validates:
- Pydantic model validation
- Topic status values
- Authorization logic (tested at API level)
"""

import pytest

from backend.api.seo.routes import (
    SeoTopic,
    SeoTopicCreate,
    SeoTopicListResponse,
    SeoTopicUpdate,
)


@pytest.mark.unit
class TestSeoTopicModels:
    """Test SeoTopic Pydantic models."""

    def test_topic_create_valid_keyword(self):
        """Valid keyword should pass validation."""
        req = SeoTopicCreate(keyword="project management")
        assert req.keyword == "project management"
        assert req.source_analysis_id is None
        assert req.notes is None

    def test_topic_create_with_all_fields(self):
        """All fields should be accepted."""
        req = SeoTopicCreate(
            keyword="saas marketing",
            source_analysis_id=123,
            notes="High potential topic",
        )
        assert req.keyword == "saas marketing"
        assert req.source_analysis_id == 123
        assert req.notes == "High potential topic"

    def test_topic_create_empty_keyword_fails(self):
        """Empty keyword should fail validation."""
        with pytest.raises(ValueError):
            SeoTopicCreate(keyword="")

    def test_topic_create_long_keyword(self):
        """Keyword at max length should be valid."""
        long_keyword = "a" * 255
        req = SeoTopicCreate(keyword=long_keyword)
        assert len(req.keyword) == 255

    def test_topic_create_too_long_keyword_fails(self):
        """Keyword over max length should fail."""
        with pytest.raises(ValueError):
            SeoTopicCreate(keyword="a" * 256)

    def test_topic_create_long_notes(self):
        """Notes at max length should be valid."""
        long_notes = "a" * 1000
        req = SeoTopicCreate(keyword="test", notes=long_notes)
        assert len(req.notes) == 1000

    def test_topic_create_too_long_notes_fails(self):
        """Notes over max length should fail."""
        with pytest.raises(ValueError):
            SeoTopicCreate(keyword="test", notes="a" * 1001)

    def test_topic_update_status(self):
        """Status update should be valid."""
        req = SeoTopicUpdate(status="writing")
        assert req.status == "writing"
        assert req.notes is None

    def test_topic_update_notes(self):
        """Notes update should be valid."""
        req = SeoTopicUpdate(notes="Updated notes")
        assert req.status is None
        assert req.notes == "Updated notes"

    def test_topic_update_both_fields(self):
        """Both fields can be updated."""
        req = SeoTopicUpdate(status="published", notes="Published to blog")
        assert req.status == "published"
        assert req.notes == "Published to blog"

    def test_topic_update_empty(self):
        """Empty update is valid (no changes)."""
        req = SeoTopicUpdate()
        assert req.status is None
        assert req.notes is None

    def test_topic_update_clear_notes(self):
        """Notes can be set to empty string."""
        req = SeoTopicUpdate(notes="")
        assert req.notes == ""


@pytest.mark.unit
class TestSeoTopicStatus:
    """Test valid status values."""

    def test_valid_status_researched(self):
        """'researched' status should be accepted."""
        req = SeoTopicUpdate(status="researched")
        assert req.status == "researched"

    def test_valid_status_writing(self):
        """'writing' status should be accepted."""
        req = SeoTopicUpdate(status="writing")
        assert req.status == "writing"

    def test_valid_status_published(self):
        """'published' status should be accepted."""
        req = SeoTopicUpdate(status="published")
        assert req.status == "published"


@pytest.mark.unit
class TestSeoTopicListResponse:
    """Test SeoTopicListResponse model."""

    def test_empty_response(self):
        """Empty topic list response is valid."""
        resp = SeoTopicListResponse(topics=[], total=0)
        assert len(resp.topics) == 0
        assert resp.total == 0

    def test_response_with_topics(self):
        """Response with topics is valid."""
        from datetime import datetime

        topic = SeoTopic(
            id=1,
            keyword="test keyword",
            status="researched",
            source_analysis_id=None,
            notes=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        resp = SeoTopicListResponse(topics=[topic], total=1)
        assert len(resp.topics) == 1
        assert resp.total == 1
        assert resp.topics[0].keyword == "test keyword"
