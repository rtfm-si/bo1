import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration for Bo1 frontend.
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
	testDir: './e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: process.env.CI ? [['html', { open: 'never' }], ['github']] : 'html',

	use: {
		baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		video: 'on-first-retry'
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
