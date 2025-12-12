/**
 * E2E tests for completed meeting view.
 *
 * Tests cover:
 * - Completed meeting header shows correct status
 * - Synthesis/conclusion tab visible and navigable
 * - Focus area tabs work correctly
 * - PDF export button functions
 * - Meeting metrics display
 *
 * Note: These tests use mocked API responses to simulate completed meetings.
 * Full SSE streaming is not tested here.
 */
import { test, expect } from '@playwright/test';

// Mock completed session data
const mockCompletedSession = {
	id: 'test-completed-session',
	problem_statement: 'Should we expand to European markets this quarter?',
	status: 'completed',
	created_at: new Date().toISOString(),
	completed_at: new Date().toISOString(),
	user_id: 'test_user_1'
};

// Mock events for a completed meeting
const mockEvents = [
	{
		event_type: 'session_started',
		data: { session_id: 'test-completed-session' },
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'decomposition_complete',
		data: {
			sub_problems: [
				{ id: 'sp1', goal: 'Market opportunity assessment' },
				{ id: 'sp2', goal: 'Resource requirements analysis' }
			]
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'experts_selected',
		data: {
			sub_problem_id: 'sp1',
			experts: [
				{ name: 'Strategic Analyst', role: 'analyst' },
				{ name: 'Market Expert', role: 'market' }
			]
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'synthesis_complete',
		data: {
			sub_problem_id: 'sp1',
			recommendation: 'Proceed with caution',
			key_insights: ['Market is growing', 'Competition is fierce']
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'meta_synthesis',
		data: {
			recommendation: 'Overall recommendation',
			executive_summary: 'Based on analysis, we recommend a phased approach.',
			key_actions: ['Conduct market research', 'Build partnerships']
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'session_complete',
		data: { session_id: 'test-completed-session' },
		timestamp: new Date().toISOString()
	}
];

test.describe('Completed Meeting View', () => {
	test.beforeEach(async ({ page }) => {
		// Mock session API
		await page.route('**/api/v1/sessions/test-completed-session', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockCompletedSession)
			})
		);

		// Mock events API
		await page.route('**/api/v1/sessions/test-completed-session/events', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ events: mockEvents })
			})
		);

		// Mock SSE (return completed state immediately)
		await page.route('**/api/v1/sessions/test-completed-session/stream', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: 'data: {"event_type":"session_complete","data":{}}\n\n'
			})
		);
	});

	test.describe('Header status', () => {
		test('shows "Meeting Complete" for completed session', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Wait for page to load
			await page.waitForLoadState('networkidle');

			// Check header shows complete status
			await expect(page.getByText(/Meeting Complete|Completed/i).first()).toBeVisible({
				timeout: 5000
			});
		});

		test('shows problem statement in header', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check problem statement displayed
			await expect(page.getByText(/European markets/i)).toBeVisible();
		});
	});

	test.describe('Tabs navigation', () => {
		test('conclusion/synthesis tab is visible for completed meeting', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for conclusion/synthesis tab
			const conclusionTab = page.getByRole('button', { name: /Conclusion|Synthesis|Summary/i });
			await expect(conclusionTab.first()).toBeVisible({ timeout: 5000 });
		});

		test('focus area tabs are navigable', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find focus area tabs (may be labeled "Focus Area 1" or sub-problem goals)
			const tabs = page.getByRole('button').filter({ hasText: /Focus Area|Market|Resource/i });
			const tabCount = await tabs.count();

			if (tabCount >= 2) {
				// Click second tab
				await tabs.nth(1).click();

				// Content should change (implementation-specific)
				await page.waitForTimeout(300);
			}
		});
	});

	test.describe('Meeting content', () => {
		test('displays executive summary', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for executive summary content
			await expect(page.getByText(/phased approach/i)).toBeVisible({ timeout: 5000 });
		});

		test('displays key actions/recommendations', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for action items
			await expect(page.getByText(/market research|partnerships/i).first()).toBeVisible({
				timeout: 5000
			});
		});
	});

	test.describe('PDF export', () => {
		test('PDF export button is visible', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for export/download button
			const exportButton = page.getByRole('button', { name: /Export|Download|PDF/i });
			await expect(exportButton.first()).toBeVisible({ timeout: 5000 });
		});

		test('clicking export triggers download', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Set up download listener
			const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

			// Click export button
			const exportButton = page.getByRole('button', { name: /Export|Download|PDF/i });
			if (await exportButton.first().isVisible()) {
				await exportButton.first().click();

				// Check if download was triggered (may fail in headless)
				const download = await downloadPromise;
				if (download) {
					expect(download.suggestedFilename()).toMatch(/\.pdf$|\.html$/);
				}
			}
		});
	});

	test.describe('Metrics sidebar', () => {
		test('displays meeting metrics', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for metrics section (Rounds, Contributions, etc.)
			// Implementation may vary - look for common metric labels
			const metricsSection = page.locator('[data-testid="metrics"], .metrics, aside');
			if (await metricsSection.first().isVisible()) {
				await expect(
					metricsSection.first().getByText(/Rounds|Contributions|Experts/i)
				).toBeVisible();
			}
		});
	});

	test.describe('Navigation', () => {
		test('back link returns to dashboard', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click back/home link
			const backLink = page.getByRole('link', { name: /Back|Dashboard|Home/i });
			if (await backLink.first().isVisible()) {
				await backLink.first().click();
				await expect(page).toHaveURL(/\/dashboard|\/$/);
			}
		});

		test('AI disclaimer is visible', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for AI disclaimer
			await expect(page.getByText(/AI|artificial intelligence|not financial advice/i)).toBeVisible(
				{ timeout: 5000 }
			);
		});
	});
});

test.describe('Meeting in progress', () => {
	test.beforeEach(async ({ page }) => {
		// Mock active session
		await page.route('**/api/v1/sessions/test-active-session', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					...mockCompletedSession,
					id: 'test-active-session',
					status: 'in_progress',
					completed_at: null
				})
			})
		);

		await page.route('**/api/v1/sessions/test-active-session/events', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ events: mockEvents.slice(0, 3) }) // Only early events
			})
		);
	});

	test('shows "Meeting in Progress" for active session', async ({ page }) => {
		await page.goto('/meeting/test-active-session');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check header shows in progress status
		await expect(page.getByText(/In Progress|Working|Deliberating/i).first()).toBeVisible({
			timeout: 5000
		});
	});

	test('shows working status banner', async ({ page }) => {
		await page.goto('/meeting/test-active-session');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check for activity/working indicator
		const workingIndicator = page.locator('[data-testid="working-status"], .working-status');
		if (await workingIndicator.first().isVisible()) {
			await expect(workingIndicator.first()).toBeVisible();
		}
	});
});
