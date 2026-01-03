"""Schema validation tests: ensure Pydantic models match PostgreSQL schema.

These tests introspect the live database schema and compare against
Pydantic model definitions to catch model/migration drift early.

Run with: pytest tests/test_schema_validation.py -v
Or: pytest -m db_schema
"""

import pytest

from bo1.models.persona import PersonaProfile
from bo1.models.session import Session
from tests.utils.schema_introspector import (
    ValidationResult,
    get_table_columns,
    validate_model_against_schema,
)


def format_validation_errors(result: ValidationResult, model_name: str, table_name: str) -> str:
    """Format validation result into readable error message."""
    errors = [f"\n{model_name} vs {table_name} schema mismatch:"]

    if result.missing_in_model:
        errors.append(f"  DB columns missing in model: {result.missing_in_model}")
    if result.missing_in_db:
        errors.append(f"  Model fields missing in DB: {result.missing_in_db}")
    if result.type_mismatches:
        errors.append("  Type mismatches:")
        for m in result.type_mismatches:
            errors.append(f"    - {m}")
    if result.nullability_mismatches:
        errors.append("  Nullability mismatches:")
        for m in result.nullability_mismatches:
            errors.append(f"    - {m}")

    return "\n".join(errors)


@pytest.mark.db_schema
class TestSessionModelSchema:
    """Validate Session Pydantic model against sessions table."""

    # DB columns that are intentionally not in Pydantic model
    EXCLUDED_DB_COLUMNS = {
        # These columns exist in DB but are deprecated or internal-only
        "total_tokens",
        "max_rounds",
        "completed_at",
        "killed_at",
        "killed_by",
        "kill_reason",
        # Partition key columns
        "partition_key",
        # Context tracking columns
        "session_context",
        "skip_clarification",
        "context_ids",
        # Promo tracking
        "promo_code_id",
        "used_promo_credit",
        # Analytics columns
        "contribution_count",
    }

    # Pydantic fields that are computed or don't map to DB columns
    # These fields were added to the model before the migration was created
    COMPUTED_FIELDS: set[str] = {"contribution_count"}

    def test_session_model_matches_schema(self):
        """Session model fields should match sessions table columns."""
        result = validate_model_against_schema(
            model=Session,
            table_name="sessions",
            excluded_db_columns=self.EXCLUDED_DB_COLUMNS,
            computed_model_fields=self.COMPUTED_FIELDS,
        )

        assert result.is_valid, format_validation_errors(result, "Session", "sessions")

    def test_sessions_table_exists(self):
        """Verify sessions table is accessible."""
        columns = get_table_columns("sessions")
        assert len(columns) > 0, "sessions table should have columns"

    def test_session_critical_columns_exist(self):
        """Verify critical session columns exist in DB."""
        columns = get_table_columns("sessions")
        column_names = {col.name for col in columns}

        critical_columns = {
            "id",
            "user_id",
            "problem_statement",
            "status",
            "created_at",
            "updated_at",
        }
        missing = critical_columns - column_names

        assert not missing, f"Critical columns missing from sessions table: {missing}"


@pytest.mark.db_schema
class TestPersonaModelSchema:
    """Validate PersonaProfile Pydantic model against personas table.

    NOTE: PersonaProfile is a rich model populated from personas.json file,
    while the DB personas table is a minimal reference table with just
    id, code, name, expertise, system_prompt, is_dynamic, created_at.

    Most PersonaProfile fields come from JSON, not DB. Tests here validate
    the DB table structure, not full model-to-table mapping.
    """

    # DB columns that are intentionally not in Pydantic model
    EXCLUDED_DB_COLUMNS = {
        # Timestamps managed by DB
        "created_at",
        # Columns from legacy schema
        "expertise",
        # Dynamic persona flag
        "is_dynamic",
    }

    # Pydantic fields that come from JSON, not DB
    # (PersonaProfile is hydrated from personas.json, DB just stores refs)
    COMPUTED_FIELDS = {
        "description",
        "is_active",
        "emoji",
        "archetype",
        "display_name",
        "domain_expertise",
        "is_visible",
        "category",
        "color_hex",
        "persona_type",
        "response_style",
        "traits",
        "default_weight",
        "temperature",
    }

    def test_persona_core_fields_match_schema(self):
        """PersonaProfile core fields should match personas table columns.

        Only validates fields that map directly to DB (id, code, name, system_prompt).
        Other fields come from personas.json file.
        """
        result = validate_model_against_schema(
            model=PersonaProfile,
            table_name="personas",
            excluded_db_columns=self.EXCLUDED_DB_COLUMNS,
            computed_model_fields=self.COMPUTED_FIELDS,
        )

        # Check missing fields - type mismatch on id is expected (DB int, model str)
        # The ID in PersonaProfile is a UUID string, but DB uses int autoincrement
        # This is a known design difference (model ID is populated from JSON)
        if result.type_mismatches:
            # Filter out known id type mismatch
            unexpected_mismatches = [m for m in result.type_mismatches if "id:" not in m]
            assert not unexpected_mismatches, f"Unexpected type mismatches: {unexpected_mismatches}"

        assert not result.missing_in_model, f"DB columns not mapped: {result.missing_in_model}"
        assert not result.missing_in_db, (
            f"Model fields missing from DB (should be in COMPUTED_FIELDS): {result.missing_in_db}"
        )

    def test_personas_table_exists(self):
        """Verify personas table is accessible."""
        columns = get_table_columns("personas")
        assert len(columns) > 0, "personas table should have columns"

    def test_persona_critical_columns_exist(self):
        """Verify critical persona columns exist in DB."""
        columns = get_table_columns("personas")
        column_names = {col.name for col in columns}

        critical_columns = {"id", "code", "name", "system_prompt"}
        missing = critical_columns - column_names

        assert not missing, f"Critical columns missing from personas table: {missing}"


@pytest.mark.db_schema
class TestContributionsSchema:
    """Validate contributions table schema (no dedicated Pydantic model yet)."""

    def test_contributions_table_exists(self):
        """Verify contributions table is accessible."""
        columns = get_table_columns("contributions")
        assert len(columns) > 0, "contributions table should have columns"

    def test_contributions_critical_columns_exist(self):
        """Verify critical contribution columns exist in DB."""
        columns = get_table_columns("contributions")
        column_names = {col.name for col in columns}

        critical_columns = {
            "id",
            "session_id",
            "persona_code",
            "content",
            "round_number",
            "phase",
            "created_at",
        }
        missing = critical_columns - column_names

        assert not missing, f"Critical columns missing from contributions table: {missing}"


@pytest.mark.db_schema
class TestSchemaIntrospection:
    """Test schema introspection utility functions."""

    def test_get_table_columns_returns_data(self):
        """get_table_columns should return column info for existing table."""
        columns = get_table_columns("users")
        assert len(columns) > 0

        # Check structure
        col = columns[0]
        assert hasattr(col, "name")
        assert hasattr(col, "data_type")
        assert hasattr(col, "is_nullable")

    def test_get_table_columns_nonexistent_table(self):
        """get_table_columns should return empty list for nonexistent table."""
        columns = get_table_columns("this_table_does_not_exist_xyz")
        assert columns == []

    def test_column_types_are_recognized(self):
        """Common PostgreSQL types should be in our mapping."""
        from tests.utils.schema_introspector import PG_TO_PYTHON_TYPE

        expected_types = ["text", "integer", "boolean", "jsonb", "timestamp with time zone"]
        for pg_type in expected_types:
            assert pg_type in PG_TO_PYTHON_TYPE, f"Missing mapping for {pg_type}"
