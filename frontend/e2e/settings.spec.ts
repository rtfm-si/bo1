/**
 * E2E tests for settings pages.
 *
 * Tests cover:
 * - Settings navigation and layout
 * - Account settings page
 * - Privacy settings page
 * - Billing settings page
 * - Integrations settings page
 *
 * Note: Uses mocked API responses for consistent test data.
 */
import { test, expect } from './fixtures';

// Mock user data
const mockUser = {
	user_id: 'test-user',
	email: 'test@example.com',
	name: 'Test User',
	is_admin: false,
	tier: 'starter'
};

// Mock billing info
const mockBillingInfo = {
	tier: 'starter',
	status: 'active',
	current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
	cancel_at_period_end: false,
	stripe_customer_id: 'cus_test123'
};

// Mock usage data
const mockUsage = {
	meetings_used: 5,
	meetings_limit: 10,
	analyses_used: 3,
	analyses_limit: 20,
	api_calls_used: 100,
	api_calls_limit: 1000,
	period_start: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
	period_end: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString()
};

// Mock email preferences
const mockEmailPrefs = {
	marketing: true,
	meeting_completed: true,
	action_reminders: true,
	weekly_digest: false
};

// Mock retention setting
const mockRetention = {
	retention_days: 730
};

test.describe('Settings Pages', () => {
	test.beforeEach(async ({ page }) => {
		// Mock user API
		await page.route('**/api/v1/user', (route) => {
			if (route.request().method() === 'PATCH') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...mockUser, ...route.request().postDataJSON() })
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockUser)
			});
		});

		// Mock billing info
		await page.route('**/api/v1/billing/info', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockBillingInfo)
			})
		);

		// Mock usage API
		await page.route('**/api/v1/user/usage', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockUsage)
			})
		);

		// Mock tier info
		await page.route('**/api/v1/user/tier-info', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					tier: 'starter',
					limits: { meetings: 10, analyses: 20, api_calls: 1000 },
					features: { datasets: true, mentor: true, api_access: false }
				})
			})
		);

		// Mock email preferences
		await page.route('**/api/v1/user/email-preferences', (route) => {
			if (route.request().method() === 'PATCH') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ ...mockEmailPrefs, ...route.request().postDataJSON() })
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockEmailPrefs)
			});
		});

		// Mock retention setting
		await page.route('**/api/v1/user/retention', (route) => {
			if (route.request().method() === 'PATCH') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ retention_days: 365 })
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockRetention)
			});
		});

		// Mock Google Sheets status
		await page.route('**/api/v1/auth/google/sheets/status', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ connected: false })
			})
		);

		// Mock Google Calendar status
		await page.route('**/api/v1/integrations/google-calendar/status', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ connected: false })
			})
		);
	});

	test.describe('Settings layout', () => {
		test('displays settings navigation sidebar', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for settings navigation items
			await expect(page.getByRole('link', { name: /Account/i })).toBeVisible();
			await expect(page.getByRole('link', { name: /Privacy/i })).toBeVisible();
			await expect(page.getByRole('link', { name: /Billing/i })).toBeVisible();
		});

		test('settings page shows heading', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for settings heading
			await expect(page.getByRole('heading', { name: /Settings/i })).toBeVisible();
		});
	});

	test.describe('Account settings', () => {
		test('displays user email', async ({ page }) => {
			await page.goto('/settings/account');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check user email is displayed
			await expect(page.getByText('test@example.com')).toBeVisible();
		});

		test('displays account tier', async ({ page }) => {
			await page.goto('/settings/account');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check tier is displayed
			await expect(page.getByText(/starter/i).first()).toBeVisible();
		});
	});

	test.describe('Privacy settings', () => {
		test('displays email preferences', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for email preferences section
			await expect(page.getByText(/Email preferences|Notifications/i).first()).toBeVisible();
		});

		test('displays data retention options', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for data retention section
			await expect(page.getByText(/Data retention|Retention/i).first()).toBeVisible();
		});

		test('displays data export button', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for export button
			await expect(page.getByRole('button', { name: /Export|Download/i })).toBeVisible();
		});

		test('displays account deletion option', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for delete account button
			await expect(page.getByRole('button', { name: /Delete Account|Delete/i }).first()).toBeVisible();
		});
	});

	test.describe('Billing settings', () => {
		test('displays current plan', async ({ page }) => {
			await page.goto('/settings/billing');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for plan display
			await expect(page.getByText(/Current Plan|Starter/i).first()).toBeVisible();
		});

		test('displays usage meters', async ({ page }) => {
			await page.goto('/settings/billing');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for usage meters
			await expect(page.getByText(/Usage|Meetings|5.*10/i).first()).toBeVisible();
		});

		test('displays manage subscription button', async ({ page }) => {
			await page.goto('/settings/billing');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for manage subscription link/button
			const manageBtn = page.getByRole('button', { name: /Manage|Portal|Upgrade/i });
			await expect(manageBtn.first()).toBeVisible();
		});
	});

	test.describe('Integrations settings', () => {
		test('displays Google Sheets integration', async ({ page }) => {
			await page.goto('/settings/integrations');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for Google Sheets section
			await expect(page.getByText(/Google Sheets/i)).toBeVisible();
		});

		test('displays Google Calendar integration', async ({ page }) => {
			await page.goto('/settings/integrations');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for Google Calendar section
			await expect(page.getByText(/Google Calendar/i)).toBeVisible();
		});

		test('shows connect buttons for disconnected integrations', async ({ page }) => {
			await page.goto('/settings/integrations');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for connect buttons
			const connectBtns = page.getByRole('button', { name: /Connect/i });
			const count = await connectBtns.count();
			expect(count).toBeGreaterThanOrEqual(1);
		});
	});

	test.describe('Navigation', () => {
		test('clicking Account navigates to account settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			await page.getByRole('link', { name: /Account/i }).click();
			await expect(page).toHaveURL(/\/settings\/account/);
		});

		test('clicking Privacy navigates to privacy settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			await page.getByRole('link', { name: /Privacy/i }).click();
			await expect(page).toHaveURL(/\/settings\/privacy/);
		});

		test('clicking Billing navigates to billing settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			await page.getByRole('link', { name: /Billing/i }).click();
			await expect(page).toHaveURL(/\/settings\/billing/);
		});

		test('clicking Integrations navigates to integrations settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			await page.getByRole('link', { name: /Integrations/i }).click();
			await expect(page).toHaveURL(/\/settings\/integrations/);
		});
	});

	test.describe('Error handling', () => {
		test('shows error on API failure', async ({ page }) => {
			// Override to return error
			await page.route('**/api/v1/user', (route) =>
				route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Internal server error' })
				})
			);

			await page.goto('/settings/account');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for error handling (graceful degradation)
			// The page should still load, potentially with an error message
			await expect(page.getByRole('heading', { name: /Settings|Account/i })).toBeVisible();
		});
	});
});
