# Website Crawler

Self-discovering website crawler for comprehensive testing of boardof.one.

## Features

- **Route Discovery**: Automatically finds all pages by following links
- **Element Testing**: Tests all buttons, links, dropdowns, inputs, tabs, accordions
- **Validation**: Checks for console errors, network errors, empty content, broken images
- **Accessibility**: Basic a11y checks (alt text, button names, input labels)
- **Reporting**: Generates detailed markdown reports with health scores
- **Configurable**: Control depth, pages, what to skip, and whether to run new meetings

## Quick Start

### 1. Setup Authentication (one-time)

```bash
# Run in headed mode to login manually and capture session
cd frontend
npx playwright test e2e/crawler/setup-auth.ts --headed
```

This saves your auth state to `.auth-state.json` for future headless runs.

### 2. Run Full Crawl

```bash
# Default: crawl boardof.one, skip new meeting creation
npx playwright test e2e/crawler/crawler.spec.ts -g "comprehensive crawl"

# With verbose output
CRAWLER_VERBOSE=true npx playwright test e2e/crawler/crawler.spec.ts -g "comprehensive"

# Test new meeting creation (caution: creates data)
RUN_NEW_MEETING=true npx playwright test e2e/crawler/crawler.spec.ts -g "comprehensive"
```

### 3. Run Focused Crawls

```bash
# Just dashboard
npx playwright test e2e/crawler/crawler.spec.ts -g "smoke test"

# Meetings section only
npx playwright test e2e/crawler/crawler.spec.ts -g "meetings pages"

# Actions section only
npx playwright test e2e/crawler/crawler.spec.ts -g "actions pages"

# Settings section only
npx playwright test e2e/crawler/crawler.spec.ts -g "settings pages"

# Datasets section only
npx playwright test e2e/crawler/crawler.spec.ts -g "datasets pages"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAWLER_BASE_URL` | `https://boardof.one` | Site to crawl |
| `CRAWLER_USER_EMAIL` | `e2e.test@boardof.one` | Test user email |
| `CRAWLER_USER_PASSWORD` | (none) | Password for auto-login |
| `CRAWLER_AUTH_STATE` | `.auth-state.json` | Saved auth state file |
| `CRAWLER_MAX_PAGES` | `100` | Max pages to crawl |
| `CRAWLER_MAX_DEPTH` | `5` | Max link depth |
| `CRAWLER_VERBOSE` | `false` | Verbose logging |
| `RUN_NEW_MEETING` | `false` | Test meeting creation |

### Local Development

```bash
# Test against local dev server
E2E_BASE_URL=http://localhost:5173 npx playwright test e2e/crawler/crawler.spec.ts
```

## Reports

Reports are saved to `e2e/crawler/reports/`:

- `crawl-report-{timestamp}.md` - Human-readable markdown report
- `crawl-report-{timestamp}.json` - Raw data for analysis

### Report Contents

- **Executive Summary**: Pages, elements, interactions, issues count
- **Health Score**: 0-100 score based on success rate and issues
- **Issues by Category**: Grouped counts of issue types
- **Critical & Error Issues**: Detailed list requiring attention
- **Warnings**: Expandable section of minor issues
- **Page Details**: Per-page breakdown of validation results
- **Discovered Routes**: All routes found during crawl

## Issue Categories

| Category | Description |
|----------|-------------|
| `console_error` | JavaScript errors in console |
| `network_error` | Failed HTTP requests (4xx/5xx) |
| `empty_content` | Content areas with no text |
| `broken_image` | Images that failed to load |
| `interaction_failed` | Elements that couldn't be clicked/used |
| `timeout` | Page load timeouts |
| `navigation_error` | Failed page navigations |
| `accessibility` | Missing alt text, labels, etc. |

## What Gets Tested

### Elements Discovered
- Buttons and `[role="button"]`
- Internal links (`<a href>`)
- Dropdowns and selects
- Text inputs and textareas
- Checkboxes, radios, switches
- Tabs and accordions
- Menu triggers

### Validations
- Console errors
- Network errors (4xx, 5xx)
- Empty content areas
- Broken images
- Basic accessibility

### Skipped by Default
- External links
- Logout/destructive actions
- New meeting creation (unless `RUN_NEW_MEETING=true`)
- Admin pages
- Auth callback routes
- File downloads (PDF, ZIP, etc.)

## Architecture

```
e2e/crawler/
├── types.ts           # TypeScript interfaces
├── crawler.ts         # Main WebsiteCrawler class
├── report-generator.ts # Markdown report generation
├── crawler.spec.ts    # Playwright test suites
├── setup-auth.ts      # Auth state capture
├── index.ts           # Module exports
└── reports/           # Generated reports
    └── *.md, *.json
```

## Troubleshooting

### "No authentication method available"

Run the auth setup:
```bash
npx playwright test e2e/crawler/setup-auth.ts --headed
```

### Tests timing out

Increase timeout or reduce scope:
```bash
CRAWLER_MAX_PAGES=20 npx playwright test e2e/crawler/crawler.spec.ts
```

### Too many false positives

Check the report for patterns. Common causes:
- Elements that disappear after click (expected behavior)
- Slow API responses (increase timeout)
- Dynamic content loading (crawler waits, but may miss some)

## Extending

The crawler is designed to be extended:

```typescript
import { WebsiteCrawler, ReportGenerator } from './crawler';

const crawler = new WebsiteCrawler(page, context, {
  baseUrl: 'https://example.com',
  maxPages: 50,
  skipPatterns: [/admin/, /logout/],
  includePatterns: [/dashboard/]
});

const report = await crawler.crawl();
const generator = new ReportGenerator(report);
await generator.generate();
```
