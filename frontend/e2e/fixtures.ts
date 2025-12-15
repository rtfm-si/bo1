/**
 * Custom Playwright test fixtures for Bo1 E2E tests.
 * Extends base test to handle common setup like cookie consent.
 */
import { test as base } from '@playwright/test';

/**
 * Extended test fixture that dismisses GDPR cookie consent banner
 * before each test by setting the consent cookie.
 */
export const test = base.extend({
	page: async ({ page }, use) => {
		// Set cookie consent before navigating to any page
		// This prevents the GDPR banner from appearing and conflicting with selectors
		await page.context().addCookies([
			{
				name: 'bo1_cookie_consent',
				value: JSON.stringify({
					essential: true,
					analytics: true,
					timestamp: new Date().toISOString()
				}),
				domain: 'localhost',
				path: '/',
				expires: Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60, // 1 year
				httpOnly: false,
				secure: false,
				sameSite: 'Lax'
			}
		]);

		await use(page);
	}
});

export { expect } from '@playwright/test';
