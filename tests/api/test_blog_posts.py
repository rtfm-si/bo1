"""Tests for blog post API endpoints.

Tests:
- Blog post CRUD operations
- Status transitions (draft -> scheduled -> published)
- AI generation endpoint
- Topic discovery endpoint
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.blog import router
from backend.api.middleware.admin import require_admin_any


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with blog router and admin auth override."""
    test_app = FastAPI()
    test_app.dependency_overrides[require_admin_any] = mock_admin_override
    test_app.include_router(router, prefix="/api/admin")
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_post():
    """Sample blog post data."""
    return {
        "id": "test-post-id",
        "title": "Test Blog Post",
        "slug": "test-blog-post",
        "content": "# Test\n\nThis is test content.",
        "excerpt": "Test excerpt",
        "status": "draft",
        "published_at": None,
        "seo_keywords": ["test", "blog"],
        "generated_by_topic": None,
        "meta_title": "Test Meta Title",
        "meta_description": "Test meta description",
        "author_id": "user-123",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }


# ============================================================================
# List Posts
# ============================================================================


class TestListPosts:
    """Tests for GET /api/admin/blog/posts."""

    def test_list_posts_success(self, client, sample_post):
        """Test listing blog posts."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.list.return_value = [sample_post]
            mock_repo.count.return_value = 1

            response = client.get("/api/admin/blog/posts")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["posts"]) == 1
        assert data["posts"][0]["title"] == "Test Blog Post"

    def test_list_posts_with_status_filter(self, client, sample_post):
        """Test listing posts with status filter."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.list.return_value = [sample_post]
            mock_repo.count.return_value = 1

            response = client.get("/api/admin/blog/posts?status=draft")

        assert response.status_code == 200
        mock_repo.list.assert_called_with(status="draft", limit=50, offset=0)


# ============================================================================
# Create Post
# ============================================================================


class TestCreatePost:
    """Tests for POST /api/admin/blog/posts."""

    def test_create_post_success(self, client, sample_post):
        """Test creating a blog post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.create.return_value = sample_post

            response = client.post(
                "/api/admin/blog/posts",
                json={
                    "title": "Test Blog Post",
                    "content": "# Test\n\nThis is test content.",
                    "excerpt": "Test excerpt",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Blog Post"
        assert data["status"] == "draft"

    def test_create_post_with_schedule(self, client, sample_post):
        """Test creating a scheduled post."""
        future_date = datetime.now(UTC) + timedelta(days=7)
        scheduled_post = {**sample_post, "status": "scheduled", "published_at": future_date}

        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.create.return_value = scheduled_post

            response = client.post(
                "/api/admin/blog/posts",
                json={
                    "title": "Scheduled Post",
                    "content": "Content",
                    "status": "scheduled",
                    "published_at": future_date.isoformat(),
                },
            )

        assert response.status_code == 200
        assert response.json()["status"] == "scheduled"

    def test_create_post_invalid_status(self, client):
        """Test creating post with invalid status."""
        response = client.post(
            "/api/admin/blog/posts",
            json={
                "title": "Test",
                "content": "Content",
                "status": "invalid",
            },
        )

        assert response.status_code == 422


# ============================================================================
# Get Post
# ============================================================================


class TestGetPost:
    """Tests for GET /api/admin/blog/posts/{id}."""

    def test_get_post_success(self, client, sample_post):
        """Test getting a single post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.get_by_id.return_value = sample_post

            response = client.get("/api/admin/blog/posts/test-post-id")

        assert response.status_code == 200
        assert response.json()["title"] == "Test Blog Post"

    def test_get_post_not_found(self, client):
        """Test getting non-existent post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.get_by_id.return_value = None

            response = client.get("/api/admin/blog/posts/nonexistent")

        assert response.status_code == 404


# ============================================================================
# Update Post
# ============================================================================


class TestUpdatePost:
    """Tests for PATCH /api/admin/blog/posts/{id}."""

    def test_update_post_success(self, client, sample_post):
        """Test updating a post."""
        updated_post = {**sample_post, "title": "Updated Title"}

        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.update.return_value = updated_post

            response = client.patch(
                "/api/admin/blog/posts/test-post-id",
                json={"title": "Updated Title"},
            )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_post_not_found(self, client):
        """Test updating non-existent post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.update.return_value = None

            response = client.patch(
                "/api/admin/blog/posts/nonexistent",
                json={"title": "Updated"},
            )

        assert response.status_code == 404


# ============================================================================
# Delete Post
# ============================================================================


