#!/usr/bin/env python3
"""Check if openapi.json is up-to-date with the backend FastAPI app.

Usage:
    python scripts/check_openapi_fresh.py
    uv run python scripts/check_openapi_fresh.py

Exits with code 1 if openapi.json is stale (backend changed but spec not regenerated).
"""

import hashlib
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

    Must match the transformation in export_openapi.py.
    """
    schemas = spec.get("components", {}).get("schemas", {})
    hoisted: dict[str, dict] = {}

    def rewrite_refs(obj: dict | list, parent_schema: str) -> dict | list:
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

    for schema_name, schema in list(schemas.items()):
        if "$defs" in schema:
            for def_name, def_schema in schema["$defs"].items():
                hoisted_name = f"{schema_name}_{def_name}"
                hoisted[hoisted_name] = def_schema

    for schema_name, schema in list(schemas.items()):
        if "$defs" in schema:
            rewritten = rewrite_refs(schema, schema_name)
            if isinstance(rewritten, dict):
                rewritten.pop("$defs", None)
                schemas[schema_name] = rewritten

    schemas.update(hoisted)
    return spec


def normalize_openapi(spec: dict) -> str:
    """Normalize OpenAPI spec for stable comparison.

    Removes runtime-dependent values like timestamps and versions that
    would cause spurious diffs.
    """
    # Deep copy to avoid modifying original
    normalized = json.loads(json.dumps(spec))

    # Remove fields that may change based on environment/runtime
    if "info" in normalized:
        # Version might be dynamic; keep it but it should be stable
        pass

    # Sort keys for consistent ordering
    return json.dumps(normalized, indent=2, sort_keys=True)


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def main() -> None:
    """Check if openapi.json matches current backend spec."""
    openapi_path = Path(__file__).parent.parent / "openapi.json"

    # Check if openapi.json exists
    if not openapi_path.exists():
        print("openapi.json not found", file=sys.stderr)
        print("Run `make openapi-export` to generate it", file=sys.stderr)
        sys.exit(1)

    # Get current spec from backend and apply same transformations as export
    current_spec = app.openapi()
    current_spec = hoist_defs_to_schemas(current_spec)
    current_normalized = normalize_openapi(current_spec)
    current_hash = compute_hash(current_normalized)

    # Read committed spec
    with openapi_path.open() as f:
        committed_spec = json.load(f)
    committed_normalized = normalize_openapi(committed_spec)
    committed_hash = compute_hash(committed_normalized)

    # Compare
    if current_hash == committed_hash:
        print("openapi.json is up-to-date with backend", file=sys.stderr)
        sys.exit(0)

    # Specs differ - show helpful diff info
    print("openapi.json is STALE - backend API changed but spec not regenerated", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"  Current backend hash:  {current_hash[:16]}", file=sys.stderr)
    print(f"  Committed spec hash:   {committed_hash[:16]}", file=sys.stderr)
    print("", file=sys.stderr)

    # Find what changed (paths, schemas)
    current_paths = set(current_spec.get("paths", {}).keys())
    committed_paths = set(committed_spec.get("paths", {}).keys())

    added_paths = current_paths - committed_paths
    removed_paths = committed_paths - current_paths

    if added_paths:
        print(f"  Added paths: {', '.join(sorted(added_paths)[:5])}", file=sys.stderr)
    if removed_paths:
        print(f"  Removed paths: {', '.join(sorted(removed_paths)[:5])}", file=sys.stderr)

    current_schemas = set(current_spec.get("components", {}).get("schemas", {}).keys())
    committed_schemas = set(committed_spec.get("components", {}).get("schemas", {}).keys())

    added_schemas = current_schemas - committed_schemas
    removed_schemas = committed_schemas - current_schemas

    if added_schemas:
        print(f"  Added schemas: {', '.join(sorted(added_schemas)[:5])}", file=sys.stderr)
    if removed_schemas:
        print(f"  Removed schemas: {', '.join(sorted(removed_schemas)[:5])}", file=sys.stderr)

    print("", file=sys.stderr)
    print("To fix: make openapi-export && cd frontend && npm run generate:types", file=sys.stderr)
    print("Or run: make generate-types", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
