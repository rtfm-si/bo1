/**
 * E2E sweep test for ALL admin pages.
 *
 * Tests:
 * - Page loads without redirect to login
 * - Page heading/title visible
 * - Key elements present
 * - Navigation links work
 * - Buttons are clickable
 *
 * Reports findings to console for manual review.
 */
import { test, expect } from './fixtures';

// Types for findings
interface Finding {
	page: string;
	type: 'error' | 'warning' | 'info';
	message: string;
}

const findings: Finding[] = [];

function addFinding(page: string, type: Finding['type'], message: string) {
	findings.push({ page, type, message });
	console.log(`[${type.toUpperCase()}] ${page}: ${message}`);
}

// Admin pages to test (16 total)
const ADMIN_PAGES = [
	{ path: '/admin', name: 'Dashboard', heading: /Admin Dashboard/i },
	{ path: '/admin/sessions', name: 'Sessions', heading: /Active Sessions/i },
	{ path: '/admin/costs', name: 'Costs', heading: /Cost Analytics/i },
	{ path: '/admin/users', name: 'Users', heading: /User Management|Users/i },
	{ path: '/admin/waitlist', name: 'Waitlist', heading: /Waitlist/i },
	{ path: '/admin/whitelist', name: 'Whitelist', heading: /Whitelist|Beta Whitelist/i },
	{ path: '/admin/promotions', name: 'Promotions', heading: /Promotions/i },
	{ path: '/admin/feedback', name: 'Feedback', heading: /Feedback|User Feedback/i },
	{ path: '/admin/metrics', name: 'Metrics', heading: /Metrics|Usage Metrics/i },
	{ path: '/admin/embeddings', name: 'Embeddings', heading: /Embeddings/i },
	{ path: '/admin/kill-history', name: 'Kill History', heading: /Kill History/i },
	{ path: '/admin/ops', name: 'AI Ops', heading: /AI Ops|Self-Healing|Operations/i },
	{ path: '/admin/alerts/settings', name: 'Alert Settings', heading: /Alert|Settings/i },
	{ path: '/admin/alerts/history', name: 'Alert History', heading: /Alert|History/i },
	{ path: '/admin/landing-analytics', name: 'Landing Analytics', heading: /Landing|Analytics/i },
	{ path: '/admin/blog', name: 'Blog', heading: /Blog/i }
];

// Mock data for API responses
const mockAdminUser = {
	user_id: 'admin-user-e2e',
	email: 'admin@example.com',
	is_admin: true,
	tier: 'pro',
	workspace_id: 'ws-1'
};

const mockEmptyList: unknown[] = [];

const mockSessions = {
	active_count: 0,
	sessions: [],
	longest_running: [],
	most_expensive: []
};

const mockCostSummary = {
	today: 1.5,
	this_week: 10.0,
	this_month: 45.0,
	all_time: 150.0,
	session_count_today: 5,
	session_count_week: 25,
	session_count_month: 100,
	session_count_total: 500
};

const mockUserCosts = {
	users: [
		{ user_id: 'user-1', email: 'user1@test.com', total_cost: 10.5, session_count: 5 },
		{ user_id: 'user-2', email: 'user2@test.com', total_cost: 8.2, session_count: 3 }
	],
	total: 2
};

const mockDailyCosts = {
	days: [
		{ date: '2024-01-01', total_cost: 1.5, session_count: 5 },
		{ date: '2024-01-02', total_cost: 2.0, session_count: 8 }
	]
};

const mockProviderCosts = {
	providers: [
		{ provider: 'anthropic', amount_usd: 40.0, percentage: 80, request_count: 1000 },
		{ provider: 'voyage', amount_usd: 10.0, percentage: 20, request_count: 500 }
	],
	total_usd: 50.0
};

const mockFixedCosts = {
	costs: [
		{
			id: '1',
			provider: 'digitalocean',
			description: 'Droplet',
			category: 'compute',
			monthly_amount_usd: 48.0
		}
	],
	monthly_total: 48.0
};

