/**
 * Auth fixtures for E2E tests.
 *
 * When backend runs with DEBUG=true and ENABLE_SUPERTOKENS_AUTH=false,
 * all authenticated requests are allowed with a default test_user_1.
 *
 * For SuperTokens-enabled environments, these fixtures create auth state
 * via direct API calls, avoiding OAuth browser flows.
 */
import { test as base, expect, type Page, type APIRequestContext } from '@playwright/test';

const API_BASE_URL = process.env.E2E_API_URL || 'http://localhost:8000';

export interface TestUser {
	id: string;
	email: string;
}

export interface AuthFixtures {
	authenticatedPage: Page;
	testUser: TestUser;
	apiContext: APIRequestContext;
}

/**
 * Extended test fixture with authenticated page.
 *
 * In debug mode, the API accepts requests without auth.
 * The frontend needs to have session state set for protected routes.
 */
export const test = base.extend<AuthFixtures>({
	testUser: async ({}, use) => {
		// Default test user when running against debug backend
		const user: TestUser = {
			id: 'test_user_1',
			email: 'test_user_1@test.com'
		};
		await use(user);
	},

	apiContext: async ({ playwright }, use) => {
		const context = await playwright.request.newContext({
			baseURL: API_BASE_URL
		});
		await use(context);
		await context.dispose();
	},

	authenticatedPage: async ({ page, context }, use) => {
		// Set up mock auth state for the frontend
		// The frontend checks localStorage/cookies for auth state
		await page.goto('/');

		// Set auth cookie that frontend expects (mimics SuperTokens session)
		await context.addCookies([
			{
				name: 'sAccessToken',
				value: 'e2e_test_token',
				domain: 'localhost',
				path: '/'
			},
			{
				name: 'sFrontToken',
				value: btoa(JSON.stringify({ uid: 'test_user_1', up: {} })),
				domain: 'localhost',
				path: '/'
			}
		]);

		// Set localStorage auth state
		await page.evaluate(() => {
			localStorage.setItem(
				'supertokens-auth',
				JSON.stringify({
					userId: 'test_user_1',
					authenticated: true
				})
			);
		});

		await use(page);
	}
});

export { expect };

/**
 * Login helper for tests that need to go through the login flow.
 * Note: Full OAuth flow cannot be tested without mocking the OAuth provider.
 */
export async function loginViaUI(page: Page): Promise<void> {
	await page.goto('/login');

	// In a real test with mock OAuth, we would:
	// 1. Click the Google sign-in button
	// 2. Have a mock OAuth server that returns a valid token
	// 3. Complete the callback flow

	// For now, this is a placeholder for when OAuth mocking is set up
	throw new Error(
		'loginViaUI requires OAuth mocking. Use authenticatedPage fixture for debug mode.'
	);
}

/**
 * Logout helper.
 */
export async function logout(page: Page): Promise<void> {
	// Click logout in header dropdown or settings
	const logoutButton = page.getByRole('button', { name: /logout|sign out/i });
	if (await logoutButton.isVisible()) {
		await logoutButton.click();
		await page.waitForURL('/login');
	} else {
		// Navigate to settings and logout
		await page.goto('/settings');
		await page.getByRole('button', { name: /logout|sign out/i }).click();
		await page.waitForURL('/login');
	}
}

/**
 * Check if user is authenticated by verifying redirect behavior.
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
	// Try to access a protected route
	await page.goto('/dashboard');
	const url = new URL(page.url());
	return !url.pathname.includes('/login');
}
