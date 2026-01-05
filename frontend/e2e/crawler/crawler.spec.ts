/**
 * Comprehensive Website Crawler Test
 *
 * Self-discovers routes and tests all interactive elements.
 * Generates a detailed report of all issues found.
 *
 * Usage:
 *   # Default: test boardof.one without running new meetings
 *   npx playwright test e2e/crawler/crawler.spec.ts
 *
 *   # With new meeting test
 *   RUN_NEW_MEETING=true npx playwright test e2e/crawler/crawler.spec.ts
 *
 *   # Local development
 *   E2E_BASE_URL=http://localhost:5173 npx playwright test e2e/crawler/crawler.spec.ts
 *
 *   # Verbose output
 *   CRAWLER_VERBOSE=true npx playwright test e2e/crawler/crawler.spec.ts
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import { WebsiteCrawler } from './crawler';
import { ReportGenerator } from './report-generator';
import type { CrawlConfig } from './types';

// Configuration from environment
const BASE_URL = process.env.CRAWLER_BASE_URL || process.env.E2E_BASE_URL || 'https://boardof.one';
const RUN_NEW_MEETING = process.env.RUN_NEW_MEETING === 'true';
const VERBOSE = process.env.CRAWLER_VERBOSE === 'true';
const MAX_PAGES = parseInt(process.env.CRAWLER_MAX_PAGES || '100', 10);
const MAX_DEPTH = parseInt(process.env.CRAWLER_MAX_DEPTH || '5', 10);

// Test user credentials
const TEST_USER_EMAIL = process.env.CRAWLER_USER_EMAIL || 'e2e.test@boardof.one';
const TEST_USER_PASSWORD = process.env.CRAWLER_USER_PASSWORD;

// Auth state file (can be pre-saved from a manual login)
const AUTH_STATE_FILE = process.env.CRAWLER_AUTH_STATE || './e2e/crawler/.auth-state.json';

// Skip in CI unless explicitly enabled - crawler requires production auth
const SKIP_IN_CI = process.env.CI === 'true' && process.env.RUN_CRAWLER !== 'true';

test.describe('Website Crawler', () => {
	test.skip(SKIP_IN_CI, 'Crawler tests require manual auth setup - run locally with ./run-crawl.sh');
	test.setTimeout(600000); // 10 minute timeout for full crawl

	test('comprehensive crawl of all pages and interactions', async ({ page, context }) => {
		console.log(`\nStarting comprehensive crawl of ${BASE_URL}`);
		console.log(`Run new meeting: ${RUN_NEW_MEETING}`);
		console.log(`Max pages: ${MAX_PAGES}, Max depth: ${MAX_DEPTH}`);

		// Authenticate (already navigates to dashboard and verifies login)
		await authenticate(page, context);
		console.log('Successfully authenticated');

		// Configure crawler
		const config: Partial<CrawlConfig> = {
			baseUrl: BASE_URL,
			maxPages: MAX_PAGES,
			maxDepth: MAX_DEPTH,
			runNewMeeting: RUN_NEW_MEETING,
			verbose: VERBOSE,
			timeout: 30000,
			screenshotOnError: true,
			skipPatterns: [
				/^mailto:/,
				/^tel:/,
				/^javascript:/,
				/\.(pdf|zip|doc|docx|xls|xlsx)$/i,
				/logout/i,
				/signout/i,
				/^#$/,
				/^#[a-zA-Z]/,
				// Skip external links
				/^https?:\/\/(?!boardof\.one)/,
				// Skip admin if not admin user
				/\/admin/,
				// Skip auth callback routes
				/\/auth\//
			]
		};

		// Add meeting skip patterns if not running new meetings
		if (!RUN_NEW_MEETING) {
			config.skipPatterns!.push(
				/\/meetings\/new/,
				/\/meeting\/new/
			);
		}

		// Run crawler
		const crawler = new WebsiteCrawler(page, context, config);
		const report = await crawler.crawl();

		// Generate report
		const generator = new ReportGenerator(report);
		const reportPath = await generator.generate();

		console.log(`\nReport saved to: ${reportPath}`);

		// Assert no critical issues
		const criticalCount = report.summary.issuesBySeverity.critical || 0;
		const errorCount = report.summary.issuesBySeverity.error || 0;

		// Log summary
		console.log('\n--- CRAWL COMPLETE ---');
		console.log(`Pages: ${report.summary.totalPages}`);
		console.log(`Elements: ${report.summary.totalElements}`);
		console.log(`Interactions: ${report.summary.totalInteractions}`);
		console.log(`Critical: ${criticalCount}, Errors: ${errorCount}`);

		// The test passes but records all issues
		// We don't fail on issues because this is a discovery tool
		expect(report.summary.totalPages).toBeGreaterThan(0);
	});

	test('quick smoke test - dashboard only', async ({ page, context }) => {
		test.setTimeout(120000); // 2 minute timeout

		await authenticate(page, context);

		const config: Partial<CrawlConfig> = {
			baseUrl: BASE_URL,
			maxPages: 5,
			maxDepth: 1,
			runNewMeeting: false,
			verbose: true,
			includePatterns: [
				/\/dashboard/,
				/\/$/
			]
		};

		const crawler = new WebsiteCrawler(page, context, config);
		const report = await crawler.crawl();

		const generator = new ReportGenerator(report, './e2e/crawler/reports/smoke');
		await generator.generate();

		expect(report.summary.totalPages).toBeGreaterThan(0);
	});

	test('crawl meetings pages', async ({ page, context }) => {
		test.setTimeout(300000); // 5 minute timeout

		await authenticate(page, context);

		const config: Partial<CrawlConfig> = {
			baseUrl: BASE_URL,
			maxPages: 30,
			maxDepth: 3,
			runNewMeeting: RUN_NEW_MEETING,
			verbose: VERBOSE,
			includePatterns: [
				/\/meetings/,
				/\/meeting\//,
				/\/dashboard/
			]
		};

		const crawler = new WebsiteCrawler(page, context, config);
		const report = await crawler.crawl();

		const generator = new ReportGenerator(report, './e2e/crawler/reports/meetings');
		await generator.generate();

		expect(report.summary.totalPages).toBeGreaterThan(0);
	});

	test('crawl actions pages', async ({ page, context }) => {
		test.setTimeout(180000); // 3 minute timeout

		await authenticate(page, context);

		const config: Partial<CrawlConfig> = {
			baseUrl: BASE_URL,
			maxPages: 20,
			maxDepth: 2,
			runNewMeeting: false,
			verbose: VERBOSE,
			includePatterns: [
				/\/actions/,
				/\/dashboard/
			]
		};

		const crawler = new WebsiteCrawler(page, context, config);
		const report = await crawler.crawl();

		const generator = new ReportGenerator(report, './e2e/crawler/reports/actions');
		await generator.generate();

		expect(report.summary.totalPages).toBeGreaterThan(0);
	});

	test('crawl settings pages', async ({ page, context }) => {
		test.setTimeout(180000); // 3 minute timeout

		await authenticate(page, context);

		const config: Partial<CrawlConfig> = {
			baseUrl: BASE_URL,
			maxPages: 20,
			maxDepth: 2,
			runNewMeeting: false,
			verbose: VERBOSE,
			includePatterns: [
				/\/settings/,
				/\/dashboard/
			]
		};

		const crawler = new WebsiteCrawler(page, context, config);
		const report = await crawler.crawl();

		const generator = new ReportGenerator(report, './e2e/crawler/reports/settings');
		await generator.generate();

		expect(report.summary.totalPages).toBeGreaterThan(0);
	});

	test('crawl datasets pages', async ({ page, context }) => {
		test.setTimeout(180000); // 3 minute timeout

		await authenticate(page, context);

		const config: Partial<CrawlConfig> = {
			baseUrl: BASE_URL,
			maxPages: 20,
			maxDepth: 2,
			runNewMeeting: false,
			verbose: VERBOSE,
			includePatterns: [
				/\/datasets/,
				/\/dashboard/
			]
		};

		const crawler = new WebsiteCrawler(page, context, config);
		const report = await crawler.crawl();

		const generator = new ReportGenerator(report, './e2e/crawler/reports/datasets');
		await generator.generate();

		expect(report.summary.totalPages).toBeGreaterThan(0);
	});
});

/**
 * Authenticate with the site
 *
 * SuperTokens requires three things for authenticated state:
 * 1. sAccessToken cookie (JWT)
 * 2. sFrontToken cookie (base64 user info for frontend SDK)
 * 3. localStorage supertokens-auth state
 */
