#!/usr/bin/env python3
"""Audit Pydantic models against PostgreSQL schema.

Compares field definitions in Pydantic models with actual database columns
to detect schema drift and missing migrations.

Usage:
    python scripts/audit_model_schema.py
    python scripts/audit_model_schema.py --output report.md
    python scripts/audit_model_schema.py --json

Exit codes:
    0 - No gaps found
    1 - Gaps detected (use in CI to fail builds)
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from psycopg2.extras import RealDictCursor

from bo1.models.recommendations import Recommendation
from bo1.models.session import Session
from bo1.models.state import ContributionMessage
from bo1.state.database import db_session_batch

# =============================================================================
# Type Mappings: Python/Pydantic → PostgreSQL
# =============================================================================

# Map Python types to compatible PostgreSQL types
PYTHON_TO_PG_TYPES: dict[str, set[str]] = {
    # Strings
    "str": {"text", "character varying", "varchar", "name", "uuid"},
    "str | None": {"text", "character varying", "varchar", "name", "uuid"},
    # Integers
    "int": {"integer", "bigint", "smallint", "serial", "bigserial"},
    "int | None": {"integer", "bigint", "smallint", "serial", "bigserial"},
    # Floats
    "float": {"double precision", "real", "numeric", "decimal"},
    "float | None": {"double precision", "real", "numeric", "decimal"},
    # Booleans
    "bool": {"boolean"},
    "bool | None": {"boolean"},
    # Datetime
    "datetime": {"timestamp with time zone", "timestamp without time zone", "timestamp"},
    "datetime | None": {"timestamp with time zone", "timestamp without time zone", "timestamp"},
    # JSON/dict
    "dict": {"jsonb", "json"},
    "dict | None": {"jsonb", "json"},
    "dict[str, Any]": {"jsonb", "json"},
    "dict[str, Any] | None": {"jsonb", "json"},
    "dict[str, str]": {"jsonb", "json"},
    "dict[str, str] | None": {"jsonb", "json"},
    # Lists
    "list": {"jsonb", "json", "ARRAY"},
    "list | None": {"jsonb", "json", "ARRAY"},
    "list[str]": {"jsonb", "json", "ARRAY"},
    "list[str] | None": {"jsonb", "json", "ARRAY"},
    "list[float]": {"jsonb", "json", "ARRAY", "vector"},
    "list[float] | None": {"jsonb", "json", "ARRAY", "vector"},
    # Enums (stored as text/varchar)
    "SessionStatus": {"text", "character varying", "varchar"},
    "ContributionType": {"text", "character varying", "varchar"},
    "ContributionStatus": {"text", "character varying", "varchar"},
    "DeliberationPhaseType": {"text", "character varying", "varchar"},
    "DeliberationPhaseType | str": {"text", "character varying", "varchar"},
    "DeliberationPhaseType | str | None": {"text", "character varying", "varchar"},
}

# Fields intentionally not in database (computed, ephemeral, etc.)
KNOWN_EXCEPTIONS: dict[str, set[str]] = {
    "sessions": {
        # These are Pydantic model fields that don't exist in DB
    },
    "contributions": set(),
    "recommendations": {
        "weight",  # Computed at runtime, not persisted
        "alternatives_considered",  # Optional rich field, not in DB
        "risk_assessment",  # Optional rich field, not in DB
    },
}

# Map model classes to table names
MODEL_TABLE_MAPPING: dict[type, str] = {
    Session: "sessions",
    ContributionMessage: "contributions",
    Recommendation: "recommendations",
}


# =============================================================================
# Data Classes for Results
# =============================================================================


@dataclass
class ColumnInfo:
    """Database column metadata."""

    name: str
    data_type: str
    is_nullable: bool
    column_default: str | None = None


@dataclass
class FieldInfo:
    """Pydantic model field metadata."""

    name: str
    type_annotation: str
    is_optional: bool
    default: Any = None


@dataclass
class TypeMismatch:
    """Type compatibility issue."""

    field_name: str
    python_type: str
    db_type: str
    message: str


@dataclass
class AuditResult:
    """Audit results for a single model/table pair."""

    model_name: str
    table_name: str
    missing_in_db: list[str] = field(default_factory=list)
    missing_in_model: list[str] = field(default_factory=list)
    type_mismatches: list[TypeMismatch] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Return True if any validation issues were found."""
        return bool(self.missing_in_db or self.missing_in_model or self.type_mismatches)


