"""Tests for the datetime isoformat linter."""

import ast

# Import the linter module
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lint_datetime import IsoformatVisitor, check_file, load_allowlist


class TestIsoformatVisitor:
    """Tests for the AST visitor that detects .isoformat() calls."""

    def test_detects_isoformat_in_dict_literal(self) -> None:
        """Should detect .isoformat() inside dict."""
        code = """
def get_data():
    return {"created_at": dt.isoformat()}
"""
        tree = ast.parse(code)
        visitor = IsoformatVisitor(Path("test.py"))
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].context == "dict_literal"
        assert visitor.violations[0].line == 3

    def test_detects_isoformat_in_return_statement(self) -> None:
        """Should detect .isoformat() in return (outside dict)."""
        code = """
def get_time():
    return dt.isoformat()
"""
        tree = ast.parse(code)
        visitor = IsoformatVisitor(Path("test.py"))
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].context == "return_statement"

    def test_ignores_isoformat_outside_return_and_dict(self) -> None:
        """Should not flag .isoformat() in regular expressions."""
        code = """
def process():
    timestamp = dt.isoformat()  # Just assignment, not return
    cache_key = f"key:{dt.isoformat()}"
    print(dt.isoformat())
"""
        tree = ast.parse(code)
        visitor = IsoformatVisitor(Path("test.py"))
        visitor.visit(tree)

        assert len(visitor.violations) == 0

    def test_detects_nested_isoformat_in_dict(self) -> None:
        """Should detect .isoformat() in nested dict structures."""
        code = """
def get_response():
    return {
        "data": {
            "timestamps": {
                "created": obj.created_at.isoformat()
            }
        }
    }
"""
        tree = ast.parse(code)
        visitor = IsoformatVisitor(Path("test.py"))
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].context == "dict_literal"

    def test_detects_conditional_isoformat(self) -> None:
        """Should detect .isoformat() in conditional expressions."""
        code = """
def format_date():
    return {"date": dt.isoformat() if dt else None}
"""
        tree = ast.parse(code)
        visitor = IsoformatVisitor(Path("test.py"))
        visitor.visit(tree)

        assert len(visitor.violations) == 1

    def test_reports_correct_line_numbers(self) -> None:
        """Should report accurate line numbers for violations."""
        code = """
# Line 2
# Line 3
def get_data():  # Line 4
    # Line 5
    return {"created_at": dt.isoformat()}  # Line 6
"""
        tree = ast.parse(code)
        visitor = IsoformatVisitor(Path("test.py"))
        visitor.visit(tree)

        assert len(visitor.violations) == 1
        assert visitor.violations[0].line == 6


class TestCheckFile:
    """Tests for the file-level check function."""

    def test_check_file_with_violations(self) -> None:
        """Should return violations from a file."""
        code = """
def handler():
    return {"ts": datetime.now().isoformat()}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            violations = check_file(Path(f.name))

        assert len(violations) == 1

    def test_check_file_without_violations(self) -> None:
        """Should return empty list for clean files."""
        code = """
from pydantic import BaseModel
from datetime import datetime

class Response(BaseModel):
    created_at: datetime

def handler():
    return Response(created_at=datetime.now())
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            violations = check_file(Path(f.name))

        assert len(violations) == 0

    def test_check_file_handles_syntax_errors(self) -> None:
        """Should gracefully handle files with syntax errors."""
        code = """
def broken(
    # Missing closing paren
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            violations = check_file(Path(f.name))

        assert len(violations) == 0  # No crash, returns empty


class TestLoadAllowlist:
    """Tests for the allowlist loading function."""

    def test_load_allowlist_parses_paths(self) -> None:
        """Should parse path entries from allowlist file."""
        content = """# Comment line
backend/api/actions.py  # TODO: fix later
backend/api/events.py

# Another comment
backend/api/projects.py
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()

            allowlist = load_allowlist(Path(f.name))

        assert "backend/api/actions.py" in allowlist
        assert "backend/api/events.py" in allowlist
        assert "backend/api/projects.py" in allowlist
        assert len(allowlist) == 3

    def test_load_allowlist_skips_comments(self) -> None:
        """Should skip lines starting with #."""
        content = """# This is a comment
# backend/api/should_not_include.py
backend/api/include.py
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()

            allowlist = load_allowlist(Path(f.name))

        assert "backend/api/include.py" in allowlist
        assert len(allowlist) == 1

    def test_load_allowlist_returns_empty_for_missing_file(self) -> None:
        """Should return empty set if file doesn't exist."""
        allowlist = load_allowlist(Path("/nonexistent/path.txt"))
        assert len(allowlist) == 0

    def test_load_allowlist_returns_empty_for_none(self) -> None:
        """Should return empty set if path is None."""
        allowlist = load_allowlist(None)
        assert len(allowlist) == 0


class TestIntegration:
    """Integration tests using the actual project files."""

    def test_allowlist_covers_all_violations(self) -> None:
        """The allowlist should suppress all known violations."""
        # This test runs the actual linter
        import subprocess

        result = subprocess.run(
            ["python", "scripts/lint_datetime.py", "--base", ".", "--quiet"],
            capture_output=True,
            text=True,
        )
        # Exit code 0 means no violations
        assert result.returncode == 0, f"Violations found:\n{result.stdout}"

    def test_linter_detects_new_violation(self) -> None:
        """Adding a new .isoformat() should be detected."""
        # Create a temp file NOT in allowlist
        code = """
def test_endpoint():
    return {"timestamp": dt.isoformat()}
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir="backend/api", prefix="test_temp_", delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            violations = check_file(Path(temp_path))
            assert len(violations) == 1
        finally:
            Path(temp_path).unlink()
