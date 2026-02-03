"""Tests for bo1/models/util.py."""

from enum import Enum
from typing import ClassVar
from uuid import UUID

import pytest
from pydantic import Field, ValidationError

from bo1.models.util import FromDbRowMixin, coerce_enum, normalize_uuid


class SampleStatus(str, Enum):
    """Sample enum for testing."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class SampleModel(FromDbRowMixin):
    """Sample model for testing FromDbRowMixin."""

    id: str
    name: str
    status: SampleStatus = SampleStatus.ACTIVE
    parent_id: str | None = None
    items: list[str] = Field(default_factory=list)
    count: int = 0


class CustomUuidModel(FromDbRowMixin):
    """Model with custom UUID fields override."""

    id: str  # Not a UUID in this model
    external_ref: str  # This is a UUID

    _uuid_fields: ClassVar[set[str]] = {"external_ref"}


class TestNormalizeUuid:
    """Tests for normalize_uuid helper."""

    def test_normalize_uuid_from_uuid_object(self) -> None:
        """UUID objects with .hex attribute are converted to strings."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")
        result = normalize_uuid(uuid_obj)
        assert result == "12345678-1234-5678-1234-567812345678"
        assert isinstance(result, str)

    def test_normalize_uuid_from_string(self) -> None:
        """String UUIDs pass through unchanged."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = normalize_uuid(uuid_str)
        assert result == uuid_str
        assert isinstance(result, str)

    def test_normalize_uuid_none(self) -> None:
        """None input returns None."""
        result = normalize_uuid(None)
        assert result is None

    def test_normalize_uuid_empty_string(self) -> None:
        """Empty string passes through (falsy but valid)."""
        result = normalize_uuid("")
        assert result == ""


class TestCoerceEnum:
    """Tests for coerce_enum helper."""

    def test_coerce_enum_from_string(self) -> None:
        """String values are converted to enum."""
        result = coerce_enum("active", SampleStatus)
        assert result == SampleStatus.ACTIVE
        assert isinstance(result, SampleStatus)

    def test_coerce_enum_already_enum(self) -> None:
        """Enum values pass through unchanged."""
        result = coerce_enum(SampleStatus.INACTIVE, SampleStatus)
        assert result == SampleStatus.INACTIVE
        assert isinstance(result, SampleStatus)

    def test_coerce_enum_with_default(self) -> None:
        """None with default returns default."""
        result = coerce_enum(None, SampleStatus, SampleStatus.ACTIVE)
        assert result == SampleStatus.ACTIVE

    def test_coerce_enum_none_without_default(self) -> None:
        """None without default raises ValueError."""
        with pytest.raises(ValueError, match="Cannot coerce None"):
            coerce_enum(None, SampleStatus)

    def test_coerce_enum_invalid_value(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            coerce_enum("invalid_value", SampleStatus)


class TestFromDbRowMixin:
    """Tests for FromDbRowMixin."""

    def test_mixin_handles_uuid_normalization(self) -> None:
        """UUID objects with .hex attribute are normalized to strings."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")
        row = {
            "id": uuid_obj,
            "name": "Test",
            "status": "active",
        }
        model = SampleModel.from_db_row(row)
        assert model.id == "12345678-1234-5678-1234-567812345678"
        assert isinstance(model.id, str)

    def test_mixin_handles_enum_coercion(self) -> None:
        """String values are coerced to enum types."""
        row = {
            "id": "abc123",
            "name": "Test",
            "status": "inactive",
        }
        model = SampleModel.from_db_row(row)
        assert model.status == SampleStatus.INACTIVE
        assert isinstance(model.status, SampleStatus)

    def test_mixin_handles_optional_uuid(self) -> None:
        """Optional UUID fields handle None correctly."""
        row = {
            "id": "abc123",
            "name": "Test",
            "status": "active",
            "parent_id": None,
        }
        model = SampleModel.from_db_row(row)
        assert model.parent_id is None

    def test_mixin_normalizes_optional_uuid(self) -> None:
        """Optional UUID fields normalize UUID objects."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")
        row = {
            "id": "abc123",
            "name": "Test",
            "status": "active",
            "parent_id": uuid_obj,
        }
        model = SampleModel.from_db_row(row)
        assert model.parent_id == "12345678-1234-5678-1234-567812345678"

    def test_mixin_handles_list_default(self) -> None:
        """List fields with None value get empty list."""
        row = {
            "id": "abc123",
            "name": "Test",
            "status": "active",
            "items": None,
        }
        model = SampleModel.from_db_row(row)
        assert model.items == []

    def test_mixin_preserves_list_values(self) -> None:
        """List fields with actual values are preserved."""
        row = {
            "id": "abc123",
            "name": "Test",
            "status": "active",
            "items": ["a", "b", "c"],
        }
        model = SampleModel.from_db_row(row)
        assert model.items == ["a", "b", "c"]

    def test_mixin_uses_field_defaults(self) -> None:
        """Missing keys use field defaults."""
        row = {
            "id": "abc123",
            "name": "Test",
            # status missing - should use default ACTIVE
            # count missing - should use default 0
        }
        model = SampleModel.from_db_row(row)
        assert model.status == SampleStatus.ACTIVE
        assert model.count == 0

    def test_mixin_raises_on_missing_required(self) -> None:
        """Missing required fields raise validation error."""
        row = {
            "id": "abc123",
            # name is required but missing
        }
        with pytest.raises(ValidationError):
            SampleModel.from_db_row(row)

    def test_mixin_custom_uuid_fields(self) -> None:
        """Custom _uuid_fields override controls UUID normalization."""
        uuid_obj = UUID("12345678-1234-5678-1234-567812345678")
        row = {
            "id": "not-a-uuid",  # Should NOT be normalized
            "external_ref": uuid_obj,  # Should be normalized
        }
        model = CustomUuidModel.from_db_row(row)
        assert model.id == "not-a-uuid"  # Passed through unchanged
        assert model.external_ref == "12345678-1234-5678-1234-567812345678"