# =============================================================================
# Schema Introspection
# =============================================================================


def get_table_columns(table_name: str) -> list[ColumnInfo]:
    """Query PostgreSQL information_schema for table columns.

    Uses db_session_batch() with default statement timeout to prevent
    runaway queries against information_schema.
    """
    query = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = %s
    ORDER BY ordinal_position;
    """

    with db_session_batch() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (table_name,))
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


def get_model_fields(model_class: type) -> list[FieldInfo]:
    """Extract field definitions from a Pydantic model."""
    fields = []

    for name, field_info in model_class.model_fields.items():
        # Get type annotation as string
        annotation = field_info.annotation
        type_str = _format_type_annotation(annotation)

        # Determine if optional
        is_optional = _is_optional_type(annotation) or field_info.default is not None

        fields.append(
            FieldInfo(
                name=name,
                type_annotation=type_str,
                is_optional=is_optional,
                default=field_info.default,
            )
        )

    return fields


def _format_type_annotation(annotation: Any) -> str:
    """Format a type annotation to a readable string."""
    if annotation is None:
        return "None"

    # Handle string annotations
    if isinstance(annotation, str):
        return annotation

    # Get the origin type (for generics like list[str], dict[str, Any], etc.)
    origin = getattr(annotation, "__origin__", None)

    # Handle Union types (including Optional which is Union[X, None])
    if origin is type(None) or str(origin) == "typing.Union":
        args = getattr(annotation, "__args__", ())
        # Check if it's Optional (Union with None)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            inner = _format_type_annotation(non_none_args[0])
            return f"{inner} | None"
        return " | ".join(_format_type_annotation(a) for a in args)

    # Handle generic types
    if origin is not None:
        args = getattr(annotation, "__args__", ())
        if args:
            args_str = ", ".join(_format_type_annotation(a) for a in args)
            origin_name = getattr(origin, "__name__", str(origin))
            return f"{origin_name}[{args_str}]"
        return getattr(origin, "__name__", str(origin))

    # Handle regular types
    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation).replace("typing.", "")


def _is_optional_type(annotation: Any) -> bool:
    """Check if a type annotation is Optional (Union with None)."""
    origin = getattr(annotation, "__origin__", None)
    if str(origin) == "typing.Union":
        args = getattr(annotation, "__args__", ())
        return type(None) in args
    return False


# =============================================================================
# Comparison Logic
# =============================================================================


def compare_model_to_schema(
    model_class: type, table_name: str, known_exceptions: set[str] | None = None
) -> AuditResult:
    """Compare a Pydantic model to its database table schema."""
    result = AuditResult(model_name=model_class.__name__, table_name=table_name)
    exceptions = known_exceptions or set()

    # Get schema from both sources
    db_columns = get_table_columns(table_name)
    model_fields = get_model_fields(model_class)

    db_column_map = {col.name: col for col in db_columns}
    model_field_map = {f.name: f for f in model_fields}

    # Check for fields in model but not in DB
    for field_name, field_info in model_field_map.items():
        if field_name in exceptions:
            continue

        if field_name not in db_column_map:
            result.missing_in_db.append(field_name)
        else:
            # Check type compatibility
            db_col = db_column_map[field_name]
            mismatch = check_type_compatibility(field_info, db_col)
            if mismatch:
                result.type_mismatches.append(mismatch)

    # Check for columns in DB but not in model
    for col_name, _col_info in db_column_map.items():
        if col_name not in model_field_map:
            result.missing_in_model.append(col_name)

    return result


def check_type_compatibility(field: FieldInfo, column: ColumnInfo) -> TypeMismatch | None:
    """Check if a Pydantic field type is compatible with a PostgreSQL column type."""
    python_type = field.type_annotation
    db_type = column.data_type

    # Look up compatible PostgreSQL types for this Python type
    compatible_types = PYTHON_TO_PG_TYPES.get(python_type)

    if compatible_types is None:
        # Unknown Python type - try base type matching
        base_type = python_type.split("[")[0].split(" |")[0].strip()
        compatible_types = PYTHON_TO_PG_TYPES.get(base_type)

    if compatible_types is None:
        return TypeMismatch(
            field_name=field.name,
            python_type=python_type,
            db_type=db_type,
            message=f"Unknown Python type '{python_type}' - cannot verify compatibility",
        )

    # Check if DB type is in the compatible set
    if db_type.lower() not in {t.lower() for t in compatible_types}:
        # Special case: handle ARRAY types
        if "ARRAY" in db_type.upper() and "list" in python_type.lower():
            return None  # Compatible

        return TypeMismatch(
            field_name=field.name,
            python_type=python_type,
            db_type=db_type,
            message=f"Type mismatch: Python '{python_type}' vs DB '{db_type}'",
        )

    return None


# =============================================================================
# Report Generation
# =============================================================================


def generate_markdown_report(results: list[AuditResult], timestamp: datetime) -> str:
    """Generate a markdown report of audit results."""
    lines = [
        "# Model-Schema Audit Report",
        "",
        f"Generated: {timestamp.isoformat()}",
        "",
    ]

    total_issues = sum(1 for r in results if r.has_issues)
    lines.append(f"**Summary:** {len(results)} models audited, {total_issues} with issues")
    lines.append("")

    for result in results:
        status = "❌" if result.has_issues else "✅"
        lines.append(f"## {status} {result.model_name} → `{result.table_name}`")
        lines.append("")

        if not result.has_issues:
            lines.append("No issues found.")
            lines.append("")
            continue

        if result.missing_in_db:
            lines.append("### Fields in Model but NOT in Database")
            lines.append("")
            lines.append("These fields may need migrations:")
            lines.append("")
            for field_name in result.missing_in_db:
                lines.append(f"- `{field_name}`")
            lines.append("")

        if result.missing_in_model:
            lines.append("### Columns in Database but NOT in Model")
            lines.append("")
            lines.append("These may be untracked schema or intentional DB-only columns:")
            lines.append("")
            for col_name in result.missing_in_model:
                lines.append(f"- `{col_name}`")
            lines.append("")

        if result.type_mismatches:
            lines.append("### Type Mismatches")
            lines.append("")
            lines.append("| Field | Python Type | DB Type | Issue |")
            lines.append("|-------|-------------|---------|-------|")
            for mismatch in result.type_mismatches:
                lines.append(
                    f"| `{mismatch.field_name}` | `{mismatch.python_type}` "
                    f"| `{mismatch.db_type}` | {mismatch.message} |"
                )
            lines.append("")

    return "\n".join(lines)


def generate_json_report(results: list[AuditResult], timestamp: datetime) -> str:
    """Generate a JSON report of audit results."""
    data = {
        "timestamp": timestamp.isoformat(),
        "summary": {
            "models_audited": len(results),
            "models_with_issues": sum(1 for r in results if r.has_issues),
        },
        "results": [
            {
                "model": result.model_name,
                "table": result.table_name,
                "has_issues": result.has_issues,
                "missing_in_db": result.missing_in_db,
                "missing_in_model": result.missing_in_model,
                "type_mismatches": [
                    {
                        "field": m.field_name,
                        "python_type": m.python_type,
                        "db_type": m.db_type,
                        "message": m.message,
                    }
                    for m in result.type_mismatches
                ],
            }
            for result in results
        ],
    }
    return json.dumps(data, indent=2)


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> int:
    """Run the model-schema audit."""
    parser = argparse.ArgumentParser(
        description="Audit Pydantic models against PostgreSQL schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--output", "-o", type=Path, help="Output file path (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of markdown")
    parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 if issues found")
    args = parser.parse_args()

    timestamp = datetime.now()
    results: list[AuditResult] = []

    print("Auditing model-schema alignment...", file=sys.stderr)

    for model_class, table_name in MODEL_TABLE_MAPPING.items():
        print(f"  Checking {model_class.__name__} → {table_name}...", file=sys.stderr)
        exceptions = KNOWN_EXCEPTIONS.get(table_name, set())
        result = compare_model_to_schema(model_class, table_name, exceptions)
        results.append(result)

    # Generate report
    if args.json:
        report = generate_json_report(results, timestamp)
    else:
        report = generate_markdown_report(results, timestamp)

    # Output report
    if args.output:
        args.output.write_text(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Determine exit code
    has_issues = any(r.has_issues for r in results)

    if has_issues:
        print(
            f"\n⚠️  Found issues in {sum(1 for r in results if r.has_issues)} model(s)",
            file=sys.stderr,
        )
        if args.ci:
            return 1
    else:
        print("\n✅ All models align with database schema", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
