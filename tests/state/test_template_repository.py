"""Tests for TemplateRepository.

Validates:
- list_active() returns active templates only
- get_by_slug() returns correct template
- create() creates new templates
- update() updates templates with version increment
- delete() only deletes non-builtin templates
- deactivate()/activate() soft delete behavior
"""

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest


class TestTemplateRepository:
    """Test template repository operations."""

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

    @pytest.fixture
    def sample_template(self):
        """Sample template data."""
        from datetime import datetime

        return {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Product Launch",
            "slug": "launch",
            "description": "Plan and execute a product launch",
            "category": "strategy",
            "problem_statement_template": "Should we launch [product] in [market]?",
            "context_hints": ["product_name", "target_market"],
            "suggested_persona_traits": ["analytical", "risk_averse"],
            "is_builtin": True,
            "is_active": True,
            "version": 1,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def test_list_active_returns_active_templates(self, sample_template):
        """Verify list_active returns only active templates."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_query", return_value=[sample_template]):
            templates = repo.list_active()

        assert len(templates) == 1
        assert templates[0]["name"] == "Product Launch"

    def test_list_active_with_category_filter(self, mock_connection, mock_cursor, sample_template):
        """Verify list_active filters by category."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_query", return_value=[sample_template]) as mock_query:
            _ = repo.list_active(category="strategy")

            # Verify category was passed to query
            call_args = mock_query.call_args
            assert "category = %s" in call_args[0][0]
            assert call_args[0][1] == ("strategy",)

    def test_get_by_slug_returns_correct_template(self, sample_template):
        """Verify get_by_slug returns matching template."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_one", return_value=sample_template) as mock_query:
            template = repo.get_by_slug("launch")

        assert template["slug"] == "launch"
        mock_query.assert_called_once()

    def test_get_by_slug_returns_none_for_missing(self):
        """Verify get_by_slug returns None for non-existent slug."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_one", return_value=None):
            template = repo.get_by_slug("nonexistent")

        assert template is None

    def test_create_template(self, sample_template):
        """Verify create() inserts new template."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_returning", return_value=sample_template) as mock_query:
            template = repo.create(
                name="Product Launch",
                slug="launch",
                description="Plan and execute a product launch",
                category="strategy",
                problem_statement_template="Should we launch [product] in [market]?",
                context_hints=["product_name"],
                suggested_persona_traits=["analytical"],
            )

        assert template["name"] == "Product Launch"
        mock_query.assert_called_once()

    def test_update_increments_version(self, sample_template):
        """Verify update() increments template version."""
        from bo1.state.repositories.template_repository import TemplateRepository

        updated_template = {**sample_template, "version": 2}

        repo = TemplateRepository()
        with patch.object(repo, "_execute_one", return_value=updated_template) as mock_query:
            template = repo.update(
                template_id="550e8400-e29b-41d4-a716-446655440000",
                name="Updated Launch",
            )

        assert template["version"] == 2
        # Verify version increment is in SQL
        call_args = mock_query.call_args
        assert "version = version + 1" in call_args[0][0]

    def test_delete_only_non_builtin(self, mock_connection, mock_cursor):
        """Verify delete() only deletes non-builtin templates."""
        from bo1.state.repositories.template_repository import TemplateRepository

        mock_cursor.rowcount = 1

        repo = TemplateRepository()
        with patch.object(repo, "_execute_count", return_value=1) as mock_query:
            result = repo.delete("550e8400-e29b-41d4-a716-446655440000")

        assert result is True
        # Verify is_builtin check is in SQL
        call_args = mock_query.call_args
        assert "is_builtin = false" in call_args[0][0]

    def test_delete_fails_for_builtin(self, mock_connection, mock_cursor):
        """Verify delete() returns False for builtin templates."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_count", return_value=0):
            result = repo.delete("builtin-template-id")

        assert result is False

    def test_deactivate_soft_deletes(self, sample_template):
        """Verify deactivate() sets is_active to False."""
        from bo1.state.repositories.template_repository import TemplateRepository

        deactivated = {**sample_template, "is_active": False}

        repo = TemplateRepository()
        with patch.object(repo, "update", return_value=deactivated) as mock_update:
            result = repo.deactivate("550e8400-e29b-41d4-a716-446655440000")

        assert result["is_active"] is False
        mock_update.assert_called_once_with(
            "550e8400-e29b-41d4-a716-446655440000",
            is_active=False,
        )

    def test_activate_reactivates(self, sample_template):
        """Verify activate() sets is_active to True."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "update", return_value=sample_template) as mock_update:
            result = repo.activate("550e8400-e29b-41d4-a716-446655440000")

        assert result["is_active"] is True
        mock_update.assert_called_once_with(
            "550e8400-e29b-41d4-a716-446655440000",
            is_active=True,
        )

    def test_slug_exists_check(self):
        """Verify slug_exists() returns True for existing slug."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_one", return_value={"id": "exists"}):
            assert repo.slug_exists("launch") is True

        with patch.object(repo, "_execute_one", return_value=None):
            assert repo.slug_exists("nonexistent") is False

    def test_slug_exists_with_exclude(self):
        """Verify slug_exists() excludes given template ID."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(repo, "_execute_one", return_value=None) as mock_query:
            repo.slug_exists("launch", exclude_id="550e8400-e29b-41d4-a716-446655440000")

        call_args = mock_query.call_args
        assert "id != %s" in call_args[0][0]

    def test_get_categories(self):
        """Verify get_categories returns distinct categories."""
        from bo1.state.repositories.template_repository import TemplateRepository

        repo = TemplateRepository()
        with patch.object(
            repo, "_execute_query", return_value=[{"category": "strategy"}, {"category": "pricing"}]
        ):
            categories = repo.get_categories()

        assert categories == ["strategy", "pricing"]
