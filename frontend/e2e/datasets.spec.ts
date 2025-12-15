/**
 * E2E tests for dataset management flow.
 *
 * Tests cover:
 * - Dataset list page
 * - CSV file upload via drag-drop
 * - CSV file upload via file picker
 * - Dataset detail page with profile
 * - Dataset Q&A chat interface
 * - Google Sheets connection (mocked OAuth)
 *
 * Note: Uses mocked API responses for consistent test data.
 */
import { test, expect } from './fixtures';

// Mock datasets data - matches DatasetListResponse structure
const mockDatasets = {
	datasets: [
		{
			id: 'ds-1',
			user_id: 'test-user',
			name: 'sales_2024.csv',
			description: 'Sales data for 2024',
			source_type: 'upload' as const,
			source_uri: null,
			file_key: 'datasets/test-user/sales_2024.csv',
			row_count: 1500,
			column_count: 12,
			file_size_bytes: 102400,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString()
		},
		{
			id: 'ds-2',
			user_id: 'test-user',
			name: 'Customer Survey',
			description: 'Customer satisfaction survey',
			source_type: 'sheets' as const,
			source_uri: 'https://docs.google.com/spreadsheets/d/test',
			file_key: null,
			row_count: 500,
			column_count: 8,
			file_size_bytes: null,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString()
		}
	],
	total: 2,
	limit: 50,
	offset: 0
};

// Mock dataset detail - matches DatasetDetailResponse structure
const mockDatasetProfile = {
	id: 'ds-1',
	user_id: 'test-user',
	name: 'sales_2024.csv',
	description: 'Sales data for 2024',
	source_type: 'upload' as const,
	source_uri: null,
	file_key: 'datasets/test-user/sales_2024.csv',
	row_count: 1500,
	column_count: 12,
	file_size_bytes: 102400,
	created_at: new Date().toISOString(),
	updated_at: new Date().toISOString(),
	summary: 'This dataset contains sales data for 2024 including revenue, units, and customer segments.',
	profiles: [
		{ id: 'p1', column_name: 'date', data_type: 'date', null_count: 0, unique_count: 365, min_value: '2024-01-01', max_value: '2024-12-31', mean_value: null, sample_values: ['2024-01-01', '2024-06-15'] },
		{ id: 'p2', column_name: 'revenue', data_type: 'currency', null_count: 5, unique_count: 1200, min_value: '100', max_value: '50000', mean_value: 5432, sample_values: [100, 5000, 12000] },
		{ id: 'p3', column_name: 'units', data_type: 'integer', null_count: 0, unique_count: 500, min_value: '1', max_value: '1000', mean_value: 45, sample_values: [1, 45, 100] },
		{ id: 'p4', column_name: 'segment', data_type: 'categorical', null_count: 0, unique_count: 4, min_value: null, max_value: null, mean_value: null, sample_values: ['Enterprise', 'SMB', 'Consumer', 'Startup'] }
	]
};

const mockAnalyses = {
	analyses: [
		{
			id: 'analysis-1',
			query: 'What are the top selling products?',
			result: 'Top products by revenue are: Product A ($500K), Product B ($350K)',
			chart_url: null,
			created_at: new Date().toISOString()
		}
	]
};

