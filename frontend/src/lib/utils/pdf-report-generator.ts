/**
 * PDF Report Generator
 *
 * Generates HTML reports from meeting session data for PDF export.
 * Extracted from meeting page for reusability and maintainability.
 *
 * CSS styles are in: /src/lib/styles/pdf-report.css
 * Markdown utilities: /src/lib/utils/markdown-formatter.ts
 * Data extraction: /src/lib/utils/report-data-extractor.ts
 */

import type { SSEEvent } from '$lib/api/sse-events';
import type { ActionStatus } from '$lib/api/types';
import { formatMarkdownToHtml, parseSynthesisSections, type ParsedAction } from './markdown-formatter';
import {
	extractExperts,
	extractSubProblems,
	extractSynthesis,
	countContributionsByExpert,
	calculateRounds,
	calculateDuration,
	getContributionCount,
	formatReportDate,
	getInitials
} from './report-data-extractor';

// Import CSS as raw string for inline embedding in HTML document
import pdfReportCss from '$lib/styles/pdf-report.css?raw';

// Session data interface (compatible with SessionDetailResponse and local SessionData)
interface SessionInfo {
	id: string;
	problem?: {
		statement: string;
		context?: Record<string, unknown>;
	};
	status: string;
	phase?: string | null;
	created_at: string;
}

/**
 * Action data for PDF report
 */
export interface ReportAction {
	id: string;
	title: string;
	description: string;
	status: ActionStatus;
	priority: 'high' | 'medium' | 'low';
	timeline: string;
	target_end_date: string | null;
	// Extended fields for full details
	what_and_how?: string[];
	success_criteria?: string[];
	dependencies?: string[];
	assignee?: string | null;
	progress_value?: number | null;
	progress_type?: 'percentage' | 'points' | 'status' | null;
	estimated_effort_points?: number | null;
	category?: string;
}

/**
 * Parameters for generateReportHTML function
 */
export interface ReportGeneratorParams {
	/** The session data containing problem statement and status */
	session: SessionInfo;
	/** Array of SSE events from the meeting */
	events: SSEEvent[];
	/** Session ID for footer metadata */
	sessionId: string;
	/** Optional actions to include in report */
	actions?: ReportAction[];
}

/**
 * Inline SVG logo (print-clean, no drop shadows)
 */
const LOGO_SVG = `<svg width="36" height="36" viewBox="0 0 264 264" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="4" width="256" height="256" rx="20" fill="#00C3D0"/>
<rect x="4" width="256" height="256" rx="20" fill="url(#pg)"/>
<path d="M142.831 93.1533C142.831 109.288 135.735 120.271 121.545 126.103C140.401 130.379 149.829 141.46 149.829 159.344C149.829 186.559 128.446 200.166 85.6792 200.166C73.2381 200.166 60.4082 199.778 47.1895 199L48.939 157.011L47.1895 58.4542L97.3428 58.1626C111.728 58.1626 122.905 61.1757 130.875 67.2019C138.846 73.228 142.831 81.8785 142.831 93.1533ZM112.505 97.2355C112.505 90.8206 110.659 86.2523 106.965 83.5308C103.272 80.8093 96.6624 79.4486 87.1372 79.4486H76.3484L75.7652 117.647L96.1764 118.521C107.062 115.606 112.505 108.51 112.505 97.2355ZM93.8437 178.88C101.036 178.88 107.16 177.131 112.214 173.632C117.268 169.938 119.795 164.69 119.795 157.886C119.795 147.583 112.991 141.168 99.3839 138.641L75.182 138.933L74.8904 154.387L75.7652 178.006C80.8194 178.589 86.8456 178.88 93.8437 178.88ZM211.82 153.512L213.278 199H183.827L184.994 156.428V120.271L160.209 126.978L158.168 125.228V102.193L209.196 87.3215L213.278 90.529L211.82 153.512Z" fill="white"/>
<defs><linearGradient id="pg" x1="132" y1="0" x2="132" y2="256" gradientUnits="userSpaceOnUse">
<stop offset="0.158654" stop-color="#069CA6" stop-opacity="0"/><stop offset="1" stop-color="#03767E"/>
</linearGradient></defs></svg>`;

