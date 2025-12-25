#!/usr/bin/env python3
"""Filter OpenAPI spec to exclude admin endpoints for public documentation.

Removes:
- Paths matching /admin/* and /api/admin/*
- Schemas referenced only by admin endpoints
- Admin-related tags

Usage:
    python scripts/filter_openapi_spec.py [input_path] [output_path]
    python scripts/filter_openapi_spec.py --stdout  # Output to stdout
    python scripts/filter_openapi_spec.py  # Default: openapi.json -> openapi-public.json
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

# Patterns for admin paths to filter out
ADMIN_PATH_PATTERNS = [
    r"^/admin(/.*)?$",
    r"^/api/admin(/.*)?$",
]


def is_admin_path(path: str) -> bool:
    """Check if a path matches admin endpoint patterns."""
    for pattern in ADMIN_PATH_PATTERNS:
        if re.match(pattern, path):
            return True
    return False


def extract_schema_refs(obj: Any, refs: set[str] | None = None) -> set[str]:
    """Recursively extract all $ref schema references from an object."""
    if refs is None:
        refs = set()

    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            # Extract schema name from #/components/schemas/SchemaName
            if ref.startswith("#/components/schemas/"):
                schema_name = ref.split("/")[-1]
                refs.add(schema_name)
        for value in obj.values():
            extract_schema_refs(value, refs)
    elif isinstance(obj, list):
        for item in obj:
            extract_schema_refs(item, refs)

    return refs


def get_all_schema_dependencies(schemas: dict[str, Any], initial_schemas: set[str]) -> set[str]:
    """Get all schemas including transitive dependencies.

    Starting from initial_schemas, recursively find all referenced schemas.
    """
    all_schemas = set(initial_schemas)
    to_process = list(initial_schemas)

    while to_process:
        schema_name = to_process.pop()
        if schema_name not in schemas:
            continue

        schema_def = schemas[schema_name]
        refs = extract_schema_refs(schema_def)

        for ref in refs:
            if ref not in all_schemas:
                all_schemas.add(ref)
                to_process.append(ref)

    return all_schemas


def filter_openapi_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Filter OpenAPI spec to remove admin endpoints and unused schemas.

    Args:
        spec: Full OpenAPI specification dict

    Returns:
        Filtered OpenAPI specification dict
    """
    filtered = json.loads(json.dumps(spec))  # Deep copy

    # Step 1: Remove admin paths
    paths = filtered.get("paths", {})
    admin_paths = [p for p in paths if is_admin_path(p)]
    for path in admin_paths:
        del paths[path]

    # Step 2: Collect all schema refs used by remaining (public) paths
    public_schemas = extract_schema_refs(paths)

    # Step 3: Get transitive dependencies (schemas referencing other schemas)
    schemas = filtered.get("components", {}).get("schemas", {})
    required_schemas = get_all_schema_dependencies(schemas, public_schemas)

    # Step 4: Remove unused schemas (admin-only)
    admin_schemas = set(schemas.keys()) - required_schemas
    for schema_name in admin_schemas:
        del schemas[schema_name]

    # Step 5: Remove admin-related tags from global tags list
    if "tags" in filtered:
        filtered["tags"] = [t for t in filtered["tags"] if t.get("name", "").lower() != "admin"]

    # Step 6: Update description to indicate filtered spec
    if "info" in filtered:
        desc = filtered["info"].get("description", "")
        if desc:
            filtered["info"]["description"] = (
                desc + "\n\n**Note:** This is the public API documentation. "
                "Admin endpoints are documented separately."
            )
        else:
            filtered["info"]["description"] = (
                "Public API documentation. Admin endpoints are documented separately."
            )

    return filtered


def main() -> None:
    """Main entry point for CLI usage."""
    # Determine input/output paths
    if len(sys.argv) > 1 and sys.argv[1] == "--stdout":
        input_path = Path("openapi.json")
        output_stdout = True
    else:
        input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
        output_path = Path(sys.argv[2] if len(sys.argv) > 2 else "openapi-public.json")
        output_stdout = False

    # Load input spec
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with input_path.open() as f:
        spec = json.load(f)

    # Count before filtering
    paths_before = len(spec.get("paths", {}))
    schemas_before = len(spec.get("components", {}).get("schemas", {}))

    # Filter the spec
    filtered_spec = filter_openapi_spec(spec)

    # Count after filtering
    paths_after = len(filtered_spec.get("paths", {}))
    schemas_after = len(filtered_spec.get("components", {}).get("schemas", {}))

    # Output
    if output_stdout:
        json.dump(filtered_spec, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        with output_path.open("w") as f:
            json.dump(filtered_spec, f, indent=2, sort_keys=True)
            f.write("\n")

        print(f"✓ Public OpenAPI spec exported to {output_path}", file=sys.stderr)
        print(
            f"  Paths: {paths_before} → {paths_after} ({paths_before - paths_after} removed)",
            file=sys.stderr,
        )
        print(
            f"  Schemas: {schemas_before} → {schemas_after} ({schemas_before - schemas_after} removed)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
