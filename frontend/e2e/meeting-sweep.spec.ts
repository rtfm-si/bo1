/**
 * E2E sweep test for meeting lifecycle (create → in-progress → complete).
 *
 * Tests:
 * - Meeting creation form and validation
 * - In-progress meeting phases and SSE events
 * - Completed meeting view (synthesis, tabs, export)
 * - Edge cases (validation, 404, errors)
 *
 * Reports findings to console for manual review (follows admin-sweep pattern).
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

// Mock user data
const mockUser = {
	user_id: 'test-user-sweep',
	email: 'sweep@example.com',
	is_admin: false,
	tier: 'starter',
	workspace_id: 'ws-1'
};

// Mock session data for various states
const mockPendingSession = {
	id: 'sweep-pending-session',
	problem_statement: 'Should we expand to European markets this quarter?',
	status: 'pending',
	phase: 'pending',
	created_at: new Date().toISOString(),
	updated_at: new Date().toISOString(),
	last_activity_at: new Date().toISOString(),
	cost: 0,
	expert_count: 0,
	contribution_count: 0,
	task_count: 0,
	focus_area_count: 0,
	stale_insights: null
};

const mockActiveSession = {
	...mockPendingSession,
	id: 'sweep-active-session',
	status: 'active',
	phase: 'deliberation',
	expert_count: 3,
	contribution_count: 2,
	problem: {
		statement: 'Should we expand to European markets this quarter?',
		sub_problems: [
			{ id: 'sp1', goal: 'Market opportunity assessment' },
			{ id: 'sp2', goal: 'Resource requirements analysis' }
		]
	}
};

const mockCompletedSession = {
	...mockActiveSession,
	id: 'sweep-completed-session',
	status: 'completed',
	phase: 'complete',
	cost: 0.15,
	contribution_count: 6,
	task_count: 4,
	focus_area_count: 2
};

// Mock events for completed session
const mockCompletedEvents = [
	{
		event_type: 'session_started',
		data: { session_id: 'sweep-completed-session' },
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
				{ name: 'Market Expert', role: 'market' },
				{ name: 'Finance Lead', role: 'finance' }
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
			content: 'Analysis of market opportunity shows significant potential in Germany and UK markets.'
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'contribution',
		data: {
			sub_problem_index: 0,
			round: 1,
			persona_name: 'Market Expert',
			content: 'Market dynamics suggest timing is favorable with reduced competition post-Brexit.'
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'contribution',
		data: {
			sub_problem_index: 0,
			round: 1,
			persona_name: 'Finance Lead',
			content: 'Initial investment of €500K recommended with 18-month ROI projection.'
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'convergence',
		data: {
			sub_problem_index: 0,
			round: 1,
			score: 0.85,
			exploration_score: 0.78,
			novelty_score: 0.72
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'synthesis_complete',
		data: {
			sub_problem_id: 'sp1',
			sub_problem_index: 0,
			recommendation: 'Proceed with phased European expansion',
			key_insights: ['Germany is primary target', 'UK secondary market', 'Q1 2025 optimal timing']
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'meta_synthesis_complete',
		data: {
			synthesis: JSON.stringify({
				problem_statement: 'Should we expand to European markets this quarter?',
				synthesis_summary:
					'Based on comprehensive analysis, we recommend a phased European expansion starting with Germany in Q1 2025.',
				sub_problems_addressed: ['Market opportunity assessment', 'Resource requirements analysis'],
				recommended_actions: [
					{
						action: 'Conduct detailed market research in Germany',
						rationale: 'Understand regulatory requirements and competitive landscape',
						priority: 'high',
						timeline: 'Q4 2024',
						success_metrics: ['Market analysis complete', 'Partner shortlist created'],
						risks: ['Resource availability', 'Market timing']
					},
					{
						action: 'Establish local partnership network',
						rationale: 'Build distribution and support presence',
						priority: 'high',
						timeline: 'Q1 2025',
						success_metrics: ['3+ partnerships signed', 'Support SLAs in place'],
						risks: ['Partner alignment', 'Contract negotiations']
					},
					{
						action: 'Adapt product for EU compliance',
						rationale: 'Ensure GDPR and local regulatory compliance',
						priority: 'medium',
						timeline: 'Q1 2025',
						success_metrics: ['GDPR audit passed', 'Local data residency'],
						risks: ['Engineering capacity', 'Compliance complexity']
					}
				]
			})
		},
		timestamp: new Date().toISOString()
	},
	{
		event_type: 'session_complete',
		data: { session_id: 'sweep-completed-session' },
		timestamp: new Date().toISOString()
	}
];

// Mock events for active/in-progress session
const mockActiveEvents = mockCompletedEvents.slice(0, 6); // Up to contributions

// Mock datasets
const mockDatasets = {
	datasets: [
		{ id: 'ds1', name: 'Sales Data 2024', row_count: 1500 },
		{ id: 'ds2', name: 'Customer Survey', row_count: 500 }
	]
};

test.describe('Meeting Lifecycle Sweep', () => {
	test.beforeEach(async ({ page }) => {
		// Mock user API
		await page.route('**/api/v1/user', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockUser)
			})
		);

		// Mock datasets API
		await page.route('**/api/v1/datasets*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockDatasets)
			})
		);

		// Mock sessions list API
		await page.route('**/api/v1/sessions', (route) => {
			if (route.request().method() === 'GET') {
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ sessions: [], total: 0 })
				});
			}
			// POST - create session
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockPendingSession)
			});
		});

		// Mock individual session endpoints
		await page.route('**/api/v1/sessions/sweep-pending-session', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockPendingSession)
			})
		);

		await page.route('**/api/v1/sessions/sweep-active-session', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockActiveSession)
			})
		);

		await page.route('**/api/v1/sessions/sweep-completed-session', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(mockCompletedSession)
			})
		);

		// Mock events APIs
		await page.route('**/api/v1/sessions/sweep-pending-session/events', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ session_id: 'sweep-pending-session', events: [], count: 0 })
			})
		);

		await page.route('**/api/v1/sessions/sweep-active-session/events', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					session_id: 'sweep-active-session',
					events: mockActiveEvents,
					count: mockActiveEvents.length
				})
			})
		);

		await page.route('**/api/v1/sessions/sweep-completed-session/events', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					session_id: 'sweep-completed-session',
					events: mockCompletedEvents,
					count: mockCompletedEvents.length
				})
			})
		);

		// Mock SSE streams
		await page.route('**/api/v1/sessions/*/stream', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: 'data: {"event_type":"heartbeat","data":{}}\n\n'
			})
		);

		// Mock start session
		await page.route('**/api/v1/sessions/*/start', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ status: 'started' })
			})
		);

		// Mock share endpoints
		await page.route('**/api/v1/sessions/*/share', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					share_token: 'test-share-token',
					share_url: 'https://boardof.one/share/test-share-token'
				})
			})
		);

		// Mock PDF export
		await page.route('**/api/v1/sessions/*/export*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/pdf',
				body: Buffer.from('%PDF-1.4 test content')
			})
		);
	});

	// ===== MEETING CREATION FLOW =====
	test.describe('Meeting Creation Flow', () => {
		test('new meeting page renders correctly', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				addFinding('Meeting Creation', 'warning', 'Redirected to login - skipping test');
				test.skip();
				return;
			}

			// Check page heading
			const heading = page.getByRole('heading', { name: /Start New Meeting|New Meeting/i });
			const headingVisible = await heading.isVisible().catch(() => false);
			if (!headingVisible) {
				addFinding('Meeting Creation', 'error', 'Page heading not found');
			}

			// Check textarea
			const textarea = page.locator('#problem, textarea[name="problem"], textarea[placeholder*="Example"]');
			const textareaVisible = await textarea.first().isVisible().catch(() => false);
			if (!textareaVisible) {
				addFinding('Meeting Creation', 'error', 'Problem textarea not found');
			}

			// Check submit button
			const submitBtn = page.getByRole('button', { name: /Start Meeting/i });
			await expect(submitBtn).toBeVisible();

			// Check cancel button
			const cancelLink = page.getByRole('link', { name: /Cancel/i });
			const cancelVisible = await cancelLink.isVisible().catch(() => false);
			if (!cancelVisible) {
				addFinding('Meeting Creation', 'info', 'Cancel link not found');
			}
		});

		test('form validation prevents short input', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem, textarea').first();
			const submitBtn = page.getByRole('button', { name: /Start Meeting/i });

			// Initially disabled
			const initiallyDisabled = await submitBtn.isDisabled();
			if (!initiallyDisabled) {
				addFinding('Meeting Creation', 'warning', 'Submit button not disabled initially');
			}

			// Short text should keep disabled
			await textarea.fill('Short');
			const stillDisabled = await submitBtn.isDisabled();
			if (!stillDisabled) {
				addFinding('Meeting Creation', 'error', 'Submit button enabled with short text');
			}

			// Valid text should enable
			await textarea.fill(
				'Should we expand to European markets this quarter given current economic conditions?'
			);
			await expect(submitBtn).toBeEnabled();
		});

		test('example questions populate textarea', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Check examples section exists
			const examplesSection = page.getByText(/Need inspiration|Examples/i);
			const examplesVisible = await examplesSection.isVisible().catch(() => false);
			if (!examplesVisible) {
				addFinding('Meeting Creation', 'info', 'Examples section not found');
				return;
			}

			// Click an example button
			const exampleBtn = page.locator('button').filter({ hasText: /Series A|Expansion|Market/i }).first();
			if (await exampleBtn.isVisible()) {
				await exampleBtn.click();

				const textarea = page.locator('#problem, textarea').first();
				const value = await textarea.inputValue();
				if (value.length < 20) {
					addFinding('Meeting Creation', 'error', 'Example did not populate textarea');
				}
			}
		});

		test('dataset selector visible when datasets exist', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Check for dataset selector
			const datasetLabel = page.getByText(/Attach Dataset|Dataset/i);
			const datasetVisible = await datasetLabel.isVisible().catch(() => false);
			if (!datasetVisible) {
				addFinding('Meeting Creation', 'info', 'Dataset selector not visible');
			} else {
				// Check dropdown has options
				const select = page.locator('#dataset, select[name="dataset"]').first();
				if (await select.isVisible()) {
					const options = await select.locator('option').count();
					if (options < 2) {
						addFinding('Meeting Creation', 'warning', 'Dataset selector has fewer options than expected');
					}
				}
			}
		});

		test('cancel button navigates back', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const cancelLink = page.getByRole('link', { name: /Cancel|Back/i });
			if (await cancelLink.first().isVisible()) {
				await cancelLink.first().click();
				await page.waitForLoadState('networkidle');

				if (!page.url().includes('/dashboard')) {
					addFinding('Meeting Creation', 'warning', 'Cancel did not navigate to dashboard');
				}
			}
		});

		test('form submission shows loading state', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem, textarea').first();
			const submitBtn = page.getByRole('button', { name: /Start Meeting/i });

			await textarea.fill(
				'Should we expand to European markets this quarter given current economic conditions?'
			);

			// Add delay to API response
			await page.route('**/api/v1/sessions', async (route) => {
				if (route.request().method() === 'POST') {
					await new Promise((r) => setTimeout(r, 1000));
					await route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify(mockPendingSession)
					});
				} else {
					await route.continue();
				}
			});

			await submitBtn.click();

			// Check for loading state
			const loadingText = page.getByText(/Starting|Loading|Creating/i);
			const loadingVisible = await loadingText.isVisible().catch(() => false);
			if (!loadingVisible) {
				addFinding('Meeting Creation', 'info', 'Loading state text not visible during submission');
			}
		});

		test('API error shows error message', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			// Mock API failure
			await page.route('**/api/v1/sessions', (route) => {
				if (route.request().method() === 'POST') {
					return route.fulfill({
						status: 500,
						contentType: 'application/json',
						body: JSON.stringify({ detail: 'Internal server error' })
					});
				}
				return route.continue();
			});

			const textarea = page.locator('#problem, textarea').first();
			const submitBtn = page.getByRole('button', { name: /Start Meeting/i });

			await textarea.fill(
				'Should we expand to European markets this quarter given current economic conditions?'
			);
			await submitBtn.click();

			// Check for error indication (toast or inline)
			await page.waitForTimeout(1000);
			const errorIndicator = page.locator('[role="alert"], .toast, [data-sonner-toast], .error');
			const errorVisible = await errorIndicator.first().isVisible().catch(() => false);
			if (!errorVisible) {
				addFinding('Meeting Creation', 'warning', 'Error message not displayed after API failure');
			}
		});
	});

	// ===== IN-PROGRESS MEETING =====
	test.describe('In-Progress Meeting', () => {
		test('active meeting shows correct status', async ({ page }) => {
			await page.goto('/meeting/sweep-active-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for in-progress indicator
			const statusIndicator = page.getByText(/In Progress|Working|Deliberating|Active/i);
			const statusVisible = await statusIndicator.first().isVisible().catch(() => false);
			if (!statusVisible) {
				addFinding('In-Progress Meeting', 'warning', 'Status indicator not showing in-progress state');
			}
		});

		test('expert panel displays personas', async ({ page }) => {
			await page.goto('/meeting/sweep-active-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for expert names from our mock data
			const expertNames = ['Strategic Analyst', 'Market Expert', 'Finance Lead'];
			let foundExperts = 0;

			for (const name of expertNames) {
				const expert = page.getByText(name);
				if (await expert.first().isVisible().catch(() => false)) {
					foundExperts++;
				}
			}

			if (foundExperts === 0) {
				addFinding('In-Progress Meeting', 'warning', 'No expert personas visible');
			} else if (foundExperts < expertNames.length) {
				addFinding('In-Progress Meeting', 'info', `Only ${foundExperts}/${expertNames.length} experts visible`);
			}
		});

		test('contribution cards render', async ({ page }) => {
			await page.goto('/meeting/sweep-active-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Look for contribution content
			const contributions = page.locator('[data-testid="contribution"], .contribution, article');
			const contribCount = await contributions.count();

			if (contribCount === 0) {
				// Try finding contribution text
				const contribText = page.getByText(/market opportunity|competitive landscape|Investment/i);
				const hasContribText = await contribText.first().isVisible().catch(() => false);
				if (!hasContribText) {
					addFinding('In-Progress Meeting', 'warning', 'Contribution cards not visible');
				}
			}
		});

		test('phase indicator updates', async ({ page }) => {
			await page.goto('/meeting/sweep-active-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for phase/progress indicator
			const phaseIndicator = page.locator(
				'[data-testid="phase"], .phase, [aria-label*="progress"], .progress'
			);
			const phaseVisible = await phaseIndicator.first().isVisible().catch(() => false);

			// Alternative: check for round indicator
			const roundIndicator = page.getByText(/Round|Phase/i);
			const roundVisible = await roundIndicator.first().isVisible().catch(() => false);

			if (!phaseVisible && !roundVisible) {
				addFinding('In-Progress Meeting', 'info', 'Phase/progress indicator not visible');
			}
		});
	});

	// ===== COMPLETED MEETING VIEW =====
	test.describe('Completed Meeting View', () => {
		test('shows "Meeting Complete" status', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			const completeStatus = page.getByText(/Meeting Complete|Completed/i);
			const statusVisible = await completeStatus.first().isVisible().catch(() => false);
			if (!statusVisible) {
				addFinding('Completed Meeting', 'warning', 'Complete status not visible');
			}
		});

		test('synthesis tab displays conclusion', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Click Summary/Synthesis tab if needed
			const summaryTab = page.getByRole('tab', { name: /Summary|Synthesis|Conclusion/i });
			if (await summaryTab.isVisible()) {
				await summaryTab.click();
				await page.waitForTimeout(300);
			}

			// Check for synthesis content
			const synthesisContent = page.getByText(/phased.*expansion|European.*expansion/i);
			const contentVisible = await synthesisContent.first().isVisible().catch(() => false);
			if (!contentVisible) {
				addFinding('Completed Meeting', 'error', 'Synthesis content not visible');
			}
		});

		test('focus area tabs navigate correctly', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Find focus area tabs
			const tabs = page.getByRole('tab').filter({ hasText: /Market|Resource|Focus/i });
			const tabCount = await tabs.count();

			if (tabCount >= 2) {
				// Click second tab
				await tabs.nth(1).click();
				await page.waitForTimeout(300);

				// Content should change
				const tabPanel = page.getByRole('tabpanel');
				const panelVisible = await tabPanel.first().isVisible().catch(() => false);
				if (!panelVisible) {
					addFinding('Completed Meeting', 'warning', 'Tab panel not visible after tab click');
				}
			} else if (tabCount === 0) {
				addFinding('Completed Meeting', 'info', 'No focus area tabs found');
			}
		});

		test('recommendations list renders', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Navigate to summary tab if needed
			const summaryTab = page.getByRole('tab', { name: /Summary/i });
			if (await summaryTab.isVisible()) {
				await summaryTab.click();
				await page.waitForTimeout(300);
			}

			// Check for recommended actions
			const actionKeywords = ['market research', 'partnership', 'compliance', 'Germany'];
			let foundActions = 0;

			for (const keyword of actionKeywords) {
				const action = page.getByText(new RegExp(keyword, 'i'));
				if (await action.first().isVisible().catch(() => false)) {
					foundActions++;
				}
			}

			if (foundActions === 0) {
				addFinding('Completed Meeting', 'warning', 'No recommended actions visible');
			}
		});

		test('PDF export button triggers download', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			const exportBtn = page.getByRole('button', { name: /Export|Download|PDF/i });
			const exportVisible = await exportBtn.first().isVisible().catch(() => false);

			if (!exportVisible) {
				addFinding('Completed Meeting', 'warning', 'Export button not visible');
				return;
			}

			// Set up download listener
			const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

			await exportBtn.first().click();

			const download = await downloadPromise;
			if (!download) {
				addFinding('Completed Meeting', 'info', 'Download not triggered (may be modal or different flow)');
			}
		});

		test('share functionality works', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			const shareBtn = page.getByRole('button', { name: /Share/i });
			const shareVisible = await shareBtn.first().isVisible().catch(() => false);

			if (!shareVisible) {
				addFinding('Completed Meeting', 'info', 'Share button not visible');
				return;
			}

			await shareBtn.first().click();
			await page.waitForTimeout(500);

			// Check for share modal/dialog or copied notification
			const shareDialog = page.locator('[role="dialog"], .modal, [data-testid="share"]');
			const shareNotification = page.getByText(/copied|share link|link generated/i);

			const dialogVisible = await shareDialog.first().isVisible().catch(() => false);
			const notificationVisible = await shareNotification.first().isVisible().catch(() => false);

			if (!dialogVisible && !notificationVisible) {
				addFinding('Completed Meeting', 'warning', 'Share action did not show feedback');
			}
		});

		test('meeting metrics visible', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for metrics labels
			const metricLabels = ['Rounds', 'Contributions', 'Experts', 'Cost'];
			let foundMetrics = 0;

			for (const label of metricLabels) {
				const metric = page.getByText(new RegExp(label, 'i'));
				if (await metric.first().isVisible().catch(() => false)) {
					foundMetrics++;
				}
			}

			if (foundMetrics === 0) {
				addFinding('Completed Meeting', 'warning', 'No meeting metrics visible');
			} else if (foundMetrics < 2) {
				addFinding('Completed Meeting', 'info', `Only ${foundMetrics} metrics visible`);
			}
		});

		test('no raw JSON in synthesis display', async ({ page }) => {
			await page.goto('/meeting/sweep-completed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Navigate to summary tab if needed
			const summaryTab = page.getByRole('tab', { name: /Summary/i });
			if (await summaryTab.isVisible()) {
				await summaryTab.click();
				await page.waitForTimeout(300);
			}

			// Get visible text
			const pageContent = await page.locator('main, [role="main"], .content').first().textContent();

			// Check for raw JSON patterns
			const jsonPatterns = [/\{\s*"[^"]+"\s*:/, /"\s*:\s*\[\s*"/, /"priority"\s*:\s*"/];

			for (const pattern of jsonPatterns) {
				if (pattern.test(pageContent || '')) {
					addFinding('Completed Meeting', 'error', 'Raw JSON visible in synthesis display');
					break;
				}
			}
		});
	});

	// ===== EDGE CASES =====
	test.describe('Edge Cases', () => {
		test('empty problem statement validation', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const submitBtn = page.getByRole('button', { name: /Start Meeting/i });

			// Should be disabled with empty input
			await expect(submitBtn).toBeDisabled();

			// Check for validation message
			const validationMsg = page.getByText(/minimum|required|characters/i);
			const msgVisible = await validationMsg.first().isVisible().catch(() => false);
			if (!msgVisible) {
				addFinding('Edge Cases', 'info', 'No validation message for empty input');
			}
		});

		test('very long problem statement handling', async ({ page }) => {
			await page.goto('/meeting/new');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			const textarea = page.locator('#problem, textarea').first();

			// Fill very long text
			const longText = 'Should we expand? '.repeat(500); // ~9000 chars
			await textarea.fill(longText);

			// Check if truncated or character count shown
			const charCount = page.locator('[data-testid="char-count"], .char-count');
			const charCountVisible = await charCount.isVisible().catch(() => false);

			const value = await textarea.inputValue();
			if (value.length > 10000) {
				addFinding('Edge Cases', 'warning', 'Very long input not truncated');
			}
		});

		test('meeting not found (404)', async ({ page }) => {
			// Mock 404 for non-existent session
			await page.route('**/api/v1/sessions/non-existent-session', (route) =>
				route.fulfill({
					status: 404,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'Session not found' })
				})
			);

			await page.goto('/meeting/non-existent-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for 404 message or redirect
			const notFoundMsg = page.getByText(/not found|404|doesn't exist|does not exist/i);
			const msgVisible = await notFoundMsg.first().isVisible().catch(() => false);

			const redirectedToDashboard = page.url().includes('/dashboard');

			if (!msgVisible && !redirectedToDashboard) {
				addFinding('Edge Cases', 'warning', 'No 404 message or redirect for non-existent meeting');
			}
		});

		test('session expired/killed state', async ({ page }) => {
			// Mock killed session
			await page.route('**/api/v1/sessions/sweep-killed-session', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						...mockActiveSession,
						id: 'sweep-killed-session',
						status: 'killed',
						phase: 'killed'
					})
				})
			);

			await page.route('**/api/v1/sessions/sweep-killed-session/events', (route) =>
				route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({
						session_id: 'sweep-killed-session',
						events: [
							...mockActiveEvents,
							{
								event_type: 'session_killed',
								data: { reason: 'Admin terminated' },
								timestamp: new Date().toISOString()
							}
						],
						count: mockActiveEvents.length + 1
					})
				})
			);

			await page.goto('/meeting/sweep-killed-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');

			// Check for killed/terminated indicator
			const killedMsg = page.getByText(/killed|terminated|stopped|cancelled/i);
			const msgVisible = await killedMsg.first().isVisible().catch(() => false);
			if (!msgVisible) {
				addFinding('Edge Cases', 'info', 'No killed status indicator visible');
			}
		});

		test('network error handling', async ({ page }) => {
			// Mock network error
			await page.route('**/api/v1/sessions/sweep-error-session', (route) => route.abort('failed'));

			await page.goto('/meeting/sweep-error-session');

			if (page.url().includes('/login')) {
				test.skip();
				return;
			}

			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(2000);

			// Check for error message
			const errorMsg = page.getByText(/error|failed|unable|couldn't load/i);
			const msgVisible = await errorMsg.first().isVisible().catch(() => false);
			if (!msgVisible) {
				addFinding('Edge Cases', 'warning', 'No error message for network failure');
			}
		});
	});

	// ===== CONSOLE ERRORS =====
	test('no critical console errors', async ({ page }) => {
		const consoleErrors: string[] = [];

		page.on('console', (msg) => {
			if (msg.type() === 'error') {
				consoleErrors.push(msg.text());
			}
		});

		// Visit multiple pages
		await page.goto('/meeting/new');
		await page.waitForLoadState('networkidle');

		await page.goto('/meeting/sweep-completed-session');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		// Filter critical errors
		const criticalErrors = consoleErrors.filter(
			(err) =>
				!err.includes('net::') &&
				!err.includes('favicon') &&
				!err.includes('404') &&
				!err.includes('ERR_BLOCKED_BY_CLIENT') &&
				(err.includes('TypeError') ||
					err.includes('SyntaxError') ||
					err.includes('ReferenceError') ||
					err.includes('Uncaught'))
		);

		if (criticalErrors.length > 0) {
			for (const err of criticalErrors.slice(0, 5)) {
				addFinding('Console', 'error', `JS Error: ${err.slice(0, 200)}`);
			}
		}
	});

	// ===== FINDINGS SUMMARY =====
	test.afterAll(() => {
		console.log('\n=== MEETING SWEEP FINDINGS SUMMARY ===\n');

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
