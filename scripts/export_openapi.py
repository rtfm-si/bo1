#!/usr/bin/env python3
"""Export OpenAPI spec to JSON file for frontend type generation.

Usage:
    python scripts/export_openapi.py [output_path]
    python scripts/export_openapi.py --stdout  # Output to stdout

Defaults to openapi.json in the repo root.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Suppress all logging during import (backend logs to stdout during init)
logging.disable(logging.CRITICAL)
os.environ["LOG_LEVEL"] = "CRITICAL"

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Redirect stdout/stderr temporarily to suppress any remaining output
_stdout = sys.stdout
_stderr = sys.stderr
_devnull = open(os.devnull, "w")
sys.stdout = _devnull
sys.stderr = _devnull

from backend.api.main import app  # noqa: E402

# Restore stdout/stderr
_devnull.close()
sys.stdout = _stdout
sys.stderr = _stderr


def hoist_defs_to_schemas(spec: dict) -> dict:
    """Hoist inline $defs to components/schemas for openapi-typescript compatibility.

    Pydantic v2 creates inline $defs in each schema. openapi-typescript expects
    all refs to be in #/components/schemas/. This function:
    1. Hoists all $defs to components/schemas (with parent prefix to avoid conflicts)
    2. Rewrites $refs from #/$defs/Name to #/components/schemas/Parent_Name
    """
    schemas = spec.get("components", {}).get("schemas", {})
    hoisted: dict[str, dict] = {}

    def rewrite_refs(obj: dict | list, parent_schema: str) -> dict | list:
        """Recursively rewrite $refs from local $defs to hoisted schemas."""
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                if ref.startswith("#/$defs/"):
                    def_name = ref.split("/")[-1]
                    hoisted_name = f"{parent_schema}_{def_name}"
                    return {"$ref": f"#/components/schemas/{hoisted_name}"}
            return {k: rewrite_refs(v, parent_schema) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [rewrite_refs(item, parent_schema) for item in obj]
        return obj

    # First pass: hoist all $defs
    for schema_name, schema in list(schemas.items()):
        if "$defs" in schema:
            for def_name, def_schema in schema["$defs"].items():
                hoisted_name = f"{schema_name}_{def_name}"
                hoisted[hoisted_name] = def_schema

    # Second pass: rewrite refs and remove $defs
    for schema_name, schema in list(schemas.items()):
        if "$defs" in schema:
            rewritten = rewrite_refs(schema, schema_name)
            if isinstance(rewritten, dict):
                rewritten.pop("$defs", None)
                schemas[schema_name] = rewritten

    # Add hoisted schemas
    schemas.update(hoisted)

    return spec


def main() -> None:
    """Export OpenAPI spec to JSON file."""
    spec = app.openapi()
    spec = hoist_defs_to_schemas(spec)

    # Handle stdout mode for use with docker redirect
    if len(sys.argv) > 1 and sys.argv[1] == "--stdout":
        json.dump(spec, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return

    output_path = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")

    # Write with consistent formatting
    with output_path.open("w") as f:
        json.dump(spec, f, indent=2, sort_keys=True)
        f.write("\n")  # Trailing newline

    print(f"✓ OpenAPI spec exported to {output_path}", file=sys.stderr)
    print(f"  Paths: {len(spec.get('paths', {}))}", file=sys.stderr)
    print(f"  Schemas: {len(spec.get('components', {}).get('schemas', {}))}", file=sys.stderr)


if __name__ == "__main__":
    main()
