"""Tests for scripts/audit_model_schema.py.

Tests type mapping logic and comparison functions without requiring database.
"""

# Import from script
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from audit_model_schema import (
    PYTHON_TO_PG_TYPES,
    AuditResult,
    ColumnInfo,
    FieldInfo,
    TypeMismatch,
    _format_type_annotation,
    _is_optional_type,
    check_type_compatibility,
    compare_model_to_schema,
    generate_json_report,
    generate_markdown_report,
    get_model_fields,
)


class TestTypeMapping:
    """Tests for Python → PostgreSQL type mapping."""

    def test_string_types_compatible(self):
        """str should be compatible with text, varchar, uuid."""
        assert "text" in PYTHON_TO_PG_TYPES["str"]
        assert "character varying" in PYTHON_TO_PG_TYPES["str"]
        assert "uuid" in PYTHON_TO_PG_TYPES["str"]

    def test_optional_string_types_compatible(self):
        """str | None should have same mappings as str."""
        assert PYTHON_TO_PG_TYPES["str | None"] == PYTHON_TO_PG_TYPES["str"]

    def test_int_types_compatible(self):
        """int should be compatible with integer, bigint, serial."""
        assert "integer" in PYTHON_TO_PG_TYPES["int"]
        assert "bigint" in PYTHON_TO_PG_TYPES["int"]
        assert "serial" in PYTHON_TO_PG_TYPES["int"]

    def test_float_types_compatible(self):
        """float should be compatible with double precision, numeric."""
        assert "double precision" in PYTHON_TO_PG_TYPES["float"]
        assert "numeric" in PYTHON_TO_PG_TYPES["float"]

    def test_bool_types_compatible(self):
        """bool should be compatible with boolean."""
        assert "boolean" in PYTHON_TO_PG_TYPES["bool"]

    def test_datetime_types_compatible(self):
        """datetime should be compatible with timestamp types."""
        assert "timestamp with time zone" in PYTHON_TO_PG_TYPES["datetime"]
        assert "timestamp without time zone" in PYTHON_TO_PG_TYPES["datetime"]

    def test_dict_types_compatible(self):
        """dict should be compatible with jsonb, json."""
        assert "jsonb" in PYTHON_TO_PG_TYPES["dict"]
        assert "json" in PYTHON_TO_PG_TYPES["dict"]
        assert "jsonb" in PYTHON_TO_PG_TYPES["dict[str, Any]"]

    def test_list_types_compatible(self):
        """list should be compatible with jsonb, json, ARRAY."""
        assert "jsonb" in PYTHON_TO_PG_TYPES["list"]
        assert "ARRAY" in PYTHON_TO_PG_TYPES["list"]
        assert "vector" in PYTHON_TO_PG_TYPES["list[float] | None"]

    def test_enum_types_compatible(self):
        """Enums should be compatible with text/varchar."""
        assert "text" in PYTHON_TO_PG_TYPES["SessionStatus"]
        assert "text" in PYTHON_TO_PG_TYPES["ContributionType"]


