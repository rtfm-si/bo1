#!/bin/bash
# Run chaos tests for Bo1 recovery path validation
#
# Usage:
#   ./scripts/run_chaos_tests.sh          # Run all chaos tests
#   ./scripts/run_chaos_tests.sh llm      # Run only LLM chaos tests
#   ./scripts/run_chaos_tests.sh -v       # Run with verbose output
#
# Tests are marked with @pytest.mark.chaos and run in isolation.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default settings
VERBOSE=""
TEST_FILTER=""
TIMEOUT=300  # 5 minutes per test file

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -vv)
            VERBOSE="-vv"
            shift
            ;;
        llm|redis|postgres|embedding|sse)
            TEST_FILTER="tests/chaos/test_${1}_chaos.py"
            shift
            ;;
        --coverage)
            COVERAGE="--cov=bo1 --cov-report=term-missing --cov-report=html:coverage_chaos"
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options] [test_type]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose    Verbose output"
            echo "  -vv              Very verbose output"
            echo "  --coverage       Generate coverage report"
            echo "  --timeout N      Set test timeout in seconds (default: 300)"
            echo "  -h, --help       Show this help"
            echo ""
            echo "Test types:"
            echo "  llm              Run LLM circuit breaker chaos tests"
            echo "  redis            Run Redis checkpoint chaos tests"
            echo "  postgres         Run PostgreSQL chaos tests"
            echo "  embedding        Run embedding service chaos tests"
            echo "  sse              Run SSE connection chaos tests"
            echo ""
            echo "Examples:"
            echo "  $0               Run all chaos tests"
            echo "  $0 llm           Run only LLM chaos tests"
            echo "  $0 -v --coverage Run all with verbose + coverage"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set test path
if [[ -z "$TEST_FILTER" ]]; then
    TEST_PATH="tests/chaos"
else
    TEST_PATH="$TEST_FILTER"
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Bo1 Chaos Test Suite                            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Tests: $TEST_PATH"
echo "║  Timeout: ${TIMEOUT}s per test"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Run tests
uv run pytest \
    "$TEST_PATH" \
    -m "chaos" \
    $VERBOSE \
    $COVERAGE \
    --timeout="$TIMEOUT" \
    --timeout-method=thread \
    -x \
    --tb=short \
    2>&1

EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Chaos tests passed"
else
    echo "❌ Chaos tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