const LOGO_SVG_SMALL = LOGO_SVG.replace('width="36" height="36"', 'width="24" height="24"');

/**
 * Render an expert table row
 */
function renderExpertRow(
	expert: { name: string; displayName: string; archetype: string; expertise: string[] },
	contributionCount: number
): string {
	const initials = getInitials(expert.name);
	return `
		<tr>
			<td><span class="expert-avatar">${initials}</span></td>
			<td><strong>${expert.displayName}</strong><br><span class="expert-role-text">${expert.archetype || 'Domain Expert'}</span></td>
			<td>${contributionCount} contribution${contributionCount !== 1 ? 's' : ''}</td>
			<td>${expert.expertise?.slice(0, 3).join(', ') || ''}</td>
		</tr>`;
}

/**
 * Render a focus area item HTML
 */
function renderFocusArea(subProblem: { goal?: string } | string, index: number): string {
	const goal = typeof subProblem === 'string' ? subProblem : subProblem.goal || subProblem;
	return `
		<div class="focus-area">
			<span class="focus-number">${index + 1}</span>
			<div class="focus-content">
				<div class="focus-title">${goal}</div>
			</div>
		</div>`;
}

/**
 * Render a section with header and content
 */
function renderSection(sectionNum: number, title: string, content: string, boxClass: string): string {
	return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">${title}</span>
			</div>
			<div class="${boxClass}">
				<div class="${boxClass === 'recommendation-box' ? 'recommendation-content' : 'analysis-content'}">${content}</div>
			</div>
		</div>`;
}

/**
 * Render recommended actions as a table (from JSON synthesis)
 */
function renderRecommendedActionsTable(actions: ParsedAction[], sectionNum: number): string {
	if (!actions || actions.length === 0) return '';

	const rows = actions.map((a) => {
		const priorityDot = a.priority === 'high' || a.priority === 'critical'
			? '<span class="priority-dot priority-dot-high"></span>'
			: a.priority === 'low'
				? '<span class="priority-dot priority-dot-low"></span>'
				: '<span class="priority-dot priority-dot-medium"></span>';
		return `
		<tr>
			<td>${priorityDot} ${a.priority || 'medium'}</td>
			<td><strong>${a.title}</strong><br><span class="action-desc">${a.description || ''}</span></td>
			<td>${a.timeline || ''}</td>
			<td>${a.success_metrics?.slice(0, 2).join('; ') || ''}</td>
		</tr>`;
	}).join('');

	return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">Recommended Actions</span>
			</div>
			<table class="actions-table">
				<thead><tr><th>Priority</th><th>Action</th><th>Timeline</th><th>Success Metrics</th></tr></thead>
				<tbody>${rows}</tbody>
			</table>
		</div>`;
}

/**
 * Render considerations as a bulleted list
 */
