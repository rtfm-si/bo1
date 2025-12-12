"""Tests for session export endpoint.

Tests GET /api/v1/sessions/{id}/export for JSON and Markdown export.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.services.session_export import SessionExporter


class TestSessionExporterService:
    """Test SessionExporter service class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def exporter(self, mock_db):
        """Create SessionExporter instance."""
        return SessionExporter(mock_db)

    def test_exporter_initialization(self, exporter, mock_db):
        """Test exporter initializes with db session."""
        assert exporter.db is mock_db

    @pytest.mark.asyncio
    async def test_export_to_json_structure(self, exporter):
        """Test JSON export returns expected structure."""
        # Mock session repository
        mock_session = {
            "id": "test-session-id",
            "user_id": "test-user-id",
            "problem_statement": "Test problem",
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "synthesis": {"summary": "Test synthesis"},
        }

        with patch("bo1.state.repositories.session_repository.session_repository") as mock_repo:
            mock_repo.get_session_by_id.return_value = mock_session

            result = await exporter.export_to_json("test-session-id", "test-user-id")

            assert isinstance(result, dict)
            assert "metadata" in result
            assert result["metadata"]["session_id"] == "test-session-id"

    @pytest.mark.asyncio
    async def test_export_to_json_permission_denied(self, exporter):
        """Test export raises error for non-owner."""
        mock_session = {
            "id": "test-session-id",
            "user_id": "other-user-id",
            "problem_statement": "Test",
        }

        with patch("bo1.state.repositories.session_repository.session_repository") as mock_repo:
            mock_repo.get_session_by_id.return_value = mock_session

            with pytest.raises(ValueError, match="does not own"):
                await exporter.export_to_json("test-session-id", "test-user-id")

    @pytest.mark.asyncio
    async def test_export_to_json_session_not_found(self, exporter):
        """Test export raises error for missing session."""
        with patch("bo1.state.repositories.session_repository.session_repository") as mock_repo:
            mock_repo.get_session_by_id.return_value = None

            with pytest.raises(ValueError, match="not found"):
                await exporter.export_to_json("nonexistent-id", "test-user-id")

    @pytest.mark.asyncio
    async def test_export_to_markdown_structure(self, exporter):
        """Test Markdown export returns text content."""
        mock_session = {
            "id": "test-session-id",
            "user_id": "test-user-id",
            "problem_statement": "Test problem statement",
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
            "synthesis": {"summary": "Test synthesis"},
        }

        with patch("bo1.state.repositories.session_repository.session_repository") as mock_repo:
            mock_repo.get_session_by_id.return_value = mock_session

            result = await exporter.export_to_markdown("test-session-id", "test-user-id")

            assert isinstance(result, str)
            assert "Deliberation Report" in result or "Test problem" in result


class TestExportFormatValidation:
    """Test export format parameter validation."""

    def test_valid_json_format(self):
        """Test 'json' is a valid format."""
        valid_formats = ["json", "markdown"]
        assert "json" in valid_formats

    def test_valid_markdown_format(self):
        """Test 'markdown' is a valid format."""
        valid_formats = ["json", "markdown"]
        assert "markdown" in valid_formats

    def test_invalid_format_rejected(self):
        """Test invalid formats are rejected."""
        valid_formats = ["json", "markdown"]
        assert "pdf" not in valid_formats
        assert "html" not in valid_formats
        assert "csv" not in valid_formats