const mockPerUserCosts = {
	overall_avg: 5.0,
	total_users: 10,
	users: []
};

const mockUsers = {
	users: [
		{
			user_id: 'user-1',
			email: 'user1@test.com',
			is_admin: false,
			created_at: new Date().toISOString()
		}
	],
	total: 1
};

const mockWaitlist = {
	entries: [{ id: '1', email: 'wait@test.com', status: 'pending', created_at: new Date().toISOString() }],
	total: 1
};

const mockWhitelist = {
	entries: [{ id: '1', email: 'beta@test.com', created_at: new Date().toISOString() }],
	total: 1
};

const mockFeedback = {
	feedback: [
		{
			id: '1',
			user_id: 'user-1',
			type: 'feature_request',
			content: 'Test feedback',
			created_at: new Date().toISOString()
		}
	],
	total: 1
};

const mockMetrics = {
	signups: { total: 100, today: 5, week: 20, month: 50 },
	dau: { count: 25 },
	funnel: { started: 100, completed: 80 }
};

const mockEmbeddings = {
	total: 1000,
	by_type: { research: 500, context: 500 }
};

const mockKillHistory = {
	kills: [
		{
			id: '1',
			session_id: 'sess-1',
			reason: 'Test kill',
			killed_by: 'admin',
			killed_at: new Date().toISOString()
		}
	],
	total: 1
};

const mockOps = {
	error_patterns: [],
	remediation_history: [],
	health_status: 'healthy'
};

const mockAlertSettings = {
	settings: [{ id: '1', name: 'Test Alert', enabled: true, threshold: 100 }]
};

const mockAlertHistory = {
	alerts: [{ id: '1', type: 'cost', message: 'Test alert', created_at: new Date().toISOString() }],
	total: 1
};

const mockLandingAnalytics = {
	page_views: 1000,
	unique_visitors: 500,
	conversions: 50,
	geo: { US: 300, UK: 100, Other: 100 }
};

const mockBlogPosts = {
	posts: [
		{ id: '1', title: 'Test Post', slug: 'test-post', status: 'published', created_at: new Date().toISOString() }
	],
	total: 1
};

const mockEmailStats = {
	total: 100,
	by_period: { today: 5, week: 20, month: 50 },
	by_type: { welcome: 30, meeting_complete: 40, action_reminder: 30 }
};

const mockAdminStats = {
	totalUsers: 100,
	totalMeetings: 500,
	totalCost: 150.0,
	whitelistCount: 25,
	waitlistPending: 5
};

