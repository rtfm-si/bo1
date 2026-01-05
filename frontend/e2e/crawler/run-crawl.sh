#!/bin/bash
#
# Website Crawler Runner
#
# Usage:
#   ./run-crawl.sh                    # Full crawl
#   ./run-crawl.sh setup              # Capture auth state
#   ./run-crawl.sh smoke              # Quick smoke test
#   ./run-crawl.sh meetings           # Meetings section only
#   ./run-crawl.sh actions            # Actions section only
#   ./run-crawl.sh settings           # Settings section only
#   ./run-crawl.sh datasets           # Datasets section only
#   ./run-crawl.sh full --new-meeting # Full crawl with new meeting test
#

set -e

cd "$(dirname "$0")/../.."

MODE=${1:-full}
EXTRA_ARGS=""

# Parse flags
for arg in "$@"; do
    case $arg in
        --new-meeting)
            export RUN_NEW_MEETING=true
            ;;
        --verbose)
            export CRAWLER_VERBOSE=true
            ;;
        --headed)
            EXTRA_ARGS="$EXTRA_ARGS --headed"
            ;;
        --local)
            export CRAWLER_BASE_URL="http://localhost:5173"
            ;;
    esac
done

case $MODE in
    setup)
        echo "=== Setting up authentication ==="
        echo "A browser will open. Please log in manually."
        npx playwright test e2e/crawler/setup-auth.ts --headed
        ;;
    smoke)
        echo "=== Running smoke test ==="
        npx playwright test e2e/crawler/crawler.spec.ts -g "smoke test" $EXTRA_ARGS
        ;;
    meetings)
        echo "=== Crawling meetings pages ==="
        npx playwright test e2e/crawler/crawler.spec.ts -g "meetings pages" $EXTRA_ARGS
        ;;
    actions)
        echo "=== Crawling actions pages ==="
        npx playwright test e2e/crawler/crawler.spec.ts -g "actions pages" $EXTRA_ARGS
        ;;
    settings)
        echo "=== Crawling settings pages ==="
        npx playwright test e2e/crawler/crawler.spec.ts -g "settings pages" $EXTRA_ARGS
        ;;
    datasets)
        echo "=== Crawling datasets pages ==="
        npx playwright test e2e/crawler/crawler.spec.ts -g "datasets pages" $EXTRA_ARGS
        ;;
    full|comprehensive)
        echo "=== Running comprehensive crawl ==="
        if [ "$RUN_NEW_MEETING" = "true" ]; then
            echo "WARNING: New meeting creation is ENABLED"
        fi
        npx playwright test e2e/crawler/crawler.spec.ts -g "comprehensive crawl" $EXTRA_ARGS
        ;;
    *)
        echo "Usage: $0 [mode] [flags]"
        echo ""
        echo "Modes:"
        echo "  setup       - Capture auth state (opens browser)"
        echo "  smoke       - Quick smoke test (dashboard only)"
        echo "  meetings    - Crawl meetings section"
        echo "  actions     - Crawl actions section"
        echo "  settings    - Crawl settings section"
        echo "  datasets    - Crawl datasets section"
        echo "  full        - Comprehensive crawl (default)"
        echo ""
        echo "Flags:"
        echo "  --new-meeting  Enable new meeting creation test"
        echo "  --verbose      Enable verbose logging"
        echo "  --headed       Run with visible browser"
        echo "  --local        Test against localhost:5173"
        exit 1
        ;;
esac

echo ""
echo "=== Crawl complete ==="
echo "Reports saved to: e2e/crawler/reports/"
