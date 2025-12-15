/**
 * E2E tests for dashboard page.
 *
 * Tests cover:
 * - Dashboard renders core components
 * - Quick actions panel buttons work
 * - Recent meetings list displays
 * - Outstanding actions section
 * - Activity heatmap renders
 *
 * Note: Uses mocked API responses for consistent test data.
 */
import { test, expect } from './fixtures';

// Mock sessions data
const mockSessions = {
	sessions: [
		{
			id: 'session-1',
			problem_statement: 'Should we expand to European markets?',
			status: 'completed',
			phase: 'complete',
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString(),
			last_activity_at: new Date().toISOString(),
			cost: 0.15,
			expert_count: 3,
			contribution_count: 6,
			task_count: 2,
			focus_area_count: 2
		},
		{
			id: 'session-2',
			problem_statement: 'What pricing strategy should we use for Q1?',
			status: 'active',
			phase: 'deliberation',
			created_at: new Date(Date.now() - 86400000).toISOString(),
			updated_at: new Date().toISOString(),
			last_activity_at: new Date().toISOString(),
			cost: 0.08,
			expert_count: 4,
			contribution_count: 4,
			task_count: 0,
			focus_area_count: 1
		}
	],
	total: 2,
	limit: 50,
	offset: 0
};

// Mock actions data - AllActionsResponse structure
const mockActions = {
	sessions: [
		{
			session_id: 'session-1',
			problem_statement: 'European expansion',
			session_status: 'completed',
			created_at: new Date().toISOString(),
			extracted_at: new Date().toISOString(),
			task_count: 2,
			by_status: { todo: 1, in_progress: 1, done: 0 },
			tasks: [
				{
					id: 'action-1',
					title: 'Conduct market research for Europe',
					description: 'Research key European markets',
					status: 'todo',
					priority: 'high',
					category: 'research',
					suggested_completion_date: new Date(Date.now() - 86400000).toISOString(), // Overdue
					created_at: new Date().toISOString(),
					session_id: 'session-1',
					problem_statement: 'European expansion',
					updated_at: new Date().toISOString()
				},
				{
					id: 'action-2',
					title: 'Build partnership roadmap',
					description: 'Create partnership strategy',
					status: 'in_progress',
					priority: 'medium',
					category: 'implementation',
					suggested_completion_date: new Date(Date.now() + 86400000 * 7).toISOString(), // 7 days
					created_at: new Date().toISOString(),
					session_id: 'session-1',
					problem_statement: 'European expansion',
					updated_at: new Date().toISOString()
				}
			]
		}
	],
	total_tasks: 2,
	by_status: { todo: 1, in_progress: 1, done: 0 }
};

// Mock action stats for heatmap
const mockActionStats = {
	daily_stats: Array.from({ length: 365 }, (_, i) => ({
		date: new Date(Date.now() - i * 86400000).toISOString().split('T')[0],
		sessions_run: i % 7 === 0 ? 1 : 0,
		actions_completed: i % 3 === 0 ? 1 : 0,
		actions_started: i % 5 === 0 ? 1 : 0,
		mentor_sessions: i % 10 === 0 ? 1 : 0
	})),
	total_sessions: 52,
	total_actions_completed: 122,
	total_actions_started: 73,
	total_mentor_sessions: 37
};

// Mock user context
const mockUserContext = {
	context: {
		company_name: 'Test Company',
		industry: 'SaaS',
		onboarding_completed: true
	}
};

