"""Tests for data_profile tool module."""

from unittest.mock import MagicMock, patch

import pytest

from bo1.tools.data_profile import (
    DATA_PROFILE_TOOL,
    handle_data_profile_tool,
)


class TestDataProfileToolDefinition:
    """Tests for DATA_PROFILE_TOOL definition."""

    def test_tool_name(self):
        assert DATA_PROFILE_TOOL["name"] == "data_profile_dataset"

    def test_tool_has_description(self):
        assert "description" in DATA_PROFILE_TOOL
        assert len(DATA_PROFILE_TOOL["description"]) > 0

    def test_tool_input_schema(self):
        schema = DATA_PROFILE_TOOL["input_schema"]
        assert schema["type"] == "object"
        assert "dataset_id" in schema["properties"]
        assert "dataset_id" in schema["required"]


class TestHandleDataProfileTool:
    """Tests for handle_data_profile_tool function."""

    @pytest.mark.asyncio
    async def test_dataset_not_found(self):
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        result = await handle_data_profile_tool("missing-id", "user-1", repository=mock_repo)

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_cached_profile_returned(self):
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {
            "id": "test-id",
            "name": "Test Dataset",
            "row_count": 100,
            "column_count": 2,
            "summary": "Existing summary",
        }
        mock_repo.get_profiles.return_value = [
            {
                "column_name": "id",
                "data_type": "integer",
                "null_count": 0,
                "unique_count": 100,
            }
        ]

        result = await handle_data_profile_tool("test-id", "user-1", repository=mock_repo)

        assert result["success"] is True
        assert result["cached"] is True
        assert result["summary"] == "Existing summary"
        assert len(result["columns"]) == 1

    @pytest.mark.asyncio
    @patch("bo1.tools.data_profile.profile_dataset")
    @patch("bo1.tools.data_profile.save_profile")
    @patch("bo1.tools.data_profile.generate_dataset_summary")
    async def test_new_profile_generated(self, mock_generate, mock_save, mock_profile):
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {
            "id": "test-id",
            "name": "Test Dataset",
            "row_count": None,
            "column_count": None,
            "summary": None,
        }
        mock_repo.get_profiles.return_value = []

        # Mock profile result
        mock_col = MagicMock()
        mock_col.name = "col1"
        mock_col.inferred_type.value = "text"
        mock_col.stats.null_count = 0
        mock_col.stats.unique_count = 10
        mock_col.stats.min_value = None
        mock_col.stats.max_value = None
        mock_col.stats.mean_value = None

        mock_profile_result = MagicMock()
        mock_profile_result.row_count = 100
        mock_profile_result.column_count = 1
        mock_profile_result.columns = [mock_col]
        mock_profile_result.to_dict.return_value = {}
        mock_profile.return_value = mock_profile_result

        mock_generate.return_value = "New summary"

        result = await handle_data_profile_tool("test-id", "user-1", repository=mock_repo)

        assert result["success"] is True
        assert result["cached"] is False
        assert result["summary"] == "New summary"
        mock_profile.assert_called_once()
        mock_save.assert_called_once()
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("bo1.tools.data_profile.profile_dataset")
    async def test_profile_error_handled(self, mock_profile):
        from backend.services.profiler import ProfileError

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {
            "id": "test-id",
            "name": "Test Dataset",
            "summary": None,
        }
        mock_repo.get_profiles.return_value = []

        mock_profile.side_effect = ProfileError("Failed to load")

        result = await handle_data_profile_tool("test-id", "user-1", repository=mock_repo)

        assert result["success"] is False
        assert "Failed to load" in result["error"]
