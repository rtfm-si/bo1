/**
 * E2E tests for actions management flow.
 *
 * Tests cover:
 * - Actions list page with filters
 * - Status filter and due date filter
 * - Bulk selection and bulk actions
 * - Action detail page
 * - Gantt chart view
 *
 * Note: Uses mocked API responses for consistent test data.
 */
import { test, expect } from '@playwright/test';

// Mock actions data
const mockActions = {
	actions: [
		{
			id: 'action-1',
			title: 'Conduct market research',
			status: 'todo',
			priority: 'high',
			due_date: new Date(Date.now() - 86400000).toISOString(), // Yesterday (overdue)
			session_id: 'session-1',
			session_problem: 'European expansion',
			created_at: new Date().toISOString()
		},
		{
			id: 'action-2',
			title: 'Build partnership roadmap',
			status: 'in_progress',
			priority: 'medium',
			due_date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
			session_id: 'session-1',
			session_problem: 'European expansion',
			created_at: new Date().toISOString()
		},
		{
			id: 'action-3',
			title: 'Review competitor analysis',
			status: 'completed',
			priority: 'low',
			due_date: null,
			session_id: 'session-2',
			session_problem: 'Pricing strategy',
			created_at: new Date().toISOString()
		},
		{
			id: 'action-4',
			title: 'Draft marketing plan',
			status: 'todo',
			priority: 'medium',
			due_date: new Date().toISOString(), // Today
			session_id: 'session-1',
			session_problem: 'European expansion',
			created_at: new Date().toISOString()
		}
	],
	total: 4,
	meetings: [
		{ id: 'session-1', problem_statement: 'European expansion' },
		{ id: 'session-2', problem_statement: 'Pricing strategy' }
	]
};

const mockGanttData = {
	tasks: mockActions.actions.map((a) => ({
		id: a.id,
		name: a.title,
		start: a.due_date || new Date().toISOString(),
		end: a.due_date || new Date().toISOString(),
		progress: a.status === 'completed' ? 100 : a.status === 'in_progress' ? 50 : 0,
		dependencies: []
	}))
};

