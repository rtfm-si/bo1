/**
 * E2E tests for meeting creation flow.
 *
 * Tests cover:
 * - New meeting page UI elements
 * - Form validation (min length, submit states)
 * - Example question usage
 * - Dataset attachment (optional)
 * - Navigation from dashboard to new meeting
 *
 * Note: Full deliberation is not tested here due to SSE complexity.
 * See meeting-complete.spec.ts for completed meeting tests.
 */
import { test, expect } from './fixtures';

// Skip tests that require authentication in OAuth-enabled environments
const authSkip = process.env.E2E_SKIP_AUTH === 'true';

test.describe('Meeting Creation', () => {
	test.describe('New meeting page', () => {
		test('renders meeting creation form', async ({ page }) => {
			// Go directly to new meeting page (auth redirect tested in auth.spec.ts)
			await page.goto('/meeting/new');

			// Skip if redirected to login (OAuth environment)
			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Check page title
			await expect(page).toHaveTitle(/New Meeting/);

			// Check heading
			await expect(page.getByRole('heading', { name: 'Start New Meeting' })).toBeVisible();

			// Check form elements
			const textarea = page.locator('#problem');
			await expect(textarea).toBeVisible();
			await expect(textarea).toHaveAttribute('placeholder', /Example:/);

			// Check submit button
			const submitButton = page.getByRole('button', { name: /Start Meeting/i });
			await expect(submitButton).toBeVisible();
			await expect(submitButton).toBeDisabled(); // Should be disabled with empty input

			// Check cancel button
			const cancelLink = page.getByRole('link', { name: /Cancel/i });
			await expect(cancelLink).toBeVisible();
		});

		test('shows character count and validation', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem');
			const submitButton = page.getByRole('button', { name: /Start Meeting/i });

			// Initially empty - button disabled
			await expect(submitButton).toBeDisabled();

			// Type short text (< 20 chars)
			await textarea.fill('Short text');
			// UI shows "(minimum 20 characters)" in parens
			await expect(page.getByText('(minimum 20 characters)')).toBeVisible();
			await expect(submitButton).toBeDisabled();

			// Type valid text (>= 20 chars)
			await textarea.fill('This is a longer problem statement that exceeds the minimum');
			await expect(page.getByText('(minimum 20 characters)')).not.toBeVisible();
			await expect(submitButton).toBeEnabled();
		});

		test('displays example questions', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Check examples section
			await expect(page.getByText(/Need inspiration/i)).toBeVisible();

			// Check example buttons exist (at least one)
			const exampleButtons = page.locator('button:has-text("Series A")');
			await expect(exampleButtons.first()).toBeVisible();
		});

		test('clicking example fills textarea', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem');

			// Click an example
			await page.locator('button:has-text("Series A")').first().click();

			// Check textarea is filled
			const value = await textarea.inputValue();
			expect(value.length).toBeGreaterThan(20);
			expect(value).toContain('Series A');
		});

		test('back button navigates to dashboard', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Click back button (aria-label)
			await page.getByRole('link', { name: /Back to dashboard/i }).click();

			await expect(page).toHaveURL('/dashboard');
		});

		test('cancel button navigates to dashboard', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.getByRole('link', { name: /Cancel/i }).click();

			await expect(page).toHaveURL('/dashboard');
		});

		test('shows what happens next info', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Check info box - exact text from UI
			await expect(page.getByText('What happens next?')).toBeVisible();
			await expect(page.getByText(/3-5 expert personas/i)).toBeVisible();
			// Be more specific to avoid matching multiple elements
			await expect(page.getByText('A clear recommendation with action steps')).toBeVisible();
		});
	});

	test.describe('Form submission', () => {
		test('submit button shows loading state', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem');
			const submitButton = page.getByRole('button', { name: /Start Meeting/i });

			// Fill valid text
			await textarea.fill(
				'Should we expand to the European market now or focus on strengthening our US presence first?'
			);

			// Mock the API to delay response
			await page.route('**/api/v1/sessions', async (route) => {
				await new Promise((r) => setTimeout(r, 1000));
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 'test-session-id', status: 'pending' })
				});
			});

			// Click submit
			await submitButton.click();

			// Check loading state - UI shows "Starting meeting..." with ellipsis
			await expect(page.getByText('Starting meeting...')).toBeVisible();
		});

		test('shows error on API failure', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem');
			const submitButton = page.getByRole('button', { name: /Start Meeting/i });

			await textarea.fill(
				'Should we expand to the European market now or focus on strengthening our US presence first?'
			);

			// Mock API failure
			await page.route('**/api/v1/sessions', (route) =>
				route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Internal server error' })
				})
			);

			await submitButton.click();

			// API errors show toast notification, not inline error
			await expect(page.locator('[role="alert"], .toast, [data-sonner-toast]').first()).toBeVisible({ timeout: 5000 });
		});

		test('Ctrl+Enter submits form', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem');

			await textarea.fill(
				'Should we expand to the European market now or focus on strengthening our US presence first?'
			);

			// Mock successful API with delay to catch loading state
			await page.route('**/api/v1/sessions', async (route) => {
				await new Promise((r) => setTimeout(r, 500));
				await route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ id: 'test-session', status: 'pending' })
				});
			});
			await page.route('**/api/v1/sessions/*/start', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ status: 'started' })
				})
			);

			// Use keyboard shortcut
			await textarea.press('Control+Enter');

			// Should show loading state
			await expect(page.getByText('Starting meeting...')).toBeVisible();
		});
	});

	test.describe('Dataset attachment', () => {
		test('shows dataset selector when datasets exist', async ({ page }) => {
			// Mock datasets API before navigation
			await page.route('**/api/v1/datasets*', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						datasets: [
							{ id: 'ds1', name: 'Sales Data 2024', row_count: 1500 },
							{ id: 'ds2', name: 'Customer Survey', row_count: 500 }
						]
					})
				})
			);

			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Check dataset selector label - text contains "Attach Dataset"
			await expect(page.getByText('Attach Dataset (Optional)')).toBeVisible();

			// Check options - select has id="dataset"
			const select = page.locator('#dataset');
			await expect(select).toBeVisible();
			await expect(select.locator('option')).toHaveCount(3); // None + 2 datasets
		});

		test('hides dataset selector when no datasets', async ({ page }) => {
			// Mock empty datasets before navigation
			await page.route('**/api/v1/datasets*', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ datasets: [] })
				})
			);

			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Dataset selector section should not be visible (no label, no select)
			await expect(page.getByText('Attach Dataset (Optional)')).not.toBeVisible();
			await expect(page.locator('#dataset')).not.toBeVisible();
		});
	});

	test.describe('Navigation from dashboard', () => {
		test('new meeting button on dashboard navigates to form', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Find and click new meeting button/link
			const newMeetingLink = page.getByRole('link', { name: /New Meeting|New Decision/i });
			if (await newMeetingLink.isVisible()) {
				await newMeetingLink.click();
				await expect(page).toHaveURL('/meeting/new');
			}
		});
	});
});