async function authenticate(page: Page, context: BrowserContext): Promise<void> {
	// Try to load stored auth state first
	try {
		const fs = await import('fs');
		if (fs.existsSync(AUTH_STATE_FILE)) {
			const state = JSON.parse(fs.readFileSync(AUTH_STATE_FILE, 'utf-8'));

			if (!state.cookies || state.cookies.length === 0) {
				throw new Error('No cookies in auth state file');
			}

			// Add all cookies from the file (should include sAccessToken, sRefreshToken, sFrontToken)
			await context.addCookies(state.cookies);
			console.log(`Added ${state.cookies.length} cookies from auth state file`);

			// Navigate to dashboard
			await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });

			// Wait for session verification to complete
			console.log('Waiting for session verification...');
			try {
				await page.waitForFunction(() => {
					const verifying = document.body?.textContent?.includes('Verifying your session');
					return !verifying;
				}, { timeout: 15000 });
			} catch {
				console.log('Session verification wait timed out');
			}

			// Additional wait for any redirects
			await page.waitForTimeout(2000);

			// Check final URL
			const finalUrl = page.url();
			if (finalUrl.includes('/login')) {
				console.log(`Auth failed - redirected to login. Final URL: ${finalUrl}`);
				throw new Error('Session verification failed - ended up on login page');
			}

			console.log(`Auth successful - on ${finalUrl}`);
			return;
		}
	} catch (e) {
		console.log('No stored auth state or error loading:', e);
	}

	// If no stored state, try to login via UI
	if (TEST_USER_PASSWORD) {
		await loginViaUI(page, TEST_USER_EMAIL, TEST_USER_PASSWORD);
		return;
	}

	// For production without stored creds, we need manual intervention
	// This will pause and wait for manual login
	console.log('\nNo auth credentials provided.');
	console.log('Options:');
	console.log('1. Set CRAWLER_USER_PASSWORD environment variable');
	console.log('2. Provide pre-saved auth state in', AUTH_STATE_FILE);
	console.log('3. Run: npx playwright test --headed to login manually\n');

	// In headed mode, give user chance to login manually
	if (process.env.HEADED || process.env.PWTEST_HEADED) {
		console.log('Navigating to login page for manual authentication...');
		await page.goto(`${BASE_URL}/login`);
		console.log('Please log in manually. Waiting 60 seconds...');
		await page.waitForURL('**/dashboard', { timeout: 60000 });
		console.log('Login detected, continuing...');

		// Save auth state for future runs
		const cookies = await context.cookies();
		const fs = await import('fs');
		fs.writeFileSync(AUTH_STATE_FILE, JSON.stringify({ cookies }, null, 2));
		console.log('Auth state saved to', AUTH_STATE_FILE);
	} else {
		throw new Error('No authentication method available. See options above.');
	}
}

