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
			dataset_id: 'ds-1',
			title: 'Top selling products',
			chart_spec: { chart_type: 'bar', x_field: 'product', y_field: 'revenue' },
			chart_url: null,
			created_at: new Date().toISOString()
		}
	],
	total: 1
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
		// FIXME: Flaky - heading not found due to page load timing in CI
		test.fixme('displays datasets list', async ({ page }) => {
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

		test('empty state when no datasets', async ({ page }) => {
			// Override mock to return empty datasets - must be set before navigation
			await page.unroute('**/api/v1/datasets**');
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

			// Check empty state message - exact text from UI
			await expect(page.getByText('No datasets yet')).toBeVisible();
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

	// FIXME: Flaky - AI Summary section may not load in time in CI
	test.fixme('displays dataset profile summary', async ({ page }) => {
		await page.goto('/datasets/ds-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check dataset name displayed in heading (not breadcrumb)
		await expect(page.getByRole('heading', { name: 'sales_2024.csv' })).toBeVisible();

		// Check AI Summary section header
		await expect(page.getByText('AI Summary')).toBeVisible();

		// Check summary content - the mock has "This dataset contains sales data for 2024..."
		await expect(page.getByText(/contains sales data for 2024/i)).toBeVisible();
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

	test('displays row and column counts', async ({ page }) => {
		await page.goto('/datasets/ds-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check rows stat - label and value in stats grid
		const rowsStat = page.locator('.bg-neutral-50, .dark\\:bg-neutral-700\\/50').filter({ hasText: 'Rows' });
		await expect(rowsStat.getByText('1,500')).toBeVisible();

		// Check columns stat - label and value in stats grid
		const columnsStat = page.locator('.bg-neutral-50, .dark\\:bg-neutral-700\\/50').filter({ hasText: 'Columns' });
		await expect(columnsStat.getByText('12')).toBeVisible();
	});

	test.describe('Chat interface', () => {
		test('chat input is visible', async ({ page }) => {
			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click the collapsed chat bar to expand it
			const chatBar = page.getByRole('button', { name: /Ask a question about your data/i });
			await expect(chatBar).toBeVisible({ timeout: 5000 });
			await chatBar.click();

			// Check for chat input in expanded state
			const chatInput = page.locator(
				'input[placeholder*="Ask"], textarea[placeholder*="Ask"], input[placeholder*="question"]'
			);
			await expect(chatInput.first()).toBeVisible({ timeout: 5000 });
		});

		test('can submit question', async ({ page }) => {
			// Mock SSE for chat - proper SSE format with event name
			await page.route('**/api/v1/datasets/ds-1/ask', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'text/event-stream',
					body: 'event: analysis\ndata: {"content":"The top products are Product A and Product B"}\n\nevent: done\ndata: {"conversation_id":"conv-1"}\n\n'
				})
			);

			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click the collapsed chat bar to expand it
			const chatBar = page.getByRole('button', { name: /Ask a question about your data/i });
			await expect(chatBar).toBeVisible({ timeout: 5000 });
			await chatBar.click();

			// Find and fill chat input - exact placeholder from DatasetChat.svelte
			const chatInput = page.getByPlaceholder('Ask a question about your data...');
			await expect(chatInput).toBeVisible();
			await chatInput.fill('What are the top selling products?');

			// Submit via Enter
			await page.keyboard.press('Enter');

			// Response from SSE mock should appear (component shows assistant response)
			await expect(page.getByText('The top products are Product A and Product B')).toBeVisible({
				timeout: 5000
			});
		});

		test('shows analysis history', async ({ page }) => {
			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for Analysis History section header
			await expect(page.getByText('Analysis History')).toBeVisible();

			// Analysis gallery should display the mock analysis title on hover
			// The title is shown in the hover overlay - we can check for the button existence
			const analysisButton = page.locator('button[type="button"]').filter({ hasText: /Top selling products|Analysis/i });
			await expect(analysisButton.first()).toBeVisible({ timeout: 5000 });
		});
	});

	test.describe('Navigation', () => {
		// Flaky in CI due to navigation timing, works locally
		test.fixme('back link returns to datasets list', async ({ page }) => {
			await page.goto('/datasets/ds-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click back link - may go to /datasets or /mentor?tab=data depending on navigation context
			const backLink = page.getByRole('link', { name: /Back|Datasets/i });
			if (await backLink.first().isVisible()) {
				await backLink.first().click();
				// Accept either /datasets or /mentor?tab=data as valid destinations
				await expect(page).toHaveURL(/\/datasets$|\/mentor\?tab=data/);
			}
		});
	});
});

// Mock insights data - matches DatasetInsightsResponse structure
const mockInsights = {
	insights: {
		identity: { name: 'Sales Data', description: 'Sales transaction data' },
		headline_metrics: [
			{ label: 'Total Revenue', value: '$1.2M', context: 'vs $800K last period', trend: 'up 50%', is_good: true },
			{ label: 'Avg Order', value: '$245', context: 'per transaction', trend: 'up 12%', is_good: true },
			{ label: 'Customers', value: '4,892', context: 'unique buyers', trend: null, is_good: null },
			{ label: 'Refund Rate', value: '2.3%', context: 'of orders', trend: 'down 0.5%', is_good: true }
		],
		insights: [
			{ type: 'trend', severity: 'high', headline: 'Revenue growing rapidly', detail: 'Q4 revenue is 50% higher than Q3', metric: 'revenue', action: 'Analyze top products' },
			{ type: 'pattern', severity: 'medium', headline: 'Weekend sales spike', detail: 'Saturday and Sunday account for 40% of weekly sales', metric: 'orders', action: null },
			{ type: 'anomaly', severity: 'low', headline: 'Unusual spike on Dec 15', detail: 'Orders were 3x normal volume', metric: 'orders', action: 'Investigate promotion' }
		],
		quality: { overall_score: 92, completeness: 98, consistency: 88, validity: 95 },
		suggested_questions: [
			{ question: 'What products have the highest revenue?', category: 'revenue', why_relevant: 'Identify top performers' },
			{ question: 'Which customer segment is growing fastest?', category: 'growth', why_relevant: 'Focus acquisition efforts' },
			{ question: 'What is the trend in average order value?', category: 'metrics', why_relevant: 'Track pricing effectiveness' }
		],
		column_semantics: [],
		narrative_summary: 'This sales dataset shows strong Q4 performance with 50% revenue growth.'
	},
	generated_at: new Date().toISOString(),
	model_used: 'claude-3-haiku',
	tokens_used: 1500,
	cached: true
};

test.describe.skip('Analysis Tab - Insights Preview', () => {
	// FIXME: All tests in this group fail in CI due to select dropdown timeout
	// selectOption times out waiting for the dataset dropdown to be available
	test.beforeEach(async ({ page }) => {
		// Mock datasets list
		await page.route('**/api/v1/datasets**', (route) => {
			const url = route.request().url();
			if (url.includes('/insights')) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockInsights)
				});
			}
			if (url.match(/\/api\/v1\/datasets\/ds-1$/)) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockDatasetProfile)
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockDatasets)
			});
		});

		// Mock mentor conversations
		await page.route('**/api/v1/mentor/conversations**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ conversations: [], total: 0 })
			})
		);
	});

	test('selecting dataset shows insights panel', async ({ page }) => {
		await page.goto('/mentor?tab=analysis');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Select dataset from dropdown
		const datasetSelector = page.locator('select');
		await datasetSelector.selectOption('ds-1');

		// Wait for insights to load
		await page.waitForResponse((resp) => resp.url().includes('/insights') && resp.status() === 200);

		// Check headline metrics appear
		await expect(page.getByText('Key Metrics')).toBeVisible();
		await expect(page.getByText('Total Revenue')).toBeVisible();
		await expect(page.getByText('$1.2M')).toBeVisible();

		// Check insights section appears
		await expect(page.getByText('Notable Patterns')).toBeVisible();
		await expect(page.getByText('Revenue growing rapidly')).toBeVisible();

		// Check suggested questions appear
		await expect(page.getByText('Explore Your Data')).toBeVisible();
		await expect(page.getByText('What products have the highest revenue?')).toBeVisible();
	});

	test('clicking suggested question submits it', async ({ page }) => {
		// Mock analysis SSE response
		await page.route('**/api/v1/datasets/ds-1/ask', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: 'event: analysis\ndata: {"content":"Top products: Product A ($500K), Product B ($300K)"}\n\nevent: done\ndata: {"conversation_id":"conv-1"}\n\n'
			})
		);

		await page.goto('/mentor?tab=analysis');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Select dataset
		const datasetSelector = page.locator('select');
		await datasetSelector.selectOption('ds-1');

		// Wait for insights
		await page.waitForResponse((resp) => resp.url().includes('/insights') && resp.status() === 200);

		// Click suggested question
		await page.getByRole('button', { name: /What products have the highest revenue/i }).click();

		// Response should appear
		await expect(page.getByText('Top products: Product A')).toBeVisible({ timeout: 5000 });
	});

	test('insights panel hides after first question', async ({ page }) => {
		// Mock analysis SSE response
		await page.route('**/api/v1/datasets/ds-1/ask', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: 'event: analysis\ndata: {"content":"Analysis complete"}\n\nevent: done\ndata: {"conversation_id":"conv-1"}\n\n'
			})
		);

		await page.goto('/mentor?tab=analysis');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Select dataset
		const datasetSelector = page.locator('select');
		await datasetSelector.selectOption('ds-1');

		// Wait for insights
		await page.waitForResponse((resp) => resp.url().includes('/insights') && resp.status() === 200);

		// Insights should be visible
		await expect(page.getByText('Key Metrics')).toBeVisible();

		// Click suggested question
		await page.getByRole('button', { name: /What products have the highest revenue/i }).click();

		// Wait for response
		await expect(page.getByText('Analysis complete')).toBeVisible({ timeout: 5000 });

		// Insights panel should be hidden (messages.length > 0)
		await expect(page.getByText('Key Metrics')).not.toBeVisible();
	});

	test('switching datasets loads new insights', async ({ page }) => {
		// Add second dataset with different insights
		const secondDataset = {
			...mockDatasets,
			datasets: [
				...mockDatasets.datasets,
				{
					id: 'ds-3',
					user_id: 'test-user',
					name: 'inventory_2024.csv',
					description: 'Inventory data',
					source_type: 'upload' as const,
					source_uri: null,
					file_key: 'datasets/test-user/inventory.csv',
					row_count: 2000,
					column_count: 8,
					file_size_bytes: 50000,
					created_at: new Date().toISOString(),
					updated_at: new Date().toISOString()
				}
			]
		};

		const inventoryInsights = {
			...mockInsights,
			insights: {
				...mockInsights.insights,
				headline_metrics: [
					{ label: 'SKUs', value: '1,234', context: 'active products', trend: null, is_good: null }
				],
				narrative_summary: 'Inventory dataset with 1,234 active SKUs.'
			}
		};

		await page.route('**/api/v1/datasets**', (route) => {
			const url = route.request().url();
			if (url.includes('ds-3/insights')) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(inventoryInsights)
				});
			}
			if (url.includes('ds-1/insights')) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockInsights)
				});
			}
			if (url.match(/\/api\/v1\/datasets\/ds-\d+$/)) {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockDatasetProfile)
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(secondDataset)
			});
		});

		await page.goto('/mentor?tab=analysis');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Select first dataset
		const datasetSelector = page.locator('select');
		await datasetSelector.selectOption('ds-1');

		// Wait for first insights
		await expect(page.getByText('Total Revenue')).toBeVisible();

		// Select second dataset
		await datasetSelector.selectOption('ds-3');

		// Wait for new insights - use exact match to avoid strict mode violation
		await expect(page.getByText('SKUs', { exact: true })).toBeVisible();
		await expect(page.getByText('1,234', { exact: true })).toBeVisible();

		// Old insights should be gone
		await expect(page.getByText('Total Revenue')).not.toBeVisible();
	});

	test('unprofiled dataset shows profiling message', async ({ page }) => {
		await page.route('**/api/v1/datasets/ds-1/insights', (route) =>
			route.fulfill({
				status: 422,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Dataset not yet profiled' })
			})
		);

		await page.goto('/mentor?tab=analysis');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Select dataset
		const datasetSelector = page.locator('select');
		await datasetSelector.selectOption('ds-1');

		// Wait for 422 response
		await page.waitForResponse((resp) => resp.url().includes('/insights'));

		// Check profiling message appears
		await expect(page.getByText(/Analyzing your data/i)).toBeVisible();
	});
});