function renderConsiderations(items: string[], sectionNum: number): string {
	if (!items || items.length === 0) return '';
	return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">Implementation Considerations</span>
			</div>
			<ul class="considerations-list">
				${items.map((c) => `<li>${c}</li>`).join('')}
			</ul>
		</div>`;
}

/**
 * Format a date string to a readable format
 */
function formatDate(dateStr: string | null): string {
	if (!dateStr) return 'Not set';
	try {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	} catch {
		return 'Not set';
	}
}

/**
 * Check if a date is overdue (past today)
 */
function isOverdue(dateStr: string | null): boolean {
	if (!dateStr) return false;
	try {
		const dueDate = new Date(dateStr);
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		return dueDate < today;
	} catch {
		return false;
	}
}

/**
 * Truncate text with ellipsis if too long
 */
function truncateText(text: string, maxLength: number): string {
	if (!text || text.length <= maxLength) return text;
	return text.substring(0, maxLength).trim() + '...';
}

/**
 * Format progress value for display
 */
function formatProgress(value: number | null | undefined, type: string | null | undefined): string {
	if (value === null || value === undefined) return '';
	if (type === 'percentage') return `${value}%`;
	if (type === 'points') return `${value} pts`;
	return `${value}`;
}

/**
 * Get status badge class
 */
function getStatusClass(status: ActionStatus): string {
	const statusClasses: Record<ActionStatus, string> = {
		todo: 'status-todo',
		in_progress: 'status-in-progress',
		blocked: 'status-blocked',
		in_review: 'status-in-review',
		done: 'status-done',
		cancelled: 'status-cancelled',
		failed: 'status-failed',
		abandoned: 'status-abandoned',
		replanned: 'status-replanned'
	};
	return statusClasses[status] || 'status-todo';
}

/**
 * Get priority badge class
 */
function getPriorityClass(priority: 'high' | 'medium' | 'low'): string {
	return `priority-${priority}`;
}

/**
 * Render list items HTML (for what_and_how, success_criteria, dependencies)
 */
function renderListItems(items: string[] | undefined, limit: number = 3): string {
	if (!items || items.length === 0) return '';
	const displayItems = items.slice(0, limit);
	const remaining = items.length - limit;
	let html = displayItems.map((item) => `<li>${truncateText(item, 150)}</li>`).join('');
	if (remaining > 0) {
		html += `<li class="more-items">+${remaining} more...</li>`;
	}
	return html;
}

/**
 * Render an action item HTML with full details
 */
function renderActionItem(action: ReportAction): string {
	const statusLabel = action.status.replace('_', ' ');
	const overdue = isOverdue(action.target_end_date) && action.status !== 'done' && action.status !== 'cancelled';
	const description = truncateText(action.description || '', 500);
	const progress = formatProgress(action.progress_value, action.progress_type);

	// Build optional sections
	const whatAndHowHtml = action.what_and_how?.length
		? `<div class="action-section">
			<div class="action-section-label">How to Complete</div>
			<ul class="action-list">${renderListItems(action.what_and_how)}</ul>
		</div>`
		: '';

	const successCriteriaHtml = action.success_criteria?.length
		? `<div class="action-section">
			<div class="action-section-label">Success Criteria</div>
			<ul class="action-list">${renderListItems(action.success_criteria)}</ul>
		</div>`
		: '';

	const dependenciesHtml = action.dependencies?.length
		? `<div class="action-section">
			<div class="action-section-label">Dependencies</div>
			<ul class="action-list action-dependencies">${renderListItems(action.dependencies)}</ul>
		</div>`
		: '';

	return `
		<div class="action-item${overdue ? ' action-overdue' : ''}">
			<div class="action-header">
				<span class="action-title">${action.title}</span>
				<div class="action-badges">
					<span class="action-status ${getStatusClass(action.status)}">${statusLabel}</span>
					<span class="action-priority ${getPriorityClass(action.priority)}">${action.priority}</span>
					${action.category ? `<span class="action-category">${action.category}</span>` : ''}
				</div>
			</div>
			${description ? `<div class="action-description">${description}</div>` : ''}
			${whatAndHowHtml}
			${successCriteriaHtml}
			${dependenciesHtml}
			<div class="action-meta">
				${action.timeline ? `<span class="action-timeline">${action.timeline}</span>` : ''}
				${action.target_end_date ? `<span class="action-due${overdue ? ' overdue' : ''}">Due: ${formatDate(action.target_end_date)}${overdue ? ' (Overdue)' : ''}</span>` : ''}
				${action.assignee ? `<span class="action-assignee">Assigned: ${action.assignee}</span>` : ''}
				${progress ? `<span class="action-progress">Progress: ${progress}</span>` : ''}
				${action.estimated_effort_points ? `<span class="action-effort">Effort: ${action.estimated_effort_points} pts</span>` : ''}
			</div>
		</div>`;
}

/**
 * Render actions section HTML
 */
function renderActionsSection(actions: ReportAction[], sectionNum: number, showEmptyState: boolean = true): string {
	// Handle empty state
	if (!actions || actions.length === 0) {
		if (!showEmptyState) return '';
		return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">Action Items</span>
			</div>
			<div class="actions-empty">
				<p>No actions were generated for this meeting.</p>
			</div>
		</div>`;
	}

	// Sort by priority (high first) then by status
	const sortedActions = [...actions].sort((a, b) => {
		const priorityOrder = { high: 0, medium: 1, low: 2 };
		const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
		if (priorityDiff !== 0) return priorityDiff;
		return a.status.localeCompare(b.status);
	});

	// Limit to 50 actions to prevent PDF overflow
	const displayActions = sortedActions.slice(0, 50);
	const hiddenCount = sortedActions.length - 50;

	return `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">Action Items (${actions.length})</span>
			</div>
			<div class="actions-section">
				${displayActions.map((action) => renderActionItem(action)).join('')}
				${hiddenCount > 0 ? `<div class="actions-truncated">+${hiddenCount} more actions not shown</div>` : ''}
			</div>
		</div>`;
}

