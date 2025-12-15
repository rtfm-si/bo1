import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration for Bo1 frontend.
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
	testDir: './e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0, // 1 retry to reduce CI time
	workers: process.env.CI ? 4 : undefined, // More workers for parallelism
	timeout: 30000, // 30s per test max
	expect: {
		timeout: 10000 // 10s for expect assertions
	},
	reporter: process.env.CI
		? [['html', { open: 'never' }], ['github'], ['json', { outputFile: 'playwright-results.json' }]]
		: 'html',

	use: {
		baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		video: process.env.CI ? 'off' : 'on-first-retry', // Disable video in CI for speed
		navigationTimeout: 15000,
		actionTimeout: 10000
	},

	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		},
		{
			name: 'firefox',
			use: { ...devices['Desktop Firefox'] }
		}
	],

	// Run frontend dev server before tests (local only)
	webServer: process.env.CI
		? undefined
		: {
				command: 'npm run dev',
				url: 'http://localhost:5173',
				reuseExistingServer: true,
				timeout: 120000
			}
});
