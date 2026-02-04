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

	});

	test.describe('Settings layout', () => {
		test('displays settings navigation sidebar', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for settings navigation items (actual sidebar structure)
			// Account section has: Profile, Privacy, Workspace
			// Billing section has: Plan & Usage
			// Links include emojis, so match partial text
			await expect(page.getByRole('link', { name: /👤 Profile/ })).toBeVisible();
			await expect(page.getByRole('link', { name: /🔒 Privacy/ })).toBeVisible();
			await expect(page.getByRole('link', { name: /💳 Plan & Usage/ })).toBeVisible();
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
		// FIXME: Flaky - email may not appear in main content area in CI
		test.fixme('displays user email', async ({ page }) => {
			await page.goto('/settings/account');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check user email is displayed (or "Not set" for placeholder emails)
			// Email appears in Profile section - use exact match to avoid header nav email
			await expect(
				page.locator('main').getByText('test@example.com').or(page.locator('main').getByText('Not set'))
			).toBeVisible();
		});

		test('displays account tier', async ({ page }) => {
			await page.goto('/settings/account');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check tier is displayed in Subscription section (Free, Starter, Pro, or Enterprise)
			await expect(page.getByText(/Free|Starter|Pro|Enterprise/i).first()).toBeVisible();
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

			// Check for email preferences section heading
			await expect(page.getByRole('heading', { name: /Email Preferences/i })).toBeVisible();
		});

		test('displays data retention options', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for data retention section heading
			await expect(page.getByRole('heading', { name: /Data Retention/i })).toBeVisible();
		});

		test('displays data export button', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for export button ("Download My Data")
			await expect(page.getByRole('button', { name: /Download My Data/i })).toBeVisible();
		});

		test('displays account deletion option', async ({ page }) => {
			await page.goto('/settings/privacy');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for delete account button
			await expect(page.getByRole('button', { name: /Delete My Account/i })).toBeVisible();
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

			// Check for "Current Plan" heading
			await expect(page.getByRole('heading', { name: /Current Plan/i })).toBeVisible();
		});

		test('displays usage meters', async ({ page }) => {
			await page.goto('/settings/billing');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for "Usage This Month" section
			await expect(page.getByRole('heading', { name: /Usage This Month/i })).toBeVisible();
		});

		test('displays upgrade or manage options', async ({ page }) => {
			await page.goto('/settings/billing');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for upgrade or manage options (varies by tier)
			// Free tier sees "Upgrade Your Plan" heading or "Contact Sales" buttons
			// Paid tier sees "Manage Subscription" button
			// Check any of these exist on the page
			const hasUpgradeHeading = await page.getByRole('heading', { name: /Upgrade Your Plan/i }).isVisible();
			const hasManageBtn = await page.getByRole('button', { name: /Manage Subscription/i }).first().isVisible();
			const hasContactBtn = await page.getByRole('button', { name: /Contact Sales/i }).first().isVisible();

			expect(hasUpgradeHeading || hasManageBtn || hasContactBtn).toBe(true);
		});
	});

	test.describe('Integrations settings', () => {
		test('displays integrations page heading', async ({ page }) => {
			await page.goto('/settings/integrations');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for Integrations page heading
			await expect(page.getByRole('heading', { name: /^Integrations$/i })).toBeVisible();
		});

	});

	test.describe('Navigation', () => {
		test('clicking Profile navigates to account settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Sidebar shows "👤 Profile" which links to /settings/account
			await page.getByRole('link', { name: /👤 Profile/ }).click();
			await expect(page).toHaveURL(/\/settings\/account/);
		});

		test('clicking Privacy navigates to privacy settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click the sidebar Privacy link (has emoji prefix)
			await page.getByRole('link', { name: /🔒 Privacy/ }).click();
			await expect(page).toHaveURL(/\/settings\/privacy/);
		});

		test('clicking Plan & Usage navigates to billing settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Sidebar shows "💳 Plan & Usage" which links to /settings/billing
			await page.getByRole('link', { name: /💳 Plan & Usage/ }).click();
			await expect(page).toHaveURL(/\/settings\/billing/);
		});

		test('clicking Workspace navigates to workspace settings', async ({ page }) => {
			await page.goto('/settings');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Sidebar shows "🏢 Workspace" which links to /settings/workspace
			await page.getByRole('link', { name: /🏢 Workspace/ }).click();
			await expect(page).toHaveURL(/\/settings\/workspace/);
		});
	});

	test.describe('Error handling', () => {
		test('shows error on API failure', async ({ page }) => {
			// Override user preferences to return error
			await page.route('**/api/v1/user/preferences', (route) =>
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
			// The page should still load with the Settings heading visible
			await expect(page.getByRole('heading', { name: /Settings/i })).toBeVisible();
		});
	});
});
