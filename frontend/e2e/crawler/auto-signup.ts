/**
 * Auto Signup Script - Creates account with email/password
 * Run with: npx tsx e2e/crawler/auto-signup.ts
 */

import { chromium } from 'playwright';
import * as fs from 'fs';

const BASE_URL = process.env.CRAWLER_BASE_URL || 'https://boardof.one';
const AUTH_STATE_FILE = './e2e/crawler/.auth-state.json';
const EMAIL = 'crawler@boardof.one';
const PASSWORD = 'Crawler12345';  // 12+ chars with letters and numbers

async function main() {
	console.log('\n=================================================');
	console.log('AUTO SIGNUP - Creating account');
	console.log('=================================================');
	console.log(`Target: ${BASE_URL}`);
	console.log(`Email: ${EMAIL}`);
	console.log('=================================================\n');

	const browser = await chromium.launch({
		headless: process.env.HEADLESS !== 'false',
		slowMo: process.env.HEADLESS !== 'false' ? 0 : 100,
	});

	const context = await browser.newContext();
	const page = await context.newPage();

	// Listen for console messages
	page.on('console', msg => {
		if (msg.type() === 'error' || msg.text().toLowerCase().includes('auth')) {
			console.log(`   [Console ${msg.type()}]: ${msg.text()}`);
		}
	});

	try {
		// Go to login page
		console.log('1. Navigating to login page...');
		await page.goto(`${BASE_URL}/login`);
		await page.waitForLoadState('networkidle');

		// Handle cookie consent if present
		const cookieButton = page.getByRole('button', { name: /Accept All|Essential Only/i });
		if (await cookieButton.isVisible({ timeout: 2000 }).catch(() => false)) {
			console.log('   Accepting cookies...');
			await cookieButton.first().click();
			await page.waitForTimeout(500);
		}

		// Check GDPR consent checkbox
		console.log('2. Accepting privacy policy...');
		const checkbox = page.locator('input[type="checkbox"]').first();
		if (!await checkbox.isChecked()) {
			await checkbox.check();
		}

		// Stay on Sign In mode
		console.log('3. Staying on Sign In mode...');
		await page.waitForTimeout(500);

		// Fill email
		console.log('4. Filling email...');
		await page.locator('input#email').fill(EMAIL);

		// Fill password
		console.log('5. Filling password...');
		await page.locator('input#password').fill(PASSWORD);

		// Click Sign In button
		console.log('6. Clicking Sign In...');
		await page.locator('button[type="submit"]').click();

		// Wait a bit for the request to process
		await page.waitForTimeout(3000);

		// Check current URL
		console.log('   Current URL:', page.url());

		// Wait for navigation to dashboard
		console.log('7. Waiting for dashboard...');

		try {
			// Wait for either dashboard or any navigation
			await Promise.race([
				page.waitForURL('**/dashboard', { timeout: 30000 }),
				page.waitForURL('**/meeting/**', { timeout: 30000 }),
			]);
			console.log('\n✓ Signed in successfully!');
			console.log('   Final URL:', page.url());
		} catch {
			// Check current URL and page state
			console.log('   URL after timeout:', page.url());

			const pageContent = await page.content();
			if (pageContent.includes('Invalid email or password')) {
				console.log('\n✗ Invalid password');
				throw new Error('Invalid password');
			} else if (pageContent.includes('not whitelisted') || pageContent.includes('closed beta')) {
				console.log('\n✗ Account not whitelisted');
				throw new Error('Not whitelisted');
			} else if (page.url().includes('/dashboard') || page.url().includes('/meeting')) {
				console.log('\n✓ Already on dashboard/meeting!');
			} else {
				// Take screenshot
				await page.screenshot({ path: 'e2e/crawler/signin-error.png' });
				console.log('\n✗ Unknown error. Screenshot saved.');
				throw new Error('Signin failed');
			}
		}

		// Save auth state
		console.log('\n8. Saving auth state...');
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

	} catch (error) {
		console.error('\n✗ Failed:', error);

		// Take screenshot on error
		await page.screenshot({ path: 'e2e/crawler/signin-error.png' });
		console.log('Screenshot saved to e2e/crawler/signin-error.png');
	} finally {
		await browser.close();
	}
}

main().catch(console.error);
