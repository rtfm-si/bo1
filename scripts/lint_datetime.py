#!/usr/bin/env python3
"""AST-based linter to detect raw .isoformat() calls in API response code.

This script enforces that all datetime fields use Pydantic model serialization
rather than manual .isoformat() calls in dict literals or return statements.

Usage:
    python scripts/lint_datetime.py [--allowlist FILE] [--quiet]

Returns exit code 1 if violations found, 0 otherwise.
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """A detected .isoformat() usage in API code."""

    file: Path
    line: int
    context: str  # 'dict_literal' or 'return_statement'


def load_allowlist(allowlist_path: Path | None) -> set[str]:
    """Load allowlisted file paths from file."""
    if not allowlist_path or not allowlist_path.exists():
        return set()

    paths = set()
    for line in allowlist_path.read_text().splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        # Extract path (ignore TODO references after path)
        path = line.split()[0] if line else ""
        if path:
            paths.add(path)
    return paths


class IsoformatVisitor(ast.NodeVisitor):
    """AST visitor that detects .isoformat() in dict literals and returns."""

    def __init__(self, file_path: Path) -> None:
        """Initialize visitor with file path for violation reporting."""
        self.file_path = file_path
        self.violations: list[Violation] = []
        self._in_return = False
        self._in_dict = False

    def visit_Return(self, node: ast.Return) -> None:
        """Track when we're inside a return statement."""
        old = self._in_return
        self._in_return = True
        self.generic_visit(node)
        self._in_return = old

    def visit_Dict(self, node: ast.Dict) -> None:
        """Track when we're inside a dict literal."""
        old = self._in_dict
        self._in_dict = True
        self.generic_visit(node)
        self._in_dict = old

    def visit_Call(self, node: ast.Call) -> None:
        """Check for .isoformat() method calls."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "isoformat":
                # Only flag if inside dict or return
                if self._in_dict:
                    self.violations.append(
                        Violation(file=self.file_path, line=node.lineno, context="dict_literal")
                    )
                elif self._in_return:
                    self.violations.append(
                        Violation(file=self.file_path, line=node.lineno, context="return_statement")
                    )
        self.generic_visit(node)


def check_file(file_path: Path) -> list[Violation]:
    """Check a single file for .isoformat() violations."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return []

    visitor = IsoformatVisitor(file_path)
    visitor.visit(tree)
    return visitor.violations


def find_api_files(base_path: Path) -> list[Path]:
    """Find all Python files in backend/api/ directory."""
    api_dir = base_path / "backend" / "api"
    if not api_dir.exists():
        return []
    return sorted(api_dir.rglob("*.py"))


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Lint for raw .isoformat() in API code")
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path("scripts/lint_datetime_allowlist.txt"),
        help="File containing allowlisted paths",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output violation count")
    parser.add_argument(
        "--base", type=Path, default=Path("."), help="Base directory (default: current)"
    )
    args = parser.parse_args()

    allowlist = load_allowlist(args.allowlist)
    api_files = find_api_files(args.base)

    all_violations: list[Violation] = []

    for file_path in api_files:
        # Skip allowlisted files
        rel_path = str(file_path.relative_to(args.base))
        if rel_path in allowlist or any(rel_path.startswith(a) for a in allowlist):
            continue

        violations = check_file(file_path)
        all_violations.extend(violations)

    if not args.quiet:
        for v in all_violations:
            rel_path = v.file.relative_to(args.base)
            print(f"{rel_path}:{v.line}: .isoformat() in {v.context}")

    if all_violations:
        print(f"\nFound {len(all_violations)} violation(s)")
        return 1

    if not args.quiet:
        print("No violations found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
