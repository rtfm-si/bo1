#!/bin/bash
# Install git hooks for Board of One
# Usage: ./scripts/install-hooks.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "📦 Installing git hooks for Board of One..."
echo ""

# =============================================================================
# Pre-Push Hook
# =============================================================================
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook to run CI/CD validation checks before pushing
# This catches issues that would cause CI/CD to fail:
# 1. Type checking errors (mypy)
# 2. Missing files required by Docker builds
# 3. Tests that would fail in CI

set -e  # Exit on first error

echo ""
echo "🚀 Pre-push validation running..."
echo "   (This mirrors CI/CD checks to prevent push failures)"
echo ""

EXIT_CODE=0

# =============================================================================
# 1. Type Checking (matches CI workflow line 48)
# =============================================================================
echo "📝 Step 1/4: Type checking with mypy..."
if command -v uv &> /dev/null; then
    uv run mypy bo1/ --install-types --non-interactive
else
    mypy bo1/ --install-types --non-interactive
fi

if [ $? -ne 0 ]; then
    echo "❌ Type checking failed"
    EXIT_CODE=1
fi
echo "✅ Type checking passed"
echo ""

# =============================================================================
# 2. Docker Build File Validation (NEW - catches missing files)
# =============================================================================
echo "🐋 Step 2/4: Validating Docker build dependencies..."

# Check if critical files for Docker builds are tracked by git
MISSING_FILES=()

# Files required by backend/Dockerfile
for file in "pyproject.toml" "README.md" "uv.lock"; do
    if ! git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "❌ Docker build validation failed!"
    echo ""
    echo "The following files are required by Docker builds but NOT tracked by git:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "These files exist locally but are in .gitignore, so CI/CD won't have them."
    echo "Either:"
    echo "  1. Remove them from .gitignore and commit them (if they're lock files)"
    echo "  2. Update Dockerfiles to make them optional"
    echo ""
    EXIT_CODE=1
else
    echo "✅ All Docker build dependencies are tracked by git"
fi
echo ""

# =============================================================================
# 3. Quick Test Suite (non-LLM tests only)
# =============================================================================
echo "🧪 Step 3/4: Running quick test suite (non-LLM tests)..."
if command -v uv &> /dev/null; then
    # Run only fast tests (skip LLM calls)
    uv run pytest -m "not requires_llm" -q --tb=line --maxfail=3 2>&1 | tail -20
    TEST_EXIT=$?
else
    echo "⚠️  uv not found, skipping tests"
    TEST_EXIT=0
fi

if [ $TEST_EXIT -ne 0 ]; then
    echo "❌ Tests failed"
    EXIT_CODE=1
else
    echo "✅ Tests passed"
fi
echo ""

# =============================================================================
# 4. Linting (ruff check)
# =============================================================================
echo "🔍 Step 4/4: Linting with ruff..."
if command -v uv &> /dev/null; then
    uv run ruff check . --quiet
    LINT_EXIT=$?
else
    echo "⚠️  uv not found, skipping linting"
    LINT_EXIT=0
fi

if [ $LINT_EXIT -ne 0 ]; then
    echo "❌ Linting failed"
    EXIT_CODE=1
else
    echo "✅ Linting passed"
fi
echo ""

# =============================================================================
# Final Result
# =============================================================================
if [ $EXIT_CODE -ne 0 ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "❌ Pre-push validation FAILED!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "One or more checks failed. These would cause CI/CD to fail."
    echo "Please fix the errors above before pushing."
    echo ""
    echo "To skip this check (NOT recommended), use:"
    echo "  git push --no-verify"
    echo ""
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "✅ All pre-push validation checks passed!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Proceeding with push..."
echo ""

exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"
echo "✅ Installed pre-push hook"

# =============================================================================
# Install pre-commit hooks
# =============================================================================
if command -v pre-commit &> /dev/null; then
    echo ""
    echo "📦 Installing pre-commit hooks..."
    cd "$REPO_ROOT"
    pre-commit install
    echo "✅ Installed pre-commit hooks"
else
    echo ""
    echo "⚠️  pre-commit not found. Install with: pip install pre-commit"
    echo "   Then run: pre-commit install"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Git hooks installation complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Hooks installed:"
echo "  - Pre-commit: Runs ruff, mypy on changed files"
echo "  - Pre-push:   Runs full CI/CD validation (mypy, tests, linting, Docker checks)"
echo ""
echo "To bypass hooks (not recommended):"
echo "  git commit --no-verify"
echo "  git push --no-verify"
echo ""
