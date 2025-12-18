"""Test that all @retry_db usages have explicit total_timeout parameter.

This test uses AST parsing to find all @retry_db and @retry_db_async
decorators and ensures they specify total_timeout explicitly, preventing
reliance on implicit defaults.
"""

import ast
from pathlib import Path

import pytest

# Directories to scan for retry decorator usage
SCAN_DIRECTORIES = [
    "bo1",
    "backend",
]

# Files/patterns to exclude from scanning
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".venv",
    "node_modules",
]


class RetryDecoratorVisitor(ast.NodeVisitor):
    """AST visitor to find @retry_db decorators without explicit total_timeout."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[dict] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_decorators(node)
        self.generic_visit(node)

    def _check_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check decorators for retry_db/retry_db_async without total_timeout."""
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            # Get decorator name
            if isinstance(decorator.func, ast.Name):
                name = decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                name = decorator.func.attr
            else:
                continue

            if name not in ("retry_db", "retry_db_async"):
                continue

            # Check if total_timeout is specified as keyword argument
            has_total_timeout = any(kw.arg == "total_timeout" for kw in decorator.keywords)

            if not has_total_timeout:
                self.violations.append(
                    {
                        "file": self.filepath,
                        "line": decorator.lineno,
                        "function": node.name,
                        "decorator": name,
                    }
                )


def find_python_files(base_dirs: list[str]) -> list[Path]:
    """Find all Python files in the given directories."""
    project_root = Path(__file__).parent.parent.parent
    files = []

    for base_dir in base_dirs:
        dir_path = project_root / base_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Skip excluded patterns
            if any(excl in str(py_file) for excl in EXCLUDE_PATTERNS):
                continue
            files.append(py_file)

    return files


def check_file_for_violations(filepath: Path) -> list[dict]:
    """Parse a Python file and check for retry decorator violations."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = RetryDecoratorVisitor(str(filepath))
    visitor.visit(tree)
    return visitor.violations


class TestRetryTimeoutConsistency:
    """Tests for @retry_db timeout consistency."""

    def test_all_retry_db_have_explicit_timeout(self) -> None:
        """All @retry_db decorators must have explicit total_timeout parameter."""
        files = find_python_files(SCAN_DIRECTORIES)
        all_violations: list[dict] = []

        for filepath in files:
            violations = check_file_for_violations(filepath)
            all_violations.extend(violations)

        if all_violations:
            msg_lines = [
                "Found @retry_db decorators without explicit total_timeout:",
                "",
            ]
            for v in all_violations:
                msg_lines.append(
                    f"  {v['file']}:{v['line']} - {v['function']}() "
                    f"uses @{v['decorator']} without total_timeout"
                )
            msg_lines.extend(
                [
                    "",
                    "Fix: Add explicit total_timeout parameter, e.g.:",
                    "  @retry_db(max_attempts=3, base_delay=0.5, total_timeout=30.0)",
                ]
            )
            pytest.fail("\n".join(msg_lines))

    def test_scan_finds_test_files(self) -> None:
        """Sanity check: ensure we're scanning Python files."""
        files = find_python_files(SCAN_DIRECTORIES)
        assert len(files) > 0, "No Python files found to scan"

    def test_visitor_detects_missing_timeout(self) -> None:
        """Test that the AST visitor correctly detects missing timeout."""
        source = """
@retry_db(max_attempts=3)
def bad_function():
    pass

@retry_db(max_attempts=3, total_timeout=30.0)
def good_function():
    pass
"""
        tree = ast.parse(source)
        visitor = RetryDecoratorVisitor("test.py")
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0]["function"] == "bad_function"

    def test_visitor_handles_async(self) -> None:
        """Test that the AST visitor handles async functions."""
        source = """
@retry_db_async(max_attempts=3)
async def bad_async():
    pass

@retry_db_async(max_attempts=3, total_timeout=30.0)
async def good_async():
    pass
"""
        tree = ast.parse(source)
        visitor = RetryDecoratorVisitor("test.py")
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0]["function"] == "bad_async"