class TestCheckTypeCompatibility:
    """Tests for type compatibility checking."""

    def test_compatible_str_text(self):
        """str field should be compatible with text column."""
        field = FieldInfo(name="name", type_annotation="str", is_optional=False)
        column = ColumnInfo(name="name", data_type="text", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is None

    def test_compatible_str_varchar(self):
        """str field should be compatible with character varying."""
        field = FieldInfo(name="name", type_annotation="str", is_optional=False)
        column = ColumnInfo(name="name", data_type="character varying", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is None

    def test_compatible_int_integer(self):
        """int field should be compatible with integer column."""
        field = FieldInfo(name="count", type_annotation="int", is_optional=False)
        column = ColumnInfo(name="count", data_type="integer", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is None

    def test_compatible_float_double_precision(self):
        """float field should be compatible with double precision."""
        field = FieldInfo(name="cost", type_annotation="float", is_optional=False)
        column = ColumnInfo(name="cost", data_type="double precision", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is None

    def test_compatible_datetime_timestamp(self):
        """datetime field should be compatible with timestamp."""
        field = FieldInfo(name="created_at", type_annotation="datetime", is_optional=False)
        column = ColumnInfo(
            name="created_at", data_type="timestamp with time zone", is_nullable=False
        )

        result = check_type_compatibility(field, column)
        assert result is None

    def test_compatible_dict_jsonb(self):
        """dict field should be compatible with jsonb."""
        field = FieldInfo(name="metadata", type_annotation="dict[str, Any]", is_optional=True)
        column = ColumnInfo(name="metadata", data_type="jsonb", is_nullable=True)

        result = check_type_compatibility(field, column)
        assert result is None

    def test_incompatible_str_integer(self):
        """str field should NOT be compatible with integer column."""
        field = FieldInfo(name="name", type_annotation="str", is_optional=False)
        column = ColumnInfo(name="name", data_type="integer", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is not None
        assert isinstance(result, TypeMismatch)
        assert "mismatch" in result.message.lower()

    def test_incompatible_int_text(self):
        """int field should NOT be compatible with text column."""
        field = FieldInfo(name="count", type_annotation="int", is_optional=False)
        column = ColumnInfo(name="count", data_type="text", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is not None

    def test_unknown_type_returns_warning(self):
        """Unknown Python types should return a warning mismatch."""
        field = FieldInfo(name="custom", type_annotation="CustomType", is_optional=False)
        column = ColumnInfo(name="custom", data_type="text", is_nullable=False)

        result = check_type_compatibility(field, column)
        assert result is not None
        assert "unknown" in result.message.lower()

    def test_array_list_compatible(self):
        """list[float] should be compatible with ARRAY."""
        field = FieldInfo(name="embedding", type_annotation="list[float] | None", is_optional=True)
        column = ColumnInfo(name="embedding", data_type="ARRAY", is_nullable=True)

        result = check_type_compatibility(field, column)
        assert result is None


class TestAuditResult:
    """Tests for AuditResult dataclass."""

    def test_has_issues_when_missing_in_db(self):
        """has_issues should be True when fields missing in DB."""
        result = AuditResult(
            model_name="Test",
            table_name="test",
            missing_in_db=["field1"],
        )
        assert result.has_issues is True

    def test_has_issues_when_missing_in_model(self):
        """has_issues should be True when columns missing in model."""
        result = AuditResult(
            model_name="Test",
            table_name="test",
            missing_in_model=["col1"],
        )
        assert result.has_issues is True

    def test_has_issues_when_type_mismatch(self):
        """has_issues should be True when type mismatches exist."""
        result = AuditResult(
            model_name="Test",
            table_name="test",
            type_mismatches=[
                TypeMismatch(
                    field_name="field1",
                    python_type="str",
                    db_type="integer",
                    message="Type mismatch",
                )
            ],
        )
        assert result.has_issues is True

    def test_no_issues_when_empty(self):
        """has_issues should be False when no issues."""
        result = AuditResult(model_name="Test", table_name="test")
        assert result.has_issues is False


class TestFormatTypeAnnotation:
    """Tests for type annotation formatting."""

    def test_simple_str(self):
        """Format simple str type."""
        assert _format_type_annotation(str) == "str"

    def test_simple_int(self):
        """Format simple int type."""
        assert _format_type_annotation(int) == "int"

    def test_optional_str(self):
        """Format Optional[str] / str | None."""
        from typing import Optional

        result = _format_type_annotation(Optional[str])  # noqa: UP045
        assert "str" in result
        assert "None" in result

    def test_list_of_str(self):
        """Format list[str]."""
        result = _format_type_annotation(list[str])
        assert "list" in result
        assert "str" in result

    def test_dict_str_any(self):
        """Format dict[str, Any]."""
        result = _format_type_annotation(dict[str, Any])
        assert "dict" in result
        assert "str" in result


class TestIsOptionalType:
    """Tests for optional type detection."""

    def test_optional_str_is_optional(self):
        """Optional[str] should be detected as optional."""
        from typing import Optional

        assert _is_optional_type(Optional[str]) is True  # noqa: UP045

    def test_str_is_not_optional(self):
        """str should not be detected as optional."""
        assert _is_optional_type(str) is False

    def test_union_with_none_is_optional(self):
        """Union[str, None] should be detected as optional."""
        from typing import Union

        assert _is_optional_type(Union[str, None]) is True  # noqa: UP007


class TestCompareModelToSchema:
    """Tests for model-to-schema comparison with mocks."""

    @patch("audit_model_schema.get_table_columns")
    @patch("audit_model_schema.get_model_fields")
    def test_all_fields_match(self, mock_get_fields, mock_get_columns):
        """No issues when all fields match columns."""
        mock_get_columns.return_value = [
            ColumnInfo(name="id", data_type="text", is_nullable=False),
            ColumnInfo(name="name", data_type="text", is_nullable=False),
        ]
        mock_get_fields.return_value = [
            FieldInfo(name="id", type_annotation="str", is_optional=False),
            FieldInfo(name="name", type_annotation="str", is_optional=False),
        ]

        result = compare_model_to_schema(MagicMock, "test_table")

        assert result.has_issues is False
        assert result.missing_in_db == []
        assert result.missing_in_model == []
        assert result.type_mismatches == []

    @patch("audit_model_schema.get_table_columns")
    @patch("audit_model_schema.get_model_fields")
    def test_field_missing_in_db(self, mock_get_fields, mock_get_columns):
        """Detect fields in model but not in DB."""
        mock_get_columns.return_value = [
            ColumnInfo(name="id", data_type="text", is_nullable=False),
        ]
        mock_get_fields.return_value = [
            FieldInfo(name="id", type_annotation="str", is_optional=False),
            FieldInfo(name="new_field", type_annotation="str", is_optional=False),
        ]

        result = compare_model_to_schema(MagicMock, "test_table")

        assert result.has_issues is True
        assert "new_field" in result.missing_in_db

    @patch("audit_model_schema.get_table_columns")
    @patch("audit_model_schema.get_model_fields")
    def test_column_missing_in_model(self, mock_get_fields, mock_get_columns):
        """Detect columns in DB but not in model."""
        mock_get_columns.return_value = [
            ColumnInfo(name="id", data_type="text", is_nullable=False),
            ColumnInfo(name="legacy_col", data_type="text", is_nullable=True),
        ]
        mock_get_fields.return_value = [
            FieldInfo(name="id", type_annotation="str", is_optional=False),
        ]

        result = compare_model_to_schema(MagicMock, "test_table")

        assert result.has_issues is True
        assert "legacy_col" in result.missing_in_model

    @patch("audit_model_schema.get_table_columns")
    @patch("audit_model_schema.get_model_fields")
    def test_known_exception_skipped(self, mock_get_fields, mock_get_columns):
        """Known exceptions should not be flagged."""
        mock_get_columns.return_value = [
            ColumnInfo(name="id", data_type="text", is_nullable=False),
        ]
        mock_get_fields.return_value = [
            FieldInfo(name="id", type_annotation="str", is_optional=False),
            FieldInfo(name="computed_field", type_annotation="str", is_optional=False),
        ]

        result = compare_model_to_schema(
            MagicMock, "test_table", known_exceptions={"computed_field"}
        )

        assert result.has_issues is False
        assert "computed_field" not in result.missing_in_db


class TestReportGeneration:
    """Tests for report generation."""

    def test_markdown_report_no_issues(self):
        """Markdown report should show success for no issues."""
        results = [AuditResult(model_name="TestModel", table_name="test")]
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        report = generate_markdown_report(results, timestamp)

        assert "Model-Schema Audit Report" in report
        assert "TestModel" in report
        assert "No issues found" in report

    def test_markdown_report_with_issues(self):
        """Markdown report should list issues."""
        results = [
            AuditResult(
                model_name="TestModel",
                table_name="test",
                missing_in_db=["new_field"],
                missing_in_model=["old_col"],
            )
        ]
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        report = generate_markdown_report(results, timestamp)

        assert "new_field" in report
        assert "old_col" in report
        assert "NOT in Database" in report
        assert "NOT in Model" in report

    def test_json_report_structure(self):
        """JSON report should have expected structure."""
        import json

        results = [AuditResult(model_name="TestModel", table_name="test")]
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        report = generate_json_report(results, timestamp)
        data = json.loads(report)

        assert "timestamp" in data
        assert "summary" in data
        assert "results" in data
        assert data["summary"]["models_audited"] == 1
        assert data["summary"]["models_with_issues"] == 0


class TestGetModelFields:
    """Tests for Pydantic model field extraction."""

    def test_extract_session_fields(self):
        """Should extract fields from Session model."""
        from bo1.models.session import Session

        fields = get_model_fields(Session)

        field_names = {f.name for f in fields}
        assert "id" in field_names
        assert "user_id" in field_names
        assert "problem_statement" in field_names
        assert "status" in field_names
        assert "created_at" in field_names

    def test_extract_contribution_fields(self):
        """Should extract fields from ContributionMessage model."""
        from bo1.models.state import ContributionMessage

        fields = get_model_fields(ContributionMessage)

        field_names = {f.name for f in fields}
        assert "persona_code" in field_names
        assert "persona_name" in field_names
        assert "content" in field_names
        assert "round_number" in field_names

    def test_extract_recommendation_fields(self):
        """Should extract fields from Recommendation model."""
        from bo1.models.recommendations import Recommendation

        fields = get_model_fields(Recommendation)

        field_names = {f.name for f in fields}
        assert "persona_code" in field_names
        assert "recommendation" in field_names
        assert "confidence" in field_names
