"""Tests for meeting templates API endpoints.

Tests:
- GET /api/v1/templates - List active templates
- GET /api/v1/templates/{slug} - Get template by slug
- Pydantic model validation
"""

from datetime import UTC, datetime

import pytest

from backend.api.models import (
    MeetingTemplate,
    MeetingTemplateCreate,
    MeetingTemplateListResponse,
    MeetingTemplateUpdate,
)


class TestMeetingTemplateModels:
    """Test MeetingTemplate Pydantic models."""

    def test_meeting_template_creation(self):
        """Test MeetingTemplate model creation."""
        now = datetime.now(UTC)
        template = MeetingTemplate(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Product Launch",
            slug="launch",
            description="Plan and execute a product launch",
            category="strategy",
            problem_statement_template="Should we launch [product] in [market]?",
            context_hints=["product_name", "target_market"],
            suggested_persona_traits=["analytical"],
            is_builtin=True,
            version=1,
            created_at=now,
            updated_at=now,
        )
        assert template.name == "Product Launch"
        assert template.slug == "launch"
        assert template.category == "strategy"
        assert template.is_builtin is True

    def test_meeting_template_defaults(self):
        """Test MeetingTemplate default values."""
        now = datetime.now(UTC)
        template = MeetingTemplate(
            id="test-id",
            name="Test",
            slug="test",
            description="A test template",
            category="strategy",
            problem_statement_template="Test statement",
            created_at=now,
            updated_at=now,
        )
        assert template.context_hints == []
        assert template.suggested_persona_traits == []
        assert template.is_builtin is False
        assert template.version == 1

    def test_meeting_template_list_response(self):
        """Test MeetingTemplateListResponse model."""
        now = datetime.now(UTC)
        template = MeetingTemplate(
            id="test-id",
            name="Test",
            slug="test",
            description="A test template",
            category="strategy",
            problem_statement_template="Test",
            created_at=now,
            updated_at=now,
        )
        response = MeetingTemplateListResponse(
            templates=[template],
            total=1,
            categories=["strategy", "pricing"],
        )
        assert len(response.templates) == 1
        assert response.total == 1
        assert "strategy" in response.categories


class TestMeetingTemplateCreateModel:
    """Test MeetingTemplateCreate validation."""

    def test_valid_create_request(self):
        """Test valid template creation request."""
        create = MeetingTemplateCreate(
            name="New Template",
            slug="new-template",
            description="A new template for testing purposes",
            category="strategy",
            problem_statement_template="Should we proceed with [action]?",
            context_hints=["action", "timeline"],
            suggested_persona_traits=["analytical"],
        )
        assert create.name == "New Template"
        assert create.slug == "new-template"

    def test_slug_validation_lowercase(self):
        """Test slug must be lowercase with hyphens."""
        with pytest.raises(ValueError):
            MeetingTemplateCreate(
                name="Test",
                slug="Invalid_Slug",  # Contains uppercase and underscore
                description="A test template for validation",
                category="strategy",
                problem_statement_template="Should we proceed with [action]?",
            )

    def test_slug_validation_valid_pattern(self):
        """Test valid slug patterns."""
        create = MeetingTemplateCreate(
            name="Test",
            slug="valid-slug-123",
            description="A test template for validation",
            category="strategy",
            problem_statement_template="Should we proceed with [action]?",
        )
        assert create.slug == "valid-slug-123"

    def test_category_validation(self):
        """Test category must be from allowed values."""
        with pytest.raises(ValueError):
            MeetingTemplateCreate(
                name="Test",
                slug="test",
                description="A test template for validation",
                category="invalid-category",
                problem_statement_template="Should we proceed with [action]?",
            )

    def test_valid_categories(self):
        """Test all valid categories."""
        valid_categories = ["strategy", "pricing", "product", "growth", "operations", "team"]
        for category in valid_categories:
            create = MeetingTemplateCreate(
                name="Test",
                slug="test",
                description="A test template for validation",
                category=category,
                problem_statement_template="Should we proceed with [action]?",
            )
            assert create.category == category

    def test_context_hints_limit(self):
        """Test context_hints limited to 20 items."""
        # Should fail if more than 20 hints
        from pydantic import ValidationError

        too_many_hints = [f"hint_{i}" for i in range(21)]
        with pytest.raises(ValidationError, match="too_long"):
            MeetingTemplateCreate(
                name="Test",
                slug="test",
                description="A test template for validation",
                category="strategy",
                problem_statement_template="Should we proceed with [action]?",
                context_hints=too_many_hints,
            )

    def test_persona_traits_limit(self):
        """Test suggested_persona_traits limited to 10 items."""
        from pydantic import ValidationError

        too_many_traits = [f"trait_{i}" for i in range(11)]
        with pytest.raises(ValidationError, match="too_long"):
            MeetingTemplateCreate(
                name="Test",
                slug="test",
                description="A test template for validation",
                category="strategy",
                problem_statement_template="Should we proceed with [action]?",
                suggested_persona_traits=too_many_traits,
            )


class TestMeetingTemplateUpdateModel:
    """Test MeetingTemplateUpdate validation."""

    def test_partial_update(self):
        """Test update with only some fields."""
        update = MeetingTemplateUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.category is None

    def test_is_active_update(self):
        """Test updating is_active flag."""
        update = MeetingTemplateUpdate(is_active=False)
        assert update.is_active is False

    def test_all_fields_update(self):
        """Test update with all fields."""
        update = MeetingTemplateUpdate(
            name="Updated",
            description="Updated description here",
            category="pricing",
            problem_statement_template="Updated statement for template testing",  # 20+ chars
            context_hints=["new_hint"],
            suggested_persona_traits=["new_trait"],
            is_active=True,
        )
        assert update.name == "Updated"
        assert update.category == "pricing"
        assert update.is_active is True