/**
 * Login via the UI with email/password
 */
async function loginViaUI(page: Page, email: string, password: string): Promise<void> {
	console.log(`Logging in as ${email}...`);
	await page.goto(`${BASE_URL}/login`);

	// Handle OAuth or magic link flow
	// For OAuth, we may need to click the provider button
	const googleButton = page.getByRole('button', { name: /google|sign in/i });
	if (await googleButton.isVisible({ timeout: 3000 }).catch(() => false)) {
		// This is OAuth flow - we can't automate without stored session
		throw new Error('OAuth login detected. Please use stored auth state instead.');
	}

	// Check for email/password form
	const emailInput = page.getByLabel(/email/i);
	const passwordInput = page.getByLabel(/password/i);

	if (await emailInput.isVisible({ timeout: 3000 }).catch(() => false)) {
		await emailInput.fill(email);
		await passwordInput.fill(password);
		await page.getByRole('button', { name: /sign in|log in|submit/i }).click();
		await page.waitForURL('**/dashboard', { timeout: 30000 });
		console.log('Login successful');
	} else {
		throw new Error('Could not find login form');
	}
}

/**
 * Extract user ID from SuperTokens JWT
 * JWT format: header.payload.signature (all base64url encoded)
 */
function extractUserIdFromJWT(jwt: string): string | null {
	try {
		const parts = jwt.split('.');
		if (parts.length !== 3) return null;

		// Decode payload (second part)
		// Replace URL-safe chars and add padding
		const payload = parts[1]
			.replace(/-/g, '+')
			.replace(/_/g, '/');
		const padded = payload + '='.repeat((4 - payload.length % 4) % 4);

		const decoded = Buffer.from(padded, 'base64').toString('utf-8');
		const data = JSON.parse(decoded);

		// SuperTokens stores user ID in 'sub' claim
		return data.sub || null;
	} catch {
		return null;
	}
}