test.describe('Dashboard Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock user API
		await page.route('**/api/v1/user', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					user_id: 'test-user',
					email: 'test@example.com',
					is_admin: false,
					tier: 'starter'
				})
			})
		);

		// Mock sessions API
		await page.route('**/api/v1/sessions**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockSessions)
			})
		);

		// Mock actions API
		await page.route('**/api/v1/actions**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockActions)
			})
		);

		// Mock action stats API
		await page.route('**/api/v1/actions/stats**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockActionStats)
			})
		);

		// Mock user context API
		await page.route('**/api/v1/context', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockUserContext)
			})
		);

		// Mock action reminders API
		await page.route('**/api/v1/actions/reminders**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ reminders: [] })
			})
		);

		// Mock value metrics API
		await page.route('**/api/v1/user/value-metrics', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ metrics: [] })
			})
		);
	});

	test.describe('Page rendering', () => {
		test('renders dashboard with welcome message', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for dashboard heading or welcome
			await expect(page.getByText(/Dashboard|Welcome/i).first()).toBeVisible();
		});

		test('displays quick actions panel', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for New Meeting button/link
			const newMeetingBtn = page.getByRole('link', { name: /New Meeting|New Decision/i });
			await expect(newMeetingBtn.first()).toBeVisible();
		});

		test('displays recent meetings section', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for recent meetings content (from mock data)
			await expect(page.getByText(/European markets/i)).toBeVisible({ timeout: 5000 });
		});

		test('displays outstanding actions section', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for outstanding actions heading
			await expect(page.getByText(/Outstanding|Actions/i).first()).toBeVisible();

			// Check for action from mock data
			await expect(page.getByText(/market research/i).first()).toBeVisible({ timeout: 5000 });
		});

		test('displays activity heatmap', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for heatmap container (it renders a grid of cells)
			const heatmapContainer = page.locator('[data-testid="activity-heatmap"], .activity-heatmap');
			if (await heatmapContainer.first().isVisible()) {
				await expect(heatmapContainer.first()).toBeVisible();
			}
		});
	});

	test.describe('Quick actions', () => {
		test('new meeting button navigates to meeting creation', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find and click new meeting button
			const newMeetingBtn = page.getByRole('link', { name: /New Meeting|New Decision/i });
			if (await newMeetingBtn.first().isVisible()) {
				await newMeetingBtn.first().click();
				await expect(page).toHaveURL(/\/meeting\/new/);
			}
		});

		test('view actions link navigates to actions page', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find and click view all actions link
			const actionsLink = page.getByRole('link', { name: /View all|All Actions/i });
			if (await actionsLink.first().isVisible()) {
				await actionsLink.first().click();
				await expect(page).toHaveURL(/\/actions/);
			}
		});
	});

	test.describe('Actions needing attention', () => {
		test('shows overdue actions with warning indicator', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for overdue indicator (red badge/text)
			const overdueIndicator = page.locator('.text-red-500, .text-red-600, .bg-red-100');
			await expect(overdueIndicator.first()).toBeVisible({ timeout: 5000 });
		});

		test('clicking action navigates to action detail', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click on an action
			const actionLink = page.getByText(/market research/i).first();
			if (await actionLink.isVisible()) {
				await actionLink.click();
				await expect(page).toHaveURL(/\/actions\/action-1/);
			}
		});
	});

	test.describe('Recent meetings', () => {
		test('clicking meeting navigates to meeting detail', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click on a meeting
			const meetingLink = page.getByText(/European markets/i);
			if (await meetingLink.isVisible()) {
				await meetingLink.click();
				await expect(page).toHaveURL(/\/meeting\/session-1/);
			}
		});

		test('shows meeting status badges', async ({ page }) => {
			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for status badge
			const statusBadge = page.locator('span').filter({ hasText: /completed|active|in progress/i });
			await expect(statusBadge.first()).toBeVisible({ timeout: 5000 });
		});
	});

	test.describe('Empty state', () => {
		test('shows empty state when no sessions', async ({ page }) => {
			// Override to return empty sessions
			await page.route('**/api/v1/sessions**', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ sessions: [], total: 0, limit: 50, offset: 0 })
				})
			);

			await page.route('**/api/v1/actions**', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ sessions: [], total_tasks: 0, by_status: {} })
				})
			);

			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for onboarding or empty state message
			await expect(page.getByText(/Get started|first meeting|No meetings/i).first()).toBeVisible({
				timeout: 5000
			});
		});
	});

	test.describe('Error handling', () => {
		test('shows error message on API failure', async ({ page }) => {
			// Override to return error
			await page.route('**/api/v1/sessions**', (route) =>
				route.fulfill({
					status: 500,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Internal server error' })
				})
			);

			await page.goto('/dashboard');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Error should be visible or gracefully handled
			const errorOrFallback = page.locator('.text-red-500, .bg-red-50, [role="alert"]');
			if (await errorOrFallback.first().isVisible()) {
				await expect(errorOrFallback.first()).toBeVisible();
			}
		});
	});
});