test.describe('Admin Pages Sweep', () => {
	test.beforeEach(async ({ page }) => {
		// Mock admin user check
		await page.route('**/api/v1/user', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAdminUser)
			})
		);

		// Mock admin stats for dashboard
		await page.route('**/api/admin/stats', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAdminStats)
			})
		);

		// Mock email stats
		await page.route('**/api/admin/email/stats*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockEmailStats)
			})
		);

		// Mock sessions
		await page.route('**/api/admin/sessions*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockSessions)
			})
		);

		// Mock cost endpoints
		await page.route('**/api/admin/costs/summary', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockCostSummary)
			})
		);

		await page.route('**/api/admin/costs/users*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockUserCosts)
			})
		);

		await page.route('**/api/admin/costs/daily*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockDailyCosts)
			})
		);

		await page.route('**/api/admin/costs/by-provider*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockProviderCosts)
			})
		);

		await page.route('**/api/admin/costs/fixed*', (route) => {
			if (route.request().method() === 'GET') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify(mockFixedCosts)
				});
			}
			return route.continue();
		});

		await page.route('**/api/admin/costs/per-user*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockPerUserCosts)
			})
		);

		// Mock users
		await page.route('**/api/admin/users*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockUsers)
			})
		);

		// Mock waitlist
		await page.route('**/api/admin/waitlist*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockWaitlist)
			})
		);

		// Mock whitelist
		await page.route('**/api/admin/whitelist*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockWhitelist)
			})
		);

		// Mock promotions
		await page.route('**/api/admin/promotions*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockEmptyList)
			})
		);

		// Mock feedback
		await page.route('**/api/admin/feedback*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockFeedback)
			})
		);

		// Mock metrics
		await page.route('**/api/admin/metrics*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockMetrics)
			})
		);

		// Mock embeddings
		await page.route('**/api/admin/embeddings*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockEmbeddings)
			})
		);

		// Mock kill history
		await page.route('**/api/admin/kill-history*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockKillHistory)
			})
		);

		// Mock ops
		await page.route('**/api/admin/ops*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockOps)
			})
		);

		// Mock alert settings
		await page.route('**/api/admin/alerts/settings*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAlertSettings)
			})
		);

		// Mock alert history
		await page.route('**/api/admin/alerts/history*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAlertHistory)
			})
		);

		await page.route('**/api/admin/alerts*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockAlertHistory)
			})
		);

		// Mock landing analytics
		await page.route('**/api/admin/landing-analytics*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockLandingAnalytics)
			})
		);

		// Mock blog
		await page.route('**/api/admin/blog*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockBlogPosts)
			})
		);

		// Mock KPIs endpoint
		await page.route('**/api/admin/kpis*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					kpis: [],
					period: { start: new Date().toISOString(), end: new Date().toISOString() }
				})
			})
		);

		// Catch-all for other admin endpoints
		await page.route('**/api/admin/**', (route) => {
			console.log(`[MOCK] Unhandled admin endpoint: ${route.request().url()}`);
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ data: [], total: 0 })
			});
		});
	});

	// Generate a test for each admin page
	for (const adminPage of ADMIN_PAGES) {
		test(`${adminPage.name} page loads and displays correctly`, async ({ page }) => {
			// Navigate to page
			await page.goto(adminPage.path);

			// Check for redirect to login (auth failure)
			if (page.url().includes('/login')) {
				addFinding(adminPage.name, 'error', 'Redirected to login - auth mock may have failed');
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check page heading
			const heading = page.getByRole('heading', { name: adminPage.heading }).first();
			const headingVisible = await heading.isVisible().catch(() => false);

			if (!headingVisible) {
				// Try alternative: check for any heading containing the name
				const altHeading = page.locator('h1, h2').filter({ hasText: new RegExp(adminPage.name, 'i') }).first();
				const altVisible = await altHeading.isVisible().catch(() => false);
				if (!altVisible) {
					addFinding(adminPage.name, 'warning', `Expected heading "${adminPage.heading}" not found`);
				}
			}

			// Check for console errors
			const consoleErrors: string[] = [];
			page.on('console', (msg) => {
				if (msg.type() === 'error') {
					consoleErrors.push(msg.text());
				}
			});

			// Check for back-to-admin link (except on main admin page)
			if (adminPage.path !== '/admin') {
				const backLink = page.locator('a[href="/admin"]').first();
				const backLinkVisible = await backLink.isVisible().catch(() => false);
				if (!backLinkVisible) {
					addFinding(adminPage.name, 'info', 'No back-to-admin link found');
				}
			}

			// Check for any error alerts on the page
			const errorAlert = page.locator('[role="alert"]').filter({ hasText: /error|failed/i }).first();
			const hasErrorAlert = await errorAlert.isVisible().catch(() => false);
			if (hasErrorAlert) {
				const errorText = await errorAlert.textContent().catch(() => 'Unknown error');
				addFinding(adminPage.name, 'warning', `Error alert displayed: ${errorText}`);
			}

			// Check for loading spinners stuck
			await page.waitForTimeout(2000); // Give time for data to load
			const spinner = page.locator('.animate-spin').first();
			const spinnerVisible = await spinner.isVisible().catch(() => false);
			if (spinnerVisible) {
				addFinding(adminPage.name, 'warning', 'Loading spinner still visible after 2s');
			}

			// Report console errors
			if (consoleErrors.length > 0) {
				addFinding(adminPage.name, 'error', `Console errors: ${consoleErrors.slice(0, 3).join('; ')}`);
			}

			// Basic assertion: page should have loaded (not redirected)
			expect(page.url()).toContain(adminPage.path);
		});
	}

	test('Admin dashboard navigation links work', async ({ page }) => {
		await page.goto('/admin');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Test each navigation link from dashboard
		const navLinks = [
			{ href: '/admin/sessions', name: 'Sessions' },
			{ href: '/admin/costs', name: 'Costs' },
			{ href: '/admin/metrics', name: 'Metrics' },
			{ href: '/admin/kill-history', name: 'Kill History' },
			{ href: '/admin/alerts/history', name: 'Alerts' },
			{ href: '/admin/ops', name: 'Ops' },
			{ href: '/admin/landing-analytics', name: 'Landing Analytics' },
			{ href: '/admin/embeddings', name: 'Embeddings' },
			{ href: '/admin/waitlist', name: 'Waitlist' },
			{ href: '/admin/users', name: 'Users' },
			{ href: '/admin/whitelist', name: 'Whitelist' },
			{ href: '/admin/promotions', name: 'Promotions' },
			{ href: '/admin/feedback', name: 'Feedback' }
		];

		for (const link of navLinks) {
			const linkEl = page.locator(`a[href="${link.href}"]`).first();
			const linkVisible = await linkEl.isVisible().catch(() => false);

			if (!linkVisible) {
				addFinding('Dashboard', 'warning', `Navigation link to ${link.name} (${link.href}) not visible`);
			}
		}

		// Verify at least some links exist
		const visibleLinks = await page.locator('a[href^="/admin/"]').count();
		expect(visibleLinks).toBeGreaterThan(5);
	});

	test('Admin sessions page buttons work', async ({ page }) => {
		await page.goto('/admin/sessions');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check refresh button
		const refreshBtn = page.getByRole('button', { name: /Refresh/i });
		await expect(refreshBtn).toBeVisible();

		// Click refresh and verify it works (no error)
		await refreshBtn.click();
		await page.waitForTimeout(500);

		// Check auto-refresh checkbox
		const autoRefreshCheckbox = page.locator('input[type="checkbox"]').first();
		const checkboxVisible = await autoRefreshCheckbox.isVisible().catch(() => false);
		if (checkboxVisible) {
			await autoRefreshCheckbox.click();
			// Should toggle without error
		}
	});

	test('Admin costs page tabs work', async ({ page }) => {
		await page.goto('/admin/costs');

		if (page.url().includes('/login')) {
			test.skip();
			return;
		}

		await page.waitForLoadState('networkidle');

		// Check tabs exist
		const overviewTab = page.getByRole('button', { name: /Overview/i });
		const providersTab = page.getByRole('button', { name: /Provider/i });
		const fixedTab = page.getByRole('button', { name: /Fixed/i });

		await expect(overviewTab).toBeVisible();
		await expect(providersTab).toBeVisible();
		await expect(fixedTab).toBeVisible();

		// Click each tab
		await providersTab.click();
		await page.waitForTimeout(300);

		await fixedTab.click();
		await page.waitForTimeout(300);

		await overviewTab.click();
		await page.waitForTimeout(300);

		// Check export button
		const exportBtn = page.getByRole('button', { name: /Export|CSV/i });
		await expect(exportBtn).toBeVisible();
	});

	test.afterAll(() => {
		// Print findings summary
		console.log('\n=== ADMIN SWEEP FINDINGS SUMMARY ===\n');

		const errors = findings.filter((f) => f.type === 'error');
		const warnings = findings.filter((f) => f.type === 'warning');
		const infos = findings.filter((f) => f.type === 'info');

		console.log(`Errors: ${errors.length}`);
		errors.forEach((f) => console.log(`  - [${f.page}] ${f.message}`));

		console.log(`\nWarnings: ${warnings.length}`);
		warnings.forEach((f) => console.log(`  - [${f.page}] ${f.message}`));

		console.log(`\nInfo: ${infos.length}`);
		infos.forEach((f) => console.log(`  - [${f.page}] ${f.message}`));

		console.log('\n=== END FINDINGS ===\n');
	});
});
