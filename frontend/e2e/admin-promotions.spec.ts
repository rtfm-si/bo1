/**
 * E2E tests for admin promotions management flow.
 *
 * Tests cover:
 * - Promotions list page with filtering
 * - Add promotion modal and form validation
 * - Delete (deactivate) promotion flow
 * - Empty state handling
 *
 * Note: Uses mocked API responses for consistent test data.
 */
import { test, expect } from '@playwright/test';

// Mock promotions data - matches Promotion interface
const mockPromotions = [
	{
		id: 'promo-1',
		code: 'WELCOME10',
		type: 'goodwill_credits',
		value: 10,
		max_uses: 100,
		uses_count: 25,
		expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days from now
		created_at: new Date().toISOString(),
		is_active: true
	},
	{
		id: 'promo-2',
		code: 'SUMMER50',
		type: 'percentage_discount',
		value: 50,
		max_uses: 50,
		uses_count: 50,
		expires_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago (expired)
		created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
		is_active: true
	},
	{
		id: 'promo-3',
		code: 'INACTIVE_CODE',
		type: 'flat_discount',
		value: 5.0,
		max_uses: null,
		uses_count: 10,
		expires_at: null,
		created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
		is_active: false
	},
	{
		id: 'promo-4',
		code: 'UNLIMITED',
		type: 'extra_deliberations',
		value: 3,
		max_uses: null,
		uses_count: 15,
		expires_at: null,
		created_at: new Date().toISOString(),
		is_active: true
	}
];

// New promotion to be created in tests
const newPromotion = {
	id: 'promo-new',
	code: 'TESTPROMO',
	type: 'goodwill_credits',
	value: 5,
	max_uses: 10,
	uses_count: 0,
	expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
	created_at: new Date().toISOString(),
	is_active: true
};

