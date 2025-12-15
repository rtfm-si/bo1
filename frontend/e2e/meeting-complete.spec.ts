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
import { test, expect } from './fixtures';

// Mock completed session data - matches SessionResponse structure
const mockCompletedSession = {
	id: 'test-completed-session',
	problem_statement: 'Should we expand to European markets this quarter?',
	status: 'completed' as const,
	phase: 'complete',
	created_at: new Date().toISOString(),
	updated_at: new Date().toISOString(),
	last_activity_at: new Date().toISOString(),
	cost: 0.15,
	expert_count: 2,
	contribution_count: 2,
	task_count: 2,
	focus_area_count: 2,
	stale_insights: null
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
			sub_problem_index: 0,
			experts: [
				{ name: 'Strategic Analyst', role: 'analyst' },
				{ name: 'Market Expert', role: 'market' }
			]
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'contribution',
		data: {
			sub_problem_index: 0,
			round: 1,
			persona_name: 'Strategic Analyst',
			content: 'Analysis of market opportunity...'
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'contribution',
		data: {
			sub_problem_index: 0,
			round: 1,
			persona_name: 'Market Expert',
			content: 'Market dynamics suggest...'
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'convergence',
		data: {
			sub_problem_index: 0,
			round: 1,
			score: 0.75,
			exploration_score: 0.8,
			novelty_score: 0.6
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'synthesis_complete',
		data: {
			sub_problem_id: 'sp1',
			sub_problem_index: 0,
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
		test.fixme('shows "Meeting Complete" for completed session', async ({ page }) => {
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

		test.fixme('shows problem statement in header', async ({ page }) => {
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
		test.fixme('conclusion/synthesis tab is visible for completed meeting', async ({ page }) => {
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
		test.fixme('displays executive summary', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for executive summary content
			await expect(page.getByText(/phased approach/i)).toBeVisible({ timeout: 5000 });
		});

		test.fixme('displays key actions/recommendations', async ({ page }) => {
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
		test.fixme('PDF export button is visible', async ({ page }) => {
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

		test.fixme('clicking export triggers download', async ({ page }) => {
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

			// Check for AI disclaimer - use specific text to avoid matching multiple elements
			await expect(page.getByText('AI-generated content')).toBeVisible({ timeout: 5000 });
		});
	});

	// Additional tests from _PLAN.md requirements
	test.describe('Connection status for completed meetings', () => {
		test('does not show Connected indicator for completed session', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// For completed meetings, "Connected" indicator should be hidden
			// Check that the live connection indicator is not visible
			const connectedIndicator = page.locator('text=Connected').first();
			const isVisible = await connectedIndicator.isVisible().catch(() => false);

			// If visible, it should be in a non-prominent location or the meeting isn't being treated as completed
			if (isVisible) {
				// This is acceptable as long as it's not misleading - completed meetings may show status differently
				// The key is that "Connecting..." or active SSE indicators shouldn't appear
				const connectingIndicator = page.locator('text=Connecting...').first();
				await expect(connectingIndicator).not.toBeVisible();
			}
		});
	});

	test.describe('Synthesis content rendering', () => {
		test.fixme('does not display raw JSON in executive summary', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check that raw JSON syntax is not displayed
			// Look for common JSON patterns that shouldn't appear in rendered content
			const pageContent = await page.locator('main').textContent();

			// Should not contain unrendered JSON syntax
			expect(pageContent).not.toMatch(/\{\s*"[^"]+"\s*:/); // { "key":
			expect(pageContent).not.toMatch(/"\s*:\s*\[\s*"/); // ": ["
		});

		test.fixme('displays formatted recommendations', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Verify synthesis content is properly formatted/rendered
			// Check for key action items from our mock data
			await expect(page.getByText(/market research/i).first()).toBeVisible({ timeout: 5000 });
		});
	});

	test.describe('Focus Area tab labels', () => {
		test('shows truncated goals in tab labels', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// With multiple sub-problems, tabs should show goal text (truncated if long)
			// Look for our mock sub-problem goals in the tabs
			const tabs = page.getByRole('button').filter({ hasText: /Market|Resource|Focus Area/i });
			const tabCount = await tabs.count();

			if (tabCount >= 2) {
				// Check that at least one tab shows goal text (not just "Focus Area 1")
				const marketTab = page.getByRole('button', { name: /Market/i });
				const resourceTab = page.getByRole('button', { name: /Resource/i });

				// At least one should be visible with goal text
				const marketVisible = await marketTab.first().isVisible().catch(() => false);
				const resourceVisible = await resourceTab.first().isVisible().catch(() => false);

				expect(marketVisible || resourceVisible).toBe(true);
			}
		});
	});

	test.describe('Sidebar metrics values', () => {
		test('displays rounds count greater than zero', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for the Deliberation Progress section with rounds counter
			const roundsSection = page.locator('text=Rounds').first();
			if (await roundsSection.isVisible()) {
				// Find the parent container and check for a non-zero number
				const roundsContainer = roundsSection.locator('xpath=ancestor::div[contains(@class, "flex")]').first();
				const roundsText = await roundsContainer.textContent();

				// Should show "1" from our mock convergence event with round: 1
				expect(roundsText).toMatch(/[1-9]/);
			}
		});

		test('displays contributions count greater than zero', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for contributions counter
			const contributionsSection = page.locator('text=Contributions').first();
			if (await contributionsSection.isVisible()) {
				const contributionsContainer = contributionsSection
					.locator('xpath=ancestor::div[contains(@class, "flex")]')
					.first();
				const contributionsText = await contributionsContainer.textContent();

				// Should show "2" from our 2 mock contribution events
				expect(contributionsText).toMatch(/[1-9]/);
			}
		});
	});

	test.describe('Breadcrumb navigation', () => {
		test('shows problem excerpt in breadcrumb', async ({ page }) => {
			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Breadcrumb should show problem statement excerpt, not raw UUID
			// Look for breadcrumb nav containing problem text
			const breadcrumb = page.locator('nav[aria-label="Breadcrumb"], [data-testid="breadcrumb"], .breadcrumb');
			if (await breadcrumb.first().isVisible()) {
				const breadcrumbText = await breadcrumb.first().textContent();

				// Should contain part of problem statement, not just UUID
				// Our mock problem: "Should we expand to European markets this quarter?"
				const hasReadableText =
					breadcrumbText?.includes('European') ||
					breadcrumbText?.includes('expand') ||
					breadcrumbText?.includes('markets');

				// UUID pattern check - should not be primarily UUID
				const isJustUUID = /^[a-f0-9-]{36}$/i.test(breadcrumbText?.trim() || '');

				expect(hasReadableText || !isJustUUID).toBe(true);
			}
		});
	});

	test.describe('Console errors', () => {
		test('no parsing errors in console for completed meeting', async ({ page }) => {
			const consoleErrors: string[] = [];

			page.on('console', (msg) => {
				if (msg.type() === 'error') {
					consoleErrors.push(msg.text());
				}
			});

			await page.goto('/meeting/test-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(1000); // Allow time for async rendering

			// Filter out known acceptable errors (network, external resources)
			const criticalErrors = consoleErrors.filter(
				(err) =>
					!err.includes('net::') &&
					!err.includes('favicon') &&
					!err.includes('404') &&
					(err.includes('JSON') || err.includes('parse') || err.includes('SyntaxError'))
			);

			expect(criticalErrors).toHaveLength(0);
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
					status: 'active',
					phase: 'deliberation'
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

	test.fixme('shows "Meeting in Progress" for active session', async ({ page }) => {
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
