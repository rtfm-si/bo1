/**
 * Manual Auth Script - Uses persistent browser context
 * Run with: npx tsx e2e/crawler/manual-auth.ts
 */

import { chromium } from 'playwright';
import * as fs from 'fs';
import * as readline from 'readline';

const BASE_URL = process.env.CRAWLER_BASE_URL || 'https://boardof.one';
const AUTH_STATE_FILE = './e2e/crawler/.auth-state.json';

async function waitForEnter(message: string): Promise<void> {
	const rl = readline.createInterface({
		input: process.stdin,
		output: process.stdout
	});
	return new Promise((resolve) => {
		rl.question(message, () => {
			rl.close();
			resolve();
		});
	});
}

async function main() {
	console.log('\n=================================================');
	console.log('MANUAL AUTH - Using persistent browser profile');
	console.log('=================================================');
	console.log(`Target: ${BASE_URL}`);
	console.log('\n1. Browser will open to login page');
	console.log('2. Log in with crawler@boardof.one via Google');
	console.log('3. Once you reach the dashboard, come back here');
	console.log('4. Press ENTER to save auth state');
	console.log('=================================================\n');

	// Use persistent context - more like a real browser
	const context = await chromium.launchPersistentContext('/tmp/playwright-user-data', {
		headless: false,
		slowMo: 50,
		args: [
			'--disable-blink-features=AutomationControlled',
			'--no-first-run',
			'--no-default-browser-check'
		]
	});

	const page = await context.newPage();
	await page.goto(`${BASE_URL}/login`);

	console.log('Browser opened. Complete the login, then press ENTER here...\n');

	await waitForEnter('Press ENTER after you have logged in and see the dashboard: ');

	const currentUrl = page.url();
	console.log(`\nCurrent URL: ${currentUrl}`);

	if (currentUrl.includes('/dashboard') || currentUrl.includes('/meeting')) {
		console.log('Login successful!');

		// Save cookies
		const cookies = await context.cookies();

		const authState = {
			cookies,
			capturedAt: new Date().toISOString(),
			baseUrl: BASE_URL
		};

		fs.writeFileSync(AUTH_STATE_FILE, JSON.stringify(authState, null, 2));

		console.log('\n=================================================');
		console.log('AUTH STATE SAVED');
		console.log('=================================================');
		console.log(`File: ${AUTH_STATE_FILE}`);
		console.log(`Cookies: ${cookies.length}`);
		console.log('\nYou can now run the crawler:');
		console.log('  npx playwright test e2e/crawler/crawler.spec.ts -g "comprehensive"');
		console.log('=================================================\n');
	} else {
		console.log('\nNot on dashboard yet. Current URL:', currentUrl);
		console.log('Please try again after completing login.');
	}

	await context.close();
}

main().catch(console.error);