test.describe('Admin Promotions Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock admin promotions list API
		await page.route('**/api/admin/promotions', (route) => {
			if (route.request().method() === 'GET') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockPromotions)
				});
			}
			// POST for creating new promotion
			if (route.request().method() === 'POST') {
				return route.fulfill({
					status: 201,
					contentType: 'application/json',
					body: JSON.stringify(newPromotion)
				});
			}
			return route.continue();
		});

		// Mock delete promotion API
		await page.route('**/api/admin/promotions/*', (route) => {
			if (route.request().method() === 'DELETE') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ status: 'deactivated', promotion_id: 'promo-1' })
				});
			}
			return route.continue();
		});

		// Mock admin user check (user must be admin to access this page)
		await page.route('**/api/v1/user', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					user_id: 'admin-user',
					email: 'admin@example.com',
					is_admin: true,
					tier: 'pro'
				})
			})
		);
	});

	test.describe('List view', () => {
		test('page loads with promotions list', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check page title
			await expect(page.getByRole('heading', { name: /Promotions/i }).first()).toBeVisible();

			// Check Add Promotion button exists
			await expect(page.getByRole('button', { name: /Add Promotion/i })).toBeVisible();

			// Check promotions are displayed
			await expect(page.getByText('WELCOME10')).toBeVisible();
			await expect(page.getByText('SUMMER50')).toBeVisible();
			await expect(page.getByText('UNLIMITED')).toBeVisible();
		});

		test('displays promotion card with code, type, and status', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check WELCOME10 card details
			await expect(page.getByText('WELCOME10')).toBeVisible();
			await expect(page.getByText('Goodwill Credits').first()).toBeVisible();

			// Check status badges exist
			const activeBadge = page.locator('span').filter({ hasText: 'Active' });
			await expect(activeBadge.first()).toBeVisible();
		});

		test('shows usage progress for promotions with max_uses', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// WELCOME10 has max_uses=100, uses_count=25 (25%)
			// Check that usage text shows
			await expect(page.getByText('25 / 100')).toBeVisible();
		});

		test('refresh button reloads data', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find and click refresh button
			const refreshButton = page.getByRole('button', { name: /Refresh/i });
			await expect(refreshButton).toBeVisible();
			await refreshButton.click();

			// Wait for reload
			await page.waitForLoadState('networkidle');

			// Data should still be visible
			await expect(page.getByText('WELCOME10')).toBeVisible();
		});
	});

	test.describe('Filter tabs', () => {
		test('filter tabs are visible', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check filter tabs exist
			await expect(page.getByRole('button', { name: /All/i })).toBeVisible();
			await expect(page.getByRole('button', { name: /Active/i })).toBeVisible();
			await expect(page.getByRole('button', { name: /Expired/i })).toBeVisible();
		});

		test('clicking Active tab filters to active promotions only', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click Active filter
			await page.getByRole('button', { name: /Active/i }).click();
			await page.waitForTimeout(300);

			// WELCOME10 and UNLIMITED should be visible (active, not expired)
			await expect(page.getByText('WELCOME10')).toBeVisible();
			await expect(page.getByText('UNLIMITED')).toBeVisible();

			// INACTIVE_CODE should NOT be visible
			await expect(page.getByText('INACTIVE_CODE')).not.toBeVisible();
		});

		test('clicking Expired tab shows expired/inactive promotions', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click Expired filter
			await page.getByRole('button', { name: /Expired/i }).click();
			await page.waitForTimeout(300);

			// SUMMER50 (expired) and INACTIVE_CODE should be visible
			await expect(page.getByText('SUMMER50')).toBeVisible();
			await expect(page.getByText('INACTIVE_CODE')).toBeVisible();

			// WELCOME10 should NOT be visible
			await expect(page.getByText('WELCOME10')).not.toBeVisible();
		});

		test('clicking All tab shows all promotions', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// First filter to Active
			await page.getByRole('button', { name: /Active/i }).click();
			await page.waitForTimeout(300);

			// Then click All
			await page.getByRole('button', { name: /All/i }).click();
			await page.waitForTimeout(300);

			// All promotions should be visible
			await expect(page.getByText('WELCOME10')).toBeVisible();
			await expect(page.getByText('SUMMER50')).toBeVisible();
			await expect(page.getByText('INACTIVE_CODE')).toBeVisible();
			await expect(page.getByText('UNLIMITED')).toBeVisible();
		});
	});

	test.describe('Create promotion flow', () => {
		test('Add Promotion button opens modal', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click Add Promotion
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Modal should be visible
			await expect(page.getByRole('dialog')).toBeVisible();
			await expect(page.getByRole('heading', { name: /Create Promotion/i })).toBeVisible();
		});

		test('modal shows all form fields', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Check form fields
			await expect(page.getByLabel(/Promo Code/i)).toBeVisible();
			await expect(page.getByLabel(/Type/i)).toBeVisible();
			await expect(page.getByLabel(/Value/i)).toBeVisible();
			await expect(page.getByLabel(/Max Uses/i)).toBeVisible();
			await expect(page.getByLabel(/Expires At/i)).toBeVisible();

			// Check action buttons
			await expect(page.getByRole('button', { name: /Cancel/i })).toBeVisible();
			await expect(page.getByRole('button', { name: /Create Promotion/i })).toBeVisible();
		});

		test('submitting valid form creates promotion', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Fill form
			await page.getByLabel(/Promo Code/i).fill('TESTPROMO');
			await page.getByLabel(/Value/i).fill('5');
			await page.getByLabel(/Max Uses/i).fill('10');

			// Submit form
			await page.getByRole('button', { name: /Create Promotion/i }).click();

			// Modal should close and new promo should appear
			await page.waitForTimeout(500);
			await expect(page.getByRole('dialog')).not.toBeVisible();
			await expect(page.getByText('TESTPROMO')).toBeVisible();
		});

		test('cancel button closes modal', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Fill some data
			await page.getByLabel(/Promo Code/i).fill('TEST');

			// Click cancel
			await page.getByRole('button', { name: /Cancel/i }).click();

			// Modal should close
			await expect(page.getByRole('dialog')).not.toBeVisible();
		});

		test('clicking backdrop closes modal', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Click backdrop (outside modal content)
			await page.locator('[role="presentation"]').click({ position: { x: 10, y: 10 } });

			// Modal should close
			await expect(page.getByRole('dialog')).not.toBeVisible();
		});
	});

	test.describe('Form validation', () => {
		test('shows error for empty code', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Clear code field and submit
			await page.getByLabel(/Promo Code/i).fill('');
			await page.getByLabel(/Value/i).fill('5');
			await page.getByRole('button', { name: /Create Promotion/i }).click();

			// Error should show
			await expect(page.getByText(/Code is required/i)).toBeVisible();
		});

		test('shows error for invalid code format', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			// Enter invalid code with spaces/lowercase
			await page.getByLabel(/Promo Code/i).fill('test code');
			await page.getByLabel(/Value/i).fill('5');
			await page.getByRole('button', { name: /Create Promotion/i }).click();

			// Error should show (code gets uppercased but spaces are invalid)
			await expect(page.getByText(/must be uppercase letters/i)).toBeVisible();
		});

		test('shows error for zero or negative value', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			await page.getByLabel(/Promo Code/i).fill('TESTCODE');
			await page.getByLabel(/Value/i).fill('0');
			await page.getByRole('button', { name: /Create Promotion/i }).click();

			// Error should show
			await expect(page.getByText(/Value must be greater than 0/i)).toBeVisible();
		});

		test('shows error for percentage over 100', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.getByRole('button', { name: /Add Promotion/i }).click();

			await page.getByLabel(/Promo Code/i).fill('TESTCODE');
			await page.getByLabel(/Type/i).selectOption('percentage_discount');
			await page.getByLabel(/Value/i).fill('150');
			await page.getByRole('button', { name: /Create Promotion/i }).click();

			// Error should show
			await expect(page.getByText(/Percentage cannot exceed 100/i)).toBeVisible();
		});
	});

	test.describe('Delete promotion flow', () => {
		test('deactivate button shows confirmation dialog', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find deactivate button on WELCOME10 card
			const promoCard = page.locator('div').filter({ hasText: 'WELCOME10' }).first();
			const deactivateBtn = promoCard.getByRole('button', { name: /Deactivate/i });

			if (await deactivateBtn.isVisible()) {
				await deactivateBtn.click();

				// Confirmation dialog should appear
				await expect(page.getByText(/Are you sure you want to deactivate/i)).toBeVisible();
				await expect(page.getByText('WELCOME10')).toBeVisible();
			}
		});

		test('confirming deletion deactivates promotion', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click deactivate on first active promo
			const deactivateBtn = page.getByRole('button', { name: /Deactivate/i }).first();
			await deactivateBtn.click();

			// Click confirm in dialog
			await page.getByRole('button', { name: /^Deactivate$/i }).click();

			// Dialog should close
			await page.waitForTimeout(500);
			await expect(page.getByText(/Are you sure/i)).not.toBeVisible();
		});

		test('cancel button dismisses deletion dialog', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click deactivate
			const deactivateBtn = page.getByRole('button', { name: /Deactivate/i }).first();
			await deactivateBtn.click();

			// Click cancel
			await page.getByRole('button', { name: /Cancel/i }).click();

			// Dialog should close
			await expect(page.getByText(/Are you sure/i)).not.toBeVisible();
		});
	});

	test.describe('Empty state', () => {
		test('shows empty state when no promotions', async ({ page }) => {
			// Override route to return empty list
			await page.route('**/api/admin/promotions', (route) => {
				if (route.request().method() === 'GET') {
					return route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify([])
					});
				}
				return route.continue();
			});

			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Empty state message
			await expect(page.getByText(/No promotions yet/i)).toBeVisible();
			await expect(page.getByText(/Create your first promotion/i)).toBeVisible();

			// Create button in empty state
			await expect(page.getByRole('button', { name: /Create Promotion/i })).toBeVisible();
		});

		test('empty state shows filter-specific message', async ({ page }) => {
			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// All promotions are either active or expired, so we need to mock differently
			// For this test, we'll just verify the filter changes empty state text
			// when filtering results in no matches

			// Mock with only active promos
			await page.route('**/api/admin/promotions', (route) => {
				if (route.request().method() === 'GET') {
					return route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify([mockPromotions[0], mockPromotions[3]]) // only active ones
					});
				}
				return route.continue();
			});

			// Reload page
			await page.reload();
			await page.waitForLoadState('networkidle');

			// Click Expired filter (should show empty since we only have active promos)
			await page.getByRole('button', { name: /Expired/i }).click();
			await page.waitForTimeout(300);

			// Should show filtered empty state
			await expect(page.getByText(/No expired/i)).toBeVisible();
		});
	});

	test.describe('Error handling', () => {
		test('shows error message on API failure', async ({ page }) => {
			// Override route to return error
			await page.route('**/api/admin/promotions', (route) => {
				if (route.request().method() === 'GET') {
					return route.fulfill({
						status: 500,
						contentType: 'application/json',
						body: JSON.stringify({ detail: 'Internal server error' })
					});
				}
				return route.continue();
			});

			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Error message should be visible
			await expect(page.getByText(/Failed to load|Internal server error/i)).toBeVisible();

			// Retry button should be available
			await expect(page.getByRole('button', { name: /Retry/i })).toBeVisible();
		});

		test('retry button reloads data after error', async ({ page }) => {
			let requestCount = 0;

			// First request fails, second succeeds
			await page.route('**/api/admin/promotions', (route) => {
				if (route.request().method() === 'GET') {
					requestCount++;
					if (requestCount === 1) {
						return route.fulfill({
							status: 500,
							contentType: 'application/json',
							body: JSON.stringify({ detail: 'Temporary error' })
						});
					}
					return route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify(mockPromotions)
					});
				}
				return route.continue();
			});

			await page.goto('/admin/promotions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Error should be visible
			await expect(page.getByText(/Failed to load|Temporary error/i)).toBeVisible();

			// Click retry
			await page.getByRole('button', { name: /Retry/i }).click();
			await page.waitForLoadState('networkidle');

			// Data should now be visible
			await expect(page.getByText('WELCOME10')).toBeVisible();
		});
	});
});
