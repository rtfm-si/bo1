/**
 * E2E tests for admin access control.
 *
 * Tests verify:
 * - Admin link visibility in header for admin user (E2E mode uses admin user)
 * - Admin user can access admin pages
 * - Admin link in header navigates correctly
 *
 * Note: In E2E mode (PUBLIC_E2E_MODE=true):
 * - The auth store uses a mocked admin user
 * - The server-side layout guard is bypassed
 * - Individual page +page.server.ts files still make admin API calls
 *
 * Server-side route protection is verified via:
 * - Unit tests for the layout guard logic
 * - Production integration tests with real auth
 */
import { test, expect } from './fixtures';

const mockAdminUser = {
	id: 'admin-user-e2e',
	user_id: 'admin-user-e2e',
	email: 'admin@example.com',
	is_admin: true,
	subscription_tier: 'pro',
	auth_provider: 'google'
};

const mockAdminStats = {
	total_users: 100,
	total_meetings: 500,
	total_cost: 150.0,
	whitelist_count: 25,
	waitlist_pending: 5
};

const mockEmailStats = {
	total: 100,
	by_period: { today: 5, week: 20, month: 50 },
	by_type: { welcome: 30, meeting_complete: 40, action_reminder: 30 }
};

test.describe('Admin Access Control - Admin User', () => {
	test.beforeEach(async ({ page }) => {
		// Mock admin user for API calls
		await page.route('**/api/v1/auth/me', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAdminUser)
			})
		);

		// Mock admin stats endpoint
		await page.route('**/api/admin/stats', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAdminStats)
			})
		);

		// Mock email stats endpoint
		await page.route('**/api/admin/email/stats*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockEmailStats)
			})
		);

		// Catch-all for other admin endpoints
		await page.route('**/api/admin/**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ data: [], total: 0 })
			})
		);
	});

	test('admin link is visible in desktop header for admin user', async ({ page }) => {
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');

		// Desktop header admin link should be visible (E2E mode uses admin user)
		const adminLink = page.locator('header a[href="/admin"]');
		await expect(adminLink).toBeVisible();
		await expect(adminLink).toHaveText(/Admin/i);
	});

	test('admin user can access /admin page', async ({ page }) => {
		await page.goto('/admin');
		await page.waitForLoadState('networkidle');

		// Should stay on admin page (not redirected)
		await expect(page).toHaveURL(/\/admin/);

		// Should see admin dashboard heading
		const adminHeading = page.getByRole('heading', { name: /Admin Dashboard/i });
		await expect(adminHeading).toBeVisible();
	});

	test('admin link in header navigates to admin page', async ({ page }) => {
		await page.goto('/dashboard');
		await page.waitForLoadState('networkidle');

		// Click admin link
		const adminLink = page.locator('header a[href="/admin"]');
		await adminLink.click();

		// Should navigate to admin page
		await expect(page).toHaveURL('/admin');
	});

	test('admin can access /admin/users page', async ({ page }) => {
		// Mock users endpoint
		await page.route('**/api/admin/users*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ users: [], total: 0 })
			})
		);

		await page.goto('/admin/users');
		await page.waitForLoadState('networkidle');

		// Should stay on admin/users page
		await expect(page).toHaveURL(/\/admin\/users/);
	});

	test('admin can access /admin/costs page', async ({ page }) => {
		// Mock cost endpoints
		await page.route('**/api/admin/costs/**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ data: [], total: 0 })
			})
		);

		await page.goto('/admin/costs');
		await page.waitForLoadState('networkidle');

		// Should stay on admin/costs page
		await expect(page).toHaveURL(/\/admin\/costs/);
	});
});
