/**
 * E2E tests for authentication flows.
 *
 * Tests cover:
 * - Login page renders correctly
 * - Unauthenticated access redirects to login
 * - Logout clears session and redirects
 *
 * Note: Full OAuth flow testing requires mock OAuth provider.
 * These tests verify the UI behavior, not the OAuth integration.
 */
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
	test.describe('Login page', () => {
		test('displays login form with Google button', async ({ page }) => {
			await page.goto('/login');

			// Check page title
			await expect(page).toHaveTitle(/Sign In/);

			// Check heading
			await expect(page.getByRole('heading', { name: 'Sign in to continue' })).toBeVisible();

			// Check Google sign-in button
			const googleButton = page.getByRole('button', { name: /Sign in with Google/i });
			await expect(googleButton).toBeVisible();
			await expect(googleButton).toBeEnabled();

			// Check disabled OAuth buttons (coming soon)
			await expect(page.getByRole('button', { name: /LinkedIn.*Coming Soon/i })).toBeVisible();
			await expect(page.getByRole('button', { name: /GitHub.*Coming Soon/i })).toBeVisible();
		});

		test('shows closed beta notice', async ({ page }) => {
			await page.goto('/login');

			// Check closed beta message
			await expect(page.getByText(/Closed Beta/)).toBeVisible();
			await expect(page.getByText(/Access is currently limited/)).toBeVisible();

			// Check waitlist link
			const waitlistLink = page.getByRole('link', { name: /Join the waitlist/i });
			await expect(waitlistLink).toBeVisible();
		});

		test('shows error message when auth fails', async ({ page }) => {
			await page.goto('/login?error=closed_beta');

			// Check error message displayed
			await expect(page.getByText(/Access limited to beta users/)).toBeVisible();
		});

		test('shows privacy policy and terms links', async ({ page }) => {
			await page.goto('/login');

			await expect(page.getByRole('link', { name: 'Terms of Service' })).toBeVisible();
			await expect(page.getByRole('link', { name: 'Privacy Policy' })).toBeVisible();
		});

		test('has back to home link', async ({ page }) => {
			await page.goto('/login');

			const backLink = page.getByRole('link', { name: /Back to home/i });
			await expect(backLink).toBeVisible();

			await backLink.click();
			await expect(page).toHaveURL('/');
		});
	});

	test.describe('Protected routes', () => {
		test('redirects unauthenticated user from dashboard to login', async ({ page }) => {
			// Clear any existing auth state
			await page.context().clearCookies();

			await page.goto('/dashboard');

			// Should redirect to login
			await expect(page).toHaveURL(/\/login/);
		});

		test('redirects unauthenticated user from settings to login', async ({ page }) => {
			await page.context().clearCookies();

			await page.goto('/settings');

			await expect(page).toHaveURL(/\/login/);
		});

		test('redirects unauthenticated user from meeting creation to login', async ({ page }) => {
			await page.context().clearCookies();

			await page.goto('/meeting/new');

			await expect(page).toHaveURL(/\/login/);
		});
	});

	test.describe('Waitlist', () => {
		test('waitlist page is accessible', async ({ page }) => {
			await page.goto('/waitlist');

			// Should not redirect to login
			await expect(page).not.toHaveURL(/\/login/);

			// Check waitlist form or content exists
			await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
		});
	});
});

test.describe('Logout', () => {
	// Note: These tests require auth fixture for authenticated state
	// Skip for now since full auth flow needs OAuth mocking

	test.skip('logout button clears session', async ({ page }) => {
		// This test would:
		// 1. Start with authenticated state
		// 2. Click logout button
		// 3. Verify redirect to login
		// 4. Verify session cookies cleared
		// 5. Verify protected routes no longer accessible
	});
});