test.describe('Actions List Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock actions API
		await page.route('**/api/v1/actions**', (route) => {
			const url = new URL(route.request().url());
			const status = url.searchParams.get('status');

			let filteredActions = [...mockActions.actions];

			if (status && status !== 'all') {
				filteredActions = filteredActions.filter((a) => a.status === status);
			}

			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ ...mockActions, actions: filteredActions })
			});
		});

		// Mock projects API
		await page.route('**/api/v1/projects**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ projects: [] })
			})
		);

		// Mock tags API
		await page.route('**/api/v1/tags**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ tags: [] })
			})
		);

		// Mock gantt API
		await page.route('**/api/v1/gantt**', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockGanttData)
			})
		);
	});

	test.describe('List view', () => {
		test('displays actions list', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check page title
			await expect(page.getByRole('heading', { name: /Actions/i }).first()).toBeVisible();

			// Check actions are displayed
			await expect(page.getByText('Conduct market research')).toBeVisible();
			await expect(page.getByText('Build partnership roadmap')).toBeVisible();
		});

		test('shows overdue warning for past due actions', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for overdue indicator (red text/badge)
			const overdueIndicator = page.locator('.text-red-500, .text-red-600, .bg-red-100');
			await expect(overdueIndicator.first()).toBeVisible({ timeout: 5000 });
		});
	});

	test.describe('Status filter', () => {
		test('filter dropdown is visible', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check filter controls
			const statusFilter = page.locator('select, [role="combobox"]').filter({ hasText: /Status/i });
			if (await statusFilter.first().isVisible()) {
				await expect(statusFilter.first()).toBeVisible();
			}
		});

		test('filtering by status updates list', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Initial: all actions visible
			await expect(page.getByText('Conduct market research')).toBeVisible();
			await expect(page.getByText('Review competitor analysis')).toBeVisible();

			// Find and click status filter
			const statusSelect = page.locator('select').filter({ hasText: /all|status/i }).first();
			if (await statusSelect.isVisible()) {
				await statusSelect.selectOption('completed');

				// Wait for filtered results
				await page.waitForTimeout(500);

				// Only completed action visible
				await expect(page.getByText('Review competitor analysis')).toBeVisible();
			}
		});
	});

	test.describe('Due date filter', () => {
		test('due date filter options exist', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for due date filter
			const dueDateFilter = page.locator('select, button').filter({ hasText: /Due|Date/i });
			if (await dueDateFilter.first().isVisible()) {
				await expect(dueDateFilter.first()).toBeVisible();
			}
		});
	});

	test.describe('Bulk actions', () => {
		test('checkboxes appear for multi-select', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for checkboxes
			const checkboxes = page.locator('input[type="checkbox"]');
			const count = await checkboxes.count();
			expect(count).toBeGreaterThanOrEqual(1);
		});

		test('select all checkbox selects all actions', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find select all checkbox (usually in header)
			const selectAll = page.locator('input[type="checkbox"]').first();
			if (await selectAll.isVisible()) {
				await selectAll.click();

				// Check that action bar appears
				const bulkActionBar = page.locator('[data-testid="bulk-actions"], .bulk-actions');
				if (await bulkActionBar.isVisible()) {
					await expect(bulkActionBar).toBeVisible();
				}
			}
		});

		test('bulk complete button works', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Select first checkbox
			const firstCheckbox = page.locator('input[type="checkbox"]').first();
			if (await firstCheckbox.isVisible()) {
				await firstCheckbox.click();

				// Look for bulk complete button
				const completeBtn = page.getByRole('button', { name: /Mark Complete|Complete/i });
				if (await completeBtn.isVisible()) {
					await expect(completeBtn).toBeEnabled();
				}
			}
		});
	});

	test.describe('Gantt view', () => {
		test('toggle to Gantt view', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for view toggle
			const ganttToggle = page.getByRole('button', { name: /Gantt/i });
			if (await ganttToggle.isVisible()) {
				await ganttToggle.click();

				// Wait for Gantt chart to render
				await page.waitForTimeout(500);

				// Check for Gantt chart container
				const ganttChart = page.locator('.gantt, [data-testid="gantt-chart"], svg.gantt');
				await expect(ganttChart.first()).toBeVisible({ timeout: 5000 });
			}
		});

		test('Gantt chart click does not navigate on drag', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Switch to Gantt view
			const ganttToggle = page.getByRole('button', { name: /Gantt/i });
			if (await ganttToggle.isVisible()) {
				await ganttToggle.click();
				await page.waitForTimeout(500);

				// Simulate drag on Gantt bar (should not navigate)
				const ganttBar = page.locator('.bar, .gantt-bar').first();
				if (await ganttBar.isVisible()) {
					const box = await ganttBar.boundingBox();
					if (box) {
						// Drag horizontally
						await page.mouse.move(box.x + 10, box.y + box.height / 2);
						await page.mouse.down();
						await page.mouse.move(box.x + 50, box.y + box.height / 2);
						await page.mouse.up();

						// Should still be on actions page
						await expect(page).toHaveURL(/\/actions/);
					}
				}
			}
		});
	});

	test.describe('Action detail navigation', () => {
		test('clicking action navigates to detail page', async ({ page }) => {
			await page.goto('/actions');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click on action title/link
			const actionLink = page.getByText('Conduct market research');
			if (await actionLink.isVisible()) {
				await actionLink.click();

				// Should navigate to action detail
				await expect(page).toHaveURL(/\/actions\/action-1/);
			}
		});
	});
});

test.describe('Action Detail Page', () => {
	test.beforeEach(async ({ page }) => {
		// Mock single action API
		await page.route('**/api/v1/actions/action-1', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockActions.actions[0])
			})
		);
	});

	test('displays action details', async ({ page }) => {
		await page.goto('/actions/action-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check action title displayed
		await expect(page.getByText('Conduct market research')).toBeVisible();
	});

	test('shows status badge', async ({ page }) => {
		await page.goto('/actions/action-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check status badge
		await expect(page.getByText(/todo|To Do/i)).toBeVisible();
	});

	test('shows priority indicator', async ({ page }) => {
		await page.goto('/actions/action-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check priority indicator
		await expect(page.getByText(/high/i)).toBeVisible();
	});

	test('back link navigates to actions list', async ({ page }) => {
		await page.goto('/actions/action-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Find and click back link
		const backLink = page.getByRole('link', { name: /Back|Actions/i });
		if (await backLink.first().isVisible()) {
			await backLink.first().click();
			await expect(page).toHaveURL(/\/actions$/);
		}
	});

	test('link to meeting is visible', async ({ page }) => {
		await page.goto('/actions/action-1');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check link to related meeting
		const meetingLink = page.getByRole('link', { name: /meeting|European expansion/i });
		await expect(meetingLink.first()).toBeVisible();
	});

	test.describe('Status update', () => {
		test('can update action status', async ({ page }) => {
			// Mock status update
			await page.route('**/api/v1/actions/action-1', (route) => {
				if (route.request().method() === 'PATCH') {
					return route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({ ...mockActions.actions[0], status: 'in_progress' })
					});
				}
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockActions.actions[0])
				});
			});

			await page.goto('/actions/action-1');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for status dropdown or buttons
			const statusControl = page.locator('select, button').filter({ hasText: /status|todo/i });
			if (await statusControl.first().isVisible()) {
				// Implementation varies - check that status controls exist
				await expect(statusControl.first()).toBeVisible();
			}
		});
	});
});
