"""Tests for admin runtime config endpoints."""

import pytest

from backend.api.admin.runtime_config import (
    RuntimeConfigItem,
    RuntimeConfigResponse,
    UpdateRuntimeConfigRequest,
)


@pytest.mark.unit
class TestRuntimeConfigItem:
    """Tests for RuntimeConfigItem model."""

    def test_structure(self) -> None:
        """Test response structure."""
        item = RuntimeConfigItem(
            key="prompt_injection_block_suspicious",
            override_value=None,
            default_value=True,
            effective_value=True,
            is_overridden=False,
        )

        assert item.key == "prompt_injection_block_suspicious"
        assert item.override_value is None
        assert item.default_value is True
        assert item.effective_value is True
        assert item.is_overridden is False

    def test_with_override(self) -> None:
        """Test item with active override."""
        item = RuntimeConfigItem(
            key="prompt_injection_block_suspicious",
            override_value=False,
            default_value=True,
            effective_value=False,
            is_overridden=True,
        )

        assert item.is_overridden is True
        assert item.effective_value is False


@pytest.mark.unit
class TestRuntimeConfigResponse:
    """Tests for RuntimeConfigResponse model."""

    def test_structure(self) -> None:
        """Test response structure."""
        response = RuntimeConfigResponse(
            items=[
                RuntimeConfigItem(
                    key="prompt_injection_block_suspicious",
                    override_value=None,
                    default_value=True,
                    effective_value=True,
                    is_overridden=False,
                ),
            ],
            count=1,
        )

        assert len(response.items) == 1
        assert response.count == 1


@pytest.mark.unit
class TestUpdateRuntimeConfigRequest:
    """Tests for UpdateRuntimeConfigRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request."""
        request = UpdateRuntimeConfigRequest(value=False)
        assert request.value is False

    def test_true_value(self) -> None:
        """Test request with True value."""
        request = UpdateRuntimeConfigRequest(value=True)
        assert request.value is True
