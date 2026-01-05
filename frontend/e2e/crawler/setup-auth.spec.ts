/**
 * Auth Setup Script
 *
 * Run this once to capture auth state for headless crawling.
 * Opens a browser for manual login, then saves the session.
 *
 * Usage:
 *   npx playwright test e2e/crawler/setup-auth.ts --headed
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.CRAWLER_BASE_URL || 'https://boardof.one';
const AUTH_STATE_FILE = './e2e/crawler/.auth-state.json';

test.describe('Auth Setup', () => {
	// Skip in CI - requires manual browser interaction
	test.skip(!!process.env.CI, 'Manual auth setup cannot run in CI');

	test('capture auth state via manual login', async ({ page, context }) => {
		test.setTimeout(300000); // 5 minutes for manual login

		console.log('\n=================================================');
		console.log('AUTH STATE CAPTURE');
		console.log('=================================================');
		console.log(`Target: ${BASE_URL}`);
		console.log('\nPlease log in to the application.');
		console.log('This script will save your session for future crawls.');
		console.log('=================================================\n');

		// Navigate to login
		await page.goto(`${BASE_URL}/login`);

		// Wait for user to complete login and reach dashboard
		console.log('Waiting for login to complete (navigate to dashboard)...');

		try {
			await page.waitForURL('**/dashboard', { timeout: 300000 });
		} catch {
			// Check if already on dashboard
			if (!page.url().includes('/dashboard')) {
				console.log('\nLogin timeout. Current URL:', page.url());
				console.log('Please ensure you complete the login process.');
				throw new Error('Login not completed within timeout');
			}
		}

		console.log('\nLogin successful!');

		// Save cookies
		const cookies = await context.cookies();

		// Save localStorage
		const localStorage = await page.evaluate(() => {
			const items: Record<string, string> = {};
			for (let i = 0; i < window.localStorage.length; i++) {
				const key = window.localStorage.key(i);
				if (key) {
					items[key] = window.localStorage.getItem(key) || '';
				}
			}
			return items;
		});

		// Save session storage
		const sessionStorage = await page.evaluate(() => {
			const items: Record<string, string> = {};
			for (let i = 0; i < window.sessionStorage.length; i++) {
				const key = window.sessionStorage.key(i);
				if (key) {
					items[key] = window.sessionStorage.getItem(key) || '';
				}
			}
			return items;
		});

		const authState = {
			cookies,
			localStorage,
			sessionStorage,
			capturedAt: new Date().toISOString(),
			baseUrl: BASE_URL
		};

		// Ensure directory exists
		const dir = path.dirname(AUTH_STATE_FILE);
		if (!fs.existsSync(dir)) {
			fs.mkdirSync(dir, { recursive: true });
		}

		fs.writeFileSync(AUTH_STATE_FILE, JSON.stringify(authState, null, 2));

		console.log('\n=================================================');
		console.log('AUTH STATE SAVED');
		console.log('=================================================');
		console.log(`File: ${AUTH_STATE_FILE}`);
		console.log(`Cookies: ${cookies.length}`);
		console.log(`LocalStorage items: ${Object.keys(localStorage).length}`);
		console.log('');
		console.log('You can now run the crawler without manual login:');
		console.log('  npx playwright test e2e/crawler/crawler.spec.ts');
		console.log('=================================================\n');

		expect(cookies.length).toBeGreaterThan(0);
	});
});