/**
 * Generate HTML report from session data and events.
 *
 * Creates a professionally formatted HTML document that can be
 * opened in a new window and printed/saved as PDF.
 *
 * Supports both lean synthesis format (The Bottom Line, Why This Matters, etc.)
 * and legacy format (Executive Summary, Recommendation, Rationale).
 *
 * @param params - Report generation parameters
 * @returns Complete HTML document as a string
 */
export function generateReportHTML(params: ReportGeneratorParams): string {
	const { session, events, sessionId, actions } = params;

	if (!session) return '';

	// Extract data using utility functions
	const synthesis = extractSynthesis(events);
	const sections = parseSynthesisSections(synthesis);
	const experts = extractExperts(events);
	const contributionsByDisplayName = countContributionsByExpert(events);
	const subProblems = extractSubProblems(events);
	const totalRounds = calculateRounds(events);
	const contributionCount = getContributionCount(events);
	const durationMins = calculateDuration(session.created_at, events);
	const reportDate = formatReportDate();

	// Fallback: if actions array is empty but synthesis has recommendedActions, convert them
	let effectiveActions = actions || [];
	if (effectiveActions.length === 0 && sections.recommendedActions && sections.recommendedActions.length > 0) {
		effectiveActions = sections.recommendedActions.map((ra, i) => ({
			id: `synth-action-${i}`,
			title: ra.title,
			description: ra.description || ra.rationale || '',
			status: 'todo' as ActionStatus,
			priority: (ra.priority === 'critical' ? 'high' : ra.priority || 'medium') as 'high' | 'medium' | 'low',
			timeline: ra.timeline || '',
			target_end_date: null,
			success_criteria: ra.success_metrics
		}));
	}

	// Build synthesis sections HTML and track section count
	let sectionNum = 1;

	// Expert panel section
	const expertRows = experts.map((exp) =>
		renderExpertRow(exp, contributionsByDisplayName.get(exp.displayName) || 0)
	).join('');

	const expertPanelHtml = `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">Expert Panel</span>
			</div>
			<table class="expert-table">
				<thead><tr><th></th><th>Expert</th><th>Contributions</th><th>Expertise</th></tr></thead>
				<tbody>${expertRows}</tbody>
			</table>
		</div>`;
	sectionNum++;

	// Focus areas
	let focusAreasHtml = '';
	if (subProblems.length > 0) {
		focusAreasHtml = `
		<div class="section">
			<div class="section-header">
				<span class="section-number">${sectionNum}.</span>
				<span class="section-title">Focus Areas Analyzed</span>
			</div>
			${subProblems.map((sp, i) => renderFocusArea(sp, i)).join('')}
		</div>`;
		sectionNum++;
	}

	// Synthesis sections
	let synthHtml = '';

	if (sections.bottomLine) {
		synthHtml += renderSection(sectionNum++, 'The Bottom Line', formatMarkdownToHtml(sections.bottomLine), 'recommendation-box');
	}

	if (sections.whyItMatters) {
		synthHtml += renderSection(sectionNum++, 'Why This Matters', formatMarkdownToHtml(sections.whyItMatters), 'full-analysis');
	}

	if (sections.nextSteps) {
		synthHtml += renderSection(sectionNum++, 'What To Do Next', formatMarkdownToHtml(sections.nextSteps), 'full-analysis');
	}

	if (sections.keyRisks) {
		synthHtml += renderSection(sectionNum++, 'Key Risks', formatMarkdownToHtml(sections.keyRisks), 'full-analysis');
	}

	if (sections.confidence) {
		synthHtml += renderSection(sectionNum++, 'Board Confidence', formatMarkdownToHtml(sections.confidence), 'full-analysis');
	}

	// Legacy format fallback
	if (!sections.bottomLine && !sections.whyItMatters && !sections.nextSteps) {
		if (sections.recommendation) {
			synthHtml += renderSection(sectionNum++, 'Recommendation', formatMarkdownToHtml(sections.recommendation), 'recommendation-box');
		}
		if (sections.rationale) {
			synthHtml += renderSection(sectionNum++, 'Rationale', formatMarkdownToHtml(sections.rationale), 'full-analysis');
		}
	}

	// Full synthesis fallback
	if (!synthHtml && synthesis) {
		synthHtml = renderSection(sectionNum++, 'Analysis', formatMarkdownToHtml(synthesis), 'full-analysis');
	}

	// Recommended actions table (from JSON synthesis)
	let recActionsHtml = '';
	if (sections.recommendedActions && sections.recommendedActions.length > 0) {
		recActionsHtml = renderRecommendedActionsTable(sections.recommendedActions, sectionNum++);
	}

	// Action items section
	const actionsHtml = renderActionsSection(effectiveActions, sectionNum++, true);

	// Considerations
	let considerationsHtml = '';
	if (sections.considerations && sections.considerations.length > 0) {
		considerationsHtml = renderConsiderations(sections.considerations, sectionNum++);
	}

	return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>Decision Report</title>
	<style>${pdfReportCss}</style>
</head>
<body>
	<div class="page">
		<!-- Cover Section -->
		<div class="cover">
			<div class="cover-header">
				<div class="logo-section">
					${LOGO_SVG}
					<span class="brand-name">Board of One</span>
				</div>
				<span class="report-type">Decision Report</span>
			</div>

			<h1 class="decision-question">${session.problem?.statement || 'Strategic Decision Analysis'}</h1>
			<p class="report-meta">Strategic Decision Analysis &middot; ${reportDate}</p>

			<!-- Metrics inline on cover -->
			<div class="metrics-grid">
				<div class="metric-card">
					<div class="metric-value">${experts.length}</div>
					<div class="metric-label">Expert Perspectives</div>
				</div>
				<div class="metric-card">
					<div class="metric-value">${totalRounds}</div>
					<div class="metric-label">Meeting Rounds</div>
				</div>
				<div class="metric-card">
					<div class="metric-value">${contributionCount}</div>
					<div class="metric-label">Key Insights</div>
				</div>
				<div class="metric-card">
					<div class="metric-value">${durationMins}m</div>
					<div class="metric-label">Analysis Time</div>
				</div>
			</div>
		</div>

		<!-- Executive Summary -->
		${
			sections.executiveSummary
				? `
		<div class="exec-summary">
			<div class="exec-summary-label">Executive Summary</div>
			<div class="exec-summary-text">${formatMarkdownToHtml(sections.executiveSummary)}</div>
		</div>`
				: ''
		}

		<!-- Expert Panel -->
		${expertPanelHtml}

		<!-- Focus Areas -->
		${focusAreasHtml}

		<!-- Synthesis Sections -->
		${synthHtml}

		<!-- Recommended Actions Table (from synthesis JSON) -->
		${recActionsHtml}

		<!-- Action Items -->
		${actionsHtml}

		<!-- Implementation Considerations -->
		${considerationsHtml}

		<!-- Footer -->
		<div class="footer">
			<div class="footer-top">
				<div class="footer-brand">
					${LOGO_SVG_SMALL}
					<span class="footer-name">Board of One</span>
				</div>
				<div class="session-info">
					Session: ${sessionId.substring(0, 8)}&hellip; &middot; ${new Date().toISOString().split('T')[0]}
				</div>
			</div>

			<div class="disclaimer">
				This report was generated using AI-assisted deliberation for learning and knowledge purposes only.
				It does not constitute professional, legal, financial, or medical advice. Verify recommendations with
				licensed professionals before taking action.
			</div>
		</div>
	</div>
</body>
</html>`;
}