class TestDeletePost:
    """Tests for DELETE /api/admin/blog/posts/{id}."""

    def test_delete_post_success(self, client):
        """Test deleting a post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.delete.return_value = True

            response = client.delete("/api/admin/blog/posts/test-post-id")

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_delete_post_not_found(self, client):
        """Test deleting non-existent post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.delete.return_value = False

            response = client.delete("/api/admin/blog/posts/nonexistent")

        assert response.status_code == 404


# ============================================================================
# Publish Post
# ============================================================================


class TestPublishPost:
    """Tests for POST /api/admin/blog/posts/{id}/publish."""

    def test_publish_post_success(self, client, sample_post):
        """Test publishing a post."""
        published_post = {**sample_post, "status": "published", "published_at": datetime.now(UTC)}

        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.publish.return_value = published_post

            response = client.post("/api/admin/blog/posts/test-post-id/publish")

        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_publish_post_not_found(self, client):
        """Test publishing non-existent post."""
        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.publish.return_value = None

            response = client.post("/api/admin/blog/posts/nonexistent/publish")

        assert response.status_code == 404


# ============================================================================
# Schedule Post
# ============================================================================


class TestSchedulePost:
    """Tests for POST /api/admin/blog/posts/{id}/schedule."""

    def test_schedule_post_success(self, client, sample_post):
        """Test scheduling a post."""
        future_date = datetime.now(UTC) + timedelta(days=7)
        scheduled_post = {**sample_post, "status": "scheduled", "published_at": future_date}

        with patch("backend.api.admin.blog.blog_repository") as mock_repo:
            mock_repo.schedule.return_value = scheduled_post

            response = client.post(
                "/api/admin/blog/posts/test-post-id/schedule",
                json={"published_at": future_date.isoformat()},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "scheduled"

    def test_schedule_post_missing_date(self, client):
        """Test scheduling without date."""
        response = client.post(
            "/api/admin/blog/posts/test-post-id/schedule",
            json={},
        )

        assert response.status_code == 400


# ============================================================================
# Generate Post
# ============================================================================


class TestGeneratePost:
    """Tests for POST /api/admin/blog/generate."""

    def test_generate_post_success(self, client, sample_post):
        """Test AI blog post generation."""
        from backend.services.content_generator import BlogContent

        mock_content = BlogContent(
            title="Generated Title",
            excerpt="Generated excerpt",
            content="# Generated content",
            meta_title="Meta title",
            meta_description="Meta description",
        )

        generated_post = {
            **sample_post,
            "title": "Generated Title",
            "generated_by_topic": "Test topic",
        }

        with (
            patch("backend.api.admin.blog.generate_blog_post", new_callable=AsyncMock) as mock_gen,
            patch("backend.api.admin.blog.blog_repository") as mock_repo,
        ):
            mock_gen.return_value = mock_content
            mock_repo.create.return_value = generated_post

            response = client.post(
                "/api/admin/blog/generate",
                json={"topic": "Test topic", "keywords": ["test", "blog"]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Generated Title"


# ============================================================================
# Discover Topics
# ============================================================================


class TestDiscoverTopics:
    """Tests for GET /api/admin/blog/topics."""

    def test_discover_topics_success(self, client):
        """Test topic discovery."""
        from backend.services.topic_discovery import Topic

        mock_topics = [
            Topic(
                title="AI in Business",
                description="How AI transforms decision-making",
                keywords=["AI", "business", "decisions"],
                relevance_score=0.95,
                source="context",
            )
        ]

        with (
            patch(
                "backend.api.admin.blog.discover_topics", new_callable=AsyncMock
            ) as mock_discover,
            patch("backend.api.admin.blog.blog_repository") as mock_repo,
        ):
            mock_discover.return_value = mock_topics
            mock_repo.list.return_value = []

            response = client.get("/api/admin/blog/topics?industry=technology")

        assert response.status_code == 200
        data = response.json()
        assert len(data["topics"]) == 1
        assert data["topics"][0]["title"] == "AI in Business"

    def test_discover_topics_rate_limit_error(self, client):
        """Test topic discovery returns 429 on rate limit."""
        from backend.services.topic_discovery import TopicDiscoveryError

        with (
            patch(
                "backend.api.admin.blog.discover_topics", new_callable=AsyncMock
            ) as mock_discover,
            patch("backend.api.admin.blog.blog_repository") as mock_repo,
        ):
            mock_discover.side_effect = TopicDiscoveryError(
                "Rate limit exceeded", error_type="rate_limit"
            )
            mock_repo.list.return_value = []

            response = client.get("/api/admin/blog/topics")

        assert response.status_code == 429
        data = response.json()
        assert "Rate limit" in data["detail"]["message"]

    def test_discover_topics_parse_error(self, client):
        """Test topic discovery returns 500 on parse error."""
        from backend.services.topic_discovery import TopicDiscoveryError

        with (
            patch(
                "backend.api.admin.blog.discover_topics", new_callable=AsyncMock
            ) as mock_discover,
            patch("backend.api.admin.blog.blog_repository") as mock_repo,
        ):
            mock_discover.side_effect = TopicDiscoveryError(
                "Failed to parse LLM response", error_type="parse_error"
            )
            mock_repo.list.return_value = []

            response = client.get("/api/admin/blog/topics")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to parse" in data["detail"]["message"]

    def test_discover_topics_empty_list(self, client):
        """Test topic discovery with no results."""
        with (
            patch(
                "backend.api.admin.blog.discover_topics", new_callable=AsyncMock
            ) as mock_discover,
            patch("backend.api.admin.blog.blog_repository") as mock_repo,
        ):
            mock_discover.return_value = []
            mock_repo.list.return_value = []

            response = client.get("/api/admin/blog/topics")

        assert response.status_code == 200
        data = response.json()
        assert data["topics"] == []


# ============================================================================
# Topic Discovery Service Unit Tests
# ============================================================================


class TestTopicDiscoveryService:
    """Unit tests for backend/services/topic_discovery.py."""

    @pytest.mark.asyncio
    async def test_discover_topics_with_mocked_llm(self):
        """Test discover_topics with mocked LLM response."""
        from unittest.mock import MagicMock

        from backend.services.topic_discovery import Topic, discover_topics

        mock_response = """{
    "topics": [
        {
            "title": "Test Topic",
            "description": "Test description",
            "keywords": ["test", "mock"],
            "relevance_score": 0.9,
            "source": "context"
        }
    ]
}"""
        # Remove leading "{" since prefill adds it
        mock_response_body = mock_response[1:]

        with patch("backend.services.topic_discovery.ClaudeClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            # Use MagicMock (not AsyncMock) for the usage object since it's not awaited
            mock_usage = MagicMock()
            mock_usage.total_tokens = 100
            mock_usage.calculate_cost.return_value = 0.001
            mock_client.call = AsyncMock(return_value=(mock_response_body, mock_usage))

            topics = await discover_topics(industry="tech")

        assert len(topics) == 1
        assert isinstance(topics[0], Topic)
        assert topics[0].title == "Test Topic"
        assert topics[0].relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_discover_topics_invalid_json_retries(self):
        """Test discover_topics retries on invalid JSON."""
        from unittest.mock import MagicMock

        from backend.services.topic_discovery import TopicDiscoveryError, discover_topics

        with patch("backend.services.topic_discovery.ClaudeClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_usage = MagicMock()
            mock_usage.total_tokens = 100
            mock_usage.calculate_cost.return_value = 0.001
            # Return invalid JSON twice (max_attempts = 2)
            mock_client.call = AsyncMock(return_value=("invalid json", mock_usage))

            with pytest.raises(TopicDiscoveryError) as exc_info:
                await discover_topics()

            assert exc_info.value.error_type == "parse_error"
            assert mock_client.call.call_count == 2  # Retried once

    @pytest.mark.asyncio
    async def test_discover_topics_rate_limit(self):
        """Test discover_topics raises TopicDiscoveryError on rate limit."""
        from anthropic import RateLimitError

        from backend.services.topic_discovery import TopicDiscoveryError, discover_topics

        with patch("backend.services.topic_discovery.ClaudeClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.call = AsyncMock(
                side_effect=RateLimitError(
                    "rate limited",
                    response=AsyncMock(status_code=429),
                    body={"error": {"message": "rate limited"}},
                )
            )

            with pytest.raises(TopicDiscoveryError) as exc_info:
                await discover_topics()

            assert exc_info.value.error_type == "rate_limit"

    @pytest.mark.asyncio
    async def test_discover_topics_mock_mode(self):
        """Test discover_topics returns mock topics when enabled."""
        from backend.services.topic_discovery import MOCK_TOPICS, discover_topics

        with patch("backend.services.topic_discovery.USE_MOCK_TOPIC_DISCOVERY", True):
            topics = await discover_topics()

        assert topics == MOCK_TOPICS
        assert len(topics) == 5
