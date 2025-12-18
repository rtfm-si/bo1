"""Schema introspection utility for validating Pydantic models against DB schema.

Provides functions to:
- Introspect PostgreSQL table columns via information_schema
- Map PostgreSQL types to Python types
- Compare Pydantic model fields with DB columns
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bo1.state.database import db_session


@dataclass
class ColumnInfo:
    """Database column metadata."""

    name: str
    data_type: str
    is_nullable: bool
    column_default: str | None = None


# PostgreSQL type -> Python type mapping
PG_TO_PYTHON_TYPE: dict[str, type | None] = {
    # String types
    "text": str,
    "character varying": str,
    "varchar": str,
    "character": str,
    "char": str,
    # Numeric types
    "integer": int,
    "bigint": int,
    "smallint": int,
    "numeric": float,
    "decimal": float,
    "real": float,
    "double precision": float,
    # Boolean
    "boolean": bool,
    # JSON types
    "json": dict,
    "jsonb": dict,
    # Date/time types
    "timestamp with time zone": datetime,
    "timestamp without time zone": datetime,
    "date": datetime,
    "time with time zone": datetime,
    "time without time zone": datetime,
    # Array types (simplified)
    "ARRAY": list,
    # Special types to skip
    "USER-DEFINED": None,  # pgvector, enums, etc.
}


def get_table_columns(table_name: str) -> list[ColumnInfo]:
    """Get column metadata for a table from information_schema.

    Args:
        table_name: Name of the PostgreSQL table

    Returns:
        List of ColumnInfo for each column in the table
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
            rows = cur.fetchall()

    return [
        ColumnInfo(
            name=row["column_name"],
            data_type=row["data_type"],
            is_nullable=row["is_nullable"] == "YES",
            column_default=row["column_default"],
        )
        for row in rows
    ]


def pg_type_to_python(pg_type: str) -> type | None:
    """Map PostgreSQL data type to Python type.

    Args:
        pg_type: PostgreSQL data type string

    Returns:
        Corresponding Python type, or None if type should be skipped
    """
    # Handle array types
    if pg_type == "ARRAY":
        return list

    return PG_TO_PYTHON_TYPE.get(pg_type)


def get_pydantic_field_info(model: type) -> dict[str, dict[str, Any]]:
    """Extract field information from a Pydantic model.

    Args:
        model: Pydantic model class

    Returns:
        Dict mapping field name to {type, is_optional, default}
    """
    fields_info = {}

    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation

        # Check if field is Optional (Union with None)
        is_optional = False
        base_type = annotation

        # Handle Optional types (Union[X, None])
        origin = getattr(annotation, "__origin__", None)
        if origin is type(None):
            is_optional = True
            base_type = type(None)
        elif hasattr(annotation, "__args__"):
            args = annotation.__args__
            if type(None) in args:
                is_optional = True
                # Get the non-None type
                base_type = next((a for a in args if a is not type(None)), annotation)

        fields_info[field_name] = {
            "type": base_type,
            "is_optional": is_optional,
            "has_default": field_info.default is not None or field_info.default_factory is not None,
        }

    return fields_info


@dataclass
class ValidationResult:
    """Result of schema validation comparison."""

    is_valid: bool
    missing_in_model: list[str]  # DB columns not in Pydantic model
    missing_in_db: list[str]  # Pydantic fields not in DB
    type_mismatches: list[str]  # Fields with incompatible types
    nullability_mismatches: list[str]  # Fields with nullability mismatch


def validate_model_against_schema(
    model: type,
    table_name: str,
    excluded_db_columns: set[str] | None = None,
    computed_model_fields: set[str] | None = None,
) -> ValidationResult:
    """Validate Pydantic model fields against PostgreSQL table schema.

    Args:
        model: Pydantic model class
        table_name: PostgreSQL table name
        excluded_db_columns: DB columns to ignore (e.g., RLS audit columns)
        computed_model_fields: Pydantic fields that don't map to DB columns

    Returns:
        ValidationResult with comparison details
    """
    excluded_db_columns = excluded_db_columns or set()
    computed_model_fields = computed_model_fields or set()

    # Get DB schema
    db_columns = get_table_columns(table_name)
    db_column_map = {col.name: col for col in db_columns}
    db_column_names = set(db_column_map.keys()) - excluded_db_columns

    # Get Pydantic fields
    model_fields = get_pydantic_field_info(model)
    model_field_names = set(model_fields.keys()) - computed_model_fields

    # Find missing columns/fields
    missing_in_model = list(db_column_names - model_field_names)
    missing_in_db = list(model_field_names - db_column_names)

    # Check type and nullability compatibility
    type_mismatches = []
    nullability_mismatches = []

    for field_name in model_field_names & db_column_names:
        db_col = db_column_map[field_name]
        model_field = model_fields[field_name]

        # Check type compatibility
        expected_python_type = pg_type_to_python(db_col.data_type)
        if expected_python_type is not None:
            actual_type = model_field["type"]
            # Allow str/Enum compatibility, dict/Any compatibility
            if not _types_compatible(expected_python_type, actual_type):
                type_mismatches.append(
                    f"{field_name}: DB={db_col.data_type} ({expected_python_type.__name__}), "
                    f"Model={actual_type}"
                )

        # Check nullability
        # DB nullable should align with Pydantic Optional
        if db_col.is_nullable and not model_field["is_optional"] and not model_field["has_default"]:
            # Only flag if DB is nullable but model requires value with no default
            nullability_mismatches.append(
                f"{field_name}: DB is nullable but Pydantic field has no default"
            )

    is_valid = not (missing_in_model or missing_in_db or type_mismatches or nullability_mismatches)

    return ValidationResult(
        is_valid=is_valid,
        missing_in_model=missing_in_model,
        missing_in_db=missing_in_db,
        type_mismatches=type_mismatches,
        nullability_mismatches=nullability_mismatches,
    )


def _types_compatible(db_type: type, model_type: Any) -> bool:
    """Check if database type is compatible with Pydantic model type.

    Args:
        db_type: Python type from PostgreSQL mapping
        model_type: Type annotation from Pydantic model

    Returns:
        True if types are compatible
    """
    # Handle exact match
    if db_type == model_type:
        return True

    # Handle str -> Enum (enums stored as text)
    if db_type is str:
        if hasattr(model_type, "__mro__") and any(
            c.__name__ == "Enum" for c in getattr(model_type, "__mro__", [])
        ):
            return True

    # Handle dict -> Any (JSONB can be any type)
    if db_type is dict:
        return True  # JSONB is flexible

    # Handle list compatibility
    if db_type is list:
        origin = getattr(model_type, "__origin__", None)
        if origin is list:
            return True

    # Handle numeric compatibility (int/float flexibility)
    if db_type in (int, float) and model_type in (int, float):
        return True

    return False