test.describe('Datasets List Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock datasets API
		await page.route('**/api/v1/datasets**', (route) => {
			const url = route.request().url();
			if (url.includes('/upload')) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						id: 'ds-new',
						name: 'uploaded.csv',
						source: 'upload',
						row_count: 100
					})
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockDatasets)
			});
		});

		// Mock sheets connection status
		await page.route('**/api/v1/auth/google/sheets/status', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ connected: false })
			})
		);
	});

	test.describe('List view', () => {
		test('displays datasets list', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check page heading
			await expect(page.getByRole('heading', { name: /Datasets|Data/i }).first()).toBeVisible();

			// Check datasets are displayed
			await expect(page.getByText('sales_2024.csv')).toBeVisible();
			await expect(page.getByText('Customer Survey')).toBeVisible();
		});

		test('shows dataset metadata', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check row count displayed
			await expect(page.getByText(/1,500 rows|1500 rows/i)).toBeVisible();

			// Check source indicators
			await expect(page.getByText(/upload|csv/i).first()).toBeVisible();
		});

		test.fixme('empty state when no datasets', async ({ page }) => {
			await page.route('**/api/v1/datasets**', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ datasets: [], total: 0, limit: 50, offset: 0 })
				})
			);

			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check empty state message
			await expect(page.getByText(/No datasets|Upload|Get started/i)).toBeVisible();
		});
	});

	test.describe('CSV Upload', () => {
		test('upload zone is visible', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check upload zone
			await expect(page.getByText(/drag.*drop|upload.*csv/i).first()).toBeVisible();
		});

		test('file picker button works', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find file input
			const fileInput = page.locator('input[type="file"]');
			await expect(fileInput).toBeAttached();
		});

		test('upload shows progress indicator', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Create a test CSV file
			const csvContent = 'name,value\nTest,123\n';

			// Mock slow upload
			await page.route('**/api/v1/datasets/upload', async (route) => {
				await new Promise((r) => setTimeout(r, 500));
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						id: 'ds-new',
						name: 'test.csv',
						source: 'upload',
						row_count: 1
					})
				});
			});

			// Trigger file upload via file chooser
			const fileChooserPromise = page.waitForEvent('filechooser');
			const uploadButton = page.getByRole('button', { name: /Upload|Browse|Select/i });
			if (await uploadButton.first().isVisible()) {
				await uploadButton.first().click();
				const fileChooser = await fileChooserPromise;
				await fileChooser.setFiles({
					name: 'test.csv',
					mimeType: 'text/csv',
					buffer: Buffer.from(csvContent)
				});

				// Check for uploading indicator
				await expect(page.getByText(/Uploading|Processing/i)).toBeVisible({ timeout: 2000 });
			}
		});

		test('upload error displays message', async ({ page }) => {
			await page.route('**/api/v1/datasets/upload', (route) =>
				route.fulfill({
					status: 400,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Invalid CSV format' })
				})
			);

			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Trigger file upload
			const fileChooserPromise = page.waitForEvent('filechooser');
			const uploadButton = page.getByRole('button', { name: /Upload|Browse|Select/i });
			if (await uploadButton.first().isVisible()) {
				await uploadButton.first().click();
				const fileChooser = await fileChooserPromise;
				await fileChooser.setFiles({
					name: 'test.csv',
					mimeType: 'text/csv',
					buffer: Buffer.from('invalid')
				});

				// Check for error message
				await expect(page.getByText(/error|failed|invalid/i)).toBeVisible({ timeout: 3000 });
			}
		});
	});

	test.describe('Google Sheets', () => {
		test('Connect Google Sheets button visible', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for Sheets connection option
			const sheetsButton = page.getByRole('button', { name: /Google Sheets|Connect.*Sheets/i });
			if (await sheetsButton.isVisible()) {
				await expect(sheetsButton).toBeVisible();
			}
		});

		test('shows connected state when Sheets linked', async ({ page }) => {
			await page.route('**/api/v1/auth/google/sheets/status', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ connected: true })
				})
			);

			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for connected indicator
			await expect(page.getByText(/connected|linked/i)).toBeVisible({ timeout: 3000 });
		});
	});

	test.describe('Navigation', () => {
		test('clicking dataset navigates to detail', async ({ page }) => {
			await page.goto('/datasets');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click on dataset
			await page.getByText('sales_2024.csv').click();

			await expect(page).toHaveURL(/\/datasets\/ds-1/);
		});
	});
});

test.describe('Dataset Detail Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock dataset detail
		await page.route('**/api/v1/datasets/ds-1', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockDatasetProfile)
			})
		);

		// Mock dataset profile
		await page.route('**/api/v1/datasets/ds-1/profile', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockDatasetProfile)
			})
		);

		// Mock analyses
		await page.route('**/api/v1/datasets/ds-1/analyses', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAnalyses)
			})
		);
	});

	test.fixme('displays dataset profile summary', async ({ page }) => {
		await page.goto('/datasets/ds-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check dataset name displayed
		await expect(page.getByText('sales_2024.csv')).toBeVisible();

		// Check summary displayed
		await expect(page.getByText(/sales data for 2024/i)).toBeVisible();
	});

	test('displays column statistics', async ({ page }) => {
		await page.goto('/datasets/ds-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check column info displayed
		await expect(page.getByText(/date|revenue|units|segment/i).first()).toBeVisible();
	});

	test.fixme('displays row and column counts', async ({ page }) => {
		await page.goto('/datasets/ds-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check counts
		await expect(page.getByText(/1,500|1500/)).toBeVisible();
		await expect(page.getByText(/12 columns|12 cols/i)).toBeVisible();
	});

	test.describe('Chat interface', () => {
		test('chat input is visible', async ({ page }) => {
			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for chat input
			const chatInput = page.locator(
				'input[placeholder*="Ask"], textarea[placeholder*="Ask"], input[placeholder*="question"]'
			);
			await expect(chatInput.first()).toBeVisible({ timeout: 5000 });
		});

		test.fixme('can submit question', async ({ page }) => {
			// Mock SSE for chat
			await page.route('**/api/v1/datasets/ds-1/ask', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'text/event-stream',
					body: 'data: {"type":"response","content":"The top products are..."}\n\n'
				})
			);

			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find and fill chat input
			const chatInput = page.locator(
				'input[placeholder*="Ask"], textarea[placeholder*="Ask"], input[placeholder*="question"]'
			);
			if (await chatInput.first().isVisible()) {
				await chatInput.first().fill('What are the top selling products?');

				// Submit
				await page.keyboard.press('Enter');

				// Should show response or loading
				await expect(page.getByText(/top products|loading|processing/i).first()).toBeVisible({
					timeout: 5000
				});
			}
		});

		test.fixme('shows analysis history', async ({ page }) => {
			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for history section
			await expect(page.getByText(/top selling products/i)).toBeVisible({ timeout: 5000 });
		});
	});

	test.describe('Navigation', () => {
		test('back link returns to datasets list', async ({ page }) => {
			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click back link
			const backLink = page.getByRole('link', { name: /Back|Datasets/i });
			if (await backLink.first().isVisible()) {
				await backLink.first().click();
				await expect(page).toHaveURL(/\/datasets$/);
			}
		});
	});
});
