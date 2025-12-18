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


def main() -> None:
    """Export OpenAPI spec to JSON file."""
    spec = app.openapi()

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
